# ruff: noqa: F811 (`key` is a fixture from test_voice, used as an argument)
"""The hub's assistant moves the arm (preview 4): "move the arm to home" and "hand me the cube".
Off unless place.yaml says so, on the brain's own computer only; the moves go through the robot
tools on the fake arm; the cube is found by its colour in a test picture. No hardware."""

import asyncio
import io
import json
import math
from collections import deque
from dataclasses import replace

import numpy as np
import pytest
from aiohttp import web
from PIL import Image, ImageDraw
from test_chat import setup_for
from test_pick_at import CubeInTheJaws
from test_table_map import _plain_map
from test_voice import key  # noqa: F401 (a fixture)

from lab_os import config
from lab_os.ai.assistant import Assistant
from lab_os.ai.chat import Conversation
from lab_os.ai.spend import SpendLog
from lab_os.hub import arm_desk
from lab_os.hub.arm_desk import HAND, LET_GO, MOVE, Actions, ArmDesk
from lab_os.hub.server import BRAIN, TOOLS, create_brain_app
from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.tools import robot as robot_tools
from lab_os.tools import table_map
from lab_os.tools.robot import RobotTools
from lab_os.venues import Venue, load_venue

SETUP = arm_desk.load()  # the repo's own config/handover.yaml
BLUE, RED = (30, 70, 200), (200, 40, 40)


def picture(*cubes) -> bytes:
    """A grey table seen by `_plain_map`'s camera (10 px = 1 cm, straight down), with squares of
    `colour` standing at (x, y) cm, `size` cm wide."""
    img = Image.new("RGB", (640, 480), (120, 120, 115))
    d = ImageDraw.Draw(img)
    for x, y, colour, size in cubes:
        u, v, half = 320 - y * 10, 460 - x * 10, size * 5
        d.rectangle([u - half, v - half, u + half, v + half], fill=colour)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=90)
    return out.getvalue()


def test_the_cube_is_found_where_it_stands():
    m = _plain_map()
    x, y = arm_desk.find_cube(picture((20, 3, BLUE, 2.5)), m, SETUP)
    assert x == pytest.approx(20, abs=0.6) and y == pytest.approx(3, abs=0.6)
    # the biggest blue patch wins; red and a blue speck don't count
    x, y = arm_desk.find_cube(
        picture((25, -5, RED, 3), (18, 8, BLUE, 0.6), (21, -2, BLUE, 2.5)), m, SETUP
    )
    assert x == pytest.approx(21, abs=0.6) and y == pytest.approx(-2, abs=0.6)
    assert arm_desk.find_cube(picture((20, 0, RED, 2.5)), m, SETUP) is None
    assert arm_desk.find_cube(picture((20, 0, BLUE, 0.5)), m, SETUP) is None  # too small


def test_the_setup_and_the_handover_pose():
    assert SETUP.pose == "handover" and SETUP.height_cm == 2.5
    pose = robot_tools.load_poses()["so101"][SETUP.pose]
    assert "gripper" not in pose  # the jaws keep their grip on the way
    with pytest.raises(arm_desk.NoSetup, match="doesn't exist"):
        arm_desk.load(config.DEFAULT_DIR / "nope.yaml")


def test_off_unless_place_yaml_says_so(tmp_path, monkeypatch):
    place = tmp_path / "place.yaml"
    monkeypatch.setattr(config, "active_dir", lambda: tmp_path)
    place.write_text("name: x\n")
    assert config.assistant_moves_arm() is False
    place.write_text("name: x\nassistant_moves_arm: true\n")
    assert config.assistant_moves_arm() is True
    from lab_os import settings

    field = settings.find("place:assistant_moves_arm")
    assert field.kind == "bool" and field.default is False


# ---------- on the fake arm ----------


@pytest.fixture
async def desk(tmp_path, monkeypatch):
    """An arm desk on a fake arm whose jaws stop on a cube, switched on, with a stand camera that
    sees a blue cube at (18, 10) cm (`shot["jpeg"]`: a picture, or one made from the desk), and
    a wrist camera that sees the cube at `shot["wrist"]` (x, y cm), if any, from the gripper."""
    from lab_os import devices

    monkeypatch.setattr(table_map, "map_path", lambda cam: tmp_path / f"{cam}.yaml")
    table_map.save(_plain_map(SETUP.camera))
    monkeypatch.setattr(devices, "camera_device", lambda cam: "/dev/video-fake")
    shot = {"jpeg": picture((18, 10, BLUE, 2.5)), "wrist": None}

    def grab(path, w, cam):
        if cam == SETUP.wrist_camera:
            return wrist_picture(d, shot["wrist"])
        return shot["jpeg"](d) if callable(shot["jpeg"]) else shot["jpeg"]

    monkeypatch.setattr(robot_tools, "_grab_jpeg", grab)
    probe = FakeArm()
    lo, hi = probe.limits["gripper"].low + 3, probe.limits["gripper"].high - 3
    arm = CubeInTheJaws(stop_deg=lo + (hi - lo) * 0.3)
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState(), speed_scale=1.0)
    task = asyncio.create_task(loop.run())
    venue = Venue("test", ("fake-arm",), True, 1.0, ai_tools={"deg_per_s": 900})
    on = {"on": True}
    d = ArmDesk(RobotTools(loop, venue, {"ws": None}), enabled=lambda: on["on"])
    d.shot, d.on = shot, on
    yield d
    task.cancel()


WRIST_F = 500  # the fake wrist camera's focal length (px): ~65° wide at 640 px


def wrist_picture(d, cube) -> bytes:
    """What a camera at the gripper point, looking along the jaws, sees of a blue cube at `cube`
    (x, y cm on the table; None: no cube): a pinhole camera, its picture turning with the arm."""
    img = Image.new("RGB", (640, 480), (120, 120, 115))
    if cube is not None:
        (gx, gy, gz), angle = d.robot.kin.fk(d.robot.arm.read_joints())
        c = np.array([gx, gy, gz]) * 100
        h, a = math.atan2(gy, gx), math.radians(angle)
        look = np.array([math.sin(a) * math.cos(h), math.sin(a) * math.sin(h), math.cos(a)])
        right = np.array([math.sin(h), -math.cos(h), 0.0])
        down = np.cross(look, right)
        rel = np.array([cube[0], cube[1], SETUP.height_cm / 2]) - c
        depth = rel @ look
        if depth > 1:
            u, v = 320 + WRIST_F * (rel @ right) / depth, 240 + WRIST_F * (rel @ down) / depth
            half = WRIST_F * SETUP.height_cm / depth / 2
            ImageDraw.Draw(img).rectangle([u - half, v - half, u + half, v + half], fill=BLUE)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=90)
    return out.getvalue()


async def settle(d):
    assert d.task is not None
    await asyncio.wait_for(d.task, 30)


def joints_near(d, pose: str) -> bool:
    now = d.robot.arm.read_joints()
    return all(abs(now[j] - v) < 1 for j, v in d.robot.poses[pose].items())


async def test_offered_only_when_on_and_on_the_brains_computer(desk):
    names = [t["function"]["name"] for t in desk.tools(local=True)]
    assert names == [MOVE, HAND, LET_GO]
    pose = desk.tools(True)[0]["function"]["parameters"]["properties"]["pose"]
    assert {"home", "ready", "handover"} <= set(pose["enum"])
    assert desk.tools(local=False) == []
    result, _ = await desk.call(MOVE, False, '{"pose": "home"}')
    assert result.startswith("Error")
    desk.robot.venue = replace(desk.robot.venue, public=True)  # a hallway screen's venue
    assert desk.tools(local=True) == []
    desk.robot.venue = replace(desk.robot.venue, public=False)
    desk.on["on"] = False
    assert desk.tools(local=True) == []
    result, _ = await desk.call(MOVE, True, '{"pose": "home"}')
    assert result.startswith("Error") and desk.task is None  # nothing moved


async def test_move_the_arm_to_home(desk):
    result, _ = await desk.call(MOVE, True, json.dumps({"pose": "home"}))
    assert "moving to home" in result
    again, _ = await desk.call(MOVE, True, '{"pose": "ready"}')
    assert "still moving to home" in again  # one request at a time
    await settle(desk)
    home = {j: v for j, v in desk.robot.poses["home"].items() if j != "gripper"}  # (jaws on a cube)
    now = desk.robot.arm.read_joints()
    soft = {j: (desk.robot.arm.limits[j].low + 3, desk.robot.arm.limits[j].high - 3) for j in home}
    assert all(abs(now[j] - min(max(v, soft[j][0]), soft[j][1])) < 1 for j, v in home.items())
    tools = {e["tool"] for e in desk.robot.calls.entries}
    assert tools == {"go_to_pose"}  # through the robot tools, on the AI Control page
    result, _ = await desk.call(MOVE, True, '{"pose": "dance"}')
    assert "no pose 'dance'" in result


async def test_refused_while_teleop_drives(desk):
    desk.robot.control["ws"] = object()
    result, _ = await desk.call(MOVE, True, '{"pose": "home"}')
    assert "teleop has control" in result and desk.task is None


async def test_hand_me_the_cube_then_let_go(desk):
    early, _ = await desk.call(LET_GO, True)
    assert "isn't holding" in early
    result, _ = await desk.call(HAND, True)
    assert "Found the cube with the stand camera, about 21 cm" in result, result
    await settle(desk)
    assert desk.holding and joints_near(desk, SETUP.pose), desk.last
    steps = [e["tool"] for e in desk.robot.calls.entries]
    assert steps[0] == "camera_snapshot" and "pick_at" in steps
    pct = desk.robot._gripper_pct(desk.robot.arm.read_joints()["gripper"])
    assert pct > 15  # still holding at the hand-over pose
    result, _ = await desk.call(LET_GO, True)
    assert "gripper is open" in result and not desk.holding
    assert desk.robot._gripper_pct(desk.robot.arm.read_joints()["gripper"]) > 90


async def test_out_of_reach_moves_nothing(desk):
    desk.shot["jpeg"] = picture((44, 25, BLUE, 2.5))
    result, _ = await desk.call(HAND, True)
    assert "can't pick it up" in result and desk.task is None
    moves = [e for e in desk.robot.calls.entries if e["tool"] != "camera_snapshot"]
    assert moves == []


def steps(d) -> list[str]:
    return [e["tool"] for e in d.robot.calls.entries]


async def test_a_cube_to_the_side_is_picked_with_a_tilted_gripper(desk):
    """Out of a straight-down pick's reach (quick job 117, lab check H.2): the gripper tilts."""
    assert desk.robot.pick_plan(30, 15, 2.5)[0] < 180
    desk.shot["jpeg"] = picture((30, 15, BLUE, 2.5))
    result, _ = await desk.call(HAND, True)
    assert "Found the cube with the stand camera" in result, result
    await settle(desk)
    assert desk.holding, desk.last
    pick = [e for e in desk.robot.calls.entries if e["tool"] == "pick_at"][-1]
    assert pick["result"]["tool_angle_deg"] < 180


async def test_a_cube_near_the_jaws_is_looked_at_again_from_home(desk):
    """The arm at ready may hide a cube under its jaws from the stand camera: it folds to home
    and looks again before it picks."""
    (gx, gy, _), _ = desk.robot.kin.fk(desk.robot.arm.read_joints())
    desk.shot["jpeg"] = picture((gx * 100 - 4, gy * 100, BLUE, 2.5))
    result, _ = await desk.call(HAND, True)
    assert "Found the cube with the stand camera" in result, result
    seen = steps(desk)
    assert seen[0] == "camera_snapshot" and "go_to_pose" in seen
    assert seen.index("go_to_pose") < len(seen) - 1 and seen[-1] == "camera_snapshot"
    await settle(desk)
    assert desk.holding, desk.last


async def test_the_wrist_camera_finds_what_the_stand_camera_cant(desk):
    desk.shot["jpeg"] = picture((20, 0, RED, 2.5))  # no blue cube for the stand camera
    desk.shot["wrist"] = (21.0, -13.0)
    result, _ = await desk.call(HAND, True)
    assert "Found the cube with the wrist camera" in result, result
    await settle(desk)
    assert desk.holding, desk.last
    pick = [e for e in desk.robot.calls.entries if e["tool"] == "pick_at"][-1]
    x, y = pick["args"]["x_cm"], pick["args"]["y_cm"]
    assert math.dist((x, y), desk.shot["wrist"]) < 1.0, (x, y)


async def test_no_camera_sees_it(desk):
    desk.shot["jpeg"] = picture((20, 0, RED, 2.5))
    result, _ = await desk.call(HAND, True)
    assert "can't see the blue cube" in result and "wrist camera didn't find it" in result
    assert "pick_at" not in steps(desk) and not desk.holding


async def test_stop_ends_the_hand_over(desk):
    result, _ = await desk.call(HAND, True)
    assert "Found the cube" in result
    for _ in range(200):  # STOP as soon as the arm moves
        if any(e["tool"] == "go_to_pose" for e in desk.robot.calls.entries):
            break
        await asyncio.sleep(0.005)
    await desk.robot.call("stop")
    await settle(desk)
    assert not desk.holding and "stopped" in desk.last
    assert not any(e["tool"] == "pick_at" for e in desk.robot.calls.entries)


async def test_actions_join_the_desks():
    class Other:
        def tools(self, local):
            return [arm_desk._tool("wave", "")]

        async def call(self, name, local, arguments="{}"):
            return f"ran {name} {arguments}", []

    a = Actions(Other())
    assert [t["function"]["name"] for t in a.tools(True)] == ["wave"]
    assert (await a.call("wave", True, "{}"))[0] == "ran wave {}"
    assert (await a.call("nope", True))[0].startswith("Error")


# ---------- through the hub's chat, with a stand-in for the AI ----------


def ai_service(script: deque, seen: list):
    """Each request gets the next reply: ("tool", name, arguments) or ("words", text)."""

    async def completions(request):
        seen.append(await request.json())
        reply = script.popleft()
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await resp.prepare(request)
        if reply[0] == "tool":
            call = {"index": 0, "id": f"c{len(seen)}", "type": "function"}
            call["function"] = {"name": reply[1], "arguments": json.dumps(reply[2])}
            delta, end = {"tool_calls": [call]}, "tool_calls"
        else:
            delta, end = {"content": reply[1]}, "stop"
        chunks = [{"choices": [{"index": 0, "delta": delta}]}]
        chunks.append({"choices": [{"index": 0, "delta": {}, "finish_reason": end}]})
        chunks.append({"choices": [], "usage": {"prompt_tokens": 100, "completion_tokens": 10}})
        for c in chunks:
            await resp.write(f"data: {json.dumps(c)}\n\n".encode())
        await resp.write(b"data: [DONE]\n\n")
        return resp

    app = web.Application()
    app.router.add_post("/v1/chat/completions", completions)

    async def models(request):
        return web.json_response({"data": []})

    app.router.add_get("/v1/models", models)
    return app


async def test_the_assistant_moves_the_arm_home_only_when_settings_allow(
    aiohttp_server,
    aiohttp_client,
    tmp_path,
    key,
    monkeypatch,
):
    switch = {"on": False}
    monkeypatch.setattr(config, "assistant_moves_arm", lambda: switch["on"])
    script, seen = deque(), []
    setup = setup_for(await aiohttp_server(ai_service(script, seen)))
    chat = Conversation(Assistant(), SpendLog(tmp_path / "spend"), setups=lambda: {"main": setup})
    arm = FakeArm()
    arm.connect()
    app = create_brain_app(
        TeleopLoop(arm=arm, inputs=InputState()), load_venue("lab"), internet=None, chat=chat
    )
    client = await aiohttp_client(app)

    async def ask(text):
        resp = await client.post("/api/chat", json={"text": text})
        return [json.loads(line) for line in (await resp.text()).splitlines() if line]

    def offered(request) -> set[str]:
        return {t["function"]["name"] for t in request.get("tools") or []}

    script.append(("words", "I can't move the arm."))
    await ask("move the arm to home")
    assert not offered(seen[-1]) & {MOVE, HAND, LET_GO}  # off by default
    switch["on"] = True
    script.extend([("tool", MOVE, {"pose": "home"}), ("words", "Going home.")])
    await ask("Hey Jarvis, move the arm to home")
    assert offered(seen[-2]) >= {MOVE, HAND, LET_GO}
    result = next(m["content"] for m in reversed(seen[-1]["messages"]) if m["role"] == "tool")
    assert "moving to home" in result
    desk = app[BRAIN].chat.actions.desks[1]
    await asyncio.wait_for(desk.task, 30)
    assert desk.last == "at home"
    assert app[TOOLS].calls.entries[-1]["tool"] == "go_to_pose"
