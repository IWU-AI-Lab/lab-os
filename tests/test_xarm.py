"""xArm driver and USB lookup tests: no hardware, the HID device is faked."""

import pytest

from lab_os.devices import PortNotAllowed, find_usb_device, load_registry
from lab_os.robots import xarm
from lab_os.robots.base import Arm  # noqa: F401  (interface the driver follows)
from lab_os.robots.xarm import MotionDisabled, XArm

XARM_SERIAL = "720710C0D60063300023D4D4"


def xarm_info(**over):
    info = {
        "path": b"/dev/hidraw4",
        "vendor_id": 0x0483,
        "product_id": 0x5750,
        "serial_number": XARM_SERIAL,
        "product_string": "xArm",
    }
    return info | over


def test_xarm1_is_in_the_registry():
    spec = load_registry().devices["xarm1"].usb[0]
    assert (spec.vendor_id, spec.product_id) == (0x0483, 0x5750)
    assert (spec.product, spec.serial) == ("xArm", XARM_SERIAL)


def test_find_picks_the_matching_serial():
    other = xarm_info(serial_number="OTHER", path=b"/dev/hidraw9")
    found = find_usb_device("xarm1", enumerate_fn=lambda v, p: [other, xarm_info()])
    assert found["path"] == b"/dev/hidraw4"


def test_find_missing_device():
    with pytest.raises(LookupError):
        find_usb_device("xarm1", enumerate_fn=lambda v, p: [])


def test_find_refuses_green_by_name():
    with pytest.raises(PortNotAllowed):
        find_usb_device("so101-green", enumerate_fn=lambda v, p: [])


def test_find_refuses_a_device_with_greens_serial():
    green_serial = sorted(load_registry().off_limits_serials())[0]
    evil = xarm_info(serial_number=green_serial)
    with pytest.raises(PortNotAllowed):
        find_usb_device("xarm1", enumerate_fn=lambda v, p: [evil])


def test_green_serials_are_blocked_on_every_os():
    from lab_os.devices import check_port_allowed

    serials = load_registry().off_limits_serials()
    assert len(serials) == 2
    for serial in serials:
        for path in (f"/dev/cu.usbmodem{serial}1", f"/dev/serial/by-id/x_{serial}-if00"):
            with pytest.raises(PortNotAllowed):
                check_port_allowed(path)


def reply(positions: dict[int, int]) -> bytes:
    body = bytes([len(positions)])
    for sid, pos in positions.items():
        body += bytes([sid, pos & 0xFF, pos >> 8])
    report = bytes([0x55, 0x55, len(body) + 2, xarm.CMD_GET_SERVO_POSITION]) + body
    return report.ljust(64, b"\x00")


class FakeHid:
    def __init__(self, positions):
        self.positions = positions
        self.written = []
        self.pending = []
        self.closed = False

    def write(self, data):
        self.written.append(bytes(data))
        if data[4] == xarm.CMD_GET_SERVO_POSITION:
            self.pending.append(reply(self.positions))
        return len(data)

    def read(self, size, timeout=None):
        return self.pending.pop(0) if self.pending else b""

    def close(self):
        self.closed = True


def connected_arm(positions=None, **kw) -> tuple[XArm, FakeHid]:
    fake = FakeHid(positions or dict.fromkeys(xarm.SERVO_IDS.values(), 500))
    arm = XArm(**kw)
    arm._dev = fake
    return arm, fake


def test_report_layout():
    report = xarm.build_report(0x15, bytes([1, 6]))
    assert len(report) == 65
    assert report[:7] == bytes([0, 0x55, 0x55, 4, 0x15, 1, 6])


def test_parse_positions():
    assert xarm.parse_positions(reply({6: 663, 1: 456})) == {6: 663, 1: 456}
    with pytest.raises(ValueError):
        xarm.parse_positions(b"\x00" * 64)


def test_read_joints_maps_servos_to_shared_names():
    positions = dict.fromkeys(xarm.SERVO_IDS.values(), 500) | {6: 750, 4: 750, 5: 750, 1: 302}
    arm, fake = connected_arm(positions)
    joints = arm.read_joints()
    assert set(joints) == set(arm.joint_names)
    assert joints["shoulder_pan"] == pytest.approx(-60.0)  # +units = counter-clockwise
    assert joints["shoulder_lift"] == pytest.approx(60.0)
    assert joints["elbow_flex"] == pytest.approx(-60.0)
    assert joints["wrist_flex"] == 0.0
    assert joints["gripper"] == pytest.approx(90.0)  # 302 = open
    assert [w[5] for w in fake.written] == [6]  # one request for all six servos


@pytest.mark.parametrize("joint", list(xarm.SERVO_IDS))
def test_position_degrees_roundtrip(joint):
    for pos in (0, 250, 302, 500, 750, 999, 1000):
        deg = xarm.position_to_degrees(joint, pos)
        assert xarm.degrees_to_position(joint, deg) == pos


def test_gripper_open_closed():
    assert xarm.degrees_to_position("gripper", 0.0) == xarm.GRIPPER_CLOSED
    assert xarm.degrees_to_position("gripper", 90.0) == xarm.GRIPPER_OPEN


def test_read_times_out_without_reply():
    arm, fake = connected_arm(read_timeout_s=0.01)
    fake.write = lambda data: len(data)  # device never answers
    with pytest.raises(TimeoutError):
        arm.read_raw()


def test_reads_are_paced_while_motion_is_on():
    arm, fake = connected_arm(allow_motion=True)
    arm.read_raw()
    arm.read_raw()  # too soon: served from the last reading
    assert len(fake.written) == 1
    arm._last_read = (arm._last_read[0] - 1.0, arm._last_read[1])
    arm.read_raw()
    assert len(fake.written) == 2


def test_read_only_reads_are_not_paced():
    arm, fake = connected_arm()
    arm.read_raw()
    arm.read_raw()
    assert len(fake.written) == 2


def test_incomplete_reply_counts_as_timeout():
    arm, fake = connected_arm({6: 500, 5: 500}, read_timeout_s=0.01)
    with pytest.raises(TimeoutError):
        arm.read_raw()


def test_read_only_driver_cannot_move():
    arm, fake = connected_arm()
    with pytest.raises(MotionDisabled):
        arm.move_joints({"gripper": 10.0}, 0.1)
    with pytest.raises(MotionDisabled):
        arm._send(xarm.CMD_SERVO_MOVE, b"\x01\x00\x00\x01\x00\x00")
    assert fake.written == []


def test_stop_sends_nothing():
    arm, fake = connected_arm()
    arm.stop()
    assert arm.stopped and fake.written == []


def test_move_encoding_when_motion_is_allowed():
    arm, fake = connected_arm(allow_motion=True)
    arm.move_joints({"gripper": 500.0}, 0.5)  # clamped to 90 deg = fully open
    move = [w for w in fake.written if w[4] == xarm.CMD_SERVO_MOVE][0]
    assert move[5] == 1  # one servo
    assert (move[8], move[9] | move[10] << 8) == (1, xarm.GRIPPER_OPEN)


def test_stopped_arm_ignores_moves():
    arm, fake = connected_arm(allow_motion=True)
    arm.stop()
    arm.move_joints({"gripper": 10.0}, 0.5)
    assert fake.written == []
