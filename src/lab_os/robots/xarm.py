"""xArm 1S (Hiwonder) over USB HID. Same interface as FakeArm (see base.py).

Protocol (from the Hiwonder xArm docs / the `xarm` PyPI package, which we don't use: it is a thin
unmaintained wrapper): 64-byte HID reports `55 55 <len> <cmd> <data...>`, `len` = len(data) + 2.
Servo positions are 0..1000 (500 = middle) and span about 240 degrees.

READ-ONLY by default: until `allow_motion=True`, only the whitelisted read commands can be sent,
so nothing here can move a servo. Turn motion on only after the builder's OK (SAFETY.md).

Measured 2026-10-27 (docs/GOTCHAS.md): position reads closer than ~0.1 s apart make the board
silently drop move commands, so with motion on, reads are paced (`min_read_interval_s`).
"""

import time
from dataclasses import dataclass, field

from lab_os.devices import find_usb_device
from lab_os.robots.base import JointLimit

SIGNATURE = 0x55
CMD_SERVO_MOVE = 0x03
CMD_GET_BATTERY_VOLTAGE = 0x0F
CMD_GET_SERVO_POSITION = 0x15
READ_COMMANDS = frozenset({CMD_GET_BATTERY_VOLTAGE, CMD_GET_SERVO_POSITION})
REPORT_SIZE = 64

# Shared joint name -> servo id on the xArm 1S (servo 1 is the gripper, 6 the base).
SERVO_IDS = {
    "shoulder_pan": 6,
    "shoulder_lift": 5,
    "elbow_flex": 4,
    "wrist_flex": 3,
    "wrist_roll": 2,
    "gripper": 1,
}
# Shared conventions (same as the SO-101 and web/arm/arm-model.js): 0 = arm upright, +pan swings to
# the arm's right (clockwise from above), +lift/+elbow/+wrist_flex tilt forward, +wrist_roll is
# counter-clockwise from above. "Forward" = the side with the controller board. Signs observed by
# the builder on 2026-10-27 (docs/GOTCHAS.md).
SIGNS = {
    "shoulder_pan": -1,  # +units = counter-clockwise from above
    "shoulder_lift": 1,  # +units = toward the board
    "elbow_flex": -1,  # +units = away from the board
    "wrist_flex": 1,  # +units = toward the board
    "wrist_roll": 1,  # +units = counter-clockwise from above
}
# HACK: 500 = upright matches the board's "Run" pose; 240 deg / 1000 units is the datasheet value,
# not measured.
DEGREES_PER_UNIT = 240 / 1000
CENTER = 500
JOINT_LIMIT = JointLimit(-120.0, 120.0)
# Gripper: 0 deg = closed, 90 = open (like the 3D model). Raw open/closed values from the builder's
# own grab script; +units closes.
GRIPPER_OPEN, GRIPPER_CLOSED = 302, 750
GRIPPER_LIMIT = JointLimit(0.0, 90.0)


class MotionDisabled(RuntimeError):
    """Raised when something tries to move the arm while the driver is read-only."""


def position_to_degrees(joint: str, position: int) -> float:
    if joint == "gripper":
        return (GRIPPER_CLOSED - position) * 90 / (GRIPPER_CLOSED - GRIPPER_OPEN)
    return SIGNS[joint] * (position - CENTER) * DEGREES_PER_UNIT


def degrees_to_position(joint: str, degrees: float) -> int:
    if joint == "gripper":
        position = GRIPPER_CLOSED - degrees * (GRIPPER_CLOSED - GRIPPER_OPEN) / 90
    else:
        position = CENTER + SIGNS[joint] * degrees / DEGREES_PER_UNIT
    return min(max(round(position), 0), 1000)


def build_report(cmd: int, data: bytes = b"") -> bytes:
    """A full HID output report: report id 0, then 64 bytes (padded; Windows insists on it)."""
    body = bytes([SIGNATURE, SIGNATURE, len(data) + 2, cmd]) + data
    return (b"\x00" + body).ljust(REPORT_SIZE + 1, b"\x00")


def parse_positions(report: bytes) -> dict[int, int]:
    """Servo id -> position from a CMD_GET_SERVO_POSITION reply."""
    if len(report) < 5 or report[0] != SIGNATURE or report[1] != SIGNATURE:
        raise ValueError(f"not an xArm report: {bytes(report[:8]).hex(' ')}")
    if report[3] != CMD_GET_SERVO_POSITION:
        raise ValueError(f"unexpected command 0x{report[3]:02x} in reply")
    count = report[4]
    if 5 + 3 * count > len(report):
        raise ValueError("position report is too short")
    return {report[5 + 3 * i]: report[6 + 3 * i] | (report[7 + 3 * i] << 8) for i in range(count)}


@dataclass
class XArm:
    name: str = "xarm1"
    model: str = "xarm1s"
    joint_names: tuple[str, ...] = tuple(SERVO_IDS)
    limits: dict[str, JointLimit] = field(
        default_factory=lambda: dict.fromkeys(SERVO_IDS, JOINT_LIMIT) | {"gripper": GRIPPER_LIMIT}
    )
    device_name: str = "xarm1"  # key in config/devices.yaml
    allow_motion: bool = False
    read_timeout_s: float = 0.1
    # HACK: 0.25 s worked in every test, ~0.09 s blocked all moves; the real limit is unknown.
    min_read_interval_s: float = 0.25  # only applies while allow_motion is on
    stopped: bool = False
    _dev: object = field(default=None, repr=False)
    _last_read: tuple[float, dict[int, int]] | None = field(default=None, repr=False)

    def connect(self) -> None:
        import hid  # late import: tests and non-xArm work don't need the native hidapi library

        info = find_usb_device(self.device_name)  # refuses off-limits devices
        self._dev = hid.Device(path=info["path"])

    def read_raw(self) -> dict[int, int]:
        """Servo id -> raw position (0..1000), one request for all six servos.

        With motion on, a call sooner than `min_read_interval_s` after the last bus read returns
        that reading again instead of asking the board (fast reads starve moves)."""
        dev = self._require_connected()
        now = time.monotonic()
        if (
            self.allow_motion
            and self._last_read
            and now - self._last_read[0] < self.min_read_interval_s
        ):
            return dict(self._last_read[1])
        while dev.read(REPORT_SIZE, 0):  # drop stale reports
            pass
        self._send(CMD_GET_SERVO_POSITION, bytes([len(SERVO_IDS), *SERVO_IDS.values()]))
        deadline = time.monotonic() + self.read_timeout_s
        while time.monotonic() < deadline:
            report = dev.read(REPORT_SIZE, max(1, int((deadline - time.monotonic()) * 1000)))
            if report and report[3] == CMD_GET_SERVO_POSITION:
                positions = parse_positions(bytes(report))
                if set(positions) != set(SERVO_IDS.values()):  # happens while servos move
                    raise TimeoutError(f"{self.name}: incomplete reply {positions}")
                self._last_read = (now, positions)
                return dict(positions)
        raise TimeoutError(f"{self.name}: no position reply within {self.read_timeout_s} s")

    def read_joints(self) -> dict[str, float]:
        raw = self.read_raw()
        return {j: position_to_degrees(j, raw[sid]) for j, sid in SERVO_IDS.items()}

    def read_battery_v(self) -> float:
        dev = self._require_connected()
        self._send(CMD_GET_BATTERY_VOLTAGE)
        report = dev.read(REPORT_SIZE, int(self.read_timeout_s * 1000))
        if not report or report[3] != CMD_GET_BATTERY_VOLTAGE:
            raise TimeoutError(f"{self.name}: no battery reply")
        return (report[5] << 8 | report[4]) / 1000

    def move_joints(self, targets: dict[str, float], speed_scale: float) -> None:
        if not self.allow_motion:
            raise MotionDisabled(f"{self.name} is read-only (allow_motion=False)")
        self._require_connected()
        if self.stopped:
            return
        unknown = set(targets) - set(self.joint_names)
        if unknown:
            raise KeyError(f"unknown joints: {sorted(unknown)}")
        speed_scale = min(max(speed_scale, 0.0), 1.0)
        if speed_scale == 0.0:
            return
        # HACK: duration from a flat 120 deg/s * speed_scale guess; replace with measured values.
        current = self.read_joints()
        travel = max(
            (abs(self.limits[j].clamp(v) - current[j]) for j, v in targets.items()), default=0
        )
        self.send_move(targets, max(int(travel / (120 * speed_scale) * 1000), 50))

    def send_move(self, targets: dict[str, float], duration_ms: int) -> None:
        """One move command, no reply wait. Clamps to limits; needs allow_motion."""
        if not self.allow_motion:
            raise MotionDisabled(f"{self.name} is read-only (allow_motion=False)")
        if self.stopped:
            return
        data = bytearray([len(targets), duration_ms & 0xFF, duration_ms >> 8])
        for joint, degrees in targets.items():
            position = degrees_to_position(joint, self.limits[joint].clamp(degrees))
            data += bytes([SERVO_IDS[joint], position & 0xFF, position >> 8])
        self._send(CMD_SERVO_MOVE, bytes(data))

    def stop(self) -> None:
        """Ignore further moves. Sends nothing: the xArm's only stop command cuts servo torque,
        which would drop the arm. A move already sent still finishes (≤ its duration), so keep
        streamed moves short (~100 ms). Hold-position on stop is still open."""
        self.stopped = True

    def resume(self) -> None:
        self.stopped = False

    def close(self) -> None:
        if self._dev is not None:
            self._dev.close()
            self._dev = None

    def _send(self, cmd: int, data: bytes = b"") -> None:
        if cmd not in READ_COMMANDS and not self.allow_motion:
            raise MotionDisabled(f"command 0x{cmd:02x} is blocked while read-only")
        self._require_connected().write(build_report(cmd, data))

    def _require_connected(self):
        if self._dev is None:
            raise RuntimeError(f"{self.name} is not connected")
        return self._dev


def main() -> None:
    """Read-only check: python -m lab_os.robots.xarm  (positions + reads/second)."""
    arm = XArm()
    arm.connect()
    try:
        print("raw positions:", arm.read_raw())
        print("joints (deg):", {j: round(v, 1) for j, v in arm.read_joints().items()})
        print("battery V:", arm.read_battery_v())
        n, t0 = 0, time.perf_counter()
        durations, timeouts = [], 0
        while time.perf_counter() - t0 < 5:
            t = time.perf_counter()
            try:
                arm.read_raw()
            except TimeoutError:
                timeouts += 1
                continue
            durations.append(time.perf_counter() - t)
            n += 1
        elapsed = time.perf_counter() - t0
        durations.sort()
        print(
            f"{n / elapsed:.0f} reads/s over {elapsed:.1f} s; "
            f"median {durations[n // 2] * 1000:.1f} ms, worst {durations[-1] * 1000:.1f} ms; "
            f"{timeouts} timeouts"
        )
    finally:
        arm.close()


if __name__ == "__main__":
    main()
