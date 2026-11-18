"""One Python program serves the WebXR page and receives its input over a WebSocket.

GET /teleop      the XR input page (Quest browser or a desktop browser + WebXR emulator);
                 also at GET / for `lab-os-teleop` (`lab-os serve` puts the hub there)
GET /monitor     live view of the (fake) arm, for a second tab or the onlooker monitor
GET /classic/teleop, /classic/monitor   the plain versions of both (before the design, 2026-11-10)
GET /static/...  the teleop pages' own scripts
GET /web/...     web files every page shares (vendored libraries, theme.js): src/lab_os/web/
GET /models/...  robot models (URDF + meshes) for the 3D view
GET /theme.json  design tokens from config/theme.yaml
WS  /ws          input page connects here; /ws?role=monitor for watchers

Only one input page drives at a time ("has control"): the first page to send input while control
is free. Others are ignored until the driver releases control (session_end or disconnect); it's
handed over, never grabbed. While the AI tools move the arm (lab_os.tools), they have control and
all teleop input is ignored. Any page, monitors included, can send `stop`; it also ends an AI move.

`local_control_only` (the brain sets it for a real arm served to the network): input pages from
other computers are watchers, so another screen can show the hub and the arm but only STOP it.
Control stays with this computer (and the Quest over `adb reverse`, which arrives as localhost),
plus the addresses in `drive_from` (`lab-os serve --drive-from pi01`: the builder's own screens).
"""

import asyncio
import json
import logging
import time
from pathlib import Path

from aiohttp import WSMsgType, web

from lab_os import REPO_ROOT
from lab_os.teleop.loop import TeleopLoop
from lab_os.teleop.messages import parse_frame, parse_joint_frame
from lab_os.teleop.recording import Recorder
from lab_os.theme import load_theme

WEB_DIR = Path(__file__).parent / "web"
SHARED_WEB_DIR = Path(__file__).parents[1] / "web"
MODELS_DIR = REPO_ROOT / "models"
STATUS_HZ = 10

log = logging.getLogger(__name__)

LOOP = web.AppKey("loop", TeleopLoop)
RECORDER = web.AppKey("recorder", Recorder | None)
ACCEPT_INPUT = web.AppKey("accept_input", bool)
CLIENTS = web.AppKey("clients", set)
INPUTS = web.AppKey("inputs", set)
OUTBOX = web.AppKey("outbox", asyncio.Queue)
# The one input WebSocket that currently drives the arm, or None. A dict so handlers can mutate it.
CONTROL = web.AppKey("control", dict)
# Set to stop the server the way Ctrl+C does (the hub's "Shut down lab-os", quick job 6): `serve()`
# returns, and the command's cleanup lets go of the arm.
SHUTDOWN = web.AppKey("shutdown", asyncio.Event)
LOCAL_CONTROL_ONLY = web.AppKey("local_control_only", bool)
DRIVE_FROM = web.AppKey("drive_from", frozenset)  # other computers' addresses that may drive
LOOPBACK = ("127.0.0.1", "::1")


def is_local(request: web.Request) -> bool:
    """The page runs on this computer (or reaches it through adb reverse)."""
    remote = request.remote or ""
    return remote in LOOPBACK or remote.startswith("::ffff:127.")


async def _page(name: str) -> web.FileResponse:
    return web.FileResponse(WEB_DIR / name)


async def index(_request: web.Request) -> web.FileResponse:
    return await _page("index.html")


async def classic_teleop(_request: web.Request) -> web.FileResponse:
    return await _page("classic/index.html")


async def classic_monitor(_request: web.Request) -> web.FileResponse:
    return await _page("classic/monitor.html")


async def monitor(_request: web.Request) -> web.FileResponse:
    return await _page("monitor.html")


async def _no_stale_files(request: web.Request, response: web.StreamResponse) -> None:
    """Pages and their scripts must always be the current version: without this, Firefox reuses
    old cached scripts for hours (docs/dev/GOTCHAS.md). `no-cache` still allows a cheap 304."""
    if not request.path.startswith("/ws"):
        response.headers.setdefault("Cache-Control", "no-cache")


async def theme(_request: web.Request) -> web.Response:
    """config/theme.yaml as JSON, re-read on every request (edit the file, reload the page)."""
    return web.json_response(load_theme(), headers={"Cache-Control": "no-store"})


def _release_control(app: web.Application, ws) -> None:
    """The driving page let go (or vanished): freeze (dead-man) and free control for others."""
    if app[CONTROL].get("ws") is ws:
        app[CONTROL]["ws"] = None
        app[LOOP].inputs.disconnect()
        log.info("control released")


def handle_message(app: web.Application, raw: dict, ws=None, is_input: bool = True) -> bool:
    """Apply one message from a client. Returns False if it was ignored because another page has
    control (so the caller can tell that page)."""
    loop = app[LOOP]
    kind = raw.get("type")
    if kind == "stop":  # from any page, monitors included
        loop.stop()
        log.info("STOP pressed on a %s page", "input" if is_input else "monitor")
        if app[RECORDER]:
            app[RECORDER].write(raw)
        return True
    if not is_input:
        return True  # monitors can only stop
    if kind in ("xr_input", "joint_input"):
        frame = parse_frame(raw) if kind == "xr_input" else parse_joint_frame(raw)
        control = app[CONTROL]
        if loop.motion_active:
            return False  # the AI tools have control until their move ends
        if control.get("ws") is None:
            control["ws"] = ws
            log.info("control taken by an input page")
        elif control["ws"] is not ws:
            return False
        loop.inputs.update(frame)
        if app[RECORDER]:
            app[RECORDER].write(raw)
    elif kind == "session_end":
        if app[CONTROL].get("ws") is not ws:
            return True  # another page's session ending must not freeze the driver
        _release_control(app, ws)
        if app[RECORDER]:
            app[RECORDER].write(raw)
    elif kind == "set_speed":  # the speed control; any input page on this computer
        speed = loop.set_speed(float(raw["speed_scale"]))
        log.info("speed scale set to %s", speed)
        if app[RECORDER]:
            app[RECORDER].write(raw)
    elif kind == "set_mode":  # hand → arm: relative or 1:1; any input page on this computer
        mode = loop.set_mode(str(raw.get("mode")))
        log.info("teleop mode set to %s", mode)
        if app[RECORDER]:
            app[RECORDER].write(raw)
    elif kind == "hello":
        log.info("input page connected: %s", raw.get("agent", "?"))
    else:
        raise ValueError(f"unknown message type {kind!r}")
    return True


async def websocket(request: web.Request) -> web.WebSocketResponse:
    app = request.app
    ws = web.WebSocketResponse(heartbeat=5.0)
    await ws.prepare(request)
    is_input = request.query.get("role", "input") == "input"
    may_drive = is_local(request) or request.remote in app[DRIVE_FROM]
    if is_input and app[LOCAL_CONTROL_ONLY] and not may_drive:
        is_input = False  # another screen: it watches (and can STOP), it never drives
        await ws.send_json(
            {"type": "error", "message": "view only: the arm is driven from the brain's computer"}
        )
        log.info("input page from %s connected view-only", request.remote)
    if is_input and not app[ACCEPT_INPUT]:
        await ws.send_json({"type": "error", "message": "replay running; live input disabled"})
        await ws.close()
        return ws

    app[CLIENTS].add(ws)
    if is_input:
        app[INPUTS].add(ws)
    bad = 0
    told_busy = False
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            try:
                accepted = handle_message(app, json.loads(msg.data), ws, is_input)
            except (ValueError, TypeError, KeyError) as e:
                bad += 1
                if bad == 1 or bad % 100 == 0:
                    log.warning("ignored bad message (%d so far): %s", bad, e)
                continue
            if not accepted and not told_busy:
                told_busy = True  # once per page; the `control` field in status keeps it current
                who = "the AI tools have" if app[LOOP].motion_active else "another page has"
                await ws.send_json({"type": "error", "message": f"{who} control"})
            elif accepted:
                told_busy = False
    finally:
        app[CLIENTS].discard(ws)
        if is_input:
            app[INPUTS].discard(ws)
            _release_control(app, ws)  # dead-man: the driver's connection is gone → freeze
    return ws


async def _broadcaster(app: web.Application) -> None:
    """The only task writing to clients: each driver command as it happens + status at 10 Hz."""
    period = 1 / STATUS_HZ
    next_status = time.monotonic()
    while True:
        try:
            msg = await asyncio.wait_for(
                app[OUTBOX].get(), timeout=max(0.0, next_status - time.monotonic())
            )
        except TimeoutError:
            next_status = time.monotonic() + period
            try:
                msg = app[LOOP].status()
            except Exception:  # a failing arm read must not end status for every page
                log.exception("status failed")
                continue
        if not app[CLIENTS]:
            continue
        text = json.dumps(msg)
        driver = app[CONTROL].get("ws")
        for ws in list(app[CLIENTS]):
            if ws.closed:
                continue
            if msg["type"] == "status":  # each page learns whether it is the one driving
                if app[LOOP].motion_active:
                    control = "ai"
                else:
                    control = "free" if driver is None else "you" if driver is ws else "other"
                await ws.send_str(json.dumps(msg | {"control": control}))
            else:
                await ws.send_str(text)


async def _background(app: web.Application):
    app[LOOP].on_command = app[OUTBOX].put_nowait
    tasks = [asyncio.create_task(app[LOOP].run()), asyncio.create_task(_broadcaster(app))]
    yield
    for t in tasks:
        t.cancel()
    if app[RECORDER]:
        app[RECORDER].close()


def create_app(
    loop: TeleopLoop,
    recorder: Recorder | None = None,
    accept_input: bool = True,
    root_page: bool = True,
    local_control_only: bool = False,
    drive_from: frozenset[str] = frozenset(),
) -> web.Application:
    """The teleop server. `root_page=False` leaves `/` free (the brain serves the hub there).
    `local_control_only`: only pages on this computer (and from the addresses in `drive_from`)
    may drive (see the module docstring)."""
    app = web.Application()
    app[LOOP] = loop
    app[RECORDER] = recorder
    app[ACCEPT_INPUT] = accept_input
    app[CLIENTS] = set()
    app[INPUTS] = set()
    app[OUTBOX] = asyncio.Queue()
    app[CONTROL] = {"ws": None}
    app[SHUTDOWN] = asyncio.Event()
    app[LOCAL_CONTROL_ONLY] = local_control_only
    app[DRIVE_FROM] = frozenset(drive_from)
    if root_page:
        app.router.add_get("/", index)
    app.router.add_get("/teleop", index)
    app.router.add_get("/monitor", monitor)
    app.router.add_get("/classic/teleop", classic_teleop)  # the plain pages, kept in case
    app.router.add_get("/classic/monitor", classic_monitor)
    app.router.add_get("/theme.json", theme)
    app.router.add_get("/ws", websocket)
    app.router.add_static("/static", WEB_DIR)
    app.router.add_static("/web", SHARED_WEB_DIR)
    app.router.add_static("/models", MODELS_DIR)
    app.cleanup_ctx.append(_background)
    app.on_response_prepare.append(_no_stale_files)
    return app
