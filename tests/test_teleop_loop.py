from pathlib import Path

from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.teleop.messages import parse_frame
from lab_os.teleop.recording import Recorder, read_recording

DT = 0.02
SAMPLE = Path(__file__).parent / "fixtures" / "sample_clutch.jsonl"


def msg(x=0.0, grip=0.0, a=False):
    return {
        "type": "xr_input",
        "t": 0,
        "hands": {
            "right": {
                "pos": [x, 1.0, 0.0],
                "quat": [0, 0, 0, 1],
                "grip": grip,
                "trigger": 0.0,
                "buttons": {"a": a},
            }
        },
    }


def make_loop():
    arm = FakeArm()
    arm.connect()
    return TeleopLoop(arm=arm, inputs=InputState(), speed_scale=1.0), arm


def feed(loop, raw, now):
    loop.inputs.update(parse_frame(raw), now=now)
    loop.step(now, DT)


def test_follows_while_clutched():
    loop, arm = make_loop()
    feed(loop, msg(grip=1.0), now=0.0)
    for i in range(1, 100):
        feed(loop, msg(x=0.1, grip=1.0), now=i * DT)
    assert arm.read_joints()["shoulder_pan"] < -15


def test_stale_input_freezes_and_needs_new_press():
    loop, arm = make_loop()
    feed(loop, msg(grip=1.0), now=0.0)
    loop.step(1.0, DT)  # nothing new for 1 s → dead-man
    assert loop.frozen and arm.stopped
    feed(loop, msg(x=0.2, grip=1.0), now=1.1)  # data back, grip still held: stay frozen
    assert loop.frozen and arm.read_joints()["shoulder_pan"] == 0.0
    feed(loop, msg(x=0.2, grip=0.0), now=1.12)
    feed(loop, msg(x=0.2, grip=1.0), now=1.14)  # fresh press → resume from current pose
    assert not loop.frozen and not arm.stopped
    assert arm.read_joints()["shoulder_pan"] == 0.0


def test_disconnect_freezes():
    loop, arm = make_loop()
    feed(loop, msg(grip=1.0), now=0.0)
    loop.inputs.disconnect()
    loop.step(0.02, DT)
    assert loop.frozen and arm.stopped


def test_stop_button_freezes():
    loop, arm = make_loop()
    feed(loop, msg(grip=1.0), now=0.0)
    feed(loop, msg(x=0.1, grip=1.0, a=True), now=0.02)
    assert loop.frozen and arm.stopped


def test_sample_recording_replays_through_the_loop():
    """The shipped sample: arm moves while clutched, ignores the hand while released."""
    loop, arm = make_loop()
    pan_at = {}
    for dt, raw in read_recording(SAMPLE):
        if raw["type"] != "xr_input":
            continue
        feed(loop, raw, now=dt)
        pan_at[round(dt, 2)] = arm.read_joints()["shoulder_pan"]
    assert pan_at[3.5] < -15  # moved right while clutched
    assert arm.read_joints()["gripper"] < 5  # trigger closed the gripper
    assert pan_at[5.0] == pan_at[3.9]  # hand moved back while released: arm held still
    assert pan_at[7.0] > pan_at[5.0] + 15  # second clutch: moved left


def test_recorder_round_trip(tmp_path):
    path = tmp_path / "rec" / "a.jsonl"
    rec = Recorder(path)
    rec.write(msg(grip=1.0))
    rec.write({"type": "session_end"})
    rec.close()
    entries = read_recording(path)
    assert [m["type"] for _, m in entries] == ["xr_input", "session_end"]
    assert entries[0][0] <= entries[1][0]


def test_command_messages_are_exactly_what_the_driver_got():
    received = []

    class SpyArm(FakeArm):
        def move_joints(self, targets, speed_scale):
            received.append((dict(targets), speed_scale))
            super().move_joints(targets, speed_scale)

    arm = SpyArm()
    arm.connect()
    sent = []
    loop = TeleopLoop(arm=arm, inputs=InputState(), speed_scale=0.4, on_command=sent.append)
    feed(loop, msg(grip=0.0), now=0.0)
    for i in range(1, 30):
        feed(loop, msg(x=0.05, grip=1.0), now=i * DT)
    loop.inputs.disconnect()
    loop.step(1.0, DT)  # → arm_stop
    feed(loop, msg(x=0.05, grip=0.0), now=1.02)
    feed(loop, msg(x=0.05, grip=1.0), now=1.04)  # fresh press → arm_resume + command
    commands = [m for m in sent if m["type"] == "arm_command"]
    assert [(m["joints"], m["speed_scale"]) for m in commands] == received
    assert [m["seq"] for m in sent] == list(range(1, len(sent) + 1))
    kinds = [m["type"] for m in sent]
    assert kinds[-3:] == ["arm_stop", "arm_resume", "arm_command"]
    assert loop.status()["last_command"] == commands[-1]
    assert loop.status()["arm"] == {"name": "fake-arm", "model": "so101"}


def test_commands_stay_inside_soft_limits():
    loop, arm = make_loop()
    sent = []
    loop.on_command = sent.append
    loop.mapper.config.deg_per_m = 5000.0  # absurd gain: the hand asks for far beyond the limits
    feed(loop, msg(grip=1.0), now=0.0)
    for i in range(1, 200):
        feed(loop, msg(x=0.5, grip=1.0), now=i * DT)
    margin = loop.mapper.config.limit_margin_deg
    for m in sent:
        if m["type"] != "arm_command":
            continue
        for j, v in m["joints"].items():
            lim = arm.limits[j]
            assert lim.low + margin - 1e-9 <= v <= lim.high - margin + 1e-9 or j == "gripper"
        assert m["joints"] == m["driver_joints"]  # the driver never had to clamp
    assert loop.last_command["joints"]["shoulder_pan"] == arm.limits["shoulder_pan"].low + margin
