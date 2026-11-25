"""The hub's assistant moves the arm (preview 4, 2026-11-20): "Move the arm to home" and "Hand me
the cube".

Off unless place.yaml has `assistant_moves_arm: true` (Settings → Robots), never on a public venue,
and only for a question asked on the brain's own computer, like visitor mode (other screens may be
in a hallway). The AI
decides when to use the tools; it never chooses the motion:
- `move_arm_to_pose`: one of poses.yaml's named poses.
- `hand_me_the_cube`: the brain finds the blue cube in the stand camera's picture (a colour search
  here, then the table map: the chat model takes text only), picks it with `pick_at` and holds it
  out at the `handover` pose (config/handover.yaml). When the stand camera can't see it, or the
  arm may hide it, the arm folds to `home` and the stand camera looks again; then the wrist
  camera searches the table from above and steers the gripper over the cube (quick job 117).
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
from lab_os.tools.robot import DOWN_DEG, Refused, RobotTools
from lab_os.tools.table_map import TableMap

log = logging.getLogger(__name__)

MOVE, HAND, LET_GO = "move_arm_to_pose", "hand_me_the_cube", "let_go_of_the_cube"
FILE = "handover.yaml"
SCALE = 4  # the colour search looks at 4×4 pixel blocks (fast enough in plain Python)
ENDED = ("stopped", "disconnected")  # a move that ended so: nothing more moves
# A cube the stand camera sees this close to the gripper point (cm, on the table) may be partly
# hidden by the arm, which puts it in the wrong place: fold the arm away and look again.
HIDDEN_CM = 8.0
FINE_CM = 7.0  # then straight down this high over the cube, where that reaches (`wrist.target`)
# Where the wrist camera looks at the table (cm from the base, degrees of turn), nearest first.
# It looks from as high as it can with the gripper tilted (straight down reaches only ~10 cm up):
# at ~20 cm from the table it sees ~20 cm of it, so these cover the arm's reach.
WRIST_LOOKS = [(r, a) for r in (18.0, 28.0) for a in (0, 30, -30, 60, -60, 90, -90)]
LOOK_FROM = [(z, a) for z in (15.0, 12.0, 9.0) for a in (140.0, 150.0, 160.0, 170.0)] + [
    (FINE_CM, DOWN_DEG)
]
LOOK_ROOM_CM = 3.0  # a place to look from has this much reach around it, for the small moves
WRIST_PROBE_CM = 2.0  # the small moves that tell how the cube moves in the wrist picture
WRIST_STEPS = 6  # moves to bring the cube to its place in the picture, at most
WRIST_DONE = 0.03  # there: within this fraction of the picture
WRIST_MAX_STEP_CM = 8.0


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
    wrist_camera: str = ""  # "": no wrist search
    wrist_target: tuple[float, float] = (0.5, 0.5)


def load(file: Path | None = None) -> HandOver:
    file = file or config.shared_path(FILE)
    try:
        raw = yaml.safe_load(file.read_text()) or {}
        cube = raw["cube"]
        lo, hi = cube["hue_deg"]
        wrist = raw.get("wrist") or {}
        tx, ty = wrist.get("target", (0.5, 0.5))
        return HandOver(
            camera=str(raw["camera"]),
            height_cm=float(cube["height_cm"]),
            hue_deg=(float(lo), float(hi)),
            min_saturation=float(cube.get("min_saturation", 0.35)),
            min_value=float(cube.get("min_value", 0.2)),
            min_area_px=int(cube.get("min_area_px", 150)),
            pose=str(raw.get("pose", "handover")),
            release_open_pct=float(raw.get("release_open_pct", 100)),
            wrist_camera=str(wrist.get("camera", "")),
            wrist_target=(float(tx), float(ty)),
        )
    except FileNotFoundError:
        raise NoSetup(f"{file} doesn't exist") from None
    except (OSError, yaml.YAMLError, KeyError, TypeError, ValueError) as e:
        raise NoSetup(f"can't read {file}: {e}") from None


def _cube_patch(jpeg: bytes, s: HandOver) -> tuple[list[tuple[int, int]], int, int] | None:
    """The largest patch of the cube's colour in a picture, in SCALE × SCALE blocks (row, col),
    and the picture's width and height. None: no patch big enough."""
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
    return patch, w, h


def find_cube(jpeg: bytes, m: TableMap, s: HandOver) -> tuple[float, float] | None:
    """Where the cube stands on the table (x, y cm), from a picture of the camera with map `m`:
    the largest patch of the cube's colour, read where it touches the table (its near edge, the
    lowest point in the picture) and moved half its size further from the camera. None: no patch
    big enough."""
    found = _cube_patch(jpeg, s)
    if found is None:
        return None
    patch, w, _ = found
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


def find_cube_px(jpeg: bytes, s: HandOver) -> tuple[float, float] | None:
    """The middle of the cube in a picture (the wrist camera's), as fractions of its width and
    height. None: no patch of its colour big enough."""
    found = _cube_patch(jpeg, s)
    if found is None:
        return None
    patch, w, h = found
    u = (sum(c for _, c in patch) / len(patch) + 0.5) * SCALE
    v = (sum(r for r, _ in patch) / len(patch) + 0.5) * SCALE
    return u / w, v / h


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


class NoCube(Exception):
    """The cube can't be found or reached. The message is a sentence for the person. `seen`: the
    stand camera saw it (out of reach), not only that it didn't."""

    def __init__(self, message: str, seen: bool = False):
        super().__init__(message)
        self.seen = seen


def out_of_reach(x: float, y: float) -> NoCube:
    return NoCube(
        f"the cube is at about ({x:g}, {y:g}) cm from the arm's base, where the arm can't pick "
        "it up. Ask the person to put it nearer, about 20 cm in front of the arm.",
        seen=True,
    )


def _after_ready(robot: RobotTools) -> dict:
    """The joints the hand-over starts its pick from: the arm at `ready`."""
    return robot.arm.read_joints() | robot.poses.get("ready", {})


async def locate_cube(robot: RobotTools, s: HandOver) -> tuple[float, float]:
    """Where the blue cube stands (x, y cm), from the stand camera's picture and its table map,
    checked to be within the arm's reach for a pick (preview 4; also `find_cube` in a program,
    quick job 81). Nothing moves. Raises NoCube with the reason."""
    m = table_map.load(s.camera)
    if m is None:
        raise NoCube(f"{s.camera} has no table map, so the brain can't find the cube.")
    try:
        shot = await robot.call("camera_snapshot", camera=s.camera, grid=False)
    except Refused as e:
        raise NoCube(f"no picture from the stand camera: {e}.") from None
    found = await asyncio.to_thread(find_cube, shot["image_jpeg"], m, s)
    if found is None:
        raise NoCube(
            "I can't see the blue cube in the stand camera's picture. Ask the person to put it on "
            "the table about 20 cm in front of the arm."
        )
    x, y = round(found[0], 1), round(found[1], 1)
    if robot.pick_plan(x, y, s.height_cm, seed=_after_ready(robot)) is None:
        raise out_of_reach(x, y)
    return x, y


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
                "minute). The cameras find the cube first (the arm may move to look); if they "
                "can't, the result says why: "
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
        how = "the stand camera"
        try:
            x, y = await locate_cube(self.robot, s)
            look_again = self._near_gripper(x, y)  # the arm may hide a part of it
        except NoCube as e:
            if e.seen:
                return f"Error: {e}"
            look_again = True
        if look_again:
            # fold the arm away and look again, then search with the wrist camera (quick job
            # 117). The answer waits for it.
            self.doing = "looking for the cube"
            self.task = asyncio.get_running_loop().create_task(self._search(s))
            try:
                found = await self.task
            except (NoCube, Refused) as e:
                return f"Error: {e}"
            if found is None:
                return f"Error: the arm looked for the cube and stopped: {self.last}."
            x, y, how = found
        self.holding = False
        self._start("bringing the cube", self._fetch(x, y, s))
        return (
            f"Found the cube with {how}, about {math.hypot(x, y):.0f} cm from the arm. The arm is "
            "picking it up now, then holds it out (about half a minute). Tell the person to say "
            "when to let go."
        )

    def _near_gripper(self, x: float, y: float) -> bool:
        """The cube the stand camera saw is near the gripper point, which may hide part of it."""
        if self._at("home") or not self.robot.kin:
            return False
        (gx, gy, _), _ = self.robot.kin.fk(self.robot.arm.read_joints())
        return math.hypot(x - gx * 100, y - gy * 100) < HIDDEN_CM

    def _at(self, pose: str) -> bool:
        now = self.robot.arm.read_joints()
        want = {j: v for j, v in self.robot.poses.get(pose, {}).items() if j != "gripper"}
        return bool(want) and all(abs(now[j] - v) < 3 for j, v in want.items() if j in now)

    async def _search(self, s: HandOver) -> tuple[float, float, str] | None:
        """Fold the arm to home and look with the stand camera again; then the wrist camera.
        (x, y, which camera found it), or None when a move ended (self.last says why). Raises
        NoCube when neither camera finds it, or it is out of reach."""
        if not await self._to_pose("home"):
            return None
        try:
            x, y = await locate_cube(self.robot, s)
            return x, y, "the stand camera"
        except NoCube as e:
            if e.seen or not s.wrist_camera:
                raise
            stand = e
        found = await self._wrist_search(s)
        if found is None:
            if self.last.startswith(ENDED):
                return None
            raise NoCube(f"{stand} The wrist camera didn't find it either ({self.last}).")
        x, y = round(found[0], 1), round(found[1], 1)
        if self.robot.pick_plan(x, y, s.height_cm, seed=_after_ready(self.robot)) is None:
            raise out_of_reach(x, y)
        return x, y, "the wrist camera"

    async def _wrist_look(self, s: HandOver) -> tuple[float, float] | None:
        try:
            shot = await self.robot.call("camera_snapshot", camera=s.wrist_camera, grid=False)
        except Refused as e:
            self.last = f"no picture from the wrist camera: {e}"
            raise _NoPicture from None
        return await asyncio.to_thread(find_cube_px, shot["image_jpeg"], s)

    async def _wrist_search(self, s: HandOver) -> tuple[float, float] | None:
        """Look at the table with the wrist camera from WRIST_LOOKS until it sees the cube, then
        find it by look, move, look (the way a person found it by hand, GOTCHAS 2026-11-17),
        learning from each move how the cube moves in the picture, so it needs no camera
        calibration: (1) tilted, the cube to the picture's middle, then along the jaws' line
        down to the table; (2) straight down over that point, the cube to `wrist.target`. The
        cube's table point, or None (self.last says why)."""
        h = s.height_cm
        try:
            for r, a in WRIST_LOOKS:
                rad = math.radians(a)
                look = self._look_from(r * math.cos(rad), r * math.sin(rad), h)
                if look is None:
                    continue
                z, angle, g = look
                # from ready each time: a line from one look to the next may leave the reach
                if not await self._to_pose("ready"):
                    return None
                try:
                    if not await self._go(*g, z, angle, "to look"):
                        return None
                except Refused:  # nothing moved
                    continue
                p = await self._wrist_look(s)
                if p is None:
                    log.info("assistant arm: no cube from (%.1f, %.1f, %g) cm, %g°", *g, z, angle)
                    continue
                log.info(
                    "assistant arm: the wrist camera sees the cube at (%.2f, %.2f) of its picture "
                    "from (%.1f, %.1f, %g) cm, tool angle %g°",
                    *p,
                    *g,
                    z,
                    angle,
                )
                g = await self._steer(s, g, z, angle, p, (0.5, 0.5))
                if g is None:
                    if self.last.startswith(ENDED):  # STOP: nothing more moves
                        return None
                    log.info("assistant arm: wrist search: %s; the next look", self.last)
                    continue
                est = _on_table(g, z, angle, h)
                log.info("assistant arm: the jaws' line meets the table at (%.1f, %.1f) cm", *est)
                ready = _after_ready(self.robot)
                if self.robot._reaches(ready, (*est, FINE_CM), DOWN_DEG) is None:
                    return est
                if not await self._go(*est, FINE_CM, DOWN_DEG, "over the cube"):
                    return None
                p = await self._wrist_look(s)
                if p is None:
                    return est
                fine = await self._steer(s, est, FINE_CM, DOWN_DEG, p, s.wrist_target)
                if fine is None and self.last.startswith(ENDED):  # STOP: nothing more moves
                    return None
                return fine or est
            self.last = "the cube isn't in any of its pictures"
            return None
        except _NoPicture:
            return None

    def _look_from(self, x: float, y: float, h: float) -> tuple[float, float, tuple] | None:
        """Where the gripper point goes so that the jaws' line meets the table at (x, y): (its
        height, the tool angle, its (x, y)), the highest and steepest of LOOK_FROM that reaches
        with LOOK_ROOM_CM around it."""
        seed = _after_ready(self.robot)
        r, heading = math.hypot(x, y), math.atan2(y, x)
        c, sn = math.cos(heading), math.sin(heading)
        room = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]
        for z, angle in LOOK_FROM:
            gr = r - (z - h / 2) * math.tan(math.radians(DOWN_DEG - angle))
            if gr <= 0:
                continue
            ok = all(
                self.robot._reaches(
                    seed,
                    (
                        gr * c + LOOK_ROOM_CM * (i * c - j * sn),
                        gr * sn + LOOK_ROOM_CM * (i * sn + j * c),
                        z,
                    ),
                    angle,
                )
                is not None
                for i, j in room
            )
            if ok:
                return z, angle, (gr * c, gr * sn)
        return None

    async def _steer(
        self, s: HandOver, g: tuple, z: float, angle: float, p: tuple, target: tuple
    ) -> tuple[float, float] | None:
        """Bring the cube seen at `p` (picture fractions), the gripper point at (g, z), to
        `target` in the picture, moving the gripper point over the table: two small moves tell
        how the cube moves in the picture (a 2×2 Jacobian), and Broyden's update refines it on
        each step. The gripper point's (x, y) there (or where it would be, when that is just
        out of reach), or None (self.last says why)."""
        cols, q, at = [], None, g
        for ux, uy in ((1.0, 0.0), (0.0, 1.0)):
            for sign in (1.0, -1.0):  # the other way when the cube leaves the picture
                d = sign * WRIST_PROBE_CM
                at = (g[0] + ux * d, g[1] + uy * d)
                try:
                    if not await self._go(*at, z, angle, "to look"):
                        return None
                except Refused:  # nothing moved
                    continue
                q = await self._wrist_look(s)
                if q is not None:
                    cols.append(((q[0] - p[0]) / d, (q[1] - p[1]) / d))
                    break
            else:
                self.last = "the cube went out of the wrist camera's picture"
                return None
        jac = np.array(cols).T  # picture fractions per cm: column 0 for x, column 1 for y
        here, p, want = np.array(at), np.array(q), np.array(target)
        for _ in range(WRIST_STEPS):
            if np.hypot(*(want - p)) < WRIST_DONE:
                return round(float(here[0]), 1), round(float(here[1]), 1)
            try:
                step = np.linalg.solve(jac, want - p)
            except np.linalg.LinAlgError:
                break
            n = float(np.hypot(*step))
            if n > WRIST_MAX_STEP_CM:
                step *= WRIST_MAX_STEP_CM / n
            nxt = here + step
            try:
                if not await self._go(float(nxt[0]), float(nxt[1]), z, angle, "to look"):
                    return None
            except Refused:
                # out of reach (nothing moved): from there the camera would see the cube at
                # `target`, so its line still tells where the cube is
                if n > WRIST_MAX_STEP_CM:
                    self.last = "the cube is where the wrist camera can't look at it"
                    return None
                log.info("assistant arm: wrist steer: (%.1f, %.1f) cm is out of reach", *nxt)
                return round(float(nxt[0]), 1), round(float(nxt[1]), 1)
            q = await self._wrist_look(s)
            if q is None:
                self.last = "the cube went out of the wrist camera's picture"
                return None
            q = np.array(q)
            log.info(
                "assistant arm: wrist steer to (%.1f, %.1f) cm: the cube at (%.2f, %.2f)",
                *nxt,
                *q,
            )
            jac += np.outer((q - p) - jac @ step, step) / float(step @ step)
            here, p = nxt, q
        if np.hypot(*(want - p)) < WRIST_DONE:
            return round(float(here[0]), 1), round(float(here[1]), 1)
        self.last = "the wrist camera's picture didn't settle on the cube"
        return None

    async def _fetch(self, x: float, y: float, s: HandOver) -> None:
        if not await self._to_pose("ready"):
            return
        plan = self.robot.pick_plan(x, y, s.height_cm)
        if plan is None:
            self.last = f"the cube at ({x:g}, {y:g}) cm is out of reach from ready"
            return
        angle, above, _ = plan
        if not await self._go(*above, angle):
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

    async def _go(self, x: float, y: float, z: float, angle: float, why: str = "") -> bool:
        """move_to again until it's there (at most max_move_cm a call)."""
        for _ in range(8):
            r = await self.robot.call("move_to", x_cm=x, y_cm=y, z_cm=z, tool_angle_deg=angle)
            if r.get("result") in ENDED:
                self.last = f"{r['result']} on the way {why or 'to the cube'}"
                return False
            p = r["gripper_point_cm"]
            if math.dist((p["x"], p["y"], p["z"]), (x, y, z)) < 0.6:
                return True
        self.last = f"didn't get {why or 'above the cube'}"
        return False


def _on_table(g: tuple, z: float, angle: float, h: float) -> tuple[float, float]:
    """Where the jaws' line from the gripper point (g, z cm) at tool angle `angle` meets the
    cube's middle height `h` / 2 (the line turns with the arm: it points away from the base)."""
    out = (z - h / 2) * math.tan(math.radians(DOWN_DEG - angle))
    heading = math.atan2(g[1], g[0])
    return round(g[0] + out * math.cos(heading), 1), round(g[1] + out * math.sin(heading), 1)


class _NoPicture(Exception):
    """The wrist camera gave no picture (self.last says why)."""


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
