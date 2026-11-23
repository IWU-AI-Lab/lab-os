"""Webcam teleop (preview 2): the page and its vendored hand tracker are served, its messages reach
the arm like the Quest's bare hands, and the page's own maths (webcam-hands.js, run with node; those
tests are skipped without node): hand sides, pinch, the wrist's position, and the freeze rules."""

import asyncio
import json
import shutil
import subprocess

import pytest

from lab_os import REPO_ROOT
from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.teleop.server import create_app

MODULE = REPO_ROOT / "src/lab_os/teleop/web/webcam-hands.js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node isn't installed")


def run(expr: str):
    """Evaluate `expr` with the module imported as `m`; returns its JSON value."""
    script = (
        f"import({json.dumps(MODULE.as_uri())}).then(m => "
        f"console.log(JSON.stringify((() => {{ {expr} }})())))"
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


# ---- served, and its messages drive like the Quest's bare hands --------------------------------


async def test_page_and_hand_tracker_served(aiohttp_client):
    arm = FakeArm()
    arm.connect()
    client = await aiohttp_client(create_app(TeleopLoop(arm=arm, inputs=InputState())))
    for path in (
        "/webcam",
        "/static/webcam.js",
        "/static/webcam-hands.js",
        "/web/vendor/mediapipe/vision_bundle.mjs",
        "/web/vendor/mediapipe/wasm/vision_wasm_internal.js",
        "/web/vendor/mediapipe/hand_landmarker.task",
    ):
        resp = await client.get(path)
        assert resp.status == 200, path
    wasm = await client.get("/web/vendor/mediapipe/wasm/vision_wasm_internal.wasm")
    assert wasm.status == 200
    # the browser compiles wasm while it downloads only with this type
    assert wasm.content_type == "application/wasm"


async def test_webcam_input_moves_the_fake_arm(aiohttp_client):
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState())
    client = await aiohttp_client(create_app(loop))
    ws = await client.ws_connect("/ws")

    def frame(x, grip):
        hand = {"pos": [x, 0.0, 0.5], "quat": [0, 0, 0, 1], "trigger": 0.0, "grip": grip}
        return {"type": "xr_input", "t": 0, "source": "webcam", "hands": {"right": hand}}

    start = dict(arm.read_joints())
    await ws.send_json(frame(0.0, 1.0))  # clutch held
    for i in range(30):
        await ws.send_json(frame(0.01 * i, 1.0))  # the hand moves to the right
        await asyncio.sleep(0.02)
    assert arm.read_joints() != start
    await ws.close()


# ---- the page's maths -------------------------------------------------------------------------


def hand(wrist_x, label="Left"):
    return {"image": [{"x": wrist_x, "y": 0.5}], "label": label}


@needs_node
def test_sides_by_place_and_label():
    # one hand: MediaPipe's label as it is (quick job 88: the opposite label swapped the hands on a
    # real webcam)
    assert run(f"return m.sidesOf([{json.dumps(hand(0.3, 'Right'))}])") == ["right"]
    assert run(f"return m.sidesOf([{json.dumps(hand(0.3, 'Left'))}])") == ["left"]
    assert run(f"return m.sidesOf([{json.dumps(hand(0.3, 'Right'))}], true)") == ["left"]
    # two hands, different labels: the labels (they follow crossed arms)
    crossed = json.dumps([hand(0.8, "Right"), hand(0.2, "Left")])
    assert run(f"return m.sidesOf({crossed})") == ["right", "left"]
    # two hands, the same label: the person's right hand is on the picture's left
    two = json.dumps([hand(0.8, "Left"), hand(0.2, "Left")])
    assert run(f"return m.sidesOf({two})") == ["left", "right"]
    assert run(f"return m.sidesOf({two}, true)") == ["right", "left"]


@needs_node
def test_pinch():
    def pinch(d):
        return run(
            "const w = Array.from({length: 21}, () => ({x: 0, y: 0, z: 0}));"
            f"w[8] = {{x: {d}, y: 0, z: 0}}; return m.pinchAmount(w);"
        )

    assert pinch(0.07) == 0  # a relaxed open hand
    assert pinch(0.02) == 1
    assert 0.3 < pinch(0.035) < 0.7


PALM_WORLD = (
    "const world = Array.from({length: 21}, () => ({x: 0, y: 0, z: 0}));"
    "world[5] = {x: 0.08, y: 0, z: 0}; world[17] = {x: 0, y: 0.08, z: 0};"
    "world[9] = {x: 0.06, y: 0.06, z: 0};"
)


def wrist(cx, cy, size_px, depth=True):
    """The wrist position for a palm drawn `size_px` wide at picture point (cx, cy) of 1280×720."""
    return run(
        PALM_WORLD + "const W = 1280, H = 720;"
        f"const at = (dx, dy) => ({{x: ({cx} + dx) / W, y: ({cy} + dy) / H}});"
        "const img = Array.from({length: 21}, () => at(0, 0));"
        f"img[5] = at({size_px}, 0); img[17] = at(0, {size_px});"
        f"img[9] = at(0.75 * {size_px}, 0.75 * {size_px});"
        f"return m.wristPosition(img, world, W, H, {{depth: {json.dumps(depth)}}});"
    )


@needs_node
def test_wrist_position():
    f = run("return m.focalPx(1280, 720)")
    centre = wrist(640, 360, 100)
    assert centre[0] == pytest.approx(0) and centre[1] == pytest.approx(0)
    assert centre[2] == pytest.approx(f * 0.08 / 100)  # a bigger palm = a closer hand
    near = wrist(640, 360, 200)
    assert near[2] < centre[2]  # toward the camera = forward = smaller z
    # the picture's left is the person's right (+x); the picture's top is up (+y)
    left_top = wrist(300, 100, 100)
    assert left_top[0] > 0 and left_top[1] > 0
    assert wrist(640, 360, 200, depth=False)[2] == 0.5  # depth off: a flat plane


STEP = """
const h = new m.WebcamHands();
const R = (x, pinch = 0) => ({side: "right", pos: [x, 0, 0.5], pinch});
const L = (pinch) => ({side: "left", pos: [0, 0, 0.5], pinch});
const out = [];
const go = (hands, t, space = false) => { const o = h.step(hands, t, space);
  out.push({state: o.state, grip: o.msg.hands.right.grip, pos: o.msg.hands.right.pos,
            quat: o.msg.hands.right.quat, clutch: o.clutch,
            source: o.msg.source, frame: o.msg.frame ?? null, left: "left" in o.msg.hands}); };
// a hand counts only after a few frames in a row: show them before t (not recorded)
const warm = (hands, t, space = false) => {
  for (let i = m.STEADY_FRAMES - 1; i > 0; i--) h.step(hands, t - i * 0.03, space); };
"""


@needs_node
def test_freeze_until_the_clutch_is_let_go():
    out = run(
        STEP
        + """
warm([R(0), L(0)], 0.00);
go([R(0), L(1)], 0.00);         // clutch held: following
go([L(1)], 0.03);               // right hand out of view: tracking lost, frozen
warm([R(0.05), L(1)], 0.06);
go([R(0.05), L(1)], 0.06);      // back, clutch still held: still frozen, grip 0
go([R(0.05), L(0)], 0.09);      // clutch let go: unfrozen, holding
go([R(0.05), L(1)], 0.12);      // pinch again: following
return out;"""
    )
    assert [o["state"] for o in out] == ["following", "frozen", "frozen", "holding", "following"]
    assert out[1]["pos"] is None and out[1]["grip"] == 0
    assert out[2]["grip"] == 0 and out[2]["pos"] is not None
    assert out[4]["grip"] == 1
    # the Quest's bare-hands message, relative only, the right hand only (a second arm holds)
    assert all(o["source"] == "webcam" and o["frame"] is None and not o["left"] for o in out)


@needs_node
def test_space_is_a_clutch_and_a_lost_hand_without_it_needs_nothing():
    out = run(
        STEP
        + """
warm([R(0)], 0.00);
go([R(0)], 0.00, true);         // Space held, no left hand: following
go([], 0.03, false);            // hand gone with the clutch let go: holds, no freeze
warm([R(0.2)], 0.2);
go([R(0.2)], 0.2, true);        // back with Space: follows from the new place
return out;"""
    )
    assert [o["state"] for o in out] == ["following", "no hand", "following"]


@needs_node
def test_a_jump_is_tracking_lost():
    out = run(
        STEP
        + """
warm([R(0), L(0)], 0.00);
go([R(0), L(1)], 0.00);
go([R(0.01), L(1)], 0.03);
go([R(0.5), L(1)], 0.06);       // 49 cm in 30 ms: not a real hand
return out;"""
    )
    assert out[1]["state"] == "following"
    assert out[2]["state"] == "frozen" and out[2]["pos"] is None


@needs_node
def test_a_hand_counts_only_after_a_few_frames():
    """Quick job 88: a left hand that wasn't there showed for a few seconds. A hand for fewer than
    STEADY_FRAMES frames in a row is ignored, so a short ghost pinch never holds the clutch."""
    out = run(
        STEP
        + """
warm([R(0)], 0.0);
for (let i = 0; i < m.STEADY_FRAMES - 1; i++) go([R(0), L(1)], 0.03 * i);  // a ghost left pinch
go([R(0)], 0.2);                                                         // gone again
for (let i = 0; i < m.STEADY_FRAMES; i++) go([R(0), L(1)], 0.3 + 0.03 * i);  // a real one
return out;"""
    )
    steady = run("return m.STEADY_FRAMES")
    assert all(o["clutch"] == 0 and o["state"] == "holding" for o in out[:steady])
    assert out[-1]["clutch"] == 1 and out[-1]["state"] == "following"


@needs_node
def test_the_hands_moves_count_more_than_one_to_one():
    """Quick job 88: the picture is smaller than the arm's reach, so a move counts REACH times."""
    out = run(
        STEP
        + """
warm([R(0), L(0)], 0.0);
go([R(0), L(1)], 0.0);
for (let i = 1; i <= 60; i++) go([R(0.002 * i), L(1)], 0.033 * i);  // 12 cm in 2 s, then still
for (let i = 61; i <= 150; i++) go([R(0.12), L(1)], 0.033 * i);
return out;"""
    )
    reach = run("return m.REACH")
    assert reach > 1
    assert out[-1]["pos"][0] == pytest.approx(0.12 * reach, abs=0.003)


def turned(roll_deg=0.0, tilt_deg=0.0):
    """World landmarks of a flat hand, fingers up, palm to the camera, turned in the picture by
    `roll_deg` (about the camera's axis) and tilted by `tilt_deg` (fingers toward the camera)."""
    return (
        "const rot = (p, r, t) => {"
        "  const [cr, sr, ct, st] = [Math.cos(r), Math.sin(r), Math.cos(t), Math.sin(t)];"
        "  let {x, y, z} = p; [y, z] = [y * ct - z * st, y * st + z * ct];"
        "  return {x: x * cr - y * sr, y: x * sr + y * cr, z}; };"
        "const base = Array.from({length: 21}, () => ({x: 0, y: 0, z: 0}));"
        "base[5] = {x: -0.03, y: -0.08, z: 0}; base[17] = {x: 0.04, y: -0.07, z: 0};"
        "base[9] = {x: 0, y: -0.085, z: 0};"  # picture y is down: fingers up = −y
        f"const [r, t] = [{roll_deg} * Math.PI / 180, {tilt_deg} * Math.PI / 180];"
        "const w = base.map((p) => rot(p, r, t));"
    )


def twist_deg(q, axis):
    """The turn about one room axis, as the brain measures it (mapping.py `_twist_deg`)."""
    import math

    return math.degrees(2 * math.atan2(q[axis], q[3]))


@needs_node
def test_the_hands_turn_is_sent_like_the_quests():
    """Quick job 88: hand roll → wrist_roll, hand tilt → wrist_flex, as on the Quest: the page sends
    the hand's turn, and the brain reads its change about the room's axes (x: tilt, z: roll)."""

    def quat(roll=0.0, tilt=0.0):
        return run(turned(roll, tilt) + "return m.axesQuat(m.handAxes(w));")

    rest = quat()
    rolled = quat(roll=30)
    tilted = quat(tilt=30)

    def rel(q):  # q · rest⁻¹
        x1, y1, z1, w1 = q
        x2, y2, z2, w2 = -rest[0], -rest[1], -rest[2], rest[3]
        return [
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        ]

    assert abs(twist_deg(rel(rolled), 2)) == pytest.approx(30, abs=1)  # roll: about forward
    assert abs(twist_deg(rel(rolled), 0)) < 2
    assert abs(twist_deg(rel(tilted), 0)) == pytest.approx(30, abs=1)  # tilt: about left-right
    assert abs(twist_deg(rel(tilted), 2)) < 2
    # through WebcamHands: the turn is in the message (no turn measured: a fixed one)
    out = run(
        turned(30)
        + STEP
        + """
const RA = (axes) => ({side: "right", pos: [0, 0, 0.5], pinch: 0, axes});
warm([RA(m.handAxes(w))], 0.0);
go([RA(m.handAxes(w))], 0.0);
go([R(0)], 0.03);
return out;"""
    )
    assert out[0]["quat"] != [0, 0, 0, 1] and out[1]["quat"] == [0, 0, 0, 1]
