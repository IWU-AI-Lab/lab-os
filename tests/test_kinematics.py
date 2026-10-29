"""xArm kinematics + IK teleop: the gripper must move the way the hand moves (no hardware)."""

import math

import pytest

from lab_os.kinematics import IK_JOINTS, XArmKinematics, kinematics_for, solve_ik
from lab_os.robots.base import JointLimit
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
HAND = (0.0, 1.0, -0.3)


def test_upright_is_straight_up():
    tip, angle = KIN.fk({})
    assert tip == pytest.approx((0.0, 0.0, 0.065 + 0.101 + 0.095 + 0.145))
    assert angle == 0.0


def test_conventions_match_the_3d_model():
    (x, _, _), _ = KIN.fk({"shoulder_lift": 30.0})
    assert x > 0  # +lift tilts forward (+x)
    (_, y, _), _ = KIN.fk({"shoulder_pan": 30.0, "shoulder_lift": 30.0})
    assert y < 0  # +pan swings to the arm's right (−y)


def test_ik_round_trip():
    tip, angle = KIN.fk(REACHING)
    seed = REACHING | {"shoulder_lift": 25.0, "elbow_flex": 45.0}
    q = solve_ik(KIN, seed, tip, angle)
    got, got_angle = KIN.fk(q)
    assert math.dist(got, tip) < 1e-4
    assert got_angle == pytest.approx(angle, abs=0.01)


def test_unreachable_target_never_swings_the_base():
    bounds = dict.fromkeys(IK_JOINTS, JointLimit(-117, 117))
    q = dict(REACHING)
    for _ in range(100):
        q = solve_ik(KIN, q, (0.9, 0.0, 0.1), 90.0, bounds)
    assert abs(q["shoulder_pan"]) < 1.0
    assert KIN.fk(q)[0][0] > KIN.fk(REACHING)[0][0]  # stretched toward it


def hand(pos=HAND, pitch_deg=0.0, grip=1.0):
    s = math.sin(math.radians(pitch_deg) / 2)
    return ControllerState(
        pos, (s, 0.0, 0.0, math.cos(math.radians(pitch_deg) / 2)), 0.0, grip, {}, (0.0, 0.0)
    )


def drive(c_end, start=REACHING, ticks=200):
    """Engage at HAND, move the hand to c_end, return (start gripper pose, end gripper pose)."""
    m = ClutchMapper(kinematics=KIN)
    joints = dict(start)
    m.step(hand(), joints, 0.02, 1.0, LIMITS)
    for _ in range(ticks):
        joints = joints | (m.step(c_end, joints, 0.02, 1.0, LIMITS) or {})
    return KIN.fk(start), KIN.fk(joints), joints


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
def test_gripper_follows_the_hand(move, axis, sign):
    end = tuple(h + d for h, d in zip(HAND, move, strict=True))
    (tip0, angle0), (tip1, angle1), _ = drive(hand(end))
    delta = [b - a for a, b in zip(tip0, tip1, strict=True)]
    assert sign * delta[axis] == pytest.approx(0.03, abs=0.002)  # 6 cm hand → 3 cm gripper
    for other in {0, 1, 2} - {axis}:
        assert abs(delta[other]) < 0.002  # and only along that axis
    assert angle1 == pytest.approx(angle0, abs=1.0)  # tilt kept


def test_nose_up_tilts_the_gripper_up():
    (tip0, angle0), (tip1, angle1), _ = drive(hand(pitch_deg=20.0))
    assert angle1 == pytest.approx(angle0 - 20.0, abs=0.5)
    assert math.dist(tip0, tip1) < 0.002  # the gripper point stays put


def test_reach_limit_slips_without_windup():
    far = (HAND[0], HAND[1], HAND[2] - 2.0)  # 2 m forward: way out of reach
    _, (tip_far, _), joints = drive(hand(far), ticks=400)
    m_back = (HAND[0], HAND[1], HAND[2] - 1.9)  # then 10 cm back
    m = ClutchMapper(kinematics=KIN)
    # Re-run in one mapper: push out, then come back a little.
    j = dict(REACHING)
    m.step(hand(), j, 0.02, 1.0, LIMITS)
    for c, n in ((hand(far), 400), (hand(m_back), 200)):
        for _ in range(n):
            j = j | (m.step(c, j, 0.02, 1.0, LIMITS) or {})
        if c.pos == far:
            out = KIN.fk(j)[0][0]
    assert KIN.fk(j)[0][0] < out - 0.03  # came back ~5 cm right away, not after 2 m


def test_upright_start_does_not_snap():
    upright = dict.fromkeys(REACHING, 0.0) | {"gripper": 30.0}
    left = (HAND[0] - 0.06, HAND[1], HAND[2])
    _, _, joints = drive(hand(left), start=upright, ticks=50)
    assert all(abs(joints[j]) < 30 for j in IK_JOINTS)  # no wild jumps from the singular pose


def test_arms_without_kinematics_use_joint_space():
    assert kinematics_for("so101") is None
    assert kinematics_for("xarm1s") is KIN or isinstance(kinematics_for("xarm1s"), XArmKinematics)
