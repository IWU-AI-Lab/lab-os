"""Shut down from the hub (quick job 6): the brain's computer only (any venue); any
move stops, every page is told, then the server stops the way Ctrl+C does (no hardware)."""

import asyncio
from dataclasses import replace

from aiohttp import web
from test_hub_devices import next_of, page  # same folder (pytest puts it on the path)
from test_hub_server import SRC, VENUE, make_app

from lab_os.hub import server as hub_server
from lab_os.robots.fake import FakeArm
from lab_os.teleop import cli as teleop_cli
from lab_os.teleop.loop import InputState, Motion, TeleopLoop
from lab_os.teleop.server import LOOP, SHUTDOWN


class LimpArm(FakeArm):
    limp_on_close = True  # like a real SO-101: closing switches the torque off


async def test_allowed_here_and_no_warning_for_the_fake_arm(aiohttp_client):
    client = await aiohttp_client(make_app())
    r = await (await client.get("/api/shutdown")).json()
    assert r == {"allowed": True, "why_not": None, "warning": None}


async def test_warns_that_an_arm_that_goes_limp_drops(aiohttp_client):
    arm = LimpArm(name="so101-white")
    arm.connect()
    app = hub_server.create_brain_app(TeleopLoop(arm=arm, inputs=InputState()), VENUE)
    client = await aiohttp_client(app)
    r = await (await client.get("/api/shutdown")).json()
    assert "so101-white goes limp" in r["warning"] and "drops" in r["warning"]


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
