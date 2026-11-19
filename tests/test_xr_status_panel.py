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


def panel(status=STATUS, frozen=False, gripper=42, no_controller=False, source="controllers"):
    feed = (
        None
        if status is None
        else {"status": status, "frozen": frozen, "joints": {"gripper": gripper}}
    )
    args = json.dumps([feed, no_controller, source])
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
        ({"frozen": True}, "Frozen", "held"),
        (
            {"frozen": True, "status": STATUS | {"needs_release": True}},
            "Frozen: let go of the grip",
            "held",
        ),
        (
            {"frozen": True, "status": STATUS | {"needs_release": True}, "source": "hands"},
            "Frozen: let go of the pinch",
            "held",
        ),
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
