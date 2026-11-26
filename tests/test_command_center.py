"""The Command Center (quick job 134, docs/design/command-center.md): its page, the workspace's
layout (only the picture) and the teleop permission (which devices may drive a real arm)."""

import yaml
from test_hub_devices import page  # same folder (pytest puts it on the path)
from test_hub_server import SRC, make_app

from lab_os import config
from lab_os.hub import command_center
from lab_os.hub.command_center import LayoutStore, clean_layout
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
    assert 'id="ws"' in html and 'id="devices"' in html and 'id="screens"' in html
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
    assert "function pick(key, add)" in js and "function focus(key)" in js
    assert 'classList.contains("foc")) focus(node)' in js  # focus only from its own mark
    assert 'b.className = `btn small${a.real ? "" : " virtual"}`' in js
    assert "/api/hub-devices/open" in js and "/api/hub-devices/close" in js
    assert 'data-k="display_name"' in js
