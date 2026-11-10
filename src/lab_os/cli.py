"""`uv run lab-os serve`: the brain. Serves the hub at http://localhost:8080/ with the teleop
pages inside it, and drives the fake arm (or a real one via --arm)."""

import argparse
import asyncio
import contextlib
import logging

from lab_os import config
from lab_os.hub.internet import InternetCheck
from lab_os.hub.server import create_brain_app
from lab_os.teleop.cli import add_arm_args, make_loop, serve, use_config
from lab_os.tools.mcp_server import DEFAULT_PORT as MCP_PORT
from lab_os.venues import load_venue

LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


def _banner(port: int, host: str, mcp_port: int) -> str:
    lines = [
        f"Hub:      http://localhost:{port}/",
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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="lab-os", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("serve", help="serve the hub + teleop pages and drive the arm")
    s.add_argument("--port", type=int, default=8080)
    s.add_argument(
        "--host",
        default="127.0.0.1",
        help="address to listen on (default: this computer only). 0.0.0.0 lets other screens on "
        "the network open the hub; only allowed with a fake arm",
    )
    s.add_argument(
        "--mcp-port",
        type=int,
        default=MCP_PORT,
        help=f"port of the robot tools for AI tools (MCP, on 127.0.0.1 only; default {MCP_PORT}; "
        "0 = off)",
    )
    add_arm_args(s)
    n = sub.add_parser(
        "new-place",
        help="write a starter config folder for another place (a home): place.yaml, devices.yaml "
        "with the software arm, venues/home.yaml, .env.example",
    )
    n.add_argument("folder", help="e.g. ~/my-lab-os (outside the repo)")
    args = parser.parse_args(argv)
    if args.command == "new-place":
        try:
            folder = config.new_place(args.folder)
        except config.ConfigError as e:
            raise SystemExit(str(e)) from None
        print(f"Wrote {folder}. Edit place.yaml (the name), then: lab-os serve --config {folder}")
        return

    if args.host not in LOCAL_HOSTS and not args.arm.startswith("fake"):
        raise SystemExit(
            f"--host {args.host} would let anyone on the network drive {args.arm}; "
            "real arms are served on this computer only (leave out --host)"
        )
    logging.basicConfig(level=logging.INFO, format="\n%(levelname)s %(message)s")
    use_config(args)
    loop = make_loop(args)  # stops with a message if the venue or arm doesn't fit this place
    venue = load_venue(args.venue)
    app = create_brain_app(loop, venue, internet=InternetCheck(), mcp_port=args.mcp_port or None)
    if args.mcp_port and not args.arm.startswith("fake"):
        print(f"AI tools can move the REAL {args.arm}: each move asks first; STOP on any page.")
    if args.host not in LOCAL_HOSTS:
        print(f"listening on {args.host}: other computers on the network can open the hub")
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
