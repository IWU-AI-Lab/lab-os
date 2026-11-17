"""The green launcher's check: only looks at names and LeLab's saved settings, and refuses unless
exactly the two green arms are plugged in the way LeLab expects. Fake folders, no real ports."""

import json

import pytest

from lab_os import green
from lab_os.green import check, remember


@pytest.fixture(autouse=True)
def lelab_installed(monkeypatch):
    monkeypatch.setattr(green, "_lelab", lambda: "/usr/local/bin/lelab")  # CI has no LeLab


FOLLOWER = "usb-1a86_USB_Single_Serial_5B41533501-if00"  # as in devices.yaml (CLAUDE.md)
LEADER = "usb-1a86_USB_Single_Serial_5B41531599-if00"
WHITE = "usb-1a86_USB_Single_Serial_5B41532410-if00"


def setup(tmp_path, plugged, saved=("ttyACM0", "ttyACM1")):
    """`plugged`: by-id name → fake tty name. `saved`: LeLab's (leader, follower) tty names."""
    dev, by_id, home = tmp_path / "dev", tmp_path / "by-id", tmp_path / "lerobot"
    for d in (dev, by_id, home / "ports", home / "robots"):
        d.mkdir(parents=True)
    for name, tty in plugged.items():
        (dev / tty).touch()
        (by_id / name).symlink_to(dev / tty)
    leader, follower = (str(dev / t) for t in saved)
    (home / "ports/leader_port.txt").write_text(leader + "\n")
    (home / "ports/follower_port.txt").write_text(follower)
    (home / "robots/SO-101_Green_Follower.json").write_text(
        json.dumps({"leader_port": leader, "follower_port": follower})
    )
    (tmp_path / "proc").mkdir()  # no program has anything open
    return {
        "by_id": by_id,
        "home": home,
        "last_good": tmp_path / "last.json",
        "proc": tmp_path / "proc",
    }


def test_both_greens_alone_and_saved_right_is_ok(tmp_path):
    paths = setup(tmp_path, {LEADER: "ttyACM0", FOLLOWER: "ttyACM1"})
    c = check(**paths)
    assert c.ok, c.lines
    assert (c.follower, c.leader) == ("5B41533501", "5B41531599")


def test_white_plugged_in_refuses(tmp_path):
    paths = setup(tmp_path, {LEADER: "ttyACM0", FOLLOWER: "ttyACM1", WHITE: "ttyACM2"})
    c = check(**paths)
    assert not c.ok
    assert any("so101-white" in t for ok, t in c.lines if not ok)


def test_a_green_missing_refuses(tmp_path):
    assert not check(**setup(tmp_path, {LEADER: "ttyACM0"})).ok


def test_lelab_pointing_at_another_port_refuses(tmp_path):
    # the greens came up as ACM1/ACM2 (something was plugged in before): LeLab's ACM0 is wrong
    paths = setup(tmp_path, {LEADER: "ttyACM1", FOLLOWER: "ttyACM2"}, saved=("ttyACM0", "ttyACM1"))
    c = check(**paths)
    assert not c.ok
    assert any("not a green arm" in t for ok, t in c.lines if not ok)


def test_swapped_since_last_start_refuses(tmp_path):
    paths = setup(tmp_path / "a", {LEADER: "ttyACM0", FOLLOWER: "ttyACM1"})
    remember(check(**paths), paths["last_good"])
    # plugged in the other order: LeLab's saved follower (ACM1) is now the other arm
    swapped = setup(tmp_path / "b", {LEADER: "ttyACM1", FOLLOWER: "ttyACM0"})
    c = check(**(swapped | {"last_good": paths["last_good"]}))
    assert not c.ok
    assert any("swapped" in t for ok, t in c.lines if not ok)


BRAIN = ["/home/lab/lab-os/.venv/bin/python3", "/home/lab/lab-os/.venv/bin/lab-os", "serve"]
LELAB = ["/home/lab/.local/share/uv/tools/lelab/bin/python", "/home/lab/.local/bin/lelab"]


def hold(paths, tty, program="python3", pid="4321", argv=BRAIN):
    """A program (by default the brain driving so101-green) has this fake tty open."""
    fd = paths["proc"] / pid / "fd"
    fd.mkdir(parents=True)
    (paths["proc"] / pid / "comm").write_text(program + "\n")
    (paths["proc"] / pid / "cmdline").write_bytes(b"\0".join(a.encode() for a in argv) + b"\0")
    (fd / "9").symlink_to(paths["by_id"].parent / "dev" / tty)


def test_a_green_port_open_in_another_program_refuses(tmp_path, monkeypatch):
    monkeypatch.setattr(green, "_answers", lambda port: False)  # LeLab not running
    paths = setup(tmp_path, {LEADER: "ttyACM0", FOLLOWER: "ttyACM1"})
    hold(paths, "ttyACM1")
    c = check(**paths)
    assert not c.ok
    assert any("…3501 is open in python3 (pid 4321)" in t for ok, t in c.lines if not ok)


def test_lelab_already_running_may_hold_the_ports(tmp_path, monkeypatch):
    monkeypatch.setattr(green, "_answers", lambda port: True)  # LeLab answers
    paths = setup(tmp_path, {LEADER: "ttyACM0", FOLLOWER: "ttyACM1"})
    hold(paths, "ttyACM1", program="lelab", argv=LELAB)
    c = check(**paths)
    assert c.ok and c.running, c.lines


def test_the_brain_on_a_green_port_refuses_even_while_lelab_runs(tmp_path, monkeypatch):
    # lab check 8.12: LeLab's page answered, the brain drove so101-green, and LeLab started anyway
    monkeypatch.setattr(green, "_answers", lambda port: True)
    paths = setup(tmp_path, {LEADER: "ttyACM0", FOLLOWER: "ttyACM1"})
    hold(paths, "ttyACM1", program="lab-os", pid="777")
    c = check(**paths)
    assert not c.ok
    assert any("…3501 is open in lab-os (pid 777)" in t for ok, t in c.lines if not ok)


def test_lelabs_own_helper_counts_as_lelab(tmp_path, monkeypatch):
    # a teleop run LeLab starts runs on LeLab's own Python: its command line goes through lelab/
    monkeypatch.setattr(green, "_answers", lambda port: True)
    paths = setup(tmp_path, {LEADER: "ttyACM0", FOLLOWER: "ttyACM1"})
    hold(paths, "ttyACM0", program="python", argv=[LELAB[0], "-m", "lerobot.teleoperate"])
    assert check(**paths).ok


def test_a_name_that_only_contains_lelab_is_not_lelab(tmp_path):
    proc = tmp_path / "proc"
    (proc / "5").mkdir(parents=True)
    (proc / "5" / "cmdline").write_bytes(b"/home/x/notlelab/run\0")
    assert not green._is_lelab("run (pid 5)", proc)
    (proc / "5" / "cmdline").write_bytes(b"/home/x/.local/bin/lelab\0")
    assert green._is_lelab("lelab (pid 5)", proc)


def test_cant_tell_who_has_the_port_refuses(tmp_path, monkeypatch):
    monkeypatch.setattr(green, "users_of", lambda path, proc: None)  # no /proc and no lsof
    c = check(**setup(tmp_path, {LEADER: "ttyACM0", FOLLOWER: "ttyACM1"}))
    assert not c.ok
    assert any("can't tell" in t for ok, t in c.lines if not ok)


# ---------- Stop LeLab (quick job 7): only the one the launcher started ----------


def _fake_lelab(tmp_path):
    """A stand-in LeLab: a script called `lelab`, in its own process group like the real one."""
    import subprocess

    script = tmp_path / "lelab"
    script.write_text("#!/bin/sh\nsleep 30\n")
    script.chmod(0o755)
    return subprocess.Popen([str(script)], start_new_session=True)


def test_stop_lelab_stops_the_one_the_launcher_started(tmp_path, monkeypatch):
    monkeypatch.setattr(green, "_answers", lambda port: False)
    p = _fake_lelab(tmp_path)
    note = tmp_path / "started.json"
    green._note_started(p.pid, note)
    assert green.started_lelab(note) == p.pid
    assert green.stop_lelab(note, wait_s=3) == "LeLab stopped."
    assert p.wait(timeout=3) is not None


def test_another_program_at_that_pid_is_left_alone(tmp_path, monkeypatch):
    import subprocess

    monkeypatch.setattr(green, "_answers", lambda port: False)
    other = subprocess.Popen(["sleep", "30"])  # not lelab
    note = tmp_path / "started.json"
    green._note_started(other.pid, note)
    try:
        assert green.started_lelab(note) is None
        assert green.stop_lelab(note) == "LeLab isn't running."
        assert other.poll() is None  # still running
    finally:
        other.kill()


def test_a_stale_start_time_never_matches(tmp_path):
    p = _fake_lelab(tmp_path)
    note = tmp_path / "started.json"
    note.write_text(f'{{"pid": {p.pid}, "started": "Mon Jan  1 00:00:00 2024"}}')
    try:
        assert green.started_lelab(note) is None
    finally:
        p.kill()


def test_a_lelab_started_another_way_is_left_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(green, "_answers", lambda port: True)
    said = green.stop_lelab(tmp_path / "none.json")
    assert "not one the launcher started" in said
