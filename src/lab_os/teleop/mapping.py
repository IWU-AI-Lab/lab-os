"""Clutch-controlled mapping from a hand controller to arm joints (current-focus.md steps 3-4).

Two modes, chosen by whether the arm has kinematics (lab_os.kinematics):
- **IK (hand space), step 4:** the gripper moves the way your hand moves: hand forward/left/up in
  the room → gripper forward/left/up, scaled by `tip_m_per_hand_m`. Controller pitch tilts the
  gripper (nose up = gripper tilts up); roll drives wrist_roll directly. Several joints move at
  once; that's intended. Unreachable targets slip like a joint limit (no wind-up).
- **Joint space, step 3 (fallback):** hand x/y/z → pan/lift/elbow, pitch/roll → wrist joints.

- Grip held = clutch engaged = the arm follows the controller. Released = the arm freezes.
- Relative: on engage, remember the controller pose and the arm's *current* joints; afterwards the
  arm moves by how far the controller has moved since then. No snapping, ever.
- Gentle ramps: each joint's commanded position changes by at most `max_deg_per_s * speed_scale`.
- Tilt-for-rotation (kept from the glove): controller pitch → wrist_flex, roll → wrist_roll.
  Measured in the room's axes (left-right = pitch, forward = roll), so pitching a tilted
  controller doesn't leak into roll. Angles are unwrapped frame to frame: rolling past 180° keeps
  counting (then the soft limit holds the joint) instead of jumping to the other end.
- Trigger → gripper (0 = open, fully pressed = closed).
- Soft limits: targets stay `limit_margin_deg` inside the arm's joint limits, so the driver never
  has to clamp. At a limit the clutch "slips": moving the hand further does nothing, and moving it
  back moves the arm back immediately (no wind-up, no jump on the next grab).

Joint limits don't prevent every self-collision (e.g. the gripper hitting the base or table);
that needs a collision model.
"""

import math
from dataclasses import dataclass, field

from lab_os.kinematics import IK_JOINTS, Kinematics, solve_ik
from lab_os.robots.base import JointLimit
from lab_os.teleop.messages import ControllerState, Quat, Vec3


@dataclass
class MappingConfig:
    hand: str = "right"
    grip_on: float = 0.6  # hysteresis: engage above this...
    grip_off: float = 0.4  # ...release below this
    deg_per_m: float = 200.0  # joint space: 10 cm of hand motion → 20° of joint motion
    tip_m_per_hand_m: float = 0.5  # IK: 10 cm of hand motion → 5 cm of gripper motion
    slip_m: float = 0.002  # IK: a target further than this from what the arm reached slips
    # IK: +wrist_roll is counter-clockwise seen from the gripper tip; the operator stands behind
    # the arm and looks along the gripper the other way, so a counter-clockwise hand roll (as you
    # see it) is −wrist_roll. Found flipped by the builder on the Quest, 2026-10-29.
    ik_roll_sign: float = -1.0
    max_deg_per_s: float = 90.0  # ramp limit at speed_scale = 1
    # Trigger released = fully open, pressed = closed: the ends of the arm's gripper limit (inside
    # the soft margin). These two are only used for an arm without a gripper limit.
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


def soft_bounds(
    limits: dict[str, JointLimit], joints: dict[str, float], margin: float
) -> dict[str, tuple[float, float]]:
    """Limits minus `margin`, widened to include where the arm already is, even if that is outside
    the limits (moved by hand, older wider limits): starting a move must never make it jump
    into range. It can move back toward the range, never further out."""
    bounds = {}
    for joint, lim in limits.items():
        lo, hi = lim.low + margin, lim.high - margin
        if lo > hi:
            lo = hi = (lim.low + lim.high) / 2
        now = joints.get(joint)
        if now is not None:
            lo, hi = min(lo, now), max(hi, now)
        bounds[joint] = (lo, hi)
    return bounds


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
    kinematics: Kinematics | None = None  # None = joint-space mapping
    engaged: bool = False
    # After a freeze (connection loss), grip must be released and pressed again before moving.
    needs_release: bool = False
    _anchor_pos: Vec3 | None = None
    _anchor_quat: Quat | None = None
    _twist: dict[int, float] = field(default_factory=dict)  # unwrapped twist per axis, degrees
    _anchor_joints: dict[str, float] = field(default_factory=dict)
    _commanded: dict[str, float] = field(default_factory=dict)
    _bounds: dict[str, tuple[float, float]] = field(default_factory=dict)
    _anchor_tip: Vec3 = (0.0, 0.0, 0.0)  # IK: gripper point / tool angle the hand motion adds to
    _anchor_angle: float = 0.0
    _ik_seed: dict[str, float] = field(default_factory=dict)

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
            self._twist = {0: 0.0, 2: 0.0}
            self._anchor_joints = dict(arm_joints)
            self._commanded = dict(arm_joints)
            self._bounds = soft_bounds(limits or {}, arm_joints, cfg.limit_margin_deg)
            if self.kinematics:
                self._anchor_tip, self._anchor_angle = self.kinematics.fk(arm_joints)
                self._ik_seed = dict(arm_joints)
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

    def _gripper(self, trigger: float) -> float:
        """Trigger 0 → the gripper's open end, 1 → its closed end (0 = closed, + = open)."""
        cfg = self.config
        lo, hi = self._bounds.get("gripper", (cfg.gripper_closed, cfg.gripper_open))
        return hi + (lo - hi) * trigger

    def _unwrapped(self, rel: Quat, axis: int) -> float:
        """Twist about `axis` since the anchor, continuous across ±180° (no sudden full turn)."""
        prev = self._twist.get(axis, 0.0)
        step = (_twist_deg(rel, axis) - prev + 180.0) % 360.0 - 180.0
        self._twist[axis] = prev + step
        return self._twist[axis]

    def _desired_ik(self, dpos: Vec3, pitch: float) -> dict[str, float]:
        """IK joints for the anchor gripper pose moved by the hand. WebXR → arm axes: hand forward
        (−z) = arm +x, hand left (−x) = arm +y, up (+y) = +z."""
        cfg, kin = self.config, self.kinematics
        dx, dy, dz = dpos
        s = cfg.tip_m_per_hand_m
        target = tuple(
            a + d for a, d in zip(self._anchor_tip, (-dz * s, -dx * s, dy * s), strict=True)
        )
        angle = self._anchor_angle - pitch  # nose up → the gripper tilts back/up
        bounds = {j: JointLimit(*self._bounds[j]) for j in IK_JOINTS if j in self._bounds}
        q = solve_ik(kin, self._ik_seed, target, angle, bounds)
        self._ik_seed = q
        reached, reached_angle = kin.fk(q)
        # Slip: an unreachable target moves the anchor instead, so moving the hand back moves the
        # arm back straight away.
        miss = [r - t for r, t in zip(reached, target, strict=True)]
        if math.sqrt(sum(m * m for m in miss)) > cfg.slip_m:
            self._anchor_tip = tuple(a + m for a, m in zip(self._anchor_tip, miss, strict=True))
        if abs(reached_angle - angle) > 1.0:
            self._anchor_angle += reached_angle - angle
        return {j: q[j] for j in IK_JOINTS}

    def _desired(self, c: ControllerState) -> dict[str, float]:
        cfg = self.config
        a = self._anchor_joints
        dx, dy, dz = (now - then for now, then in zip(c.pos, self._anchor_pos, strict=True))
        # Rotation since the anchor, in room axes (current · anchor⁻¹).
        rel = _quat_mul(c.quat, _quat_conj(self._anchor_quat))
        # WebXR axes: +x right, +y up, -z forward (away from the user). Twist about the
        # controller's x = pitch (nose up > 0), about its z = roll.
        if self.kinematics and all(j in a for j in IK_JOINTS):
            desired = self._desired_ik((dx, dy, dz), self._unwrapped(rel, 0))
            desired["wrist_roll"] = a.get("wrist_roll", 0.0) + cfg.ik_roll_sign * self._unwrapped(
                rel, 2
            )
            desired["gripper"] = self._gripper(c.trigger)
            return {j: v for j, v in desired.items() if j in a}
        motion = {
            "shoulder_pan": dx * cfg.deg_per_m,
            "shoulder_lift": dy * cfg.deg_per_m,
            "elbow_flex": dz * cfg.deg_per_m,  # dz < 0 = forward
            "wrist_flex": self._unwrapped(rel, 0),
            "wrist_roll": self._unwrapped(rel, 2),
        }
        desired = {j: a.get(j, 0.0) + cfg.signs.get(j, 1.0) * m for j, m in motion.items()}
        desired["gripper"] = self._gripper(c.trigger)
        return {j: v for j, v in desired.items() if j in a}
