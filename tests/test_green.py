"""The green launcher's check: only looks at names and LeLab's saved settings, and refuses unless
exactly the two green arms are plugged in the way LeLab expects. Fake folders, no real ports."""

import json

from lab_os.green import check, remember

FOLLOWER = "usb-1a86_USB_Single_Serial_5B41531599-if00"  # which green is which: made up here
LEADER = "usb-1a86_USB_Single_Serial_5B41533501-if00"
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
    return {"by_id": by_id, "home": home, "last_good": tmp_path / "last.json"}


def test_both_greens_alone_and_saved_right_is_ok(tmp_path):
    paths = setup(tmp_path, {LEADER: "ttyACM0", FOLLOWER: "ttyACM1"})
    c = check(**paths)
    assert c.ok, c.lines
    assert (c.follower, c.leader) == ("5B41531599", "5B41533501")


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
