"""The stand camera's table map (focus item 6): a printed ChArUco sheet → pixels to table cm, a cm
grid on the camera's pictures, `table_point`. No camera: the sheet is drawn and seen in perspective
in code. The detection tests need OpenCV (the `so101` extra) and are skipped without it."""

import io

import numpy as np
import pytest
from PIL import Image

from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.tools import robot as robot_tools
from lab_os.tools import table_map
from lab_os.tools.robot import Refused, RobotTools
from lab_os.tools.table_map import TableMap
from lab_os.venues import Venue

SQ_PX = 60  # one square on the drawn sheet
MARGIN = 30
ORIGIN = (29.0, 5.25)
# The drawn sheet's corners → where a camera behind the arm sees them (far edge small, at the top)
VIEW_DST = np.float32([[520, 160], [760, 160], [900, 620], [380, 620]])
CAM = (1280, 720)


def _sheet_px_of(x_cm, y_cm):
    """Where table (x, y) cm is on the drawn sheet image (corner 0 = ORIGIN)."""
    u0 = v0 = MARGIN + SQ_PX  # the first inner corner
    k = SQ_PX / 3.5  # px per cm
    return u0 + (ORIGIN[1] - y_cm) * k, v0 + (ORIGIN[0] - x_cm) * k


def _view():
    """The camera's picture of the sheet, and the sheet → camera homography."""
    cv2 = pytest.importorskip("cv2")
    sheet = table_map.board_image(SQ_PX, MARGIN)
    h, w = sheet.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    hv = cv2.getPerspectiveTransform(src, VIEW_DST)
    cam = cv2.warpPerspective(sheet, hv, CAM, borderValue=200)
    return cv2.cvtColor(cam, cv2.COLOR_GRAY2BGR), hv


def _camera_px_of(hv, x_cm, y_cm):
    u, v = _sheet_px_of(x_cm, y_cm)
    p = hv @ (u, v, 1.0)
    return p[0] / p[2], p[1] / p[2]


def test_the_sheet_seen_in_perspective_maps_pixels_to_table_cm():
    image, hv = _view()
    m = table_map.calibrate(image, "cam", ORIGIN)
    assert m.corners == 24 and m.worst_mm < 1.0 and table_map.fit_ok(m)
    for x, y in [(29, 5.25), (20, 0), (25, -5), (12, 3)]:  # on the sheet and off it
        got = m.to_table(*_camera_px_of(hv, x, y))
        assert got == pytest.approx((x, y), abs=0.2)
        back = m.to_pixels(x, y)
        assert back == pytest.approx(_camera_px_of(hv, x, y), abs=1.0)


def test_a_smaller_picture_maps_the_same_place():
    image, hv = _view()
    m = table_map.calibrate(image, "cam", ORIGIN)
    u, v = _camera_px_of(hv, 22, -2)
    assert m.to_table(u / 2, v / 2, width_px=CAM[0] // 2) == pytest.approx((22, -2), abs=0.3)


def test_no_sheet_says_what_to_check():
    pytest.importorskip("cv2")
    blank = np.full((480, 640, 3), 180, np.uint8)
    with pytest.raises(table_map.BoardNotFound, match="whole sheet in the picture"):
        table_map.calibrate(blank, "cam")


def test_a_scaled_print_uses_the_measured_square():
    """A printer that shrank the sheet to 97 %: with the measured square the cm stay right."""
    image, hv = _view()
    m = table_map.calibrate(image, "cam", ORIGIN, square_mm=35 * 0.97)
    far = m.to_table(*_camera_px_of(hv, 29 - 3.5 * 6, 5.25))  # 6 squares toward the arm
    assert far[0] == pytest.approx(29 - 3.5 * 6 * 0.97, abs=0.2)


# ---------- without OpenCV: a known map ----------


def _plain_map(camera="cam"):
    """A map where 10 px = 1 cm, x forward = up the picture, base at pixel (320, 460)."""
    h = np.linalg.inv(np.array([[0, -10, 320], [-10, 0, 460], [0, 0, 1]], dtype=float))
    return TableMap(camera, h.tolist(), 640, 480, ORIGIN, 35.0, 24, 0.4, "2026-11-16T12:00:00")


def _jpeg(w=640, h=480):
    out = io.BytesIO()
    Image.new("RGB", (w, h), (90, 90, 90)).save(out, "JPEG")
    return out.getvalue()


def test_pixels_and_cm_round_trip():
    m = _plain_map()
    assert m.to_table(320, 460) == pytest.approx((0, 0))
    assert m.to_table(320, 160) == pytest.approx((30, 0))
    assert m.to_table(220, 160) == pytest.approx((30, 10))  # left in the picture = the arm's left
    assert m.to_pixels(30, 10, width_px=320) == pytest.approx((110, 80))


def test_the_grid_is_drawn_on_a_picture_of_the_same_shape_only():
    m = _plain_map()
    before = _jpeg()
    after = Image.open(io.BytesIO(table_map.draw_grid(before, m)))
    assert after.size == (640, 480)
    assert after.getpixel((320, 160)) != (90, 90, 90)  # x30 crosses y0 there
    assert after.getpixel((320, 460))[0] > 200  # the red dot at the base
    assert table_map.draw_grid(_jpeg(640, 640), m) == _jpeg(640, 640)  # another shape: untouched


def test_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setattr(table_map, "map_path", lambda cam: tmp_path / f"{cam}.yaml")
    assert table_map.load("cam") is None
    table_map.save(_plain_map())
    m = table_map.load("cam")
    assert m == _plain_map()
    (tmp_path / "cam.yaml").write_text("not: [a map")
    assert table_map.load("cam") is None  # broken file: as if none


# ---------- the tools ----------


@pytest.fixture
def tools(tmp_path, monkeypatch):
    monkeypatch.setattr(table_map, "map_path", lambda cam: tmp_path / f"{cam}.yaml")
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState())
    return RobotTools(loop, Venue("lab", (), True, 0.5), {"ws": None}, poses={})


async def test_table_point_needs_a_map_and_gives_cm(tools):
    with pytest.raises(Refused, match="no table map"):
        await tools.table_point("cam", 320, 160)
    table_map.save(_plain_map())
    r = await tools.table_point("cam", 320, 160)
    assert r["table_cm"] == {"x": 30.0, "y": 0.0}
    r = await tools.table_point("cam", 160, 80, width_px=320)
    assert r["table_cm"] == {"x": 30.0, "y": 0.0}
    with pytest.raises(Refused):
        await tools.table_point("cam", float("nan"), 3)


async def test_camera_snapshot_gets_the_grid_when_the_camera_has_a_map(tools, monkeypatch):
    from lab_os import devices

    monkeypatch.setattr(devices, "camera_device", lambda cam: "/dev/video-fake")
    monkeypatch.setattr(robot_tools, "_grab_jpeg", lambda path, w, cam: _jpeg())
    r = await tools.camera_snapshot("cam")
    assert r["image_jpeg"] == _jpeg() and "no table map" in r["table_grid"]
    table_map.save(_plain_map())
    r = await tools.camera_snapshot("cam")
    assert r["image_jpeg"] != _jpeg() and "yellow lines = x" in r["table_grid"]
    r = await tools.camera_snapshot("cam", grid=False)
    assert r["image_jpeg"] == _jpeg() and "table_grid" not in r
