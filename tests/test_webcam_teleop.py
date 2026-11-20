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
    # one hand: MediaPipe's label is for a mirrored picture, so it's the other hand
    assert run(f"return m.sidesOf([{json.dumps(hand(0.3, 'Left'))}])") == ["right"]
    assert run(f"return m.sidesOf([{json.dumps(hand(0.3, 'Right'))}])") == ["left"]
    # two hands, different labels: the labels (they follow crossed arms)
    crossed = json.dumps([hand(0.8, "Left"), hand(0.2, "Right")])
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
            source: o.msg.source, frame: o.msg.frame ?? null, left: "left" in o.msg.hands}); };
"""


@needs_node
def test_freeze_until_the_clutch_is_let_go():
    out = run(
        STEP
        + """
go([R(0), L(1)], 0.00);         // clutch held: following
go([L(1)], 0.03);               // right hand out of view: tracking lost, frozen
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
go([R(0)], 0.00, true);         // Space held, no left hand: following
go([], 0.03, false);            // hand gone with the clutch let go: holds, no freeze
go([R(0.2)], 0.06, true);       // back with Space: follows from the new place
return out;"""
    )
    assert [o["state"] for o in out] == ["following", "no hand", "following"]


@needs_node
def test_a_jump_is_tracking_lost():
    out = run(
        STEP
        + """
go([R(0), L(1)], 0.00);
go([R(0.01), L(1)], 0.03);
go([R(0.5), L(1)], 0.06);       // 49 cm in 30 ms: not a real hand
return out;"""
    )
    assert out[1]["state"] == "following"
    assert out[2]["state"] == "frozen" and out[2]["pos"] is None
