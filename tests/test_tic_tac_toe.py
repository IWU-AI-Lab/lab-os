"""Tic-tac-toe (preview 1): the layout, the board drawn on the stand camera's picture, and the
robot's turn on the fake arm (take a piece from each start spot, put one down in each cell) through
the robot tools' own checks. No hardware."""

import asyncio
import io
import math

import pytest
from PIL import Image
from test_table_map import _jpeg, _plain_map

from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.tools import robot as robot_tools
from lab_os.tools import table_map, tic_tac_toe
from lab_os.tools.robot import Refused, RobotTools
from lab_os.venues import Venue

GAME = tic_tac_toe.load()  # the repo's own layout: config/games/tic-tac-toe.yaml


def test_the_layout_names_the_cells_like_a_page_seen_from_behind_the_arm():
    cells = GAME.cells()
    assert list(cells) == ["A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3"]
    cx, cy = GAME.center_cm
    s = GAME.cell_cm
    assert cells["B2"] == (cx, cy)
    assert cells["A1"] == (cx + s, cy + s)  # far, on the arm's left: top left in the picture
    assert cells["C3"] == (cx - s, cy - s)
    assert len(GAME.robot_start_cm) == 5  # five pieces each
    summary = GAME.summary()
    assert summary["cells_cm"]["A1"] == {"x": cx + s, "y": cy + s}
    assert f"height_cm={GAME.height_cm:g}" in summary["to_take_a_piece"]


def test_start_spots_are_off_the_board_and_apart():
    half = GAME.cell_cm * 1.5
    cx, cy = GAME.center_cm
    for x, y in GAME.robot_start_cm:
        assert abs(x - cx) > half + 1 or abs(y - cy) > half + 1, (x, y)  # 1 cm clear of the paper
    spots = GAME.robot_start_cm
    gaps = [math.dist(a, b) for i, a in enumerate(spots) for b in spots[i + 1 :]]
    assert min(gaps) >= 5.5  # room for the open jaws between pieces


def test_a_broken_or_missing_layout_says_which_file(tmp_path):
    with pytest.raises(tic_tac_toe.NoGame, match="doesn't exist"):
        tic_tac_toe.load(tmp_path / "nope.yaml")
    bad = tmp_path / "bad.yaml"
    bad.write_text("board: {center_cm: [20, 0]}\n")
    with pytest.raises(tic_tac_toe.NoGame, match="bad.yaml"):
        tic_tac_toe.load(bad)


# ---------- the robot's turn on the fake arm ----------


async def make():
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState(), speed_scale=1.0)
    venue = Venue("test", ("fake-arm",), True, 1.0, ai_tools={"deg_per_s": 900})
    return RobotTools(loop, venue, {"ws": None}), asyncio.create_task(loop.run())  # real poses


async def go(tools, x, y, z, angle):
    """move_to again until it arrives, as the AI does (at most 10 cm a call)."""
    for _ in range(8):
        r = await tools.call("move_to", x_cm=x, y_cm=y, z_cm=z, tool_angle_deg=angle)
        assert r["result"] in ("arrived", "stopped_short"), r
        p = r["gripper_point_cm"]
        if math.dist((p["x"], p["y"], p["z"]), (x, y, z)) < 0.6:
            return r
    raise AssertionError(f"never got to {(x, y, z)}: {r}")


async def to_pose(tools, name):
    """go_to_pose again until it's all the way there (at most 30° a joint per call)."""
    for _ in range(8):
        r = await tools.call("go_to_pose", name=name)
        assert r["result"] in ("arrived", "stopped_short"), r
        if not any(c.startswith("went") for c in r.get("clipped", [])):
            return
    raise AssertionError(f"never got to {name}")


# the steps the AI is given (Layout.summary), one function each
Z, A = GAME.travel_z_cm, GAME.place_tool_angle_deg
PARK, VIA = (*GAME.park_cm, Z), (*GAME.via_cm, Z)


async def at_the_start(tools):
    await to_pose(tools, "ready")
    p = (await tools.call("arm_status"))["gripper_point_cm"]
    await go(tools, p["x"], p["y"], Z, A)
    await go(tools, *VIA, A)
    await go(tools, *PARK, 180)


async def take(tools, spot):
    x, y = spot
    await go(tools, *VIA, A)
    await go(tools, x, y, Z, 180)
    r = await tools.call("pick_at", x_cm=x, y_cm=y, height_cm=GAME.height_cm)
    assert [s["step"][:3] for s in r["steps"]] == ["1/5", "2/5", "3/5", "4/5", "5/5"], r
    return r


async def put_down(tools, cell):
    x, y = GAME.cells()[cell]
    await go(tools, *VIA, A)
    await go(tools, x, y, Z, A)
    r = await go(tools, x, y, GAME.height_cm / 2 + 0.5, A)
    assert r["result"] == "arrived", r
    r = await tools.call("gripper", open_pct=GAME.release_open_pct)
    assert r["result"] == "arrived", r
    await go(tools, x, y, Z, A)
    await go(tools, *VIA, A)
    await go(tools, *PARK, 180)


@pytest.mark.parametrize("cell", list(GAME.cells()))
async def test_a_robot_turn_to_each_cell_on_the_fake_arm(cell):
    """From the start, take a piece (each start spot in turn) and put it down in the cell, along
    the route: nothing refused, and only the step down into that cell goes below the travel height
    over the paper. One cell per test, so the parallel test workers share them."""
    i = list(GAME.cells()).index(cell)
    tools, task = await make()
    try:
        await at_the_start(tools)
        n = len(tools.calls.entries)
        r = await take(tools, GAME.robot_start_cm[i % len(GAME.robot_start_cm)])
        assert r["result"] == "missed"  # the fake jaws close on nothing
        await put_down(tools, cell)
        if cell == "C3":
            await to_pose(tools, "home")  # at the end, with the board cleared
    finally:
        task.cancel()
    refused = [e for e in tools.calls.entries if e["outcome"] in ("refused", "error")]
    assert not refused, refused
    cx, cy = GAME.center_cm
    half = GAME.cell_cm * 1.5
    low = set()
    for e in tools.calls.entries[n:]:
        p = e["result"].get("gripper_point_cm") if isinstance(e["result"], dict) else None
        on_paper = p and abs(p["x"] - cx) <= half and abs(p["y"] - cy) <= half
        if on_paper and p["z"] < Z - 0.6 and e["tool"] != "go_to_pose":
            low.add((round(p["x"]), round(p["y"])))
    x, y = GAME.cells()[cell]
    assert low == {(round(x), round(y))}, low


# ---------- the board on the picture ----------


def test_the_board_is_drawn_on_a_picture_of_the_same_shape_only():
    m = _plain_map()  # 10 px = 1 cm, x forward = up the picture, base at (320, 460)
    after = Image.open(io.BytesIO(tic_tac_toe.draw(_jpeg(), m, GAME)))
    assert after.size == (640, 480)
    cx, cy = GAME.center_cm
    edge_x = cx + GAME.cell_cm * 1.5  # the board's far edge, on its middle column
    r, g, b = after.getpixel((round(320 - cy * 10), round(460 - edge_x * 10)))
    assert r > 150 and b > 150 and g < 120  # magenta
    sx, sy = GAME.robot_start_cm[0]
    ring = after.getpixel((round(320 - sy * 10), round(460 - (sx + 2) * 10)))
    assert ring[1] > 150 and ring[0] < 120  # green
    assert tic_tac_toe.draw(_jpeg(640, 640), m, GAME) == _jpeg(640, 640)


@pytest.fixture
def snap(tmp_path, monkeypatch):
    from lab_os import devices

    monkeypatch.setattr(table_map, "map_path", lambda cam: tmp_path / f"{cam}.yaml")
    monkeypatch.setattr(devices, "camera_device", lambda cam: "/dev/video-fake")
    monkeypatch.setattr(robot_tools, "_grab_jpeg", lambda path, w, cam: _jpeg())
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState())
    return RobotTools(loop, Venue("lab", (), True, 0.5), {"ws": None}, poses={})


async def test_camera_snapshot_with_the_board(snap, monkeypatch, tmp_path):
    r = await snap.call("camera_snapshot", camera="cam", board=True)  # no table map yet
    assert "not drawn" in r["board"]["how_to_read"] and "cells_cm" in r["board"]
    table_map.save(_plain_map())
    grid_only = (await snap.call("camera_snapshot", camera="cam"))["image_jpeg"]
    r = await snap.call("camera_snapshot", camera="cam", board=True)
    assert r["image_jpeg"] != grid_only and "yellow lines = x" in r["table_grid"]
    assert "Magenta squares" in r["board"]["how_to_read"]
    assert set(r["board"]["cells_cm"]) == set(GAME.cells())
    assert len(r["board"]["robot_start_cm"]) == 5
    assert "board" not in await snap.call("camera_snapshot", camera="cam")  # off by default
    monkeypatch.setattr(tic_tac_toe, "path", lambda: tmp_path / "none.yaml")
    with pytest.raises(Refused, match="no tic-tac-toe layout"):
        await snap.call("camera_snapshot", camera="cam", board=True)


async def test_no_camera_still_gives_the_board(snap, monkeypatch):
    """The fake arm has no camera: the board's positions and steps come anyway, so the same
    prompt works; the person says where the pieces are. Without board, still a refusal."""
    from lab_os import devices

    def gone(cam):
        raise LookupError(f"{cam} isn't plugged in")

    monkeypatch.setattr(devices, "camera_device", gone)
    r = await snap.call("camera_snapshot", camera="cam", board=True)
    assert "image_jpeg" not in r and "isn't plugged in" in r["picture"]
    assert "ask the person" in r["picture"] and "route" in r["board"]
    with pytest.raises(Refused, match="isn't plugged in"):
        await snap.call("camera_snapshot", camera="cam")


async def test_the_mcp_tool_gives_the_board_without_a_picture(monkeypatch):
    from lab_os import devices
    from lab_os.tools.mcp_server import create_mcp_server

    monkeypatch.setattr(devices, "camera_device", lambda cam: (_ for _ in ()).throw(LookupError()))
    tools, task = await make()
    try:
        server = create_mcp_server(tools)
        out = await server.call_tool("camera_snapshot", {"camera": GAME.camera, "board": True})
    finally:
        task.cancel()
    text = str(out)
    assert "cells_cm" in text and "image/jpeg" not in text
