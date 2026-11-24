"""What the Quest sees (quick job 36): scrcpy started and stopped from the hub, on the brain's
computer only. No headset, no download: adb's list and the scrcpy process are stand-ins."""

import io
import tarfile

import pytest

from lab_os import quest_view as qv
from lab_os.devices import Device, Registry, load_registry
from lab_os.hub import server as hub_server
from lab_os.hub.server import QUEST_VIEW, create_brain_app
from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.venues import load_venue

REG = Registry(
    {
        "quest-a": Device("quest-a", "quest", serial="SERIAL_A", mirror=("--fullscreen",)),
        "quest-b": Device("quest-b", "quest", serial="SERIAL_B"),
        "fake-arm": Device("fake-arm", "fake"),
    }
)


class FakeProc:
    def __init__(self, cmd, env=None, **kw):
        self.cmd, self.env, self.returncode, self.ended = cmd, env, None, False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = 0

    def wait(self, timeout=None):
        return 0


@pytest.fixture
def scrcpy(tmp_path, monkeypatch):
    """A downloaded scrcpy (a stand-in file) and a system adb on the PATH."""
    folder = tmp_path / "scrcpy"
    exe = folder / f"scrcpy-linux-x86_64-{qv.VERSION}" / "scrcpy"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    monkeypatch.setattr(qv.shutil, "which", lambda name: "/usr/bin/adb" if name == "adb" else None)
    monkeypatch.setattr(qv.platform, "system", lambda: "Linux")
    return folder


def view(folder, seen=("SERIAL_B",)):
    started = []

    def popen(cmd, env=None, **kw):
        started.append(FakeProc(cmd, env))
        return started[-1]

    v = qv.QuestView(
        folder=folder, registry=lambda: REG, devices=lambda adb: list(seen), popen=popen
    )
    return v, started


def test_starts_the_connected_headset_with_the_system_adb(scrcpy):
    v, started = view(scrcpy)
    s = v.status()
    assert s["installed"] and not s["running"] and s["why_not"] is None
    assert s["headsets"] == [
        {"name": "quest-a", "connected": False, "via": None, "host": ""},
        {"name": "quest-b", "connected": True, "via": "usb", "host": ""},
    ]
    assert v.start() == "quest-b"
    cmd = started[0].cmd
    assert cmd[0].endswith("scrcpy") and "--serial=SERIAL_B" in cmd
    assert {"--no-control", "--no-audio"} <= set(cmd)  # watch only, the headset keeps its sound
    assert "--window-title=Quest view (quest-b)" in cmd and "--video-bit-rate=8M" in cmd
    assert started[0].env["ADB"] == "/usr/bin/adb"  # the same adb server as teleop's adb reverse
    assert v.status()["running"] and v.status()["headset"] == "quest-b"
    assert v.start() == "quest-b" and len(started) == 1  # one window at a time
    assert v.stop() and not v.status()["running"]
    assert not v.stop()


def test_a_headsets_own_options_are_added(scrcpy):
    v, started = view(scrcpy, seen=("SERIAL_A",))
    v.start("quest-a")
    assert started[0].cmd[-1] == "--fullscreen"


def test_says_why_it_cant_start(scrcpy, tmp_path):
    v, _ = view(scrcpy, seen=())
    assert "No headset is connected" in v.status()["why_not"]
    with pytest.raises(qv.QuestViewError, match="No headset"):
        v.start()
    v, _ = view(scrcpy)
    with pytest.raises(qv.QuestViewError, match="quest-a isn't connected"):
        v.start("quest-a")
    empty, _ = view(tmp_path / "nothing")
    assert "isn't installed" in empty.status()["why_not"]
    with pytest.raises(qv.QuestViewError, match="lab-os quest-view --install"):
        empty.start()


def test_a_window_closed_by_hand_counts_as_closed(scrcpy):
    v, started = view(scrcpy)
    v.start()
    started[0].returncode = 0  # someone closed scrcpy's window
    assert not v.status()["running"] and v.headset == ""


def test_the_bundled_adb_only_without_a_system_one(tmp_path, monkeypatch):
    exe = tmp_path / "scrcpy"
    exe.write_text("")
    (tmp_path / "adb").write_text("")
    monkeypatch.setattr(qv.platform, "system", lambda: "Linux")
    monkeypatch.setattr(qv.shutil, "which", lambda name: None)
    assert qv.find_adb(exe) == str(tmp_path / "adb")
    monkeypatch.setattr(qv.shutil, "which", lambda name: "/usr/bin/adb")
    assert qv.find_adb(exe) == "/usr/bin/adb"


def _tarball() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        data = b"#!/bin/sh\n"
        info = tarfile.TarInfo(f"scrcpy-linux-x86_64-{qv.VERSION}/scrcpy")
        info.size, info.mode = len(data), 0o755
        t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_install_checks_the_download_and_remove_deletes_it(tmp_path, monkeypatch):
    data = _tarball()
    monkeypatch.setattr(qv.platform, "system", lambda: "Linux")
    monkeypatch.setattr(qv.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(qv.urllib.request, "urlopen", lambda url, timeout: io.BytesIO(data))
    folder = tmp_path / "downloads" / "scrcpy"
    with pytest.raises(qv.QuestViewError, match="checksum"):  # the pinned sum isn't this file's
        qv.install(folder)
    assert qv.downloaded(folder) is None
    name = qv.ASSETS[("Linux", "x86_64")][0]
    monkeypatch.setitem(qv.ASSETS, ("Linux", "x86_64"), (name, qv.hashlib.sha256(data).hexdigest()))
    program = qv.install(folder)
    assert program == qv.downloaded(folder) and program.read_bytes() == b"#!/bin/sh\n"
    assert not (folder / name).exists()  # the archive itself isn't kept
    assert qv.remove(folder) and not folder.exists()
    assert not qv.remove(folder)


def test_the_labs_headsets_have_their_serials():
    quests = {d.name: d.serial for d in load_registry().devices.values() if d.kind == "quest"}
    assert set(quests) == {"quest-a", "quest-b", "quest-c"} and all(quests.values())


# ---------- on the hub ----------


def make_app(view):
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState())
    return create_brain_app(loop, load_venue("lab"), internet=None, quest_view=view)


async def test_the_hub_starts_and_stops_it(aiohttp_client, scrcpy):
    v, started = view(scrcpy)
    app = make_app(v)
    client = await aiohttp_client(app)
    s = await (await client.get("/api/quest-view")).json()
    assert s["here"] and s["installed"] and not s["running"]
    r = await (await client.post("/api/quest-view/start", json={})).json()
    assert r == {"ok": True, "headset": "quest-b"}
    assert (await (await client.get("/api/quest-view")).json())["running"]
    r = await client.post("/api/quest-view/start", json={"headset": "quest-a"})
    assert r.status == 200  # already open: no second window
    assert (await (await client.post("/api/quest-view/stop")).json())["stopped"]
    r = await client.post("/api/quest-view/start", json={"headset": "quest-a"})
    assert r.status == 400 and "quest-a isn't connected" in (await r.json())["message"]
    assert app[QUEST_VIEW] is v


async def test_only_from_the_brains_computer(aiohttp_client, scrcpy, monkeypatch):
    v, started = view(scrcpy)
    client = await aiohttp_client(make_app(v))
    monkeypatch.setattr(hub_server, "is_local", lambda request: False)
    assert not (await (await client.get("/api/quest-view")).json())["here"]
    assert (await client.post("/api/quest-view/start", json={})).status == 403
    assert (await client.post("/api/quest-view/stop")).status == 403
    assert started == []


def test_adb_reverse_runs_for_each_new_connection():
    """Quick job 73: after each new USB connection the Quest needs `adb reverse` again; the brain
    runs it by itself, once per connection, and says a failure once."""
    from types import SimpleNamespace

    from lab_os.quest_view import AdbReverse

    here: list[str] = []
    ran: list[list[str]] = []
    fail = {"on": False}

    def run(cmd, **kw):
        ran.append(cmd)
        return SimpleNamespace(returncode=1 if fail["on"] else 0, stdout="", stderr="no device")

    rev = AdbReverse(8080, find=lambda: "/usr/bin/adb", devices=lambda adb: list(here), run=run)
    assert rev.check() == [] and ran == []  # no headset
    here.append("2G0YC5ZG")
    assert rev.check() == ["2G0YC5ZG"]
    assert ran == [["/usr/bin/adb", "-s", "2G0YC5ZG", "reverse", "tcp:8080", "tcp:8080"]]
    assert rev.check() == [] and len(ran) == 1  # still connected: not again
    here.clear()
    rev.check()
    here.append("2G0YC5ZG")  # the cable plugged in again
    assert rev.check() == ["2G0YC5ZG"] and len(ran) == 2
    here.append("PHONE1")
    fail["on"] = True
    assert rev.check() == [] and rev.failed == {"PHONE1": "no device"}
    assert AdbReverse(8080, find=lambda: None).check() == []  # no adb: nothing


def test_the_button_follows_the_window():
    """Quick job 49 (F.12): closed with its own X, the window stayed lit on the hub for up to 5 s,
    and a press then only turned the light off. Both hubs ask again on focus, every second while
    it's open, and before acting on a press."""
    from test_hub_server import SRC

    for page in ("hub.js", "design.html"):
        src = (SRC / "hub" / "web" / page).read_text()
        assert 'addEventListener("focus", pollQuestView)' in src, page
        assert "q?.running ? 1000 : 5000" in src, page
        click = src.split('$("#qv-btn").addEventListener("click"', 1)[1].split("});", 1)[0]
        assert "await pollQuestView()" in click and "q.running" in click, page


WIFI_REG = Registry(
    {
        "quest-a": Device("quest-a", "quest", serial="SERIAL_A", host="192.168.8.180"),
        "quest-b": Device("quest-b", "quest", serial="SERIAL_B"),
    }
)


def wifi_view(folder, seen=(), answers=True):
    """Quest view, quest-a on the router's Wi-Fi (quick job 103). `answers`: adb connect works."""
    started, tried = [], []

    def popen(cmd, env=None, **kw):
        started.append(FakeProc(cmd, env))
        return started[-1]

    def connect(adb, address):
        tried.append(address)
        return answers

    v = qv.QuestView(folder=folder, registry=lambda: WIFI_REG, devices=lambda adb: list(seen),
                     popen=popen, connect=connect)  # fmt: skip
    return v, started, tried


def test_usb_stays_the_first_choice(scrcpy):
    """Quick job 103: plugged in, the view comes over USB even when Wi-Fi also reaches it."""
    v, started, tried = wifi_view(scrcpy, seen=("192.168.8.180:5555", "SERIAL_A"))
    assert v.status()["headsets"][0] == {"name": "quest-a", "connected": True, "via": "usb",
                                         "host": "192.168.8.180"}  # fmt: skip
    v.start()
    assert "--serial=SERIAL_A" in started[0].cmd and not tried
    assert v.status()["via"] == "usb"


def test_quest_view_on_wifi_without_the_cable(scrcpy):
    """Quick job 103: no cable, and adb already reaches the headset at its address: the view
    comes over Wi-Fi, at a lower bit rate."""
    v, started, tried = wifi_view(scrcpy, seen=("192.168.8.180:5555",))
    s = v.status()
    assert s["why_not"] is None and s["headsets"][0]["via"] == "wifi"
    assert v.start() == "quest-a"
    cmd = started[0].cmd
    assert "--serial=192.168.8.180:5555" in cmd and "--video-bit-rate=4M" in cmd and not tried
    assert v.status()["via"] == "wifi"
    assert v.stop() and v.status()["via"] == ""


def test_the_press_reaches_the_headset_on_wifi(scrcpy):
    """Not seen yet: the button stays usable (a headset has an address), and the press runs adb
    connect first."""
    v, started, tried = wifi_view(scrcpy)
    assert v.status()["why_not"] is None
    assert v.start() == "quest-a"
    assert tried == ["192.168.8.180:5555"] and "--serial=192.168.8.180:5555" in started[0].cmd


def test_says_why_wifi_did_not_reach_it(scrcpy):
    v, started, tried = wifi_view(scrcpy, answers=False)
    with pytest.raises(qv.QuestViewError) as e:
        v.start()
    msg = str(e.value)
    assert "quest-a at 192.168.8.180:5555" in msg and "uv run lab-os quest-view --wifi" in msg
    assert not started


def test_wifi_switches_a_usb_headset_to_tcp_mode(scrcpy):
    """`lab-os quest-view --wifi`: adb tcpip 5555 for a headset on USB with an address, then adb
    connect; one sentence for each headset on USB."""
    ran = []

    class Done:
        returncode, stdout, stderr = 0, "restarting in TCP mode port: 5555", ""

    def run(cmd, **kw):
        ran.append(cmd)
        return Done()

    reg = Registry(WIFI_REG.devices | {"quest-c": Device("quest-c", "quest", serial="SERIAL_C")})
    said = qv.wifi(registry=lambda: reg, devices=lambda adb: ["SERIAL_A", "SERIAL_C"], run=run,
                   connect=lambda adb, address: address == "192.168.8.180:5555")  # fmt: skip
    assert ran == [["/usr/bin/adb", "-s", "SERIAL_A", "tcpip", "5555"]]
    assert said[0].startswith("quest-a: ready on Wi-Fi at 192.168.8.180:5555")
    assert said[1].startswith("quest-c: no address")
    with pytest.raises(qv.QuestViewError, match="by USB first"):
        qv.wifi(registry=lambda: reg, devices=lambda adb: [], run=run)


def test_the_lab_quest_has_its_wifi_address():
    d = load_registry().devices["quest-a"]
    assert d.host == "192.168.8.180"  # reserved in the router; config/place.yaml drive_from too
