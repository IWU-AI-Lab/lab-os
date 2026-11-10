"""The module pages in the hub's design (teleop, monitor, AI control, settings), the plain pages
kept at /classic/…, the settings (src/lab_os/settings.py) and what keeps the brain up when a port is
taken. No hardware, no internet; settings are only ever written into a temporary place."""

import asyncio
import socket

import pytest
from aiohttp import web
from test_hub_server import make_app

import lab_os.hub.server as hub_server
from lab_os import config, settings
from lab_os.hub.server import TOOLS, side_view_cm
from lab_os.kinematics import so101_kinematics
from lab_os.venues import load_venue


@pytest.fixture
def home(tmp_path):
    folder = config.new_place(tmp_path / "home")
    config.use(folder)
    return folder


async def test_the_pages(aiohttp_client):
    client = await aiohttp_client(make_app())
    pages = {
        "/teleop": ['id="enter"', 'id="desk-mode"', "/web/design/kit.css"],
        "/monitor": ['id="joints"', 'data-role="monitor"', "/web/design/kit.css"],
        "/classic/teleop": ['id="enter"', "/static/classic/style.css"],
        "/classic/monitor": ['id="joints"', "/static/classic/style.css"],
        "/ai": ["/hub/ai.js", 'id="calls"'],
        "/settings": ["/hub/settings.js", 'id="this-screen"'],
    }
    for path, parts in pages.items():
        text = await (await client.get(path)).text()
        for part in parts:
            assert part in text, (path, part)
    for path in ("/web/design/kit.js", "/web/design/icons.svg", "/static/pages.css", "/hub/ai.js"):
        assert (await client.get(path)).status == 200, path


async def test_ai_calls_show_what_the_tools_did(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    await app[TOOLS].call("arm_status")
    await app[TOOLS].call("gripper", open_pct=60)
    d = await (await client.get("/api/ai-calls")).json()
    assert [c["tool"] for c in d["calls"]] == ["arm_status", "gripper"]
    assert d["calls"][1]["outcome"] == "ok" and d["control"] == "free"
    assert d["mcp"] is None and d["motion_allowed"] is True  # no MCP port in tests
    later = await (await client.get(f"/api/ai-calls?after={d['calls'][0]['t']}")).json()
    assert [c["tool"] for c in later["calls"]] == ["gripper"]


async def test_arm_has_a_side_view(aiohttp_client):
    client = await aiohttp_client(make_app())
    arm = await (await client.get("/api/arm")).json()
    side = arm["side_cm"]
    assert side[0] == {"name": "base", "r": 0.0, "z": 0.0} and side[-1]["name"] == "tip"
    assert side[-1]["r"] == pytest.approx(arm["gripper_point_cm"]["x"], abs=0.2)  # pan 0: r = x


def test_side_view_turns_with_the_pan():
    straight = side_view_cm(so101_kinematics(), {"shoulder_pan": 0})
    turned = side_view_cm(so101_kinematics(), {"shoulder_pan": 60})
    assert [p["r"] for p in straight] == pytest.approx([p["r"] for p in turned], abs=0.15)
    assert side_view_cm(object(), {}) is None  # an arm without joint-by-joint kinematics


# ---------- settings ----------


def test_a_change_keeps_every_other_line(home):
    settings.write("theme:hub.look", "design")
    settings.write("theme:hub.modules", ["monitor", "teleop"])
    before = (config.DEFAULT_DIR / "theme.yaml").read_text().splitlines()
    after = (home / "theme.yaml").read_text().splitlines()  # the place's own copy, made now
    changed = [(a, b) for a, b in zip(before, after, strict=True) if a != b]
    assert len(changed) == 2
    assert changed[0][1].startswith("  look: design ") and "# plain | design" in changed[0][1]
    assert changed[1][1].startswith("  modules: [monitor, teleop]")
    assert "look: plain" in (config.DEFAULT_DIR / "theme.yaml").read_text()  # the repo's untouched


def test_values_are_checked(home):
    with pytest.raises(settings.SettingError, match="between 0.05 and 1"):
        settings.write("venue:max_speed_scale", 3)
    with pytest.raises(settings.SettingError, match="one of"):
        settings.write("theme:quality.default", "ultra")
    with pytest.raises(settings.SettingError, match="no setting"):
        settings.write("theme:nope", 1)
    assert settings.write("venue:max_speed_scale", "0.35") == 0.35
    assert load_venue("home").max_speed_scale == 0.35
    assert settings.write("place:name", "  Home Lab ") == "Home Lab"
    assert config.load_place().name == "Home Lab"


def test_a_module_adds_its_own_section(monkeypatch):
    monkeypatch.setattr(settings, "SECTIONS", list(settings.SECTIONS))
    settings.register(
        settings.Section(
            "xarm",
            "xArm",
            (settings.Field("venue", "xarm.speed", "Speed", "number", min=0, max=1),),
        )
    )
    assert settings.find("venue:xarm.speed").label == "Speed"
    assert settings.read()[-1]["id"] == "xarm"


async def test_settings_change_only_from_this_computer(aiohttp_client, home, monkeypatch):
    client = await aiohttp_client(make_app(venue=load_venue("home")))
    got = await (await client.get("/api/settings")).json()
    assert got["writable"] is True and got["venue"] == "home"
    keys = {f["key"] for s in got["sections"] for f in s["fields"]}
    assert {
        "theme:hub.look",
        "theme:quality.default",
        "place:persona",
        "venue:motion_allowed",
    } <= keys

    res = await client.post("/api/settings", json={"key": "theme:clock", "value": "12h"})
    assert (await res.json()) == {
        "ok": True,
        "key": "theme:clock",
        "value": "12h",
        "applies": "reload",
    }
    assert (await (await client.get("/theme.json")).json())["clock"] == "12h"
    bad = await client.post("/api/settings", json={"key": "theme:clock", "value": "25h"})
    assert bad.status == 400 and "one of" in (await bad.json())["message"]

    monkeypatch.setattr(hub_server, "is_local", lambda request: False)  # a hallway screen
    assert (
        await client.post("/api/settings", json={"key": "theme:clock", "value": "24h"})
    ).status == 403
    assert (await (await client.get("/api/settings")).json())["writable"] is False


async def test_the_title_follows_place_yaml_without_a_restart(aiohttp_client, home):
    client = await aiohttp_client(make_app(venue=load_venue("home")))
    settings.write("place:name", "Renamed")
    assert (await (await client.get("/api/hub")).json())["title"] == "Renamed"


# ---------- a port that's taken ----------


def _taken_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    return s, s.getsockname()[1]


async def test_the_brain_runs_on_when_the_ai_tools_port_is_taken(caplog):
    from lab_os.tools.mcp_server import McpHttp, create_mcp_server
    from lab_os.tools.project import ProjectTools

    app = make_app()
    sock, port = _taken_port()
    try:
        mcp = McpHttp(create_mcp_server(app[TOOLS], ProjectTools(config.DEFAULT_DIR)), port)
        await asyncio.wait_for(mcp.serve(), 10)  # returns instead of exiting the program
    finally:
        sock.close()
    assert mcp.failed and "AI tools (MCP) are off" in caplog.text


async def test_a_taken_hub_port_says_so():
    from lab_os.teleop.cli import serve

    sock, port = _taken_port()
    try:
        with pytest.raises(SystemExit, match="is another lab-os already running"):
            await serve(web.Application(), port)
    finally:
        sock.close()
