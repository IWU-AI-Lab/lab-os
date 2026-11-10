"""xArm 1S (Hiwonder) over USB HID. Same interface as FakeArm (see base.py).

Protocol (from the Hiwonder xArm docs / the `xarm` PyPI package, which we don't use: it is a thin
unmaintained wrapper): 64-byte HID reports `55 55 <len> <cmd> <data...>`, `len` = len(data) + 2.
Servo positions are 0..1000 (500 = middle) and span about 240 degrees.

READ-ONLY by default: until `allow_motion=True`, only the whitelisted read commands can be sent,
so nothing here can move a servo. Turn motion on only after the builder's OK (SAFETY.md).

With motion on, a worker thread owns the USB device (docs/GOTCHAS.md 2026-10-27/29):
- Never blocks the caller: `move_joints` only stores the goal, `read_joints` returns the driver's
  estimate (where each servo was told to be, following the board's linear interpolation).
- No reads while moving: reads closer than ~0.1 s apart make the board drop moves, and a read
  blocks for 10-100 ms. The worker reads only when the arm has been idle for a while.
- "Lead" targets: while a joint is moving, it aims `lead_s` ahead along its current speed, with a
  move duration of `lead_s`. The servo then runs smoothly instead of stopping in its deadband
  (it ignores errors of a few units). When the goal stops changing, the aim is the goal itself,
  and `stop()` sends "hold where you are" at once, so nothing coasts on.
- Limits come from `calibration/<name>/limits.yaml` (measured by hand: `python -m
  lab_os.robots.xarm calibrate`), otherwise from conservative defaults. Driving a servo into a hard
  stop makes it switch itself off (goes limp).
"""

import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from lab_os import REPO_ROOT
from lab_os.devices import default_device, find_usb_device
from lab_os.robots.base import JointLimit

log = logging.getLogger(__name__)
CALIBRATION_DIR = REPO_ROOT / "calibration"

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
JOINT_LIMIT = JointLimit(-120.0, 120.0)  # what the servo itself allows (0..1000 units)
# Used until calibration/<name>/limits.yaml exists: the raw ranges of the builder's own grab script
# (known safe on this arm), converted with SIGNS; wrist_roll is a guess. Calibrate to widen them.
DEFAULT_LIMITS = {
    "shoulder_pan": JointLimit(-72.0, 72.0),  # raw 800..200
    "shoulder_lift": JointLimit(-24.0, 96.0),  # raw 400..900
    "elbow_flex": JointLimit(-6.0, 108.0),  # raw 525..50 (upright "Run" pose reads about -5.5)
    "wrist_flex": JointLimit(-24.0, 84.0),  # raw 400..850
    "wrist_roll": JointLimit(-90.0, 90.0),
}
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
    # Signed 16-bit: a servo pushed past its 0 end by hand reports e.g. -36, not 65500
    # (2026-10-29: that made a calibration say -15600°).
    out = {}
    for i in range(count):
        v = report[6 + 3 * i] | (report[7 + 3 * i] << 8)
        out[report[5 + 3 * i]] = v - 0x10000 if v >= 0x8000 else v
    return out


PLAUSIBLE_DEG = 30.0  # readings a little past the servo's 0..1000 happen when pushed by hand


def load_limits(name: str, directory: Path = CALIBRATION_DIR) -> dict[str, JointLimit]:
    """Measured limits from calibration/<name>/limits.yaml, else the defaults. Never wider than
    the servo range."""
    defaults = dict(DEFAULT_LIMITS) | {"gripper": GRIPPER_LIMIT}
    limits = dict(defaults)
    path = directory / name / "limits.yaml"
    if path.exists():
        raw = yaml.safe_load(path.read_text()) or {}
        for joint, (lo, hi) in (raw.get("limits_deg") or {}).items():
            if joint not in limits:
                continue
            lo, hi = min(lo, hi), max(lo, hi)
            hard = GRIPPER_LIMIT if joint == "gripper" else JOINT_LIMIT
            # A side far outside what the servo can report is a bad reading, not a limit: keep
            # the safe default for that side.
            if lo < hard.low - PLAUSIBLE_DEG:
                log.warning("%s: ignoring calibrated %s low %.1f°, using default", name, joint, lo)
                lo = defaults[joint].low
            if hi > hard.high + PLAUSIBLE_DEG:
                log.warning("%s: ignoring calibrated %s high %.1f°, using default", name, joint, hi)
                hi = defaults[joint].high
            limits[joint] = JointLimit(max(lo, hard.low), min(hi, hard.high))
    return limits


@dataclass
class _Segment:
    """One commanded servo move: linear from `start` to `aim` over `duration` (the board's own
    interpolation), so the driver knows where the servo should be without asking."""

    start: float
    aim: float
    t0: float
    duration: float

    def at(self, t: float) -> float:
        k = 1.0 if self.duration <= 0 else min(max((t - self.t0) / self.duration, 0.0), 1.0)
        return self.start + (self.aim - self.start) * k


@dataclass
class XArm:
    name: str = "xarm1"
    model: str = "xarm1s"
    joint_names: tuple[str, ...] = tuple(SERVO_IDS)
    limits: dict[str, JointLimit] | None = None  # None = load_limits(name)
    device_name: str = "xarm1"  # key in config/devices.yaml
    allow_motion: bool = False
    read_timeout_s: float = 0.15  # replies take up to ~120 ms (2026-10-29)
    # Motion tuning (worker thread). lead_s: how far ahead a moving joint aims, also the move
    # duration. HACK: values from the first tests, not optimized.
    lead_s: float = 0.3
    period_s: float = 0.02
    max_deg_per_s: float = 120.0  # at speed_scale 1; big jumps are spread out at this speed
    idle_read_after_s: float = 0.6  # read the board only after this long without a move
    min_read_interval_s: float = 0.25  # reads closer than ~0.1 s made the board drop moves
    off_by_warn_deg: float = 10.0  # idle reading this far from the estimate: limp or blocked
    stopped: bool = False
    _dev: object = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)  # driver state
    _io: threading.RLock = field(default_factory=threading.RLock, repr=False)  # the USB device
    _thread: threading.Thread | None = field(default=None, repr=False)
    _quit: threading.Event = field(default_factory=threading.Event, repr=False)
    _goal: dict[str, float] = field(default_factory=dict, repr=False)  # from move_joints
    _goal_seq: int = field(default=0, repr=False)
    _speed: float = field(default=1.0, repr=False)
    _hold: bool = field(default=False, repr=False)
    _seg: dict[str, _Segment] = field(default_factory=dict, repr=False)
    _prev_goal: dict[str, float] = field(default_factory=dict, repr=False)
    _prev_goal_t: float = field(default=0.0, repr=False)
    _seen_seq: int = field(default=0, repr=False)
    _vel: dict[str, float] = field(default_factory=dict, repr=False)
    _last_change_t: float = field(default=-1e9, repr=False)
    _last_send_t: float = field(default=-1e9, repr=False)
    _last_read_t: float = field(default=-1e9, repr=False)
    measured: dict[str, float] = field(default_factory=dict)  # latest real reading (degrees)
    # The limits, widened to include where the arm really is: if it starts outside them (moved by
    # hand, older limits), goals are clamped to here instead of snapping it back into range.
    _allowed: dict[str, JointLimit] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.limits is None:
            self.limits = load_limits(self.name)

    # ---- connection ---------------------------------------------------------------------------
    def connect(self) -> None:
        import hid  # late import: tests and non-xArm work don't need the native hidapi library

        info = find_usb_device(self.device_name)  # refuses off-limits devices
        self._dev = hid.Device(path=info["path"])
        if self.allow_motion:
            self._init_estimate()
            self._quit.clear()
            self._thread = threading.Thread(target=self._run, name=f"{self.name}-io", daemon=True)
            self._thread.start()

    def close(self) -> None:
        if self._thread:
            self.stop()
            time.sleep(2 * self.period_s)  # let the worker send the hold
            self._quit.set()
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._dev is not None:
            self._dev.close()
            self._dev = None

    # ---- reading ------------------------------------------------------------------------------
    def read_raw(self) -> dict[int, int]:
        """Servo id -> raw position (0..1000), straight from the board (blocks 10-100 ms). For
        read-only use; while a motion worker runs, use read_joints()."""
        dev = self._require_connected()
        with self._io:  # request + reply as one unit, whichever thread asks
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
                    return positions
        raise TimeoutError(f"{self.name}: no position reply within {self.read_timeout_s} s")

    def read_measured(self) -> dict[str, float]:
        raw = self.read_raw()
        return {j: position_to_degrees(j, raw[sid]) for j, sid in SERVO_IDS.items()}

    def read_joints(self) -> dict[str, float]:
        """Read-only: a real reading. With motion on: the driver's estimate (never blocks)."""
        if not self.allow_motion:
            return self.read_measured()
        with self._lock:
            if not self._seg:
                self._init_estimate()
            return self._estimate()

    def read_battery_v(self) -> float:
        dev = self._require_connected()
        with self._io:
            self._send(CMD_GET_BATTERY_VOLTAGE)
            report = dev.read(REPORT_SIZE, int(self.read_timeout_s * 1000))
        if not report or report[3] != CMD_GET_BATTERY_VOLTAGE:
            raise TimeoutError(f"{self.name}: no battery reply")
        return (report[5] << 8 | report[4]) / 1000

    # ---- moving -------------------------------------------------------------------------------
    def move_joints(self, targets: dict[str, float], speed_scale: float) -> None:
        """Store a new goal; the worker moves there (smoothly, at most max_deg_per_s * speed)."""
        if not self.allow_motion:
            raise MotionDisabled(f"{self.name} is read-only (allow_motion=False)")
        self._require_connected()
        unknown = set(targets) - set(self.joint_names)
        if unknown:
            raise KeyError(f"unknown joints: {sorted(unknown)}")
        with self._lock:
            if self.stopped:
                return
            self._goal.update({j: self._allow(j).clamp(v) for j, v in targets.items()})
            self._goal_seq += 1
            self._speed = min(max(speed_scale, 0.0), 1.0)

    def commanded_joints(self) -> dict[str, float]:
        """The goal as accepted (after clamping), for viewers; read_joints() is the estimate."""
        with self._lock:
            return self._estimate() | dict(self._goal)

    def _allow(self, joint: str) -> JointLimit:
        return self._allowed.get(joint) or self.limits[joint]

    def _widen_to(self, measured: dict[str, float]) -> None:
        """Recompute the allowed ranges from the limits and a real reading (caller holds _lock)."""
        self._allowed = {
            j: JointLimit(
                min(lim.low, measured.get(j, lim.low)), max(lim.high, measured.get(j, lim.high))
            )
            for j, lim in self.limits.items()
        }

    def _estimate(self) -> dict[str, float]:
        """Where each servo should be now (caller holds _lock)."""
        now = time.monotonic()
        return {j: seg.at(now) for j, seg in self._seg.items()}

    def send_move(self, targets: dict[str, float], duration_ms: int) -> None:
        """One raw move command, bypassing the worker (motion tests). Clamps to limits."""
        if not self.allow_motion:
            raise MotionDisabled(f"{self.name} is read-only (allow_motion=False)")
        if self.stopped:
            return
        self._write_move({j: self.limits[j].clamp(v) for j, v in targets.items()}, duration_ms)

    def stop(self) -> None:
        """Freeze: further moves are ignored and the worker sends "hold where you are now"
        (not the servo's stop command: that cuts torque and drops the arm)."""
        with self._lock:
            self.stopped = True
            self._hold = True

    def resume(self) -> None:
        with self._lock:
            self.stopped = False

    # ---- worker -------------------------------------------------------------------------------
    def _run(self) -> None:
        while not self._quit.is_set():
            t = time.monotonic()
            try:
                self._tick(t)
            except Exception:  # never let the I/O thread die silently
                log.exception("%s: worker tick failed", self.name)
            self._quit.wait(max(0.0, self.period_s - (time.monotonic() - t)))

    def _tick(self, now: float) -> None:
        """One worker step: hold / follow the goal / read when idle."""
        with self._lock:
            hold, self._hold = self._hold, False
            goal, seq, speed = dict(self._goal), self._goal_seq, self._speed
            est = {j: seg.at(now) for j, seg in self._seg.items()}
            if hold:
                self._goal = {}
        if hold:
            self._command({j: v for j, v in est.items()}, now, 0.1, est)
            return
        if goal:
            self._follow(goal, seq, speed, est, now)
        if (
            now - self._last_send_t > self.idle_read_after_s
            and now - self._last_read_t > self.min_read_interval_s
        ):
            self._idle_read(est, now)

    def _follow(self, goal: dict[str, float], seq: int, speed: float, est, now: float) -> None:
        if seq != self._seen_seq:  # a new goal: estimate each joint's speed from the last one
            dt = now - self._prev_goal_t
            if self._prev_goal and 0 < dt < 0.2:
                self._vel = {j: (v - self._prev_goal.get(j, v)) / dt for j, v in goal.items()}
            else:
                self._vel = {}
            self._prev_goal, self._prev_goal_t, self._seen_seq = goal, now, seq
            if any(abs(v) > 0.5 for v in self._vel.values()):
                self._last_change_t = now
        elif now - self._prev_goal_t > 2.5 * self.period_s:
            self._vel = {}  # the goal stopped changing (key released, hand still): no lead
        cap = self.max_deg_per_s * max(speed, 0.05) * self.lead_s  # most a joint may travel
        aim = {}
        for j, g in goal.items():
            lead = self._vel.get(j, 0.0) * self.lead_s
            a = self._allow(j).clamp(g + lead)
            now_j = est.get(j, g)
            aim[j] = now_j + min(max(a - now_j, -cap), cap)
        moving = any(abs(aim[j] - est.get(j, aim[j])) > 0.2 for j in aim)
        changed = any(abs(aim[j] - self._seg[j].aim) > 0.2 if j in self._seg else True for j in aim)
        if changed or (moving and now - self._last_send_t > 0.1):
            self._command(aim, now, self.lead_s, est)

    def _command(self, aim: dict[str, float], now: float, duration: float, est) -> None:
        self._write_move(aim, int(duration * 1000))
        with self._lock:
            for j, a in aim.items():
                self._seg[j] = _Segment(est.get(j, a), a, now, duration)
        self._last_send_t = now

    def _idle_read(self, est: dict[str, float], now: float) -> None:
        self._last_read_t = now
        try:
            measured = self.read_measured()
        except TimeoutError:
            return
        self.measured = measured
        for j, m in measured.items():
            if j in est and abs(m - est[j]) > self.off_by_warn_deg:
                log.warning(
                    "%s: %s is at %.1f°, told %.1f° (limp, blocked, or moved by hand?)",
                    self.name,
                    j,
                    m,
                    est[j],
                )
        with self._lock:  # the reading is the truth now
            self._seg = {j: _Segment(m, m, now, 0.0) for j, m in measured.items()}
            self._widen_to(measured)
            self._goal = {j: v for j, v in self._goal.items() if abs(v - measured[j]) > 0.5}

    def _init_estimate(self) -> None:
        for attempt in range(5):
            try:
                measured = self.read_measured()
                break
            except TimeoutError:
                if attempt == 4:
                    raise
                time.sleep(0.3)
        self.measured = measured
        now = time.monotonic()
        self._seg = {j: _Segment(m, m, now, 0.0) for j, m in measured.items()}
        self._widen_to(measured)

    # ---- low level ----------------------------------------------------------------------------
    def _write_move(self, targets: dict[str, float], duration_ms: int) -> None:
        data = bytearray([len(targets), duration_ms & 0xFF, duration_ms >> 8])
        for joint, degrees in targets.items():
            position = degrees_to_position(joint, degrees)
            data += bytes([SERVO_IDS[joint], position & 0xFF, position >> 8])
        self._send(CMD_SERVO_MOVE, bytes(data))

    def _send(self, cmd: int, data: bytes = b"") -> None:
        if cmd not in READ_COMMANDS and not self.allow_motion:
            raise MotionDisabled(f"command 0x{cmd:02x} is blocked while read-only")
        with self._io:
            self._require_connected().write(build_report(cmd, data))

    def _require_connected(self):
        if self._dev is None:
            raise RuntimeError(f"{self.name} is not connected")
        return self._dev


def calibrate(name: str | None = None, seconds: float = 60.0) -> None:
    """Measure joint limits BY HAND, read-only (no motion command is ever sent).

    Switch the arm on but don't press "Run": the servos are limp. Gently move each joint to the
    furthest safe point in both directions (stop before anything touches the table, the base or
    another part). Press Ctrl+C when done; the ranges are written to calibration/<name>/limits.yaml.
    """
    name = name or default_device(("xarm1s",))
    arm = XArm(name=name, device_name=name)
    arm.connect()
    lo: dict[str, float] = {}
    hi: dict[str, float] = {}
    print(calibrate.__doc__)
    t0 = time.monotonic()
    try:
        while time.monotonic() - t0 < seconds:
            try:
                now = arm.read_measured()
            except TimeoutError:
                continue
            for j, v in now.items():
                if not -120.0 - PLAUSIBLE_DEG <= v <= 120.0 + PLAUSIBLE_DEG:
                    continue  # a garbled reading, not a position
                lo[j], hi[j] = min(lo.get(j, v), v), max(hi.get(j, v), v)
            line = "  ".join(f"{j[:8]} {lo[j]:+6.1f}..{hi[j]:+6.1f}" for j in now)
            sys.stdout.write("\r" + line)
            sys.stdout.flush()
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        arm.close()
    path = CALIBRATION_DIR / name / "limits.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "note": "Measured by hand with the servos limp (python -m lab_os.robots.xarm calibrate).",
        "measured": time.strftime("%Y-%m-%d"),
        "limits_deg": {j: [round(lo[j], 1), round(hi[j], 1)] for j in lo},
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    print(f"\nwrote {path}")


def main() -> None:
    """Read-only check: python -m lab_os.robots.xarm  (positions + reads/second).
    `python -m lab_os.robots.xarm calibrate` measures joint limits by hand."""
    if sys.argv[1:2] == ["calibrate"]:
        calibrate()
        return
    name = default_device(("xarm1s",))
    arm = XArm(name=name, device_name=name)
    arm.connect()
    try:
        print("raw positions:", arm.read_raw())
        print("joints (deg):", {j: round(v, 1) for j, v in arm.read_measured().items()})
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
