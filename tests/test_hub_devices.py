"""Devices (focus step 8): named hub pages, the brain's list, "open on…", each device's settings,
the "Start lab-os" icon. No browser: the pages are WebSocket clients here (the browser check with
headless pages: docs/guides/lab-checklist.md and the PR)."""

import asyncio
import http.server
import json
import threading

import pytest
from test_hub_server import SRC, make_app  # same folder (pytest puts it on the path)

from lab_os import cli
from lab_os.hub import hub_devices, launch
from lab_os.hub.hub_devices import DeviceError, DeviceSettings, clean_name


async def page(client, device: str, window: str = "", screen: dict | None = None, **state):
    """A hub page: connects, reads the welcome, says hello."""
    ws = await client.ws_connect(f"/ws/hub-device?device={device}&window={window}")
    welcome = await ws.receive_json(timeout=2)
    assert welcome["type"] == "welcome"
    hello = {"type": "hello", "look": "design", "stage": "hub", "showing": None, **state}
    if screen:
        hello["screen"] = screen
    await ws.send_json(hello)
    await settle(client)
    return ws, welcome


async def settle(client, n: int = 10):
    for _ in range(n):  # let the brain read what the pages sent
        await asyncio.sleep(0.01)


async def next_of(ws, kind: str, until=lambda msg: True) -> dict:
    while True:
        msg = await ws.receive_json(timeout=2)
        if msg["type"] == kind and until(msg):
            return msg


def test_names():
    assert clean_name(" Desk ") == "desk"
    assert clean_name("pi01") == "pi01"
    for bad in ("", "-desk", "the desk", "a" * 33, "desk!"):
        with pytest.raises(DeviceError):
            clean_name(bad)


async def test_the_brain_lists_the_devices_with_the_hub_open(aiohttp_client):
    client = await aiohttp_client(make_app())
    desk, welcome = await page(client, "desk")
    assert welcome["device"] == "desk" and welcome["window"]
    newline, _ = await page(client, "newline")
    nameless, _ = await page(client, "")  # a page with no name: not offered as a place to open
    got = await (await client.get("/api/hub-devices")).json()
    assert [d["name"] for d in got["devices"]] == ["desk", "newline"]
    assert got["devices"][0]["windows"][0]["stage"] == "hub"
    await newline.close()
    await settle(client)
    got = await (await client.get("/api/hub-devices")).json()
    assert [d["name"] for d in got["devices"]] == ["desk"]
    await desk.close()
    await nameless.close()


async def test_a_copied_tab_gets_its_own_window(aiohttp_client):
    client = await aiohttp_client(make_app())
    a, wa = await page(client, "desk", window="w-same1")
    b, wb = await page(client, "desk", window="w-same1")
    assert wa["window"] == "w-same1" and wb["window"] != "w-same1"
    await a.close()
    await b.close()


async def test_open_on_another_device_and_bring_it_back(aiohttp_client):
    client = await aiohttp_client(make_app())
    desk, _ = await page(client, "desk")
    newline, nw = await page(client, "newline")
    r = await client.post(
        "/api/hub-devices/open",
        json={
            "module": "monitor",
            "device": "desk",
            "from": "newline",
            "from_window": nw["window"],
        },
    )
    out = await r.json()
    assert out["ok"] and out["message"] == "Monitor is open on desk."
    msg = await next_of(desk, "open")
    assert msg == {
        "type": "open",
        "module": "monitor",
        "from": "newline",
        "from_window": nw["window"],
    }
    # the sender sees it's there: "bring it back"
    listed = await next_of(newline, "devices", lambda m: m["devices"][0]["windows"][0]["showing"])
    shown = listed["devices"][0]["windows"][0]
    assert shown["showing"] == {"id": "monitor", "title": "Monitor"}
    assert shown["from"] == "newline"
    sent = (await (await client.get("/api/hub-devices")).json())["sent"]
    assert sent[0]["device"] == "desk" and sent[0]["showing"]["id"] == "monitor"
    r = await client.post(
        "/api/hub-devices/close", json={"device": "desk", "window": out["window"]}
    )
    assert (await r.json())["ok"]
    assert (await next_of(desk, "close")) == {"type": "close"}
    assert (await (await client.get("/api/hub-devices")).json())["sent"] == []
    await desk.close()
    await newline.close()


async def test_open_on_refuses_what_it_cant_do(aiohttp_client):
    client = await aiohttp_client(make_app())
    desk, _ = await page(client, "desk")
    for body, words in (
        ({"module": "monitor", "device": "newline"}, "doesn't have the hub open"),
        ({"module": "nonsense", "device": "desk"}, "isn't a page that opens on a device"),
        ({"module": "monitor", "device": "Not A Name"}, "isn't a device name"),
    ):
        r = await client.post("/api/hub-devices/open", json=body)
        assert r.status == 400 and words in (await r.json())["message"], body
    await desk.close()


async def test_a_device_with_two_monitors_picks_the_free_one_or_asks(aiohttp_client):
    client = await aiohttp_client(make_app())
    left, _ = await page(client, "desk", screen={"left": 0, "top": 0, "width": 1920})
    right, rw = await page(client, "desk", screen={"left": 1920, "top": 0, "width": 1920})
    newline, _ = await page(client, "newline")
    r = await (
        await client.post("/api/hub-devices/open", json={"module": "monitor", "device": "desk"})
    ).json()
    assert not r["ok"] and r["message"] == "desk has 2 monitors free: which one?"
    assert [w["label"] for w in r["ask"]] == ["left monitor", "right monitor"]
    # the right one is busy now: the left one is picked without asking
    await right.send_json({"type": "state", "showing": "teleop"})
    await settle(client)
    r = await (
        await client.post("/api/hub-devices/open", json={"module": "monitor", "device": "desk"})
    ).json()
    assert r["ok"] and r["label"] == "left monitor"
    assert (await next_of(left, "open"))["module"] == "monitor"
    # both busy: asked again; picking one replaces what it shows
    r = await (
        await client.post("/api/hub-devices/open", json={"module": "ai", "device": "desk"})
    ).json()
    assert "every monitor" in r["message"]
    r = await (
        await client.post(
            "/api/hub-devices/open",
            json={"module": "ai", "device": "desk", "window": rw["window"]},
        )
    ).json()
    assert r["ok"] and r["label"] == "right monitor"
    for ws in (left, right, newline):
        await ws.close()


async def test_a_device_can_send_to_its_own_other_monitor(aiohttp_client):
    client = await aiohttp_client(make_app())
    left, lw = await page(client, "desk", screen={"left": 0})
    right, _ = await page(client, "desk", screen={"left": 1920})
    r = await (
        await client.post(
            "/api/hub-devices/open",
            json={
                "module": "monitor",
                "device": "desk",
                "from": "desk",
                "from_window": lw["window"],
            },
        )
    ).json()
    assert r["ok"] and r["label"] == "right monitor"  # never the window that sent it
    await left.close()
    await right.close()


async def test_one_busy_monitor_asks_before_replacing(aiohttp_client):
    client = await aiohttp_client(make_app())
    desk, _ = await page(client, "desk", showing="teleop")
    r = await (
        await client.post("/api/hub-devices/open", json={"module": "monitor", "device": "desk"})
    ).json()
    assert not r["ok"] and r["message"] == "desk is showing Teleop: replace it?"
    assert r["ask"][0]["label"] == "desk"
    await desk.close()


async def test_each_device_keeps_its_settings_under_its_name(aiohttp_client, tmp_path):
    store = DeviceSettings(lambda: tmp_path / "hub-devices.yaml")
    client = await aiohttp_client(make_app(device_settings=store))
    one, _ = await page(client, "newline")
    two, _ = await page(client, "newline", screen={"left": 1920})  # its second monitor
    r = await client.post("/api/hub-devices/newline/settings", json={"res": "0.5", "sound": False})
    assert (await r.json())["settings"] == {"res": "0.5", "sound": False}
    for ws in (one, two):  # every window of the device gets them at once
        assert (await next_of(ws, "settings"))["settings"] == {"res": "0.5", "sound": False}
    # the next page under that name gets them in its welcome, also after a restart (the file)
    _, welcome = await page(client, "newline")
    assert welcome["settings"] == {"res": "0.5", "sound": False}
    assert "newline:" in (tmp_path / "hub-devices.yaml").read_text()
    again = DeviceSettings(lambda: tmp_path / "hub-devices.yaml")
    assert again.get("newline") == {"res": "0.5", "sound": False}
    # back to the default
    r = await client.post("/api/hub-devices/newline/settings", json={"res": ""})
    assert (await r.json())["settings"] == {"sound": False}
    got = await (await client.get("/api/hub-devices/newline/settings")).json()
    assert got["settings"] == {"sound": False}
    for bad in ({"res": "9"}, {"colour": "red"}, {"sound": "yes"}, {}):
        r = await client.post("/api/hub-devices/newline/settings", json=bad)
        assert r.status == 400, bad
    await one.close()
    await two.close()


def test_tests_never_write_the_repos_device_settings():
    from lab_os import config

    assert config.DEFAULT_DIR not in hub_devices.settings_file().parents  # conftest's temporary
    assert hub_devices.settings_file().parent == config.local_dir()


async def test_pages_reconnect_after_the_brain_restarts(aiohttp_client):
    """The list lives in the pages: a new brain knows a device again as soon as its page is back."""
    first = await aiohttp_client(make_app())
    desk, welcome = await page(first, "desk", showing="monitor", **{"from": "newline"})
    await first.close()  # the brain stops
    second = await aiohttp_client(make_app())  # and starts again, empty
    assert (await (await second.get("/api/hub-devices")).json())["devices"] == []
    back, again = await page(
        second, "desk", window=welcome["window"], showing="monitor", **{"from": "newline"}
    )
    assert again["window"] == welcome["window"]  # the same window, so "bring it back" still works
    got = await (await second.get("/api/hub-devices")).json()
    assert got["sent"][0]["from"] == "newline"
    await back.close()


def test_the_hub_pages_join_as_devices():

    web = SRC / "hub" / "web"
    for name, look in (("hub.js", '"plain"'), ("design.html", '"design"')):
        text = (web / name).read_text()
        assert "connectDevice(" in text and f"look: {look}" in text, name
        assert "fillOpenOn(" in text and "fillSent(" in text, name
    device = (SRC / "web" / "device.js").read_text()
    assert "/ws/hub-device" in device and "setTimeout(open, retry)" in device  # reconnects
    settings = (web / "settings.js").read_text()
    assert "setPref" in settings
    assert "This device" in (web / "settings.html").read_text()
    for name in ("screen.js", "voice.js"):  # the readers use the device's settings
        assert 'from "/web/device.js"' in (SRC / "web" / name).read_text(), name


def test_start_icon(tmp_path, monkeypatch):
    path = launch.write_icon("desk", ["--arm", "so101-white"], folder=tmp_path)
    text = path.read_text()
    assert "Name=Start lab-os" in text
    assert "serve --open desk --host 0.0.0.0 --arm so101-white" in text
    assert launch.start_command("desk", ["--host", "127.0.0.1"])[-2:] == ["--host", "127.0.0.1"]
    assert launch.hub_url(8080, "desk") == "http://localhost:8080/?device=desk"


def test_serve_open_only_opens_when_a_brain_already_runs(monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(launch, "brain_answers", lambda port: True)
    monkeypatch.setattr(launch, "bring_to_front", lambda device, port: None)  # no window yet
    monkeypatch.setattr(launch, "open_hub", lambda url: opened.append(url) or f"opened {url}")
    cli.main(["serve", "--open", "Desk", "--port", "8095"])
    assert opened == ["http://localhost:8095/?device=desk"]
    assert "already runs" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="isn't a device name"):
        cli.main(["serve", "--open", "the desk"])


def test_device_settings_reject_junk_in_the_file(tmp_path):
    f = tmp_path / "hub-devices.yaml"
    f.write_text("devices: [not, a, map]\n")
    assert DeviceSettings(lambda: f).get("desk") == {}
    f.write_text(": : :\n")
    assert DeviceSettings(lambda: f).get("desk") == {}
    json.dumps(DeviceSettings(lambda: f).update("desk", {"quality": "minimal"}))
    assert "minimal" in f.read_text()


def test_the_wake_word_sensitivity_is_a_device_setting(tmp_path):
    s = DeviceSettings(lambda: tmp_path / "hub-devices.yaml")
    assert s.update("quest", {"wake_sensitivity": 8}) == {"wake_sensitivity": 8}
    for junk in (True, 10, 0, "8"):
        with pytest.raises(DeviceError, match="wake_sensitivity can be 1, 2"):
            s.update("quest", {"wake_sensitivity": junk})
    assert s.update("quest", {"wake_sensitivity": ""}) == {}  # back to the default (5)


def test_the_assistant_languages_are_device_settings(tmp_path):
    s = DeviceSettings(lambda: tmp_path / "hub-devices.yaml")
    assert s.update("desk", {"hear_in": "en", "answer_in": "en"}) == {
        "hear_in": "en",
        "answer_in": "en",
    }
    with pytest.raises(DeviceError, match="hear_in can be"):
        s.update("desk", {"hear_in": "fr"})
    assert s.update("desk", {"hear_in": "", "answer_in": ""}) == {}  # back to any


class _FakeDevTools(http.server.BaseHTTPRequestHandler):
    """lab-os's own browser, as its DevTools port answers."""

    targets: list = []
    activated: list = []
    closed: list = []

    def do_GET(self):  # noqa: N802 (the http.server name)
        if self.path == "/json/list":
            body = json.dumps(self.targets).encode()
        elif self.path.startswith("/json/activate/"):
            self.activated.append(self.path.rsplit("/", 1)[1])
            body = b"Target activated"
        elif self.path.startswith("/json/close/"):
            self.closed.append(self.path.rsplit("/", 1)[1])
            body = b"Target is closing"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_a_second_tap_brings_the_one_hub_window_to_the_front(tmp_path, monkeypatch, capsys):
    """Quick job 59: the icon opens no second window while lab-os's own one is open."""
    cmd = launch.browser_command("http://localhost:8080/?device=desk", profile=tmp_path)
    if cmd:  # a Chromium browser on this computer: lab-os's own profile, DevTools on any free port
        assert f"--user-data-dir={tmp_path}" in cmd and "--remote-debugging-port=0" in cmd
    assert launch.bring_to_front("desk", 8080, profile=tmp_path) is None  # no browser runs
    (tmp_path / "DevToolsActivePort").write_text("1\n/devtools/browser/x\n")  # left behind
    assert launch.bring_to_front("desk", 8080, profile=tmp_path) is None

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _FakeDevTools)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    (tmp_path / "DevToolsActivePort").write_text(f"{server.server_port}\n/devtools/browser/x\n")
    _FakeDevTools.targets = [
        {"id": "other", "type": "page", "url": "https://example.com/?device=desk"},
        {"id": "sent", "type": "page", "url": "http://localhost:8080/monitor?device=newline"},
        {"id": "hub", "type": "page", "url": "http://localhost:8080/design?device=desk"},
        {"id": "worker", "type": "service_worker", "url": "http://localhost:8080/sw.js"},
    ]
    try:
        assert [t["id"] for t in launch.hub_windows("desk", 8080, profile=tmp_path)] == [
            "hub",
            "sent",
        ]
        assert "front" in launch.bring_to_front("desk", 8080, profile=tmp_path)
        assert _FakeDevTools.activated == ["hub"]

        opened = []
        monkeypatch.setattr(launch, "PROFILE", tmp_path)
        monkeypatch.setattr(launch, "brain_answers", lambda port: True)
        monkeypatch.setattr(launch, "open_hub", lambda url: opened.append(url) or "opened")
        cli.main(["serve", "--open", "desk", "--port", "8080"])
        assert opened == [] and "to the front" in capsys.readouterr().out
        assert _FakeDevTools.activated == ["hub", "hub"]

        # quick job 64: Shut down and Ctrl+C close lab-os's own windows for this brain only
        assert launch.close_hub_windows(8080, profile=tmp_path) == 2
        assert sorted(_FakeDevTools.closed) == ["hub", "sent"]
        assert launch.close_hub_windows(8099, profile=tmp_path) == 0
    finally:
        server.shutdown()


async def test_the_brain_puts_its_own_windows_full_screen(aiohttp_client, monkeypatch, tmp_path):
    """Quick job 74: a page sent to another monitor, and the hub that sent it, full screen without
    a press: the brain asks lab-os's own browser. Elsewhere it says why, and the page asks."""
    from lab_os.hub import server as hub_server

    monkeypatch.setattr(launch, "PROFILE", tmp_path)  # no lab-os browser runs
    client = await aiohttp_client(make_app())
    url = "http://localhost:8080/monitor?screen=1"
    got = await (await client.post("/api/window-state", json={"url": url})).json()
    assert not got["ok"] and "lab-os's own browser" in got["why"]
    assert (await client.post("/api/window-state", json={"state": "normal"})).status == 400
    assert "Unknown" in await launch.set_window_state(url, "maximized", tmp_path)
    asked = []

    async def fake_state(u, state, profile=None):
        asked.append((u, state))
        return ""

    monkeypatch.setattr(launch, "set_window_state", fake_state)
    got = await (await client.post("/api/window-state", json={"url": url})).json()
    assert got == {"ok": True, "why": ""} and asked == [(url, "fullscreen")]
    monkeypatch.setattr(hub_server, "is_local", lambda request: False)  # another computer
    got = await (await client.post("/api/window-state", json={"url": url})).json()
    assert not got["ok"] and len(asked) == 1


def test_pages_choose_full_screen_or_a_window():
    """Quick job 74: an app window is not full screen (it matched "standalone", so the button never
    showed); module pages on their own screen choose Full screen or Window."""
    fs = (SRC / "web" / "fullscreen.js").read_text()
    full_by_other = fs.split("export const fullByOther")[1].split(";")[0]
    assert "standalone" not in full_by_other and "/api/window-state" in fs
    kit = (SRC / "web" / "design" / "kit.js").read_text()
    assert "lab-os.window:" in kit and 'brainWindow("fullscreen")' in kit and "Window`" in kit
    design = (SRC / "hub" / "web" / "design.html").read_text()
    assert "wasFull" in design and 'brainWindow("fullscreen")' in design


async def test_set_up_the_room(aiohttp_client, monkeypatch, tmp_path):
    """Quick job 71: room.yaml says which device shows which page; one call opens each on its
    device, as "Open on…" does, and skips and names a device that isn't connected."""
    from lab_os import config
    from lab_os.hub import room

    layout = tmp_path / "room.yaml"
    layout.write_text(
        "layout:\n  newline: core\n  pi-1: monitor\n  pi-2: teleop\n  win-1: nonsense\n"
    )
    real = config.layers
    monkeypatch.setattr(
        config,
        "layers",
        lambda name, *a, **k: [layout] if name == "room.yaml" else real(name, *a, **k),
    )
    client = await aiohttp_client(make_app())
    newline, _ = await page(client, "newline", showing="teleop")
    pi1, _ = await page(client, "pi-1")
    win1, _ = await page(client, "win-1")
    got = await (await client.post("/api/room/setup")).json()
    assert [o["device"] for o in got["opened"]] == ["newline", "pi-1"]
    assert {s["device"]: s["why"] for s in got["skipped"]} == {
        "pi-2": "not connected (its hub isn't open)",
        "win-1": "'nonsense' isn't a page that opens on a device",
    }
    assert "Monitor on pi-1" in got["message"] and "Skipped: pi-2" in got["message"]
    assert (await next_of(pi1, "open"))["module"] == "monitor"
    assert (await next_of(newline, "close"))["type"] == "close"  # the core: nothing opened
    # the assistant's tool does the same
    desk = room.RoomDesk(lambda: client.app[hub_devices_key()])
    assert desk.tools(False)[0]["function"]["name"] == "set_up_room"
    said, _ = await desk.call("set_up_room", False)
    assert "Set up the room" in said
    for ws in (newline, pi1, win1):
        await ws.close()


def hub_devices_key():
    from lab_os.hub.server import HUB_DEVICES

    return HUB_DEVICES


def test_the_room_layout_file_and_the_ways_in():
    from lab_os.hub import room

    pairs = room.load_layout()  # the repo's config/room.yaml: the recommended layout
    assert ("newline", "core") in pairs and all(p for _, p in pairs)
    assert "roomRow()" in (SRC / "hub" / "web" / "settings.js").read_text()
    with pytest.raises(SystemExit, match="didn't answer on port 1"):
        cli.main(["room", "--port", "1"])


def test_device_settings_save_without_a_local_folder(tmp_path):
    """Quick job 60 found it: in a fresh copy of lab-os there's no config/local/ yet, and the first
    device setting failed ("No such file or directory"). The folder is made on the first save."""
    store = DeviceSettings(lambda: tmp_path / "local" / "hub-devices.yaml")
    store.update("quest-a", {"sound": False})
    assert (tmp_path / "local" / "hub-devices.yaml").exists()


async def test_every_view_opens_on_a_device(aiohttp_client):
    """The builder, 2026-11-21: "all the pages should be able to open on a device": not only the
    module buttons, also webcam teleop, the details pages, the system diagram, the conversation."""
    from lab_os.hub.server import DEVICE_VIEWS

    client = await aiohttp_client(make_app())
    views = {v["id"]: v for v in (await (await client.get("/api/hub")).json())["views"]}
    assert {"webcam", "spend", "commits", "project", "devices", "system", "chat", "xr"} <= set(
        views
    )
    assert views["webcam"]["page"] == "/webcam" and views["spend"]["page"] == ""
    newline, welcome = await page(client, "newline")
    for view in ("spend", "system", "webcam", "chat"):
        ask = {"module": view, "device": "newline", "window": welcome["window"]}
        r = await (await client.post("/api/hub-devices/open", json=ask)).json()
        assert r["ok"] and DEVICE_VIEWS[view][0] in r["message"], view
        assert (await next_of(newline, "open"))["module"] == view
    await newline.close()
    design = (SRC / "hub" / "web" / "design.html").read_text()
    assert "function viewEl(id)" in design and "setViews(hub?.views" in design
    assert "S.views" in (SRC / "hub" / "web" / "hub.js").read_text()
