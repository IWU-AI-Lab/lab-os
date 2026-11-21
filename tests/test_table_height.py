"""A table height per arm (quick job 28): so101-white stands on a ~1.6 cm plate, so its z = 0 is
above the table. Every height the AI tools, pick_at, the floor and teleop use is measured from the
table. Fake arm, no hardware."""

import asyncio
from types import SimpleNamespace

import pytest

from lab_os.devices import load_registry, table_z_cm
from lab_os.hub.server import side_view_cm
from lab_os.kinematics import kinematics_for, on_table, solve_ik
from lab_os.robots.fake import SO101_READY, FakeArm
from lab_os.teleop.cli import teleop_floor_m
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.tools import pose_view as pv
from lab_os.tools.robot import Refused, RobotTools
from lab_os.venues import Venue

PLATE = -1.6


def test_the_setting_per_arm():
    reg = load_registry()
    assert reg.devices["so101-white"].table_z_cm == PLATE
    assert table_z_cm("so101-white") == PLATE
    assert table_z_cm("so101-green") == 0.0
    assert table_z_cm("fake-arm") == 0.0
    assert table_z_cm("no-such-arm") == 0.0


def test_kinematics_from_the_table():
    kin = kinematics_for("so101")
    assert on_table(kin, 0.0) is kin  # nothing to change
    table = on_table(kin, PLATE)
    (x, y, z), a = kin.fk(SO101_READY)
    (tx, ty, tz), ta = table.fk(SO101_READY)
    assert (tx, ty, ta) == (x, y, a) and tz == pytest.approx(z + 0.016)
    assert table.frames(SO101_READY)["tip"][0][2] == pytest.approx(z + 0.016)
    assert table.roll_sign == kin.roll_sign
    # IK aims in table heights: 5 cm above the table = 3.4 cm in the arm's own numbers
    q = solve_ik(table, SO101_READY, (x, y, 0.05), a)
    assert kin.fk(q)[0][2] == pytest.approx(0.034, abs=0.002)
    assert not hasattr(on_table(kinematics_for("xarm1s"), PLATE), "frames")  # the xArm has none


async def rig(table=PLATE, **ai_tools):
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState(), speed_scale=1.0)
    venue = Venue("test", ("fake-arm",), True, 1.0, ai_tools={"deg_per_s": 900} | ai_tools)
    tools = RobotTools(loop, venue, {"ws": None}, poses={}, table_z_cm=table)
    return tools, asyncio.create_task(loop.run())


async def test_arm_status_measures_from_the_table_and_says_so():
    tools, task = await rig()
    plain, task2 = await rig(table=0.0)
    try:
        s, s0 = await tools.arm_status(), await plain.arm_status()
    finally:
        task.cancel()
        task2.cancel()
    assert s["gripper_point_cm"]["z"] == pytest.approx(s0["gripper_point_cm"]["z"] + 1.6, abs=0.1)
    assert s["table_z_cm"] == PLATE and "stands 1.6 cm above" in s["frame"]
    assert s0["table_z_cm"] == 0.0 and "above it" not in s0["frame"]


async def test_move_to_and_the_floor_are_from_the_table():
    tools, task = await rig()
    try:
        start = (await tools.arm_status())["gripper_point_cm"]
        r = await tools.call("move_to", x_cm=start["x"], y_cm=start["y"], z_cm=3.0)
        assert r["gripper_point_cm"]["z"] == pytest.approx(3.0, abs=0.5)
        arm_z = kinematics_for("so101").fk(tools.arm.read_joints())[0][2] * 100
        assert arm_z == pytest.approx(1.4, abs=0.5)  # 1.6 cm lower in the arm's own numbers
        # the 1 cm floor is 1 cm above the TABLE: z 0.5 from the table is refused
        with pytest.raises(Refused, match="below the 1 cm floor"):
            await tools.call("move_to", x_cm=start["x"], y_cm=start["y"], z_cm=0.5)
    finally:
        task.cancel()


async def test_pick_at_grips_from_the_table():
    """The grip height is measured from the table (quick job 28): as deep as the jaws reach
    (quick job 51: 4 cm below the top), never below the floor, here -0.5 cm."""
    tools, task = await rig(min_z_cm=-0.5)
    try:
        for _ in range(4):
            await tools.call("move_to", x_cm=20, y_cm=0, z_cm=9, tool_angle_deg=180)
        n = len(tools.calls.entries)
        await tools.call("pick_at", x_cm=20, y_cm=0, height_cm=3)
    finally:
        task.cancel()
    downs = [e for e in tools.calls.entries[n:] if e["tool"] == "move_to"]
    assert downs[1]["args"]["z_cm"] == pytest.approx(-0.5)  # the floor: 3 - 4 cm is below it


def test_teleop_floor_in_the_arms_own_heights():
    venue = SimpleNamespace(floor_cm=-0.5)
    assert teleop_floor_m(venue, "so101-white") == pytest.approx(-0.021)
    assert teleop_floor_m(venue, "fake-arm") == pytest.approx(-0.005)


def test_the_side_view_and_pose_view_put_the_arm_on_its_plate():
    kin = on_table(kinematics_for("so101"), PLATE)
    side = side_view_cm(kin, SO101_READY)
    assert side[0] == {"name": "base", "r": 0.0, "z": 1.6}
    png = pv.render("so101", SO101_READY, (25.0, 0.0, 6.5), 120.0, table_z_cm=PLATE)
    assert png.startswith(b"\x89PNG")
