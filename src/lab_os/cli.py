"""`uv run lab-os serve`: the brain. Serves the hub at http://localhost:8080/ with the teleop
pages inside it, and drives the SO-101s plugged in (or the arm --arm names; the fake arm when
none is)."""

import argparse
import asyncio
import contextlib
import os
import socket
import sys
from pathlib import Path

from lab_os import brainlog, config, term
from lab_os.devices import load_registry
from lab_os.hub import launch, tls
from lab_os.hub.hub_devices import DeviceError, clean_name
from lab_os.hub.internet import InternetCheck
from lab_os.hub.server import HTTPS_PORT, RESTART, create_brain_app
from lab_os.personas import current_persona, load_persona
from lab_os.quest_view import AdbReverse
from lab_os.robots.raspbot import from_registry as raspbot_from_registry
from lab_os.teleop.cli import (
    add_arm_args,
    any_real_arm,
    arm_finder,
    close_arms,
    make_loop,
    serve,
    use_config,
)
from lab_os.teleop.recording import Recorder
from lab_os.teleop.server import SHUTDOWN
from lab_os.tools.mcp_server import DEFAULT_PORT as MCP_PORT
from lab_os.venues import load_venue

LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


def _https(args) -> tuple[int, object] | None:
    """(port, ssl context) for the hub over HTTPS (phones, quick job 124), or None: off, or the
    brain listens on this computer only (no phone reaches it then)."""
    if not args.https_port or args.host in LOCAL_HOSTS:
        return None
    try:
        return args.https_port, tls.server_context()
    except (OSError, ValueError) as e:
        print(f"no HTTPS for phones: the certificate failed ({e})")
        return None


def _banner(port: int, host: str, mcp_port: int, https_port: int = 0) -> str:
    lines = [
        f"Hub:      http://localhost:{port}/",
        f"Teleop:   http://localhost:{port}/teleop   (Quest: docs/guides/quest-setup.md)",
        f"Monitor:  http://localhost:{port}/monitor",
        f"Webcam:   http://localhost:{port}/webcam   (preview; "
        "docs/archive/guides-2026-11-25/webcam-teleop.md)",
    ]
    if mcp_port:
        lines.append(
            f"AI tools: http://127.0.0.1:{mcp_port}/mcp   (MCP, this computer only; "
            "docs/guides/ai-control.md)"
        )
    if host not in LOCAL_HOSTS:
        lines.append(
            f"Other screens: http://<this computer's IP address>:{port}/ "
            "(docs/archive/guides-2026-11-25/hub.md)"
        )
    if https_port:
        lines.append(
            f"Phones:   https://<this computer's IP address>:{https_port}/   (the phone's "
            "remote with its microphone; quick job 124)"
        )
    return "\n".join(lines)


def _addresses(names: list[str], place_names: tuple[str, ...] = ()) -> frozenset[str]:
    """--drive-from names and place.yaml's `drive_from` → IP addresses (looked up once, at
    start). A wrong --drive-from stops the brain; a place.yaml name that isn't found (that device
    is off now) is only said, so the brain still starts (quick job 95)."""
    out = set()
    for name in names:
        try:
            out.add(socket.gethostbyname(name))
        except OSError:
            raise SystemExit(f"--drive-from {name}: no computer by that name here") from None
    for name in place_names:
        try:
            out.add(socket.gethostbyname(name))
        except OSError:
            print(
                f"place.yaml drive_from: {name} is not found now. It cannot drive until a restart."
            )
    return frozenset(out)


def _table_map(args) -> None:
    """`lab-os table-map CAMERA`: one picture of the sheet → the camera's table map + a preview."""
    try:
        import cv2
    except ImportError:
        raise SystemExit(
            "needs OpenCV: run it with uv run --extra so101 lab-os table-map …"
        ) from None
    from lab_os import devices
    from lab_os.tools import table_map
    from lab_os.tools.robot import Refused, grab_frame

    try:
        config.use(args.config)
    except config.ConfigError as e:
        raise SystemExit(str(e)) from None
    origin = tuple(args.origin) if args.origin else table_map.DEFAULT_ORIGIN_CM
    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            raise SystemExit(f"can't read the picture {args.image}")
    else:
        try:
            frame = grab_frame(devices.camera_device(args.camera))
        except (KeyError, LookupError, devices.InUse, devices.PortNotAllowed, Refused) as e:
            raise SystemExit(f"{args.camera}: {e}") from None
    try:
        m = table_map.calibrate(frame, args.camera, origin, args.square_mm)
    except table_map.BoardNotFound as e:
        raise SystemExit(f"No table map: {e}") from None
    path = table_map.save(m)
    _, jpeg = cv2.imencode(".jpg", frame)
    preview = config.logs_dir() / "table-maps" / f"{args.camera}.jpg"
    preview.parent.mkdir(parents=True, exist_ok=True)
    preview.write_bytes(table_map.draw_grid(jpeg.tobytes(), m))
    print(f"Saw {m.corners} of 24 corners; the fit's worst corner is {m.worst_mm} mm off.")
    if not table_map.fit_ok(m):
        print("That's more than 5 mm: is the sheet flat? Check it, then run this again.")
    print(f"Saved {path}.\nLook at {preview}: the red dot should sit at the middle of the arm's")
    print("base, and where the x30 and y+0 lines cross should measure 30 cm straight ahead of it.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="lab-os", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("serve", help="serve the hub + teleop pages and drive the arm")
    s.add_argument("--port", type=int, default=8080)
    s.add_argument(
        "--host",
        default="127.0.0.1",
        help="address to listen on (default: this computer only). 0.0.0.0 lets other screens on "
        "the network open the hub; with a real arm they only watch (and can STOP)",
    )
    s.add_argument(
        "--drive-from",
        action="append",
        default=[],
        metavar="NAME_OR_ADDRESS",
        help="another computer that may drive a real arm too (repeatable; e.g. pi01.iwu.ai.lab or "
        "192.168.7.118). Without it, other screens only watch and STOP",
    )
    s.add_argument(
        "--mcp-port",
        type=int,
        default=MCP_PORT,
        help=f"port of the robot tools for AI tools (MCP, on 127.0.0.1 only; default {MCP_PORT}; "
        "0 = off)",
    )
    s.add_argument(
        "--https-port",
        type=int,
        default=tls.DEFAULT_PORT,
        help="with --host 0.0.0.0: the hub over HTTPS on this port too, so a phone's browser gives "
        f"the microphone (quick job 124; default {tls.DEFAULT_PORT}; 0 = off)",
    )
    s.add_argument(
        "--persona",
        help="who the assistant is (personas/<id>.yaml: lab-assistant, jarvis, …; default: "
        "$LAB_OS_PERSONA, else `persona` in place.yaml, else lab-assistant)",
    )
    add_arm_args(s)
    s.add_argument(
        "--record",
        type=Path,
        help="save the teleop input to this .jsonl file (replay it: lab-os-teleop replay <file>)",
    )
    s.add_argument(
        "--open",
        metavar="DEVICE",
        help="once it runs, open the hub on this computer as that device (e.g. desk), full screen; "
        "if a brain already runs here, bring its hub window to the front, else open the hub (the "
        '"Start lab-os" icon does this)',
    )
    s.add_argument(
        "--status-line",
        action="store_true",
        help="print teleop's live status line (input, clutch, joints) under the log; off by "
        "default: the hub shows the state",
    )
    g = sub.add_parser(
        "green",
        help="start the SO-101 training setup (so101-green + LeLab) after checking the ports; "
        "opens nothing itself (docs/archive/guides-2026-11-25/green-launcher.md)",
    )
    g.add_argument("--wait", action="store_true", help="wait for Enter before closing")
    g.add_argument("--stop", action="store_true", help="stop the LeLab this launcher started")
    n = sub.add_parser(
        "new-place",
        help="write a starter config folder for another place (a home): place.yaml, devices.yaml "
        "with the software arm, venues/home.yaml, .env.example",
    )
    n.add_argument("folder", help="e.g. ~/my-lab-os (outside the repo)")
    i = sub.add_parser(
        "icon",
        help='make the "Start lab-os" icon on this computer (the brain\'s): it starts the brain '
        "and opens the hub as DEVICE. Options after -- go to lab-os serve "
        "(docs/archive/guides-2026-11-25/hub.md → "
        "Devices)",
    )
    i.add_argument("--device", default="desk", help="this computer's device name (default: desk)")
    i.add_argument("serve_args", nargs=argparse.REMAINDER, help="-- --arm so101-white …")
    tm = sub.add_parser(
        "table-map",
        help="calibrate a fixed camera to the table with the printed sheet (models/charuco/), so "
        "its pictures get a cm grid (docs/guides/ai-control.md → Table map)",
    )
    tm.add_argument("camera", help="e.g. so101-white-cam-stand (names in devices.yaml)")
    tm.add_argument(
        "--origin",
        nargs=2,
        type=float,
        metavar=("X_CM", "Y_CM"),
        default=None,
        help="the sheet's 'Board origin' corner from the middle of the arm's base: cm forward, cm "
        "to the left (default 29 5.25: the sheet on Google's outline)",
    )
    tm.add_argument("--square-mm", type=float, default=35.0, help="one printed square (35)")
    tm.add_argument("--image", help="calibrate from this picture instead of the camera")
    tm.add_argument("--config", help="the place's config folder (docs/dev/places.md)")
    qv = sub.add_parser(
        "quest-view",
        help="what the Quest sees, on this computer (scrcpy): --install downloads it into "
        "downloads/scrcpy/, --remove deletes it, --wifi makes it work without the USB cable; "
        "without one, says what's there "
        "(docs/archive/guides-2026-11-25/quest-view.md)",
    )
    qv.add_argument("--install", action="store_true", help="download scrcpy (no sudo)")
    qv.add_argument("--remove", action="store_true", help="delete the downloaded scrcpy")
    qv.add_argument(
        "--wifi",
        action="store_true",
        help="with the headset on USB: switch its adb to Wi-Fi (adb tcpip 5555), so Quest view "
        "also works without the cable until the headset restarts",
    )
    rm = sub.add_parser(
        "room",
        help="set up the room: open each page of room.yaml on its device (the running brain does "
        'it, as "Open on…"; docs/archive/guides-2026-11-25/hub.md → Devices)',
    )
    rm.add_argument("--port", type=int, default=8080, help="the brain's port (default 8080)")
    lg = sub.add_parser(
        "logs",
        help="print the brain's log from its file (the last entries, or --at a time): what the "
        "terminal said, kept for a few days (quick job 85)",
    )
    lg.add_argument(
        "--at",
        metavar="TIME",
        help='the minutes around this time: 18:14 (the last 18:14) or "2026-11-21 18:14"',
    )
    lg.add_argument("--config", help="the place's config folder (docs/dev/places.md)")
    rb = sub.add_parser(
        "raspbot",
        help="deploy: copy lab-os's program to the Raspbot and (re)start it there; the car does "
        "not move (docs/guides/raspbot.md)",
    )
    rb.add_argument("action", choices=["deploy"])
    rb.add_argument("--to", default="raspbot1", help="the Raspbot's ssh name (default raspbot1)")
    us = sub.add_parser(
        "usb",
        help="list every USB device under its USB controller, with its lab-os name (Linux; "
        "docs/guides/plug-in.md)",
    )
    us.add_argument("--config", help="the place's config folder (docs/dev/places.md)")
    ma = sub.add_parser(
        "measure-arm",
        help="measure an SO-101's height error by hand, read only (jaw tips on the table), and "
        "write its shoulder offset and table height to devices.yaml (quick job 121)",
    )
    ma.add_argument("arm", help="the arm's name, e.g. so101-green")
    ma.add_argument("--config", help="the place's config folder (docs/dev/places.md)")
    args = parser.parse_args(argv)
    if args.command == "measure-arm":
        from lab_os.robots import measure_arm

        use_config(args)
        raise SystemExit(measure_arm.run(args.arm))
    if args.command == "usb":
        from lab_os import usb_map

        use_config(args)
        print(usb_map.report())
        return
    if args.command == "raspbot":
        from lab_os.robots.raspbot import deploy

        raise SystemExit(deploy(args.to))
    if args.command == "logs":
        return _logs(args)
    if args.command == "room":
        return _room(args.port)
    if args.command == "quest-view":
        from lab_os import quest_view

        try:
            print(quest_view.main(args.install, args.remove, args.wifi))
        except (quest_view.QuestViewError, OSError) as e:
            raise SystemExit(str(e)) from None
        return
    if args.command == "table-map":
        return _table_map(args)
    if args.command == "icon":
        return _icon(args)
    if args.command == "green":
        from lab_os import green

        if args.stop:
            print(green.stop_lelab())
            return
        raise SystemExit(green.main(wait=args.wait))
    if args.command == "new-place":
        try:
            folder = config.new_place(args.folder)
        except config.ConfigError as e:
            raise SystemExit(str(e)) from None
        print(f"Wrote {folder}. Edit place.yaml (the name), then: lab-os serve --config {folder}")
        return

    after_start = None
    if args.open:
        try:
            device = clean_name(args.open)
        except DeviceError as e:
            raise SystemExit(f"--open: {e}") from None
        if launch.brain_answers(args.port):  # already running (a second tap on the icon)
            said = launch.bring_to_front(device, args.port) or launch.open_hub(
                launch.hub_url(args.port, device)
            )
            print(f"lab-os already runs here: {said}")
            return

        def after_start():
            print(launch.open_hub(launch.hub_url(args.port, device)))

    args.quiet = args.quiet or not args.status_line  # the brain's terminal is for its log
    term.setup_logging()
    use_config(args)
    brainlog.log_to_file()  # the terminal's log in a file too, for `lab-os logs` (quick job 85)
    drive_from = _addresses(args.drive_from, config.load_place().drive_from)
    # no --arm: the arms plugged in (quick job 61). Stops with a message if the venue or a named
    # arm doesn't fit this place.
    loop = make_loop(args)
    # a real arm on the network: other screens watch (and can STOP), only this computer drives
    local_control_only = args.host not in LOCAL_HOSTS and any_real_arm(args)
    venue = load_venue(args.venue)
    if args.persona:
        try:
            load_persona(args.persona)  # a typo stops here, not silently as the plain one
        except config.ConfigError as e:
            raise SystemExit(str(e)) from None
    app = create_brain_app(
        loop,
        venue,
        internet=InternetCheck(),
        mcp_port=args.mcp_port or None,
        check_ai=True,
        persona=lambda: current_persona(args.persona, venue.name),
        local_control_only=local_control_only,
        recorder=Recorder(args.record) if args.record else None,
        drive_from=drive_from,
        # no --arm and none plugged in: take an SO-101 plugged in later (quick job 73)
        find_arm=arm_finder() if getattr(args, "auto_arm", False) and args.arm == "fake" else None,
        adb_reverse=AdbReverse(args.port),  # the Quest's browser reaches it by USB (quick job 73)
        raspbot=raspbot_from_registry(load_registry()),  # the Raspbot page's car (quick job 72)
    )
    if args.record:
        print(f"recording teleop input to {args.record}")
    if args.mcp_port and not loop.arm.name.startswith("fake"):
        print(f"AI tools can move the REAL {loop.arm.name}: STOP on any page.")
    if loop.left:
        print(f"AI tools drive {loop.arm.name}; they drive {loop.left.arm.name} when they name it.")
    if args.host not in LOCAL_HOSTS:
        print(f"listening on {args.host}: other computers on the network can open the hub")
    if local_control_only:
        also = f" and {', '.join(sorted(drive_from))}" if drive_from else ""
        arms = loop.arm.name + (f" and {loop.left.arm.name}" if loop.left else "")
        print(f"Other screens are view-only for {arms} (STOP works); drive from here{also}.")
    elif drive_from and args.host in LOCAL_HOSTS:
        print("--drive-from needs --host 0.0.0.0: other computers can't reach the hub yet.")
    try:
        with contextlib.suppress(KeyboardInterrupt):
            https = _https(args)
            app[HTTPS_PORT] = https[0] if https else 0
            banner = _banner(args.port, args.host, args.mcp_port, https[0] if https else 0)
            asyncio.run(
                serve(
                    app,
                    args.port,
                    host=args.host,
                    banner=banner,
                    after_start=after_start,
                    https=https,
                )
            )
    finally:  # Ctrl+C, or "Shut down lab-os" in the hub: the same letting go
        close_arms(loop)
        if not app[RESTART]["asked"]:  # and lab-os's own hub windows close (quick job 64)
            closed = launch.close_hub_windows(args.port)
            if closed:
                print(f"\nclosed lab-os's hub window{'s' if closed > 1 else ''} ({closed})")
    print()
    if app[RESTART]["asked"]:  # Settings' "Restart Now": the same options, without --open
        print(f"lab-os is restarting ({loop.arm.name} was let go); it starts again now.")
        os.execv(sys.executable, [sys.executable, "-m", "lab_os.cli", *_without_open(sys.argv[1:])])
    if app[SHUTDOWN].is_set():
        print(f"lab-os was shut down from the hub; {loop.arm.name} was let go.")


def _logs(args) -> None:
    """`lab-os logs`: the brain's log file, the end or the minutes around a time."""
    use_config(args)
    try:
        print(brainlog.show(args.at))
    except ValueError as e:
        raise SystemExit(str(e)) from None


def _room(port: int) -> None:
    """`lab-os room` (quick job 71): the running brain sets up the room; say what it did."""
    import json
    import urllib.request

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/room/setup", data=b"{}", method="POST"
    )
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(json.load(r)["message"])
    except OSError as e:
        raise SystemExit(f"The brain didn't answer on port {port} ({e}): start it first.") from None


def _without_open(argv: list[str]) -> list[str]:
    """The command line again for a restart, minus --open (the pages reload by themselves)."""
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False
        elif a == "--open":
            skip = True
        elif not a.startswith("--open="):
            out.append(a)
    return out


def _icon(args) -> None:
    """`lab-os icon`: the "Start lab-os" icon (Linux), or the command for a shortcut elsewhere."""
    try:
        device = clean_name(args.device)
    except DeviceError as e:
        raise SystemExit(f"--device: {e}") from None
    extra = [a for a in args.serve_args if a != "--"]
    if sys.platform.startswith("linux"):
        path = launch.write_icon(device, extra)
        print(f'Wrote {path}: "Start lab-os" is in the app list (right-click → Add to Favorites).')
        print(f"It runs: {' '.join(launch.start_command(device, extra))}")
    else:
        print("Put this in a shortcut (it starts the brain, then opens the hub as " + device + "):")
        print("  " + " ".join(launch.start_command(device, extra)))


run = term.exit_in_red(main)  # the `lab-os` command; tests call main()

if __name__ == "__main__":
    run()
