"""The headset's teleop status panel (quick job 37): what it says in each state and how serious each
is (its colour), in the hub's words: plain, no dot separators. Runs the page's own module with node;
skipped without node. The drawing (cut corners, theme colours and fonts) was checked by eye."""

import json
import shutil
import subprocess

import pytest

from lab_os import REPO_ROOT

MODULE = REPO_ROOT / "src/lab_os/teleop/web/status-text.js"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node isn't installed")

STATUS = {
    "clutch": False,
    "mode": "relative",
    "speed_scale": 0.5,
    "limits": {"gripper": [0, 100]},
    "one_to_one_deg_per_s": 180,
    "capture_cm": 6,
}


def panel(
    status=STATUS,
    frozen=False,
    gripper=42,
    no_controller=False,
    source="controllers",
    moving=False,
    off=None,
):
    feed = (
        None
        if status is None
        else {"status": status, "frozen": frozen, "joints": {"gripper": gripper}}
    )
    args = json.dumps([feed, no_controller, source, moving, off])
    script = (
        f"import({json.dumps(MODULE.as_uri())}).then(m => "
        f"console.log(JSON.stringify(m.panelText(...{args}))))"
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.parametrize(
    "kw, state, level",
    [
        ({}, "Holding", "normal"),
        ({"status": STATUS | {"clutch": True}}, "Following", "following"),
        ({"status": STATUS | {"clutch": True, "one_to_one": True}}, "Following 1:1", "following"),
        (
            {"status": STATUS | {"clutch": True, "one_to_one": True, "servos": {"hot": True}}},
            "1:1 slowed: servos warm",
            "warning",
        ),
        ({"frozen": True}, "Stopped", "held"),
        ({"frozen": True, "status": STATUS | {"needs_release": True}}, "Stopped", "held"),
        ({"no_controller": True}, "No controller", "warning"),
        ({"no_controller": True, "source": "hands"}, "No right hand", "warning"),
        ({"status": None}, "Connecting…", "offline"),
        ({"status": STATUS | {"arm": {"connected": False}}}, "Arm disconnected", "offline"),
        (
            {"status": STATUS | {"mode": "one_to_one", "hand_gap_cm": 14.4}},
            "Reach the gripper: 14 cm",
            "normal",
        ),
    ],
)
def test_each_state_and_how_serious(kw, state, level):
    p = panel(**kw)
    assert (p["state"], p["level"]) == (state, level)
    assert "·" not in p["state"] and not any("·" in h for h in p["hint"])


def test_gripper_and_speed():
    p = panel(gripper=42)
    assert p["gripper"] == 42 and p["speed"] == {"label": "Speed", "value": 50, "unit": "%"}
    one = panel(status=STATUS | {"mode": "one_to_one"})
    assert one["speed"] == {"label": "Speed 1:1", "value": 180, "unit": "°/s top"}
    no_cap = panel(status=STATUS | {"mode": "one_to_one", "one_to_one_deg_per_s": None})
    assert no_cap["speed"]["value"] is None and no_cap["speed"]["unit"] == "servo max"
    assert panel(status=None)["gripper"] is None and panel(status=None)["speed"] is None


def test_the_hint_fits_the_way_in():
    assert panel()["hint"] == ["Hold grip = move", "trigger = gripper", "A/X = stop"]
    assert panel(source="hands")["hint"] == ["Hold left pinch = move", "right pinch = gripper"]
    assert panel(no_controller=True)["hint"][0] == "Pick up the controllers"
    assert panel(status=STATUS | {"mode": "one_to_one"})["hint"][0] == "1:1: hand in the ball"


TWO = STATUS | {
    "left_arm": {"connected": True, "frozen": False, "clutch": False, "needs_release": False}
}


@pytest.mark.parametrize(
    "left, state, level",
    [
        ({}, "Left holding", "normal"),
        ({"clutch": True}, "Left following", "following"),
        ({"frozen": True}, "Left stopped", "held"),
        ({"frozen": True, "needs_release": True}, "Left stopped: let go", "held"),
        ({"connected": False}, "Left disconnected", "offline"),
    ],
)
def test_two_arms_each_has_its_state(left, state, level):
    """Two arms at once (preview 3): the left arm's chip, and the right one says "Right …"."""
    s = TWO | {"left_arm": TWO["left_arm"] | left, "clutch": True}
    p = panel(status=s)
    assert p["left"] == {"state": state, "level": level}
    assert (p["state"], p["level"]) == ("Right following", "following")


def test_two_arms_hint_and_short_frozen_words():
    p = panel(status=TWO)
    assert p["hint"] == ["Grip = move its arm", "trigger = gripper", "Y + grip = move 3D arm",
                         "A/X = stop both"]  # fmt: skip
    frozen = panel(frozen=True, status=TWO | {"needs_release": True})
    assert frozen["state"] == "Right stopped: let go"
    assert panel(status=TWO, source="hands")["hint"][0] == "Two arms: controllers only"
    assert panel(status=TWO, no_controller=True)["left"] is None  # one message: pick them up
    assert panel()["left"] is None  # one arm: as before


def test_two_arms_y_held_says_the_grips_move_the_3d_arms():
    p = panel(status=TWO, moving=True)
    assert p["hint"][0] == "Y held: a grip moves its 3D arm" and "tap Y = put back" in p["hint"]


def test_two_arms_in_1_to_1_each_arm_says_where_its_hand_is():
    left = TWO["left_arm"] | {"mode": "one_to_one", "hand_gap_cm": 14.4, "capture_cm": 8.0}
    s = TWO | {"mode": "one_to_one", "hand_gap_cm": 20.2, "left_arm": left}
    p = panel(status=s)
    assert p["state"] == "Right: reach the gripper 20 cm"
    assert p["left"] == {"state": "Left: reach the gripper 14 cm", "level": "normal"}
    assert p["hint"][0] == "1:1: each hand in its ball"
    held = left | {"clutch": True, "one_to_one": True}
    assert panel(status=s | {"left_arm": held})["left"]["state"] == "Left following 1:1"


@pytest.mark.parametrize(
    "off, state, hint",
    [
        ({"from": "desk"}, "lab-os is off", ["The arm was let go", "Start it from its icon"]),
        ({"from": "desk", "restart": True}, "lab-os is restarting", ["It comes back by itself"]),
    ],
)
def test_says_lab_os_is_off_in_the_headset(off, state, hint):
    """Quick job 44: the page's "lab-os is off" cover isn't seen in the headset; the panel says it,
    whatever the arm was doing (two arms too), with nothing that looks live."""
    two = STATUS | {"clutch": True, "left_arm": {"connected": True, "frozen": False}}
    t = panel(status=two, off=off)
    assert (t["state"], t["level"], t["hint"]) == (state, "offline", hint)
    assert t["gripper"] is None and t["speed"] is None and t["left"] is None


def test_stopped_says_what_to_do():
    """Quick job 66: "frozen: release grip" said neither what happened nor what to do. The chip
    says what happened; the hint says what to do."""
    held = panel(frozen=True, status=STATUS | {"needs_release": True})
    assert held["hint"] == ["Let go of the grip", "then grab again"]
    hands = panel(frozen=True, status=STATUS | {"needs_release": True}, source="hands")
    assert hands["hint"] == ["Let go of the pinch", "then pinch again"]
    assert panel(frozen=True)["hint"] == ["Hold grip = move", "trigger = gripper", "A/X = stop"]
    assert "release" not in held
