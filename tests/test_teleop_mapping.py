import math

import pytest

from lab_os.robots.base import JointLimit
from lab_os.teleop.mapping import ClutchMapper, MappingConfig
from lab_os.teleop.messages import ControllerState

DT = 0.02  # 50 Hz
JOINTS = {
    "shoulder_pan": 10.0,
    "shoulder_lift": -5.0,
    "elbow_flex": 20.0,
    "wrist_flex": 0.0,
    "wrist_roll": 0.0,
    "gripper": 60.0,
}


def ctrl(pos=(0.0, 1.0, 0.0), grip=0.0, trigger=0.0, roll_deg=0.0, tracked=True):
    r = math.radians(roll_deg) / 2
    return ControllerState(
        pos=pos if tracked else None,
        quat=(0.0, 0.0, math.sin(r), math.cos(r)) if tracked else None,
        trigger=trigger,
        grip=grip,
        buttons={"a": False, "b": False, "thumbstick": False},
        thumbstick=(0.0, 0.0),
    )


def run(mapper, c, joints, ticks, speed=1.0):
    out = None
    for _ in range(ticks):
        out = mapper.step(c, joints, DT, speed) or out
        if out:
            joints = joints | out
    return joints


def test_no_grip_no_motion():
    assert ClutchMapper().step(ctrl(grip=0.0), JOINTS, DT, 1.0) is None


def test_engage_starts_from_current_pose_no_snap():
    out = ClutchMapper().step(ctrl(grip=1.0), JOINTS, DT, 1.0)
    assert out == JOINTS  # hand hasn't moved since engaging → arm stays exactly where it is


def test_relative_motion_maps_to_joints():
    m = ClutchMapper()
    m.step(ctrl(grip=1.0), JOINTS, DT, 1.0)
    moved = ctrl(pos=(0.1, 1.1, -0.1), grip=1.0, roll_deg=30)
    joints = run(m, moved, JOINTS, ticks=200)
    assert joints["shoulder_pan"] == pytest.approx(10.0 + 20.0)  # right
    assert joints["shoulder_lift"] == pytest.approx(-5.0 - 20.0)  # up (SO-101: -lift raises)
    assert joints["elbow_flex"] == pytest.approx(20.0 - 20.0)  # forward (elbow opens)
    assert joints["wrist_roll"] == pytest.approx(30.0, abs=0.01)


def test_ramp_limits_each_step():
    cfg = MappingConfig(max_deg_per_s=90.0)
    m = ClutchMapper(cfg)
    m.step(ctrl(grip=1.0), JOINTS, DT, 0.5)
    out = m.step(ctrl(pos=(1.0, 1.0, 0.0), grip=1.0), JOINTS, DT, speed_scale=0.5)
    assert abs(out["shoulder_pan"] - JOINTS["shoulder_pan"]) == pytest.approx(90 * 0.5 * DT)


def test_release_freezes_and_reengage_does_not_jump():
    m = ClutchMapper()
    m.step(ctrl(grip=1.0), JOINTS, DT, 1.0)
    joints = run(m, ctrl(pos=(0.1, 1.0, 0.0), grip=1.0), JOINTS, ticks=100)
    assert m.step(ctrl(pos=(0.1, 1.0, 0.0), grip=0.0), joints, DT, 1.0) is None
    # Hand moves far away while released, then grips again: arm must not jump.
    out = m.step(ctrl(pos=(-0.5, 1.0, 0.0), grip=1.0), joints, DT, 1.0)
    assert out == joints


def test_grip_hysteresis():
    m = ClutchMapper()
    m.step(ctrl(grip=0.7), JOINTS, DT, 1.0)
    assert m.engaged
    m.step(ctrl(grip=0.5), JOINTS, DT, 1.0)
    assert m.engaged  # between grip_off and grip_on: stays engaged
    m.step(ctrl(grip=0.3), JOINTS, DT, 1.0)
    assert not m.engaged


def test_trigger_closes_gripper():
    m = ClutchMapper()
    m.step(ctrl(grip=1.0), JOINTS, DT, 1.0)
    joints = run(m, ctrl(grip=1.0, trigger=1.0), JOINTS, ticks=100)
    assert joints["gripper"] == pytest.approx(0.0)


def test_tracking_lost_releases():
    m = ClutchMapper()
    m.step(ctrl(grip=1.0), JOINTS, DT, 1.0)
    assert m.step(ctrl(grip=1.0, tracked=False), JOINTS, DT, 1.0) is None
    assert not m.engaged


def test_after_reset_grip_must_be_released_first():
    m = ClutchMapper()
    m.step(ctrl(grip=1.0), JOINTS, DT, 1.0)
    m.reset()
    assert m.step(ctrl(grip=1.0), JOINTS, DT, 1.0) is None  # still held: ignored
    m.step(ctrl(grip=0.0), JOINTS, DT, 1.0)
    assert m.step(ctrl(grip=1.0), JOINTS, DT, 1.0) == JOINTS


LIMITS = {j: JointLimit(-100.0, 100.0) for j in JOINTS}


def test_limit_slip_no_windup():
    """Push far past a limit, then move back a little: the arm follows back immediately."""
    m = ClutchMapper()
    start = JOINTS | {"shoulder_pan": 0.0}
    m.step(ctrl(grip=1.0), start, DT, 1.0, LIMITS)
    joints = run_l(m, ctrl(pos=(-1.0, 1.0, 0.0), grip=1.0), start, ticks=300)  # 200° asked
    assert joints["shoulder_pan"] == pytest.approx(-97.0)  # held 3° inside the limit
    joints = run_l(m, ctrl(pos=(-0.95, 1.0, 0.0), grip=1.0), joints, ticks=100)  # back 5 cm
    assert joints["shoulder_pan"] == pytest.approx(-87.0)  # moved back 10° right away


def test_regrab_after_limit_does_not_jump():
    m = ClutchMapper()
    m.step(ctrl(grip=1.0), JOINTS, DT, 1.0, LIMITS)
    joints = run_l(m, ctrl(pos=(-1.0, 1.0, 0.0), grip=1.0), JOINTS, ticks=300)
    m.step(ctrl(pos=(-1.0, 1.0, 0.0), grip=0.0), joints, DT, 1.0, LIMITS)
    assert m.step(ctrl(pos=(-1.0, 1.0, 0.0), grip=1.0), joints, DT, 1.0, LIMITS) == joints


def test_engaging_outside_soft_range_does_not_move():
    m = ClutchMapper()
    near_limit = JOINTS | {"shoulder_pan": 99.5}  # inside the hard limit, outside the margin
    assert m.step(ctrl(grip=1.0), near_limit, DT, 1.0, LIMITS) == near_limit


def run_l(mapper, c, joints, ticks):
    for _ in range(ticks):
        out = mapper.step(c, joints, DT, 1.0, LIMITS)
        if out:
            joints = joints | out
    return joints


def _quat(axis, deg):
    s = math.sin(math.radians(deg) / 2)
    return (*(a * s for a in axis), math.cos(math.radians(deg) / 2))


def _qmul(a, b):
    return (
        a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1],
        a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
        a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3],
        a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2],
    )


def with_quat(q):
    return ControllerState((0.0, 1.0, 0.0), q, 0.0, 1.0, {}, (0.0, 0.0))


WIDE_LIMITS = {j: JointLimit(-120.0, 120.0) for j in JOINTS} | {"gripper": JointLimit(0.0, 90.0)}


def test_rolling_past_180_never_spins_the_wrist_around():
    m = ClutchMapper()
    joints = dict(JOINTS)
    seen = []
    for roll in [*range(0, 400, 5), *range(400, 300, -5)]:  # roll far past 180, then back a bit
        for _ in range(3):
            out = m.step(ctrl(grip=1.0, roll_deg=roll), joints, DT, 1.0, WIDE_LIMITS)
            joints = joints | (out or {})
        seen.append(joints["wrist_roll"])
    steps = [abs(b - a) for a, b in zip(seen, seen[1:], strict=False)]
    assert max(steps) < 10  # no jump to the other end
    assert max(seen) <= 120
    assert seen[-1] < max(seen)  # rolling back moves it back straight away (no wind-up)


def test_pitching_a_tilted_controller_only_moves_wrist_flex():
    held = _qmul(_quat((0, 1, 0), 40), _quat((1, 0, 0), -30))  # yawed + pitched, like the emulator
    m = ClutchMapper()
    joints = run(m, with_quat(held), dict(JOINTS), 2)
    joints = run(m, with_quat(_qmul(_quat((1, 0, 0), 30), held)), joints, 50)  # +30 about room x
    assert joints["wrist_flex"] == pytest.approx(-30.0, abs=0.1)
    assert joints["wrist_roll"] == pytest.approx(0.0, abs=0.1)
