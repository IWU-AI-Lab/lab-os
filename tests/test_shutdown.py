"""Shut down from the hub (quick job 6): the brain's computer only (any venue); any
move stops, every page is told, then the server stops the way Ctrl+C does (no hardware)."""

import asyncio
from dataclasses import replace

import pytest
from aiohttp import web
from test_hub_devices import next_of, page  # same folder (pytest puts it on the path)
from test_hub_server import SRC, VENUE, make_app

from lab_os.hub import server as hub_server
from lab_os.robots.fake import FakeArm
from lab_os.teleop import cli as teleop_cli
from lab_os.teleop.loop import InputState, Motion, TeleopLoop
from lab_os.teleop.messages import JointFrame
from lab_os.teleop.server import LOOP, SHUTDOWN
from lab_os.tools.robot import Refused


class LimpArm(FakeArm):
    limp_on_close = True  # like a real SO-101: closing switches the torque off


async def test_allowed_here_and_no_warning_for_the_fake_arm(aiohttp_client):
    client = await aiohttp_client(make_app())
    r = await (await client.get("/api/shutdown")).json()
    assert r == {"allowed": True, "why_not": None, "warning": None, "limp": []}


async def test_warns_that_an_arm_that_goes_limp_drops(aiohttp_client):
    arm = LimpArm(name="so101-white")
    arm.connect()
    app = hub_server.create_brain_app(TeleopLoop(arm=arm, inputs=InputState()), VENUE)
    client = await aiohttp_client(app)
    r = await (await client.get("/api/shutdown")).json()
    assert "so101-white goes limp" in r["warning"] and "drops" in r["warning"]
    assert r["limp"] == ["so101-white"]  # the confirmation's button names it too (quick job 44)


async def test_also_on_a_public_venue(aiohttp_client):
    # a person is always at the brain's computer (the builder, 2026-11-19): no public-venue rule
    app = make_app(venue=replace(VENUE, public=True))
    client = await aiohttp_client(app)
    r = await (await client.get("/api/shutdown")).json()
    assert r["allowed"] and r["why_not"] is None


async def test_only_from_the_brains_computer(aiohttp_client, monkeypatch):
    app = make_app()
    client = await aiohttp_client(app)
    monkeypatch.setattr(hub_server, "is_local", lambda request: False)  # a hallway screen
    r = await (await client.get("/api/shutdown")).json()
    assert not r["allowed"] and "brain's computer" in r["why_not"]
    assert (await client.post("/api/shutdown", json={})).status == 403
    assert not app[SHUTDOWN].is_set()


async def test_shut_down_stops_the_move_tells_every_page_then_stops(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    hub, _ = await page(client, "desk")
    monitor = await client.ws_connect("/ws?role=monitor")
    motion = Motion(path=[{"shoulder_pan": 45.0}], deg_per_s=1.0)
    app[LOOP].start_motion(motion)

    resp = await client.post("/api/shutdown", json={"from": "desk"})
    assert resp.status == 200 and (await resp.json())["ok"]
    assert motion.result == "lab-os is shutting down" and app[LOOP].frozen
    told = await next_of(hub, "brain_off")
    assert told["from"] == "desk" and told["time_ms"] > 0
    assert (await next_of(monitor, "brain_off"))["from"] == "desk"
    assert not app[SHUTDOWN].is_set()  # a moment for the pages to hear it first
    await asyncio.wait_for(app[SHUTDOWN].wait(), timeout=2)
    await hub.close()
    await monitor.close()


async def test_ctrl_c_tells_every_page_lab_os_is_off(aiohttp_client):
    """Quick job 64: after Ctrl+C the pages only greyed the core (lab check 11.12). The server
    stopping without Shut down tells them, as Shut down does, before the sockets close."""
    app = make_app()
    client = await aiohttp_client(app)
    hub, _ = await page(client, "desk")
    monitor = await client.ws_connect("/ws?role=monitor")
    stopping = asyncio.create_task(app.shutdown())  # what Ctrl+C runs, once serve() ends
    told = await next_of(hub, "brain_off")
    assert told["from"] == "" and "restart" not in told
    assert (await next_of(monitor, "brain_off"))["from"] == ""
    await asyncio.wait_for(stopping, 2)
    await hub.close()
    await monitor.close()


async def test_after_shut_down_the_pages_are_told_once(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    hub, _ = await page(client, "desk")
    await client.post("/api/shutdown", json={"from": "desk"})
    assert (await next_of(hub, "brain_off"))["from"] == "desk"
    await app.shutdown()
    while (msg := await hub.receive(timeout=2)).type.name == "TEXT":
        assert msg.json()["type"] != "brain_off"  # no second "lab-os is off" without a name
    await hub.close()


def test_a_shut_down_page_tries_to_close_itself():
    """Other devices: the browser closes the page if it allows; else "lab-os is off" stays."""
    off = (SRC / "web" / "off.js").read_text()
    assert "if (!restarting)" in off and "window.close()" in off


# ---------- no move after a shutdown starts, and a quick end (quick job 44) ----------


async def test_after_the_shutdown_starts_the_ai_tools_cant_move(aiohttp_client):
    """F.9: the arm went limp, but the AI's next small move started during the ~30 s wait."""
    app = make_app()
    client = await aiohttp_client(app)
    tools = app[hub_server.TOOLS]
    await client.post("/api/shutdown", json={"from": "desk"})
    for tool, args in (
        ("move_joints", {"joints": {"shoulder_pan": 10.0}}),
        ("go_to_pose", {"name": "ready"}),
        ("gripper", {"open_pct": 50}),
        ("wave", {}),
    ):
        with pytest.raises(Refused, match="lab-os is shutting down"):
            await tools.call(tool, **args)
    with pytest.raises(RuntimeError, match="shutting down"):
        app[LOOP].start_motion(Motion(path=[{"shoulder_pan": 10.0}]))
    assert (await tools.call("stop"))["result"] == "stopped"  # STOP still answers


async def test_a_move_that_was_running_says_why_it_stopped(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    tools = app[hub_server.TOOLS]
    move = asyncio.create_task(tools.call("move_joints", joints={"shoulder_pan": 25.0}))
    await asyncio.sleep(0.2)
    await client.post("/api/shutdown", json={"from": "desk"})
    r = await asyncio.wait_for(move, 2)
    assert r["result"] == "stopped" and "lab-os is shutting down" in r["clipped"][-1]


def test_after_the_shutdown_starts_teleop_input_moves_nothing():
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState())
    loop.shut_down("lab-os is shutting down")
    before = arm.read_joints()
    for i in range(20):  # a page keeps jogging, fresh input every tick
        loop.inputs.update(JointFrame(t=i, rates={"shoulder_pan": 1.0}), now=i * 0.02)
        loop.step(i * 0.02, 0.02)
    assert arm.read_joints() == before and loop.frozen
    assert loop.status()["shutting_down"]


def test_after_the_shutdown_starts_the_arm_is_never_reconnected():
    """A reconnect switches the motors' torque on; while shutting down, the USB isn't checked."""
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState())
    arm.plugged = False
    loop.check_link(0.0, force=True)
    assert not loop.arm_connected  # unplugged: let go
    loop.shut_down("lab-os is shutting down")
    arm.plugged = True
    loop.check_link(10.0, force=True)
    assert not loop.arm_connected  # plugged back in during the shutdown: left alone


def test_both_arms_stop_for_good():
    right, left = FakeArm(), FakeArm(name="fake-left")
    right.connect()
    left.connect()
    loop = TeleopLoop(arm=right, inputs=InputState())
    loop.left = TeleopLoop(arm=left, inputs=loop.inputs, is_left=True)
    loop.shut_down("lab-os is shutting down")
    assert loop.left.shutting_down == "lab-os is shutting down" and loop.left.frozen


async def test_serve_ends_quickly_with_pages_open(unused_tcp_port):
    """F.9: the terminal stayed ~30 s after the shutdown; aiohttp waited for the open pages."""
    import aiohttp

    app = make_app()
    task = asyncio.create_task(teleop_cli.serve(app, unused_tcp_port, banner="test"))
    base = f"http://127.0.0.1:{unused_tcp_port}"
    async with aiohttp.ClientSession() as s:
        for _ in range(50):
            try:
                await s.get(f"{base}/api/status")
                break
            except aiohttp.ClientError:
                await asyncio.sleep(0.05)
        socks = [
            await s.ws_connect(f"{base}/ws?role=monitor"),
            await s.ws_connect(f"{base}/ws/hub-device?device=desk"),
            await s.ws_connect(f"{base}/ws/voice?device=desk"),
        ]
        t0 = asyncio.get_running_loop().time()
        assert (await s.post(f"{base}/api/shutdown", json={"from": "desk"})).status == 200
        await asyncio.wait_for(task, timeout=4)
        assert asyncio.get_running_loop().time() - t0 < 2.5
        for ws in socks:
            while not ws.closed:  # each page hears the close (and reconnects later by itself)
                await ws.receive(timeout=2)


async def test_a_bad_device_name_is_left_out(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    hub, _ = await page(client, "desk")
    assert (await client.post("/api/shutdown", json={"from": "<b>x"})).status == 200
    assert (await next_of(hub, "brain_off"))["from"] == ""
    await hub.close()


async def test_serve_returns_once_shut_down(unused_tcp_port):
    app = web.Application()
    app[SHUTDOWN] = asyncio.Event()
    task = asyncio.create_task(teleop_cli.serve(app, unused_tcp_port, banner="test"))
    await asyncio.sleep(0.2)
    assert not task.done()
    app[SHUTDOWN].set()
    await asyncio.wait_for(task, timeout=2)  # then `lab-os serve` lets go of the arm (Ctrl+C's way)


def test_pages_hear_it():
    """Every page that talks to the brain covers itself with "lab-os is off" (web/off.js)."""
    for f in ("teleop/web/link.js", "web/device.js"):
        js = (SRC / f).read_text()
        assert "brain_off" in js and "showOff" in js, f
    for f in ("hub/web/design.html", "hub/web/hub.js"):
        assert "onOff:" in (SRC / f).read_text(), f  # and the microphone closes
    assert "function off()" in (SRC / "web/voice.js").read_text()
    assert "/api/shutdown" in (SRC / "hub/web/settings.js").read_text()
    assert '"power-menu"' in (SRC / "hub/web/design.html").read_text()
    # in the headset the page's cover isn't seen (quick job 44): the VR/AR hub draws a card, and
    # the teleop status panel says it
    xr = (SRC / "hub/web/xr-hub.js").read_text()
    assert '"brain_off"' in xr and "turnOff" in xr and "OffCard" in xr
    assert "offMessage()" in (SRC / "teleop/web/xr-scene.js").read_text()


# ---------- restart (quick job 38): Settings' "Restart Now" ----------


async def test_restart_is_a_shutdown_that_asks_to_start_again(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    hub, _ = await page(client, "desk")
    assert not app[hub_server.RESTART]["asked"]
    resp = await client.post("/api/restart", json={"from": "desk"})
    assert resp.status == 200 and (await resp.json())["message"] == "lab-os is restarting."
    told = await next_of(hub, "brain_off")
    assert told["restart"] is True and told["from"] == "desk"  # the pages say it comes back
    await asyncio.wait_for(app[SHUTDOWN].wait(), timeout=2)
    assert app[hub_server.RESTART]["asked"]  # lab_os.cli starts it again
    await hub.close()


async def test_restart_only_from_the_brains_computer(aiohttp_client, monkeypatch):
    app = make_app()
    client = await aiohttp_client(app)
    monkeypatch.setattr(hub_server, "is_local", lambda request: False)
    assert (await client.post("/api/restart", json={})).status == 403
    assert not app[hub_server.RESTART]["asked"]


async def test_settings_that_need_a_restart_are_listed(aiohttp_client, monkeypatch):
    from lab_os import settings

    monkeypatch.setattr(settings, "write", lambda key, value, venue=None: value)
    client = await aiohttp_client(make_app())
    for key in ("venue:max_speed_scale", "theme:clock", "venue:max_speed_scale"):
        value = 0.4 if key.endswith("scale") else "24h"
        assert (await client.post("/api/settings", json={"key": key, "value": value})).status == 200
    s = await (await client.get("/api/settings")).json()
    assert s["restart_needed"] == ["Top Speed"]  # the clock applies at once; listed once


def test_a_restart_doesnt_open_the_hub_again():
    from lab_os.cli import _without_open

    argv = ["serve", "--open", "desk", "--arm", "so101-white", "--open=quest", "--port", "8080"]
    assert _without_open(argv) == ["serve", "--arm", "so101-white", "--port", "8080"]


async def test_a_setting_set_back_needs_no_restart(aiohttp_client, monkeypatch):
    """Quick job 45: a value set back to what the brain runs with takes the amber bar away."""
    from lab_os import settings

    monkeypatch.setattr(settings, "write", lambda key, value, venue=None: value)
    client = await aiohttp_client(make_app())
    s = await (await client.get("/api/settings")).json()
    running = next(
        f["value"]
        for sec in s["sections"]
        for f in sec["fields"]
        if f["key"] == "venue:max_speed_scale"
    )
    r = await (
        await client.post("/api/settings", json={"key": "venue:max_speed_scale", "value": 0.3})
    ).json()
    assert r["restart_needed"] == ["Top Speed"] and r["restart_keys"] == ["venue:max_speed_scale"]
    r = await (
        await client.post("/api/settings", json={"key": "venue:max_speed_scale", "value": running})
    ).json()
    assert r["restart_needed"] == [] and r["restart_keys"] == []
    assert (await (await client.get("/api/settings")).json())["restart_needed"] == []


async def test_a_broken_config_file_is_a_sentence(aiohttp_client, monkeypatch, tmp_path):
    """Quick job 45: a file broken by hand gave "500 Internal Server Error", no "Saved", and then
    an empty settings page. Now: the file and the line, on the page and for a change."""
    from lab_os import config

    bad = tmp_path / "theme.yaml"
    bad.write_text("hub:\n  look: [plain\n")
    real = config.layers
    monkeypatch.setattr(
        config,
        "layers",
        lambda name, *a, **k: (
            [*real(name, *a, **k), bad] if name == "theme.yaml" else real(name, *a, **k)
        ),
    )
    client = await aiohttp_client(make_app())
    s = await (await client.get("/api/settings")).json()
    assert s["sections"] and any("line 3" in p or "line 2" in p for p in s["problems"])
    assert "theme.yaml" in s["problems"][0]
    res = await client.post("/api/settings", json={"key": "theme:clock", "value": "12h"})
    got = await res.json()
    assert res.status == 400 and not got["ok"] and "can't be read" in got["message"]
