"""Arm kinematics for teleop: where the gripper is for given joints (forward kinematics), and the
joints that put it somewhere (inverse kinematics, a small damped-least-squares solver).

Frame (all arms): metres, Z up, the arm faces +x at shoulder_pan = 0, +y = the arm's left.
Joints use the shared names and degrees. The IK solves shoulder_pan, shoulder_lift, elbow_flex and
wrist_flex for a gripper position plus a "tool angle" (the gripper's tilt from vertical in the
arm's plane, + = forward); wrist_roll and the gripper are passed through unchanged.

The xArm 1S is modelled by hand (same dimensions as web/arm/arm-model.js); the SO-101 straight from
its URDF (models/so101), whose joint names are already the shared ones.
"""

import functools
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from lab_os import REPO_ROOT
from lab_os.robots.base import JointLimit

Vec3 = tuple[float, float, float]
Mat3 = tuple[Vec3, Vec3, Vec3]
IK_JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex")
SO101_URDF = REPO_ROOT / "models/so101/so101_new_calib.urdf"


class Kinematics(Protocol):
    # wrist_roll direction for a hand roll that is counter-clockwise as the operator sees it
    # (standing behind the arm, looking along the gripper). Differs per arm (docs/dev/GOTCHAS.md).
    roll_sign: float

    def fk(self, joints: dict[str, float]) -> tuple[Vec3, float]:
        """Gripper point (m) and tool angle (degrees from vertical, + = forward)."""
        ...


@dataclass(frozen=True)
class XArmKinematics:
    """xArm 1S: base pan, then three parallel pitch joints (lift, elbow, wrist_flex), then roll.

    Same conventions as the 3D model: all-zero = upright, +pan swings the arm to its right
    (clockwise from above), +lift/+elbow/+wrist_flex tilt forward.
    """

    shoulder_z: float = 0.065  # shoulder axis above the table (Hiwonder drawing)
    upper: float = 0.101  # shoulder → elbow
    fore: float = 0.095  # elbow → wrist_flex axis
    tool: float = 0.145  # wrist_flex axis → between the fingers (roll 45 + pivot 50 + 50 mm)
    # +wrist_roll is counter-clockwise seen from the gripper tip, so the operator behind it sees
    # it clockwise. Found flipped by the builder on the Quest, 2026-10-29.
    roll_sign: float = -1.0

    def fk(self, joints: dict[str, float]) -> tuple[Vec3, float]:
        pan = math.radians(joints.get("shoulder_pan", 0.0))
        a1 = math.radians(joints.get("shoulder_lift", 0.0))
        a2 = a1 + math.radians(joints.get("elbow_flex", 0.0))
        a3 = a2 + math.radians(joints.get("wrist_flex", 0.0))
        # Each link's angle from vertical, in the arm's plane (r = forward distance, z = up).
        r = self.upper * math.sin(a1) + self.fore * math.sin(a2) + self.tool * math.sin(a3)
        z = (
            self.shoulder_z
            + self.upper * math.cos(a1)
            + self.fore * math.cos(a2)
            + self.tool * math.cos(a3)
        )
        return (r * math.cos(pan), -r * math.sin(pan), z), math.degrees(a3)


# ---- URDF chains (SO-101) ----------------------------------------------------------------------
def _rpy(r: float, p: float, y: float) -> Mat3:
    cr, sr, cp, sp, cy, sy = (
        math.cos(r),
        math.sin(r),
        math.cos(p),
        math.sin(p),
        math.cos(y),
        math.sin(y),
    )
    return (
        (cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
        (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
        (-sp, cp * sr, cp * cr),
    )


def _about(axis: Vec3, a: float) -> Mat3:
    x, y, z = axis
    c, s = math.cos(a), math.sin(a)
    t = 1 - c
    return (
        (t * x * x + c, t * x * y - s * z, t * x * z + s * y),
        (t * x * y + s * z, t * y * y + c, t * y * z - s * x),
        (t * x * z - s * y, t * y * z + s * x, t * z * z + c),
    )


def _mm(a: Mat3, b: Mat3) -> Mat3:
    (b0, b1, b2) = b
    return tuple(tuple(r[0] * b0[j] + r[1] * b1[j] + r[2] * b2[j] for j in range(3)) for r in a)


def _mv(a: Mat3, v: Vec3) -> Vec3:
    return tuple(a[i][0] * v[0] + a[i][1] * v[1] + a[i][2] * v[2] for i in range(3))


@dataclass(frozen=True)
class UrdfJoint:
    name: str
    xyz: Vec3  # origin, in the parent link's frame
    rot: Mat3  # origin rotation (from rpy)
    axis: Vec3 | None  # None = fixed joint


def load_chain(urdf: Path, tip: str) -> tuple[UrdfJoint, ...]:
    """The joints from the URDF's root link down to link `tip`, in order."""
    root = ET.parse(urdf).getroot()
    by_child = {j.find("child").get("link"): j for j in root.findall("joint")}
    chain, link = [], tip
    while link in by_child:
        j = by_child[link]
        o = j.find("origin")
        floats = lambda s: tuple(float(v) for v in s.split())  # noqa: E731
        axis = floats(j.find("axis").get("xyz")) if j.get("type") == "revolute" else None
        chain.append(
            UrdfJoint(j.get("name"), floats(o.get("xyz")), _rpy(*floats(o.get("rpy"))), axis)
        )
        link = j.find("parent").get("link")
    return tuple(reversed(chain))


@dataclass(frozen=True)
class UrdfKinematics:
    """Forward kinematics from a URDF chain whose revolute joints use the shared names (degrees).
    The tool angle is the tilt of the line from the `pivot` joint's axis to the tip: 0 = pointing
    up, 90 = pointing forward (away from the base, in the direction shoulder_pan faces), 180 =
    pointing down; range -90..270."""

    chain: tuple[UrdfJoint, ...]
    roll_sign: float = 1.0
    pivot: str = "wrist_flex"

    def frames(self, joints: dict[str, float]) -> dict[str, tuple[Vec3, Mat3]]:
        """World position + rotation of every joint's frame (after its own rotation), and of
        the tip under the key "tip"."""
        rot: Mat3 = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        pos: Vec3 = (0.0, 0.0, 0.0)
        out = {}
        for j in self.chain:
            pos = tuple(p + d for p, d in zip(pos, _mv(rot, j.xyz), strict=True))
            rot = _mm(rot, j.rot)
            if j.axis is not None:
                rot = _mm(rot, _about(j.axis, math.radians(joints.get(j.name, 0.0))))
            out[j.name] = (pos, rot)
        out["tip"] = (pos, rot)
        return out

    def fk(self, joints: dict[str, float]) -> tuple[Vec3, float]:
        f = self.frames(joints)
        tip, pivot = f["tip"][0], f[self.pivot][0]
        dx, dy, dz = (t - p for t, p in zip(tip, pivot, strict=True))
        pan = math.radians(joints.get("shoulder_pan", 0.0))
        forward = dx * math.cos(pan) - dy * math.sin(pan)  # +pan faces the arm's right (−y)
        angle = math.degrees(math.atan2(forward, dz))
        # Pointing down (180) is the usual grasp: keep the ±180 wrap away from it, at "pointing
        # backward" (-90), which the arm can't do with the gripper near the table anyway.
        return tip, angle + 360.0 if angle < -90.0 else angle


@functools.cache
def so101_kinematics() -> UrdfKinematics:
    """SO-101 from models/so101 (tip = gripper_frame_link: at the fingertips, on the fixed jaw's
    inner face; the tips reach 0.6 cm past it). Its zero pose is an "L": upper arm up, forearm and
    gripper forward (tool angle 90). +wrist_roll is clockwise seen from above / counter-clockwise
    for the operator behind it: the opposite of the xArm."""
    return UrdfKinematics(load_chain(SO101_URDF, "gripper_frame_link"), roll_sign=1.0)


KINEMATICS = {"xarm1s": XArmKinematics, "so101": so101_kinematics}


class OnTable:
    """An arm's kinematics with heights measured from the table, not from the bottom of its base
    (quick job 28). `table_z_m`: the table's z in the arm's own frame, negative for an arm on a
    plate. fk and frames report z − table_z_m, so IK (solve_ik) aims in table heights too; the
    rest (roll_sign, the xArm's lack of frames) is the wrapped kinematics'."""

    def __init__(self, kin: Kinematics, table_z_m: float):
        self.kin = kin
        self.table_z_m = table_z_m

    def fk(self, joints: dict[str, float]) -> tuple[Vec3, float]:
        (x, y, z), angle = self.kin.fk(joints)
        return (x, y, z - self.table_z_m), angle

    def __getattr__(self, name: str):
        attr = getattr(self.kin, name)  # AttributeError passes through: no frames on the xArm
        if name != "frames":
            return attr

        def frames(joints: dict[str, float]) -> dict[str, tuple[Vec3, Mat3]]:
            dz = self.table_z_m
            return {k: ((p[0], p[1], p[2] - dz), r) for k, (p, r) in attr(joints).items()}

        return frames


def on_table(kin: Kinematics | None, table_z_cm: float) -> Kinematics | None:
    """`kin` with heights from the table (OnTable), or `kin` itself when the table is at z 0."""
    if kin is None or not table_z_cm:
        return kin
    return OnTable(kin, table_z_cm / 100)


def kinematics_for(model: str) -> Kinematics | None:
    """The kinematics for an `Arm.model`, or None (teleop then falls back to joint space)."""
    make = KINEMATICS.get(model)
    return make() if make else None


# Weight of the tool angle against position in the solver: 1 rad of tilt counts like 5 cm.
ANGLE_WEIGHT_M = 0.05
# Per iteration: chase at most 1 cm of error and move no joint more than 3°. Without these, a far
# (unreachable) target made one big step swing the base ~120°.
MAX_ERR_M = 0.01
MAX_STEP_DEG = 3.0


def _task(kin: Kinematics, joints: dict[str, float]) -> list[float]:
    (x, y, z), angle = kin.fk(joints)
    return [x, y, z, math.radians(angle) * ANGLE_WEIGHT_M]


def _solve4(a: list[list[float]], b: list[float]) -> list[float]:
    """Solve a small linear system (Gaussian elimination with partial pivoting)."""
    n = len(b)
    m = [row[:] + [v] for row, v in zip(a, b, strict=True)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        for r in range(n):
            if r != col and m[col][col]:
                f = m[r][col] / m[col][col]
                m[r] = [rv - f * cv for rv, cv in zip(m[r], m[col], strict=True)]
    return [m[i][n] / m[i][i] if m[i][i] else 0.0 for i in range(n)]


def solve_ik(
    kin: Kinematics,
    seed: dict[str, float],
    target: Vec3,
    tool_angle: float,
    bounds: dict[str, JointLimit] | None = None,
    iterations: int = 40,
    damping: float = 0.01,
) -> dict[str, float]:
    """Joints near `seed` that bring the gripper to `target` with `tool_angle` (degrees).

    Damped least squares from the seed, so the answer stays on the seed's branch (no elbow flips)
    and unreachable targets end as close as the joints allow instead of failing. Each step is
    clamped to `bounds`. Joints other than IK_JOINTS are copied from the seed.
    """
    q = dict(seed)
    want = [*target, math.radians(tool_angle) * ANGLE_WEIGHT_M]
    eps = 1e-3  # degrees, for the numeric Jacobian
    for _ in range(iterations):
        now = _task(kin, q)
        err = [w - n for w, n in zip(want, now, strict=True)]
        size = math.sqrt(sum(e * e for e in err))
        if size < 1e-5:
            break
        if size > MAX_ERR_M:
            err = [e * MAX_ERR_M / size for e in err]
        cols = []
        for j in IK_JOINTS:
            dq = dict(q)
            dq[j] += eps
            cols.append(
                [(a - b) / math.radians(eps) for a, b in zip(_task(kin, dq), now, strict=True)]
            )
        jac = [[cols[c][r] for c in range(4)] for r in range(4)]  # rows = task, cols = joints
        # dq = Jᵀ (J Jᵀ + λ² I)⁻¹ err
        jjt = [
            [
                sum(jac[r][k] * jac[s][k] for k in range(4)) + (damping**2 if r == s else 0.0)
                for s in range(4)
            ]
            for r in range(4)
        ]
        y = _solve4(jjt, err)
        for c, j in enumerate(IK_JOINTS):
            step = math.degrees(sum(jac[r][c] * y[r] for r in range(4)))
            q[j] += min(max(step, -MAX_STEP_DEG), MAX_STEP_DEG)
            if bounds and j in bounds:
                q[j] = bounds[j].clamp(q[j])
    return q
