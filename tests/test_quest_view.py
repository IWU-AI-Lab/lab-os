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
        {"name": "quest-a", "connected": False},
        {"name": "quest-b", "connected": True},
    ]
    assert v.start() == "quest-b"
    cmd = started[0].cmd
    assert cmd[0].endswith("scrcpy") and "--serial=SERIAL_B" in cmd
    assert {"--no-control", "--no-audio"} <= set(cmd)  # watch only, the headset keeps its sound
    assert "--window-title=Quest view (quest-b)" in cmd
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
