"""The Command Center (quick job 134, docs/design/command-center.md): its page, the workspace's
layout (only the picture) and the teleop permission (which devices may drive a real arm)."""

import asyncio
import re

import yaml
from test_hub_devices import page, settle  # same folder (pytest puts it on the path)
from test_hub_server import SRC, make_app

from lab_os import config
from lab_os.activity import ACTIVITY, Activity
from lab_os.hub import command_center, hub_devices
from lab_os.hub.command_center import LayoutStore, clean_layout
from lab_os.hub.live_devices import LiveDevices, SeenStore
from lab_os.teleop.server import DRIVE_FROM


def test_layout_keeps_only_what_it_may(tmp_path):
    raw = {
        "places": {
            "d:desk": [10, 20.04],
            "s:desk#2": ["x", 1],
            "bad key!": [1, 2],
            "l:a": [1e9, 0],
        },
        "hidden": ["l:usb:1a86", "no spaces allowed"],
        "groups": {"s:quest#1": "l:quest-a", "s:x#1": "not ok!"},
        "other": 1,
    }
    got = clean_layout(raw)
    assert got == {
        "places": {"d:desk": [10.0, 20.0], "l:a": [100000.0, 0.0]},
        "hidden": ["l:usb:1a86"],
        "groups": {"s:quest#1": "l:quest-a"},
    }
    store = LayoutStore(lambda: tmp_path / "local" / "command-center.yaml")
    assert store.read() == {"places": {}, "hidden": [], "groups": {}}
    store.write(raw)
    assert store.read() == got
    (tmp_path / "local" / "command-center.yaml").write_text("places: [broken")
    assert store.read()["places"] == {}  # a broken file: an empty workspace, no error


async def test_page_and_layout(aiohttp_client):
    client = await aiohttp_client(make_app())
    html = await (await client.get("/command-center")).text()
    for part in ("ws", "devices", "pages", "insp"):  # quick job 148: Pages and the inspector
        assert f'id="{part}"' in html
    assert (await client.get("/hub/command-center.js")).status == 200
    hub = await (await client.get("/api/hub")).json()
    assert "/command-center" in {p["path"] for p in hub["pages"]}  # All Pages
    assert {"id": "command", "title": "Command Center", "page": "/command-center"} in hub["views"]
    state = await (await client.get("/api/command-center")).json()
    assert state["layout"] == {"places": {}, "hidden": [], "groups": {}}
    assert state["drive_from"] == []  # make_app gives no --drive-from
    lay = {"places": {"d:desk": [5, 6]}, "hidden": ["s:desk#1"], "groups": {}}
    r = await (await client.post("/api/command-center/layout", json=lay)).json()
    assert r["ok"] and r["layout"]["places"] == {"d:desk": [5.0, 6.0]}
    kept = yaml.safe_load((config.local_dir() / "command-center.yaml").read_text())
    assert kept["hidden"] == ["s:desk#1"]


async def test_only_on_the_brains_computer(aiohttp_client, monkeypatch):
    """Another screen can't open the page, see the layout or give itself the right to drive."""
    import lab_os.hub.server as server

    client = await aiohttp_client(make_app())
    monkeypatch.setattr(command_center, "on_this_computer", lambda request: False)
    monkeypatch.setattr(server, "on_this_computer", lambda request: False)
    resp = await client.get("/command-center")
    assert resp.status == 403 and "only on the brain's own computer" in await resp.text()
    assert (await client.get("/api/command-center")).status == 403
    drive = {"addresses": ["192.168.8.50"], "allowed": True}
    assert (await client.post("/api/command-center/drive", json=drive)).status == 403
    assert (await client.post("/api/command-center/layout", json={})).status == 403
    assert (await client.get("/api/command-center/activity")).status == 403


async def test_teleop_permission(aiohttp_client):
    """Allow driving: the brain's set at once, and local/place.yaml for the next start; stop
    driving takes it out of both. place.yaml's other entries stay."""
    app = make_app()
    client = await aiohttp_client(app)
    listed = list(config.load_place().drive_from)
    r = await (
        await client.post(
            "/api/command-center/drive", json={"addresses": ["192.168.8.50"], "allowed": True}
        )
    ).json()
    assert r["ok"] and "192.168.8.50" in r["drive_from"] and "192.168.8.50" in app[DRIVE_FROM]
    assert list(config.load_place().drive_from) == [*listed, "192.168.8.50"]
    assert "drive_from" in (config.local_dir() / "place.yaml").read_text()
    r = await (
        await client.post(
            "/api/command-center/drive", json={"addresses": ["192.168.8.50"], "allowed": False}
        )
    ).json()
    assert r["ok"] and "192.168.8.50" not in app[DRIVE_FROM]
    assert list(config.load_place().drive_from) == listed
    bad = {"addresses": ["not an address; rm"], "allowed": True}
    assert (await client.post("/api/command-center/drive", json=bad)).status == 400


async def test_screens_carry_their_size(aiohttp_client):
    """Each screen's resolution and whether it is the brain's own computer, for the previews."""
    client = await aiohttp_client(make_app())
    screen = {"left": 0, "top": 0, "width": 1600, "height": 900, "ratio": 1.25}
    ws, _ = await page(client, "newline", screen=screen)
    got = (await (await client.get("/api/hub-devices")).json())["devices"]
    newline = next(d for d in got if d["name"] == "newline")
    assert newline["here"] is True  # the test client is on this computer
    assert newline["windows"][0]["screen"]["width"] == 1600
    assert newline["windows"][0]["screen"]["ratio"] == 1.25
    await ws.close()


def test_the_page_keeps_its_rules():
    """Highlight never opens the focus modal; real and workspace-only actions look different."""
    js = (SRC / "hub" / "web" / "command-center.js").read_text()
    assert "function pick(key, add)" in js and "function focus(key, keep = false)" in js
    assert 'classList.contains("foc")) focus(node)' in js  # focus only from its own mark
    assert 'b.className = `btn small${a.real ? "" : " virtual"}`' in js
    assert "/api/hub-devices/open" in js and "/api/hub-devices/close" in js
    assert "/api/hub-devices/start" in js and "#start-all" in js  # quick job 139
    assert 'data-k="display_name"' in js
    # quick job 148: one drag carrier for every kind of pointer; a drop opens the page there
    assert "const carry = {" in js and "start(view, x, y)" in js and "drop(x, y)" in js
    assert "function openPageOn(view, key)" in js and "function renderInspector(" in js


def test_a_page_opens_at_once_and_follows_other_devices():
    """Quick job 167: a choice in a page list, or a press on a page tile while a screen is
    highlighted, opens the page at once (no Open button); the lists, the tiles and the focus window
    follow a change that another device makes; All to the Start Screen keeps the robot pages;
    M and S are in the inspector and the focus window, which is a grid."""
    js = (SRC / "hub" / "web" / "command-center.js").read_text()
    html = (SRC / "hub" / "web" / "command-center.html").read_text()
    assert "if (sel.value) { a.run(sel.value); after(); }" in js
    assert 'label: one ? "Open"' not in js and not re.search(r"S\.page\b", js)
    assert "function choosePage(id) {\n  const targets = selectedScreens(" in js
    assert "syncPageSelects();" in js and "refreshFocus();" in js and "markTiles();" in js
    keep = '["teleop", "webcam", "raspbot", "ai", "training", "command"]'
    assert f"const KEEP_OPEN = new Set({keep});" in js
    assert 'id="all-idle"' in html and "All to the Start Screen" in html  # quick job 168
    assert '"/api/hub-devices/idle"' in js and "NO_NAME_SOUND" in js
    assert 'part(s ? `Sound (${esc(sd.title)})` : "Sound", soundBlock(sd))' in js
    assert "${hasSound(d) ? `<h3>Sound</h3>${soundBlock(d)}`" in js
    assert ".fgrid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));" in html
    assert 'class="fscreens"' in js and "<h3>Modules</h3>" in js


# ---------- quick job 149: the activity list, the devices that are off ----------
def test_activity_keeps_the_newest_first():
    t = [100.0]
    act = Activity(clock=lambda: t[0], size=3)
    for word in ("a", "b", "c", "d"):
        t[0] += 1
        act.add(f"pi7  {word}\n", "page")
    assert [e["text"] for e in act.recent()] == [
        "pi7 d",
        "pi7 c",
        "pi7 b",
    ]  # names stay as they are
    assert act.recent()[0] == {"t": 104.0, "text": "pi7 d", "kind": "page"}
    act.add("   ")
    assert len(act.recent()) == 3  # an empty line is not an event


def test_devices_that_come_and_go_are_noted(tmp_path):
    act = Activity()
    live = LiveDevices(SeenStore(lambda: tmp_path / "seen.yaml"), activity=act)
    arm = {"id": "so101-white", "name": "so101-white", "kind": "arm"}
    screen = {"id": "screen:desk", "name": "desk", "kind": "screen"}
    live.update([arm, screen])
    live.update([screen])
    assert [e["text"] for e in act.recent()] == [
        "so101-white disconnected",
        "so101-white connected",
    ]
    off = next(d for d in live.listing() if d["id"] == "so101-white")
    assert off["connected"] is False and off["last_seen"]  # the Command Center's dim card


async def test_screens_opening_pages_are_noted(aiohttp_client, monkeypatch):
    """A page that wakes reports nothing for a moment: no "went back to the hub" for that."""
    monkeypatch.setattr(hub_devices, "BACK_QUIET_S", 0.05)
    app = make_app()
    client = await aiohttp_client(app)
    texts = lambda: [e["text"] for e in app[ACTIVITY].recent()]  # noqa: E731
    ws, _ = await page(client, "pi7")
    assert texts() == ["pi7 opened the hub"]
    await ws.send_json({"type": "state", "showing": None})  # waking: nothing yet
    await ws.send_json({"type": "state", "showing": "teleop", "from": "desk"})
    await settle(client)
    await asyncio.sleep(0.1)
    assert texts()[0] == "pi7 opened Teleop (from desk)" and len(texts()) == 2
    await ws.send_json({"type": "state", "showing": None})
    await settle(client)
    await asyncio.sleep(0.1)
    assert texts()[0] == "pi7 went back to the hub"
    await ws.close()
    await settle(client)
    assert texts()[0] == "pi7 closed the hub"
    got = await (await client.get("/api/command-center/activity")).json()
    assert got["events"][0]["text"] == "pi7 closed the hub"


async def test_stop_is_noted(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws?role=monitor")
    await ws.send_json({"type": "stop"})
    for _ in range(50):
        if app[ACTIVITY].recent():
            break
        await asyncio.sleep(0.01)
    assert app[ACTIVITY].recent()[0]["text"].startswith("STOP pressed")
    assert app[ACTIVITY].recent()[0]["kind"] == "stop"
    await ws.close()


# ---------- quick job 140: the way in on the brain's hub, and the opening ----------
async def test_the_way_in_is_on_the_brains_hub_only(aiohttp_client, monkeypatch):
    import lab_os.hub.server as server

    client = await aiohttp_client(make_app())
    assert (await (await client.get("/api/hub")).json())["here"] is True
    monkeypatch.setattr(server, "on_this_computer", lambda request: False)
    assert (await (await client.get("/api/hub")).json())["here"] is False
    hub = (SRC / "hub" / "web" / "design.html").read_text()
    assert 'id="cc-launch"' in hub and 'data-module="command"' in hub
    assert '$("#cc-launch").hidden = !(hub?.here && S.page.command)' in hub  # not on other screens
    assert 'id === "command" ? $("#cc-launch")' in hub  # it unfolds from there, also by voice


async def test_there_is_no_opening(aiohttp_client):
    """Quick job 164: the builder removed the opening (it was clunky); it is in docs/archive/."""
    client = await aiohttp_client(make_app())
    assert (await client.get("/hub/command-center-intro.js")).status == 404
    js = (SRC / "hub" / "web" / "command-center.js").read_text()
    html = await (await client.get("/command-center")).text()
    assert "playIntro" not in js and "#intro" not in html and 'class="page wait"' not in html
    hub = (SRC / "hub" / "web" / "design.html").read_text()
    assert "lab-os-sfx" not in hub  # its sounds came through the hub
