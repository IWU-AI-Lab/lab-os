"""Clutch-controlled mapping from a hand controller to arm joints (teleop focus steps 3-4).

Two mappings, chosen by whether the arm has kinematics (lab_os.kinematics):
- **IK (hand space), step 4:** the gripper moves the way your hand moves: hand forward/left/up in
  the room → gripper forward/left/up, scaled by `tip_m_per_hand_m`. Controller pitch tilts the
  gripper (nose up = gripper tilts up); roll drives wrist_roll directly. Several joints move at
  once; that's intended. Unreachable targets slip like a joint limit (no wind-up).
- **Joint space, step 3 (fallback):** hand x/y/z → pan/lift/elbow, pitch/roll → wrist joints.

- Grip held = clutch engaged = the arm follows the controller. Released = the arm freezes.
- Relative (`mode: relative`, the default): on engage, remember the controller pose and the arm's
  *current* joints; afterwards the arm moves by how far the controller has moved since then,
  scaled. No snapping, ever.
- **1:1** (`mode: one_to_one`, IK only, decision 2026-11-10): the gripper point goes where the hand
  is, at scale 1, so hand and arm stay together (the relative mode drifts apart: scale ½, slips at
  limits). Needs hand positions measured from the 3D arm's base (`XRFrame.arm_frame`: the Quest
  page, once its 3D arm is lined up on the real one). To avoid any jump, the clutch engages only
  with the hand within `capture_m` of the gripper ("grab it"); that small offset is kept. Nothing
  slips: an unreachable hand leaves the arm as close as it gets, and it follows again as soon as
  the hand comes back. Orientation stays relative (pitch → tilt, roll → wrist_roll, degree for
  degree). Without arm positions or kinematics it falls back to relative.
- Gentle ramps: the joint furthest from its target moves at most `max_deg_per_s * speed_scale`;
  the others are slowed by the same factor, so all arrive together and the gripper moves along the
  line the hand drew (the gripper itself ramps on its own).
- Tilt-for-rotation (kept from the glove): controller pitch → wrist_flex, roll → wrist_roll.
  Measured in the room's axes (left-right = pitch, forward = roll), so pitching a tilted
  controller doesn't leak into roll. Angles are unwrapped frame to frame: rolling past 180° keeps
  counting (then the soft limit holds the joint) instead of jumping to the other end.
- Trigger → gripper (0 = open, fully pressed = closed).
- Soft limits: targets stay `limit_margin_deg` inside the arm's joint limits, so the driver never
  has to clamp. At a limit the clutch "slips": moving the hand further does nothing, and moving it
  back moves the arm back immediately (no wind-up, no jump on the next grab).

- IK only: the table. The gripper and the wrist stay `floor_m` above the base's bottom (z = 0); a
  target below that slips like a limit, and a step that would dip goes as far as it can (the arm
  used to stretch out into the table: docs/dev/GOTCHAS.md, 2026-11-10).

Joint limits and the floor don't prevent every self-collision (e.g. the gripper hitting the
base); that needs a collision model.
"""

import math
from dataclasses import dataclass, field

from lab_os.kinematics import IK_JOINTS, Kinematics, solve_ik
from lab_os.robots.base import JointLimit
from lab_os.teleop.messages import ControllerState, Quat, Vec3


@dataclass
class MappingConfig:
    hand: str = "right"
    mode: str = "relative"  # or "one_to_one" (MODES)
    capture_m: float = 0.08  # 1:1: the clutch engages only with the hand this close to the gripper
    grip_on: float = 0.6  # hysteresis: engage above this...
    grip_off: float = 0.4  # ...release below this
    deg_per_m: float = 200.0  # joint space: 10 cm of hand motion → 20° of joint motion
    tip_m_per_hand_m: float = 0.5  # IK: 10 cm of hand motion → 5 cm of gripper motion
    slip_m: float = 0.002  # IK: a target further than this from what the arm reached slips
    # (IK: the direction of wrist_roll for a hand roll is the arm's `Kinematics.roll_sign`.)
    max_deg_per_s: float = 90.0  # ramp limit at speed_scale = 1
    # Trigger released = fully open, pressed = closed: the ends of the arm's gripper limit (inside
    # the soft margin). These two are only used for an arm without a gripper limit.
    gripper_open: float = 60.0
    gripper_closed: float = 0.0
    limit_margin_deg: float = 3.0  # stay this far inside each joint limit
    floor_m: float = 0.01  # IK: gripper and wrist at least this high above the base's bottom
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


MODES = ("relative", "one_to_one")

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
    _floor: float = 0.0
    # 1:1: whether this grab follows the hand absolutely, the hand→gripper offset kept at engage,
    # and (while not engaged) how far the hand is from the gripper point, for the pages
    absolute: bool = False
    _offset: Vec3 = (0.0, 0.0, 0.0)
    hand_gap_m: float | None = None

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
        arm_frame: bool = False,
        one_to_one_deg_per_s: float | None = None,
    ) -> dict[str, float] | None:
        """Return joint targets for this tick, or None when the arm should hold still.
        `arm_frame`: the controller's position is measured from the arm's base (1:1 possible).
        `one_to_one_deg_per_s`: a 1:1 grab's top joint speed (the venue's; inf = no cap) instead
        of `max_deg_per_s` × speed_scale, so the arm keeps up with the hand."""
        cfg = self.config
        if controller is None or not controller.tracked:
            self.engaged = False  # tracking lost = clutch released
            self.hand_gap_m = None
            return None
        one_to_one = cfg.mode == "one_to_one" and self.kinematics is not None and arm_frame
        if one_to_one and not self.engaged:
            tip = self.kinematics.fk(arm_joints)[0]
            self.hand_gap_m = math.dist(tip, self._hand_in_arm(controller.pos))
        elif not one_to_one:
            self.hand_gap_m = None

        if self.needs_release:
            if controller.grip < cfg.grip_off:
                self.needs_release = False
            return None

        if (
            not self.engaged
            and controller.grip > cfg.grip_on
            and not (one_to_one and self.hand_gap_m > cfg.capture_m)  # 1:1: grab the gripper
        ):
            self.engaged = True
            self.absolute = one_to_one
            self._anchor_pos = controller.pos
            self._anchor_quat = controller.quat
            self._twist = {0: 0.0, 2: 0.0}
            self._anchor_joints = dict(arm_joints)
            self._commanded = dict(arm_joints)
            self._bounds = soft_bounds(limits or {}, arm_joints, cfg.limit_margin_deg)
            if self.kinematics:
                self._anchor_tip, self._anchor_angle = self.kinematics.fk(arm_joints)
                self._ik_seed = dict(arm_joints)
                # like the limits: an arm already lower may stay there or come up, never go lower
                self._floor = min(cfg.floor_m, self._lowest(arm_joints))
                if one_to_one:
                    hand = self._hand_in_arm(controller.pos)
                    self._offset = tuple(t - h for t, h in zip(self._anchor_tip, hand, strict=True))
                    self.hand_gap_m = None
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
        if self.absolute and one_to_one_deg_per_s is not None:
            fast = one_to_one_deg_per_s
            max_step = math.inf if math.isinf(fast) else fast * dt
        else:
            max_step = cfg.max_deg_per_s * min(max(speed_scale, 0.0), 1.0) * dt
        deltas = {j: t - self._commanded.get(j, t) for j, t in desired.items()}
        arm = [abs(d) for j, d in deltas.items() if j != "gripper"]
        k = min(1.0, max_step / max(arm)) if arm and max(arm) > 0 else 1.0
        for joint, delta in deltas.items():
            if joint == "gripper":
                delta = min(max(delta, -max_step), max_step)
            else:
                delta *= k  # all arm joints slowed together: they arrive at the same time
            self._commanded[joint] = self._commanded.get(joint, desired[joint]) + delta
        return {j: self._commanded[j] for j in desired}

    def _above_floor(self, start: dict[str, float], end: dict[str, float]) -> dict[str, float]:
        """The furthest point from `start` toward `end` (in joint space) that stays above the
        floor; `start` itself if none does."""
        lo, hi = 0.0, 1.0
        for _ in range(8):  # 8 halvings: within 0.4 % of the way
            mid = (lo + hi) / 2
            q = {j: start[j] + (end[j] - start[j]) * mid for j in end}
            if self._lowest(q) >= self._floor - 0.001:
                lo = mid
            else:
                hi = mid
        return {j: start[j] + (end[j] - start[j]) * lo for j in end}

    def _lowest(self, joints: dict[str, float]) -> float:
        """Height of the lowest of the wrist and the gripper point (m above the base's bottom)."""
        frames = getattr(self.kinematics, "frames", None)
        if frames is None:
            return self.kinematics.fk(joints)[0][2]
        f = frames(joints)
        return min(f[n][0][2] for n in ("wrist_flex", "tip") if n in f)

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

    @staticmethod
    def _hand_in_arm(pos: Vec3) -> Vec3:
        """A position from the page in the arm's axes. WebXR → arm axes: hand forward (−z) = arm
        +x, hand left (−x) = arm +y, up (+y) = +z."""
        px, py, pz = pos
        return (-pz, -px, py)

    def _desired_ik(self, pos: Vec3, dpos: Vec3, pitch: float) -> dict[str, float]:
        """IK joints for the anchor gripper pose moved by the hand (relative), or for where the
        hand is plus the grab's offset (1:1)."""
        cfg, kin = self.config, self.kinematics
        if self.absolute:
            hand = self._hand_in_arm(pos)
            x, y, z = (h + o for h, o in zip(hand, self._offset, strict=True))
        else:
            s = cfg.tip_m_per_hand_m
            move = (d * s for d in self._hand_in_arm(dpos))
            x, y, z = (a + d for a, d in zip(self._anchor_tip, move, strict=True))
        target = (x, y, max(z, self._floor))
        angle = self._anchor_angle - pitch  # nose up → the gripper tilts back/up
        bounds = {j: JointLimit(*self._bounds[j]) for j in IK_JOINTS if j in self._bounds}
        q = solve_ik(kin, self._ik_seed, target, angle, bounds)
        if self._lowest(q) < self._floor - 0.001:
            q = self._above_floor(self._ik_seed, q)  # e.g. the wrist would dip: go as far as it can
        self._ik_seed = q
        reached, reached_angle = kin.fk(q)
        # Slip: an unreachable target moves the anchor instead, so moving the hand back moves the
        # arm back straight away.
        miss = [r - t for r, t in zip(reached, (x, y, z), strict=True)]  # the floor slips too
        if not self.absolute and math.sqrt(sum(m * m for m in miss)) > cfg.slip_m:
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
            desired = self._desired_ik(c.pos, (dx, dy, dz), self._unwrapped(rel, 0))
            roll = self.kinematics.roll_sign * self._unwrapped(rel, 2)
            desired["wrist_roll"] = a.get("wrist_roll", 0.0) + roll
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
