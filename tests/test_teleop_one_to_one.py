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
    loop = TeleopLoop(
        arm=arm,
        inputs=InputState(),
        mapper=ClutchMapper(kinematics=KIN),
        one_to_one_deg_per_s=180.0,  # the lab venue's
    )
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


# ---------- speed: 1:1 keeps up with the hand, up to the venue's cap (2026-11-11) ----------


def ticks_to_reach(m, goal, joints, cap, speed_scale=0.5, limit=400):
    """Ticks until the gripper is within 3 mm of a hand that jumped to `goal`."""
    for n in range(1, limit + 1):
        out = m.step(hand(goal), joints, DT, speed_scale, LIMITS, True, one_to_one_deg_per_s=cap)
        joints = joints | (out or {})
        if math.dist(tip(joints), goal) < 0.003:
            return n
    return limit


def test_one_to_one_is_not_slowed_by_the_speed_setting():
    start = dict(SO101_HOME)
    t0 = tip(start)
    goal = add(t0, (0.0, 0.10, 0.0))  # 10 cm to the left, at once
    times = {}
    for cap, scale in [(180.0, 0.05), (180.0, 1.0), (45.0, 1.0), (math.inf, 0.05)]:
        m = mapper()
        joints = follow(m, [t0], start, ticks_per_point=1)
        times[(cap, scale)] = ticks_to_reach(m, goal, joints, cap, speed_scale=scale)
    assert times[(180.0, 0.05)] == times[(180.0, 1.0)]  # the slider doesn't matter in 1:1
    assert times[(180.0, 1.0)] * 3 < times[(45.0, 1.0)]  # today's lab speed was ~45°/s
    assert times[(math.inf, 0.05)] <= 2  # no cap: there by the next tick


def test_a_wave_is_followed_at_the_hands_speed():
    """A quick wave, 1.5 Hz and 10 cm side to side (the base turns up to ~110°/s): with 180°/s
    the gripper keeps the whole swing; with the old ~45°/s it gets well under half of it."""
    start = dict(SO101_HOME)
    t0 = tip(start)

    def swing(cap):
        m = mapper()
        joints = follow(m, [t0], start, ticks_per_point=1)
        ys, lag = [], 0.0
        for i in range(150):  # 3 s at 50 Hz
            p = add(t0, (0.0, 0.05 * math.sin(2 * math.pi * 1.5 * i * DT), 0.0))
            out = m.step(hand(p), joints, DT, 0.5, LIMITS, True, one_to_one_deg_per_s=cap)
            joints = joints | (out or {})
            if i >= 50:  # after the first second
                ys.append(tip(joints)[1] - t0[1])
                lag = max(lag, math.dist(tip(joints), p))
        return (max(ys) - min(ys)) / 0.10, lag

    fast, fast_lag = swing(180.0)
    slow, _ = swing(45.0)
    free, free_lag = swing(math.inf)
    assert fast > 0.9 and fast_lag < 0.02  # most of the wave, under 2 cm behind
    assert slow < 0.6
    assert free > 0.98 and free_lag < 0.002


def test_the_loop_sends_the_venues_speed_to_the_arm_while_following_1to1():
    loop, arm = make_loop()
    seen = []
    move = arm.move_joints
    arm.move_joints = lambda t, s, deg_per_s=None: (seen.append(deg_per_s), move(t, s, deg_per_s))
    loop.set_mode("one_to_one")
    loop.mapper.needs_release = False
    t0 = tip(arm.read_joints())
    for i, p in enumerate([t0] * 3 + [add(t0, (0.02, 0, 0))] * 5):
        loop.inputs.update(parse_frame(quest(p)), now=i * DT)
        loop.step(i * DT, DT)
    assert seen and set(seen) == {180.0}
    assert loop.status()["one_to_one_deg_per_s"] == 180.0


def test_a_venue_with_1to1_off_offers_relative_only():
    loop, _ = make_loop()
    loop.one_to_one_deg_per_s = 0.0
    assert loop.status()["modes"] == ["relative"]
    with pytest.raises(ValueError, match="isn't available"):
        loop.set_mode("one_to_one")
    loop.one_to_one_deg_per_s = math.inf
    assert loop.status()["one_to_one_deg_per_s"] is None  # "none": no software cap


def test_servo_health_is_logged_and_hot_servos_slow_1to1(tmp_path):
    loop, arm = make_loop()
    temps = {"elbow_flex": 41.0, "wrist_flex": 38.0}
    arm.read_health = lambda: {
        j: {"temp_c": t, "load_pct": 20.0, "volts": 12.0} for j, t in temps.items()
    }
    loop.health_log = tmp_path / "health.jsonl"
    loop.check_health(100.0)
    loop.check_health(101.0)  # not yet: every 5 s
    lines = loop.health_log.read_text().splitlines()
    assert len(lines) == 1 and '"temp_c": 41.0' in lines[0]
    assert loop.status()["servos"]["max_temp_c"] == 41.0 and not loop.status()["servos"]["hot"]
    assert loop.one_to_one_cap() == 180.0
    temps["elbow_flex"] = 61.0
    loop.check_health(106.0)
    assert loop.status()["servos"]["hot"]
    assert loop.one_to_one_cap() == loop.mapper.config.max_deg_per_s  # back to relative speed
