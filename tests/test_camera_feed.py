"""Quick job 63: camera pictures on the teleop page. No camera: the device check, the camera and
the JPEG encoder are faked."""

import time

import pytest
from test_hub_server import make_app  # same folder (pytest puts it on the path)

from lab_os import camera_feed, devices
from lab_os.camera_feed import CameraError, CameraFeeds, arm_cameras
from lab_os.devices import Device, Registry


class FakeCapture:
    def __init__(self, path):
        self.path, self.released, self.reads = path, False, 0

    def read(self):
        self.reads += 1
        time.sleep(0.01)
        return True, f"frame {self.reads}"

    def release(self):
        self.released = True


@pytest.fixture
def feeds(monkeypatch):
    monkeypatch.setattr(camera_feed, "IDLE_S", 0.3)
    opened: list[FakeCapture] = []
    busy: set[str] = set()

    def device(name):
        if name in busy:
            raise devices.InUse(f"{name} is in use by lelab (pid 42): one program per port.")
        if name == "unplugged":
            raise LookupError("unplugged: not plugged in")
        return {
            "white-cam-stand": "/dev/v4l/by-path/usb-0:8",
            "green-cam-stand": "/dev/v4l/by-path/usb-0:8",
        }.get(name, f"/dev/{name}")

    def capture(path):
        opened.append(FakeCapture(path))
        return opened[-1]

    f = CameraFeeds(device=device, capture=capture, encode=lambda frame, w: frame.encode())
    f.opened, f.busy = opened, busy
    yield f
    f.close_all()


def test_a_camera_opens_when_asked_and_closes_when_nobody_looks(feeds):
    assert feeds.jpeg("white-cam-stand").startswith(b"frame")
    assert len(feeds.opened) == 1 and feeds.frame("white-cam-stand") is not None
    feeds.jpeg("white-cam-stand")
    assert len(feeds.opened) == 1  # still open: the same reader
    time.sleep(0.6)  # nobody asked for longer than IDLE_S
    assert feeds.opened[0].released and feeds.frame("white-cam-stand") is None
    feeds.jpeg("white-cam-stand")
    assert len(feeds.opened) == 2  # opened again on the next picture


def test_two_names_for_one_socket_share_one_reader(feeds):
    feeds.jpeg("white-cam-stand")
    feeds.jpeg("green-cam-stand")
    assert len(feeds.opened) == 1


def test_a_camera_another_program_has_is_refused(feeds):
    feeds.busy.add("white-cam-wrist")
    with pytest.raises(CameraError, match="in use by lelab"):
        feeds.jpeg("white-cam-wrist")
    with pytest.raises(CameraError, match="not plugged in"):
        feeds.jpeg("unplugged")
    assert feeds.opened == []  # nothing was opened


def test_an_arms_cameras_by_name():
    reg = Registry(
        {
            "so101-white": Device("so101-white", "so101"),
            "so101-white-cam-wrist": Device("so101-white-cam-wrist", "camera", socket="usb-0:7"),
            "so101-white-cam-stand": Device("so101-white-cam-stand", "camera", socket="usb-0:8"),
            "so101-green-cam-stand": Device("so101-green-cam-stand", "camera", socket="usb-0:8"),
        }
    )
    assert arm_cameras("so101-white", reg) == ["so101-white-cam-stand", "so101-white-cam-wrist"]
    assert arm_cameras("fake-arm", reg) == []


async def test_the_brain_serves_the_pictures(aiohttp_client, feeds, monkeypatch):
    from lab_os.hub.server import FEEDS

    app = make_app()
    app[FEEDS] = feeds
    client = await aiohttp_client(app)
    cams = await (await client.get("/api/arm-cameras")).json()
    assert cams == {"arm": "fake-arm", "cameras": []}  # the fake arm has none
    res = await client.get("/api/camera-feed/white-cam-stand")
    assert res.status == 200 and res.content_type == "image/jpeg"
    assert res.headers["Cache-Control"] == "no-store"
    feeds.busy.add("white-cam-wrist")
    res = await client.get("/api/camera-feed/white-cam-wrist")
    assert res.status == 409 and "in use by lelab" in await res.text()


def test_the_teleop_page_shows_them_under_the_joints():
    from test_hub_server import SRC

    web = SRC / "teleop" / "web"
    assert 'id="arm-cams"' in (web / "arm" / "arm-panel.js").read_text()
    assert "initCams(link)" in (web / "teleop-page.js").read_text()
    cams = (web / "cams.js").read_text()
    assert "/api/camera-feed/" in cams and "document.hidden" in cams  # only while it's shown


def test_every_camera_once_for_each_socket():
    """Quick job 93: two names for one socket are one camera on the Cameras page."""
    reg = Registry(
        {
            "so101-green-cam-wrist": Device("so101-green-cam-wrist", "camera", socket="usb-0:7"),
            "so101-white": Device("so101-white", "so101"),
            "so101-white-cam-wrist": Device("so101-white-cam-wrist", "camera", socket="usb-0:7"),
            "so101-white-cam-stand": Device("so101-white-cam-stand", "camera", socket="usb-0:8"),
            "secret-cam": Device("secret-cam", "camera", off_limits=True, socket="usb-0:9"),
            "new-cam": Device("new-cam", "camera"),  # no socket yet: shown, its picture says why
            "hub-cam": Device("hub-cam", "camera", beside="so101-white", hub_port="2"),
            "hub-cam-2": Device("hub-cam-2", "camera", beside="so101-white", hub_port="2"),
        }
    )
    assert camera_feed.all_cameras(reg) == [
        {
            "id": "so101-green-cam-wrist",
            "names": ["so101-green-cam-wrist", "so101-white-cam-wrist"],
        },
        {"id": "so101-white-cam-stand", "names": ["so101-white-cam-stand"]},
        {"id": "new-cam", "names": ["new-cam"]},
        {"id": "hub-cam", "names": ["hub-cam", "hub-cam-2"]},  # one port of the arm's hub
    ]
    assert camera_feed.all_cameras(Registry({})) == []


async def test_the_cameras_page(aiohttp_client, monkeypatch):
    """Quick job 93: the page and its list; it asks only for the pictures it shows, and keeps the
    switches for each device."""
    from test_hub_server import SRC

    monkeypatch.setattr(
        camera_feed,
        "all_cameras",
        lambda: [{"id": "white-cam-stand", "names": ["white-cam-stand"]}],
    )
    client = await aiohttp_client(make_app())
    got = await (await client.get("/api/cameras")).json()
    assert got["cameras"][0]["id"] == "white-cam-stand"
    page = await (await client.get("/cameras")).text()
    assert "/web/design/kit.css" in page and "/api/cameras" in page
    assert "/api/camera-feed/" in page and "document.hidden" in page
    assert 'setPref("cameras_hidden"' in page and "There is no camera" in page
    views = (await (await client.get("/api/hub")).json())["views"]
    assert {"id": "cameras", "title": "Cameras", "page": "/cameras"} in views
    # a button around the core (the builder, 2026-11-23), with its icon in the designed hub
    assert {"id": "cameras", "title": "Cameras", "page": "/cameras"} in (
        await (await client.get("/api/hub")).json()
    )["modules"]
    assert (
        'cameras: ["Cameras", "i-cam", "page"]' in (SRC / "hub" / "web" / "design.html").read_text()
    )


async def test_the_board_drawn_on_the_live_picture(aiohttp_client, monkeypatch):
    """The Cameras page's Board button: the brain draws the tic-tac-toe board on the board
    camera's live pictures (also under another name for its socket), and on no other camera."""
    from test_table_map import _jpeg, _plain_map

    from lab_os.hub import server
    from lab_os.tools import tic_tac_toe

    game = tic_tac_toe.load()
    plain = _jpeg()

    class Feeds:
        def jpeg(self, name):
            return plain

        def close_all(self):
            pass

    monkeypatch.setattr(server.table_map, "load", lambda cam: _plain_map(cam))
    monkeypatch.setattr(
        camera_feed,
        "all_cameras",
        lambda: [
            {"id": "other-cam", "names": [game.camera, "other-cam"]},  # one socket, two names
            {"id": "wrist-cam", "names": ["wrist-cam"]},
        ],
    )
    app = make_app()
    app[server.FEEDS] = Feeds()
    client = await aiohttp_client(app)
    got = (await (await client.get("/api/cameras")).json())["cameras"]
    assert [c["board"] for c in got] == [True, False]
    drawn = await (await client.get("/api/camera-feed/other-cam?board=1")).read()
    assert drawn != plain
    assert await (await client.get("/api/camera-feed/other-cam")).read() == plain
    assert await (await client.get("/api/camera-feed/wrist-cam?board=1")).read() == plain
    monkeypatch.setattr(server.table_map, "load", lambda cam: None)  # no table map: no board
    got = (await (await client.get("/api/cameras")).json())["cameras"]
    assert not any(c["board"] for c in got)
    assert await (await client.get("/api/camera-feed/other-cam?board=1")).read() == plain
    page = await (await client.get("/cameras")).text()
    assert "?board=1" in page and "c.board" in page
