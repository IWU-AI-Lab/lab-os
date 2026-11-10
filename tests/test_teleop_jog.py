"""Joint jogging (keyboard/mouse desktop modes): no IK, one motor per key, limits respected."""

import pytest

from lab_os.kinematics import XArmKinematics
from lab_os.robots.fake import FakeArm
from lab_os.robots.xarm import XArm, load_limits
from lab_os.teleop.jog import JogMapper
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.teleop.mapping import ClutchMapper
from lab_os.teleop.messages import parse_frame, parse_joint_frame

DT = 0.02


def jog_msg(**rates):
    return parse_joint_frame({"type": "joint_input", "t": 0, "rates": rates})


def xarm_loop():
    x = XArm(limits=load_limits("not-calibrated"))  # defaults, not calibration/ on disk
    arm = FakeArm(
        name="fake-xarm1", model=x.model, limits=x.limits, joints={j: 0.0 for j in x.joint_names}
    )
    arm.connect()
    # The arm has kinematics, so pose input would use IK; joint input must not.
    return TeleopLoop(
        arm=arm, inputs=InputState(), mapper=ClutchMapper(kinematics=XArmKinematics())
    )


def run(loop, frame, ticks, t0=0.0):
    for i in range(ticks):
        now = t0 + i * DT
        loop.inputs.update(frame, now)
        loop.step(now, DT)
    return t0 + ticks * DT


def test_one_key_moves_only_its_motor():
    loop = xarm_loop()
    t = run(loop, jog_msg(), 2)  # all released first (fresh start needs a release)
    run(loop, jog_msg(wrist_flex=1.0), 50, t)  # 1 s at full jog speed
    joints = loop.arm.read_joints()
    assert joints["wrist_flex"] == pytest.approx(60.0 * loop.speed_scale, abs=1.0)
    assert all(joints[j] == 0.0 for j in joints if j != "wrist_flex")  # no IK: nothing else moves


def test_negative_rate_moves_the_other_way_and_stops_at_the_soft_limit():
    loop = xarm_loop()
    t = run(loop, jog_msg(), 2)
    run(loop, jog_msg(shoulder_pan=-1.0), 500, t)  # long enough to hit the limit
    low = loop.arm.limits["shoulder_pan"].low
    assert loop.arm.read_joints()["shoulder_pan"] == pytest.approx(low + 3.0)  # 3° margin


def test_release_holds_and_unknown_joints_are_ignored():
    loop = xarm_loop()
    t = run(loop, jog_msg(), 2)
    t = run(loop, jog_msg(elbow_flex=0.5), 10, t)
    held = loop.arm.read_joints()["elbow_flex"]
    run(loop, jog_msg(not_a_joint=1.0), 20, t)  # e.g. a key for a joint this arm doesn't have
    assert loop.arm.read_joints()["elbow_flex"] == held


def test_after_a_freeze_keys_must_be_released_first():
    loop = xarm_loop()
    t = run(loop, jog_msg(), 2)
    t = run(loop, jog_msg(gripper=1.0), 10, t)
    loop.stop()
    before = loop.arm.read_joints()["gripper"]
    t = run(loop, jog_msg(gripper=1.0), 10, t)  # still held after STOP: ignored
    assert loop.arm.read_joints()["gripper"] == before
    t = run(loop, jog_msg(), 1, t)
    run(loop, jog_msg(gripper=1.0), 10, t)
    assert loop.arm.read_joints()["gripper"] > before


def test_switching_input_kind_freezes_and_starts_clean():
    loop = xarm_loop()
    t = run(loop, jog_msg(), 2)
    t = run(loop, jog_msg(wrist_roll=1.0), 5, t)
    pose = parse_frame(
        {
            "type": "xr_input",
            "t": 0,
            "hands": {"right": {"pos": [0, 1, 0], "quat": [0, 0, 0, 1], "grip": 1.0}},
        }
    )
    run(loop, pose, 1, t)
    assert loop.frozen and loop.input_kind == "pose"


def test_bad_rates_are_rejected():
    with pytest.raises(ValueError):
        parse_joint_frame({"type": "joint_input", "rates": {"gripper": 3}})


def test_jog_mapper_keeps_its_own_target_between_presses():
    """The xArm reports late; a new press must continue from the last command, not the reading."""
    m = JogMapper()
    lagging = {"wrist_roll": 0.0}
    m.step({"wrist_roll": 1.0}, lagging, DT, 1.0)
    for _ in range(9):
        out = m.step({"wrist_roll": 1.0}, lagging, DT, 1.0)
    m.step({}, lagging, DT, 1.0)  # released; the reading still says 0
    again = m.step({"wrist_roll": 1.0}, lagging, DT, 1.0)
    assert again["wrist_roll"] > out["wrist_roll"]


def test_terminal_status_line_handles_joint_input():
    from lab_os.teleop.cli import _fmt_status

    loop = xarm_loop()
    run(loop, jog_msg(gripper=0.5), 1)
    assert "gripper +0.50" in _fmt_status(loop)


def test_jogging_from_outside_the_limits_never_jumps():
    """Real-arm bug 2026-10-29: base at +116° with a 72° limit jumped to 72° on the first key."""
    loop = xarm_loop()
    loop.arm.joints["shoulder_pan"] = 116.6  # outside the (default) limit
    t = run(loop, jog_msg(), 2)
    run(loop, jog_msg(shoulder_pan=-1.0), 1, t)  # one tick toward the middle
    after = loop.arm.read_joints()["shoulder_pan"]
    assert 115.0 < after < 116.6  # moved a fraction of a degree, no jump
    run(loop, jog_msg(shoulder_pan=1.0), 50, t + 0.1)  # outward: never past where it was
    assert loop.arm.read_joints()["shoulder_pan"] <= 116.6


def test_engaging_a_pose_input_outside_the_limits_does_not_move():
    from lab_os.teleop.mapping import ClutchMapper
    from lab_os.teleop.messages import ControllerState

    arm_joints = {
        "shoulder_pan": 116.6,
        "shoulder_lift": 0.0,
        "elbow_flex": 0.0,
        "wrist_flex": 0.0,
        "wrist_roll": -116.4,
        "gripper": 30.0,
    }
    c = ControllerState((0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0), 0.0, 1.0, {}, (0.0, 0.0))
    out = ClutchMapper(config=ClutchMapper().config).step(
        c, arm_joints, DT, 1.0, load_limits("not-calibrated")
    )
    assert out["shoulder_pan"] == 116.6 and out["wrist_roll"] == -116.4


class _Tty:
    def __init__(self, tty=True):
        self.tty, self.text = tty, ""

    def isatty(self):
        return self.tty

    def write(self, s):
        self.text += s

    def flush(self):
        pass


def test_the_status_line_is_drawn_only_when_it_changes(monkeypatch):
    """A wrapped line can't be redrawn in place, so it's cut to the terminal's width; an unchanged
    line isn't drawn again; a log file (not a terminal) gets nothing."""
    import os

    from lab_os.teleop import cli

    monkeypatch.setattr(cli.shutil, "get_terminal_size", lambda: os.terminal_size((30, 20)))
    now = [0.0]
    monkeypatch.setattr(cli.time, "monotonic", lambda: now[0])
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState())
    out = _Tty()
    tick = cli._make_printer(out)
    for _ in range(5):
        now[0] += 1
        tick(loop)
    assert out.text.count("\r") == 1
    assert all(len(line) <= 29 for line in out.text.replace("\033[K", "").split("\r"))
    log_file = _Tty(tty=False)
    cli._make_printer(log_file)(loop)
    assert log_file.text == ""


def test_lab_os_serve_has_no_status_line_unless_asked(monkeypatch):
    from lab_os import cli

    made = []

    def stop_before_the_arm(args):
        made.append(args.quiet)
        raise SystemExit("stop")

    monkeypatch.setattr(cli, "make_loop", stop_before_the_arm)
    for argv in (["serve"], ["serve", "--status-line"]):
        with pytest.raises(SystemExit):
            cli.main(argv)
    assert made == [True, False]
