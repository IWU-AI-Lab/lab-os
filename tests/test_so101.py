"""SO-101 driver tests: no hardware and no LeRobot, the LeRobot robot + bus are faked."""

import json
import stat
from dataclasses import dataclass

import pytest

from lab_os import devices
from lab_os.devices import InUse, load_registry
from lab_os.robots import so101
from lab_os.robots.base import Arm  # noqa: F401  (interface the driver follows)
from lab_os.robots.fake import SO101_JOINTS, so101_limits
from lab_os.robots.so101 import MotionDisabled, SO101Arm, calibrated_limits

PORT = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41532410-if00"


@dataclass
class Cal:
    range_min: int
    range_max: int


def full_calibration():
    # ±1000 steps around the middle ≈ ±88° for every joint; wrist_roll gets the whole turn.
    cal = {j: Cal(1048, 3048) for j in SO101_JOINTS}
    cal["wrist_roll"] = Cal(0, 4095)
    return cal


class FakeBus:
    def __init__(self, positions, calibrated=True):
        self.positions = dict(positions)  # LeRobot units: degrees, gripper 0..100
        self.calibrated = calibrated
        self.connected = False
        self.torque = False
        self.writes = []  # (register, values), in order
        self.fail_reads = 0
        names = list(positions)
        self.health = {
            "Present_Temperature": dict.fromkeys(names, 34),
            "Present_Load": dict.fromkeys(names, 125),  # 12.5 %
            "Present_Voltage": dict.fromkeys(names, 121),  # 12.1 V
        }

    def connect(self):
        self.connected = True

    def read_calibration(self):  # a borrowed arm's motors: what LeLab wrote last (reads only)
        return dict(self.held)

    @property
    def is_calibrated(self):
        return self.calibrated

    def sync_read(self, register, num_retry=0, normalize=True):
        if register in self.health:  # raw servo units, like LeRobot with normalize=False
            assert normalize is False
            return dict(self.health[register])
        assert register == "Present_Position"
        if self.fail_reads:
            self.fail_reads -= 1
            raise ConnectionError("Incorrect status packet!")
        return dict(self.positions)

    def sync_write(self, register, values):
        self.writes.append((register, dict(values), self.torque))

    def disconnect(self, disable_torque=True):
        self.connected = False
        if disable_torque:
            self.torque = False


class FakeRobot:
    def __init__(self, positions, calibration=None, calibrated=True):
        self.bus = FakeBus(positions, calibrated)
        self.calibration = full_calibration() if calibration is None else calibration

    def configure(self):
        self.bus.torque = True  # LeRobot's configure() ends with torque on


START = {
    "shoulder_pan": 5.0,
    "shoulder_lift": -20.0,
    "elbow_flex": 40.0,
    "wrist_flex": 40.0,
    "wrist_roll": 0.0,
    "gripper": 30.0,
}


@pytest.fixture
def no_port_check(monkeypatch):
    monkeypatch.setattr(so101, "guarded_port", lambda name: (None, PORT))


@pytest.fixture
def clock(monkeypatch):
    """time.monotonic() for the driver; tests move it on with clock[0] += dt."""
    t = [10.0]
    monkeypatch.setattr(so101.time, "monotonic", lambda: t[0])
    return t


def arm_with(robot, **kw):
    return SO101Arm(make_robot=lambda name, port, calibration_dir: robot, **kw)


def test_read_only_writes_nothing(no_port_check):
    robot = FakeRobot(START)
    arm = arm_with(robot)
    arm.connect()
    assert arm.read_joints() == START
    with pytest.raises(MotionDisabled):
        arm.move_joints({"gripper": 10.0}, 1.0)
    arm.stop()
    arm.close()
    assert robot.bus.writes == []
    assert not robot.bus.torque


def test_motion_sets_goals_to_here_before_torque_goes_on(no_port_check):
    robot = FakeRobot(START)
    arm = arm_with(robot, allow_motion=True)
    arm.connect()
    register, values, torque = robot.bus.writes[0]
    assert register == "Goal_Position" and values == START
    assert not torque  # written while torque was still off
    assert robot.bus.torque  # then configure() switched it on


def test_moves_are_speed_capped_and_limited(no_port_check, clock):
    robot = FakeRobot(START)
    arm = arm_with(robot, allow_motion=True, max_deg_per_s=100.0)
    arm.connect()
    clock[0] += 0.05
    arm.move_joints({"shoulder_pan": 90.0}, speed_scale=0.5)  # 100°/s × 0.5 × 50 ms = 2.5°
    assert robot.bus.writes[-1][1] == {"shoulder_pan": pytest.approx(7.5)}
    assert arm.read_joints()["shoulder_pan"] == pytest.approx(7.5)  # commanded, no bus read
    clock[0] += 0.05
    arm.move_joints({"gripper": 500.0}, speed_scale=100.0)  # speed_scale is capped at 1
    assert robot.bus.writes[-1][1] == {"gripper": pytest.approx(35.0)}


def test_one_to_one_uses_its_own_speed_not_the_speed_scale(no_port_check, clock):
    robot = FakeRobot(START)
    arm = arm_with(robot, allow_motion=True, max_deg_per_s=100.0)
    arm.connect()
    clock[0] += 0.05
    arm.move_joints({"shoulder_pan": 60.0}, speed_scale=0.05, deg_per_s=180.0)  # 180 × 50 ms = 9°
    assert robot.bus.writes[-1][1] == {"shoulder_pan": pytest.approx(14.0)}
    clock[0] += 0.0  # the same instant: no cap at all must not turn into 0 × inf
    arm.move_joints({"shoulder_pan": 60.0}, speed_scale=0.05, deg_per_s=float("inf"))
    assert robot.bus.writes[-1][1] == {"shoulder_pan": pytest.approx(60.0)}  # straight there


def test_servo_health(no_port_check):
    robot = FakeRobot(START)
    arm = arm_with(robot, allow_motion=True)
    arm.connect()
    h = arm.read_health()
    assert h["elbow_flex"] == {"temp_c": 34.0, "load_pct": 12.5, "volts": 12.1}
    assert set(h) == set(START)


def test_joint_outside_its_limits_never_jumps(no_port_check, clock):
    robot = FakeRobot(START | {"elbow_flex": 95.0})  # past the calibrated ±88°
    arm = arm_with(robot, allow_motion=True, max_deg_per_s=1e6)
    arm.connect()
    clock[0] += 0.1
    arm.move_joints({"elbow_flex": 120.0}, 1.0)
    assert robot.bus.writes[-1][1]["elbow_flex"] == pytest.approx(95.0)  # stays, not further
    clock[0] += 0.1
    arm.move_joints({"elbow_flex": 0.0}, 1.0)
    assert robot.bus.writes[-1][1]["elbow_flex"] == pytest.approx(0.0)  # may come back


def test_stop_holds_where_it_is_and_ignores_moves(no_port_check):
    robot = FakeRobot(START)
    arm = arm_with(robot, allow_motion=True)
    arm.connect()
    robot.bus.positions["shoulder_pan"] = 12.0  # it got there
    arm.stop()
    assert robot.bus.writes[-1][1]["shoulder_pan"] == 12.0
    n = len(robot.bus.writes)
    arm.move_joints({"shoulder_pan": 30.0}, 1.0)
    assert len(robot.bus.writes) == n
    arm.resume()
    arm.move_joints({"shoulder_pan": 13.0}, 1.0)
    assert len(robot.bus.writes) == n + 1


def test_a_failed_read_returns_the_last_reading(no_port_check):
    robot = FakeRobot(START)
    arm = arm_with(robot, min_read_interval_s=0.0)
    arm.connect()
    robot.bus.fail_reads = 1
    assert arm.read_joints() == START


def test_needs_a_calibration_and_refuses_a_different_one(no_port_check):
    with pytest.raises(RuntimeError, match="no calibration"):
        arm_with(FakeRobot(START, calibration={})).connect()
    robot = FakeRobot(START, calibrated=False)
    with pytest.raises(RuntimeError, match="different calibration"):
        arm_with(robot, allow_motion=True).connect()
    assert robot.bus.writes == [] and not robot.bus.connected


def test_close_switches_torque_off_only_when_it_was_on(no_port_check):
    robot = FakeRobot(START)
    arm = arm_with(robot, allow_motion=True)
    arm.connect()
    arm.close()
    assert not robot.bus.torque and not robot.bus.connected


def test_limits_are_the_urdf_narrowed_by_the_calibration():
    limits = calibrated_limits(full_calibration(), so101_limits())
    assert limits["elbow_flex"].high == pytest.approx(87.9, abs=0.1)  # calibration: ±1000 steps
    assert limits["shoulder_pan"].high == pytest.approx(87.9, abs=0.1)
    urdf = so101_limits()
    assert limits["wrist_roll"] == urdf["wrist_roll"]  # whole turn recorded: the URDF decides
    assert limits["gripper"] == urdf["gripper"]


# ---- the green follower: borrowed, calibration read only (step 11) ------------------------------
@dataclass
class MotorCal:  # like LeRobot's MotorCalibration
    id: int
    drive_mode: int
    homing_offset: int
    range_min: int
    range_max: int


def green_file(offset: int) -> dict:
    """A calibration file like LeRobot's for all six motors; `offset` tells setups apart."""
    return {
        j: {
            "id": i + 1,
            "drive_mode": 0,
            "homing_offset": offset + i,
            "range_min": 1048,
            "range_max": 3048,
        }
        for i, j in enumerate(SO101_JOINTS)
    }


SHEEP = green_file(-30)  # the builder's own follower calibration
LELABS = green_file(13)  # LeLab's, up to 43 steps away (GOTCHAS 2026-11-16)


def holding(cal: dict) -> dict:
    """What the motors hold when `cal` was last written into them."""
    return {m: MotorCal(**v) for m, v in cal.items()}


def green_robot(held: dict, loaded: list):
    """A stand-in LeRobot follower for a borrowed arm: loads nothing from its (empty) folder,
    and its motors hold `held`. `loaded` gets (folder, files in it) when it's made."""

    def make(name, port, calibration_dir):
        loaded.append((calibration_dir, sorted(p.name for p in calibration_dir.iterdir())))
        robot = FakeRobot(START, calibration={})
        robot.bus.held = holding(held)
        return robot

    return make


@pytest.fixture
def lerobot_cache(tmp_path, monkeypatch):
    """A LeRobot calibration cache like the training project's, with LeLab's two setups (names
    crossed, as on the lab desktop), made READ ONLY (files and folders): any write would fail."""
    root = tmp_path / "lerobot-calibration"
    robots, leaders = root / "robots" / "so_follower", root / "teleoperators" / "so_leader"
    for folder in (robots, leaders):
        folder.mkdir(parents=True)
    (robots / "sheep.json").write_text(json.dumps(SHEEP))
    (robots / "SO-101_Green_Leader.json").write_text(json.dumps(LELABS))
    (leaders / "shepherd.json").write_text(json.dumps(green_file(500)))
    (leaders / "SO-101_Green_Follower.json").write_text(json.dumps(green_file(900)))
    files = [*robots.iterdir(), *leaders.iterdir()]
    for path in [*files, robots, leaders, robots.parent, leaders.parent, root]:
        path.chmod(stat.S_IRUSR | (stat.S_IXUSR if path.is_dir() else 0))
    monkeypatch.setattr(so101, "lerobot_calibration_root", lambda: root)
    registry = load_registry()
    monkeypatch.setattr(so101, "guarded_port", lambda name: (registry.devices[name], PORT))
    before = {f: (f.read_bytes(), f.stat().st_mtime_ns) for f in files}
    yield root
    assert {f: (f.read_bytes(), f.stat().st_mtime_ns) for f in files} == before  # untouched
    for path in [root, robots.parent, leaders.parent, robots, leaders, *files]:
        path.chmod(0o700)


@pytest.mark.parametrize(
    "held, name", [(SHEEP, "sheep.json"), (LELABS, "SO-101_Green_Leader.json")]
)
def test_green_uses_the_file_its_motors_hold(lerobot_cache, held, name):
    loaded = []
    arm = SO101Arm(name="so101-green", make_robot=green_robot(held, loaded))
    arm.connect()
    assert arm.calibration_source.name == name
    folder, files_then = loaded[0]
    assert files_then == []  # LeRobot was given an empty temporary folder, never the cache
    assert not folder.exists()  # and it's gone once connected
    robot = arm._robot
    assert robot.bus.writes == []  # nothing written to the motors
    assert robot.calibration["elbow_flex"].homing_offset == held["elbow_flex"]["homing_offset"]
    assert robot.bus.calibration is robot.calibration
    assert arm.limits["shoulder_pan"].high == pytest.approx(87.9, abs=0.1)
    arm.close()


def test_after_lelab_switches_setups_the_next_connect_follows(lerobot_cache):
    names = []
    for held in (SHEEP, LELABS, SHEEP):  # LeLab's teleop wrote the other setup in between
        arm = SO101Arm(name="so101-green", make_robot=green_robot(held, []))
        arm.connect()
        names.append(arm.calibration_source.name)
        arm.close()
    assert names == ["sheep.json", "SO-101_Green_Leader.json", "sheep.json"]


def test_green_holding_no_known_calibration_is_refused_and_not_fixed(lerobot_cache):
    robots = []

    def make(name, port, folder):
        robots.append(green_robot(green_file(7), [])(name, port, folder))
        return robots[-1]

    arm = SO101Arm(name="so101-green", make_robot=make, allow_motion=True)
    with pytest.raises(RuntimeError, match="matches none of the files.*never writes"):
        arm.connect()
    assert robots[0].bus.writes == [] and not robots[0].bus.connected
    assert arm._robot is None


def test_the_leader_finds_its_file_among_the_leader_files(lerobot_cache):
    arm = SO101Arm(name="so101-green-leader", make_robot=green_robot(green_file(500), []))
    arm.connect()
    assert arm.calibration_source.name == "shepherd.json"
    assert arm.calibration_source.parent.parent.name == "teleoperators"
    arm.close()


def test_matching_needs_every_motor_offset_and_range(tmp_path):
    held = holding(SHEEP)
    good, off_by_one, missing, broken = (tmp_path / f"{n}.json" for n in "abcd")
    good.write_text(json.dumps(SHEEP))
    nudged = json.loads(json.dumps(SHEEP))
    nudged["wrist_roll"]["range_max"] += 1
    off_by_one.write_text(json.dumps(nudged))
    missing.write_text(json.dumps({k: v for k, v in SHEEP.items() if k != "gripper"}))
    broken.write_text("{not json")
    files = [good, off_by_one, missing, broken]
    assert so101.matching_calibration(held, files) == [good]


def test_the_follower_looks_in_robots_first_then_teleoperators(tmp_path):
    for f in ("robots/a/x.json", "teleoperators/b/y.json"):
        (tmp_path / f).parent.mkdir(parents=True)
        (tmp_path / f).write_text("{}")
    registry = load_registry()
    follower = so101.lerobot_calibration_files(registry.devices["so101-green"], tmp_path)
    leader = so101.lerobot_calibration_files(registry.devices["so101-green-leader"], tmp_path)
    assert [f.name for f in follower] == ["x.json", "y.json"]
    assert [f.name for f in leader] == ["y.json", "x.json"]


def test_white_still_uses_lab_os_calibration_folder(no_port_check):
    seen = []
    SO101Arm(make_robot=lambda n, p, d: seen.append(d) or FakeRobot(START)).connect()
    assert seen == [so101.CALIBRATION_DIR / "so101-white"]


def test_a_port_in_use_is_refused_before_lerobot_is_touched(monkeypatch):
    def must_not_run(*a):
        raise AssertionError("the port must not open")

    monkeypatch.setattr("lab_os.robots.so101_setup.os.path.exists", lambda p: True)
    monkeypatch.setattr("lab_os.robots.so101_setup.usb_serial_of", lambda p, root=None: None)
    monkeypatch.setattr(devices, "users_of", lambda path, proc=None: ["lelab (pid 42)"])
    with pytest.raises(InUse, match="so101-green is in use by lelab \\(pid 42\\)"):
        SO101Arm(name="so101-green", make_robot=must_not_run).connect()


def test_watch_only_reads(no_port_check, monkeypatch, capsys):
    robot = FakeRobot(START)
    arm = arm_with(robot)
    arm.connect()
    ticks = iter([None, KeyboardInterrupt])

    def sleep(_):
        if (t := next(ticks)) is not None:
            raise t

    monkeypatch.setattr(so101.time, "sleep", sleep)
    so101.watch(arm)
    assert robot.bus.writes == []
    assert "+40.0" in capsys.readouterr().out  # elbow_flex
