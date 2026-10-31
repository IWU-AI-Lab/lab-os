"""xArm driver and USB lookup tests: no hardware, the HID device is faked."""

import time

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


MOVE, READ = xarm.CMD_SERVO_MOVE, xarm.CMD_GET_SERVO_POSITION


def moves(fake):
    """Decoded move commands: (duration_ms, {servo_id: position})."""
    out = []
    for w in fake.written:
        if w[4] == MOVE:
            n = w[5]
            out.append(
                (
                    w[6] | w[7] << 8,
                    {w[8 + 3 * k]: w[9 + 3 * k] | w[10 + 3 * k] << 8 for k in range(n)},
                )
            )
    return out


def reads(fake):
    return sum(w[4] == READ for w in fake.written)


def motion_arm(**kw):
    arm, fake = connected_arm(allow_motion=True, limits=xarm.load_limits("none"), **kw)
    arm.read_joints()  # first call takes one real reading (the starting estimate)
    arm._last_read_t = time.monotonic()
    fake.written.clear()
    return arm, fake


def T(offset=0.0):
    """Tick times on the same clock as the driver's estimate."""
    return time.monotonic() + offset


def stream(arm, joint, start, deg_per_s, ticks, t0, dt=0.02):
    """Teleop-style: a new goal every tick, moving at deg_per_s."""
    for k in range(ticks):
        arm.move_joints({joint: start + deg_per_s * dt * k}, 1.0)
        arm._tick(t0 + dt * k)
    return t0 + dt * ticks


def test_move_joints_never_touches_usb():
    arm, fake = motion_arm()
    arm.move_joints({"wrist_roll": 10.0}, 0.5)
    assert fake.written == []  # the worker sends; the teleop loop never waits for USB


def test_a_moving_joint_aims_ahead_so_the_servo_keeps_running():
    arm, fake = motion_arm()
    t = stream(arm, "wrist_roll", 0.0, 12.0, 30, T())  # 12 °/s, like a held key at speed 0.2
    duration, last = moves(fake)[-1]
    goal = 12.0 * 0.02 * 29
    aimed = xarm.position_to_degrees("wrist_roll", last[2])
    assert aimed == pytest.approx(goal + 12.0 * arm.lead_s, abs=0.5)  # lead_s ahead
    assert duration == int(arm.lead_s * 1000)
    # Key released: the goal stops changing → the next command aims at the goal (no coasting).
    for k in range(5):
        arm._tick(t + 0.02 * k)
    assert xarm.position_to_degrees("wrist_roll", moves(fake)[-1][1][2]) == pytest.approx(
        goal, abs=0.3
    )


def test_no_reads_while_moving_and_one_when_idle():
    arm, fake = motion_arm()
    t = stream(arm, "gripper", 30.0, 12.0, 50, T())
    assert reads(fake) == 0
    arm._tick(t + 0.1)  # released: one last move, aimed at the goal itself
    arm._tick(t + 1.0)  # idle for a while
    assert reads(fake) == 1


def test_stop_holds_where_the_servo_is_now():
    arm, fake = motion_arm()
    t = stream(arm, "wrist_roll", 0.0, 30.0, 20, T())
    est = arm.read_joints()["wrist_roll"]
    arm.stop()
    arm._tick(t)
    duration, last = moves(fake)[-1]
    held = xarm.position_to_degrees("wrist_roll", last[2])
    assert held < 30.0 * 0.02 * 19 + 1  # not the lead target ahead of the goal
    assert held == pytest.approx(est, abs=2.0)
    n = len(moves(fake))
    arm.move_joints({"wrist_roll": 50.0}, 1.0)  # ignored while stopped
    arm._tick(t + 0.02)
    assert len(moves(fake)) == n


def test_a_big_jump_is_spread_out():
    arm, fake = motion_arm()
    arm.move_joints({"shoulder_pan": 70.0}, 0.5)
    arm._tick(T())
    first = xarm.position_to_degrees("shoulder_pan", moves(fake)[-1][1][6])
    assert abs(first) <= 120.0 * 0.5 * arm.lead_s + 0.3  # ≤ 18° per lead_s, not all 70° at once


def test_idle_reading_far_from_the_estimate_is_reported(caplog):
    arm, fake = motion_arm()
    t = stream(arm, "elbow_flex", 0.0, 30.0, 30, T())  # told to go to ~17°...
    fake.positions = dict.fromkeys(xarm.SERVO_IDS.values(), 500)  # ...but it never moved (limp)
    arm._tick(t + 0.1)
    arm._tick(t + 1.0)
    assert "elbow_flex" in caplog.text
    assert arm.read_joints()["elbow_flex"] == pytest.approx(0.0)  # the reading wins


def test_limits_from_calibration_file(tmp_path):
    (tmp_path / "xarm9").mkdir()
    (tmp_path / "xarm9" / "limits.yaml").write_text(
        "limits_deg:\n  shoulder_pan: [50, -60]\n  elbow_flex: [-125, 30]\n"
    )
    limits = xarm.load_limits("xarm9", tmp_path)
    assert (limits["shoulder_pan"].low, limits["shoulder_pan"].high) == (-60, 50)
    assert limits["elbow_flex"].low == -120.0  # never beyond what the servo allows
    assert limits["wrist_flex"] == xarm.DEFAULT_LIMITS["wrist_flex"]  # not measured: default


def test_without_calibration_the_safe_defaults_apply():
    limits = xarm.load_limits("not-calibrated")
    assert limits["shoulder_pan"].high == 72.0
    assert limits["gripper"] == xarm.GRIPPER_LIMIT


def test_move_encoding_and_clamp():
    arm, fake = motion_arm()
    arm.send_move({"gripper": 500.0}, 300)  # clamped to 90° = fully open
    duration, servos = moves(fake)[-1]
    assert (duration, servos) == (300, {1: xarm.GRIPPER_OPEN})


def test_starting_outside_the_limits_does_not_snap_back():
    # Base found at raw 14 = +116.6° (driven there with older, wider limits); default limit is 72°.
    arm, fake = motion_arm(positions=dict.fromkeys(xarm.SERVO_IDS.values(), 500) | {6: 14})
    start = arm.read_joints()["shoulder_pan"]
    assert start > 100
    arm.move_joints({"shoulder_pan": start - 1.0}, 1.0)  # jog 1° back toward the middle
    arm._tick(T())
    aimed = xarm.position_to_degrees("shoulder_pan", moves(fake)[-1][1][6])
    assert aimed == pytest.approx(start - 1.0, abs=0.3)  # not clamped to 72°
    arm.move_joints({"shoulder_pan": start + 5.0}, 1.0)  # but never further out than it is
    arm._tick(T(0.02))
    assert xarm.position_to_degrees("shoulder_pan", moves(fake)[-1][1][6]) <= start + 0.3


def test_positions_past_zero_are_negative_not_huge():
    report = reply({6: 500}).replace(
        bytes([6, 500 & 0xFF, 500 >> 8]), bytes([6, 0xDC, 0xFF])
    )  # -36
    assert xarm.parse_positions(report)[6] == -36


def test_a_garbled_calibration_side_falls_back_to_the_default(tmp_path):
    # The real file from 2026-10-29: two sides came from the unsigned-parsing bug.
    (tmp_path / "xarm1").mkdir()
    (tmp_path / "xarm1" / "limits.yaml").write_text(
        "limits_deg:\n  shoulder_pan: [-15600.0, 103.2]\n  elbow_flex: [-15603.4, 110.2]\n"
        "  wrist_flex: [-108.5, 129.4]\n  gripper: [12.7, 126.0]\n"
    )
    limits = xarm.load_limits("xarm1", tmp_path)
    assert limits["shoulder_pan"].low == xarm.DEFAULT_LIMITS["shoulder_pan"].low  # not -120
    assert limits["shoulder_pan"].high == 103.2
    assert limits["elbow_flex"].low == xarm.DEFAULT_LIMITS["elbow_flex"].low
    assert limits["wrist_flex"].high == 120.0  # a bit past the servo range: clamped
    assert (limits["gripper"].low, limits["gripper"].high) == (12.7, 90.0)
