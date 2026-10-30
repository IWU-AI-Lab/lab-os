"""SO-101 motor setup / calibration command, against a fake motor bus (no hardware, no LeRobot)."""

import pytest

from lab_os.devices import PortNotAllowed, load_registry
from lab_os.robots import so101_setup as setup
from lab_os.robots.so101_setup import MOTORS

WHITE = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41532410-if00"
GREEN = "usb-1a86_USB_Single_Serial_5B41531599-if00"
FRESH = (1_000_000, 1)  # a new STS3215: ID 1 at 1 Mbaud


class FakeBus:
    """Just what the setup code uses of LeRobot's FeetechMotorsBus. `on_bus` = (baud, id) of
    every motor currently plugged in."""

    available_baudrates = [115_200, 500_000, 1_000_000]
    default_baudrate = 1_000_000
    model_number_table = {"sts3215": 777}

    def __init__(self, on_bus=(), model=777):
        self.on_bus = list(on_bus)
        self.model = model
        self.baud = self.default_baudrate
        self.setup_calls = []

    def set_baudrate(self, baud):
        self.baud = baud

    def broadcast_ping(self):
        return {i: self.model for b, i in self.on_bus if b == self.baud} or None

    def ping(self, motor_id):
        return self.model if (self.baud, motor_id) in self.on_bus else None

    def setup_motor(self, joint, initial_baudrate, initial_id):
        self.setup_calls.append((joint, initial_baudrate, initial_id))
        self.on_bus.remove((initial_baudrate, initial_id))
        self.on_bus.append((self.default_baudrate, MOTORS[joint]))
        self.baud = self.default_baudrate


def quiet(*_):
    pass


def answers(*replies, before=None):
    """An `ask` that returns the replies in order; `before(prompt)` runs first (plug a motor)."""
    it = iter(replies)

    def ask(prompt):
        if before:
            before(prompt)
        return next(it)

    return ask


# ---- port guard ---------------------------------------------------------------------------------
def test_green_is_refused_before_anything_opens():
    with pytest.raises(PortNotAllowed):
        setup.guarded_port("so101-green")


def test_a_non_so101_device_is_refused():
    with pytest.raises(PortNotAllowed):
        setup.guarded_port("xarm1")


def fake_sysfs(tmp_path, port, serial):
    """/sys/class/tty/<tty>/device -> a USB interface whose parent has `serial`."""
    usb = tmp_path / "devices" / "1-5"
    (usb / "1-5:1.0").mkdir(parents=True)
    (usb / "serial").write_text(serial + "\n")
    # Named like the code will look it up: ttyACM0 while the real board is plugged in.
    tty = tmp_path / "class" / "tty" / setup.os.path.basename(setup.os.path.realpath(port))
    tty.mkdir(parents=True)
    (tty / "device").symlink_to(usb / "1-5:1.0")
    return tmp_path


def test_board_serial_matches_white(tmp_path):
    reg = load_registry()
    sys_root = fake_sysfs(tmp_path, WHITE, "5B41532410")
    assert setup.usb_serial_of(WHITE, sys_root) == "5B41532410"
    setup.check_board_serial(WHITE, reg.devices["so101-white"], reg, sys_root)


@pytest.mark.parametrize("serial", ["5B41531599", "5B41533501", "SOMETHING-ELSE"])
def test_board_with_another_serial_is_refused(tmp_path, serial):
    reg = load_registry()
    sys_root = fake_sysfs(tmp_path, WHITE, serial)
    with pytest.raises(PortNotAllowed):
        setup.check_board_serial(WHITE, reg.devices["so101-white"], reg, sys_root)


def test_unknown_sysfs_skips_the_second_check(tmp_path):
    reg = load_registry()
    assert setup.usb_serial_of(WHITE, tmp_path) is None
    setup.check_board_serial(WHITE, reg.devices["so101-white"], reg, tmp_path)


def test_port_list_labels_green_as_off_limits(tmp_path):
    for name in (GREEN, WHITE.rsplit("/", 1)[-1], "usb-other_thing-if00"):
        (tmp_path / name).touch()
    lines = setup.describe_serial_ports(load_registry(), str(tmp_path) + "/")
    assert any("so101-green" in line and "OFF LIMITS" in line for line in lines)
    assert any(line.endswith("->  so101-white") for line in lines)
    assert any(line.endswith("->  unknown") for line in lines)


@pytest.mark.parametrize("reply", ["", "y", "no", "YES please"])
def test_anything_but_yes_opens_nothing(monkeypatch, reply):
    reg = load_registry()
    monkeypatch.setattr(setup, "guarded_port", lambda name, registry: (reg.devices[name], WHITE))
    monkeypatch.setattr(setup, "_require_lerobot", lambda: None)

    def no_bus(port):
        raise AssertionError("the port must not open")

    monkeypatch.setattr(setup, "make_bus", no_bus)
    monkeypatch.setattr(setup, "calibrate", no_bus)
    for command in ("setup-motors", "check", "calibrate"):
        assert setup.main([command], ask=answers(reply), say=quiet) == 1


def test_a_missing_board_is_reported_not_opened(monkeypatch):
    said = []
    monkeypatch.setattr(setup.os.path, "exists", lambda p: False)
    assert setup.main(["setup-motors"], ask=answers(), say=said.append) == 1
    assert "isn't there" in said[0]


# ---- motor setup walkthrough ------------------------------------------------------------------
def test_walks_each_motor_gripper_first():
    bus = FakeBus()

    def plug_a_fresh_motor(prompt):
        bus.on_bus = [FRESH]

    results = setup.setup_motors(bus, ask=answers(*[""] * 6, before=plug_a_fresh_motor), say=quiet)
    assert [c[0] for c in bus.setup_calls] == list(reversed(MOTORS))
    assert all(c[1:] == FRESH for c in bus.setup_calls)
    assert set(results) == set(MOTORS)
    assert results["gripper"].endswith("ID 6 @ 1000000 baud")


def test_two_motors_on_the_bus_are_refused_then_retried():
    bus = FakeBus(on_bus=[FRESH, (1_000_000, 2)])
    said = []

    def unplug_one_after_the_error(prompt):
        if said and "more than one" in said[-1]:
            bus.on_bus = [FRESH]

    ask = answers("", "", "q", before=unplug_one_after_the_error)
    setup.setup_motors(bus, ask=ask, say=said.append)
    assert bus.setup_calls == [("gripper", *FRESH)]  # only after the second motor was unplugged


def test_no_motor_wrong_model_skip_and_quit():
    said = []
    bus = FakeBus()
    results = setup.setup_motors(bus, ask=answers("", "s", "q"), say=said.append)
    assert any("no motor answers" in s for s in said)
    assert results == {"gripper": "skipped"}
    assert bus.setup_calls == []

    bus = FakeBus(on_bus=[FRESH], model=1234)
    said.clear()
    setup.setup_motors(bus, ask=answers("", "q"), say=said.append)
    assert any("model number 1234" in s for s in said)
    assert bus.setup_calls == []


def test_motor_at_another_baud_rate_is_found():
    bus = FakeBus(on_bus=[(115_200, 7)])
    assert setup.setup_one(bus, "wrist_roll").startswith("ID 7 @ 115200 baud")
    assert bus.on_bus == [(1_000_000, 5)]


def test_leader_walkthrough_names_the_gear_ratios():
    said = []
    setup.setup_motors(FakeBus(), role="leader", ask=answers("q"), say=said.append)
    assert any("gripper" in s and "1/147" in s for s in said)


# ---- check --------------------------------------------------------------------------------------
def test_check_passes_with_all_six_ids():
    bus = FakeBus(on_bus=[(1_000_000, i) for i in MOTORS.values()])
    assert setup.check_motors(bus, say=quiet)


def test_check_fails_on_a_missing_or_unset_motor():
    bus = FakeBus(on_bus=[(1_000_000, i) for i in (1, 2, 3, 4, 5)] + [(115_200, 1)])
    said = []
    assert not setup.check_motors(bus, say=said.append)
    assert any("✗ gripper" in s for s in said)
    assert any("115200" in s for s in said)


# ---- calibration (needs LeRobot: skipped where the extra isn't installed, e.g. CI) -------------
def test_calibration_uses_our_folder_and_id():
    pytest.importorskip("lerobot")
    reg = load_registry()
    for name in ("so101-white", "so101-white-leader"):
        _, config = setup.arm_class_and_config(reg.devices[name], WHITE)
        assert config.id == name
        assert config.calibration_dir == setup.CALIBRATION_DIR / name
        assert "huggingface" not in str(config.calibration_dir)
