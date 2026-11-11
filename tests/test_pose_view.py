"""pose_view: a picture of the arm's 3D model in its pose, for an AI without cameras (step 3).
On the fake arm; no hardware, no internet."""

import asyncio
import io

import pytest
from mcp import Client
from PIL import Image
from test_hub_server import make_app  # same folder (pytest puts it on the path)
from test_robot_tools import venue

from lab_os.kinematics import so101_kinematics
from lab_os.robots.fake import SO101_HOME, FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.tools import pose_view as pv
from lab_os.tools.mcp_server import create_mcp_server
from lab_os.tools.robot import Refused, RobotTools


@pytest.fixture
async def rig():
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState(), speed_scale=1.0)
    task = asyncio.create_task(loop.run())
    yield RobotTools(loop, venue(), {"ws": None})
    task.cancel()


def png_size(data: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(data)).size


def red_pixels(data: bytes) -> list[tuple[int, int]]:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    px = img.load()
    return [(x, y) for y in range(pv.HEAD_H, h) for x in range(w) if px[x, y] == pv.TIP]


def test_the_meshes_load_and_shrink():
    parts, joints, base = pv.load_model(pv.URDFS["so101"])
    assert base == "base_link"
    assert {p.link for p in parts} >= {"base_link", "upper_arm_link", "moving_jaw_so101_v1_link"}
    assert 3_000 < sum(len(p.tris) for p in parts) < 60_000  # simplified, not ~300k
    assert {"shoulder_pan", "gripper", "gripper_frame_joint"} <= {j.name for j in joints}


def test_link_frames_agree_with_the_ik_model():
    """The picture and the move tools must agree on where the gripper point is."""
    _, joints, base = pv.load_model(pv.URDFS["so101"])
    q = dict(SO101_HOME) | {"shoulder_pan": 30, "elbow_flex": 20}
    tip_link = pv.link_frames(joints, base, q)["gripper_frame_link"][0]
    tip_ik = so101_kinematics().fk(q)[0]
    assert all(abs(a - b) < 1e-9 for a, b in zip(tip_link, tip_ik, strict=True))


def test_the_red_dot_moves_with_the_gripper():
    """Side view: the gripper point is drawn where the kinematics says, in the left panel."""
    kin = so101_kinematics()

    def dot(q):
        (x, y, z), a = kin.fk(q)
        reds = red_pixels(pv.render("so101", q, (x * 100, y * 100, z * 100), a))
        side = [p for p in reds if p[0] < pv.PANEL_W]
        return sum(p[0] for p in side) / len(side), sum(p[1] for p in side) / len(side)

    low = dot(dict(SO101_HOME))
    high = dot(dict(SO101_HOME) | {"shoulder_lift": -40})  # upper arm back: gripper higher
    assert high[1] < low[1] - 20  # higher up in the picture


async def test_pose_view_on_the_fake_arm(rig):
    r = await rig.call("pose_view")
    assert png_size(r["image_png"]) == (2 * pv.PANEL_W, pv.PANEL_H)
    assert r["gripper_point_cm"] == rig.position()["gripper_point_cm"]
    assert "side" in r["views"] and "top" in r["views"]
    assert "last_target_cm" not in r
    entry = rig.calls.entries[-1]
    assert entry["tool"] == "pose_view" and entry["outcome"] == "ok"
    assert entry["result"]["image_png"].endswith("bytes")  # the log keeps no picture


async def test_pose_view_shows_the_last_target_and_marks(rig):
    start = rig.position()["gripper_point_cm"]
    await rig.call("move_to", x_cm=start["x"] + 2, y_cm=start["y"], z_cm=start["z"])
    marks = [{"x_cm": 20, "y_cm": 5, "z_cm": 1.5, "label": "cube", "size_cm": 3}]
    r = await rig.call("pose_view", marks=marks)
    assert r["last_target_cm"]["x"] == round(start["x"] + 2, 1)
    assert png_size(r["image_png"])[0] == 2 * pv.PANEL_W


async def test_pose_view_grows_to_fit_a_far_mark(rig):
    r = await rig.call("pose_view", marks=[{"x_cm": 120, "y_cm": 0, "z_cm": 0}])
    assert png_size(r["image_png"]) == (2 * pv.PANEL_W, pv.PANEL_H)  # same size, smaller scale


@pytest.mark.parametrize(
    "marks, words",
    [
        ([{"x_cm": 1}], "needs x_cm, y_cm and z_cm"),
        ([{"x_cm": 1, "y_cm": 2, "z_cm": float("nan")}], "must be a number"),
        ([{"x_cm": 1, "y_cm": 2, "z_cm": 3, "size_cm": 99}], "size_cm 0–30"),
        ([{"x_cm": 0, "y_cm": 0, "z_cm": 0}] * 11, "at most 10"),
    ],
)
async def test_bad_marks_are_refused(rig, marks, words):
    with pytest.raises(Refused, match=words):
        await rig.call("pose_view", marks=marks)


async def test_an_arm_without_a_3d_model_is_refused(rig):
    rig.arm.model = "xarm1s"
    with pytest.raises(Refused, match="no 3D model"):
        await rig.call("pose_view")


async def test_pose_view_over_mcp_is_a_picture_and_text(rig):
    async with Client(create_mcp_server(rig)) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
        assert tools["pose_view"].annotations.read_only_hint is True
        r = await c.call_tool("pose_view", {"marks": [{"x_cm": 15, "y_cm": 0, "z_cm": 2}]})
    kinds = [c.type for c in r.content]
    assert kinds[0] == "image" and r.content[0].mime_type == "image/png"
    assert "text" in kinds and "gripper_point_cm" in r.content[kinds.index("text")].text


async def test_people_can_see_the_same_picture(aiohttp_client):
    client = await aiohttp_client(make_app())
    res = await client.get("/api/pose-view.png")
    assert res.status == 200 and res.content_type == "image/png"
    assert png_size(await res.read()) == (2 * pv.PANEL_W, pv.PANEL_H)
