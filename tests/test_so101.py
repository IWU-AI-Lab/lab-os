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
GREEN_CAL = {"shoulder_pan": {"id": 1, "range_min": 1048, "range_max": 3048}}


@pytest.fixture
def lerobot_cache(tmp_path, monkeypatch):
    """A LeRobot calibration cache like the training project's, made READ ONLY (files and
    folders), so any write into it would fail."""
    root = tmp_path / "lerobot-calibration"
    folder = root / "robots" / "so101_follower"
    folder.mkdir(parents=True)
    source = folder / "green_follower.json"
    source.write_text(json.dumps(GREEN_CAL))
    (root / "teleoperators" / "so101_leader").mkdir(parents=True)
    (root / "teleoperators" / "so101_leader" / "green_leader.json").write_text("{}")
    for path in (source, folder, folder.parent, root):
        path.chmod(stat.S_IRUSR | (stat.S_IXUSR if path.is_dir() else 0))
    monkeypatch.setattr(so101, "lerobot_calibration_root", lambda: root)
    green = load_registry().devices["so101-green"]
    monkeypatch.setattr(so101, "guarded_port", lambda name: (green, PORT))
    yield source
    for path in (root, folder.parent, folder, source):
        path.chmod(0o700)


def test_green_reads_lerobots_calibration_through_a_copy(lerobot_cache):
    before = (lerobot_cache.read_bytes(), lerobot_cache.stat().st_mtime_ns)
    seen = {}

    def make_robot(name, port, calibration_dir):
        copy = calibration_dir / f"{name}.json"
        seen["dir"], seen["data"] = calibration_dir, json.loads(copy.read_text())
        copy.write_text("{}")  # LeRobot saving its calibration would land in the copy only
        return FakeRobot(START)

    arm = SO101Arm(name="so101-green", make_robot=make_robot)
    arm.connect()
    assert seen["data"] == GREEN_CAL  # the training project's file, as is
    assert seen["dir"] != lerobot_cache.parent  # LeRobot never learns the real folder
    assert not seen["dir"].exists()  # the copy is gone once the robot has loaded it
    assert (lerobot_cache.read_bytes(), lerobot_cache.stat().st_mtime_ns) == before
    assert arm.limits["shoulder_pan"].high == pytest.approx(87.9, abs=0.1)
    arm.close()


def test_green_with_a_different_calibration_in_its_motors_is_not_fixed_by_lab_os(lerobot_cache):
    robot = FakeRobot(START, calibrated=False)
    arm = SO101Arm(name="so101-green", make_robot=lambda n, p, d: robot, allow_motion=True)
    with pytest.raises(RuntimeError, match="never writes a borrowed arm's calibration"):
        arm.connect()
    assert robot.bus.writes == [] and not robot.bus.connected


def test_the_calibration_file_must_be_unambiguous(tmp_path):
    green = load_registry().devices["so101-green"]
    folder = tmp_path / "robots" / "so101_follower"
    folder.mkdir(parents=True)
    with pytest.raises(LookupError, match="found: none"):
        so101.lerobot_calibration_file(green, tmp_path)
    (folder / "a.json").write_text("{}")
    (folder / "b.json").write_text("{}")
    with pytest.raises(LookupError, match="Set calibration_id"):
        so101.lerobot_calibration_file(green, tmp_path)
    picked = devices.Device(**{**green.__dict__, "calibration_id": "b"})
    assert so101.lerobot_calibration_file(picked, tmp_path) == folder / "b.json"
    leader = load_registry().devices["so101-green-leader"]
    (tmp_path / "teleoperators" / "x").mkdir(parents=True)
    (tmp_path / "teleoperators" / "x" / "l.json").write_text("{}")
    assert so101.lerobot_calibration_file(leader, tmp_path).parent.parent.name == "teleoperators"


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
