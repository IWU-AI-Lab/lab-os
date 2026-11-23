# ruff: noqa: F811 (`desk` is a fixture from test_arm_desk, used as an argument)
"""Quick job 81: one short program instead of many moves (`run_program`), on the fake arm."""

import asyncio
import json

import pytest
from test_arm_desk import SETUP, desk, joints_near  # noqa: F401 (desk: a fixture)

from lab_os.hub.arm_desk import locate_cube
from lab_os.tools.mcp_server import create_mcp_server
from lab_os.tools.program import MATH, STATISTICS, run_restricted

PICK_AND_HAND_OVER = """
def until_there(move):
    for i in range(30):
        r = move()
        if not any(c.startswith("went") for c in r.get("clipped", [])):
            return r
    return r

cube = find_cube()
if cube is None:
    raise ValueError("no cube")
x, y = cube["x_cm"], cube["y_cm"]
until_there(lambda: go_to_pose("ready"))
for i in range(10):
    p = move_to(x, y, 8.5, 180)["gripper_point_cm"]
    if abs(p["x"] - x) + abs(p["y"] - y) + abs(p["z"] - 8.5) < 1:
        break
held = pick_at(x, y, 2.5)["result"]
until_there(lambda: go_to_pose("handover"))
print("held:", held)
result = held
"""


def server_for(desk):
    return create_mcp_server(desk.robot, find_cube=lambda: locate_cube(desk.robot, SETUP))


async def run(server, code, **kw) -> dict:
    r = await server.call_tool("run_program", {"code": code, **kw})
    return json.loads(r.content[0].text)


async def test_one_program_picks_up_the_cube_and_holds_it_out(desk):
    out = await run(server_for(desk), PICK_AND_HAND_OVER)
    assert out["result"] == "done", out
    assert out["value"] == "holding" and out["printed"] == ["held: holding"]
    assert joints_near(desk, SETUP.pose)  # at the hand-over pose, the cube in the jaws
    assert desk.robot._gripper_pct(desk.robot.arm.read_joints()["gripper"]) > 15
    logged = [e["tool"] for e in desk.robot.calls.entries]  # every call on AI Control
    assert logged[0] == "camera_snapshot" and "pick_at" in logged and "move_to" in logged
    assert out["calls"][0]["call"] == "find_cube"


async def test_stop_ends_the_program_at_once(desk):
    server = server_for(desk)
    task = asyncio.create_task(run(server, "while True:\n    wait(0.2)"))
    await asyncio.sleep(0.3)
    await desk.robot.call("stop")
    out = await asyncio.wait_for(task, 5)
    assert out["result"] == "stopped" and out["line"] == 2


async def test_a_refusal_or_a_mistake_ends_it_with_its_line(desk):
    server = server_for(desk)
    out = await run(server, "go_to_pose('nowhere')")
    assert out["result"] == "error" and "nowhere" in out["error"] and out["line"] == 1
    out = await run(server, "x = 1\ny = x / 0")
    assert out["result"] == "error" and out["line"] == 2
    out = await run(server, "while True:\n    pass", time_limit_s=1)
    assert out["result"] == "time limit"


@pytest.mark.parametrize(
    "code",
    [
        "import os",
        "open('/etc/passwd')",
        "().__class__",
        "'{0.__class__}'.format(1)",
        "eval('1')",
    ],
)
def test_no_way_out_of_the_box(code):
    out = run_restricted(code, {}, 1)
    assert out["result"] == "error", out


def test_math_and_statistics_are_functions_only():
    reached = run_restricted("result = str(statistics.sys)", {}, 1)
    assert reached["result"] == "done" and reached["value"] == "None"  # nothing there
    assert not any(isinstance(v, type(json)) for v in vars(MATH).values())
    assert "sys" not in vars(STATISTICS) and "namedtuple" not in vars(STATISTICS)
    out = run_restricted("result = round(math.hypot(3, 4) + statistics.mean([1, 2, 3]), 3)", {}, 1)
    assert out["value"] == 7.0
