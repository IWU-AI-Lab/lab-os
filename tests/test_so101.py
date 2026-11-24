"""SO-101 driver tests: no hardware and no LeRobot, the LeRobot robot + bus are faked."""

import json
import math
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


# ---- the green arms: borrowed, driven with a copy of the training calibration (2026-11-17) ----
def green_file(offset: int) -> dict:
    """A calibration file like LeRobot's for all six motors; `offset` tells files apart."""
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


SHEEP = green_file(-30)  # the training follower calibration
SHEPHERD = green_file(500)  # the training leader calibration


@pytest.fixture
def training(tmp_path, monkeypatch):
    """LeRobot's cache with the two training files, READ ONLY (files and folders), and lab-os's
    calibration folder with equal copies. Yields lab-os's folder; checks the cache is untouched."""
    root = tmp_path / "lerobot-calibration"
    files = [root / "robots/so_follower/sheep.json", root / "teleoperators/so_leader/shepherd.json"]
    ours = tmp_path / "calibration"
    for f, cal, name in zip(
        files, (SHEEP, SHEPHERD), ("so101-green", "so101-green-leader"), strict=True
    ):
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps(cal))
        (ours / name).mkdir(parents=True)
        (ours / name / f"{name}.json").write_text(json.dumps(cal, indent=4))
    dirs = [f.parent for f in files] + [f.parent.parent for f in files] + [root]
    for path in [*files, *dirs]:
        path.chmod(stat.S_IRUSR | (stat.S_IXUSR if path.is_dir() else 0))
    monkeypatch.setattr(so101, "lerobot_calibration_root", lambda: root)
    monkeypatch.setattr(so101, "CALIBRATION_DIR", ours)
    registry = load_registry()
    monkeypatch.setattr(so101, "guarded_port", lambda name: (registry.devices[name], PORT))
    before = {f: (f.read_bytes(), f.stat().st_mtime_ns) for f in files}
    yield ours
    assert {f: (f.read_bytes(), f.stat().st_mtime_ns) for f in files} == before  # untouched
    for path in [*reversed(dirs), *files]:
        path.chmod(0o700)


def green_robot(made: list, calibrated: bool = True):
    """A stand-in LeRobot follower; `made` gets (folder, robot) when it's made."""

    def make(name, port, calibration_dir):
        robot = FakeRobot(START, calibrated=calibrated)
        made.append((calibration_dir, robot))
        return robot

    return make


@pytest.mark.parametrize(
    "name, source", [("so101-green", "sheep.json"), ("so101-green-leader", "shepherd.json")]
)
def test_green_drives_with_its_copy_of_the_training_calibration(training, name, source):
    made = []
    arm = SO101Arm(name=name, make_robot=green_robot(made))
    arm.connect()
    folder, robot = made[0]
    assert folder == training / name  # lab-os's copy, never LeRobot's folder
    assert arm.calibration_source.name == source
    assert robot.bus.writes == []  # nothing written to the motors
    arm.close()


def test_a_copy_that_differs_from_the_training_file_is_refused(training):
    (training / "so101-green/so101-green.json").write_text(json.dumps(green_file(13)))
    made = []
    with pytest.raises(RuntimeError, match="differs from lab-os's copy.*copy it again: cp "):
        SO101Arm(name="so101-green", make_robot=green_robot(made)).connect()
    assert made == []  # refused before the port is opened


def test_no_copy_is_refused_with_the_command_to_make_it(training):
    (training / "so101-green/so101-green.json").unlink()
    with pytest.raises(RuntimeError, match="no copy of its training calibration.*cp "):
        SO101Arm(name="so101-green", make_robot=green_robot([])).connect()


def test_motors_not_holding_the_training_calibration_are_refused_and_not_fixed(training):
    made = []
    arm = SO101Arm(
        name="so101-green", make_robot=green_robot(made, calibrated=False), allow_motion=True
    )
    with pytest.raises(RuntimeError, match="don't hold its training calibration.*never 'c'"):
        arm.connect()
    robot = made[0][1]
    assert robot.bus.writes == [] and not robot.bus.connected
    assert arm._robot is None


def test_without_the_training_file_here_the_copy_is_used(training, monkeypatch, tmp_path):
    monkeypatch.setattr(so101, "lerobot_calibration_root", lambda: tmp_path / "nowhere")
    made = []
    SO101Arm(name="so101-green", make_robot=green_robot(made)).connect()
    assert made[0][0] == training / "so101-green"


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


def test_unplugged_then_back_reconnects_from_where_the_motors_are(monkeypatch, tmp_path, clock):
    port = tmp_path / "usb-1a86_USB_Single_Serial_5B41532410-if00"
    port.touch()
    monkeypatch.setattr(so101, "guarded_port", lambda name: (None, str(port)))
    first, second = FakeRobot(START), FakeRobot(START | {"shoulder_pan": 30.0})
    robots = [first, second]
    arm = SO101Arm(make_robot=lambda name, p, d: robots.pop(0), allow_motion=True)
    arm.connect()
    assert arm.port_present()
    clock[0] += 0.05
    arm.move_joints({"shoulder_pan": 10.0}, 1.0)
    port.unlink()  # unplugged: the by-id name goes
    assert not arm.port_present()
    n = len(first.bus.writes)
    arm.drop()
    assert len(first.bus.writes) == n and not first.bus.connected  # closed, nothing written
    port.touch()  # plugged back in (moved by hand meanwhile: pan 30)
    arm.connect()
    register, values, torque = second.bus.writes[0]
    assert register == "Goal_Position" and values["shoulder_pan"] == 30.0 and not torque
    assert second.bus.torque
    assert arm.commanded_joints()["shoulder_pan"] == 30.0  # not the old goal of 10


class Port:
    """LeRobot's port handler: the bus opens it before the motor check."""

    def __init__(self):
        self.open = True

    def closePort(self):  # noqa: N802 (LeRobot's name)
        self.open = False


def test_motors_that_do_not_answer_give_a_sentence_and_free_the_port(no_port_check, caplog):
    """Quick job 94 (lab check N.17): the USB board is there, the motors' power is off. LeRobot's
    motor check raises RuntimeError after it opened the port; the driver closes it and says one
    sentence. LeRobot's own words go to the brain's log."""
    robot = FakeRobot(START)
    robot.bus.port_handler = Port()

    def no_motors():
        raise RuntimeError("FeetechMotorsBus motor check failed. Missing motor IDs: 1-6")

    robot.bus.connect = no_motors
    arm = arm_with(robot, allow_motion=True)
    with pytest.raises(so101.MotorsNotAnswering, match="Is the arm's power on"):
        arm.connect()
    assert not robot.bus.port_handler.open
    assert "Missing motor IDs" in caplog.text


def test_a_motor_that_does_not_answer_a_write_gives_the_same_sentence(no_port_check):
    """The second try in N.17: motor 2 didn't answer the torque write (a ConnectionError)."""
    robot = FakeRobot(START)

    def no_status():
        raise ConnectionError(
            "Failed to write 'Torque_Enable' on id_=2: There is no status packet!"
        )

    robot.configure = no_status
    arm = arm_with(robot, allow_motion=True)
    with pytest.raises(so101.MotorsNotAnswering):
        arm.connect()
    assert not robot.bus.connected


def test_a_joint_offset_moves_the_reading_the_goal_and_the_limits(monkeypatch):
    """Quick job 106: so101-white's shoulder_lift reads 4.7° too far forward. The driver adds
    the offset to the reading, takes it off the goal, and moves the joint's range with it."""
    robot = FakeRobot(dict.fromkeys(SO101_JOINTS, 10.0))
    monkeypatch.setattr(
        so101, "guarded_port", lambda name: (devices.Device(name, "so101", **OFFSET), PORT)
    )
    arm = SO101Arm(name="so101-white", allow_motion=True, make_robot=lambda *_: robot)
    arm.connect()
    assert arm.read_measured()["shoulder_lift"] == pytest.approx(5.3)
    assert arm.read_measured()["elbow_flex"] == 10.0
    first = robot.bus.writes[0][1]  # goals = where the motors are: unchanged in motor units
    assert first["shoulder_lift"] == pytest.approx(10.0)
    arm.move_joints({"shoulder_lift": 6.3}, speed_scale=1.0, deg_per_s=math.inf)
    assert robot.bus.writes[-1][1]["shoulder_lift"] == pytest.approx(11.0)
    lim = arm.limits["shoulder_lift"]
    plain = calibrated_limits(full_calibration(), so101_limits())["shoulder_lift"]
    assert lim.low == pytest.approx(max(plain.low - 4.7, so101_limits()["shoulder_lift"].low))
    assert lim.high == pytest.approx(plain.high - 4.7)


OFFSET = {"joint_offsets_deg": (("shoulder_lift", -4.7),)}


def test_so101_white_has_its_measured_shoulder_offset():
    """Quick job 106: the offset is in devices.yaml for the white arm only, and with it the
    model puts the jaw tips at the measured distance (A1, 2026-11-24: 29-30 cm from the base's
    turning axis by ruler, on the table)."""
    from lab_os.kinematics import on_table, so101_kinematics

    reg = load_registry()
    white = dict(reg.devices["so101-white"].joint_offsets_deg)
    assert white == {"shoulder_lift": -4.7}
    assert not reg.devices["so101-green"].joint_offsets_deg
    a1 = {  # read with the motors off, the jaw tips on the table at cell A1
        "shoulder_pan": -17.67,
        "shoulder_lift": 61.01 + white["shoulder_lift"],
        "elbow_flex": -49.19,
        "wrist_flex": 75.78,
        "wrist_roll": 94.2,
    }
    kin = on_table(so101_kinematics(), reg.devices["so101-white"].table_z_cm)
    (x, y, z), _ = kin.fk(a1)
    axis = kin.frames(a1)["shoulder_pan"][0]
    assert 29.0 < math.hypot(x - axis[0], y - axis[1]) * 100 < 30.0
    assert 0.0 < z * 100 < 1.0  # the gripper point: 0.6 cm above the tips on the table
