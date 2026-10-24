"""Cheap first mapping with clutch control (current-focus.md step 3).

- Grip held = clutch engaged = the arm follows the controller. Released = the arm freezes.
- Relative: on engage, remember the controller pose and the arm's *current* joints; afterwards the
  arm moves by how far the controller has moved since then. No snapping, ever.
- Gentle ramps: each joint's commanded position changes by at most `max_deg_per_s * speed_scale`.
- Tilt-for-rotation (kept from the glove): controller pitch → wrist_flex, roll → wrist_roll.
- Trigger → gripper (0 = open, fully pressed = closed).
- Soft limits: targets stay `limit_margin_deg` inside the arm's joint limits, so the driver never
  has to clamp. At a limit the clutch "slips": moving the hand further does nothing, and moving it
  back moves the arm back immediately (no wind-up, no jump on the next grab).

This is joint-space on purpose: proper inverse kinematics is step 4. Joint limits don't prevent
every self-collision; that needs the arm's geometry (also step 4).
"""

import math
from dataclasses import dataclass, field

from lab_os.robots.base import JointLimit
from lab_os.teleop.messages import ControllerState, Quat, Vec3


@dataclass
class MappingConfig:
    hand: str = "right"
    grip_on: float = 0.6  # hysteresis: engage above this...
    grip_off: float = 0.4  # ...release below this
    deg_per_m: float = 200.0  # 10 cm of hand motion → 20° of joint motion
    max_deg_per_s: float = 90.0  # ramp limit at speed_scale = 1
    gripper_open: float = 60.0
    gripper_closed: float = 0.0
    limit_margin_deg: float = 3.0  # stay this far inside each joint limit
    # Direction of each joint for the hand motion that drives it (+1 / -1). Defaults are the SO-101
    # convention (checked with forward kinematics on models/so101): +pan swings the gripper to the
    # arm's right, +lift and +elbow lower/fold it, +wrist_flex tilts it down. The xArm model in
    # web/arm/arm-model.js uses the same convention. A new arm that differs overrides these.
    signs: dict[str, float] = field(
        default_factory=lambda: {
            "shoulder_pan": 1.0,  # hand right → gripper right
            "shoulder_lift": -1.0,  # hand up → arm up
            "elbow_flex": 1.0,  # hand forward → elbow opens (reach out)
            "wrist_flex": -1.0,  # tilt controller nose up → gripper tilts up
            "wrist_roll": 1.0,  # roll the controller → roll the gripper
        }
    )


# Joints driven relative to the anchor (the clutch can slip on these); the gripper is absolute.
RELATIVE_JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll")


def _quat_conj(q: Quat) -> Quat:
    x, y, z, w = q
    return (-x, -y, -z, w)


def _quat_mul(a: Quat, b: Quat) -> Quat:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def _twist_deg(q: Quat, axis: int) -> float:
    """Rotation of `q` around one of its local axes (0 = x/pitch, 2 = z/roll), in degrees."""
    angle = 2.0 * math.atan2(q[axis], q[3])
    if angle > math.pi:
        angle -= 2.0 * math.pi
    elif angle < -math.pi:
        angle += 2.0 * math.pi
    return math.degrees(angle)


@dataclass
class ClutchMapper:
    config: MappingConfig = field(default_factory=MappingConfig)
    engaged: bool = False
    # After a freeze (connection loss), grip must be released and pressed again before moving.
    needs_release: bool = False
    _anchor_pos: Vec3 | None = None
    _anchor_quat: Quat | None = None
    _anchor_joints: dict[str, float] = field(default_factory=dict)
    _commanded: dict[str, float] = field(default_factory=dict)
    _bounds: dict[str, tuple[float, float]] = field(default_factory=dict)

    def reset(self, require_release: bool = True) -> None:
        """Drop the clutch (e.g. on connection loss). Requires a fresh grip press to move again."""
        self.engaged = False
        self.needs_release = require_release
        self._anchor_pos = self._anchor_quat = None

    def step(
        self,
        controller: ControllerState | None,
        arm_joints: dict[str, float],
        dt: float,
        speed_scale: float,
        limits: dict[str, JointLimit] | None = None,
    ) -> dict[str, float] | None:
        """Return joint targets for this tick, or None when the arm should hold still."""
        cfg = self.config
        if controller is None or not controller.tracked:
            self.engaged = False  # tracking lost = clutch released
            return None

        if self.needs_release:
            if controller.grip < cfg.grip_off:
                self.needs_release = False
            return None

        if not self.engaged and controller.grip > cfg.grip_on:
            self.engaged = True
            self._anchor_pos = controller.pos
            self._anchor_quat = controller.quat
            self._anchor_joints = dict(arm_joints)
            self._commanded = dict(arm_joints)
            self._bounds = self._soft_bounds(limits or {}, arm_joints)
        elif self.engaged and controller.grip < cfg.grip_off:
            self.engaged = False
        if not self.engaged:
            return None

        desired = self._desired(controller)
        for joint, target in desired.items():
            if joint not in self._bounds:
                continue
            lo, hi = self._bounds[joint]
            clamped = min(max(target, lo), hi)
            if clamped != target and joint in RELATIVE_JOINTS:
                self._anchor_joints[joint] += clamped - target  # slip: hand moves, arm stays
            desired[joint] = clamped
        max_step = cfg.max_deg_per_s * min(max(speed_scale, 0.0), 1.0) * dt
        for joint, target in desired.items():
            current = self._commanded.get(joint, target)
            delta = min(max(target - current, -max_step), max_step)
            self._commanded[joint] = current + delta
        return {j: self._commanded[j] for j in desired}

    def _soft_bounds(
        self, limits: dict[str, JointLimit], joints: dict[str, float]
    ) -> dict[str, tuple[float, float]]:
        """Limits minus the margin, widened to include where the arm already is (so engaging
        never moves it), but never beyond the hard limits."""
        m = self.config.limit_margin_deg
        bounds = {}
        for joint, lim in limits.items():
            lo, hi = lim.low + m, lim.high - m
            if lo > hi:
                lo = hi = (lim.low + lim.high) / 2
            now = joints.get(joint)
            if now is not None:
                lo, hi = min(lo, now), max(hi, now)
            bounds[joint] = (max(lo, lim.low), min(hi, lim.high))
        return bounds

    def _desired(self, c: ControllerState) -> dict[str, float]:
        cfg = self.config
        a = self._anchor_joints
        dx, dy, dz = (now - then for now, then in zip(c.pos, self._anchor_pos, strict=True))
        rel = _quat_mul(_quat_conj(self._anchor_quat), c.quat)
        # WebXR axes: +x right, +y up, -z forward (away from the user). Twist about the
        # controller's x = pitch (nose up > 0), about its z = roll.
        motion = {
            "shoulder_pan": dx * cfg.deg_per_m,
            "shoulder_lift": dy * cfg.deg_per_m,
            "elbow_flex": dz * cfg.deg_per_m,  # dz < 0 = forward
            "wrist_flex": _twist_deg(rel, 0),
            "wrist_roll": _twist_deg(rel, 2),
        }
        desired = {j: a.get(j, 0.0) + cfg.signs.get(j, 1.0) * m for j, m in motion.items()}
        desired["gripper"] = cfg.gripper_open + (cfg.gripper_closed - cfg.gripper_open) * c.trigger
        return {j: v for j, v in desired.items() if j in a}
