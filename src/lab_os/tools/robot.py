"""The robot tools for AI (docs/plan/current-focus.md step 2): read the arm, move it, stop it.

Plain logic with no MCP in it; lab_os.tools.mcp_server offers these as MCP tools. Every move runs
through the teleop loop (`Motion`), so it takes the same path to the arm as teleop: the driver's
limits, the venue's speed scale, a capped speed per tick. On top of that the brain clips and
refuses; it never trusts the numbers it's given:

- **refused** (nothing moves, the message says why): the venue doesn't allow motion; the arm is
  disconnected (its USB was unplugged; the brain reconnects when it's back); teleop has control;
  another move is running; lab-os is shutting down (quick job 44); an unknown arm, joint or
  pose; a target below the floor (`min_z_cm`) or out of reach; a path that needs a sudden big
  joint swing.
- **clipped** (it moves, and says so): targets past the soft limits (3° inside the real ones, like
  teleop); more than `max_joint_change_deg` per call (all joints go the same fraction of the way;
  the gripper is exempt); more than `max_move_cm` per call for move_to.
- **pick_at**: one call for a whole pick (open, above, straight down, close, lift), built from
  the same moves, the gripper pointing down or tilted up to 60° where that reaches (quick job
  117); it checks every point first and says each step on the AI Control page before it moves
  (decision 2026-11-16, docs/dev/existing-work-teleop-ai.md).
- **stop**: always allowed. STOP on any page also ends a move ("stopped").
- **checked**: after a move, the motors' real position is compared with the target; further than
  `SHORT_CM` / `SHORT_DEG` away = "stopped_short" with how far and which joints, never "arrived".
  `SHORT_DEG` allows for so101-white's steady sag (2.3-3.5°, mostly the elbow), so a pose that
  looks right says "arrived" (quick job 77); `SHORT_CM` is unchanged, so move_to still says when the
  gripper point is off.

Positions: cm from the arm's base (origin on the table under the base's turning axis), x forward
(where the arm faces at shoulder_pan 0), y to the arm's left, z up from the table: an arm standing
on a plate has `table_z_cm` in devices.yaml (so101-white: -1.6), and every height here (move_to,
pick_at, the floor, arm_status, pose_view) is measured from the table (quick job 28). Tool angle:
the gripper's tilt in degrees, 0 = pointing up, 90 = forward, 180 = straight down.
"""

import asyncio
import logging
import math
import time
from dataclasses import dataclass, fields, replace
from pathlib import Path

import yaml

from lab_os import config
from lab_os.kinematics import IK_JOINTS, kinematics_for, on_table, solve_ik
from lab_os.robots.base import JointLimit
from lab_os.teleop.loop import RAMP_S, Motion, TeleopLoop
from lab_os.teleop.mapping import soft_bounds
from lab_os.tools import pose_view as pv
from lab_os.tools import table_map, tic_tac_toe
from lab_os.tools.calllog import CallLog
from lab_os.venues import Venue

log = logging.getLogger(__name__)

LIMIT_MARGIN_DEG = 3.0  # moves stay this far inside each joint limit (same as teleop)
LINE_STEP_CM = 1.0  # move_to: one IK waypoint per cm, so the gripper moves in a straight line
REACH_TOLERANCE_CM = 0.5  # "reached" = the IK lands this close...
ANGLE_TOLERANCE_DEG = 5.0  # ...with the tool angle this close
SUBSTEP_DEG = 5.0  # near full stretch 1 cm can need ~20° of joint motion: split such steps so
# the gripper stays on the line between waypoints
MAX_WAYPOINT_JUMP_DEG = 30.0  # more than this for 1 cm of path = a flip of the arm: refuse
HOLD_S = 0.5  # after the last waypoint, keep sending it this long so trailing servos catch up
SETTLE_S = 0.2  # after the hold and the freeze, before reading where the arm really is
SHORT_CM = 0.5  # the gripper point ended further than this from the target: "stopped_short"
# a joint ended further than this from its target: "stopped_short". so101-white's joints sag
# 2.3-3.5° (elbow_flex, once shoulder_lift; GOTCHAS 2026-11-12): within this, a pose has arrived
# (quick job 77; 2.0 before, so nearly every move warned)
SHORT_DEG = 4.0
PICK_ABOVE_CM = 6.0  # pick_at: the hover point is this far above the object's top
PICK_OFF_CM = 1.5  # pick_at: a step that ends further off than this ends the pick
PICK_HEIGHT_CM = (0.5, 8.0)  # objects pick_at takes (cm tall)
# pick_at closes the jaws this far below the object's top, but never below the floor: as deep as
# the jaws can go without the gripper's body touching the top (it is ~10 cm from the jaw tips on
# the SO-101's model; 4 cm keeps clear). Half the height (before quick job 51) held a 3 cm cube
# with the jaw tips only, the elbow's ~3° sag lifting them more (lab check 3b.5).
PICK_JAW_DEPTH_CM = 4.0
# Closed on nothing, the real so101-white read 7.8 % open (GOTCHAS 2026-11-12): more than this
# after the lift = holding something. A guess between that and a 2.5 cm cube; lab check part 3.
PICK_HELD_PCT = 15.0
# On the SO-101 the gripper point (the model's gripper_frame_link) is on the fixed jaw's inner
# face, not between the open jaws: aimed at an object's middle, the fixed jaw came down on its
# top (quick job 106). pick_at puts the gripper point this far from the object's middle, away
# from the moving jaw, so the fixed jaw comes down beside the object (a 3.2 cm Duplo piece: 0.4
# cm clear) and the moving jaw pushes it against the fixed one.
PICK_JAW_SIDE_CM = 2.0
# The direction the moving jaw opens, in the gripper's own frame (the wrist_roll joint's frame
# of the SO-101 model; from the jaws' meshes, models/so101).
SO101_OPEN_DIR = (1.0, 0.0, 0.0)
DOWN_DEG = 180.0  # tool angle: pointing straight down
# pick_at's tool angles, steepest first (quick job 117). Straight down reaches only ~13-24 cm from
# so101-white's base, so a cube 25 cm out or to the side was "out of reach"; tilted up to 60° it
# reaches ~4-38 cm. 120° at most: the gripper's body (~10 cm from the jaw tips) stays 5 cm above
# them, clear of the object's top at PICK_JAW_DEPTH_CM.
PICK_ANGLES_DEG = (180.0, 170.0, 160.0, 150.0, 140.0, 130.0, 120.0)
SHORT_PCT = 5.0  # the gripper's opening ended further than this from the one asked for
FLOOR_SAMPLES = 20  # points checked along a joint-space move


class Refused(Exception):
    """A request the brain won't carry out. The message tells the AI why and what to do."""


@dataclass(frozen=True)
class AiLimits:
    """Per-call limits, from the venue's `ai_tools` section (config/venues/)."""

    max_joint_change_deg: float = 30.0
    max_move_cm: float = 10.0
    min_z_cm: float = 1.0
    deg_per_s: float = 60.0  # the fastest joint's speed at speed scale 1 (venue scale on top)

    @classmethod
    def from_venue(cls, venue: Venue) -> "AiLimits":
        known = {f.name for f in fields(cls)}
        for key in set(venue.ai_tools) - known:
            log.warning("venue %s: unknown ai_tools setting %r (ignored)", venue.name, key)
        limits = cls(**{k: float(v) for k, v in venue.ai_tools.items() if k in known})
        if not venue.per_move_limit:  # switched off in the venue (Settings → Robots)
            limits = replace(limits, max_joint_change_deg=math.inf, max_move_cm=math.inf)
        if not venue.floor:
            limits = replace(limits, min_z_cm=-math.inf)
        return limits

    def per_call(self) -> dict:
        """For arm_status: the numbers, or "off" for a limit that's switched off."""
        values = {
            "max_joint_change_deg": self.max_joint_change_deg,
            "max_move_cm": self.max_move_cm,
            "min_z_cm": self.min_z_cm,
        }
        return {k: v if math.isfinite(v) else "off" for k, v in values.items()}


def load_poses(path: Path | None = None) -> dict[str, dict[str, dict[str, float]]]:
    """Named poses per arm model (poses.yaml: the place's own, else config/poses.yaml)."""
    raw = yaml.safe_load((path or config.shared_path("poses.yaml")).read_text()) or {}
    return {
        model: {name: {j: float(v) for j, v in joints.items()} for name, joints in poses.items()}
        for model, poses in raw.items()
    }


def load_gestures(path: Path | None = None) -> dict[str, dict[str, dict]]:
    """Fixed moves per arm model (gestures.yaml: the place's own, else config/gestures.yaml):
    {model: {name: {"from": pose, "steps": [{joint: degrees relative to the pose}]}}}."""
    path = path or config.shared_path("gestures.yaml")
    raw = (yaml.safe_load(path.read_text()) if path.is_file() else None) or {}
    return {
        model: {
            name: {
                "from": str(g["from"]),
                "steps": [{j: float(v) for j, v in step.items()} for step in g.get("steps") or []],
            }
            for name, g in gestures.items()
        }
        for model, gestures in raw.items()
    }


def _angle_diff(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def _check_marks(marks: list) -> list[dict]:
    """pose_view's marks: points (cm) to draw, e.g. where the AI thinks the cube is."""
    if not isinstance(marks, list) or len(marks) > pv.MAX_MARKS:
        raise Refused(f"marks must be a list of at most {pv.MAX_MARKS} points")
    out = []
    for m in marks:
        if not isinstance(m, dict) or not {"x_cm", "y_cm", "z_cm"} <= set(m):
            raise Refused(
                'each mark needs x_cm, y_cm and z_cm, e.g. {"x_cm": 15, "y_cm": 5, '
                '"z_cm": 1.5, "label": "cube", "size_cm": 3}'
            )
        _finite(**{k: m[k] for k in ("x_cm", "y_cm", "z_cm")})
        size = m.get("size_cm") or 0
        _finite(size_cm=size)
        if not 0 <= size <= 30 or any(abs(m[k]) > 200 for k in ("x_cm", "y_cm", "z_cm")):
            raise Refused("marks must be within 200 cm of the base, size_cm 0–30")
        out.append(
            {k: m[k] for k in ("x_cm", "y_cm", "z_cm")}
            | {"label": str(m.get("label") or "")[:30], "size_cm": float(size)}
        )
    return out


def _finite(**values: float) -> None:
    for name, v in values.items():
        if not isinstance(v, int | float) or not math.isfinite(v):
            raise Refused(f"{name} must be a number, got {v!r}")


class RobotTools:
    """The tools for one arm, driven through `loop`. `control` is the teleop server's CONTROL dict
    (`{"ws": the driving page or None}`), so the tools know when teleop has the arm."""

    def __init__(
        self,
        loop: TeleopLoop,
        venue: Venue,
        control: dict,
        poses: dict | None = None,
        calls: CallLog | None = None,
        table_z_cm: float | None = None,
        gestures: dict | None = None,
    ):
        self.loop = loop
        self.venue = venue
        self.limits = AiLimits.from_venue(venue)
        self.control = control
        self._poses, self._gestures = poses, gestures
        self.use_arm(table_z_cm)
        self.calls = calls or CallLog()

    def use_arm(self, table_z_cm: float | None = None) -> None:
        """Take the loop's arm: its height above the table, kinematics, poses and gestures. At
        the start, and when the brain takes an arm plugged in after the start (quick job 73)."""
        self.arm = self.loop.arm
        if table_z_cm is None:  # the arm's setting in devices.yaml (0 for the software arms)
            from lab_os.devices import table_z_cm as setting

            table_z_cm = setting(self.arm.name)
        self.table_z_cm = table_z_cm
        self.kin = on_table(kinematics_for(self.arm.model), table_z_cm)
        poses = load_poses() if self._poses is None else self._poses
        gestures = load_gestures() if self._gestures is None else self._gestures
        self.poses = poses.get(self.arm.model, {})
        self.gestures = gestures.get(self.arm.model, {})
        self.last_target: tuple[tuple[float, float, float], float] | None = None  # move_to's

    # ---------- reading ----------

    def who_has_control(self) -> str:
        if self.loop.motion_active:
            return "ai"
        return "teleop" if self.control.get("ws") is not None else "free"

    def _gripper_range(self) -> tuple[float, float]:
        lim = self.arm.limits["gripper"]
        return lim.low + LIMIT_MARGIN_DEG, lim.high - LIMIT_MARGIN_DEG

    def _gripper_pct(self, deg: float) -> float:
        lo, hi = self._gripper_range()
        return round((deg - lo) / (hi - lo) * 100, 1)

    def _lowest_z_cm(self, joints: dict[str, float]) -> float:
        """The lowest point of the arm we know of (joint frames and the gripper point)."""
        frames = getattr(self.kin, "frames", None)
        if frames:
            return min(p[2] for p, _ in frames(joints).values()) * 100
        return self.kin.fk(joints)[0][2] * 100

    def _measured(self) -> dict[str, float]:
        """Where the motors really are. Drivers report where they were told to be while driving
        (`read_joints`), so after a move ask the motors (`read_measured`) where there's a way."""
        read = getattr(self.arm, "read_measured", None)
        if read is not None:
            try:
                return read()
            except Exception as e:  # a dropped packet: the driver's own idea is next best
                log.warning("%s: measured read failed (%s)", self.arm.name, e)
        return self.arm.read_joints()

    def _where(self, joints: dict[str, float] | None = None) -> dict:
        joints = self.arm.read_joints() if joints is None else joints
        out = {"joints_deg": {j: round(v, 1) for j, v in joints.items()}}
        if "gripper" in joints:
            out["gripper_open_pct"] = self._gripper_pct(joints["gripper"])
        if self.kin:
            (x, y, z), angle = self.kin.fk(joints)
            out["gripper_point_cm"] = {
                "x": round(x * 100, 1),
                "y": round(y * 100, 1),
                "z": round(z * 100, 1),
            }
            out["tool_angle_deg"] = round(angle, 1)
        return out

    def position(self) -> dict:
        """Joints, gripper opening and gripper point (cm) right now, for the hub's pages."""
        if self._disconnected():
            raise RuntimeError(self._disconnected())
        return self._where()

    def _check_arm(self, arm: str | None) -> None:
        if arm not in (None, "", self.arm.name):
            raise Refused(
                f"no arm called {arm!r} is connected; the connected arm is {self.arm.name!r}"
            )

    def _disconnected(self) -> str | None:
        """Why the arm can't be reached (its USB was unplugged), or None."""
        if self.loop.arm_connected:
            return None
        why = self.loop.arm_problem or "its USB was unplugged"
        return f"{self.arm.name} is disconnected ({why}); the brain reconnects when it's back"

    async def arm_status(self, arm: str | None = None) -> dict:
        self._check_arm(arm)
        status = {"arm": self.arm.name, "model": self.arm.model}
        if self._disconnected():
            return status | {"connected": False, "problem": self._disconnected()}
        try:
            where = self._where()
        except Exception as e:  # e.g. the arm stopped answering
            return status | {"connected": False, "problem": str(e)}
        return (
            status
            | {"connected": True}
            | where
            | {
                "limits_deg": {
                    j: [round(lim.low, 1), round(lim.high, 1)] for j, lim in self.arm.limits.items()
                },
                "control": self.who_has_control(),
                "held_still": self.loop.frozen,
                "motion_allowed": self.venue.motion_allowed,
                "speed_scale": self.loop.speed_scale,
                "per_call": self.limits.per_call(),
                "frame": "cm from the arm's base: x forward, y left, z up from the table "
                "(0 = the table" + self._plate() + "); "
                "tool angle 0 = up, 90 = forward, 180 = straight down",
                "table_z_cm": self.table_z_cm,
            }
        )

    def _plate(self) -> str:
        if not self.table_z_cm:
            return ""
        return f"; this arm's base stands {-self.table_z_cm:g} cm above it"

    async def list_poses(self, arm: str | None = None) -> dict:
        self._check_arm(arm)
        return {"arm": self.arm.name, "poses": self.poses}

    async def pose_view(self, marks: list[dict] | None = None, arm: str | None = None) -> dict:
        """A picture of the arm's 3D model where the motors are now (side + top, grid in cm),
        with the last move_to target and the caller's `marks`. The PNG is under "image_png"."""
        self._check_arm(arm)
        if self.arm.model not in pv.URDFS or not self.kin:
            raise Refused(f"no 3D model to draw for the {self.arm.model} model")
        marks = _check_marks(marks or [])
        joints = self._measured()
        where = self._where(joints)
        p = where["gripper_point_cm"]
        png = await asyncio.to_thread(  # ~0.2 s (~1 s the first time): keep the loop running
            pv.render,
            self.arm.model,
            joints,
            (p["x"], p["y"], p["z"]),
            where["tool_angle_deg"],
            self.last_target,
            marks,
            self.table_z_cm,
        )
        out = {"arm": self.arm.name} | where
        if self.last_target:
            (x, y, z), a = self.last_target
            out["last_target_cm"] = {"x": round(x, 1), "y": round(y, 1), "z": round(z, 1)}
        return out | {
            "views": "left: side, in the arm's plane (across = reach from the base axis, up = "
            "height); right: top, from above with forward up and the arm's left on the left. "
            "Red dot = gripper point, magenta x = last move_to target, blue = your marks. Drawn "
            "from the joint readings, not a camera: objects other than your marks aren't in it.",
            "image_png": png,
        }

    async def camera_snapshot(
        self, camera: str, width_px: int = 640, grid: bool = True, board: bool = False
    ) -> dict:
        """One picture from a camera in devices.yaml (read tier): opens it, grabs a frame, closes
        it. A camera another program has open is refused. The JPEG is under "image_jpeg". A
        camera with a table map (`lab-os table-map`) gets the table's cm grid drawn on it unless
        `grid` is false. `board`: the tic-tac-toe board's cells and start spots drawn on it too
        (config/games/tic-tac-toe.yaml), with their positions and the steps under "board"; those
        come even without a picture (the fake arm has no camera), with "picture" saying why."""
        from lab_os import devices

        width_px = max(160, min(int(width_px), 1280))
        m = table_map.load(camera)
        game = None
        if board:
            try:
                game = tic_tac_toe.load()
            except tic_tac_toe.NoGame as e:
                raise Refused(str(e)) from e
        from lab_os.camera_feed import FEEDS

        try:
            # open for a page under any of its names: its newest frame (quick jobs 63 and 116)
            live = FEEDS.frame(camera)
            if live is not None:
                jpeg = await asyncio.to_thread(_frame_jpeg, live, width_px)
            else:
                path = devices.camera_device(camera)  # nobody else has it (one program per camera)
                jpeg = await asyncio.to_thread(_grab_jpeg, path, width_px, camera)
        except (KeyError, LookupError, devices.InUse, devices.PortNotAllowed, Refused) as e:
            if game is None and isinstance(e, Refused):
                raise
            if game is None:
                raise Refused(str(e)) from e
            return {
                "camera": camera,
                "picture": f"none ({e}): ask the person where the pieces are",
                "board": game.summary(),
            }
        out = {"camera": camera, "width_px": width_px, "image_jpeg": jpeg}
        if m is not None and grid:
            out["image_jpeg"] = await asyncio.to_thread(table_map.draw_grid, jpeg, m)
            out["table_grid"] = table_map.describe(m)
        elif m is None:
            out["table_grid"] = "none: this camera has no table map, so no cm grid"
        if game is not None:
            if m is not None:
                out["image_jpeg"] = await asyncio.to_thread(
                    tic_tac_toe.draw, out["image_jpeg"], m, game
                )
                read = tic_tac_toe.describe(game)
            else:
                read = f"not drawn: {camera} has no table map (use {game.camera})"
            out["board"] = {"how_to_read": read} | game.summary()
        return out

    async def table_point(self, camera: str, x_px: float, y_px: float, width_px: int = 640) -> dict:
        """A pixel of a `camera_snapshot` picture `width_px` wide → where that is on the table, in
        cm from the middle of the arm's base (read tier). Needs the camera's table map."""
        m = table_map.load(camera)
        if m is None:
            raise Refused(f"{camera} has no table map (lab-os table-map {camera})")
        _finite(x_px=x_px, y_px=y_px, width_px=width_px)
        try:
            x, y = m.to_table(float(x_px), float(y_px), int(width_px))
        except ValueError as e:
            raise Refused(str(e)) from e
        return {
            "camera": camera,
            "table_cm": {"x": round(x, 1), "y": round(y, 1)},
            "note": "on the table's plane: give the pixel where the object touches the table",
        }

    # ---------- checks shared by every move ----------

    def _check_can_move(self, arm: str | None) -> None:
        self._check_arm(arm)
        if self.loop.shutting_down:  # quick job 44: from the shutdown on, nothing moves
            raise Refused(f"{self.loop.shutting_down}: nothing moves any more")
        if not self.venue.motion_allowed:
            raise Refused(
                f"the venue {self.venue.name!r} doesn't allow motion (motion_allowed: false)"
            )
        if self._disconnected():
            raise Refused(self._disconnected())
        who = self.who_has_control()
        if who == "teleop":
            raise Refused(
                "teleop has control: a teleop page is driving the arm. Ask the user; the move "
                "tools work again once that page lets go."
            )
        if who == "ai":
            raise Refused("another move is still running; wait for it to finish")

    def _clip_to_limits(self, current: dict, target: dict, notes: list[str]) -> dict:
        bounds = soft_bounds(self.arm.limits, current, LIMIT_MARGIN_DEG)
        out = {}
        for j, v in target.items():
            lo, hi = bounds[j]
            out[j] = min(max(v, lo), hi)
            if abs(out[j] - v) > 1e-6:
                notes.append(f"{j}: {v:.1f}° → {out[j]:.1f}° (joint limit)")
        return out

    def _limit_change(self, current: dict, target: dict, notes: list[str]) -> dict:
        """At most max_joint_change_deg per call (gripper exempt): all joints the same fraction."""
        far = max((abs(v - current[j]) for j, v in target.items() if j != "gripper"), default=0.0)
        cap = self.limits.max_joint_change_deg
        if far <= cap:
            return target
        k = cap / far
        notes.append(
            f"went {k:.0%} of the way: at most {cap:g}° per joint per call; call again to continue"
        )
        return {j: current[j] + (v - current[j]) * k for j, v in target.items()}

    def _check_floor(self, start: dict, points: list[dict]) -> None:
        """Nothing may go below min_z_cm, unless it's already lower (then: never lower still)."""
        if not self.kin:
            return
        floor = min(self.limits.min_z_cm, self._lowest_z_cm(start) - 0.1)
        for q in points:
            z = self._lowest_z_cm(q)
            if z < floor:
                raise Refused(
                    f"that would take the arm to {z:.1f} cm above the table, below the "
                    f"{self.limits.min_z_cm:g} cm floor; nothing moved"
                )

    def _line(self, start: dict, target: dict) -> list[dict]:
        return [
            start | {j: start[j] + (v - start[j]) * i / FLOOR_SAMPLES for j, v in target.items()}
            for i in range(1, FLOOR_SAMPLES + 1)
        ]

    async def _run(
        self,
        path: list[dict],
        notes: list[str],
        aim: tuple[tuple, float] | None = None,
        smooth: bool = False,
    ) -> dict:
        """Follow `path`, then report where the arm really ended up. `aim` (move_to only) is
        the gripper point (cm) and tool angle the move was aiming for. `smooth`: start slowly,
        speed up and slow down at the end (moves to a named pose, quick job 118)."""
        motion = Motion(path=path, deg_per_s=self.limits.deg_per_s, hold_s=HOLD_S, smooth=smooth)
        speed = self.limits.deg_per_s * max(self.loop.speed_scale, 0.01)
        self.loop.start_motion(motion)
        ramps = RAMP_S if smooth else 0.0  # a smooth move takes RAMP_S longer
        try:
            await asyncio.wait_for(motion.done.wait(), motion.travel_deg / speed + ramps + 5.0)
        except TimeoutError:
            self.loop.stop()
            notes.append("took far longer than expected, so it was stopped")
        except asyncio.CancelledError:
            self.loop.stop()  # the AI tool went away mid-move: freeze (dead-man)
            raise
        if motion.result == "disconnected":
            notes.append(
                "the arm was disconnected during the move (its USB was unplugged). Don't move "
                "again until the user says so."
            )
            return {"result": "disconnected", "clipped": notes, "problem": self._disconnected()}
        if motion.result != "arrived":
            notes.append(
                f"stopped before arriving: {self.loop.shutting_down}. Nothing moves now."
                if self.loop.shutting_down
                else "stopped before arriving (STOP was pressed, or the arm was frozen). Don't "
                "move again until the user says so."
            )
            return {"result": "stopped", "clipped": notes} | self._where()
        await asyncio.sleep(SETTLE_S)
        joints = self._measured()
        where = self._where(joints)
        off = self._off_target(path[-1], joints, where, aim)
        result = "stopped_short" if off.pop("short") else "arrived"
        return {"result": result, "clipped": notes} | off | where

    def _off_target(self, target: dict, joints: dict, where: dict, aim: tuple | None) -> dict:
        """Compare where the arm ended with where it was sent. Never a plain "arrived" when it
        isn't there: a blind AI can't tell otherwise (GOTCHAS 2026-11-10)."""
        out: dict = {"short": False}
        said: list[str] = []
        joint_short = {
            j: round(v - joints[j], 1)
            for j, v in target.items()
            if j != "gripper" and j in joints and abs(v - joints[j]) > SHORT_DEG
        }
        if aim is not None and "gripper_point_cm" in where:
            (gx, gy, gz), angle = aim
            p = where["gripper_point_cm"]
            off_cm = math.dist((gx, gy, gz), (p["x"], p["y"], p["z"]))
            out |= {
                "target_cm": {"x": round(gx, 1), "y": round(gy, 1), "z": round(gz, 1)},
                "target_tool_angle_deg": round(angle, 1),
                "off_by_cm": round(off_cm, 1),
            }
            if off_cm > SHORT_CM:
                out["short"] = True
                said.append(
                    f"stopped {off_cm:.1f} cm from the target ({gx:.1f}, {gy:.1f}, {gz:.1f}) cm: "
                    f"the gripper point is at ({p['x']:.1f}, {p['y']:.1f}, {p['z']:.1f}) cm, "
                    f"tool angle {where['tool_angle_deg']:.0f}° (asked {angle:.0f}°)"
                )
        if joint_short:
            out["short"] = True
            out["joints_short_deg"] = joint_short
            said.append(
                "short of the command: "
                + ", ".join(f"{j} by {abs(d):.1f}°" for j, d in joint_short.items())
            )
        if "gripper" in target and "gripper" in joints:
            want, got = self._gripper_pct(target["gripper"]), self._gripper_pct(joints["gripper"])
            if abs(want - got) > SHORT_PCT:
                out["short"] = True
                said.append(
                    f"the gripper stopped at {got:.0f} % open instead of {want:.0f} %"
                    + (" (it may be holding something)" if got > want else "")
                )
        if out["short"]:
            why = (
                ". Likely load, a joint near its limit, or something in the way. Check before "
                "gripping or moving on."
                if joint_short or out.get("off_by_cm", 0) > SHORT_CM
                else "."
            )
            out["message"] = "; ".join(said) + why
        return out

    # ---------- moving ----------

    async def move_joints(
        self, joints: dict[str, float], relative: bool = False, arm: str | None = None
    ) -> dict:
        self._check_can_move(arm)
        if not joints:
            raise Refused("no joints given")
        unknown = set(joints) - set(self.arm.joint_names)
        if unknown:
            raise Refused(
                f"unknown joints {sorted(unknown)}; this arm has {list(self.arm.joint_names)}"
            )
        _finite(**joints)
        current = self.arm.read_joints()
        notes: list[str] = []
        target = {j: current[j] + v if relative else v for j, v in joints.items()}
        target = self._clip_to_limits(current, target, notes)
        target = self._limit_change(current, target, notes)
        self._check_floor(current, self._line(current, target))
        return await self._run([target], notes)

    async def gripper(self, open_pct: float, arm: str | None = None) -> dict:
        self._check_can_move(arm)
        _finite(open_pct=open_pct)
        notes: list[str] = []
        pct = min(max(open_pct, 0.0), 100.0)
        if pct != open_pct:
            notes.append(f"open_pct {open_pct:g} → {pct:g} (0–100)")
        lo, hi = self._gripper_range()
        return await self._run([{"gripper": lo + (hi - lo) * pct / 100}], notes)

    async def go_to_pose(self, name: str, arm: str | None = None, one_move: bool = False) -> dict:
        """A named pose. `one_move`: all the way in one smooth move, without the per-call limit
        (the hub's chat only, quick job 118; the AI tools and programs keep the limit)."""
        self._check_can_move(arm)
        if name not in self.poses:
            raise Refused(f"no pose called {name!r}; poses for this arm: {sorted(self.poses)}")
        current = self.arm.read_joints()
        notes: list[str] = []
        pose = {j: v for j, v in self.poses[name].items() if j in current}
        target = self._clip_to_limits(current, pose, notes)
        if not one_move:
            target = self._limit_change(current, target, notes)
        self._check_floor(current, self._line(current, target))
        return await self._run([target], notes, smooth=True)

    async def move_to(
        self,
        x_cm: float,
        y_cm: float,
        z_cm: float,
        tool_angle_deg: float | None = None,
        arm: str | None = None,
    ) -> dict:
        self._check_can_move(arm)
        if not self.kin:
            raise Refused(f"no kinematics for the {self.arm.model} model; use move_joints")
        _finite(x_cm=x_cm, y_cm=y_cm, z_cm=z_cm)
        if tool_angle_deg is not None:
            _finite(tool_angle_deg=tool_angle_deg)
        if z_cm < self.limits.min_z_cm:
            raise Refused(
                f"z {z_cm:g} cm is below the {self.limits.min_z_cm:g} cm floor; nothing moved"
            )
        current = self.arm.read_joints()
        (tx, ty, tz), angle0 = self.kin.fk(current)
        start = (tx * 100, ty * 100, tz * 100)
        goal = (x_cm, y_cm, z_cm)
        angle1 = angle0 if tool_angle_deg is None else tool_angle_deg
        d_angle = _angle_diff(angle1, angle0)
        dist = math.dist(start, goal)
        notes: list[str] = []
        k = min(
            1.0,
            self.limits.max_move_cm / dist if dist > 1e-9 else 1.0,
            self.limits.max_joint_change_deg / abs(d_angle) if abs(d_angle) > 1e-9 else 1.0,
        )
        if k < 1.0:
            notes.append(
                f"went {k:.0%} of the way: at most {self.limits.max_move_cm:g} cm and "
                f"{self.limits.max_joint_change_deg:g}° of tilt per call; call again to continue"
            )
        end = tuple(s + (g - s) * k for s, g in zip(start, goal, strict=True))
        steps = max(
            1, math.ceil(math.dist(start, end) / LINE_STEP_CM), math.ceil(abs(d_angle * k) / 5)
        )
        bounds = {
            j: JointLimit(lo, hi)
            for j, (lo, hi) in soft_bounds(self.arm.limits, current, LIMIT_MARGIN_DEG).items()
        }
        path, seed = [], dict(current)

        def solve(f: float) -> tuple[dict, tuple]:
            p_cm = tuple(s + (e - s) * f for s, e in zip(start, end, strict=True))
            a = angle0 + d_angle * k * f
            q = solve_ik(self.kin, seed, tuple(v / 100 for v in p_cm), a, bounds, iterations=80)
            (rx, ry, rz), ra = self.kin.fk(q)
            miss = math.dist(p_cm, (rx * 100, ry * 100, rz * 100))
            if miss > REACH_TOLERANCE_CM or abs(_angle_diff(ra, a)) > ANGLE_TOLERANCE_DEG:
                on_the_way = "" if k == 1.0 and f == 1.0 else f" (on the way to {goal} cm)"
                raise Refused(
                    f"can't reach ({p_cm[0]:.1f}, {p_cm[1]:.1f}, {p_cm[2]:.1f}) cm with tool angle "
                    f"{a:.0f}°{on_the_way}: the closest the arm gets is ({rx * 100:.1f}, "
                    f"{ry * 100:.1f}, {rz * 100:.1f}) cm at {ra:.0f}°. Nothing moved. Try a nearer "
                    "point or another tool angle."
                )
            return q, max(abs(q[j] - seed[j]) for j in IK_JOINTS)

        for i in range(1, steps + 1):
            q, jump = solve(i / steps)
            if jump > MAX_WAYPOINT_JUMP_DEG:
                raise Refused(
                    "that path needs a sudden big joint swing (the arm would flip); nothing "
                    "moved. Try another tool angle or a nearer point."
                )
            n = math.ceil(jump / SUBSTEP_DEG)
            for sub in range(1, n):  # extra waypoints on the line, solved from the previous one
                q_sub, _ = solve((i - 1 + sub / n) / steps)
                path.append({j: q_sub[j] for j in IK_JOINTS})
                seed = q_sub
            if n > 1:
                q, _ = solve(i / steps)
            path.append({j: q[j] for j in IK_JOINTS})
            seed = q
        self._check_floor(current, [current | wp for wp in path])
        self.last_target = (end, angle0 + d_angle * k)
        return await self._run(path, notes, aim=self.last_target)

    def _reaches(self, seed: dict, point_cm: tuple, angle: float) -> dict | None:
        """The joints that put the gripper point at `point_cm` with `angle`, or None."""
        bounds = {
            j: JointLimit(lo, hi)
            for j, (lo, hi) in soft_bounds(self.arm.limits, seed, LIMIT_MARGIN_DEG).items()
        }
        q = solve_ik(self.kin, seed, tuple(v / 100 for v in point_cm), angle, bounds, 120)
        (rx, ry, rz), ra = self.kin.fk(q)
        miss = math.dist(point_cm, (rx * 100, ry * 100, rz * 100))
        if miss > REACH_TOLERANCE_CM or abs(_angle_diff(ra, angle)) > ANGLE_TOLERANCE_DEG:
            return None
        return q

    def _fixed_jaw_beside(
        self, current: dict, x_cm: float, y_cm: float, z_cm: float, angle: float = DOWN_DEG
    ):
        """Where the gripper point goes so the object at (x, y) stands between the open jaws:
        PICK_JAW_SIDE_CM from it, against the moving jaw's opening direction, at tool angle
        `angle`. Only arms whose kinematics have frames (the SO-101); others aim at (x, y)."""
        if not hasattr(self.kin, "frames"):
            return x_cm, y_cm
        gx, gy = x_cm, y_cm
        for _ in range(3):  # the direction turns with shoulder_pan: settle it
            q = self._reaches(current, (gx, gy, z_cm), angle)
            if q is None:
                return gx, gy  # the checks below refuse it with their own sentence
            rot = self.kin.frames(q)["wrist_roll"][1]
            dx, dy = (sum(rot[i][k] * SO101_OPEN_DIR[k] for k in range(3)) for i in range(2))
            n = math.hypot(dx, dy)
            if n < 1e-6:
                return gx, gy
            gx = x_cm - PICK_JAW_SIDE_CM * dx / n
            gy = y_cm - PICK_JAW_SIDE_CM * dy / n
        return gx, gy

    def pick_plan(
        self, x_cm: float, y_cm: float, height_cm: float, seed: dict | None = None
    ) -> tuple[float, tuple, tuple] | None:
        """How pick_at takes the object at (x, y), starting from the joints `seed` (default: where
        the arm is): (tool angle, the point above it, the grip point), with the steepest angle of
        PICK_ANGLES_DEG that reaches both points and keeps the arm above the floor. None: out of
        reach (quick job 117)."""
        current = seed or self.arm.read_joints()
        for angle in PICK_ANGLES_DEG:
            z_above = height_cm + PICK_ABOVE_CM
            gx, gy = self._fixed_jaw_beside(current, x_cm, y_cm, z_above, angle)
            above = (gx, gy, z_above)
            grip = (gx, gy, max(height_cm - PICK_JAW_DEPTH_CM, self.limits.min_z_cm))
            q_above = self._reaches(current, above, angle)
            q_grip = q_above and self._reaches(q_above, grip, angle)
            if q_grip and self._lowest_z_cm(q_grip) >= self.limits.min_z_cm - REACH_TOLERANCE_CM:
                return angle, above, grip
        return None

    async def pick_at(
        self,
        x_cm: float,
        y_cm: float,
        height_cm: float = 2.5,
        open_pct: float = 100.0,
        arm: str | None = None,
    ) -> dict:
        """Pick up the object standing at (x, y) on the table: open, go above it pointing
        down (tilted up to 60° when straight down can't reach it: `pick_plan`), go straight
        down as deep as the jaws reach (PICK_JAW_DEPTH_CM below its top, never below the
        floor), close, lift. Every point is checked before anything moves; each step is logged
        (and shown on AI Control) before it moves."""
        self._check_can_move(arm)
        if not self.kin:
            raise Refused(f"no kinematics for the {self.arm.model} model; pick with move_joints")
        _finite(x_cm=x_cm, y_cm=y_cm, height_cm=height_cm, open_pct=open_pct)
        lo_h, hi_h = PICK_HEIGHT_CM
        if not lo_h <= height_cm <= hi_h:
            raise Refused(
                f"height_cm {height_cm:g}: pick_at takes objects {lo_h:g}–{hi_h:g} cm tall"
            )
        plan = self.pick_plan(x_cm, y_cm, height_cm)
        if plan is None:
            raise Refused(
                f"can't reach ({x_cm:g}, {y_cm:g}) with the gripper pointing down or tilted up to "
                f"{DOWN_DEG - PICK_ANGLES_DEG[-1]:g}°; nothing moved. Too near the base or too far "
                "out: pick something else or move it."
            )
        angle, above, grip = plan
        current = self.arm.read_joints()
        (tx, ty, tz), _ = self.kin.fk(current)
        here = (tx * 100, ty * 100, tz * 100)
        far = math.dist(here, above)
        if far > self.limits.max_move_cm:
            raise Refused(
                f"the point above the object ({above[0]:.1f}, {above[1]:.1f}, {above[2]:.1f}) cm "
                f"is {far:.1f} cm from the gripper; pick_at starts within "
                f"{self.limits.max_move_cm:g} cm of it. Nothing moved: move_to near it first "
                f"(tool angle {angle:g}), then pick_at."
            )
        steps: list[dict] = []

        async def step(n: int, say: str, tool: str, **args) -> dict:
            self.calls.write("pick_at", {"step": f"{n}/5 {say}"}, "next", say)
            r = await self.call(tool, **args)
            steps.append({"step": f"{n}/5 {say}", "result": r.get("result")} | _brief(r))
            return r

        def ended(why: str, r: dict) -> dict:
            out = {"result": r.get("result"), "steps": steps, "message": why}
            return out | (r if self._disconnected() else self._where())

        r = await step(1, "open the gripper", "gripper", open_pct=open_pct)
        if r["result"] in ("stopped", "disconnected"):
            return ended(f"{r['result']} at step 1. Don't move again until the user says so.", r)
        moves = [(2, f"go above it, tool angle {angle:g}°", above), (3, "go straight down", grip)]
        for n, say, (x, y, z) in moves:
            r = await step(n, say, "move_to", x_cm=x, y_cm=y, z_cm=z, tool_angle_deg=angle)
            if r["result"] in ("stopped", "disconnected"):
                why = f"{r['result']} at step {n}. Don't move again until the user says so."
                return ended(why, r)
            if r.get("off_by_cm", 0.0) > PICK_OFF_CM:
                return ended(
                    f"step {n} ended {r['off_by_cm']} cm off, so the pick stopped there with the "
                    "gripper open. Look (wrist camera), then move_to and pick_at again.",
                    r,
                )
        r = await step(4, "close the gripper", "gripper", open_pct=0)
        if r["result"] in ("stopped", "disconnected"):
            return ended(f"{r['result']} at step 4. Don't move again until the user says so.", r)
        x, y, z = above
        r = await step(5, "lift", "move_to", x_cm=x, y_cm=y, z_cm=z, tool_angle_deg=angle)
        if r["result"] in ("stopped", "disconnected"):
            return ended(f"{r['result']} at step 5. Don't move again until the user says so.", r)
        held = r.get("gripper_open_pct", 0.0) > PICK_HELD_PCT
        out = ended(
            f"holding something: the gripper stopped at {r['gripper_open_pct']:.0f} % open. "
            "Check with the wrist camera."
            if held
            else "closed on nothing (the gripper shut all the way): missed. Look with the "
            "cameras before trying again.",
            r,
        )
        out["result"] = "holding" if held else "missed"
        out["tool_angle_deg"] = angle
        return out

    def use_venue(self, venue: Venue) -> None:
        """Another venue while running (the hub's visitor mode, quick job 35): its limits."""
        self.venue, self.limits = venue, AiLimits.from_venue(venue)

    def gesture_path(self, name: str) -> tuple[list[dict], list[str]]:
        """A fixed move's waypoints (gestures.yaml): the start pose, each step, the start pose
        again; clipped to the soft limits and checked against the floor all the way, like a
        move tool's. Raises Refused (nothing moved) when the arm can't move or it would go below
        the floor. Not limited per call like an AI tool's move: no AI chooses it."""
        self._check_can_move(None)
        gesture = self.gestures.get(name)
        if gesture is None:
            raise Refused(f"no {name} for the {self.arm.model} model (gestures.yaml)")
        if gesture["from"] not in self.poses:
            raise Refused(f"{name} starts from {gesture['from']!r}, which isn't in poses.yaml")
        current = self.arm.read_joints()
        base = {j: v for j, v in self.poses[gesture["from"]].items() if j in current}
        points = [
            base,
            *(
                {**base, **{j: base[j] + d for j, d in step.items() if j in base}}
                for step in gesture["steps"]
            ),
            base,
        ]
        notes: list[str] = []
        path = [self._clip_to_limits(current, p, notes) for p in points]
        prev = current
        for wp in path:
            self._check_floor(current, self._line(prev, prev | wp))
            prev = prev | wp
        return path, sorted(set(notes))

    async def wave(self, arm: str | None = None) -> dict:
        """The wave (quick job 35): gestures.yaml's fixed poses around `ready`, at the venue's
        speed. Logged like a tool call. The hub's assistant may start it in visitor mode; it never
        chooses the motion, and it isn't one of the MCP tools."""
        self._check_arm(arm)
        path, notes = self.gesture_path("wave")
        return await self._run(path, notes)

    async def stop(self, arm: str | None = None) -> dict:
        """Always allowed: freeze now, whoever has control."""
        self.loop.stop()
        if self._disconnected():
            return {"result": "stopped", "problem": self._disconnected()}
        return {"result": "stopped"} | self._where()

    # ---------- every call, logged ----------

    async def call(self, tool: str, **args) -> dict:
        """Run a tool by name and log it. Refusals raise `Refused` after logging."""
        try:
            result = await getattr(self, tool)(**args)
        except Refused as e:
            self.calls.write(tool, args, "refused", str(e))
            raise
        except Exception as e:
            self.calls.write(tool, args, "error", repr(e))
            raise
        outcome = (
            "stopped"
            if result.get("result") == "stopped" and tool != "stop"
            else "short"
            if result.get("result") == "stopped_short"
            else "clipped"
            if result.get("clipped")
            else "ok"
        )
        logged = dict(result)
        for key in ("image_png", "image_jpeg"):
            if key in logged:
                logged[key] = f"{len(logged[key])} bytes"
        self.calls.write(tool, args, outcome, logged)
        return result


def _brief(r: dict) -> dict:
    """What a pick step's own result says that matters afterwards."""
    keep = ("off_by_cm", "message", "gripper_open_pct", "gripper_point_cm")
    return {k: r[k] for k in keep if k in r}


def _grab_jpeg(path: str, width_px: int, camera: str) -> bytes:
    """One settled frame of `camera` at `path` as a JPEG `width_px` wide. It opens through the
    brain's camera feeds, so a page that shows the camera now shares it (quick job 116)."""
    from lab_os.camera_feed import FEEDS, CameraError

    try:
        return _frame_jpeg(FEEDS.grab(camera, path), width_px)
    except CameraError as e:
        raise Refused(str(e)) from e


def _frame_jpeg(frame, width_px: int) -> bytes:
    """A frame as a JPEG `width_px` wide (at most its own width)."""
    import cv2  # headless OpenCV, imported late

    h, w = frame.shape[:2]
    if w > width_px:
        frame = cv2.resize(frame, (width_px, round(h * width_px / w)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        raise Refused("couldn't encode the picture")
    return buf.tobytes()


def grab_frame(path: str):
    """One settled frame (BGR array, the camera's own size) from the camera at `path`."""
    import cv2

    cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
    try:
        if not cap.isOpened():
            raise Refused(f"couldn't open the camera at {path}")
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # as camera_feed: USB time
        frame = None
        last = None
        steady = 0
        start = time.monotonic()
        # These cameras start black, then auto-exposure overshoots to white: keep reading until
        # the brightness has held still for a few frames (at most ~6 s).
        while time.monotonic() - start < 6:
            ok, got = cap.read()
            if not ok:
                continue
            frame = got
            level = float(got.mean())
            steady = steady + 1 if last is not None and abs(level - last) < 3 else 0
            last = level
            if steady >= 4 and 8 < level < 245:
                break
        if frame is None:
            raise Refused(f"the camera at {path} gave no picture")
    finally:
        cap.release()
    return frame
