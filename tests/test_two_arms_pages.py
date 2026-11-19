"""Two arms at once on the pages (preview 3): each 3D arm follows only its own arm's messages
(ArmFeed by `device`), and in the headset holding Y turns the grips into "move the 3D arm" while
the real arms hold (ArmMoves). Runs the pages' own modules with node; skipped without node."""

import json
import shutil
import subprocess

import pytest

from lab_os import REPO_ROOT

WEB = REPO_ROOT / "src/lab_os/teleop/web"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node isn't installed")


def run(module: str, body: str):
    """Import `module` as `m`, run `body` (JS that ends by setting `out`), return `out`."""
    script = (
        f"import({json.dumps((WEB / module).as_uri())}).then(m => {{ let out; {body}; "
        "console.log(JSON.stringify(out)); })"
    )
    done = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


# ---------- ArmFeed: one per arm ----------

LINK = """
const handlers = {};
const link = { on: (t, fn) => (handlers[t] ||= []).push(fn) };
const send = (msg) => (handlers[msg.type] || []).forEach((fn) => fn(msg));
const status = (left) => ({ type: "status", frozen: false, clutch: false,
  joints: { shoulder_pan: 1 }, limits: {}, last_command: null,
  arm: { name: "so101-white", model: "so101" },
  left_arm: left ? { name: "so101-green", model: "so101", connected: true, problem: null,
    frozen: true, clutch: false, needs_release: true, joints: { shoulder_pan: 2 }, limits: {} }
    : null });
const right = m.getArmFeed(link), left = m.getArmFeed(link, "left");
"""


def test_each_feed_takes_only_its_own_arms_commands():
    out = run(
        "arm/arm-feed.js",
        LINK
        + """
        send(status(true));
        const before = { right: right.joints, left: left.joints, leftFrozen: left.frozen };
        send({ type: "arm_command", device: "so101-white", joints: { shoulder_pan: 10 } });
        send({ type: "arm_command", device: "so101-green", joints: { shoulder_pan: -10 } });
        send({ type: "arm_stop", device: "so101-green" });
        out = { before, right: right.joints, left: left.joints, rightFrozen: right.frozen,
                leftFrozen: left.frozen, leftName: left.status.arm.name, leftKind: left.modelKind,
                same: m.getArmFeed(link, "left") === left };
        """,
    )
    assert out["before"] == {"right": {"shoulder_pan": 1}, "left": {"shoulder_pan": 2},
                             "leftFrozen": True}  # fmt: skip
    assert out["right"] == {"shoulder_pan": 10} and out["left"] == {"shoulder_pan": -10}
    assert out["rightFrozen"] is False and out["leftFrozen"] is True
    assert (out["leftName"], out["leftKind"], out["same"]) == ("so101-green", "so101", True)


def test_one_arm_the_left_feed_has_no_status_and_commands_wait_for_a_status():
    out = run(
        "arm/arm-feed.js",
        LINK
        + """
        send({ type: "arm_command", device: "so101-white", joints: { shoulder_pan: 5 } });
        const early = right.lastCommand;
        send(status(false));
        send({ type: "arm_command", device: "so101-green", joints: { shoulder_pan: 9 } });
        const why = []; left.onChange((f, w) => why.push(w));
        send(status(true)); send(status(false));
        out = { early, leftStatus: left.status, leftJoints: left.joints, why };
        """,
    )
    assert out["early"] is None  # before any status the feed doesn't know which arm is its
    assert out["leftStatus"] is None and out["leftJoints"] == {}
    assert out["why"] == ["arm", "status", "arm"]  # a left arm came, then went


# ---------- ArmMoves: hold Y to move the 3D arms ----------


def moves(steps):
    """steps: [ms, y, left grip, right grip] → each step's result."""
    return run(
        "arm-moves.js",
        f"const a = new m.ArmMoves(); out = {json.dumps(steps)}.map(([t, y, l, r]) => "
        "a.step(t, y, { left: l, right: r }));",
    )


def test_without_y_the_grips_go_to_the_brain():
    r = moves([[0, False, 1.0, 0.5]])[0]
    assert r["send"] == {"left": 1.0, "right": 0.5} and not any(r["drag"].values())


def test_y_held_a_grip_moves_its_3d_arm_and_the_arms_hold():
    r = moves([[0, True, 0, 0], [20, True, 1.0, 0], [40, True, 1.0, 1.0]])
    assert r[1]["drag"] == {"left": True, "right": False}
    assert r[2]["drag"] == {"left": True, "right": True}
    assert all(x["send"] == {"left": 0, "right": 0} for x in r)  # the real arms hold
    assert not any(x["reset"] for x in r)


def test_a_grip_held_when_y_comes_up_reaches_the_brain_only_after_a_release():
    r = moves([[0, True, 0, 0], [20, True, 1.0, 0], [40, False, 1.0, 0], [60, False, 0, 0],
               [80, False, 1.0, 0]])  # fmt: skip
    assert r[2]["send"]["left"] == 0 and r[3]["send"]["left"] == 0
    assert r[4]["send"]["left"] == 1.0  # a fresh grip drives again


def test_a_grip_held_when_y_goes_down_must_be_let_go_before_it_moves_a_3d_arm():
    r = moves([[0, False, 1.0, 0], [20, True, 1.0, 0], [40, True, 0, 0], [60, True, 1.0, 0]])
    assert r[1]["drag"]["left"] is False and r[1]["send"]["left"] == 0  # the arm holds at once
    assert r[3]["drag"]["left"] is True


def test_a_short_tap_of_y_alone_puts_them_back():
    assert moves([[0, True, 0, 0], [200, False, 0, 0]])[1]["reset"] is True
    assert moves([[0, True, 0, 0], [900, False, 0, 0]])[1]["reset"] is False  # a long hold
    used = moves([[0, True, 0, 0], [100, True, 1.0, 0], [200, False, 0, 0]])
    assert used[2]["reset"] is False  # a grip was used: it moved a 3D arm
