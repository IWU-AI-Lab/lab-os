"""Visitor mode (quick job 35): "hey Jarvis, it's demo time" on the brain's own screen. The AI
decides: the hub's chat offers it tools to start and exit visitor mode and to wave, and it words the
welcome from the facts the start tool returns. Settings starts and exits it without asking. A
scripted stand-in plays the AI service (no internet, no keys); the wave runs on the fake arm."""

import asyncio
import json
import math
from collections import deque
from dataclasses import replace

import pytest
from aiohttp import web
from test_chat import setup_for
from test_voice import key  # noqa: F401 (a fixture)

from lab_os.ai.assistant import Assistant
from lab_os.ai.chat import Conversation
from lab_os.ai.spend import SpendLog
from lab_os.devices import Device, Registry
from lab_os.hub import server as hub_server
from lab_os.hub.server import TOOLS, create_brain_app
from lab_os.hub.visitors import EXIT, START, WAVE, robots_here, spoken_name
from lab_os.kinematics import kinematics_for
from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.teleop.server import CONTROL, LOOP
from lab_os.tools.robot import Refused, RobotTools, load_gestures, load_poses
from lab_os.venues import Venue, load_venue, visitors_venue_name

FAST = {"deg_per_s": 900}


# ---------- the facts and the venue ----------


def test_robots_are_named_as_said_aloud():
    assert spoken_name("so101-white", "so101") == "the white SO-101 arm"
    assert spoken_name("xarm1", "xarm1s") == "the xArm xarm1"


def test_only_robots_really_plugged_in_are_named():
    reg = Registry(
        {
            "so101-white": Device("so101-white", "so101", ports=("/dev/w",)),
            "so101-green": Device("so101-green", "so101", ports=("/dev/g",)),
            "so101-green-leader": Device("so101-green-leader", "so101-leader", ports=("/dev/l",)),
            "fake-arm": Device("fake-arm", "fake"),
        }
    )
    plugged = {"/dev/g", "/dev/l"}
    exists = plugged.__contains__
    assert robots_here(reg, "so101-white", True, exists) == ["so101-white", "so101-green"]
    assert robots_here(reg, "so101-white", False, exists) == ["so101-green"]  # unplugged
    assert robots_here(reg, "fake-arm", True, exists) == ["so101-green"]  # not a robot


def test_the_lab_has_one_venue_for_visitors_without_extra_limits():
    assert visitors_venue_name() == "visit-day"
    v, lab = load_venue("visit-day"), load_venue("lab")
    assert v.visitors and v.hides_spend and not lab.visitors and not lab.hides_spend
    # the builder (2026-11-18): no extra restrictions for visitors: the lab's robots, speed and 1:1
    assert set(v.active_devices) == set(lab.active_devices) and "so101-green" in v.active_devices
    assert (v.max_speed_scale, v.one_to_one_deg_per_s) == (lab.max_speed_scale, 180)
    assert not v.limits_fixed  # the limits can be switched off, as in the lab
    assert [c["say"] for c in v.cards] == ["Ask me to wave", "Open the VR hub"]
    assert v.cards[0]["ask"] and "ask" not in v.cards[1]


# ---------- the wave on the fake arm ----------


@pytest.fixture
async def rig():
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState(), speed_scale=1.0)
    task = asyncio.create_task(loop.run())
    v = Venue("test", ("fake-arm",), True, 1.0, ai_tools=FAST, visitors=True)
    yield RobotTools(loop, v, {"ws": None})
    task.cancel()


async def test_the_wave_plays_its_poses_and_ends_at_ready(rig):
    ready = load_poses()["so101"]["ready"]
    await rig.call("go_to_pose", name="ready")
    await rig.call("move_joints", joints={"shoulder_pan": ready["shoulder_pan"] + 20})
    assert rig.arm.read_joints()["shoulder_pan"] == pytest.approx(ready["shoulder_pan"] + 20)
    rig.limits = replace(rig.limits, deg_per_s=150)  # slow enough to reach each pose (~1 s)
    seen = []
    rig.loop.on_command = lambda m: seen.append(dict(m.get("joints") or {}))
    r = await rig.call("wave")
    assert r["result"] == "arrived"
    # every joint reaches the furthest the wave's steps send it, both ways (gestures.yaml)
    steps = load_gestures()["so101"]["wave"]["steps"]
    for j in ("shoulder_pan", "elbow_flex", "wrist_flex"):
        got = [c[j] for c in seen if j in c]
        deltas = [s.get(j, 0) for s in steps] + [0]
        assert max(got) == pytest.approx(ready[j] + max(deltas), abs=3), j  # within a tick (3°)
        assert min(got) == pytest.approx(ready[j] + min(deltas), abs=3), j
    end = rig.arm.read_joints()
    assert all(abs(end[j] - ready[j]) < 1 for j in ready)
    assert rig.calls.entries[-1]["tool"] == "wave"  # on the AI Control page like a tool call


async def test_the_wave_keeps_the_safety_rules(rig):
    rig.control["ws"] = object()  # teleop has the arm
    with pytest.raises(Refused, match="teleop has control"):
        rig.gesture_path("wave")
    rig.control["ws"] = None
    deep = {"from": "ready", "steps": [{"shoulder_lift": 60, "elbow_flex": -60, "wrist_flex": 60}]}
    rig.gestures = {"wave": deep}
    with pytest.raises(Refused, match="floor"):
        rig.gesture_path("wave")
    rig.gestures = {"wave": {"from": "ready", "steps": [{"shoulder_pan": 500}]}}
    path, notes = rig.gesture_path("wave")  # clipped to the soft limits, and says so
    assert path[1]["shoulder_pan"] < 120 and any("joint limit" in n for n in notes)


def test_every_gesture_stays_inside_the_limits_and_above_the_floor():
    arm = FakeArm()
    kin = kinematics_for(arm.model)
    floor = load_venue("visit-day").floor_cm
    poses = load_poses()
    for model, gestures in load_gestures().items():
        for name, g in gestures.items():
            base = poses[model][g["from"]]
            for step in g["steps"]:
                q = base | {j: base[j] + d for j, d in step.items()}
                for j, v in q.items():
                    lim = arm.limits[j]
                    assert lim.low + 3 <= v <= lim.high - 3, f"{model} {name}: {j} {v}"
                if model == arm.model:
                    lowest = min(p[2] for p, _ in kin.frames(q).values()) * 100
                    assert lowest > floor, f"{model} {name}: {lowest:.1f} cm"


def test_a_venue_switch_moves_the_loops_caps():
    loop = TeleopLoop(arm=FakeArm(), inputs=InputState(), speed_scale=0.5, max_speed_scale=0.5)
    loop.mapper.kinematics = object()
    loop.one_to_one_deg_per_s = 180
    loop.set_mode("one_to_one")
    loop.use_caps(0.3, 0.3, 0.0)  # visit-day: slower, no 1:1
    assert (loop.max_speed_scale, loop.speed_scale) == (0.3, 0.3)
    assert loop.mapper.config.mode == "relative" and loop.modes() == ["relative"]
    assert math.isclose(loop.set_speed(1.0), 0.3)


# ---------- on the hub, with a stand-in for the AI ----------


def ai_service(script: deque, seen: list):
    """Each request gets the next reply: ("tool", name) or ("words", text)."""

    async def completions(request):
        seen.append(await request.json())
        kind, what = script.popleft()
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await resp.prepare(request)
        if kind == "tool":
            call = {"index": 0, "id": f"c{len(seen)}", "type": "function"}
            call["function"] = {"name": what, "arguments": "{}"}
            chunks = [{"choices": [{"index": 0, "delta": {"tool_calls": [call]}}]}]
            end = "tool_calls"
        else:
            chunks = [{"choices": [{"index": 0, "delta": {"content": what}}]}]
            end = "stop"
        chunks.append({"choices": [{"index": 0, "delta": {}, "finish_reason": end}]})
        chunks.append({"choices": [], "usage": {"prompt_tokens": 100, "completion_tokens": 10}})
        for c in chunks:
            await resp.write(f"data: {json.dumps(c)}\n\n".encode())
        await resp.write(b"data: [DONE]\n\n")
        return resp

    async def models(request):
        return web.json_response({"data": []})

    app = web.Application()
    app.router.add_post("/v1/chat/completions", completions)
    app.router.add_get("/v1/models", models)
    return app


@pytest.fixture
async def hub(aiohttp_server, aiohttp_client, tmp_path, key, monkeypatch):  # noqa: F811
    """The brain on the fake arm, its chat answered by the stand-in. Returns (app, client, script,
    seen): put the AI's next replies in `script`; `seen` has every request the chat sent. No arm
    counts as plugged in, even if one is plugged in to this computer."""
    monkeypatch.setattr(
        hub_server, "robots_here", lambda reg, *a: robots_here(reg, *a, exists=lambda p: False)
    )
    script, seen = deque(), []
    setup = setup_for(await aiohttp_server(ai_service(script, seen)))
    chat = Conversation(Assistant(), SpendLog(tmp_path / "spend"), setups=lambda: {"main": setup})
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState())
    app = create_brain_app(loop, load_venue("lab"), internet=None, chat=chat)
    return app, await aiohttp_client(app), script, seen


async def ask(client, text):
    resp = await client.post("/api/chat", json={"text": text})
    return [json.loads(line) for line in (await resp.text()).splitlines() if line]


def answer(events) -> str:
    return "".join(e["text"] for e in events if e["type"] == "text")


def offered(request) -> set[str]:
    return {t["function"]["name"] for t in request.get("tools") or []}


def tool_result(request) -> str:
    return next(m["content"] for m in reversed(request["messages"]) if m["role"] == "tool")


async def test_the_ai_starts_visitor_mode_and_welcomes_them(hub):
    app, client, script, seen = hub
    assert (await (await client.get("/api/status")).json())["visitors"] is None
    script.extend([("tool", START), ("words", "Welcome to the AI Comp Lab!")])
    events = await ask(client, "Hey Jarvis, it's demo time")
    assert offered(seen[0]) >= {START} and not offered(seen[0]) & {EXIT, WAVE}
    assert {"type": "venue", "venue": "visit-day", "visitors": True} in events
    facts = json.loads(tool_result(seen[1]))  # what the AI words the welcome from
    assert facts["place"] == "AI Comp Lab" and facts["about"].startswith("a lab where")
    assert "robots_here" not in facts  # the fake arm isn't a robot: none listed, none mentioned
    assert facts["cards_on_screen"] == ["Ask me to wave", "Open the VR hub"]
    assert answer(events) == "Welcome to the AI Comp Lab!"
    assert app[hub_server.BRAIN].chat.take_say() == "Welcome to the AI Comp Lab!"  # typed: speak it
    st = await (await client.get("/api/status")).json()
    assert st["venue"] == "visit-day" and st["visitors"]["cards"][0]["say"] == "Ask me to wave"
    assert not (await (await client.get("/api/spend")).json())["available"]
    s = await (await client.get("/api/settings")).json()
    assert s["sections"] == [] and s["visitor_mode"]["on"] and s["visitor_mode"]["back_to"] == "lab"
    r = await client.post("/api/settings", json={"key": "theme:clock", "value": "12h"})
    assert r.status == 403
    loop, tools = app[LOOP], app[TOOLS]
    assert tools.venue.name == "visit-day" and loop.one_to_one_deg_per_s == 180  # 1:1 stays

    script.extend([("tool", EXIT), ("words", "Visitor mode is off.")])
    events = await ask(client, "Thanks Jarvis, you can exit visitor mode")
    assert offered(seen[2]) >= {EXIT, WAVE} and START not in offered(seen[2])
    assert {"type": "venue", "venue": "lab", "visitors": False} in events
    assert (await (await client.get("/api/status")).json())["visitors"] is None
    assert (await (await client.get("/api/settings")).json())["sections"]


async def test_the_ai_waves_only_in_visitor_mode(hub):
    app, client, script, seen = hub
    script.extend([("words", "I can't wave right now.")])
    await ask(client, "wave")
    assert WAVE not in offered(seen[-1])
    await client.post("/api/venue", json={"to": "visitors"})
    script.extend([("tool", WAVE), ("words", "Hello!")])
    events = await ask(client, "Can the robot say hi to us?")
    assert {"type": "wave"} in events and answer(events) == "Hello!"
    tools = app[TOOLS]
    for _ in range(100):
        if tools.who_has_control() == "ai":
            break
        await asyncio.sleep(0.02)
    assert tools.who_has_control() == "ai"  # waving
    script.extend([("tool", WAVE), ("words", "I'm already waving.")])
    await ask(client, "wave again")
    assert "already moving" in tool_result(seen[-1])
    await tools.stop()  # STOP ends the wave
    for _ in range(100):
        if tools.calls.entries:
            break
        await asyncio.sleep(0.02)
    assert tools.calls.entries[-1]["outcome"] == "stopped"
    app[CONTROL]["ws"] = object()  # teleop has the arm
    script.extend([("tool", WAVE), ("words", "Someone is driving the arm.")])
    await ask(client, "wave")
    assert "teleop" in tool_result(seen[-1])


async def test_only_from_the_brains_own_screen(hub, monkeypatch):
    app, client, script, seen = hub
    monkeypatch.setattr(hub_server, "is_local", lambda request: False)
    script.extend([("tool", START), ("words", "I can't from here.")])
    await ask(client, "it's demo time")
    assert START not in offered(seen[0])  # not offered: a call is refused
    assert len(seen) == 1 or "isn't a tool you have" in tool_result(seen[1])
    assert (await (await client.get("/api/status")).json())["visitors"] is None
    assert (await client.post("/api/venue", json={"to": "visitors"})).status == 403


async def test_settings_start_and_exit_it_without_asking(hub):
    app, client, script, seen = hub
    s = await (await client.get("/api/settings")).json()
    assert s["visitor_mode"] == {"on": False, "venue": "visit-day", "back_to": "lab", "here": True}
    r = await (await client.post("/api/venue", json={"to": "visitors"})).json()
    assert r == {"ok": True, "venue": "visit-day", "visitors": True}
    r = await (await client.post("/api/venue", json={"to": "normal"})).json()
    assert r == {"ok": True, "venue": "lab", "visitors": False}
    assert (await client.post("/api/venue", json={"to": "somewhere"})).status == 400
    assert seen == []  # no AI needed


async def test_refuses_a_venue_without_the_brains_arm(hub, monkeypatch):
    app, client, script, seen = hub
    other = Venue("visit-day", ("so101-white",), True, 0.3, visitors=True)
    monkeypatch.setattr(hub_server, "load_venue", lambda name: other)
    script.extend([("tool", START), ("words", "Visitor mode didn't start.")])
    await ask(client, "we have guests!")
    assert "fake-arm isn't one of the visit-day venue's robots" in tool_result(seen[1])
    assert (await (await client.get("/api/status")).json())["venue"] == "lab"
