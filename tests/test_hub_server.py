"""The brain's hub endpoints and pages (no hardware, no internet)."""

import re
from pathlib import Path

import pytest

from lab_os.hub.server import Assistant, create_brain_app, hub_modules, reset_after_s
from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.venues import Venue

SRC = Path(__file__).resolve().parents[1] / "src" / "lab_os"
VENUE = Venue(
    name="test-venue", active_devices=("fake-arm",), motion_allowed=True, max_speed_scale=0.5
)
FRAME = {"type": "joint_input", "t": 1, "rates": {"gripper": 0.5}}


def make_app(**kw):
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState())
    return create_brain_app(loop, kw.pop("venue", VENUE), internet=None, **kw)


async def test_pages_answer(aiohttp_client):
    client = await aiohttp_client(make_app())
    for path in (
        "/",
        "/hub/hub.js",
        "/hub/hub.css",
        "/teleop",
        "/monitor",
        "/web/theme.js",
        "/theme.json",
    ):
        resp = await client.get(path)
        assert resp.status == 200, path
    assert 'id="ignite"' in await (await client.get("/")).text()
    assert 'id="enter"' in await (await client.get("/teleop")).text()  # the designed teleop page


async def test_status(aiohttp_client):
    client = await aiohttp_client(make_app())
    st = await (await client.get("/api/status")).json()
    assert st["venue"] == "test-venue"
    assert st["internet"] is None  # not checked in tests
    assert st["ai"]["connected"] is None  # not checked in tests
    assert "OPENAI_API_KEY" in st["ai"]["paused"]  # tests never read a .env
    assert st["assistant"]["state"] == "offline"
    assert st["arm"] == {"name": "fake-arm", "connected": True, "control": "free"}
    assert st["in_use"] == []
    assert st["time_ms"] > 0


async def test_status_says_in_use_while_teleop_has_the_arm(aiohttp_client):
    client = await aiohttp_client(make_app())
    ws = await client.ws_connect("/ws")
    await ws.send_json(FRAME)
    for _ in range(100):
        st = await (await client.get("/api/status")).json()
        if st["in_use"]:
            break
    assert st["in_use"] == ["teleop"] and st["arm"]["control"] == "taken"
    await ws.close()
    for _ in range(100):
        st = await (await client.get("/api/status")).json()
        if not st["in_use"]:
            break
    assert st["in_use"] == []


async def test_project(aiohttp_client, tmp_path):
    focus = tmp_path / "focus.md"
    focus.write_text("# Current Focus: x\n\n## Steps\n0. **A** (done 2026-01-01)\n1. **B.** b\n")
    client = await aiohttp_client(make_app(focus_file=focus))
    p = await (await client.get("/api/project")).json()
    assert (p["step"], p["of"], p["next"]) == (1, 1, "B")


async def test_commits(aiohttp_client):
    client = await aiohttp_client(make_app())
    c = await (await client.get("/api/commits?days=7")).json()
    assert c["days"] == 7
    if c["available"]:  # a source copy without .git has no history
        assert len(c["per_day"]) == 7
    assert (await client.get("/api/commits?days=999")).status == 200  # capped, not an error
    assert (await client.get("/api/commits?days=lots")).status == 400


async def test_hub_config(aiohttp_client):
    client = await aiohttp_client(make_app())
    h = await (await client.get("/api/hub")).json()
    assert [m["id"] for m in h["modules"]] == ["teleop", "monitor", "ai", "training"]
    assert h["modules"][0]["page"] == "/teleop"
    assert h["reset_after_s"] == 1800


def test_modules_without_a_page_get_no_button():
    theme = {"hub": {"modules": ["monitor", "nothing-yet", "teleop"]}}
    assert [m["id"] for m in hub_modules(theme)] == ["monitor", "teleop"]
    assert hub_modules({}) == []


def test_reset_time_venue_wins_over_theme():
    theme = {"hub": {"reset_after_s": 120}}
    assert reset_after_s(theme, VENUE) == 120
    assert reset_after_s({}, VENUE) == 1800
    hallway = Venue("hallway", (), False, 0.3, reset_after_s=60)
    assert reset_after_s(theme, hallway) == 60


def test_assistant_states():
    a = Assistant()
    assert a.state == "offline"
    a.set("speaking", 1.7)
    assert (a.state, a.loudness) == ("speaking", 1.0)
    with pytest.raises(ValueError):
        a.set("dancing")


# Anything a page fetches, imports or links from http(s):// would break offline (AGENTS.md).
LOADS = re.compile(
    r"""(?:src|href|action)\s*=\s*["']https?://"""
    r"""|import\s[^;]*?from\s*["']https?://"""
    r"""|import\s*\(\s*["']https?://"""
    r"""|fetch\s*\(\s*["'`]https?://"""
    r"""|url\(\s*["']?https?://"""
    r"""|@import\s+["']?(?:url\()?["']?https?://"""
    r"""|new\s+(?:WebSocket|EventSource|Worker)\s*\(\s*["'`](?:https?|wss?)://""",
    re.IGNORECASE,
)


def test_no_web_file_loads_anything_from_the_internet():
    files = [
        f
        for d in (SRC / "web", SRC / "teleop" / "web", SRC / "hub" / "web")
        for f in d.rglob("*")
        if f.suffix in (".html", ".js", ".css", ".mjs")
    ]
    assert len(files) > 10
    bad = [
        f"{f.relative_to(SRC)}: {m.group(0)}" for f in files for m in LOADS.finditer(f.read_text())
    ]
    assert not bad, bad


async def test_status_says_in_use_while_the_ai_tools_move(aiohttp_client):
    from lab_os.teleop.loop import Motion

    app = make_app()
    client = await aiohttp_client(app)
    from lab_os.teleop.server import LOOP

    app[LOOP].start_motion(Motion(path=[{"shoulder_pan": 45.0}], deg_per_s=1.0))
    st = await (await client.get("/api/status")).json()
    assert st["in_use"] == ["ai"] and st["arm"]["control"] == "ai"
    app[LOOP].stop()


# ---------- quick job 73: an arm plugged in after the start ----------


def _app_with_a_new_arm(**kw):
    new = FakeArm(name="so101-white")
    new.connect()
    looks = []

    def find(loop, venue):
        looks.append(venue.name)
        return TeleopLoop(arm=new, inputs=loop.inputs) if new.plugged else None

    return make_app(find_arm=find, **kw), new, looks


@pytest.fixture
def no_looking_by_itself(monkeypatch):
    """The tests call take_new_arm themselves: the brain's own looking waits."""
    monkeypatch.setattr("lab_os.hub.server.NEW_ARM_EVERY_S", 3600)


async def test_an_arm_plugged_in_after_the_start_is_taken(aiohttp_client, no_looking_by_itself):
    from lab_os.hub.server import LOOP, TOOLS, take_new_arm

    app, new, looks = _app_with_a_new_arm()
    client = await aiohttp_client(app)
    fake = app[LOOP].arm
    assert await take_new_arm(app)
    assert app[LOOP].arm is new and app[TOOLS].arm is new  # the AI tools drive it too
    assert not fake.connected  # the fake arm was let go
    assert app[LOOP].frozen  # held where it is until input starts it
    arm = await (await client.get("/api/arm")).json()
    assert arm["name"] == "so101-white"  # the pages show the new arm
    assert looks


async def test_no_new_arm_while_someone_drives_the_fake_one(aiohttp_client, no_looking_by_itself):
    import time

    from lab_os.hub.server import LOOP, take_new_arm
    from lab_os.teleop.server import CONTROL

    app, new, looks = _app_with_a_new_arm()
    await aiohttp_client(app)
    fake = app[LOOP].arm
    app[CONTROL]["ws"] = object()  # a teleop page has control
    assert not await take_new_arm(app) and app[LOOP].arm is fake and not looks
    app[CONTROL]["ws"] = None
    app[LOOP].last_command_t = time.monotonic()  # it moved a moment ago (a wave between steps)
    assert not await take_new_arm(app) and app[LOOP].arm is fake
    app[LOOP].last_command_t = -1e9
    new.plugged = False  # nothing plugged in: nothing changes
    assert not await take_new_arm(app) and app[LOOP].arm is fake


def test_the_brain_looks_for_new_arms_only_when_it_chose_the_fake_arm():
    """--arm fake (or --arm so101-white) is what the builder asked for: kept. No --arm and none
    plugged in: it looks (lab_os.cli passes arm_finder())."""
    src = (SRC / "cli.py").read_text()
    assert 'arm_finder() if getattr(args, "auto_arm", False) and args.arm == "fake"' in src


async def test_the_brain_looks_by_itself(aiohttp_client, monkeypatch):
    import asyncio

    from lab_os.hub.server import LOOP

    monkeypatch.setattr("lab_os.hub.server.NEW_ARM_EVERY_S", 0.05)
    app, new, _ = _app_with_a_new_arm()
    await aiohttp_client(app)
    for _ in range(100):
        if app[LOOP].arm is new:
            break
        await asyncio.sleep(0.02)
    assert app[LOOP].arm is new
