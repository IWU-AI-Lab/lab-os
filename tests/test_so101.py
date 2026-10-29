"""SO-101 driver tests: no hardware and no LeRobot, the LeRobot robot + bus are faked."""

from dataclasses import dataclass

import pytest

from lab_os.devices import PortNotAllowed
from lab_os.robots import so101
from lab_os.robots.base import Arm  # noqa: F401  (interface the driver follows)
from lab_os.robots.fake import SO101_JOINTS, so101_limits
from lab_os.robots.so101 import MotionDisabled, SO101Arm, calibrated_limits

PORT = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41532183-if00"


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

    def connect(self):
        self.connected = True

    @property
    def is_calibrated(self):
        return self.calibrated

    def sync_read(self, register, num_retry=0):
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
    return SO101Arm(make_robot=lambda name, port: robot, **kw)


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


def test_green_is_refused_before_lerobot_is_touched():
    def must_not_run(name, port):
        raise AssertionError("no robot object for green")

    with pytest.raises(PortNotAllowed):
        SO101Arm(name="so101-green", make_robot=must_not_run).connect()
