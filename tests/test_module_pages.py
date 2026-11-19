"""The module pages in the hub's design (teleop, monitor, AI control, settings), the plain pages
kept at /classic/…, the settings (src/lab_os/settings.py) and what keeps the brain up when a port is
taken. No hardware, no internet; settings are only ever written into a temporary place."""

import asyncio
import shutil
import socket
import subprocess
from pathlib import Path

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
        "/settings": ["/hub/settings.js", 'id="list"'],
    }
    for path, parts in pages.items():
        text = await (await client.get(path)).text()
        for part in parts:
            assert part in text, (path, part)
    for path in ("/web/design/kit.js", "/web/design/icons.svg", "/static/pages.css", "/hub/ai.js"):
        assert (await client.get(path)).status == 200, path


async def test_every_page_has_the_full_screen_button(aiohttp_client):
    """Shown while not full screen, says why where the browser can't (focus: "Two taps"; GOTCHAS
    2026-11-10, /teleop on the Pi). Every page gets it from one helper, /web/fullscreen.js."""
    client = await aiohttp_client(make_app())
    kit = await (await client.get("/web/design/kit.js")).text()
    helper = await (await client.get("/web/fullscreen.js")).text()
    assert 'from "/web/fullscreen.js"' in kit and "fullscreenButton(btn)" in kit
    assert "export function whyNot" in helper and "export function fullscreenButton" in helper
    # kit.js no longer hides the button when the browser says no: the helper explains instead
    assert "if (!embedded && document.fullscreenEnabled)" not in kit
    pages = {  # page → what brings the button
        "/teleop": "/web/design/kit.js",
        "/monitor": "/web/design/kit.js",
        "/ai": "/web/design/kit.js",
        "/settings": "/web/design/kit.js",
        "/training": "/web/design/kit.js",
        "/xr": "/web/design/kit.js",
        "/plain": 'id="fs-btn"',
        "/design": 'id="fs-btn"',
        "/classic/teleop": 'import { fullscreenButton } from "/web/fullscreen.js"',
        "/classic/monitor": 'import { fullscreenButton } from "/web/fullscreen.js"',
        "/perf": 'id="full"',
    }
    for path, part in pages.items():
        text = await (await client.get(path)).text()
        assert part in text, (path, part)
    assert 'import("/web/fullscreen.js")' in await (await client.get("/design")).text()
    for script in ("/hub/hub.js", "/hub/perf.js"):
        text = await (await client.get(script)).text()
        assert 'from "/web/fullscreen.js"' in text and "fullscreenButton(" in text, script


async def test_a_drawing_resolution_per_screen(aiohttp_client):
    """?res= or Settings → This device: the designed hub's canvases, the 3D arm and AI Control's
    drawing at fewer pixels, scaled up by the screen (for the Newline; focus step 1)."""
    client = await aiohttp_client(make_app())
    design = await (await client.get("/design")).text()
    assert 'params.get("res") ?? screenPrefs().res' in design and "S.dpr = drawRes()" in design
    assert "Math.min(devicePixelRatio || 1, 2);\n  W = innerWidth" not in design  # not fixed now
    screen = await (await client.get("/web/screen.js")).text()
    assert "export function drawRes" in screen and "prefs().res" in screen  # this device's
    for path in ("/static/arm/arm-view.js", "/hub/ai.js"):
        text = await (await client.get(path)).text()
        assert 'from "/web/screen.js"' in text and "drawRes()" in text, path
    settings = await (await client.get("/hub/settings.js")).text()
    assert 'key: "res"' in settings and '"auto", "1", "0.75", "0.5"' in settings


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


async def test_training_starts_only_when_safe_and_only_here(aiohttp_client, monkeypatch):
    from lab_os import green

    started = []
    monkeypatch.setattr(green, "open_terminal", lambda: started.append(1))
    monkeypatch.setattr(green, "remember", lambda c: None)
    unsafe = green.Check([(False, "unplug so101-white")])
    monkeypatch.setattr(green, "check", lambda: unsafe)
    client = await aiohttp_client(make_app())
    assert (await client.get("/training")).status == 200
    got = await (await client.get("/api/green")).json()
    assert got["ok"] is False and got["here"] is True
    res = await (await client.post("/api/green/start")).json()
    assert res["started"] is False and not started  # refused: nothing opened

    monkeypatch.setattr(green, "check", lambda: green.Check([(True, "fine")]))
    assert (await (await client.post("/api/green/start")).json())["started"] is True
    assert started == [1]

    monkeypatch.setattr(hub_server, "is_local", lambda request: False)  # another screen
    assert (await client.post("/api/green/start")).status == 403
    assert started == [1]


def test_teleop_3d_view_and_joints_in_their_own_boxes():
    """Quick job 14: a jog names only the joints that move; the readout still keeps one row per
    joint (fixed height, notes cut with …) in a column beside the 3D view, so the view never
    resizes. Checked in headless Chrome on 2026-11-14 (one view size over 10 s of jogging)."""
    web = Path(__file__).resolve().parents[1] / "src" / "lab_os" / "teleop" / "web"
    js = (web / "arm" / "arm-panel.js").read_text()
    css = (web / "pages.css").read_text()
    assert 'class="arm3d-body"' in js and 'class="arm-readout"' in js
    assert "shown.set(name" in js and "feed.status?.joints" in js  # every joint keeps its row
    assert "<table" not in js
    body = css.split(".arm3d-body {", 1)[1].split("}", 1)[0]
    assert "grid-template-columns: minmax(0, 1fr) 15rem" in body  # the readout: a fixed column
    row = css.split(".jrow {", 1)[1].split("}", 1)[0]
    assert "grid-template-rows: 1.35rem 1.05rem" in row  # every row the same height
    assert "text-overflow: ellipsis" in css.split(".jf {", 1)[1].split("}", 1)[0]
    assert css.index(
        "@media (max-width: 900px), (orientation: portrait) {\n  /* narrow: the readout"
    ) > css.index(".arm3d-body {")


def test_x_stop_is_shown_where_you_look():
    """Quick job 19: while desktop control is on, "X = STOP" sits beside the STOP button, the X row
    is the key help's first row and the on-button says it. Hidden while X doesn't stop (it only
    works in desktop control), so the page never claims what isn't true."""
    web = Path(__file__).resolve().parents[1] / "src" / "lab_os" / "teleop" / "web"
    js = (web / "desktop-input.js").read_text()
    start = js.split("function startControl", 1)[1].split("function stopControl")[0]
    stop = js.split("function stopControl", 1)[1].split("function tick")[0]
    assert "stopKey(true)" in start and "stopKey(false)" in stop
    assert "(X = STOP, \\` to leave)" in js  # escaped: the text is inside a `template`
    assert 'link.send({ type: "stop" }); // X = STOP in every mode' in js
    for page in ("index.html", "classic/index.html"):
        html = (web / page).read_text()
        key = html.index('id="stop-key"')
        assert 'id="stop-key" class="stop-key" hidden' in html, page
        assert abs(key - html.index('id="stop"')) < 400, page  # right beside STOP
        table = html.split('<table class="keys">', 1)[1]
        assert table.index("<kbd>X</kbd>") < table.index('id="desk-keys"'), page  # first row
        assert "<kbd>Esc</kbd>" in table, page


def test_backtick_leaves_desktop_control_like_esc():
    """Backtick (`) frees the pointer and ends desktop control, the same as Esc (2026-11-17): a key
    no mode uses, so leaving doesn't need a reach to Esc. Esc stays (browsers always allow it)."""
    web = Path(__file__).resolve().parents[1] / "src" / "lab_os" / "teleop" / "web"
    js = (web / "desktop-input.js").read_text()
    keydown = js.split('document.addEventListener("keydown"', 1)[1].split("keyup")[0]
    leave = keydown.split('e.code === "Escape" || e.code === "Backquote"', 1)[1].split("return;")[0]
    assert "document.exitPointerLock()" in leave
    assert js.count("Backquote") == 1  # no mode uses the key for anything else
    assert "(X = STOP, \\` to leave)" in js  # escaped: the text is inside a `template`
    node = shutil.which("node")
    if node:  # a bare ` inside the button's template string once broke the whole script
        subprocess.run([node, "--check", str(web / "desktop-input.js")], check=True)
    for page in ("index.html", "classic/index.html"):
        table = (web / page).read_text().split('<table class="keys">', 1)[1].split("</table>")[0]
        assert "<kbd>`</kbd> or <kbd>Esc</kbd>" in table, page


def test_settings_scroll_down_not_off_to_the_side():
    """Quick job 21: the settings page (also what the designed hub's ⚙ opens) used CSS columns in a
    box of fixed height, so every section after "This device" (the AI budget, the safety limits)
    spilled into columns off to the right, out of reach: 4612 px of page in a 1526 px box at
    1600×900 (headless Chrome, 2026-11-17). Then a grid that scrolls down; since quick job 38 one
    list of groups beside a sidebar, scrolling down."""
    html = (Path(__file__).resolve().parents[1] / "src/lab_os/hub/web/settings.html").read_text()
    rule = html.split("#list {", 1)[1].split("}", 1)[0]
    assert "columns:" not in rule and "overflow-y: auto" in rule
