"""`uv run lab-os serve`: the brain. Serves the hub at http://localhost:8080/ with the teleop
pages inside it, and drives the fake arm (or a real one via --arm)."""

import argparse
import asyncio
import contextlib
import logging
import socket
from pathlib import Path

from lab_os import config
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
        f"Designed: http://localhost:{port}/design   (the reveal, preview; docs/hub.md)",
        f"Teleop:   http://localhost:{port}/teleop   (Quest: docs/quest-setup.md)",
        f"Monitor:  http://localhost:{port}/monitor",
        f"Perf:     http://localhost:{port}/perf",
    ]
    if mcp_port:
        lines.append(
            f"AI tools: http://127.0.0.1:{mcp_port}/mcp   (MCP, this computer only; "
            "docs/ai-control.md)"
        )
    if host not in LOCAL_HOSTS:
        lines.append(f"Other screens: http://<this computer's IP address>:{port}/ (docs/hub.md)")
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
        "--status-line",
        action="store_true",
        help="print teleop's live status line (input, clutch, joints) under the log; off by "
        "default: the hub shows the state",
    )
    g = sub.add_parser(
        "green",
        help="start the SO-101 training setup (so101-green + LeLab) after checking the ports; "
        "opens nothing itself (docs/green-launcher.md)",
    )
    g.add_argument("--wait", action="store_true", help="wait for Enter before closing")
    n = sub.add_parser(
        "new-place",
        help="write a starter config folder for another place (a home): place.yaml, devices.yaml "
        "with the software arm, venues/home.yaml, .env.example",
    )
    n.add_argument("folder", help="e.g. ~/my-lab-os (outside the repo)")
    args = parser.parse_args(argv)
    if args.command == "green":
        from lab_os import green

        raise SystemExit(green.main(wait=args.wait))
    if args.command == "new-place":
        try:
            folder = config.new_place(args.folder)
        except config.ConfigError as e:
            raise SystemExit(str(e)) from None
        print(f"Wrote {folder}. Edit place.yaml (the name), then: lab-os serve --config {folder}")
        return

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
            asyncio.run(serve(app, args.port, host=args.host, banner=banner))
    finally:
        loop.arm.stop()
        loop.arm.close()
    print()


if __name__ == "__main__":
    main()
