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


def hold(paths, tty, program="python3", pid="4321"):
    """A program (lab-os driving so101-green, say) has this fake tty open."""
    fd = paths["proc"] / pid / "fd"
    fd.mkdir(parents=True)
    (paths["proc"] / pid / "comm").write_text(program + "\n")
    (fd / "9").symlink_to(paths["by_id"].parent / "dev" / tty)


def test_a_green_port_open_in_another_program_refuses(tmp_path, monkeypatch):
    monkeypatch.setattr(green, "_answers", lambda port: False)  # LeLab not running
    paths = setup(tmp_path, {LEADER: "ttyACM0", FOLLOWER: "ttyACM1"})
    hold(paths, "ttyACM1")
    c = check(**paths)
    assert not c.ok
    assert any("…3501 is open in python3 (pid 4321)" in t for ok, t in c.lines if not ok)


def test_lelab_already_running_may_hold_the_ports(tmp_path, monkeypatch):
    monkeypatch.setattr(green, "_answers", lambda port: True)  # LeLab answers: the ports are its
    paths = setup(tmp_path, {LEADER: "ttyACM0", FOLLOWER: "ttyACM1"})
    hold(paths, "ttyACM1", program="lelab")
    c = check(**paths)
    assert c.ok and c.running, c.lines
