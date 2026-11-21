"""`uv run lab-os-teleop serve|replay`: the teleop program (fake arm, or a real one via --arm)."""

import argparse
import asyncio
import contextlib
import logging
import shutil
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from aiohttp import web

from lab_os import REPO_ROOT, config, term
from lab_os.devices import PortNotAllowed, load_registry, plugged_in_arms, table_z_cm
from lab_os.kinematics import kinematics_for
from lab_os.robots.base import Arm
from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.teleop.mapping import MODES, ClutchMapper, MappingConfig
from lab_os.teleop.messages import JointFrame, parse_frame, parse_joint_frame
from lab_os.teleop.recording import Recorder, replay
from lab_os.teleop.server import SHUTDOWN, create_app
from lab_os.venues import Venue, load_venue

log = logging.getLogger(__name__)

PRINT_HZ = 10
STOP_WAIT_S = 1.0  # a request still running when the server stops gets this long (quick job 44)

HEALTH_DIR = REPO_ROOT / "logs" / "servo-health"  # what 1:1 does to the servos (not in git)


def _fmt_hand(c) -> str:
    if c is None:
        return "no controller"
    if not c.tracked:
        return "tracking lost"
    x, y, z = c.pos
    btns = "".join(name[0].upper() if on else "·" for name, on in c.buttons.items())
    return f"pos {x:+.2f} {y:+.2f} {z:+.2f}  grip {c.grip:.2f}  trig {c.trigger:.2f}  [{btns}]"


def _fmt_status(loop: TeleopLoop) -> str:
    frame = loop.inputs.latest
    if isinstance(frame, JointFrame):
        moving = " ".join(f"{j} {r:+.2f}" for j, r in frame.rates.items()) or "nothing pressed"
        source = f"keys/mouse: {moving}"
    else:
        hand = frame.hands.get(loop.mapper.config.hand) if frame else None
        source = f"{loop.mapper.config.hand}: {_fmt_hand(hand)}"
    state = (
        "FROZEN"
        if loop.frozen
        else "CLUTCH"
        if loop.mapper.engaged
        else "released"
        if loop.inputs.connected
        else "waiting"
    )
    joints = " ".join(f"{v:+6.1f}" for v in loop.arm.read_joints().values())
    return f"{source} | {state:8} | arm {joints}"


def _make_printer(out=sys.stdout):
    """The live status line: redrawn in place at most PRINT_HZ times a second, only when it
    changed, cut to the terminal's width (a wrapped line can't be redrawn with \r, so every
    redraw would add lines). Nothing when the output isn't a terminal (a log file)."""
    last, shown = 0.0, ""

    def on_tick(loop: TeleopLoop) -> None:
        nonlocal last, shown
        now = time.monotonic()
        if now - last < 1 / PRINT_HZ or not out.isatty():
            return
        last = now
        width = shutil.get_terminal_size().columns - 1
        text = _fmt_status(loop)[:width]
        if text != shown:
            shown = text
            out.write("\r\033[K" + text)
            out.flush()

    return on_tick


SOFTWARE_ARMS = ("fake", "fake-xarm1")  # built in, at every place
DRIVERS = {"so101": "SO-101 (LeRobot: uv sync --extra so101)", "xarm1s": "xArm 1S (USB HID)"}


def _make_arm(name: str, venue) -> Arm:
    if name == "fake":
        return FakeArm()
    if name == "fake-xarm1":  # software xArm: same model, limits and IK as the real one
        from lab_os.robots.xarm import XArm

        x = XArm()
        home = dict.fromkeys(x.joint_names, 0.0) | {"elbow_flex": 70.0, "wrist_flex": 30.0}
        return FakeArm(
            name="fake-xarm1", model=x.model, limits=x.limits, joints=home | {"gripper": 30.0}
        )
    device = load_registry().devices.get(name)
    if device is None or device.off_limits or device.kind not in DRIVERS:
        usable = [  # a borrowed arm (the lab's green one, at every place) only where it's active
            d.name
            for d in load_registry().devices.values()
            if d.kind in DRIVERS
            and not d.off_limits
            and (not d.borrowed or d.name in venue.active_devices)
        ]
        raise SystemExit(
            f"--arm {name}: not an arm lab-os can drive here. Choose {', '.join(SOFTWARE_ARMS)} "
            f"or an arm from devices.yaml: {', '.join(usable) or 'none listed'}"
        )
    if name not in venue.active_devices:
        raise SystemExit(f"{name} is not active in venue {venue.name!r} (venues/)")
    if not venue.motion_allowed:
        raise SystemExit(f"venue {venue.name!r} doesn't allow motion")
    if device.kind == "so101":
        from lab_os.robots.so101 import SO101Arm

        return SO101Arm(name=name, allow_motion=True)
    from lab_os.robots.xarm import XArm

    return XArm(name=name, device_name=name, allow_motion=True)


def use_config(args) -> None:
    """Switch to the place in --config (loads its .env); a clear message instead of a traceback."""
    try:
        folder = config.use(args.config)
        config.load_place()
    except config.ConfigError as e:
        raise SystemExit(str(e)) from None
    if not config.is_default():
        print(f"config: {folder}")


def teleop_floor_m(venue, arm_name: str) -> float:
    """The venue's floor (cm above the table) in the arm's own heights (m), which the mapper uses:
    an arm on a plate (table_z_cm < 0) gets a lower one (quick job 28)."""
    return (venue.floor_cm + table_z_cm(arm_name)) / 100


LEFT_FAKE = "fake-left"  # `--left-arm fake`: a second software SO-101, by its own name


def _open_arm(option: str, name: str, venue) -> Arm:
    """Make and connect the arm `name` (from --arm or --left-arm), or stop with a sentence."""
    arm = FakeArm(name=LEFT_FAKE) if option == "--left-arm" and name == "fake" else None
    arm = arm or _make_arm(name, venue)
    try:
        arm.connect()
    except (PortNotAllowed, LookupError) as e:  # in use by LeLab, unplugged, no calibration file
        raise SystemExit(f"{option} {name}: not opened. {e}") from None
    return arm


def _arm_loop(arm: Arm, venue, speed: float, inputs: InputState, hand: str) -> TeleopLoop:
    """One arm's teleop loop under the venue's caps, following the `hand` controller."""
    kin = kinematics_for(arm.model)
    print(f"mapping: {'IK (hand space)' if kin else 'joint space'} for model {arm.model}")
    table = table_z_cm(arm.name)
    if table:
        print(f"{arm.name} stands {-table:g} cm above the table: heights measured from the table")
    return TeleopLoop(
        arm=arm,
        inputs=inputs,
        mapper=ClutchMapper(
            config=MappingConfig(hand=hand, floor_m=teleop_floor_m(venue, arm.name)),
            kinematics=kin,
        ),
        speed_scale=speed,
        max_speed_scale=venue.speed_cap_scale,
        one_to_one_deg_per_s=venue.one_to_one_cap,
        # real servos: temperature, load and voltage every 5 s, one file per run (not in git)
        health_log=HEALTH_DIR / f"{datetime.now():%Y-%m-%d_%H%M%S}_{arm.name}.jsonl"
        if hasattr(arm, "read_health")
        else None,
    )


def make_loop(args) -> TeleopLoop:
    """The teleop loop for the arm, venue and speed in `args` (see `add_arm_args`). With
    --left-arm: two arms at once, the right controller drives --arm and the left one the other
    (`TeleopLoop.left`)."""
    try:
        venue = load_venue(args.venue)
    except config.ConfigError as e:
        raise SystemExit(str(e)) from None
    args.auto_arm = (
        args.arm is None
    )  # no --arm: an arm plugged in later is taken too (quick job 73)
    found = _find_arms(args, venue) if args.auto_arm else set()
    left_name = getattr(args, "left_arm", None)
    if left_name and left_name == args.arm and not args.arm.startswith("fake"):
        raise SystemExit(f"--left-arm {left_name}: that's --arm too. Choose another arm.")
    # the venue's top speed is where it starts; with the speed cap off, --speed may go higher
    speed = min(args.speed, venue.speed_cap_scale) if args.speed else venue.max_speed_scale
    try:
        arm = _open_arm("--arm", args.arm, venue)
    except SystemExit as e:
        if args.arm not in found:
            raise
        print(f"{e} The fake arm instead.")  # found, but busy or not set up: the brain still starts
        args.arm = "fake"
        arm = _open_arm("--arm", args.arm, venue)
    try:
        left = _open_arm("--left-arm", left_name, venue) if left_name else None
    except SystemExit as e:
        if left_name in found:
            print(f"{e} One arm only.")
            args.left_arm = left = None
        else:
            arm.close()  # the first arm is open already: let go of it before stopping
            raise
    print(
        f"venue {venue.name}: speed scale {speed}, arm: {arm.name} "
        f"(joints: {', '.join(arm.joint_names)})"
    )
    if left:
        print(f"two arms: the right controller drives {arm.name}, the left one {left.name}")
    if any_real_arm(args):
        print("REAL ARM: it moves only while the clutch is held; Esc / release = freeze.")
    if venue.limits_off:
        off = ", ".join(venue.limits_off)
        print(f"LIMITS OFF in venue {venue.name}: {off} (Settings → Safety Limits and Shut Down)")
    inputs = InputState()  # shared: one input page, one dead-man rule for both arms
    loop = _arm_loop(arm, venue, speed, inputs, hand="right")
    loop.on_tick = None if args.quiet else _make_printer()
    if left:
        loop.left = _arm_loop(left, venue, speed, inputs, hand="left")
        loop.left.is_left = True
    return loop


def arm_finder() -> Callable[[TeleopLoop, Venue], TeleopLoop | None]:
    """An SO-101 plugged in after the brain started on the fake arm (quick job 73): the same
    rules as at the start (`plugged_in_arms`: never a borrowed arm, the green set). The finder
    returns a loop for the first one that opens (the brain then `adopt`s it), or None. A plugged-in
    arm that won't open (LeLab has it, no calibration) is said once per reason."""
    said: dict[str, str] = {}

    def find(loop: TeleopLoop, venue: Venue) -> TeleopLoop | None:
        try:
            here = plugged_in_arms(load_registry(), venue.active_devices)
        except config.ConfigError:
            return None
        for name in set(said) - set(here):
            del said[name]  # unplugged again: say it again next time
        for name in here:
            try:
                arm = _open_arm("--arm", name, venue)
            except SystemExit as e:
                if said.get(name) != str(e):
                    said[name] = str(e)
                    log.warning("%s is plugged in, but %s", name, e)
                continue
            return _arm_loop(arm, venue, loop.speed_scale, loop.inputs, hand="right")
        return None

    return find


def _find_arms(args, venue) -> set[str]:
    """No --arm (quick job 61): the SO-101s plugged in now. One becomes --arm, a second one
    --left-arm (unless --left-arm names one); none: the fake arm. Borrowed arms (the green set)
    only when named. Sets args.arm (and args.left_arm) and returns the names it found."""
    left = getattr(args, "left_arm", None)
    try:
        here = plugged_in_arms(load_registry(), venue.active_devices)
    except config.ConfigError as e:
        print(f"No arm looked for ({e}): the fake arm.")
        here = []
    here = [n for n in here if n != left]
    if not here:
        print("No arm plugged in: the fake arm (--arm names one).")
        args.arm = "fake"
        return set()
    args.arm = here[0]
    if len(here) == 1 and not left:
        # two arms without naming them (the builder, 2026-11-21): the green set as the left arm
        # beside another arm, never alone (so the AI tools never drive it unasked). Its port is
        # checked when it opens: another program using it (LeLab, a run) means one arm only.
        with contextlib.suppress(config.ConfigError):
            here += plugged_in_arms(load_registry(), venue.active_devices, borrowed=True)[:1]
    if len(here) > 1 and not left:
        args.left_arm = here[1]
    used = [args.arm] + ([args.left_arm] if len(here) > 1 and not left else [])
    print(
        f"Plugged in: {', '.join(here)}. Driving {' and '.join(used)} (--arm fake: the fake arm)."
    )
    return set(used)


def close_arms(loop: TeleopLoop) -> None:
    """Let go of the arm: stop, then close; then the left arm the same way, even if the first
    one failed."""
    try:
        loop.arm.stop()
        loop.arm.close()
    finally:
        if loop.left:
            loop.left.arm.stop()
            loop.left.arm.close()


def any_real_arm(args) -> bool:
    """--arm or --left-arm is a real arm (not a software one)."""
    names = [args.arm, getattr(args, "left_arm", None)]
    return any(n and not n.startswith("fake") for n in names)


async def serve(
    app: web.Application,
    port: int,
    extra=None,
    host: str = "127.0.0.1",
    banner: str = "",
    after_start=None,
) -> None:
    """Run `app` until `extra` finishes (or forever, or until the app's shutdown event is set:
    the hub's "Shut down lab-os"). The default host is localhost only: a secure context for
    WebXR, and nothing else on the network can connect. `after_start()` runs once it listens
    (lab-os serve --open: the browser)."""
    # shutdown_timeout: a request still running when it stops (a chat answer streaming) gets
    # this long, then it's cancelled. aiohttp's default, 60 s, kept lab-os up ~30 s (quick job 44).
    runner = web.AppRunner(app, access_log=None, shutdown_timeout=STOP_WAIT_S)
    await runner.setup()
    try:
        await web.TCPSite(runner, host, port).start()
    except OSError as e:  # e.g. another brain already runs on this port
        await runner.cleanup()
        raise SystemExit(
            f"Port {port} is in use ({e.strerror}): is another lab-os already running? Stop it "
            f"(Ctrl+C in its terminal), or use another port: --port {port + 10}"
        ) from None
    print(
        banner or f"XR page:  http://localhost:{port}/\nMonitor:  http://localhost:{port}/monitor"
    )
    if after_start:
        after_start()
    try:
        if extra:
            await extra
        else:
            await app.get(SHUTDOWN, asyncio.Event()).wait()
    finally:
        await runner.cleanup()


async def _feed_replay(loop: TeleopLoop, path: Path, speed: float, repeat: bool) -> None:
    async for msg in replay(path, speed=speed, loop=repeat):
        if msg.get("type") == "xr_input":
            loop.inputs.update(parse_frame(msg))
        elif msg.get("type") == "joint_input":
            loop.inputs.update(parse_joint_frame(msg))
        elif msg.get("type") == "session_end":
            loop.inputs.disconnect()
        elif msg.get("type") == "set_speed":
            loop.set_speed(float(msg["speed_scale"]))
        elif msg.get("type") == "set_mode":
            loop.set_mode(str(msg["mode"]))
    loop.inputs.disconnect()
    await asyncio.sleep(0.5)  # let the loop register the end (freeze) before exiting
    print("\nreplay finished")


def add_arm_args(parser: argparse.ArgumentParser) -> None:
    """--config, --venue, --quiet, --arm, --speed: shared by `lab-os-teleop` and `lab-os serve`."""
    parser.add_argument(
        "--config",
        help="this place's config folder (default: $LAB_OS_CONFIG, else lab-os's own config/); "
        "docs/dev/places.md",
    )
    parser.add_argument(
        "--venue", help="venue profile (default: $LAB_OS_VENUE, else `venue` in place.yaml)"
    )
    parser.add_argument("--quiet", action="store_true", help="don't print the live status line")
    parser.add_argument(
        "--arm",
        help="which arm to drive: fake (software SO-101), fake-xarm1 (software xArm), or a real "
        "arm's name from devices.yaml (an SO-101 needs `uv sync --extra so101` and a calibration). "
        "Default: lab-os serve drives the SO-101s plugged in (not the borrowed green set), else "
        "the fake arm; lab-os-teleop the fake arm",
    )
    parser.add_argument(
        "--left-arm",
        help="two arms at once (preview): the left controller drives this arm and the right one "
        "--arm. fake = a second software SO-101 (docs/guides/quest-setup.md → Two arms at once)",
    )
    parser.add_argument(
        "--speed", type=float, help="speed scale, capped at the venue's max_speed_scale"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="lab-os-teleop", description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    add_arm_args(parser)
    parser.set_defaults(arm="fake")  # only `lab-os serve` finds the arms plugged in (quick job 61)
    sub = parser.add_subparsers(dest="command", required=True)

    serve_cmd = sub.add_parser("serve", help="serve the XR page and drive the fake arm live")
    serve_cmd.add_argument("--record", type=Path, help="save incoming input to this .jsonl file")

    rep = sub.add_parser("replay", help="drive the fake arm from a recording")
    rep.add_argument("file", type=Path)
    rep.add_argument("--speed", type=float, default=1.0)
    rep.add_argument("--loop", action="store_true", help="repeat forever")
    rep.add_argument(
        "--mode",
        choices=MODES,
        help="hand → arm mode to start in (a set_mode in the recording still switches it)",
    )

    args = parser.parse_args(argv)
    term.setup_logging()
    use_config(args)
    loop = make_loop(args)

    if args.command == "serve":
        recorder = Recorder(args.record) if args.record else None
        if recorder:
            print(f"recording to {args.record}")
        coro = serve(create_app(loop, recorder), args.port)
    else:
        if args.mode:
            loop.set_mode(args.mode)
        app = create_app(loop, accept_input=False)
        coro = serve(app, args.port, _feed_replay(loop, args.file, args.speed, args.loop))

    try:
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(coro)
    finally:
        close_arms(loop)
    print()


run = term.exit_in_red(main)  # the `lab-os-teleop` command; tests call main()

if __name__ == "__main__":
    run()
