"""SO-101 follower over LeRobot's Feetech bus. Same interface as FakeArm / XArm (see base.py).

Needs the optional extra (`uv sync --extra so101`) and a calibration in
calibration/<name>/<name>.json: lab-os's own from `python -m lab_os.robots.so101_setup calibrate`,
or, for a borrowed arm with `training_calibration:` in devices.yaml (the greens), lab-os's COPY
of the training project's file.
The training file in LeRobot's cache (~/.cache/huggingface/lerobot/calibration/…) is the source of
truth: it's only read, and the driver refuses if the copy no longer equals it (2026-11-17).

READ-ONLY by default: until `allow_motion=True`, nothing is written to the motors (no torque, no
goal, not even the calibration). Turn motion on only after the builder's OK (SAFETY.md).
- Connect never jumps: before torque goes on, every goal is set to where the motor already is.
- Joints are LeRobot's degrees (0 = the middle pose from calibration), which should match the URDF
  (models/so101/so101_new_calib.urdf) and so the shared conventions and the IK.
- Limits: the URDF's, narrowed to the ranges measured during calibration.
- `close()` switches torque off (LeRobot's default), so the arm sags: park it first.
- Unplugged and back (quick job 27): `port_present()` says whether the by-id name is still
  there; `drop()` lets go of a port that's gone without writing; `connect()` again reconnects.
"""

import contextlib
import json
import logging
import math
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from lab_os.devices import Device, PortNotAllowed, default_device
from lab_os.robots.base import JointLimit, MotorsNotAnswering
from lab_os.robots.fake import SO101_JOINTS, so101_limits
from lab_os.robots.so101_setup import CALIBRATION_DIR, guarded_port

log = logging.getLogger(__name__)

# LeRobot degree -> shared-convention degree: +1 for every joint (the URDF is made for LeRobot's
# "new" calibration). Checked by hand on so101-white 2026-10-30 (--watch).
SIGNS = dict.fromkeys(SO101_JOINTS[:-1], 1.0)
# LeRobot's gripper is 0..100 % of its calibrated range, 0 = closed (checked 2026-10-30).
# so101-white's range is ~129° of jaw travel, so 1 % ≈ 1.3°; 1.0 is close enough (it only changes
# the jaw angle in the 3D view).
GRIPPER_DEG_PER_PCT = 1.0
STEPS = 4096  # STS3215 positions per turn


class MotionDisabled(RuntimeError):
    """Raised when something tries to move the arm while the driver is read-only."""


def calibrated_limits(
    calibration: dict, base: dict[str, JointLimit], offsets: dict[str, float] | None = None
) -> dict[str, JointLimit]:
    """`base` narrowed to the ranges recorded in a LeRobot calibration (joint -> object with
    range_min/range_max). In degrees mode, 0 is the middle of the recorded range; a joint with an
    offset (the arm's `joint_offsets_deg`) has its range moved by it, like its readings."""
    offsets = offsets or {}
    out = dict(base)
    for joint in SO101_JOINTS[:-1]:
        cal = calibration.get(joint)
        if cal is None:
            continue
        half = (cal.range_max - cal.range_min) / 2 * 360 / (STEPS - 1)
        lo, hi = sorted((-half * SIGNS[joint], half * SIGNS[joint]))
        lo, hi = lo + offsets.get(joint, 0.0), hi + offsets.get(joint, 0.0)
        b = base[joint]
        if max(lo, b.low) < min(hi, b.high):
            out[joint] = JointLimit(max(lo, b.low), min(hi, b.high))
    return out


def lerobot_calibration_root() -> Path:
    """LeRobot's own calibration cache (the training project's). Not HF_LEROBOT_CALIBRATION:
    lab-os points that at its own folder (so101_setup._require_lerobot)."""
    hf_home = os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface"
    return Path(hf_home) / "lerobot" / "calibration"


def check_training_copy(device: Device, copy: Path, root: Path | None = None) -> Path:
    """A borrowed arm: its copy in calibration/ must exist and equal the training file in
    LeRobot's cache (the source of truth; only read). Returns the training file's path. If the
    training file isn't on this computer, the copy is used as is (logged)."""
    source = (root or lerobot_calibration_root()) / device.training_calibration
    refresh = f"cp {source} {copy}"
    if not copy.is_file():
        raise RuntimeError(
            f"{device.name} has no copy of its training calibration ({copy}). Copy it: {refresh}"
        )
    if not source.is_file():
        log.warning("%s: %s isn't here; using lab-os's copy", device.name, source)
        return source
    try:
        same = json.loads(source.read_text()) == json.loads(copy.read_text())
    except ValueError:
        same = False
    if not same:
        raise RuntimeError(
            f"{device.name}'s training calibration ({source.name}) differs from lab-os's copy "
            f"({copy}): it changed, or the copy did. Check why, then copy it again: {refresh}"
        )
    return source


def lerobot_follower(name: str, port: str, calibration_dir: Path):
    """LeRobot's SO-101 follower object, for its bus (opened later) and calibration (loaded now,
    from calibration_dir/<name>.json)."""
    from lab_os.robots.so101_setup import _require_lerobot

    _require_lerobot()
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

    config = SO101FollowerConfig(
        port=port, id=name, calibration_dir=calibration_dir, use_degrees=True
    )
    return SO101Follower(config)


def _to_lerobot(joint: str, degrees: float) -> float:
    if joint == "gripper":
        return min(max(degrees / GRIPPER_DEG_PER_PCT, 0.0), 100.0)
    return degrees * SIGNS[joint]


def _from_lerobot(joint: str, value: float) -> float:
    if joint == "gripper":
        return value * GRIPPER_DEG_PER_PCT
    return value * SIGNS[joint]


@dataclass
class SO101Arm:
    name: str = "so101-white"  # also the key in config/devices.yaml and the calibration id
    model: str = "so101"
    joint_names: tuple[str, ...] = SO101_JOINTS
    limits: dict[str, JointLimit] = field(default_factory=so101_limits)  # narrowed on connect
    allow_motion: bool = False
    max_deg_per_s: float = 120.0  # at speed_scale 1; the driver's own cap, after the mapper's
    min_read_interval_s: float = 0.1  # the teleop loop asks several times a tick
    num_read_retries: int = 2
    stopped: bool = False
    make_robot: Callable[[str, str, Path], object] = lerobot_follower  # replaceable for tests
    calibration_source: Path | None = None  # a borrowed arm: the training file it copies
    # Added to a joint's reading (and taken off its goal) so the model matches the real arm:
    # `joint_offsets_deg` in devices.yaml, set on connect (quick job 106).
    offsets: dict[str, float] = field(default_factory=dict)
    _robot: object = field(default=None, repr=False)
    _port: str | None = field(default=None, repr=False)  # the by-id name it was opened by
    _last: dict[str, float] = field(default_factory=dict, repr=False)  # last reading
    _last_read_t: float = field(default=-math.inf, repr=False)
    _commanded: dict[str, float] = field(default_factory=dict, repr=False)
    _last_write_t: float = field(default=0.0, repr=False)

    def connect(self) -> None:
        # by-id name, board serial, plugged in, and no other program has the port (LeLab, a run)
        device, port = guarded_port(self.name)
        self._port = port
        if device is not None:
            self.offsets = dict(device.joint_offsets_deg)
        folder = CALIBRATION_DIR / self.name
        borrowed = device is not None and bool(device.training_calibration)
        if borrowed:
            self.calibration_source = check_training_copy(device, folder / f"{self.name}.json")
        robot = self.make_robot(self.name, port, folder)  # LeRobot loads the file now
        if not robot.calibration:
            raise RuntimeError(
                f"{self.name} has no calibration in {folder}: run "
                "uv run --extra so101 python -m lab_os.robots.so101_setup calibrate"
            )
        try:
            robot.bus.connect()  # checks all six motors answer
        except (RuntimeError, ConnectionError) as e:
            # LeRobot opened the port before the motor check and doesn't close it on a failure
            with contextlib.suppress(Exception):
                robot.bus.port_handler.closePort()
            raise self._not_answering(e) from e
        try:
            if not robot.bus.is_calibrated:
                if borrowed:
                    raise RuntimeError(
                        f"{self.name}'s motors don't hold its training calibration "
                        f"({self.calibration_source.name}). lab-os never writes a borrowed arm's "
                        "calibration: start teleop once in LeLab, or LeRobot's command line and "
                        "press ENTER at its calibration question (never 'c'), then try again."
                    )
                raise RuntimeError(
                    f"{self.name}'s motors hold a different calibration than its file. Run "
                    "so101_setup calibrate and press Enter to write the file to the motors (or "
                    "'c' to calibrate anew)."
                )
            self._robot = robot
            self._commanded = {}  # a reconnect starts from a fresh reading, not the old goal
            self.limits = calibrated_limits(robot.calibration, self.limits, self.offsets)
            now = self.read_measured()
            if self.allow_motion:
                # Goals = where the motors are, THEN LeRobot's settings (PID, gripper current
                # limit) and torque on: nothing jumps to an old goal.
                robot.bus.sync_write("Goal_Position", self._lerobot_values(now))
                robot.configure()
                self._commanded = dict(now)
                self._last_write_t = time.monotonic()
        except Exception as e:
            with contextlib.suppress(Exception):  # the port goes; the first error is the one said
                robot.bus.disconnect(disable_torque=False)
            self._robot = None
            if isinstance(e, ConnectionError):  # a read or write with no answer (motor 2, N.17)
                raise self._not_answering(e) from e
            raise

    def _not_answering(self, e: Exception) -> MotorsNotAnswering:
        log.warning("%s: %s", self.name, e)  # LeRobot's own words, for the brain's log
        return MotorsNotAnswering(MotorsNotAnswering.SENTENCE)

    def read_measured(self) -> dict[str, float]:
        """Positions straight from the motors (degrees, shared names)."""
        raw = self._require_connected().bus.sync_read(
            "Present_Position", num_retry=self.num_read_retries
        )
        self._last = {j: _from_lerobot(j, v) + self.offsets.get(j, 0.0) for j, v in raw.items()}
        self._last_read_t = time.monotonic()
        return dict(self._last)

    def read_joints(self) -> dict[str, float]:
        """While driving: where the arm was told to be (the servos follow within a few ms).
        Otherwise a reading, at most every `min_read_interval_s`; a failed read returns the
        last one (LeRobot buses drop a packet now and then)."""
        self._require_connected()
        if self._commanded and not self.stopped:
            return dict(self._commanded)
        if time.monotonic() - self._last_read_t >= self.min_read_interval_s:
            try:
                self.read_measured()
            except (ConnectionError, RuntimeError) as e:
                log.warning("%s: read failed (%s); using the last reading", self.name, e)
                if not self._last:
                    raise
        return dict(self._last)

    def move_joints(
        self, targets: dict[str, float], speed_scale: float, deg_per_s: float | None = None
    ) -> None:
        robot = self._require_connected()
        if not self.allow_motion:
            raise MotionDisabled(f"{self.name} is read-only (allow_motion=False)")
        if self.stopped:
            return
        unknown = set(targets) - set(self.joint_names)
        if unknown:
            raise KeyError(f"unknown joints: {sorted(unknown)}")
        now = time.monotonic()
        dt = min(now - self._last_write_t, 0.1)
        # 1:1 mode passes its own cap; inf = none: the goal goes straight to the servos
        speed = (
            self.max_deg_per_s * min(max(speed_scale, 0.0), 1.0) if deg_per_s is None else deg_per_s
        )
        step = math.inf if math.isinf(speed) else speed * dt
        goal = {}
        for joint, value in targets.items():
            here = self._commanded.get(joint, self._last.get(joint, value))
            lim = self.limits[joint]
            # Like FakeArm: clamp to the limits; a joint outside them may only stay or come back.
            value = min(max(value, min(lim.low, here)), max(lim.high, here))
            goal[joint] = min(max(value, here - step), here + step)
        robot.bus.sync_write("Goal_Position", self._lerobot_values(goal))
        self._commanded.update(goal)
        self._last_write_t = now

    def commanded_joints(self) -> dict[str, float]:
        return dict(self._commanded or self._last)

    def read_health(self) -> dict[str, dict[str, float]]:
        """Per servo: temperature (°C), load (% of max, signed), supply voltage, and its error
        flags (`status`, the Feetech status register; quick job 135's diagnostics). Four short
        bus reads (a few ms); the teleop loop asks every few seconds, to see what 1:1 does."""
        bus = self._require_connected().bus
        temp = bus.sync_read("Present_Temperature", normalize=False, num_retry=1)
        load = bus.sync_read("Present_Load", normalize=False, num_retry=1)
        volts = bus.sync_read("Present_Voltage", normalize=False, num_retry=1)
        try:
            status = bus.sync_read("Status", normalize=False, num_retry=1)
        except Exception:  # an older table, a dropped packet: the rest still counts
            status = {}
        return {
            j: {
                "temp_c": float(temp[j]),
                "load_pct": float(load.get(j, 0)) / 10,  # 0.1 % units
                "volts": float(volts.get(j, 0)) / 10,  # 0.1 V units
            }
            | ({"status": int(status[j])} if j in status else {})
            for j in temp
        }

    def stop(self) -> None:
        """Freeze: hold where the motors are now (torque stays on)."""
        self.stopped = True
        if self._robot is None or not self.allow_motion:
            return
        try:
            here = self.read_measured()
        except (ConnectionError, RuntimeError):
            here = self._commanded
        if here:
            self._robot.bus.sync_write("Goal_Position", self._lerobot_values(here))
            self._commanded = dict(here)

    def resume(self) -> None:
        self.stopped = False
        self._last_write_t = time.monotonic()

    def close(self) -> None:
        if self._robot is not None:
            self._robot.bus.disconnect(disable_torque=self.allow_motion)
            self._robot = None

    @property
    def limp_on_close(self) -> bool:
        """Closing switches the torque off (when it may move): a lifted arm drops. The hub's
        "Shut down lab-os" warns about it (quick job 6)."""
        return self._robot is not None and self.allow_motion

    def port_present(self) -> bool:
        """Is the arm's /dev/serial/by-id/ name still there? (gone within a moment of unplugging)"""
        return self._port is not None and os.path.exists(self._port)

    def drop(self) -> None:
        """The USB went: close the port without writing to the motors (they can't be reached).
        `connect()` opens it again once it's back."""
        robot, self._robot = self._robot, None
        self._commanded = {}
        if robot is None:
            return
        try:
            robot.bus.disconnect(disable_torque=False)  # only closes the port
        except Exception as e:
            log.warning("%s: closing the port: %s", self.name, e)

    def _lerobot_values(self, joints: dict[str, float]) -> dict[str, float]:
        return {j: _to_lerobot(j, v - self.offsets.get(j, 0.0)) for j, v in joints.items()}

    def _require_connected(self):
        if self._robot is None:
            raise RuntimeError(f"{self.name} is not connected")
        return self._robot


def watch(arm: SO101Arm, hz: float = 10.0) -> None:
    """Print the joints live until Ctrl+C (move the limp arm by hand to check directions)."""
    print("watching (read-only): move a joint by hand; Ctrl+C to stop")
    print("  ".join(f"{j[:13]:>13}" for j in arm.joint_names))
    try:
        while True:
            try:
                joints = arm.read_measured()
                sys.stdout.write("\r" + "  ".join(f"{joints[j]:+13.1f}" for j in arm.joint_names))
                sys.stdout.flush()
            except (ConnectionError, RuntimeError):
                pass  # a dropped packet: the next reading comes in 1/hz s
            time.sleep(1 / hz)
    except KeyboardInterrupt:
        print()


def main() -> None:
    """Read-only check: uv run --extra so101 python -m lab_os.robots.so101 [--watch] [arm name]
    (joint positions + reads/second, or --watch: live until Ctrl+C; nothing is written to the
    motors)."""
    args = [a for a in sys.argv[1:] if a != "--watch"]
    arm = SO101Arm(name=args[0] if args else default_device(("so101",)))
    try:
        arm.connect()
    except (PortNotAllowed, LookupError, KeyError) as e:
        raise SystemExit(f"Not opening anything: {e}") from None
    except RuntimeError as e:
        raise SystemExit(str(e)) from None
    if arm.calibration_source:
        print(
            f"calibration: lab-os's copy of {arm.calibration_source} (the training one; "
            "the motors hold it)"
        )
    if "--watch" in sys.argv:
        try:
            watch(arm)
        finally:
            arm.close()
        return
    try:
        print("joints (deg):", {j: round(v, 1) for j, v in arm.read_measured().items()})
        print("limits (deg):", {j: (round(v.low), round(v.high)) for j, v in arm.limits.items()})
        n, failed, t0 = 0, 0, time.perf_counter()
        while time.perf_counter() - t0 < 3:
            try:
                arm.read_measured()
                n += 1
            except (ConnectionError, RuntimeError):
                failed += 1
        print(f"{n / (time.perf_counter() - t0):.0f} reads/s, {failed} failed")
    finally:
        arm.close()


if __name__ == "__main__":
    main()
