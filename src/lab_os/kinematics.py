"""Arm kinematics for teleop: where the gripper is for given joints (forward kinematics), and the
joints that put it somewhere (inverse kinematics, a small damped-least-squares solver).

Frame (all arms): metres, Z up, the arm faces +x at shoulder_pan = 0, +y = the arm's left.
Joints use the shared names and degrees. The IK solves shoulder_pan, shoulder_lift, elbow_flex and
wrist_flex for a gripper position plus a "tool angle" (the gripper's tilt from vertical in the
arm's plane, + = forward); wrist_roll and the gripper are passed through unchanged.

Only the xArm 1S is modelled so far (from the same dimensions as web/arm/arm-model.js). The SO-101
needs a URDF-based model (models/so101) with the same two methods.
"""

import math
from dataclasses import dataclass
from typing import Protocol

from lab_os.robots.base import JointLimit

Vec3 = tuple[float, float, float]
IK_JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex")


class Kinematics(Protocol):
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


KINEMATICS: dict[str, Kinematics] = {"xarm1s": XArmKinematics()}


def kinematics_for(model: str) -> Kinematics | None:
    """The kinematics for an `Arm.model`, or None (teleop then falls back to joint space)."""
    return KINEMATICS.get(model)


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
