"""Quick job 109: the brain's live device list (lab_os.hub.live_devices) and where it is used: the
Devices panel's list, the Cameras page, the assistant's list_devices, and the seen devices."""

from pathlib import Path

import yaml

from lab_os import devices
from lab_os.devices import Device, Registry, UsbId
from lab_os.hub import live_devices
from lab_os.hub.live_devices import LiveDevices, SeenStore, identify

WHITE = Device(
    "so101-white",
    "so101",
    ports=("/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41532410-if00",),
    usb=(UsbId(0x1A86, 0x55D3, serial="5B41532410"),),
)
LOCKED = Device("locked-arm", "so101", off_limits=True, usb=(UsbId(0x1A86, 0x55D3, serial="X1"),))
WHITE_CAM = Device("so101-white-cam-stand", "camera", socket="usb-0:8")
GREEN_CAM = Device("so101-green-cam-stand", "camera", socket="usb-0:8", borrowed=True)
REG = Registry({d.name: d for d in (WHITE, LOCKED, GREEN_CAM, WHITE_CAM)})


def _usb(root: Path, name: str, vid: str, pid: str, serial="", maker="", product="", cls="00"):
    d = root / name
    d.mkdir(parents=True)
    for f, v in {
        "idVendor": vid,
        "idProduct": pid,
        "serial": serial,
        "manufacturer": maker,
        "product": product,
        "bDeviceClass": cls,
    }.items():
        (d / f).write_text(v + "\n")
    (d / f"{name}:1.0").mkdir()
    return d


def _sysfs(tmp_path):
    usb = tmp_path / "usb"
    _usb(usb, "1-3", "1a86", "55d3", serial="5B41532410", product="USB Single Serial")
    _usb(usb, "1-8", "32e4", "9230", product="USB Camera")
    _usb(usb, "1-2", "046d", "082c", serial="ABC", maker="Logitech", product="HD Webcam C615")
    _usb(usb, "1-4", "0c45", "7403", maker="Card", product="Reader")
    _usb(usb, "1-1", "05e3", "0610", product="USB2.1 Hub", cls="09")  # a hub: not listed
    (usb / "usb1").mkdir()  # a root hub
    video = tmp_path / "video"
    for vname, dev, index, title in (
        ("video0", "1-8", "0", "USB Camera"),
        ("video1", "1-8", "1", "USB Camera"),  # its metadata half
        ("video2", "1-2", "0", "HD Webcam C615"),
    ):
        v = video / vname
        v.mkdir(parents=True)
        (v / "index").write_text(index)
        (v / "name").write_text(title)
        (v / "device").symlink_to(usb / dev / f"{dev}:1.0")
    return usb, video


def test_what_the_computer_sees(tmp_path):
    usb, video = _sysfs(tmp_path)
    found = live_devices.usb_devices(usb)
    assert [d["usb"] for d in found] == ["1-2", "1-3", "1-4", "1-8"]  # no hub, no root hub
    assert found[1]["serial_number"] == "5B41532410" and found[1]["socket"] == "usb-0:3"
    cams = live_devices.video_cameras(video)
    assert [(c["video"], c["usb"], c["socket"]) for c in cams] == [
        ("/dev/video0", "1-8", "usb-0:8"),
        ("/dev/video2", "1-2", "usb-0:2"),
    ]
    assert live_devices.usb_devices(tmp_path / "none") == []  # not Linux: nothing
    assert live_devices.video_cameras(tmp_path / "none") == []


def test_known_and_unknown(tmp_path):
    usb, video = _sysfs(tmp_path)
    found = identify(
        REG, live_devices.usb_devices(usb), live_devices.video_cameras(video), lambda n: 2
    )
    by_id = {d["id"]: d for d in found}
    assert by_id["so101-white"]["kind"] == "arm" and by_id["so101-white"]["known"]
    reader = by_id["usb:0c45:7403:usb-0:4"]
    assert reader["known"] is False and reader["what"] == "Unknown: Card Reader (USB 0c45:7403)"
    # a camera is one entry, not its USB device too; two names for a socket: the white set's first
    cam = by_id["camera:usb-0:8"]
    assert cam["name"] == "so101-white-cam-stand"
    assert cam["names"] == ["so101-white-cam-stand", "so101-green-cam-stand"]
    assert not any(d["id"].startswith("usb:32e4") for d in found)
    webcam = by_id["camera:usb-0:2"]
    assert webcam["name"] == "camera-usb-0-2" and webcam["known"] is False
    assert "HD Webcam C615" in webcam["what"]
    # the camera of the arm in use comes first
    green_first = identify(
        REG,
        [],
        live_devices.video_cameras(video),
        lambda n: 0 if n.startswith("so101-green") else 2,
    )
    assert green_first[0]["name"] == "so101-green-cam-stand"
    # an off-limits arm is left out
    locked = {"vendor_id": 0x1A86, "product_id": 0x55D3, "serial_number": "X1", "usb": "1-9"}
    assert identify(REG, [locked | {"socket": "usb-0:9"}], [], lambda n: 2) == []


def test_a_camera_on_its_arms_hub_has_its_name():
    """Quick job 115: a camera `beside` an arm is the one on its port of the arm's hub."""
    wrist = Device("so101-white-cam-wrist", "camera", beside="so101-white", hub_port="2")
    reg = Registry({d.name: d for d in (WHITE, wrist)})
    arm = {"vendor_id": 0x1A86, "product_id": 0x55D3, "serial_number": "5B41532410"}
    arm |= {"manufacturer": "", "product_string": "", "usb": "1-7.1", "socket": "usb-0:7.1"}
    cams = [{"video": "/dev/video0", "usb": "1-7.2", "socket": "usb-0:7.2", "title": "USB Camera"}]
    by_id = {d["id"]: d for d in identify(reg, [arm], cams, lambda n: 2)}
    assert by_id["camera:usb-0:7.2"]["name"] == "so101-white-cam-wrist"
    alone = {d["id"]: d for d in identify(reg, [], cams, lambda n: 2)}  # the arm is unplugged
    assert alone["camera:usb-0:7.2"]["known"] is False


def test_an_unknown_camera_opens_by_its_socket(tmp_path):
    by_path = tmp_path / "by-path"
    by_path.mkdir()
    (by_path / "pci-0000:00:14.0-usb-0:2:1.0-video-index0").write_text("")
    assert devices.unknown_camera_name("usb-0:3.2") == "camera-usb-0-3.2"
    assert devices.unknown_camera_socket("camera-usb-0-3.2") == "usb-0:3.2"
    assert devices.unknown_camera_socket("camera-usb-x") is None
    paths = devices.camera_paths("camera-usb-0-2", REG, str(by_path))
    assert paths == [str(by_path / "pci-0000:00:14.0-usb-0:2:1.0-video-index0")]
    # a socket that belongs to an off-limits camera stays closed
    locked = Registry({"c": Device("c", "camera", off_limits=True, socket="usb-0:2")})
    try:
        devices.camera_paths("camera-usb-0-2", locked, str(by_path))
    except devices.PortNotAllowed:
        pass
    else:
        raise AssertionError("an off-limits socket was opened")


def test_seen_devices_are_kept_and_removed(tmp_path):
    store = SeenStore(lambda: tmp_path / "local" / "seen-devices.yaml")
    t = [1_700_000_000.0]
    live = LiveDevices(store, clock=lambda: t[0])
    assert live.listing() == []  # it starts empty
    arm = {
        "id": "so101-white",
        "name": "so101-white",
        "kind": "arm",
        "known": True,
        "model": "so101",
    }
    reader = {"id": "usb:0c45:7403:x", "name": "Reader", "kind": "usb", "known": False}
    assert live.update([arm, reader])
    assert not live.update([arm, reader])  # nothing changed: no message to the pages
    assert [d["connected"] for d in live.listing()] == [True, True]
    assert live.update([reader])  # the arm unplugged: still listed, not connected
    gone = next(d for d in live.listing() if d["id"] == "so101-white")
    assert gone["connected"] is False and gone["last_seen"]
    kept = yaml.safe_load((tmp_path / "local" / "seen-devices.yaml").read_text())["devices"]
    assert set(kept) == {"so101-white", "usb:0c45:7403:x"}
    # a new brain reads the list back
    restored = {d["id"]: d for d in LiveDevices(store).listing()}
    assert set(restored) == {"so101-white", "usb:0c45:7403:x"}
    assert restored["so101-white"]["model"] == "so101"
    # removed while connected: off the list until it connects again
    assert live.remove("usb:0c45:7403:x") and not live.remove("nothing")
    live.update([reader])
    assert [d["id"] for d in live.listing()] == ["so101-white"]
    live.update([])
    live.update([reader])
    assert {d["id"] for d in live.listing()} == {"so101-white", "usb:0c45:7403:x"}


async def test_the_brain_list_and_its_users(aiohttp_client, monkeypatch, tmp_path):
    """The brain looks, pushes the list to the hub pages, and the API, the Cameras page and the
    assistant's list_devices tell the same story."""
    from test_hub_server import make_app

    from lab_os.hub import server

    usb, video = _sysfs(tmp_path)
    monkeypatch.setattr(
        server,
        "scan_system",
        lambda: (live_devices.usb_devices(usb), live_devices.video_cameras(video), []),
    )
    client = await aiohttp_client(make_app())
    app = client.app
    async with client.ws_connect("/ws/hub-device?device=desk&window=w-test1") as ws:
        await ws.receive_json()  # welcome
        await server.look_at_devices(app)  # (the brain's own look may have come first)
        names: set = set()
        while "desk" not in names:  # the screen that just opened is on the list too
            msg = await ws.receive_json(timeout=5)
            if msg["type"] == "live-devices":
                names = {d["name"] for d in msg["devices"]}
        assert {"so101-white", "Reader", "camera-usb-0-2", "desk"} <= names
        assert not await server.look_at_devices(app)  # nothing new: no message
    got = (await (await client.get("/api/live-devices")).json())["devices"]
    arm = next(d for d in got if d["id"] == "so101-white")
    assert arm["connected"] and arm["kind"] == "arm"
    cams = (await (await client.get("/api/cameras")).json())["cameras"]
    # socket 8 is the green set's stand camera: the white set's are on the white arm's hub (115)
    assert [c["id"] for c in cams] == ["so101-green-cam-stand", "camera-usb-0-2"]
    listed = app[server.TOOLS_PROJECT].list_devices()
    white = next(d for d in listed["devices"] if d["name"] == "so101-white")
    green = next(d for d in listed["devices"] if d["name"] == "so101-green")
    assert white["connected"] is True and green["connected"] is False
    assert "fake-arm" not in {d["name"] for d in listed["devices"] if "connected" in d}
    assert any(d["name"] == "Reader" for d in listed["other_connected"])
    assert "so101-white" in server.lab_status(app)["devices_connected"]
    # Remove: off the panel's list
    r = await client.post("/api/live-devices/remove", json={"id": "usb:0c45:7403:usb-0:4"})
    assert r.status == 200
    assert "Reader" not in {d["name"] for d in (await r.json())["devices"]}
    assert (await client.post("/api/live-devices/remove", json={"id": "nope"})).status == 404


def test_the_motors_power_of_a_driven_arm():
    from lab_os.hub.server import _arm_power

    class Loop:
        arm_connected, arm_problem, health_ok, health = True, None, None, None

    each = Loop()
    assert _arm_power(each)["power"] is None  # not read yet
    each.health_ok, each.health = True, {"gripper": {"volts": 12.1}, "elbow_flex": {"volts": 11.9}}
    assert _arm_power(each) == {"driven": True, "problem": None, "power": "on", "volts": 11.9}
    each.health_ok = False
    assert _arm_power(each)["power"] == "off"
    each.arm_connected, each.arm_problem = False, "its USB was unplugged"
    assert _arm_power(each) == {"driven": True, "problem": "its USB was unplugged", "power": None}


def test_the_pages_use_the_list():
    src = Path(__file__).parents[1] / "src" / "lab_os"
    design = (src / "hub" / "web" / "design.html").read_text()
    assert "/api/live-devices" in design and "onLive:" in design and "data-remove" in design
    assert '"live-devices"' in (src / "web" / "device.js").read_text()
    cameras = (src / "hub" / "web" / "cameras.html").read_text()
    assert "LIST_MS" in cameras and "stream" in cameras
    assert "unplugged" in (src / "teleop" / "web" / "monitor.js").read_text()


def test_parts_built_into_the_computer_are_left_out(tmp_path):
    """Quick job 141: the lab desktop's Bluetooth and keyboard light are not devices to list."""
    usb, _ = _sysfs(tmp_path)
    (_usb(usb, "1-14", "8087", "0033") / "removable").write_text("fixed\n")
    (usb / "1-3" / "removable").write_text("removable\n")
    assert [d["usb"] for d in live_devices.usb_devices(usb)] == ["1-2", "1-3", "1-4", "1-8"]


def test_a_quest_by_its_teleop_page_and_an_arm_in_use(monkeypatch):
    """Quick job 141: a Quest on Wi-Fi without adb shows by its teleop page; an arm the brain
    doesn't drive says "in use" while another program has its port (the port is not opened)."""
    from lab_os.hub import server

    quest = Device("quest-a", "quest", serial="2G97", host="192.168.8.180")
    reg = Registry({d.name: d for d in (WHITE, quest)})
    monkeypatch.setattr(server, "load_registry", lambda: reg)
    monkeypatch.setattr(server, "users_of", lambda port: ["lelab (pid 42)"])

    class Loop:
        left = None
        arm = Device("fake-arm", "fake")
        arm_connected = True

    class Hub:
        def listing(self):
            return []

    quest_ua = "Mozilla/5.0 (X11; Linux x86_64; Quest 3) OculusBrowser/157"
    app = {
        server.LOOP: Loop(),
        server.HUB_DEVICES: Hub(),
        server.LINKS: {
            1: {"remote": "192.168.8.180", "agent": quest_ua, "device": ""},
            2: {"remote": "192.168.8.99", "agent": quest_ua, "device": ""},
            3: {"remote": "127.0.0.1", "agent": "Chrome desktop", "device": "desk"},
        },
    }
    usb = [{"vendor_id": 0x1A86, "product_id": 0x55D3, "serial_number": "5B41532410",
            "usb": "1-3", "socket": "usb-0:3"}]  # fmt: skip
    in_use = server.ports_in_use(usb)
    assert in_use == {"so101-white": ["lelab (pid 42)"]}
    got = {d["id"]: d for d in server.live_entries(app, usb, [], ["2G97"], in_use)}
    assert got["so101-white"]["power"] == "in use" and "lelab" in got["so101-white"]["problem"]
    assert got["quest-a"]["via"] == "adb (USB)"  # adb first; its teleop page adds no second one
    assert got["quest:192.168.8.99"]["known"] is False
    assert len([d for d in got.values() if d["kind"] == "headset"]) == 2
    got = {d["id"]: d for d in server.live_entries(app, usb, [], [], {})}
    assert got["quest-a"]["via"] == "Arm Control page (network)"
    assert "power" not in got["so101-white"]
