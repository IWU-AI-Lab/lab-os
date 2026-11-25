"""LeRobot's own teleop for the green set (quick job 91): the command line, the read-only training
calibration (a temporary copy), the checks (one program per port), the calibration question that is
never answered, and Stop like Ctrl+C. Fake folders and fake programs; no LeRobot, no real port."""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from lab_os import lerobot_teleop as lt
from lab_os.devices import Device, Registry

FOLLOWER = "usb-1a86_USB_Single_Serial_5B41533501-if00"
LEADER = "usb-1a86_USB_Single_Serial_5B41531599-if00"


def world(tmp_path, plugged=True, files=True):
    """A registry with the green pair (ports in a fake by-id folder), the training files in a fake
    LeRobot cache, an empty /proc and an empty /dev/v4l/by-path."""
    by_id, root, proc, by_path = (tmp_path / d for d in ("by-id", "calibration", "proc", "v4l"))
    for d in (by_id, root / "robots/so_follower", root / "teleoperators/so_leader", proc, by_path):
        d.mkdir(parents=True)
    if plugged:
        for name in (FOLLOWER, LEADER):
            (by_id / name).touch()
    if files:
        (root / "robots/so_follower/sheep.json").write_text(json.dumps({"shoulder_pan": {"id": 1}}))
        (root / "teleoperators/so_leader/shepherd.json").write_text(json.dumps({"x": 2}))
    reg = Registry(
        devices={
            "so101-green": Device(
                name="so101-green",
                kind="so101",
                ports=(str(by_id / FOLLOWER),),
                borrowed=True,
                training_calibration="robots/so_follower/sheep.json",
            ),
            "so101-green-leader": Device(
                name="so101-green-leader",
                kind="so101-leader",
                ports=(str(by_id / LEADER),),
                borrowed=True,
                training_calibration="teleoperators/so_leader/shepherd.json",
            ),
        }
    )
    return {
        "registry": reg,
        "root": root,
        "proc": proc,
        "by_path": str(by_path) + "/",
        "is_installed": lambda: True,
    }


@pytest.fixture(autouse=True)
def lelab_not_running(monkeypatch):
    monkeypatch.setattr(lt, "_answers", lambda port: False)


def test_all_fine(tmp_path):
    c, plan = lt.check(**world(tmp_path))
    assert c.ok, c.lines
    assert plan.follower_calibration.name == "sheep.json"
    assert plan.leader_calibration.name == "shepherd.json"
    assert plan.cameras == {}  # the cameras aren't plugged in: it runs without them


def test_refusals(tmp_path, monkeypatch):
    assert not lt.check(**world(tmp_path / "a", plugged=False))[0].ok
    assert not lt.check(**world(tmp_path / "b", files=False))[0].ok
    w = world(tmp_path / "c")
    assert not lt.check(**w | {"is_installed": lambda: False})[0].ok
    c, _ = lt.check(**w, brain_uses=("so101-green",))  # lab-os itself drives the follower
    assert not c.ok and any("lab-os itself" in t for ok, t in c.lines if not ok)
    monkeypatch.setattr(lt, "_answers", lambda port: port == lt.LELAB_PORT)
    c, _ = lt.check(**w)
    assert not c.ok and any("LeLab is running" in t for ok, t in c.lines if not ok)


def test_a_port_open_in_another_program_refuses(tmp_path):
    w = world(tmp_path)
    pid = w["proc"] / "4242"
    (pid / "fd").mkdir(parents=True)
    (pid / "comm").write_text("lelab\n")
    (pid / "fd" / "3").symlink_to(w["registry"].devices["so101-green"].ports[0])
    c, _ = lt.check(**w)
    assert not c.ok
    assert any("lelab (pid 4242)" in t for ok, t in c.lines if not ok)


def test_the_brains_own_teleop_is_not_another_program(tmp_path):
    """While the brain's LeRobot teleop runs, it holds the green ports: not "another program"."""
    w = world(tmp_path)
    pid = w["proc"] / "697362"
    (pid / "fd").mkdir(parents=True)
    (pid / "comm").write_text("lerobot-teleope\n")
    (pid / "stat").write_text("697362 (lerobot-teleope) S 697360 697360 697360 0 -1\n")
    (pid / "fd" / "3").symlink_to(w["registry"].devices["so101-green"].ports[0])
    assert lt.check(**w, own_group=697360)[0].ok
    c, _ = lt.check(**w, own_group=1)  # another group: refused
    assert any("lerobot-teleope (pid 697362)" in t for ok, t in c.lines if not ok)


def test_the_command_line(tmp_path):
    """LeRobot's teleop through lab-os's so101 extra, with the training files' ids, read from a
    temporary copy: LeRobot never touches its cache. Its data view on, sent to our Rerun."""
    _, plan = lt.check(**world(tmp_path))
    plan.cameras = {"stand": "/dev/v4l/by-path/pci-0000:00:14.0-usb-0:8:1.0-video-index0"}
    copy = lt.copy_calibration(plan)
    try:
        argv = lt.command(plan, copy)
        assert argv[:5] == ["uv", "run", "--extra", "so101", "lerobot-teleoperate"]
        assert "--robot.type=so101_follower" in argv and "--teleop.type=so101_leader" in argv
        assert "--robot.id=sheep" in argv and "--teleop.id=shepherd" in argv
        assert f"--robot.port={plan.follower_port}" in argv  # by-id names only
        assert f"--teleop.port={plan.leader_port}" in argv
        assert f"--robot.calibration_dir={copy / 'robot'}" in argv
        assert f"--teleop.calibration_dir={copy / 'teleop'}" in argv
        assert "--display_data=true" in argv
        # LeRobot opens its own Rerun window, as in the builder's working command
        assert not any(a.startswith(("--display_ip", "--display_port")) for a in argv)
        cams = json.loads(
            next(a for a in argv if a.startswith("--robot.cameras=")).split("=", 1)[1]
        )
        assert cams["stand"]["fourcc"] == "MJPG"
        assert cams["stand"]["type"] == "opencv" and cams["stand"]["index_or_path"].endswith(
            "index0"
        )
        assert not any("miniforge" in a or "conda" in a for a in argv)
        # the copy has the training numbers, under their ids; the cache stays as it was
        assert (copy / "robot/sheep.json").read_bytes() == plan.follower_calibration.read_bytes()
        assert (copy / "teleop/shepherd.json").read_bytes() == plan.leader_calibration.read_bytes()
        assert not str(copy).startswith(str(tmp_path / "calibration"))
    finally:
        import shutil

        shutil.rmtree(copy)


FAKE_LEROBOT = """
import sys, time
print("connecting", flush=True)
if sys.argv[1] == "calibrate":
    print("Mismatch between calibration values in the motor and the calibration file", flush=True)
    print("Press ENTER to use provided calibration file associated with the id sheep, or type 'c'",
          flush=True)
    try:
        answer = input()
        print("ANSWERED " + answer, flush=True)  # must never happen
    except EOFError:
        print("no answer", flush=True)
    time.sleep(30)
else:
    try:
        while True:
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("disconnected: torque off", flush=True)
"""


def fake_runner(tmp_path, mode):
    script = tmp_path / "fake_lerobot.py"
    script.write_text(FAKE_LEROBOT)
    seen = {}

    def popen(argv, **kw):
        seen.update(kw)
        return subprocess.Popen([sys.executable, str(script), mode], **kw)

    return lt.Runner(popen=popen), seen


def started(tmp_path, runner):
    _, plan = lt.check(**world(tmp_path))
    runner.start(plan)


def wait_for(cond, s=10.0):
    end = time.monotonic() + s
    while time.monotonic() < end and not cond():
        time.sleep(0.05)
    return cond()


def test_the_calibration_question_is_never_answered(tmp_path):
    runner, seen = fake_runner(tmp_path, "calibrate")
    started(tmp_path, runner)
    assert seen["stdin"] == subprocess.DEVNULL  # nothing can answer it
    assert seen["start_new_session"] is True
    assert wait_for(lambda: not runner.running())  # stopped at once, not after its 30 s
    assert runner.said == lt.CALIBRATION_REFUSED
    assert not any("ANSWERED" in line for line in runner.lines)
    assert runner.tmp is None  # the temporary copy is gone


def test_stop_is_like_ctrl_c(tmp_path):
    runner, _ = fake_runner(tmp_path, "run")
    started(tmp_path, runner)
    assert wait_for(lambda: "connecting" in runner.lines)
    said = runner.stop()
    assert "limp" in said and not runner.running()
    assert wait_for(lambda: "disconnected: torque off" in runner.lines)  # it got SIGINT
    assert runner.stop() == "LeRobot's teleop isn't running."


def test_a_window_that_keeps_the_pipe_open_does_not_hide_the_end(tmp_path):
    """LeRobot's Rerun window keeps LeRobot's output pipe open after LeRobot exits: the page must
    still see that LeRobot stopped, and the temporary copy must still go."""
    script = tmp_path / "exits_but_child_stays.py"
    script.write_text(
        "import subprocess, sys\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'])\n"
        "print('Error: gone', flush=True)\n"
        "sys.exit(1)\n"
    )
    runner = lt.Runner(
        popen=lambda argv, **kw: subprocess.Popen([sys.executable, str(script)], **kw)
    )
    _, plan = lt.check(**world(tmp_path))
    runner.start(plan)
    assert wait_for(lambda: runner.said, s=5.0)
    assert runner.said == "LeRobot's teleop stopped. Error: gone"
    assert wait_for(lambda: runner.tmp is None, s=2.0)
    runner._signal(runner.proc, 15)  # the "window" too


def test_a_hack_line_for_rerun_usage_data():
    assert lt.child_env()["CI"] == "1"
    focus = (Path(__file__).resolve().parents[1] / "docs/plan/current-focus.md").read_text()
    assert "lerobot_teleop.py" in focus.split("## Hacks to clean up", 1)[1]


async def test_the_page_and_its_api(aiohttp_client, monkeypatch):
    from test_hub_server import make_app

    from lab_os.green import Check
    from lab_os.hub import server as hub_server

    calls = []
    monkeypatch.setattr(lt, "check", lambda **kw: (Check([(False, "unplugged")]), lt.Plan()))
    monkeypatch.setattr(lt.RUNNER, "start", lambda plan: calls.append(plan) or "started")
    client = await aiohttp_client(make_app())
    page = await (await client.get("/training")).text()
    assert 'id="lr-start"' in page and "<iframe" not in page and "follower goes limp" in page
    got = await (await client.get("/api/lerobot-teleop")).json()
    assert got["ok"] is False and got["running"] is False and got["here"] is True
    res = await (await client.post("/api/lerobot-teleop/start")).json()
    assert not calls and res["said"].startswith("Not started")
    monkeypatch.setattr(lt, "check", lambda **kw: (Check([(True, "fine")]), lt.Plan()))
    await client.post("/api/lerobot-teleop/start")
    assert len(calls) == 1
    monkeypatch.setattr(hub_server, "is_local", lambda request: False)  # another screen
    assert (await client.post("/api/lerobot-teleop/start")).status == 403
    assert (await client.post("/api/lerobot-teleop/stop")).status == 403
    assert len(calls) == 1
