"""Quick job 61: `lab-os serve` with no --arm drives the SO-101s plugged in (never the borrowed
green set unless named), and the fake arm when none is. No hardware: the ports are faked."""

import argparse

import pytest

from lab_os import devices
from lab_os.devices import Device, PortNotAllowed, Registry, plugged_in_arms
from lab_os.robots.fake import FakeArm
from lab_os.teleop import cli as teleop_cli

WHITE = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41532410-if00"
GREEN = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41533501-if00"


def args(**kw):
    return argparse.Namespace(
        **({"arm": None, "left_arm": None, "venue": "lab", "speed": None, "quiet": True} | kw)
    )


@pytest.fixture
def plugged(monkeypatch):
    """Say which ports are there; real arms open as fake ones under their own names."""
    here: set[str] = set()
    monkeypatch.setattr(devices, "port_exists", lambda path: path in here)
    real = teleop_cli._make_arm
    monkeypatch.setattr(
        teleop_cli,
        "_make_arm",
        lambda name, venue: real(name, venue) if name.startswith("fake") else FakeArm(name=name),
    )
    return here


def test_which_arms_count(monkeypatch):
    monkeypatch.setattr(devices, "port_exists", lambda path: True)
    reg = Registry(
        {
            "a": Device("a", "so101", ports=("/dev/serial/by-id/a",)),
            "a-leader": Device("a-leader", "so101-leader", ports=("/dev/serial/by-id/al",)),
            "b": Device("b", "so101", borrowed=True, ports=("/dev/serial/by-id/b",)),
            "c": Device("c", "so101", off_limits=True, ports=("/dev/serial/by-id/c",)),
            "d": Device("d", "so101", ports=("/dev/serial/by-id/d",)),
            "e": Device("e", "so101", ports=("/dev/serial/by-id/e",)),
        }
    )
    # leaders, borrowed and off-limits arms are never taken; e isn't active in the venue
    assert plugged_in_arms(reg, ["a", "a-leader", "b", "c", "d"]) == ["a", "d"]


def test_nothing_plugged_in_is_the_fake_arm(plugged, capsys):
    a = args()
    loop = teleop_cli.make_loop(a)
    assert loop.arm.name == "fake-arm" and loop.left is None and a.arm == "fake"
    assert "No arm plugged in" in capsys.readouterr().out


def test_the_white_arm_plugged_in_is_driven(plugged, capsys):
    plugged.add(WHITE)
    a = args()
    loop = teleop_cli.make_loop(a)
    assert loop.arm.name == "so101-white" and loop.left is None
    assert teleop_cli.any_real_arm(a)
    assert "Plugged in: so101-white" in capsys.readouterr().out


def test_the_green_arm_is_taken_only_as_the_left_arm(plugged):
    """Alone it's never taken unasked (the AI tools drive --arm); beside another arm it becomes
    the left arm (the builder, 2026-11-21: two arms without naming them)."""
    plugged.update({GREEN})
    assert teleop_cli.make_loop(args()).arm.name == "fake-arm"
    plugged.add(WHITE)
    loop = teleop_cli.make_loop(args())
    assert loop.arm.name == "so101-white" and loop.left.arm.name == "so101-green"
    assert teleop_cli.make_loop(args(arm="so101-green")).arm.name == "so101-green"


def test_two_arms_plugged_in_become_both_hands(plugged, monkeypatch):
    monkeypatch.setattr(
        teleop_cli,
        "plugged_in_arms",
        lambda reg, active, borrowed=False: [] if borrowed else ["one", "two"],
    )
    loop = teleop_cli.make_loop(args())
    assert loop.arm.name == "one" and loop.left.arm.name == "two"
    # --left-arm named: the plugged-in arm that isn't it becomes --arm
    loop = teleop_cli.make_loop(args(left_arm="two"))
    assert loop.arm.name == "one" and loop.left.arm.name == "two"


def test_a_named_arm_is_never_swapped(plugged):
    plugged.add(WHITE)
    assert teleop_cli.make_loop(args(arm="fake")).arm.name == "fake-arm"  # the override


def test_an_arm_found_but_busy_starts_the_fake_arm(plugged, monkeypatch, capsys):
    """LeLab has the port, or no calibration: the brain still starts, and says why."""
    plugged.add(WHITE)

    real = teleop_cli._make_arm

    def busy(name, venue):
        if name.startswith("fake"):
            return real(name, venue)
        arm = FakeArm(name=name)

        def refuse():
            raise PortNotAllowed(f"{name}'s port is in use by lelab")

        arm.connect = refuse
        return arm

    monkeypatch.setattr(teleop_cli, "_make_arm", busy)
    a = args()
    loop = teleop_cli.make_loop(a)
    assert loop.arm.name == "fake-arm" and a.arm == "fake" and not teleop_cli.any_real_arm(a)
    out = capsys.readouterr().out
    assert "in use by lelab" in out and "The fake arm instead" in out
    with pytest.raises(SystemExit, match="in use"):  # named: it stops, as before
        teleop_cli.make_loop(args(arm="so101-white"))


def test_lab_os_teleop_still_starts_on_the_fake_arm(plugged, monkeypatch):
    plugged.add(WHITE)
    seen = []
    monkeypatch.setattr(teleop_cli, "make_loop", lambda a: seen.append(a.arm) or 1 / 0)
    with pytest.raises(ZeroDivisionError):
        teleop_cli.main(["--quiet", "serve"])
    assert seen == ["fake"]


def test_an_arm_plugged_in_later_is_found_with_the_same_rules(plugged, monkeypatch, caplog):
    """Quick job 73: started on the fake arm, the brain's finder takes the white arm once it's
    plugged in, never the green one (borrowed: only when named), and says once why an arm that's
    plugged in won't open."""
    from lab_os.venues import load_venue

    a = args()
    loop = teleop_cli.make_loop(a)
    assert a.auto_arm and a.arm == "fake"
    find = teleop_cli.arm_finder()
    venue = load_venue("lab")
    assert find(loop, venue) is None  # nothing plugged in
    plugged.add(GREEN)
    assert find(loop, venue) is None  # the green set: never by itself
    plugged.add(WHITE)
    real = teleop_cli._make_arm

    def busy(name, venue):
        raise SystemExit(f"{name}: in use by another program")

    monkeypatch.setattr(teleop_cli, "_make_arm", busy)
    assert find(loop, venue) is None and find(loop, venue) is None
    assert caplog.text.count("in use by another program") == 1  # said once, not every look
    monkeypatch.setattr(
        teleop_cli,
        "_make_arm",
        lambda n, v: real(n, v) if n.startswith("fake") else FakeArm(name=n),
    )
    new = find(loop, venue)
    assert new.arm.name == "so101-white" and new.inputs is loop.inputs


def test_a_named_arm_is_not_replaced(plugged):
    a = args(arm="fake")
    teleop_cli.make_loop(a)
    assert not a.auto_arm  # --arm fake: the builder asked for the fake arm
