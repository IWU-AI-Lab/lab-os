"""pick_at: one call for a whole pick (focus item 6, decision 2026-11-16) on the fake SO-101: the
steps in order and announced before they move, holding vs missed, the checks before anything
moves, STOP mid-pick. No hardware."""

import asyncio

import pytest

from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.tools.robot import Refused, RobotTools
from lab_os.venues import Venue

FAST = {"deg_per_s": 900}
SPOT = (20.0, 0.0)  # a cube 20 cm in front of the base


class CubeInTheJaws(FakeArm):
    """The jaws stop on something `width` degrees open once they close at the spot."""

    def __init__(self, stop_deg: float):
        super().__init__()
        self.stop_deg = stop_deg

    def move_joints(self, targets, speed_scale, deg_per_s=None):
        if "gripper" in targets:
            targets = dict(targets) | {"gripper": max(targets["gripper"], self.stop_deg)}
        super().move_joints(targets, speed_scale, deg_per_s)


async def make(arm=None, **ai_tools):
    arm = arm or FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState(), speed_scale=1.0)
    venue = Venue("test", ("fake-arm",), True, 1.0, ai_tools=FAST | ai_tools)
    return RobotTools(loop, venue, {"ws": None}, poses={}), asyncio.create_task(loop.run())


async def near_the_spot(tools):
    """Like the AI would: move_to above the spot first (within the 10 cm a call allows)."""
    for _ in range(4):
        await tools.call("move_to", x_cm=SPOT[0], y_cm=SPOT[1], z_cm=8.5, tool_angle_deg=180)


async def test_a_pick_runs_the_five_steps_in_order_each_announced_first():
    tools, task = await make()
    try:
        await near_the_spot(tools)
        n = len(tools.calls.entries)
        r = await tools.call("pick_at", x_cm=SPOT[0], y_cm=SPOT[1])
    finally:
        task.cancel()
    log = [(e["tool"], e["outcome"]) for e in tools.calls.entries[n:]]
    pairs = [(log[i], log[i + 1]) for i in range(0, 10, 2)]
    assert [a for a, _ in pairs] == [("pick_at", "next")] * 5  # said before each move
    assert [b[0] for _, b in pairs] == ["gripper", "move_to", "move_to", "gripper", "move_to"]
    assert log[-1] == ("pick_at", "ok")
    assert [s["step"][:3] for s in r["steps"]] == ["1/5", "2/5", "3/5", "4/5", "5/5"]
    assert r["result"] == "missed" and "closed on nothing" in r["message"]  # fake jaws shut
    p = r["gripper_point_cm"]
    assert p["x"] == pytest.approx(20, abs=0.5) and p["z"] == pytest.approx(8.5, abs=0.5)


async def test_jaws_stopped_on_something_say_holding():
    probe = FakeArm()
    lo, hi = probe.limits["gripper"].low + 3, probe.limits["gripper"].high - 3
    tools, task = await make(CubeInTheJaws(stop_deg=lo + (hi - lo) * 0.3))  # stops at 30 %
    try:
        await near_the_spot(tools)
        r = await tools.call("pick_at", x_cm=SPOT[0], y_cm=SPOT[1])
    finally:
        task.cancel()
    assert r["result"] == "holding" and "holding something" in r["message"]
    assert len(r["steps"]) == 5


async def test_too_far_away_is_refused_before_anything_moves():
    tools, task = await make()
    try:
        before = tools.arm.read_joints()
        with pytest.raises(Refused, match="move_to near it first"):
            await tools.call("pick_at", x_cm=30, y_cm=-15)
        assert tools.arm.read_joints() == before
    finally:
        task.cancel()


async def test_out_of_reach_and_odd_sizes_are_refused():
    tools, task = await make(max_move_cm=1000)  # the per-call limit off: only reach counts
    try:
        before = tools.arm.read_joints()
        with pytest.raises(Refused, match="can't reach"):
            await tools.call("pick_at", x_cm=60, y_cm=0)
        with pytest.raises(Refused, match="0.5–8 cm tall"):
            await tools.call("pick_at", x_cm=20, y_cm=0, height_cm=12)
        with pytest.raises(Refused):
            await tools.call("pick_at", x_cm=float("nan"), y_cm=0)
        assert tools.arm.read_joints() == before
    finally:
        task.cancel()


async def test_stop_mid_pick_ends_it_there():
    tools, task = await make()
    try:
        await near_the_spot(tools)
        tools.limits = type(tools.limits)(deg_per_s=20)  # slow, so STOP lands mid-pick
        pick = asyncio.create_task(tools.call("pick_at", x_cm=SPOT[0], y_cm=SPOT[1]))
        await asyncio.sleep(0.5)
        tools.loop.stop()  # STOP on any page
        r = await pick
    finally:
        task.cancel()
    assert r["result"] == "stopped" and "Don't move again" in r["message"]
    assert len(r["steps"]) < 5
