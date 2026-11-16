"""`uv run lab-os serve`: the brain. Serves the hub at http://localhost:8080/ with the teleop
pages inside it, and drives the fake arm (or a real one via --arm)."""

import argparse
import asyncio
import contextlib
import logging
import socket
import sys
from pathlib import Path

from lab_os import config
from lab_os.hub import launch
from lab_os.hub.hub_devices import DeviceError, clean_name
from lab_os.hub.internet import InternetCheck
from lab_os.hub.server import create_brain_app
from lab_os.personas import current_persona, load_persona
from lab_os.teleop.cli import add_arm_args, make_loop, serve, use_config
from lab_os.teleop.recording import Recorder
from lab_os.tools.mcp_server import DEFAULT_PORT as MCP_PORT
from lab_os.venues import load_venue

LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


def _banner(port: int, host: str, mcp_port: int) -> str:
    lines = [
        f"Hub:      http://localhost:{port}/",
        f"Designed: http://localhost:{port}/design   (the reveal, preview; docs/guides/hub.md)",
        f"Teleop:   http://localhost:{port}/teleop   (Quest: docs/guides/quest-setup.md)",
        f"Monitor:  http://localhost:{port}/monitor",
        f"Perf:     http://localhost:{port}/perf",
    ]
    if mcp_port:
        lines.append(
            f"AI tools: http://127.0.0.1:{mcp_port}/mcp   (MCP, this computer only; "
            "docs/guides/ai-control.md)"
        )
    if host not in LOCAL_HOSTS:
        lines.append(
            f"Other screens: http://<this computer's IP address>:{port}/ (docs/guides/hub.md)"
        )
    return "\n".join(lines)


def _addresses(names: list[str]) -> frozenset[str]:
    """--drive-from names → IP addresses (looked up once, at start)."""
    out = set()
    for name in names:
        try:
            out.add(socket.gethostbyname(name))
        except OSError:
            raise SystemExit(f"--drive-from {name}: no computer by that name here") from None
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
        'if a brain already runs here, only open the hub (the "Start lab-os" icon does this)',
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
        "opens nothing itself (docs/guides/green-launcher.md)",
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
        "and opens the hub as DEVICE. Options after -- go to lab-os serve (docs/guides/hub.md → "
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
    args = parser.parse_args(argv)
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
            print(f"lab-os already runs here: {launch.open_hub(launch.hub_url(args.port, device))}")
            return

        def after_start():
            print(launch.open_hub(launch.hub_url(args.port, device)))

    # a real arm on the network: other screens watch (and can STOP), only this computer drives
    local_control_only = args.host not in LOCAL_HOSTS and not args.arm.startswith("fake")
    args.quiet = args.quiet or not args.status_line  # the brain's terminal is for its log
    logging.basicConfig(level=logging.INFO, format="\n%(levelname)s %(message)s")
    use_config(args)
    drive_from = _addresses(args.drive_from)
    loop = make_loop(args)  # stops with a message if the venue or arm doesn't fit this place
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
    )
    if args.record:
        print(f"recording teleop input to {args.record}")
    if args.mcp_port and not args.arm.startswith("fake"):
        print(f"AI tools can move the REAL {args.arm}: each move asks first; STOP on any page.")
    if args.host not in LOCAL_HOSTS:
        print(f"listening on {args.host}: other computers on the network can open the hub")
    if local_control_only:
        also = f" and {', '.join(sorted(drive_from))}" if drive_from else ""
        print(f"Other screens are view-only for {args.arm} (STOP works); drive it from here{also}.")
    elif drive_from and args.host in LOCAL_HOSTS:
        print("--drive-from needs --host 0.0.0.0: other computers can't reach the hub yet.")
    try:
        with contextlib.suppress(KeyboardInterrupt):
            banner = _banner(args.port, args.host, args.mcp_port)
            asyncio.run(
                serve(app, args.port, host=args.host, banner=banner, after_start=after_start)
            )
    finally:
        loop.arm.stop()
        loop.arm.close()
    print()


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


if __name__ == "__main__":
    main()
