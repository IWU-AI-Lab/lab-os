"""SO-101 motor setup and calibration with lab-os's own LeRobot (the optional extra `so101`).

    uv run --extra so101 python -m lab_os.robots.so101_setup setup-motors  # IDs, one at a time
    uv run --extra so101 python -m lab_os.robots.so101_setup check         # all six answer?
    uv run --extra so101 python -m lab_os.robots.so101_setup calibrate     # -> calibration/<arm>/

Add `--arm so101-white-leader` for the leader. Every command opens only that arm's port from
config/devices.yaml, after checking the board's USB serial and waiting for you to type "yes".
Nothing here turns torque on, so no motor moves: setup writes each motor's ID and baud rate,
calibration reads positions while you move the arm by hand. Same steps as the Seeed Studio wiki
(https://wiki.seeedstudio.com/lerobot_so100m_new/) and LeRobot, but never the shared conda env or
LeRobot's cache in ~/.cache/huggingface (calibration files live in calibration/<arm>/ and travel
with the arm).

Borrowed arms (`borrowed: true` in devices.yaml: the green training set) are refused by all three
commands, by name and by board serial: lab-os never changes their motor IDs, baud rate, firmware
or calibration (AGENTS.md).
"""

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path

from lab_os import REPO_ROOT, config
from lab_os.devices import (
    BY_ID_DIR,
    Device,
    PortNotAllowed,
    Registry,
    check_not_in_use,
    default_device,
    load_registry,
    serial_port,
)

CALIBRATION_DIR = REPO_ROOT / "calibration"
MODEL = "sts3215"
# LeRobot's motor IDs for the SO-100/101 (follower and leader alike).
MOTORS = {
    "shoulder_pan": 1,
    "shoulder_lift": 2,
    "elbow_flex": 3,
    "wrist_flex": 4,
    "wrist_roll": 5,
    "gripper": 6,
}
ROLES = {"so101": "follower", "so101-leader": "leader"}
# Which STS3215 goes where. Follower: all six are the same (1/345 gearing). Leader: three gear
# ratios (from the SO-101 build docs; check the label on the motor against the wiki).
LEADER_GEARS = {
    "shoulder_pan": "1/191",
    "shoulder_lift": "1/345",
    "elbow_flex": "1/191",
    "wrist_flex": "1/147",
    "wrist_roll": "1/147",
    "gripper": "1/147",
}
INSTALL_HINT = "LeRobot isn't installed in lab-os's environment. Run:  uv sync --extra so101"

Ask = Callable[[str], str]
Say = Callable[..., None]


# ---- which port, and is it really the white board? --------------------------------------------
def usb_serial_of(port: str, sys_root: Path = Path("/sys")) -> str | None:
    """USB serial number of the adapter behind a serial port, from sysfs (Linux; opens nothing).
    None where unknown (other OS, not a USB device)."""
    tty = os.path.basename(os.path.realpath(port))
    try:
        return (sys_root / "class" / "tty" / tty / "device" / ".." / "serial").read_text().strip()
    except OSError:
        return None


def guarded_port(
    name: str,
    registry: Registry | None = None,
    sys_root: Path = Path("/sys"),
    proc: Path = Path("/proc"),
) -> tuple[Device, str]:
    """The arm's by-id port, after every check that needs no opening: known SO-101, not off
    limits, a by-id path, plugged in, (Linux) the board behind it has the expected serial, and no
    other program has it open (LeLab, a recording, a training run)."""
    registry = registry or load_registry()
    device = registry.devices.get(name)
    if device is None:
        raise KeyError(f"unknown device {name!r}; add it to config/devices.yaml")
    if device.kind not in ROLES and not device.off_limits:
        raise PortNotAllowed(f"{name} is a {device.kind!r}, not an SO-101")
    port = serial_port(name, registry)  # refuses off-limits arms, raw ttyACM names, green's ports
    if not os.path.exists(port):
        raise LookupError(f"{port} isn't there: is {name}'s board plugged in? ls -l {BY_ID_DIR}")
    check_board_serial(port, device, registry, sys_root)
    check_not_in_use(name, [port], proc)
    return device, port


class Borrowed(PortNotAllowed):
    """The motor setup tool was pointed at another project's arm."""


def refuse_borrowed(
    device: Device, port: str, registry: Registry, sys_root: Path = Path("/sys")
) -> None:
    """Raise Borrowed for a borrowed arm, by its devices.yaml entry or by the serial of the board
    behind the port (so another name for the same board doesn't get past)."""
    board = usb_serial_of(port, sys_root)
    serials = {u.serial for u in device.usb if u.serial} | ({board} if board else set())
    if device.borrowed or serials & registry.borrowed_serials():
        raise Borrowed(
            f"{device.name} is borrowed from another project (the SO-101 training set): lab-os "
            "never changes its motor IDs, baud rate, firmware or calibration (AGENTS.md). "
            "Do that in its own project (LeLab)."
        )


def check_board_serial(
    port: str, device: Device, registry: Registry, sys_root: Path = Path("/sys")
) -> None:
    """Second opinion on the by-id name: the serial the kernel reports for the board behind it."""
    actual = usb_serial_of(port, sys_root)
    if actual is None:
        return  # not Linux / not USB: the by-id name check already ran
    if actual in registry.off_limits_serials():
        raise PortNotAllowed(f"{port} leads to an off-limits board ({actual}). Never open it.")
    expected = {u.serial for u in device.usb if u.serial}
    if expected and actual not in expected:
        raise PortNotAllowed(f"{port} leads to board {actual}, but {device.name} is {expected}")


def describe_serial_ports(registry: Registry, by_id_dir: str = BY_ID_DIR) -> list[str]:
    """One line per plugged-in serial device, labeled with its owner from devices.yaml."""
    try:
        names = sorted(os.listdir(by_id_dir))
    except OSError:
        return ["(none)"]
    lines = []
    for entry in names:
        owner = next(
            (
                d
                for d in registry.devices.values()
                if os.path.join(by_id_dir, entry) in d.ports
                or any(u.serial and u.serial in entry for u in d.usb)
            ),
            None,
        )
        if owner is None:
            label = "unknown"
        elif owner.off_limits:
            label = f"{owner.name}  OFF LIMITS (won't be opened)"
        elif owner.borrowed:
            label = f"{owner.name}  (borrowed: no setup or calibration)"
        else:
            label = owner.name
        lines.append(f"{entry}  ->  {label}")
    return lines


def confirm(device: Device, port: str, registry: Registry, ask: Ask = input, say: Say = print):
    """Show what's plugged in and which port is about to open; True only on a typed "yes"."""
    say(f"Serial devices plugged in now ({BY_ID_DIR}):")
    for line in describe_serial_ports(registry):
        say("  " + line)
    say(f"\nAbout to open {device.name}'s port:\n  {port}\n  (= {os.path.realpath(port)})")
    return ask('Type "yes" to open it: ').strip().lower() == "yes"


# ---- LeRobot (optional extra, imported late) --------------------------------------------------
def _require_lerobot() -> None:
    # Belt and braces: anything LeRobot writes by default lands in our folder, never in the
    # training project's ~/.cache/huggingface calibration cache.
    os.environ["HF_LEROBOT_CALIBRATION"] = str(CALIBRATION_DIR)
    try:
        import lerobot  # noqa: F401
    except ImportError as e:
        raise SystemExit(INSTALL_HINT) from e


def make_bus(port: str):
    """A LeRobot Feetech bus for the six SO-101 motors (not connected yet)."""
    from lerobot.motors import Motor, MotorNormMode
    from lerobot.motors.feetech import FeetechMotorsBus

    norm = MotorNormMode.RANGE_M100_100
    return FeetechMotorsBus(port, {j: Motor(i, MODEL, norm) for j, i in MOTORS.items()})


# ---- motor setup (IDs + baud rate) ------------------------------------------------------------
def find_motors(bus) -> dict[int, dict[int, int]]:
    """Baud rate -> {motor ID: model number} for every motor that answers (broadcast ping)."""
    found = {}
    try:
        for baud in bus.available_baudrates:
            bus.set_baudrate(baud)
            answers = bus.broadcast_ping()
            if answers:
                found[baud] = dict(answers)
    finally:
        bus.set_baudrate(bus.default_baudrate)
    return found


def setup_one(bus, joint: str) -> str:
    """Give the ONLY motor on the bus `joint`'s ID and the default baud rate."""
    found = [(b, i, m) for b, ids in find_motors(bus).items() for i, m in ids.items()]
    if not found:
        raise RuntimeError("no motor answers: is its cable in and the board's power supply on?")
    if len(found) > 1:
        seen = ", ".join(f"ID {i} @ {b}" for b, i, _ in found)
        raise RuntimeError(f"more than one motor answers ({seen}); plug in only the {joint} motor")
    baud, old_id, model = found[0]
    if model != bus.model_number_table[MODEL]:
        raise RuntimeError(f"motor model number {model}, expected {MODEL} (STS3215)")
    target = MOTORS[joint]
    bus.setup_motor(joint, initial_baudrate=baud, initial_id=old_id)
    if bus.ping(target) is None:
        raise RuntimeError(f"written, but the motor doesn't answer as ID {target}; try again")
    return f"ID {old_id} @ {baud} baud  ->  ID {target} @ {bus.default_baudrate} baud"


def setup_motors(bus, role: str = "follower", ask: Ask = input, say: Say = print) -> dict:
    """Walk through the six motors one at a time (gripper first, like LeRobot and the wiki).
    Returns joint -> what happened. Nothing moves: only ID and baud rate are written."""
    say("Motor setup: each motor gets its ID, one at a time. Nothing moves.")
    say("Keep the board's power supply and USB connected; swap only the motor cable.")
    results: dict[str, str] = {}
    for n, joint in enumerate(reversed(MOTORS), 1):
        gear = f", gear {LEADER_GEARS[joint]}" if role == "leader" else ""
        say(f"\n[{n}/6] {joint}  ->  ID {MOTORS[joint]}{gear}")
        say(f"  Plug ONLY the {joint} motor into the controller board (unplug the previous one).")
        while True:
            answer = ask("  Enter = set it up, s = skip, q = quit: ").strip().lower()
            if answer == "q":
                say("\nStopped.")
                _summary(results, say)
                return results
            if answer == "s":
                results[joint] = "skipped"
                break
            try:
                results[joint] = setup_one(bus, joint)
            except Exception as e:  # serial errors, two motors, wrong model: say so and retry
                say(f"  ✗ {e}")
                continue
            say(f"  ✓ {results[joint]}")
            break
    _summary(results, say)
    say("\nNext: write the ID on each motor, assemble the arm (daisy-chained), then `check`.")
    return results


def _summary(results: dict[str, str], say: Say) -> None:
    say("\nSummary:")
    for joint in reversed(MOTORS):
        say(f"  {joint:<14} {results.get(joint, 'not done')}")


def check_motors(bus, say: Say = print) -> bool:
    """With the whole arm chained: does every ID answer at the default baud rate? Read-only."""
    found = find_motors(bus)
    at_default = found.pop(bus.default_baudrate, {})
    for joint, motor_id in MOTORS.items():
        ok = motor_id in at_default
        say(f"  {'✓' if ok else '✗'} {joint:<14} ID {motor_id}")
    extra = sorted(set(at_default) - set(MOTORS.values()))
    if extra:
        say(f"  ! unexpected IDs at {bus.default_baudrate} baud: {extra}")
    for baud, ids in found.items():
        say(f"  ! IDs {sorted(ids)} answer at {baud} baud: not set up yet?")
    return set(at_default) == set(MOTORS.values()) and not found


# ---- calibration ------------------------------------------------------------------------------
CALIBRATION_STEPS = """
Calibration (LeRobot's own steps; nothing moves, torque stays off the whole time):
  1. Move the arm BY HAND to the middle of every joint's range (the wiki's photo: upper arm and
     forearm at right angles, wrist straight, gripper half open), then press Enter.
     -> each motor's "middle" is stored in the motor (homing offset).
  2. Move every joint except wrist_roll slowly through its WHOLE range, one after the other;
     a live table shows min/max. Press Enter when done.
     -> the ranges are written to the motors and to {path}
If that file already exists, Enter re-uses it (writes it to the motors); "c" calibrates anew.
"""


def arm_class_and_config(device: Device, port: str):
    """LeRobot's class + config for this arm, with our id and calibration folder."""
    if ROLES[device.kind] == "follower":
        from lerobot.robots.so_follower import SO101Follower as cls
        from lerobot.robots.so_follower import SO101FollowerConfig as config_cls
    else:
        from lerobot.teleoperators.so_leader import SO101Leader as cls
        from lerobot.teleoperators.so_leader import SO101LeaderConfig as config_cls
    return cls, config_cls(port=port, id=device.name, calibration_dir=CALIBRATION_DIR / device.name)


def calibrate(device: Device, port: str) -> None:
    """Run LeRobot's calibration without its connect(): that would also write the PID settings
    and switch torque on. Here the bus only opens (checks all six motors answer), calibrate()
    switches torque off first, and the port closes with torque off. Never a borrowed arm."""
    if device.borrowed:
        raise Borrowed(f"{device.name} is borrowed: lab-os never calibrates it (AGENTS.md)")
    cls, config = arm_class_and_config(device, port)
    arm = cls(config)
    arm.bus.connect()
    try:
        arm.calibrate()
    finally:
        arm.bus.disconnect(disable_torque=True)


# ---- command line -----------------------------------------------------------------------------
def main(argv: list[str] | None = None, ask: Ask = input, say: Say = print) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m lab_os.robots.so101_setup",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", choices=["setup-motors", "check", "calibrate"])
    parser.add_argument(
        "--arm", help="device name in devices.yaml (default: the place's only SO-101 follower)"
    )
    parser.add_argument("--config", help="this place's config folder (docs/dev/places.md)")
    args = parser.parse_args(argv)

    if args.config:
        config.use(args.config)
    registry = load_registry()
    try:
        name = args.arm or default_device(("so101",), registry)
        if registry.devices.get(name) and registry.devices[name].borrowed:
            # before the port checks: a borrowed arm is refused even when it's busy or unplugged
            refuse_borrowed(registry.devices[name], "", registry)
        device, port = guarded_port(name, registry)
        refuse_borrowed(device, port, registry)
    except (KeyError, LookupError, PortNotAllowed) as e:
        say(f"Not opening anything: {e}")
        return 1
    _require_lerobot()
    if args.command == "calibrate":
        say(CALIBRATION_STEPS.format(path=CALIBRATION_DIR / device.name / f"{device.name}.json"))
    if not confirm(device, port, registry, ask, say):
        say("Not opened.")
        return 1

    if args.command == "calibrate":
        calibrate(device, port)
        return 0
    bus = make_bus(port)
    bus.connect(handshake=False)
    try:
        if args.command == "check":
            return 0 if check_motors(bus, say) else 1
        setup_motors(bus, ROLES[device.kind], ask, say)
        return 0
    finally:
        bus.disconnect(disable_torque=False)


if __name__ == "__main__":
    sys.exit(main())
