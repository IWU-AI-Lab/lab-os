"""Two arms at once (preview 3): the right controller drives one arm, the left controller the other,
both from one input page. STOP, A/X and the dead-man rule stop both. Two fake arms, no hardware."""

import argparse
import asyncio

import pytest

from lab_os.kinematics import kinematics_for
from lab_os.robots.fake import FakeArm
from lab_os.teleop import cli as teleop_cli
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.teleop.mapping import ClutchMapper, MappingConfig
from lab_os.teleop.messages import parse_frame, parse_joint_frame
from lab_os.teleop.server import create_app

DT = 0.02


def controller(x=0.0, grip=0.0, a=False):
    return {
        "pos": [x, 1.0, 0.0],
        "quat": [0, 0, 0, 1],
        "grip": grip,
        "trigger": 0.0,
        "buttons": {"a": a},
    }


def frame(right=None, left=None):
    hands = {}
    if right is not None:
        hands["right"] = right
    if left is not None:
        hands["left"] = left
    return {"type": "xr_input", "t": 0, "hands": hands}


def arm_loop(arm, inputs, hand):
    arm.connect()
    return TeleopLoop(
        arm=arm,
        inputs=inputs,
        mapper=ClutchMapper(config=MappingConfig(hand=hand), kinematics=kinematics_for(arm.model)),
        speed_scale=0.5,
        one_to_one_deg_per_s=180.0,
    )


def two_arms():
    """As `lab-os serve --left-arm` builds them: one input, the left loop inside the right."""
    inputs = InputState()
    right = arm_loop(FakeArm(name="fake-arm"), inputs, "right")
    right.left = arm_loop(FakeArm(name="fake-left"), inputs, "left")
    right.left.is_left = True
    return right, right.left


def feed(right, raw, now):
    right.inputs.update(parse_frame(raw), now=now)
    right.step(now, DT)
    right.left.step(now, DT)


def pan(loop):
    return loop.arm.read_joints()["shoulder_pan"]


def grab_and_move(right, x_right=0.0, x_left=0.0, ticks=60, start=0.0):
    """Both grips held from the start; each hand then moves to its x. Returns the next time."""
    now = start
    r = controller(grip=1.0) if x_right is not None else controller()
    lft = controller(grip=1.0) if x_left is not None else controller()
    feed(right, frame(r, lft), now)
    for _ in range(ticks):
        now += DT
        r = controller(x=x_right or 0.0, grip=1.0 if x_right is not None else 0.0)
        lft = controller(x=x_left or 0.0, grip=1.0 if x_left is not None else 0.0)
        feed(right, frame(r, lft), now)
    return now


def test_each_controller_drives_its_own_arm():
    right, left = two_arms()
    grab_and_move(right, x_right=0.1, x_left=None)
    assert pan(right) > 5 and pan(left) == 0.0  # only the right grip is held

    right, left = two_arms()
    grab_and_move(right, x_right=None, x_left=-0.1)
    assert pan(left) < -5 and pan(right) == 0.0  # only the left grip is held

    right, left = two_arms()
    grab_and_move(right, x_right=0.1, x_left=-0.1)
    assert pan(right) > 5 and pan(left) < -5  # both at once, each its own way


@pytest.mark.parametrize("side", ["right", "left"])
def test_a_or_x_on_either_controller_freezes_both(side):
    right, left = two_arms()
    now = grab_and_move(right, x_right=0.05, x_left=0.05)
    assert not right.frozen and not left.frozen
    hands = {"right": controller(x=0.05, grip=1.0), "left": controller(x=0.05, grip=1.0)}
    hands[side] = controller(x=0.05, grip=1.0, a=True)
    feed(right, frame(hands["right"], hands["left"]), now + DT)
    assert right.frozen and left.frozen
    assert right.arm.stopped and left.arm.stopped


def test_stop_freezes_both_and_both_need_a_new_grip():
    right, left = two_arms()
    now = grab_and_move(right, x_right=0.05, x_left=0.05)
    right.stop()
    assert right.frozen and left.frozen
    assert right.mapper.needs_release and left.mapper.needs_release
    before = (pan(right), pan(left))
    for _ in range(20):  # grips still held: nothing moves
        now += DT
        feed(right, frame(controller(x=0.2, grip=1.0), controller(x=0.2, grip=1.0)), now)
    assert (pan(right), pan(left)) == before


def test_the_dead_man_rule_freezes_both():
    right, left = two_arms()
    now = grab_and_move(right, x_right=0.05, x_left=0.05)
    right.step(now + 1.0, DT)  # nothing new for a second
    left.step(now + 1.0, DT)
    assert right.frozen and left.frozen
    right, left = two_arms()
    now = grab_and_move(right, x_right=0.05, x_left=0.05)
    right.inputs.disconnect()  # the page left
    right.step(now + DT, DT)
    left.step(now + DT, DT)
    assert right.frozen and left.frozen


def test_jogging_moves_only_the_right_arm():
    right, left = two_arms()
    for i in range(30):
        right.inputs.update(
            parse_joint_frame({"type": "joint_input", "rates": {"shoulder_pan": 1.0}}), now=i * DT
        )
        right.step(i * DT, DT)
        left.step(i * DT, DT)
    assert pan(right) > 1 and pan(left) == 0.0 and left.frozen


def test_speed_and_venue_caps_reach_the_left_arm():
    right, left = two_arms()
    right.set_speed(0.3)
    assert left.speed_scale == 0.3
    right.use_caps(0.4, 0.2, 0.0)  # e.g. visitor mode: slower, no 1:1
    assert (left.max_speed_scale, left.speed_scale, left.one_to_one_deg_per_s) == (0.4, 0.2, 0.0)


def test_the_left_arm_is_relative_only_but_follows_as_fast():
    right, left = two_arms()
    assert right.modes() == ["relative", "one_to_one"] and left.modes() == ["relative"]
    assert left.relative_cap() == right.relative_cap() is not None


def test_status_has_the_left_arm():
    right, left = two_arms()
    s = right.status()
    assert s["left_arm"]["name"] == "fake-left"
    assert s["left_arm"]["frozen"] is False and s["left_arm"]["connected"] is True
    assert set(s["left_arm"]) >= {"clutch", "needs_release", "joints", "limits", "problem"}
    alone = arm_loop(FakeArm(), InputState(), "right")
    assert alone.status()["left_arm"] is None


def test_close_arms_lets_go_of_both_even_if_the_first_fails():
    right, left = two_arms()
    closed = []
    left.arm.close = lambda: closed.append("left")

    def broken():
        raise OSError("the USB just went")

    right.arm.stop = broken
    with pytest.raises(OSError):
        teleop_cli.close_arms(right)
    assert closed == ["left"]


# ---------- through the server: one page, two arms ----------


async def wait_for(cond, timeout=2.0):
    for _ in range(int(timeout / 0.01)):
        if cond():
            return True
        await asyncio.sleep(0.01)
    return False


async def test_one_page_drives_both_and_stop_from_a_monitor_stops_both(aiohttp_client):
    right, left = two_arms()
    client = await aiohttp_client(create_app(right))
    page = await client.ws_connect("/ws")
    monitor = await client.ws_connect("/ws?role=monitor")
    devices = set()

    async def listen():
        async for msg in monitor:
            m = msg.json()
            if m["type"].startswith("arm_"):
                devices.add(m["device"])

    listener = asyncio.create_task(listen())
    for i in range(40):
        x = min(i * 0.005, 0.1)
        await page.send_json(frame(controller(x=x, grip=1.0), controller(x=-x, grip=1.0)))
        await asyncio.sleep(0.02)
    assert await wait_for(lambda: pan(right) > 2 and pan(left) < -2)
    await monitor.send_json({"type": "stop"})
    assert await wait_for(lambda: right.frozen and left.frozen)
    listener.cancel()
    # each arm's commands go out under its own name (the pages' ArmFeed tells them apart)
    assert devices == {"fake-arm", "fake-left"}


# ---------- the command line ----------


def args(**kw):
    base = {"venue": None, "arm": "fake", "left_arm": None, "speed": None, "quiet": True}
    return argparse.Namespace(**(base | kw))


def test_left_arm_fake_is_a_second_software_arm():
    loop = teleop_cli.make_loop(args(left_arm="fake"))
    try:
        assert loop.arm.name == "fake-arm" and loop.left.arm.name == "fake-left"
        assert loop.mapper.config.hand == "right" and loop.left.mapper.config.hand == "left"
        assert loop.left.is_left and loop.left.inputs is loop.inputs
    finally:
        teleop_cli.close_arms(loop)
    assert teleop_cli.make_loop(args()).left is None


def test_the_same_arm_twice_is_refused():
    with pytest.raises(SystemExit, match="that's --arm too"):
        teleop_cli.make_loop(args(arm="so101-white", left_arm="so101-white"))


def test_the_left_arm_gets_the_same_checks_as_the_first(monkeypatch):
    """--left-arm goes through the same refusals as --arm (an unknown arm here); the first arm,
    already open, is let go of."""
    closed = []
    real_open = teleop_cli._open_arm

    def watched(option, name, venue):
        arm = real_open(option, name, venue)
        if option == "--arm":
            arm.close = lambda: closed.append(arm.name)
        return arm

    monkeypatch.setattr(teleop_cli, "_open_arm", watched)
    with pytest.raises(SystemExit, match="not an arm lab-os can drive here"):
        teleop_cli.make_loop(args(left_arm="so101-green-leader"))
    assert closed == ["fake-arm"]


def test_lab_os_serve_takes_left_arm(monkeypatch):
    from lab_os import cli

    started = []

    def fake_run(coro):
        started.append(coro.__qualname__)
        coro.close()

    monkeypatch.setattr("asyncio.run", fake_run)
    cli.main(["serve", "--quiet", "--port", "8099", "--left-arm", "fake"])
    assert started == ["serve"]


# ---------- the hub knows the left arm ----------


class LimpArm(FakeArm):
    limp_on_close = True  # like a real SO-101: closing switches the torque off


def brain_app(right):
    from test_hub_server import VENUE  # same folder (pytest puts it on the path)

    from lab_os.hub.server import create_brain_app

    return create_brain_app(right, VENUE, internet=None)


async def test_the_shutdown_warning_names_both_arms(aiohttp_client):
    inputs = InputState()
    right = arm_loop(LimpArm(name="so101-white"), inputs, "right")
    right.left = arm_loop(LimpArm(name="so101-green"), inputs, "left")
    right.left.is_left = True
    client = await aiohttp_client(brain_app(right))
    r = await (await client.get("/api/shutdown")).json()
    assert "so101-white and so101-green go limp" in r["warning"]


async def test_the_status_report_and_api_have_the_left_arm(aiohttp_client):
    from lab_os.hub.server import lab_status

    right, left = two_arms()
    app = brain_app(right)
    r = lab_status(app)
    assert r["arm"]["left_arm"] == {"name": "fake-left", "connected": True, "held_still": False}
    left.arm_connected, left.arm_problem = False, "its USB was unplugged"
    assert any(w.startswith("fake-left is disconnected") for w in lab_status(app)["warnings"])
    client = await aiohttp_client(app)
    s = await (await client.get("/api/status")).json()
    assert s["left_arm"] == {"name": "fake-left", "connected": False}
    alone = brain_app(arm_loop(FakeArm(), InputState(), "right"))
    assert "left_arm" not in lab_status(alone)["arm"]


def test_a_venue_switch_reaches_the_left_arm():
    from lab_os.hub.server import switch_venue

    right, left = two_arms()
    app = brain_app(right)
    venue = switch_venue(app, "lab")
    assert left.max_speed_scale == venue.speed_cap_scale
    assert left.mapper.config.floor_m == teleop_cli.teleop_floor_m(venue, "fake-left")
