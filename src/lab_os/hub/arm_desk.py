"""The hub's assistant moves the arm (preview 4, 2026-11-20): "Hey Jarvis, move the arm to home" and
"Jarvis, hand me the cube".

Off unless place.yaml has `assistant_moves_arm: true` (Settings → Robots), never on a public venue,
and only for a question asked on the brain's own computer, like visitor mode (other screens may be
in a hallway). The AI
decides when to use the tools; it never chooses the motion:
- `move_arm_to_pose`: one of poses.yaml's named poses.
- `hand_me_the_cube`: the brain finds the blue cube in the stand camera's picture (a colour search
  here, then the table map: the chat model takes text only), picks it with `pick_at` and holds it
  out at the `handover` pose (config/handover.yaml).
- `let_go_of_the_cube`: opens the gripper when the person says so.
Every move is a robot tool call (lab_os.tools.robot): the same checks as an AI tool's (the soft
limits, the per-call steps, the floor, the venue's speed, one controller at a time), on the AI
Control page, and STOP ends it. The moves run in the background: the answer doesn't wait.
"""

import asyncio
import io
import json
import logging
import math
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from lab_os import config
from lab_os.tools import table_map
from lab_os.tools.robot import DOWN_DEG, PICK_ABOVE_CM, Refused, RobotTools
from lab_os.tools.table_map import TableMap

log = logging.getLogger(__name__)

MOVE, HAND, LET_GO = "move_arm_to_pose", "hand_me_the_cube", "let_go_of_the_cube"
FILE = "handover.yaml"
SCALE = 4  # the colour search looks at 4×4 pixel blocks (fast enough in plain Python)
ENDED = ("stopped", "disconnected")  # a move that ended so: nothing more moves


class NoSetup(Exception):
    """No config/handover.yaml, or one that can't be read. The message says which and why."""


@dataclass(frozen=True)
class HandOver:
    camera: str
    height_cm: float
    hue_deg: tuple[float, float]
    min_saturation: float
    min_value: float
    min_area_px: int
    pose: str
    release_open_pct: float


def load(file: Path | None = None) -> HandOver:
    file = file or config.shared_path(FILE)
    try:
        raw = yaml.safe_load(file.read_text()) or {}
        cube = raw["cube"]
        lo, hi = cube["hue_deg"]
        return HandOver(
            camera=str(raw["camera"]),
            height_cm=float(cube["height_cm"]),
            hue_deg=(float(lo), float(hi)),
            min_saturation=float(cube.get("min_saturation", 0.35)),
            min_value=float(cube.get("min_value", 0.2)),
            min_area_px=int(cube.get("min_area_px", 150)),
            pose=str(raw.get("pose", "handover")),
            release_open_pct=float(raw.get("release_open_pct", 100)),
        )
    except FileNotFoundError:
        raise NoSetup(f"{file} doesn't exist") from None
    except (OSError, yaml.YAMLError, KeyError, TypeError, ValueError) as e:
        raise NoSetup(f"can't read {file}: {e}") from None


def find_cube(jpeg: bytes, m: TableMap, s: HandOver) -> tuple[float, float] | None:
    """Where the cube stands on the table (x, y cm), from a picture of the camera with map `m`:
    the largest patch of the cube's colour, read where it touches the table (its near edge, the
    lowest point in the picture) and moved half its size further from the camera. None: no patch
    big enough."""
    from PIL import Image

    img = Image.open(io.BytesIO(jpeg)).convert("RGB")
    w, h = img.size
    hsv = np.asarray(img.convert("HSV"), dtype=float) / 255.0
    hue, sat, val = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
    lo, hi = s.hue_deg
    in_hue = (hue >= lo) & (hue <= hi) if lo <= hi else (hue >= lo) | (hue <= hi)
    mask = in_hue & (sat >= s.min_saturation) & (val >= s.min_value)
    rows, cols = h // SCALE, w // SCALE
    cut = mask[: rows * SCALE, : cols * SCALE]
    blocks = cut.reshape(rows, SCALE, cols, SCALE).mean(axis=(1, 3))
    patch = _largest_patch(blocks > 0.5)
    if len(patch) * SCALE * SCALE < s.min_area_px * (w / 640) ** 2:
        return None
    bottom = max(r for r, _ in patch)
    near = [c for r, c in patch if r >= bottom - 1]
    u = (sum(near) / len(near) + 0.5) * SCALE
    v = (bottom + 1) * SCALE
    try:
        x, y = m.to_table(u, v, w)
        fx, fy = m.to_table(u, v - 10, w)  # a little further from the camera, on the table
    except ValueError:
        return None
    d = math.hypot(fx - x, fy - y) or 1.0
    half = s.height_cm / 2  # the cube is as deep as it is tall
    return x + (fx - x) / d * half, y + (fy - y) / d * half


def _largest_patch(on: np.ndarray) -> list[tuple[int, int]]:
    seen = np.zeros_like(on, dtype=bool)
    best: list[tuple[int, int]] = []
    rows, cols = on.shape
    for r0, c0 in zip(*np.nonzero(on), strict=True):
        if seen[r0, c0]:
            continue
        seen[r0, c0] = True
        patch, todo = [], deque([(int(r0), int(c0))])
        while todo:
            r, c = todo.popleft()
            patch.append((r, c))
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if 0 <= nr < rows and 0 <= nc < cols and on[nr, nc] and not seen[nr, nc]:
                    seen[nr, nc] = True
                    todo.append((nr, nc))
        if len(patch) > len(best):
            best = patch
    return best


def _tool(name: str, description: str, parameters: dict | None = None) -> dict:
    params = parameters or {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": params},
    }


class ArmDesk:
    """The assistant's arm tools. `robot`: the brain's robot tools; `enabled()`: place.yaml's
    switch, read each turn; `setup()`: config/handover.yaml."""

    def __init__(
        self,
        robot: RobotTools,
        enabled: Callable[[], bool] = lambda: config.assistant_moves_arm(),
        setup: Callable[[], HandOver] = load,
    ):
        self.robot, self.enabled, self.setup = robot, enabled, setup
        self.task: asyncio.Task | None = None
        self.doing = ""  # what the running move is doing, for "still busy"
        self.holding = False  # holding the cube out at the hand-over pose
        self.last = "nothing yet"  # how the last request ended

    def allowed(self, local: bool) -> bool:
        """Asked on the brain's own computer, switched on, and not a public venue."""
        return local and self.enabled() and not self.robot.venue.public

    def tools(self, local: bool) -> list[dict]:
        if not self.allowed(local):
            return []
        poses = sorted(self.robot.poses)
        pose = {
            "type": "object",
            "properties": {"pose": {"type": "string", "enum": poses}},
            "required": ["pose"],
        }
        return [
            _tool(
                MOVE,
                "Move the robot arm to one of its named poses, slowly, with the robot's safety "
                "checks: home (folded, where it rests), ready (the working pose, reaching "
                "forward), handover (held out to a person). Use it when someone asks you to move "
                "the arm to one of them. It starts the move and returns at once: say in a few "
                "words what the arm does now. STOP on any screen stops it.",
                pose,
            ),
            _tool(
                HAND,
                "Pick up the blue cube from the table and hold it out to the person (about half a "
                "minute). The stand camera finds the cube first; if it can't, the result says why: "
                "tell the person. Use it when someone asks you to hand them, give them or fetch "
                "the cube. Then tell them to say when to let go.",
            ),
            _tool(
                LET_GO,
                "Open the gripper so the person can take the cube the arm holds out. Use it when "
                "they say let go, open, release, or that they have it.",
            ),
        ]

    async def call(self, name: str, local: bool, arguments: str = "{}") -> tuple[str, list[dict]]:
        """Run one: (the result for the AI, events for the asking page)."""
        if not self.allowed(local) or name not in (MOVE, HAND, LET_GO):
            return f"Error: {name} isn't a tool you have here.", []
        if self.task and not self.task.done():
            return f"Error: the arm is still {self.doing}. Wait, or press STOP.", []
        try:
            self.robot._check_can_move(None)
        except Refused as e:
            return f"Error: the arm can't move now: {e}. Say so kindly.", []
        if name == LET_GO:
            return await self._let_go(), []
        if name == MOVE:
            try:
                pose = json.loads(arguments or "{}").get("pose")
            except (ValueError, AttributeError):
                pose = None
            if pose not in self.robot.poses:
                names = ", ".join(sorted(self.robot.poses))
                return f"Error: no pose {pose!r}; the poses: {names}", []
            self._start(f"moving to {pose}", self._to_pose(pose))
            return f"The arm is moving to {pose} now, slowly. Say so in a few words.", []
        return await self._hand_over(), []

    def _start(self, doing: str, coro) -> None:
        self.doing = doing

        async def run():
            try:
                await coro
            except Refused as e:
                self.last = f"refused: {e}"
                log.info("assistant arm: %s refused: %s", doing, e)
            except Exception as e:  # the arm stopped answering: logged, the chat goes on
                self.last = f"failed: {e}"
                log.warning("assistant arm: %s failed: %r", doing, e)

        self.task = asyncio.get_running_loop().create_task(run())

    async def _hand_over(self) -> str:
        try:
            s = self.setup()
        except NoSetup as e:
            return f"Error: there's no hand-over setup ({e})."
        if s.pose not in self.robot.poses:
            return f"Error: poses.yaml has no {s.pose!r} pose to hold the cube out at."
        m = table_map.load(s.camera)
        if m is None:
            return f"Error: {s.camera} has no table map, so the brain can't find the cube."
        try:
            shot = await self.robot.call("camera_snapshot", camera=s.camera, grid=False)
        except Refused as e:
            return f"Error: no picture from the stand camera: {e}."
        found = await asyncio.to_thread(find_cube, shot["image_jpeg"], m, s)
        if found is None:
            return (
                "Error: I can't see the blue cube in the stand camera's picture. Ask the person to "
                "put it on the table about 20 cm in front of the arm."
            )
        x, y = round(found[0], 1), round(found[1], 1)
        ready = self.robot.arm.read_joints() | self.robot.poses.get("ready", {})
        above = (x, y, s.height_cm + PICK_ABOVE_CM)
        q = self.robot._reaches(ready, above, DOWN_DEG)
        if q is None or self.robot._reaches(q, (x, y, s.height_cm / 2), DOWN_DEG) is None:
            return (
                f"Error: the cube is at about ({x:g}, {y:g}) cm from the arm's base, where the "
                "arm can't pick it up. Ask the person to put it about 20 cm straight in front of "
                "the arm."
            )
        self.holding = False
        self._start("bringing the cube", self._fetch(x, y, s))
        return (
            f"Found the cube about {math.hypot(x, y):.0f} cm from the arm. The arm is picking it "
            "up now, then holds it out (about half a minute). Tell the person to say when to let "
            "go."
        )

    async def _fetch(self, x: float, y: float, s: HandOver) -> None:
        if not await self._to_pose("ready"):
            return
        if not await self._go(x, y, s.height_cm + PICK_ABOVE_CM, DOWN_DEG):
            return
        r = await self.robot.call("pick_at", x_cm=x, y_cm=y, height_cm=s.height_cm)
        if r.get("result") != "holding":
            self.last = f"the pick ended: {r.get('result')} ({r.get('message', '')})"
            return
        if not await self._to_pose(s.pose):
            return
        self.holding = True
        self.last = "holding the cube out"

    async def _let_go(self) -> str:
        if not self.holding:
            return f"Error: the arm isn't holding the cube out (last: {self.last})."
        s = self.setup()
        r = await self.robot.call("gripper", open_pct=s.release_open_pct)
        if r.get("result") in ENDED:
            return f"Error: the gripper didn't open: {r.get('result')}."
        self.holding = False
        self.last = "let go of the cube"
        return "The gripper is open: the person can take the cube."

    async def _to_pose(self, name: str) -> bool:
        """go_to_pose again until it's there (at most max_joint_change_deg a call)."""
        for _ in range(12):
            r = await self.robot.call("go_to_pose", name=name)
            if r.get("result") in ENDED:
                self.last = f"{r['result']} on the way to {name}"
                return False
            if not any(c.startswith("went") for c in r.get("clipped", [])):
                self.last = f"at {name}"
                return True
        self.last = f"didn't get to {name}"
        return False

    async def _go(self, x: float, y: float, z: float, angle: float) -> bool:
        """move_to again until it's there (at most max_move_cm a call)."""
        for _ in range(8):
            r = await self.robot.call("move_to", x_cm=x, y_cm=y, z_cm=z, tool_angle_deg=angle)
            if r.get("result") in ENDED:
                self.last = f"{r['result']} on the way to the cube"
                return False
            p = r["gripper_point_cm"]
            if math.dist((p["x"], p["y"], p["z"]), (x, y, z)) < 0.6:
                return True
        self.last = "didn't get above the cube"
        return False


class Actions:
    """Several desks of tools for the hub's chat (visitor mode, the arm) as one: `tools(local)`
    lists them all, `call` runs the one with that name."""

    def __init__(self, *desks):
        self.desks = desks

    def tools(self, local: bool) -> list[dict]:
        return [t for d in self.desks for t in d.tools(local)]

    async def call(self, name: str, local: bool, arguments: str = "{}") -> tuple[str, list[dict]]:
        for d in self.desks:
            if name in {t["function"]["name"] for t in d.tools(local)}:
                return await d.call(name, local, arguments)
        return f"Error: {name} isn't a tool you have here.", []
