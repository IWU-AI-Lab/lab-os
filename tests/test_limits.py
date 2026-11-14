"""Safety limits that can be switched off (quick job 2): the per-move limit, the speed cap and the
floor, each on by default, off in the venue file or from Settings; never off on a public venue or
the visit-day venue (`limits_locked`). On the fake arm; no hardware."""

import argparse
import asyncio
import math

import pytest

from lab_os import REPO_ROOT, config, settings
from lab_os.robots.fake import FakeArm
from lab_os.teleop.cli import make_loop
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.tools.robot import AiLimits, Refused, RobotTools
from lab_os.venues import load_venue

FAST = "  deg_per_s: 900   # tests don't wait for real-time motion\n"


@pytest.fixture
def home(tmp_path):
    folder = config.new_place(tmp_path / "home")
    config.use(folder)
    return folder


def write_venue(home, limits: str = "", extra: str = "", name: str = "home") -> None:
    (home / "venues" / f"{name}.yaml").write_text(
        f"name: {name}\nactive_devices: [fake-arm]\nmotion_allowed: true\nmax_speed_scale: 0.3\n"
        f"one_to_one_max_deg_per_s: 180\nai_tools:\n  min_z_cm: 1\n{FAST}{extra}"
        + (f"limits:\n{limits}" if limits else "")
    )


async def tools_for(venue):
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState(), speed_scale=1.0)
    task = asyncio.create_task(loop.run())
    return RobotTools(loop, venue, {"ws": None}), task


def tip(tools):
    return tools._where()["gripper_point_cm"]


def loop_args(**kw):
    return argparse.Namespace(
        **({"arm": "fake", "venue": "home", "speed": None, "quiet": True} | kw)
    )


# ---------- the venue file ----------


def test_all_on_by_default(home):
    write_venue(home)
    v = load_venue("home")
    assert v.limits_off == [] and not v.limits_fixed
    assert v.speed_cap_scale == 0.3 and v.one_to_one_cap == 180 and v.floor_cm == 1
    for name in ("lab", "visit-day"):  # the repo's venues: all on
        assert load_venue(name, REPO_ROOT / "config").limits_off == []


def test_each_can_be_switched_off(home):
    write_venue(home, "  per_move: off\n  speed_cap: off\n  floor: off\n")
    v = load_venue("home")
    assert v.limits_off == ["per_move", "speed_cap", "floor"]
    assert v.speed_cap_scale == 1.0 and v.one_to_one_cap == math.inf
    assert v.floor_cm == -math.inf
    assert v.max_speed_scale == 0.3  # still where it starts


def test_speed_cap_off_leaves_1to1_off_where_it_is_off(home):
    write_venue(home, "  speed_cap: off\n")
    (home / "venues" / "home.yaml").write_text(
        (home / "venues" / "home.yaml")
        .read_text()
        .replace("one_to_one_max_deg_per_s: 180", "one_to_one_max_deg_per_s: off")
    )
    assert load_venue("home").one_to_one_cap == 0.0  # 1:1 switched off is a mode, not a limit


def test_the_visit_day_venue_and_public_venues_refuse(home):
    write_venue(home, "  floor: off\n", "limits_locked: true\n")
    with pytest.raises(config.ConfigError, match="can't be switched off here.*limits.floor"):
        load_venue("home")
    write_venue(home, "  speed_cap: off\n", "public: true\n")
    with pytest.raises(config.ConfigError, match="limits.speed_cap is off"):
        load_venue("home")
    assert load_venue("visit-day", REPO_ROOT / "config").limits_fixed


def test_unknown_limit_is_an_error(home):
    write_venue(home, "  joints: off\n")
    with pytest.raises(config.ConfigError, match="unknown limit joints"):
        load_venue("home")


# ---------- teleop ----------


def test_teleop_gets_the_cap_and_floor(home):
    write_venue(home)
    loop = make_loop(loop_args())
    assert loop.max_speed_scale == 0.3 and loop.speed_scale == 0.3
    assert loop.one_to_one_deg_per_s == 180 and loop.mapper.config.floor_m == 0.01
    assert loop.set_speed(0.9) == 0.3


def test_teleop_with_the_cap_and_floor_off(home):
    write_venue(home, "  speed_cap: off\n  floor: off\n")
    loop = make_loop(loop_args())
    assert loop.speed_scale == 0.3  # starts at the venue's speed...
    assert loop.set_speed(0.9) == 0.9  # ...but may go up to full speed
    assert loop.one_to_one_deg_per_s == math.inf
    assert loop.mapper.config.floor_m == -math.inf
    assert make_loop(loop_args(speed=0.8)).speed_scale == 0.8


# ---------- the AI tools ----------


async def test_ai_per_move_limit_on_and_off(home):
    write_venue(home)
    assert AiLimits.from_venue(load_venue("home")).max_move_cm == 10
    write_venue(home, "  per_move: off\n")
    tools, task = await tools_for(load_venue("home"))
    try:
        assert (await tools.arm_status())["per_call"]["max_move_cm"] == "off"
        start = tip(tools)
        r = await tools.call("move_to", x_cm=start["x"], y_cm=start["y"] + 20, z_cm=start["z"])
        assert math.dist(start.values(), r["gripper_point_cm"].values()) > 19
        assert r["clipped"] == []
        j0 = tools.arm.read_joints()["shoulder_pan"]
        r = await tools.call("move_joints", joints={"shoulder_pan": 50}, relative=True)
        assert math.isclose(tools.arm.read_joints()["shoulder_pan"] - j0, 50, abs_tol=1e-6)
    finally:
        task.cancel()


async def test_ai_floor_on_and_off(home):
    write_venue(home)
    tools, task = await tools_for(load_venue("home"))
    try:
        with pytest.raises(Refused, match="below the 1 cm floor"):
            await tools.call("move_to", x_cm=25, y_cm=0, z_cm=0.5)
    finally:
        task.cancel()
    write_venue(home, "  floor: off\n")
    tools, task = await tools_for(load_venue("home"))
    try:
        assert (await tools.arm_status())["per_call"]["min_z_cm"] == "off"
        r = await tools.call("move_to", x_cm=25, y_cm=0, z_cm=0.5)
        assert r["gripper_point_cm"]["z"] < 1
    finally:
        task.cancel()


# ---------- the Settings page ----------


def limit_fields():
    return {f["key"]: f for s in settings.read("home") for f in s["fields"] if f["safety"]}


def test_settings_switch_each_off_and_on(home):
    write_venue(home)
    fields = limit_fields()
    assert set(fields) == {"venue:limits.per_move", "venue:limits.speed_cap", "venue:limits.floor"}
    assert all(f["value"] is True and f["locked"] == "" for f in fields.values())
    for key in fields:
        settings.write(key, False, "home")
    assert load_venue("home").limits_off == ["per_move", "speed_cap", "floor"]
    assert not any(f["value"] for f in limit_fields().values())
    settings.write("venue:limits.floor", True, "home")
    assert load_venue("home").limits_off == ["per_move", "speed_cap"]


def test_settings_refuse_on_the_visit_day_venue(home):
    write_venue(home, extra="limits_locked: true\n")
    assert all("visit days" in f["locked"] for f in limit_fields().values())
    with pytest.raises(settings.SettingError, match="can't be switched off here"):
        settings.write("venue:limits.floor", False, "home")
    assert settings.write("venue:limits.floor", True, "home") is True  # on is always fine
    assert load_venue("home").limits_off == []
    write_venue(home, extra="public: true\n")
    with pytest.raises(settings.SettingError, match="public venue"):
        settings.write("venue:limits.speed_cap", False, "home")


def test_the_page_marks_a_limit_thats_off():
    js = (REPO_ROOT / "src" / "lab_os" / "hub" / "web" / "settings.js").read_text()
    html = (REPO_ROOT / "src" / "lab_os" / "hub" / "web" / "settings.html").read_text()
    assert "limit-off" in js and 'id="limits-off"' in html and ".field.limit-off" in html


def test_the_floor_is_minus_half_a_cm_in_both_venues(monkeypatch):
    """Quick job 3 (decision 2026-11-13): the arm stands on the camera's base, so the table is
    below its zero; the AI tools and teleop use the same number."""
    monkeypatch.setattr(config, "active_dir", lambda: REPO_ROOT / "config")
    for name in ("lab", "visit-day"):
        v = load_venue(name, REPO_ROOT / "config")
        assert v.floor_cm == -0.5 and AiLimits.from_venue(v).min_z_cm == -0.5
    loop = make_loop(loop_args(venue="lab"))
    assert loop.mapper.config.floor_m == pytest.approx(-0.005)
