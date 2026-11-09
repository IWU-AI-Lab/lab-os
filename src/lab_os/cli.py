"""`uv run lab-os serve`: the brain. Serves the hub at http://localhost:8080/ with the teleop
pages inside it, and drives the fake arm (or a real one via --arm)."""

import argparse
import asyncio
import contextlib
import logging

from lab_os.hub.internet import InternetCheck
from lab_os.hub.server import create_brain_app
from lab_os.teleop.cli import add_arm_args, make_loop, serve
from lab_os.venues import load_venue

LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


def _banner(port: int, host: str) -> str:
    lines = [
        f"Hub:      http://localhost:{port}/",
        f"Teleop:   http://localhost:{port}/teleop   (Quest: docs/quest-setup.md)",
        f"Monitor:  http://localhost:{port}/monitor",
        f"Perf:     http://localhost:{port}/perf",
    ]
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
    add_arm_args(s)
    args = parser.parse_args(argv)

    if args.host not in LOCAL_HOSTS and not args.arm.startswith("fake"):
        raise SystemExit(
            f"--host {args.host} would let anyone on the network drive {args.arm}; "
            "real arms are served on this computer only (leave out --host)"
        )
    logging.basicConfig(level=logging.INFO, format="\n%(levelname)s %(message)s")
    venue = load_venue(args.venue)
    loop = make_loop(args)
    app = create_brain_app(loop, venue, internet=InternetCheck())
    if args.host not in LOCAL_HOSTS:
        print(f"listening on {args.host}: other computers on the network can open the hub")
    try:
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(serve(app, args.port, host=args.host, banner=_banner(args.port, args.host)))
    finally:
        loop.arm.stop()
        loop.arm.close()
    print()


if __name__ == "__main__":
    main()
