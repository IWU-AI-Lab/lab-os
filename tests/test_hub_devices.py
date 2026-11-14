"""Devices (focus step 8): named hub pages, the brain's list, "open on…", each device's settings,
the "Start lab-os" icon. No browser: the pages are WebSocket clients here (the browser check with
headless pages: docs/guides/lab-checklist.md and the PR)."""

import asyncio
import json

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
        ({"module": "nonsense", "device": "desk"}, "isn't one of the hub's modules"),
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
    assert "hub-devices" in str(hub_devices.settings_file().parent)  # conftest's temporary folder


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
