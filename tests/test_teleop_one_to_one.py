"""Teleop's 1:1 mode (decision 2026-11-10): the gripper goes where the hand is, at scale 1, so hand
and arm stay together; the relative mode drifts apart (scale ½, slips). The SO-101 model, a fake
arm, hand paths made up in code. No hardware, no headset."""

import math

import pytest

from lab_os.kinematics import so101_kinematics
from lab_os.robots.fake import SO101_HOME, FakeArm, so101_limits
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.teleop.mapping import ClutchMapper, MappingConfig
from lab_os.teleop.messages import ControllerState, parse_frame

DT = 0.02
KIN = so101_kinematics()
LIMITS = so101_limits()


def page_pos(p):
    """Where the Quest page reports a hand that is at arm point `p` (m): WebXR axes, turned with
    the arm (forward = −z, left = −x, up = +y), measured from the arm's base."""
    x, y, z = p
    return (-y, z, -x)


def hand(p, grip=1.0):
    return ControllerState(
        pos=page_pos(p),
        quat=(0.0, 0.0, 0.0, 1.0),
        trigger=0.0,
        grip=grip,
        buttons={"a": False, "b": False, "thumbstick": False},
        thumbstick=(0.0, 0.0),
    )


def tip(joints):
    return KIN.fk(joints)[0]


def mapper(mode="one_to_one"):
    return ClutchMapper(config=MappingConfig(mode=mode), kinematics=KIN)


def follow(m, path, joints, ticks_per_point=40, arm_frame=True, grip=1.0):
    """Step the mapper along hand points; the fake arm goes wherever it's told."""
    for p in path:
        for _ in range(ticks_per_point):
            out = m.step(hand(p, grip), joints, DT, 1.0, LIMITS, arm_frame=arm_frame)
            if out:
                joints = joints | out
    return joints


def add(a, b):
    return tuple(x + y for x, y in zip(a, b, strict=True))


def test_the_gripper_goes_where_the_hand_goes_at_scale_1():
    start = dict(SO101_HOME)
    t0 = tip(start)
    m = mapper()
    joints = follow(m, [t0], start, ticks_per_point=1)  # grab right at the gripper
    assert m.engaged and m.absolute
    joints = follow(m, [add(t0, (0.06, 0.0, 0.03))], joints, ticks_per_point=100)
    assert math.dist(tip(joints), add(t0, (0.06, 0.0, 0.03))) < 0.003  # 6 cm → 6 cm, not 3


def test_it_engages_only_with_the_hand_at_the_gripper_and_never_jumps():
    start = dict(SO101_HOME)
    t0 = tip(start)
    m = mapper()
    far = add(t0, (0.0, 0.0, 0.20))
    assert m.step(hand(far), start, DT, 1.0, LIMITS, arm_frame=True) is None  # grip held, 20 cm off
    assert not m.engaged and m.hand_gap_m == pytest.approx(0.20, abs=1e-6)
    near = add(t0, (0.0, 0.03, 0.04))  # 5 cm off: inside the 8 cm capture
    out = m.step(hand(near), start, DT, 1.0, LIMITS, arm_frame=True)
    arm = {j: v for j, v in out.items() if j != "gripper"}  # (the gripper follows the trigger)
    assert m.engaged and arm == {j: start[j] for j in arm}  # engaged where it is: no jump
    joints = follow(m, [add(near, (0.05, 0.0, 0.0))], start | out, ticks_per_point=100)
    # the 5 cm grab offset is kept: the gripper moved with the hand, 5 cm, keeping its distance
    assert math.dist(tip(joints), add(t0, (0.05, 0.0, 0.0))) < 0.003


def test_no_drift_out_of_reach_and_back():
    """Relative mode slips at the reach limit, so hand and arm end up apart; 1:1 doesn't."""
    start = dict(SO101_HOME)
    t0 = tip(start)
    path = [add(t0, (0.05 * i, 0.0, 0.0)) for i in range(1, 9)]  # 40 cm forward: out of reach
    path += list(reversed(path[:-1])) + [t0]  # and back to where it started
    one = follow(mapper("one_to_one"), [t0] + path, start)
    rel = follow(mapper("relative"), [t0] + path, start)
    # 1:1 is back where the hand is; relative is off by what slipped at the limit
    assert math.dist(tip(one), t0) < 0.002 < 0.005 < math.dist(tip(rel), t0)


def test_the_hand_under_the_table_keeps_the_gripper_above_it():
    start = dict(SO101_HOME)
    t0 = tip(start)
    m = mapper()
    joints = follow(m, [t0, (t0[0], t0[1], -0.10)], start, ticks_per_point=120)
    frames = KIN.frames(joints)
    assert min(frames[n][0][2] for n in ("wrist_flex", "tip")) >= m.config.floor_m - 0.002


def test_without_the_arms_position_it_falls_back_to_relative():
    start = dict(SO101_HOME)
    t0 = tip(start)
    m = mapper()
    far = add(t0, (0.0, 0.0, 0.30))  # far from the gripper: 1:1 wouldn't engage here
    out = m.step(hand(far), start, DT, 1.0, LIMITS, arm_frame=False)
    assert m.engaged and not m.absolute and out is not None
    assert m.hand_gap_m is None


def test_letting_go_and_grabbing_again_keeps_hand_and_arm_together():
    start = dict(SO101_HOME)
    t0 = tip(start)
    m = mapper()
    joints, where = follow(m, [t0], start, ticks_per_point=1), t0  # grabbed at the gripper
    for step in [(0.04, 0.02, 0.0), (0.0, -0.05, 0.03), (-0.03, 0.0, -0.02)] * 3:
        joints = follow(m, [where], joints, ticks_per_point=1)  # grab where the hand is
        where = add(where, step)
        joints = follow(m, [where], joints, ticks_per_point=80)  # move while holding
        joints = follow(m, [where], joints, ticks_per_point=2, grip=0.0)  # let go
        assert not m.engaged
        assert m.hand_gap_m < 0.005  # the gripper is still at the hand: grab again right there
    assert math.dist(tip(joints), where) < 0.005


def make_loop():
    """The teleop loop as `lab-os serve` builds it for an SO-101: with its kinematics."""
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState(), mapper=ClutchMapper(kinematics=KIN))
    loop.speed_scale = 1.0
    return loop, arm


def test_the_loop_switches_modes_and_reports_them():
    loop, _ = make_loop()
    s = loop.status()
    assert s["mode"] == "relative" and s["modes"] == ["relative", "one_to_one"]
    loop.mapper.engaged = True
    assert loop.set_mode("one_to_one") == "one_to_one"
    assert not loop.mapper.engaged and loop.mapper.needs_release  # grip again in the new mode
    with pytest.raises(ValueError):
        loop.set_mode("sideways")


def quest(p, grip=1.0):
    """An xr_input message as the Quest page sends it (positions from the 3D arm's base)."""
    right = {"pos": list(page_pos(p)), "quat": [0, 0, 0, 1], "grip": grip}
    return {"type": "xr_input", "frame": "arm", "hands": {"right": right}}


def test_the_loop_drives_one_to_one_from_quest_frames():
    loop, arm = make_loop()
    loop.set_mode("one_to_one")
    loop.mapper.needs_release = False
    t0 = tip(arm.read_joints())
    target = add(t0, (0.03, 0.02, 0.02))
    now = 0.0
    far = add(t0, (0.0, 0.0, 0.15))
    loop.inputs.update(parse_frame(quest(far)), now=now)
    loop.step(now, DT)
    s = loop.status()
    assert s["hand_gap_cm"] == pytest.approx(15.0, abs=0.1) and not s["clutch"]
    for p in [t0] + [target] * 80:
        now += DT
        loop.inputs.update(parse_frame(quest(p)), now=now)
        loop.step(now, DT)
    assert loop.status()["one_to_one"] is True
    assert math.dist(tip(arm.read_joints()), target) < 0.003


def test_an_arm_without_kinematics_offers_relative_only():
    arm = FakeArm(model="unknown")
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState(), mapper=ClutchMapper(kinematics=None))
    assert loop.status()["modes"] == ["relative"]
