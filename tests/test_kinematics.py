"""Arm kinematics + IK teleop: the gripper must move the way the hand moves, on the xArm and the
SO-101 (no hardware)."""

import math

import pytest

from lab_os.kinematics import (
    IK_JOINTS,
    UrdfKinematics,
    XArmKinematics,
    kinematics_for,
    so101_kinematics,
    solve_ik,
)
from lab_os.robots.base import JointLimit
from lab_os.robots.fake import so101_limits
from lab_os.robots.xarm import XArm, load_limits
from lab_os.teleop.mapping import ClutchMapper
from lab_os.teleop.messages import ControllerState

KIN = XArmKinematics()
LIMITS = XArm(limits=load_limits("not-calibrated")).limits  # defaults, not the file on disk
REACHING = {  # elbow bent, gripper tilted slightly down: a working pose with room to move
    "shoulder_pan": 0.0,
    "shoulder_lift": 0.0,
    "elbow_flex": 70.0,
    "wrist_flex": 30.0,
    "wrist_roll": 0.0,
    "gripper": 30.0,
}
SO101 = so101_kinematics()
SO101_REACHING = {  # fingertips ~26 cm out, 5 cm up, tilted down toward the table
    "shoulder_pan": 0.0,
    "shoulder_lift": -20.0,
    "elbow_flex": 40.0,
    "wrist_flex": 40.0,
    "wrist_roll": 0.0,
    "gripper": 30.0,
}
ARMS = {
    "xarm": (KIN, LIMITS, REACHING),
    "so101": (SO101, so101_limits(), SO101_REACHING),
}
HAND = (0.0, 1.0, -0.3)


@pytest.fixture(params=ARMS, ids=list(ARMS))
def arm(request):
    return ARMS[request.param]


def test_upright_is_straight_up():
    tip, angle = KIN.fk({})
    assert tip == pytest.approx((0.0, 0.0, 0.065 + 0.101 + 0.095 + 0.145))
    assert angle == 0.0


def test_conventions_match_the_3d_model():
    (x, _, _), _ = KIN.fk({"shoulder_lift": 30.0})
    assert x > 0  # +lift tilts forward (+x)
    (_, y, _), _ = KIN.fk({"shoulder_pan": 30.0, "shoulder_lift": 30.0})
    assert y < 0  # +pan swings to the arm's right (−y)


def test_so101_zero_is_an_L_facing_forward():
    tip, angle = SO101.fk({})
    assert (
        tip[0] > 0.35 and abs(tip[1]) < 0.001 and tip[2] > 0.2
    )  # out in front, at shoulder height
    assert angle == pytest.approx(90.0, abs=5.0)  # gripper pointing forward


def test_so101_conventions_match_the_xarm():
    (x0, _, z0), a0 = SO101.fk(SO101_REACHING)
    (_, y, _), _ = SO101.fk(SO101_REACHING | {"shoulder_pan": 30.0})
    assert y < 0  # +pan swings to the arm's right
    for joint in ("shoulder_lift", "elbow_flex", "wrist_flex"):
        _, a = SO101.fk(SO101_REACHING | {joint: SO101_REACHING[joint] + 10.0})
        assert a > a0  # each pitch joint tilts the gripper further forward/down


def test_so101_gripper_pointing_down_has_no_wraparound():
    angles = [SO101.fk(SO101_REACHING | {"wrist_flex": w})[1] for w in range(0, 90, 5)]
    steps = [b - a for a, b in zip(angles, angles[1:], strict=False)]
    assert all(0 < s < 10 for s in steps), angles  # smooth through 180 (straight down)


def roll_as_seen_from_behind(kin: UrdfKinematics, pose: dict, deg: float) -> float:
    """Turn of the gripper's sideways axis for +deg wrist_roll, counter-clockwise as seen by an
    operator standing behind the arm, looking along the gripper (degrees, signed)."""
    f0 = kin.frames(pose)["tip"]
    f1 = kin.frames(pose | {"wrist_roll": pose["wrist_roll"] + deg})["tip"]
    tool = [f0[1][i][2] for i in range(3)]  # gripper_frame_link's z: along the gripper
    side0 = [f0[1][i][0] for i in range(3)]
    side1 = [f1[1][i][0] for i in range(3)]
    cross = [
        side0[1] * side1[2] - side0[2] * side1[1],
        side0[2] * side1[0] - side0[0] * side1[2],
        side0[0] * side1[1] - side0[1] * side1[0],
    ]
    sin = sum(c * t for c, t in zip(cross, tool, strict=True))
    cos = sum(a * b for a, b in zip(side0, side1, strict=True))
    away = 1.0 if sum(t * d for t, d in zip(tool, (1.0, 0.0, 0.0), strict=True)) > 0 else -1.0
    # Right-hand turn about the tool axis pointing away from the operator = clockwise for them.
    return -away * math.degrees(math.atan2(sin, cos))


def test_so101_roll_sign_matches_the_urdf():
    pose = SO101_REACHING | {"wrist_flex": 0.0, "elbow_flex": 0.0, "shoulder_lift": 0.0}
    seen = roll_as_seen_from_behind(SO101, pose, 20.0)
    assert seen == pytest.approx(20.0 * SO101.roll_sign, abs=0.5)


def test_ik_round_trip(arm):
    kin, _, reaching = arm
    tip, angle = kin.fk(reaching)
    seed = reaching | {"shoulder_lift": reaching["shoulder_lift"] + 25.0, "elbow_flex": 45.0}
    q = solve_ik(kin, seed, tip, angle)
    got, got_angle = kin.fk(q)
    assert math.dist(got, tip) < 1e-4
    assert got_angle == pytest.approx(angle, abs=0.01)


def test_unreachable_target_never_swings_the_base(arm):
    kin, _, reaching = arm
    bounds = dict.fromkeys(IK_JOINTS, JointLimit(-117, 117))
    q = dict(reaching)
    for _ in range(100):
        q = solve_ik(kin, q, (0.9, 0.0, 0.1), 90.0, bounds)
    assert abs(q["shoulder_pan"]) < 1.0
    assert kin.fk(q)[0][0] > kin.fk(reaching)[0][0]  # stretched toward it


def hand(pos=HAND, pitch_deg=0.0, grip=1.0):
    s = math.sin(math.radians(pitch_deg) / 2)
    return ControllerState(
        pos, (s, 0.0, 0.0, math.cos(math.radians(pitch_deg) / 2)), 0.0, grip, {}, (0.0, 0.0)
    )


def drive(c_end, start=REACHING, ticks=200, kin=KIN, limits=LIMITS):
    """Engage at HAND, move the hand to c_end, return (start gripper pose, end gripper pose)."""
    m = ClutchMapper(kinematics=kin)
    joints = dict(start)
    m.step(hand(), joints, 0.02, 1.0, limits)
    for _ in range(ticks):
        joints = joints | (m.step(c_end, joints, 0.02, 1.0, limits) or {})
    return kin.fk(start), kin.fk(joints), joints


def drive_arm(arm, c_end, ticks=200):
    kin, limits, reaching = arm
    return drive(c_end, reaching, ticks, kin, limits)


@pytest.mark.parametrize(
    ("move", "axis", "sign"),
    [
        ((0.0, 0.0, -0.06), 0, +1),  # hand forward (−z) → gripper forward (+x)
        ((-0.06, 0.0, 0.0), 1, +1),  # hand left → gripper to the arm's left (+y)
        ((0.06, 0.0, 0.0), 1, -1),  # hand right → arm's right
        ((0.0, 0.06, 0.0), 2, +1),  # hand up → gripper up
        ((0.0, -0.06, 0.0), 2, -1),  # hand down → gripper down
    ],
)
def test_gripper_follows_the_hand(arm, move, axis, sign):
    end = tuple(h + d for h, d in zip(HAND, move, strict=True))
    (tip0, angle0), (tip1, angle1), _ = drive_arm(arm, hand(end))
    delta = [b - a for a, b in zip(tip0, tip1, strict=True)]
    assert sign * delta[axis] == pytest.approx(0.03, abs=0.002)  # 6 cm hand → 3 cm gripper
    for other in {0, 1, 2} - {axis}:
        assert abs(delta[other]) < 0.002  # and only along that axis
    assert angle1 == pytest.approx(angle0, abs=1.0)  # tilt kept


def test_nose_up_tilts_the_gripper_up(arm):
    (tip0, angle0), (tip1, angle1), _ = drive_arm(arm, hand(pitch_deg=20.0))
    assert angle1 == pytest.approx(angle0 - 20.0, abs=0.5)
    assert math.dist(tip0, tip1) < 0.002  # the gripper point stays put


def test_reach_limit_slips_without_windup(arm):
    kin, limits, reaching = arm
    far = (HAND[0], HAND[1], HAND[2] - 2.0)  # 2 m forward: way out of reach
    m_back = (HAND[0], HAND[1], HAND[2] - 1.9)  # then 10 cm back
    m = ClutchMapper(kinematics=kin)
    # One mapper: push out, then come back a little.
    j = dict(reaching)
    m.step(hand(), j, 0.02, 1.0, limits)
    for c, n in ((hand(far), 400), (hand(m_back), 200)):
        for _ in range(n):
            j = j | (m.step(c, j, 0.02, 1.0, limits) or {})
        if c.pos == far:
            out = kin.fk(j)[0][0]
    assert kin.fk(j)[0][0] < out - 0.03  # came back ~5 cm right away, not after 2 m


def test_upright_start_does_not_snap():
    upright = dict.fromkeys(REACHING, 0.0) | {"gripper": 30.0}
    left = (HAND[0] - 0.06, HAND[1], HAND[2])
    _, _, joints = drive(hand(left), start=upright, ticks=50)
    assert all(abs(joints[j]) < 30 for j in IK_JOINTS)  # no wild jumps from the singular pose


def test_both_arms_have_kinematics():
    assert isinstance(kinematics_for("xarm1s"), XArmKinematics)
    assert kinematics_for("so101") is SO101
    assert kinematics_for("something-else") is None  # → joint space


@pytest.mark.parametrize("arm_name", list(ARMS))
def test_rolling_the_hand_counter_clockwise_rolls_the_gripper_the_same_way_as_seen(arm_name):
    # WebXR: +z points back at the user, so +twist about z = counter-clockwise as the user sees it.
    s = math.sin(math.radians(20) / 2)
    ccw = ControllerState(
        HAND, (0.0, 0.0, s, math.cos(math.radians(20) / 2)), 0.0, 1.0, {}, (0.0, 0.0)
    )
    kin, _, _ = ARMS[arm_name]
    _, _, joints = drive_arm(ARMS[arm_name], ccw)
    # xArm: counter-clockwise from behind = −wrist_roll; SO-101: +wrist_roll.
    assert joints["wrist_roll"] == pytest.approx(20.0 * kin.roll_sign, abs=0.5)


def test_trigger_released_opens_the_gripper_all_the_way(arm):
    _, limits, _ = arm
    _, _, joints = drive_arm(arm, hand())  # trigger 0
    assert joints["gripper"] == pytest.approx(limits["gripper"].high - 3.0)  # open end − margin


def _lowest(joints):
    f = SO101.frames(joints)
    return min(f[n][0][2] for n in ("wrist_flex", "tip"))


def test_so101_stays_above_the_table_and_comes_back_up_at_once():
    deep = (HAND[0], HAND[1] - 1.0, HAND[2])  # hand 1 m down: the gripper would go 50 cm down
    up = (HAND[0], HAND[1] - 0.9, HAND[2])  # then 10 cm back up
    m = ClutchMapper(kinematics=SO101)
    j = dict(SO101_REACHING)
    m.step(hand(), j, 0.02, 1.0, so101_limits())
    for _ in range(300):
        j = j | (m.step(hand(deep), j, 0.02, 1.0, so101_limits()) or {})
    assert _lowest(j) >= m.config.floor_m - 0.003  # resting on the floor, not in the table
    low = SO101.fk(j)[0][2]
    for _ in range(200):
        j = j | (m.step(hand(up), j, 0.02, 1.0, so101_limits()) or {})
    assert SO101.fk(j)[0][2] > low + 0.03  # the floor slipped: up ~5 cm right away


def test_so101_far_reach_goes_as_far_as_the_table_allows():
    far = (HAND[0], HAND[1], HAND[2] - 2.0)  # 2 m forward at table height
    (tip0, _), (tip1, _), j = drive(hand(far), SO101_REACHING, 400, SO101, so101_limits())
    assert tip1[0] > tip0[0] + 0.05  # it reached out
    assert _lowest(j) >= 0.01 - 0.003  # without going into the table (it went 8.6 cm in)


def test_joints_arrive_together():
    # 6 cm forward at a low speed: the gripper should travel along the line, not joint by joint
    m = ClutchMapper(kinematics=SO101)
    j = dict(SO101_REACHING)
    m.step(hand(), j, 0.02, 0.2, so101_limits())
    end = (HAND[0], HAND[1], HAND[2] - 0.06)
    tip0 = SO101.fk(j)[0]
    path = []
    for _ in range(400):
        j = j | (m.step(hand(end), j, 0.02, 0.2, so101_limits()) or {})
        path.append(SO101.fk(j)[0])
    for p in path:
        assert abs(p[1] - tip0[1]) < 0.002  # never off to the side
        assert abs(p[2] - tip0[2]) < 0.006  # nor much up or down on the way
