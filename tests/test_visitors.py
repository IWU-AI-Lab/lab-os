"""Visitors' mode (quick job 35): "Hey Jarvis, say hello to our visitors" on the brain's own screen
switches to the venue for visitors (visit-day), says a welcome from real facts, shows the cards;
"wave" waves the fake arm with fixed poses; "back to normal" switches back. No AI is asked (no key
in tests, so the chat is paused, and these still answer), no hardware."""

import asyncio
import json
import math
from dataclasses import replace

import pytest

from lab_os.devices import Device, Registry
from lab_os.hub import server as hub_server
from lab_os.hub.server import TOOLS, create_brain_app
from lab_os.hub.visitors import heard, robots_here, spoken_name, welcome
from lab_os.kinematics import kinematics_for
from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.teleop.server import CONTROL, LOOP
from lab_os.tools.robot import Refused, RobotTools, load_gestures, load_poses
from lab_os.venues import Venue, load_venue, visitors_venue_name

FAST = {"deg_per_s": 900}


# ---------- the phrases and the welcome ----------


@pytest.mark.parametrize(
    "text, what",
    [
        ("Hey Jarvis, say hello to our visitors", "visitors"),
        ("say hi to the guests!", "visitors"),
        ("Demo time.", "visitors"),
        ("We have visitors", "visitors"),
        ("we’ve got guests", "visitors"),
        ("Back to normal, please", "normal"),
        ("Can you wave?", "wave"),
        ("Ask me to wave", "wave"),
        ("What's next?", None),
        ("How do microwaves work?", None),
    ],
)
def test_the_phrases(text, what):
    assert heard(text) == what


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


def test_the_welcome():
    one = welcome("AI Comp Lab", "a lab where students build robots", ["the white SO-101 arm"], 2)
    assert one == (
        "Hello, and welcome to the AI Comp Lab, a lab where students build robots. The white "
        "SO-101 arm is here today. Try one of the cards on the screen."
    )
    two = welcome("AI Comp Lab", "", ["the white SO-101 arm", "the green SO-101 arm"], 0)
    assert "The white SO-101 arm and the green SO-101 arm are here today." in two
    assert two.startswith("Hello, and welcome to the AI Comp Lab.") and "cards" not in two
    assert "No robot arm is plugged in" in welcome("Lab", "", [], 1)


def test_the_lab_has_one_venue_for_visitors_with_cards():
    assert visitors_venue_name() == "visit-day"
    v = load_venue("visit-day")
    assert v.visitors and v.limits_fixed and v.hides_spend
    assert [c["say"] for c in v.cards] == ["Ask me to wave", "Open the VR hub"]
    assert v.cards[0]["ask"] == "wave" and "ask" not in v.cards[1]
    assert not load_venue("lab").visitors and not load_venue("lab").hides_spend


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
    pans = [j["shoulder_pan"] for j in seen if "shoulder_pan" in j]
    wrists = [j["wrist_flex"] for j in seen if "wrist_flex" in j]
    assert min(pans) == pytest.approx(ready["shoulder_pan"] - 8, abs=3)  # within one tick (3°)
    assert max(wrists) == pytest.approx(ready["wrist_flex"] + 15, abs=3)  # within one tick (3°)
    assert min(wrists) == pytest.approx(ready["wrist_flex"] - 15, abs=3)  # within one tick (3°)
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


# ---------- on the hub ----------


def make_app():
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState())
    return create_brain_app(loop, load_venue("lab"), internet=None)


async def say(client, text):
    resp = await client.post("/api/chat", json={"text": text})
    return [json.loads(line) for line in (await resp.text()).splitlines() if line]


def answer(events) -> str:
    return "".join(e["text"] for e in events if e["type"] == "text")


async def test_say_hello_to_our_visitors_and_back(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    st = await (await client.get("/api/status")).json()
    assert st["visitors"] is None and st["ai"]["paused"]  # no key: the AI can't answer
    assert (await (await client.get("/api/spend")).json())["available"]

    events = await say(client, "Hey Jarvis, say hello to our visitors")
    assert {"type": "venue", "venue": "visit-day", "visitors": True} in events
    assert answer(events).startswith("Hello, and welcome to the AI Comp Lab, a lab where")
    assert "No robot arm is plugged in" in answer(events)  # the fake arm isn't a robot
    assert events[-1] == {"type": "done", "setup": None, "cost_usd": 0.0, "tools": 0, "fixed": True}
    st = await (await client.get("/api/status")).json()
    assert st["venue"] == "visit-day"
    assert [c["say"] for c in st["visitors"]["cards"]] == ["Ask me to wave", "Open the VR hub"]
    assert not (await (await client.get("/api/spend")).json())["available"]  # AI costs hidden
    s = await (await client.get("/api/settings")).json()
    assert s["sections"] == [] and s["visitors"] == {"back_to": "lab", "here": True}
    r = await client.post("/api/settings", json={"key": "theme:hub.look", "value": "design"})
    assert r.status == 403
    # the limits are visit-day's, for the AI tools and teleop alike
    loop, tools = app[LOOP], app[TOOLS]
    assert (loop.max_speed_scale, loop.speed_scale, loop.one_to_one_deg_per_s) == (0.3, 0.3, 0)
    assert tools.venue.name == "visit-day" and tools.limits.min_z_cm == 1.1

    events = await say(client, "back to normal")
    assert answer(events) == "Back to normal: the lab venue again."
    st = await (await client.get("/api/status")).json()
    assert st["venue"] == "lab" and st["visitors"] is None
    assert (await (await client.get("/api/settings")).json())["sections"]
    assert (loop.max_speed_scale, loop.one_to_one_deg_per_s) == (0.5, 180)


async def test_wave_only_while_visitors_are_here(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    events = await say(client, "wave")
    assert not any(e["type"] == "wave" for e in events)  # a question for the AI (paused here)
    assert any(e["type"] == "error" for e in events)
    await say(client, "demo time")
    events = await say(client, "Ask me to wave")
    assert {"type": "wave"} in events and answer(events) == "Hello there!"
    tools = app[TOOLS]
    for _ in range(100):
        if tools.who_has_control() == "ai":
            break
        await asyncio.sleep(0.02)
    assert tools.who_has_control() == "ai"  # waving, at visit-day's speed
    assert "already moving" in answer(await say(client, "wave"))
    await tools.stop()  # STOP ends the wave
    for _ in range(100):
        if tools.calls.entries:
            break
        await asyncio.sleep(0.02)
    assert tools.calls.entries[-1]["outcome"] == "stopped"
    app[CONTROL]["ws"] = object()  # teleop has the arm
    assert "teleop" in answer(await say(client, "wave"))


async def test_only_from_the_brains_own_screen(aiohttp_client, monkeypatch):
    app = make_app()
    client = await aiohttp_client(app)
    monkeypatch.setattr(hub_server, "is_local", lambda request: False)
    events = await say(client, "say hello to our visitors")
    assert "from the brain's own screen" in answer(events)
    assert (await (await client.get("/api/status")).json())["visitors"] is None
    assert (await client.post("/api/venue", json={"to": "normal"})).status == 403


async def test_back_to_normal_from_settings(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    await say(client, "we have visitors")
    r = await (await client.post("/api/venue", json={"to": "normal"})).json()
    assert r == {"ok": True, "venue": "lab"}
    assert (await client.post("/api/venue", json={"to": "somewhere"})).status == 400


async def test_refuses_a_venue_without_the_brains_arm(aiohttp_client, monkeypatch):
    app = make_app()
    client = await aiohttp_client(app)
    other = Venue("visit-day", ("so101-white",), True, 0.3, visitors=True)
    monkeypatch.setattr(hub_server, "load_venue", lambda name: other)
    events = await say(client, "say hello to our visitors")
    assert "fake-arm isn't one of the visit-day venue's robots" in answer(events)
    assert (await (await client.get("/api/status")).json())["venue"] == "lab"
