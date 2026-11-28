"""The robot tools for AI on the fake arm: moves, the safety rules (clip, refuse, stop), the call
log, the named poses, and the MCP server (in memory and over HTTP). No hardware, no internet."""

import asyncio
import json
import math
import socket
from dataclasses import replace

import pytest
from mcp import Client

from lab_os.kinematics import kinematics_for
from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, Motion, TeleopLoop
from lab_os.tools.calllog import CallLog
from lab_os.tools.mcp_server import McpHttp, create_mcp_server
from lab_os.tools.robot import LIMIT_MARGIN_DEG, AiLimits, Refused, RobotTools, load_poses
from lab_os.venues import Venue

FAST = {"deg_per_s": 900}  # tests don't wait for real-time motion


def venue(motion_allowed=True, **ai_tools):
    return Venue("test", ("fake-arm",), motion_allowed, 1.0, ai_tools=FAST | ai_tools)


@pytest.fixture
async def rig():
    """A running teleop loop on the fake arm, and the tools for it."""
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState(), speed_scale=1.0)
    task = asyncio.create_task(loop.run())
    control = {"ws": None}
    tools = RobotTools(loop, venue(), control)
    yield tools
    task.cancel()


def tip(tools):
    return tools._where()["gripper_point_cm"]


# ---------- reading ----------


async def test_arm_status(rig):
    s = await rig.arm_status()
    assert s["connected"] and s["arm"] == "fake-arm" and s["control"] == "free"
    assert set(s["joints_deg"]) == set(rig.arm.joint_names)
    assert 0 <= s["gripper_open_pct"] <= 100
    assert s["gripper_point_cm"]["x"] > 20  # the fake arm starts reaching forward
    assert s["per_call"] == {"max_joint_change_deg": 30, "max_move_cm": 10, "min_z_cm": 1}
    assert s["motion_allowed"] is True


async def test_list_poses(rig):
    poses = (await rig.list_poses())["poses"]
    assert {"ready", "home"} <= set(poses)


# ---------- moving ----------


async def test_move_joints_arrives_and_reports_the_real_position(rig):
    r = await rig.call("move_joints", joints={"shoulder_pan": 20})
    assert r["result"] == "arrived" and r["clipped"] == []
    assert r["joints_deg"]["shoulder_pan"] == 20
    r = await rig.call("move_joints", joints={"shoulder_pan": -10}, relative=True)
    assert r["joints_deg"]["shoulder_pan"] == 10


async def test_move_to_goes_in_a_straight_line(rig):
    start = tip(rig)
    path_z = []
    rig.loop.on_command = lambda m: (
        m["type"] == "arm_command" and path_z.append(rig.kin.fk(rig.arm.read_joints())[0][2] * 100)
    )
    r = await rig.call("move_to", x_cm=start["x"] + 4, y_cm=start["y"], z_cm=start["z"])
    end = r["gripper_point_cm"]
    assert abs(end["x"] - (start["x"] + 4)) < 0.3 and abs(end["z"] - start["z"]) < 0.3
    assert max(abs(z - start["z"]) for z in path_z) < 0.5  # stayed at the same height


async def test_gripper_open_and_close(rig):
    assert (await rig.call("gripper", open_pct=100))["gripper_open_pct"] == 100
    assert (await rig.call("gripper", open_pct=0))["gripper_open_pct"] == 0


async def test_go_to_pose(rig):
    r = await rig.call("go_to_pose", name="ready")  # where the fake arm starts
    assert r["result"] == "arrived"


# ---------- "arrived" only when it's there (GOTCHAS 2026-11-10) ----------


class SaggingArm(FakeArm):
    """Like a loaded real arm: the motors stop `sag` degrees short of the command on some joints.
    `read_joints` says where it was told to be (like the SO-101 while driving); `read_measured`
    says where the motors are."""

    def __init__(self, sag: dict[str, float]):
        super().__init__()
        self.sag = sag

    def read_measured(self) -> dict[str, float]:
        return {j: v - self.sag.get(j, 0.0) for j, v in self.read_joints().items()}


async def sagging_rig(sag):
    arm = SaggingArm(sag)
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState(), speed_scale=1.0)
    return RobotTools(loop, venue(), {"ws": None}), asyncio.create_task(loop.run())


async def test_move_to_on_target_says_arrived_and_how_close(rig):
    start = tip(rig)
    r = await rig.call("move_to", x_cm=start["x"] + 3, y_cm=start["y"], z_cm=start["z"])
    assert r["result"] == "arrived" and "message" not in r
    assert r["off_by_cm"] < 0.5
    assert r["target_cm"] == {"x": round(start["x"] + 3, 1), "y": start["y"], "z": start["z"]}


async def test_move_to_that_stops_short_says_how_far():
    tools, task = await sagging_rig({"elbow_flex": 6.0, "wrist_flex": 5.5})
    try:
        start = tip(tools)
        r = await tools.call("move_to", x_cm=start["x"] - 3, y_cm=0, z_cm=start["z"])
    finally:
        task.cancel()
    assert r["result"] == "stopped_short"
    assert r["off_by_cm"] > 0.5
    assert r["joints_short_deg"] == {"elbow_flex": 6.0, "wrist_flex": 5.5}
    assert f"stopped {r['off_by_cm']:.1f} cm from the target" in r["message"]
    assert "elbow_flex by 6.0°" in r["message"]
    # the position it reports is the measured one, not where the arm was told to go
    measured = tools.arm.read_measured()
    assert r["joints_deg"]["elbow_flex"] == round(measured["elbow_flex"], 1)
    assert tools.calls.entries[-1]["outcome"] == "short"


async def test_a_small_sag_within_tolerance_still_arrives():
    tools, task = await sagging_rig({"shoulder_pan": 1.0})
    try:
        r = await tools.call("move_joints", joints={"shoulder_pan": 5}, relative=True)
    finally:
        task.cancel()
    assert r["result"] == "arrived" and "joints_short_deg" not in r


async def test_the_white_arms_usual_sag_still_arrives_at_a_pose():
    """Quick job 77: so101-white's elbow ends 2.3-3.5° short nearly every move (GOTCHAS
    2026-11-12). A pose within that says "arrived", with no warning; a bigger miss still doesn't."""
    tools, task = await sagging_rig({"elbow_flex": 3.5, "shoulder_lift": 2.7})
    try:
        r = await tools.call("go_to_pose", name="ready")
    finally:
        task.cancel()
    assert r["result"] == "arrived" and "message" not in r and "joints_short_deg" not in r
    assert tools.calls.entries[-1]["outcome"] != "short"
    tools, task = await sagging_rig({"elbow_flex": 5.0})
    try:
        r = await tools.call("go_to_pose", name="ready")
    finally:
        task.cancel()
    assert r["result"] == "stopped_short" and r["joints_short_deg"] == {"elbow_flex": 5.0}


async def test_move_to_still_says_when_the_sag_puts_the_gripper_point_off():
    """The margin is for each joint only: the same 3.5° elbow sag moves the gripper point
    ~1.5 cm, and move_to still says so (a blind AI must not grip there; GOTCHAS 2026-11-10)."""
    tools, task = await sagging_rig({"elbow_flex": 3.5})
    try:
        start = tip(tools)
        r = await tools.call("move_to", x_cm=start["x"] - 3, y_cm=0, z_cm=start["z"])
    finally:
        task.cancel()
    assert r["result"] == "stopped_short" and r["off_by_cm"] > 0.5
    assert "joints_short_deg" not in r


async def test_a_gripper_that_closes_on_something_says_so():
    tools, task = await sagging_rig({"gripper": -30.0})  # stays open: something is in it
    try:
        r = await tools.call("gripper", open_pct=0)
    finally:
        task.cancel()
    assert r["result"] == "stopped_short"
    assert "may be holding something" in r["message"]
    assert "Likely load" not in r["message"]


async def test_a_failed_measured_read_falls_back_to_the_driver(rig, monkeypatch):
    def broken():
        raise ConnectionError("no answer")

    monkeypatch.setattr(rig.arm, "read_measured", broken, raising=False)
    r = await rig.call("move_joints", joints={"shoulder_pan": 5}, relative=True)
    assert r["result"] == "arrived"


# ---------- clipping: it moves, and says so ----------


async def test_joint_targets_are_clipped_to_the_soft_limits(rig):
    await rig.call("move_joints", joints={"shoulder_pan": 100})
    for _ in range(3):
        r = await rig.call("move_joints", joints={"shoulder_pan": 500})
    high = rig.arm.limits["shoulder_pan"].high - LIMIT_MARGIN_DEG
    assert r["joints_deg"]["shoulder_pan"] == round(high, 1)
    assert any("joint limit" in n for n in r["clipped"])
    assert rig.calls.entries[-1]["outcome"] == "clipped"


async def test_at_most_30_degrees_per_call_all_joints_the_same_fraction(rig):
    j0 = rig.arm.read_joints()
    r = await rig.call("move_joints", joints={"shoulder_pan": 60, "wrist_roll": 30}, relative=True)
    j1 = rig.arm.read_joints()
    assert math.isclose(j1["shoulder_pan"] - j0["shoulder_pan"], 30, abs_tol=1e-6)
    assert math.isclose(j1["wrist_roll"] - j0["wrist_roll"], 15, abs_tol=1e-6)
    assert "50% of the way" in r["clipped"][0]


async def test_the_gripper_is_exempt_from_the_per_call_change(rig):
    r = await rig.call("gripper", open_pct=0)
    r = await rig.call("gripper", open_pct=100)
    assert r["gripper_open_pct"] == 100 and r["clipped"] == []


async def test_gripper_percent_is_clipped_to_0_100(rig):
    r = await rig.call("gripper", open_pct=150)
    assert r["gripper_open_pct"] == 100 and "0–100" in r["clipped"][0]


async def test_move_to_goes_at_most_10_cm_per_call(rig):
    start = tip(rig)
    r = await rig.call("move_to", x_cm=start["x"], y_cm=start["y"] + 25, z_cm=start["z"])
    end = r["gripper_point_cm"]
    assert abs(math.dist(start.values(), end.values()) - 10) < 0.5
    assert "of the way" in r["clipped"][0]


async def test_go_to_pose_far_away_goes_part_of_the_way(rig):
    r = await rig.call("go_to_pose", name="home")  # ready → folded: shoulder_lift -20 → -97
    assert "of the way" in r["clipped"][-1]
    for _ in range(5):
        r = await rig.call("go_to_pose", name="home")
    # home sits at the soft limits (quick job 50): it arrives, and nothing says "clipped"
    assert r["clipped"] == []
    assert r["result"] == "arrived"
    j = r["joints_deg"]
    assert (j["shoulder_lift"], j["elbow_flex"], j["wrist_flex"]) == (-97.0, 93.8, 55.0)
    assert (j["shoulder_pan"], j["wrist_roll"], j["gripper"]) == (-2.2, 87.4, 16.5)


async def test_go_to_pose_moves_smoothly(rig):
    """Quick job 118: a move to a named pose starts slowly and slows down at the end."""
    seen = []
    rig.loop.start_motion = (lambda orig: lambda m: (seen.append(m), orig(m))[1])(
        rig.loop.start_motion
    )
    await rig.call("go_to_pose", name="home")
    await rig.call("move_joints", joints={"shoulder_pan": 5.0}, relative=True)
    assert [m.smooth for m in seen] == [True, False]


async def test_go_to_pose_in_one_move(rig):
    """The hub's chat: all the way at once (quick job 118). The AI tools keep the 30° steps."""
    r = await rig.call("go_to_pose", name="home", one_move=True)
    assert r["clipped"] == [] and r["result"] == "arrived"
    assert r["joints_deg"]["shoulder_lift"] == -97.0


# ---------- refusals: nothing moves, the message says why ----------


async def refused(rig, tool, match, **args):
    before = rig.arm.read_joints()
    with pytest.raises(Refused, match=match):
        await rig.call(tool, **args)
    assert rig.arm.read_joints() == before
    assert rig.calls.entries[-1]["outcome"] == "refused"


async def test_refused_while_teleop_has_control(rig):
    rig.control["ws"] = object()  # a teleop page is driving
    await refused(rig, "move_joints", "a person has control", joints={"shoulder_pan": 5})
    await refused(rig, "move_to", "a person has control", x_cm=25, y_cm=0, z_cm=5)
    await refused(rig, "gripper", "a person has control", open_pct=50)
    await refused(rig, "go_to_pose", "a person has control", name="ready")
    assert (await rig.arm_status())["control"] == "teleop"


async def test_refused_while_another_move_runs(rig):
    rig.loop.start_motion(Motion(path=[{"shoulder_pan": 40.0}], deg_per_s=1.0))
    await refused(rig, "move_joints", "another move", joints={"elbow_flex": 5})
    rig.loop.stop()


async def test_refused_when_the_venue_forbids_motion(rig):
    rig.venue = venue(motion_allowed=False)
    await refused(rig, "move_joints", "doesn't allow motion", joints={"shoulder_pan": 5})


async def test_refused_below_the_floor(rig):
    await refused(rig, "move_to", "below the 1 cm floor", x_cm=25, y_cm=0, z_cm=0.5)
    # tilting the upper arm forward 20° would put the gripper into the table (-1.2 cm)
    await refused(
        rig, "move_joints", "below the 1 cm floor", joints={"shoulder_lift": 20}, relative=True
    )


async def test_refused_out_of_reach(rig):
    start = tip(rig)
    far = {"x_cm": start["x"] + 24, "y_cm": 0, "z_cm": start["z"]}
    r = await rig.call("move_to", **far)  # the first 10 cm are reachable (stretched out)
    assert "of the way" in r["clipped"][0]
    await refused(rig, "move_to", "can't reach .*on the way to", **far)


async def test_near_full_stretch_the_gripper_still_moves_in_a_straight_line(rig):
    start = tip(rig)
    zs = []
    rig.loop.on_command = lambda m: (
        m["type"] == "arm_command" and zs.append(rig.kin.fk(rig.arm.read_joints())[0][2] * 100)
    )
    r = await rig.call("move_to", x_cm=start["x"] + 10, y_cm=0, z_cm=start["z"])
    assert r["result"] == "arrived"
    assert max(abs(z - start["z"]) for z in zs) < 0.5


async def test_refused_bad_names_and_numbers(rig):
    await refused(rig, "move_joints", "unknown joints", joints={"elbow": 5})
    await refused(rig, "move_joints", "no joints", joints={})
    await refused(rig, "move_joints", "must be a number", joints={"elbow_flex": math.nan})
    await refused(rig, "move_to", "must be a number", x_cm=math.inf, y_cm=0, z_cm=5)
    await refused(rig, "go_to_pose", "no pose called", name="dance")
    await refused(rig, "move_joints", "no arm called", joints={"elbow_flex": 5}, arm="so101-green")


# ---------- stop ----------


async def test_stop_is_always_allowed_even_while_teleop_has_control(rig):
    rig.control["ws"] = object()
    r = await rig.call("stop")
    assert r["result"] == "stopped" and rig.loop.frozen
    assert rig.calls.entries[-1]["outcome"] == "ok"


async def test_stop_from_a_page_ends_an_ai_move(rig):
    rig.limits = AiLimits(deg_per_s=10)  # slow, so STOP lands mid-move
    move = asyncio.create_task(rig.call("move_joints", joints={"shoulder_pan": 25}))
    await asyncio.sleep(0.3)
    assert (await rig.arm_status())["control"] == "ai"
    rig.loop.stop()  # what STOP on any page does
    r = await move
    assert r["result"] == "stopped" and "Don't move again" in r["clipped"][-1]
    assert 0 < r["joints_deg"]["shoulder_pan"] < 25
    assert rig.calls.entries[-1]["outcome"] == "stopped"


async def test_the_stop_tool_ends_an_ai_move(rig):
    rig.limits = AiLimits(deg_per_s=10)
    move = asyncio.create_task(rig.call("move_joints", joints={"shoulder_pan": 25}))
    await asyncio.sleep(0.3)
    await rig.call("stop")
    assert (await move)["result"] == "stopped"


async def test_a_cancelled_call_stops_the_arm(rig):
    rig.limits = AiLimits(deg_per_s=10)
    move = asyncio.create_task(rig.call("move_joints", joints={"shoulder_pan": 25}))
    await asyncio.sleep(0.3)
    move.cancel()  # the AI tool went away mid-move
    with pytest.raises(asyncio.CancelledError):
        await move
    assert not rig.loop.motion_active and rig.loop.frozen
    held = rig.arm.read_joints()
    await asyncio.sleep(0.2)
    assert rig.arm.read_joints() == held


# ---------- the call log ----------


async def test_every_call_is_logged_to_a_file(rig, tmp_path):
    rig.calls = CallLog(tmp_path / "run.jsonl")
    await rig.call("arm_status")
    await rig.call("gripper", open_pct=150)
    with pytest.raises(Refused):
        await rig.call("go_to_pose", name="dance")
    lines = [json.loads(x) for x in (tmp_path / "run.jsonl").read_text().splitlines()]
    assert [(e["tool"], e["outcome"]) for e in lines] == [
        ("arm_status", "ok"),
        ("gripper", "clipped"),
        ("go_to_pose", "refused"),
    ]
    assert lines[1]["args"] == {"open_pct": 150}
    assert "no pose called" in lines[2]["result"]


# ---------- config ----------


# Poses with a joint past its soft limit, and by how much (degrees): the move clips them to the
# limit. None since quick job 50 (home was 6.3° and 3.6° past, and every move to it said
# "clipped"); the limits aren't widened without the builder.
PAST_SOFT_LIMIT: dict[tuple[str, str, str], float] = {}


def test_every_named_pose_is_inside_the_limits_and_above_the_floor():
    from lab_os.robots.xarm import XArm
    from lab_os.teleop.mapping import soft_bounds
    from lab_os.venues import load_venue

    arms = {"so101": FakeArm(), "xarm1s": XArm()}
    floor = load_venue("lab").floor_cm  # from the table; an arm standing on it is the strictest
    for model, poses in load_poses().items():
        arm = arms[model]
        kin = kinematics_for(model)
        bounds = soft_bounds(arm.limits, {}, LIMIT_MARGIN_DEG)
        for name, pose in poses.items():
            clipped = {}
            for j, v in pose.items():
                lo, hi = bounds[j]
                past = max(lo - v, v - hi, 0.0)
                expected = PAST_SOFT_LIMIT.get((model, name, j), 0.0)
                assert past == pytest.approx(expected, abs=0.05), (model, name, j, past)
                clipped[j] = min(max(v, lo), hi)
            joints = dict.fromkeys(arm.joint_names, 0.0) | clipped
            frames = getattr(kin, "frames", None)
            lowest = (
                min(p[2] for p, _ in frames(joints).values()) if frames else kin.fk(joints)[0][2]
            )
            assert lowest * 100 >= floor, (model, name, lowest * 100)


def test_unknown_ai_tools_settings_are_ignored_not_fatal(caplog):
    v = Venue("x", (), True, 0.5, ai_tools={"max_move_cm": 5, "teleport": True})
    assert AiLimits.from_venue(v).max_move_cm == 5
    assert "teleport" in caplog.text


# ---------- MCP ----------

READ_TOOLS = {"arm_status", "list_poses", "pose_view", "camera_snapshot", "table_point"}
MOVE_TOOLS = {"move_joints", "gripper", "move_to", "go_to_pose", "pick_at", "run_program"}


async def test_mcp_lists_the_tools_with_their_tiers(rig):
    async with Client(create_mcp_server(rig)) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
    assert set(tools) == READ_TOOLS | MOVE_TOOLS | {"stop"}
    for name in READ_TOOLS:
        assert tools[name].annotations.read_only_hint is True
    for name in MOVE_TOOLS:
        assert tools[name].annotations.destructive_hint is True
    assert tools["stop"].annotations.destructive_hint is False


async def test_mcp_moves_and_refuses_with_a_reason(rig):
    async with Client(create_mcp_server(rig)) as c:
        r = await c.call_tool("move_joints", {"joints": {"shoulder_pan": 12}})
        assert not r.is_error
        assert json.loads(r.content[0].text)["joints_deg"]["shoulder_pan"] == 12
        rig.control["ws"] = object()
        r = await c.call_tool("move_to", {"x_cm": 25, "y_cm": 0, "z_cm": 5})
        assert r.is_error and "Refused: a person has control" in r.content[0].text
        r = await c.call_tool("stop", {})
        assert not r.is_error


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def test_mcp_over_http_on_localhost(rig):
    http = McpHttp(create_mcp_server(rig), _free_port())
    assert http.url.startswith("http://127.0.0.1:")
    task = asyncio.create_task(http.serve())
    try:
        for _ in range(50):
            if http.uvicorn.started:
                break
            await asyncio.sleep(0.05)
        async with Client(http.url) as c:
            r = await c.call_tool("arm_status", {})
            assert json.loads(r.content[0].text)["arm"] == "fake-arm"
    finally:
        await http.shutdown()
        await asyncio.wait_for(task, 5)


# ---------- the arm's USB unplugged (quick job 27) ----------


async def test_an_unplugged_arm_refuses_moves_and_says_so(rig):
    rig.arm.plugged = False
    rig.loop.check_link(0.0, force=True)
    s = await rig.arm_status()
    assert s["connected"] is False and "disconnected" in s["problem"]
    with pytest.raises(Refused, match="disconnected"):
        await rig.move_joints({"shoulder_pan": 5.0})
    assert (await rig.stop())["result"] == "stopped"  # STOP is always allowed
    rig.arm.plugged = True
    rig.loop.check_link(10.0, force=True)
    assert (await rig.arm_status())["connected"] is True


async def test_unplugged_during_a_move(rig):
    rig.limits = replace(rig.limits, deg_per_s=20.0)
    task = asyncio.create_task(rig.move_joints({"shoulder_pan": 20.0}))
    await asyncio.sleep(0.1)
    rig.arm.plugged = False
    r = await task
    assert r["result"] == "disconnected" and "unplugged" in r["problem"]


@pytest.mark.parametrize("table_z_cm", [0.0, -1.6])  # the green arm (on the table), the white one
async def test_ready_to_home_stays_above_the_floor_all_the_way(table_z_cm):
    """Quick job 30: the floor (0.8 cm above the table, both venues) never refuses going home,
    and nothing on the way dips below it."""
    from lab_os.venues import load_venue

    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState(), speed_scale=1.0)
    lab = load_venue("lab")
    v = Venue("test", ("fake-arm",), True, 1.0, ai_tools=FAST | {"min_z_cm": lab.floor_cm})
    tools = RobotTools(loop, v, {"ws": None}, table_z_cm=table_z_cm)
    seen = []
    step = loop.step

    def watch(now, dt):  # the lowest point of the arm on every tick of the move
        step(now, dt)
        seen.append(tools._lowest_z_cm(arm.read_joints()))

    loop.step = watch
    task = asyncio.create_task(loop.run())
    try:
        for _ in range(6):
            r = await tools.call("go_to_pose", name="home")
    finally:
        task.cancel()
    assert r["result"] == "arrived" and r["joints_deg"]["wrist_flex"] == 55.0
    assert min(seen) >= lab.floor_cm
