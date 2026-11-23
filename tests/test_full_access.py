# ruff: noqa: F811 (`key` is a fixture from test_voice, used as an argument)
"""Quick job 80: Full Access for the hub's assistant (every tool of the brain), the hub's buttons as
MCP tools, and the second arm by its name. Fake arms and a stand-in for the AI: no hardware."""

import json
from collections import deque

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from test_arm_desk import ai_service
from test_chat import setup_for
from test_hub_server import VENUE
from test_two_arms import arm_loop
from test_voice import key  # noqa: F401 (a fixture)

from lab_os import config
from lab_os.ai.assistant import Assistant
from lab_os.ai.chat import Conversation
from lab_os.ai.spend import SpendLog
from lab_os.hub.server import BRAIN, LOOP, TOOLS, create_brain_app
from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.venues import load_venue

MOVES = {"move_to", "pick_at", "move_joints", "gripper", "go_to_pose", "stop"}
PICTURES = {"camera_snapshot", "pose_view", "table_point"}
SYSTEM = {
    "hub_screens",
    "open_on_device",
    "bring_back",
    "set_up_the_room",
    "list_settings",
    "change_setting",
    "change_device_setting",
    "restart_lab_os",
    "shut_down_lab_os",
    "visitor_mode",
    "quest_view",
    "say_aloud",
    "teleop_speed",
    "teleop_mode",
    "wave_arm",
    "training_lelab",
    "training_lerobot_teleop",
}


def offered(request) -> set[str]:
    return {t["function"]["name"] for t in request.get("tools") or []}


async def chat_app(aiohttp_server, aiohttp_client, tmp_path, script, seen):
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

    return app, ask


async def test_full_access_gives_the_assistant_every_tool(
    aiohttp_server, aiohttp_client, tmp_path, key, monkeypatch
):
    switch = {"on": False}
    monkeypatch.setattr(config, "assistant_full_access", lambda: switch["on"])
    script, seen = deque(), []
    app, ask = await chat_app(aiohttp_server, aiohttp_client, tmp_path, script, seen)

    script.append(("words", "I can't."))
    await ask("open the gripper")
    acts = MOVES | PICTURES | SYSTEM - {"hub_screens", "list_settings"}  # (those two read)
    assert not offered(seen[-1]) & acts  # off by default: read tools only
    assert "Full Access is on" not in seen[-1]["messages"][0]["content"]

    switch["on"] = True
    script.extend(
        [
            ("tool", "go_to_pose", {"name": "ready"}),
            ("tool", "gripper", {"open_pct": 100}),
            ("words", "The gripper is open."),
        ]
    )
    await ask("go to ready and open the gripper")
    tools = offered(seen[-3])
    assert tools >= MOVES | PICTURES | SYSTEM, (MOVES | PICTURES | SYSTEM) - tools
    assert len(tools) == len(seen[-3]["tools"])  # no name twice (the chat's own tools win)
    assert "Full Access is on" in seen[-3]["messages"][0]["content"]
    done = [e["tool"] for e in app[TOOLS].calls.entries]
    assert done[-2:] == ["go_to_pose", "gripper"]  # through the robot tools, logged on AI Control


async def test_a_picture_goes_to_the_model_as_an_image(
    aiohttp_server, aiohttp_client, tmp_path, key, monkeypatch
):
    monkeypatch.setattr(config, "assistant_full_access", lambda: True)
    script, seen = deque(), []
    _, ask = await chat_app(aiohttp_server, aiohttp_client, tmp_path, script, seen)
    script.extend([("tool", "pose_view", {}), ("words", "The arm is folded.")])
    await ask("how does the arm stand?")
    last = seen[-1]["messages"]
    picture = next(m for m in last if m["role"] == "user" and isinstance(m["content"], list))
    urls = [p["image_url"]["url"] for p in picture["content"] if p["type"] == "image_url"]
    assert urls and urls[0].startswith("data:image/png;base64,")
    assert last.index(picture) > max(i for i, m in enumerate(last) if m["role"] == "tool")


async def test_the_buttons_as_mcp_tools(aiohttp_server, aiohttp_client, tmp_path, key):
    script, seen = deque(), []
    app, _ = await chat_app(aiohttp_server, aiohttp_client, tmp_path, script, seen)
    server = app[BRAIN].chat.tools.server
    names = {t.name for t in await server.list_tools()}
    assert names >= SYSTEM

    async def call(name, args=None):
        try:
            r = await server.call_tool(name, args or {})
        except ToolError as e:
            return {"error": str(e)}, True
        text = "".join(getattr(c, "text", "") for c in r.content)
        try:
            return json.loads(text), r.is_error
        except ValueError:
            return {"text": text}, r.is_error

    out, err = await call("teleop_speed", {"speed_scale": 0.3})
    assert not err and app[LOOP].speed_scale == 0.3  # the same code as the page's slider
    out, err = await call("teleop_mode", {"mode": "warp"})
    assert err
    out, err = await call("hub_screens")
    assert not err and "monitor" in out["views"]
    out, err = await call("open_on_device", {"view": "monitor", "device": "newline"})
    assert err  # no such screen with the hub open: the same refusal as "Open on…"
    out, err = await call("say_aloud", {"text": "Hello."})
    assert err  # no voice set up in the test, or no screen
    settings = (await call("list_settings"))[0]["settings"]
    assert any(s["key"] == "place:assistant_full_access" and s["value"] is False for s in settings)


async def test_ai_tools_reach_the_second_arm_by_its_name(aiohttp_client):
    inputs = InputState()
    right = arm_loop(FakeArm(name="fake-arm"), inputs, "right")
    right.left = arm_loop(FakeArm(name="fake-left"), inputs, "left")
    right.left.is_left = True
    app = create_brain_app(right, VENUE, internet=None)
    await aiohttp_client(app)
    server = app[BRAIN].chat.tools.server
    first = json.loads((await server.call_tool("arm_status", {})).content[0].text)
    assert first["arm"] == "fake-arm" and first["other_arms"] == ["fake-left"]
    second = json.loads(
        (await server.call_tool("arm_status", {"arm": "fake-left"})).content[0].text
    )
    assert second["arm"] == "fake-left" and second["other_arms"] == ["fake-arm"]
    with pytest.raises(ToolError, match="other arms: fake-left"):
        await server.call_tool("arm_status", {"arm": "nope"})
