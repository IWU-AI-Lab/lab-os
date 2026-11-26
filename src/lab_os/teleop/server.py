"""One Python program serves the WebXR page and receives its input over a WebSocket.

GET /teleop      the XR input page (Quest browser or a desktop browser + WebXR emulator);
                 also at GET / for `lab-os-teleop` (`lab-os serve` puts the hub there)
GET /webcam      webcam teleop (preview 2): a bare hand in front of a webcam, same input as the
                 Quest's bare hands (docs/archive/guides-2026-11-25/webcam-teleop.md)
GET /monitor     the list of the Monitor pages: a card for each kind of robot (quick job 147)
GET /monitor/<kind>  live view of the arms of one kind (so101, xarm), for the onlooker screen
GET /static/...  the teleop pages' own scripts
GET /web/...     web files every page shares (vendored libraries, theme.js): src/lab_os/web/
GET /models/...  robot models (URDF + meshes) for the 3D view
GET /theme.json  design tokens from config/theme.yaml
WS  /ws          input page connects here; /ws?role=monitor for watchers

Only one input page drives at a time ("has control"): the first page to send input while control
is free. Others are ignored until the driver releases control (session_end or disconnect); it's
handed over, never grabbed. While the AI tools move the arm (lab_os.tools), they have control and
all teleop input is ignored. Any page, monitors included, can send `stop`; it also ends an AI move,
and with two arms at once (`TeleopLoop.left`) it stops both arms.

`local_control_only` (the brain sets it for a real arm served to the network): input pages from
other computers are watchers, so another screen can show the hub and the arm but only STOP it.
Control stays with this computer (and the Quest over `adb reverse`, which arrives as localhost),
plus the addresses in `drive_from` (`lab-os serve --drive-from pi01`: the builder's own screens).

When the server stops (Ctrl+C, or the hub's "Shut down lab-os"), it closes every page's WebSocket
at once (`close_sockets`), so the program doesn't wait for open pages (quick job 44: ~30 s before).
"""

import asyncio
import json
import logging
import time
from pathlib import Path

from aiohttp import WSCloseCode, WSMsgType, web

from lab_os import REPO_ROOT
from lab_os.teleop.loop import TeleopLoop
from lab_os.teleop.messages import parse_frame, parse_joint_frame
from lab_os.teleop.recording import Recorder
from lab_os.theme import load_theme

WEB_DIR = Path(__file__).parent / "web"
SHARED_WEB_DIR = Path(__file__).parents[1] / "web"
MODELS_DIR = REPO_ROOT / "models"
STATUS_HZ = 10
CLOSE_WAIT_S = 1.0  # at most this long for the pages to answer the close, when the server stops

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
# The pages were told "lab-os is off" (brain_off). Ctrl+C tells them as it stops (quick job 64).
OFF_TOLD = web.AppKey("off_told", dict)
OFF_TELL_S = 0.2  # time for the broadcaster to send brain_off before the sockets close
LOCAL_CONTROL_ONLY = web.AppKey("local_control_only", bool)
NAMES = web.AppKey("names", dict)  # page → its device name, from `hello` (quick job 76)
# page → {"remote", "agent", "device"}: every open teleop page, for the live device list (a Quest
# on Wi-Fi without adb shows by its teleop page, quick job 141)
LINKS = web.AppKey("links", dict)
# a page on another computer that may only watch → its address, for the line that says how to let
# it drive (quick job 95)
WATCHERS = web.AppKey("watchers", dict)
DRIVE_FROM = web.AppKey("drive_from", set)  # other computers' addresses that may drive
# (a set: the Command Center changes it while the brain runs, quick job 134)
LOOPBACK = ("127.0.0.1", "::1")


def is_local(request: web.Request) -> bool:
    """The page runs on this computer (or reaches it through adb reverse)."""
    remote = request.remote or ""
    return remote in LOOPBACK or remote.startswith("::ffff:127.")


async def _page(name: str) -> web.FileResponse:
    return web.FileResponse(WEB_DIR / name)


async def index(_request: web.Request) -> web.FileResponse:
    return await _page("index.html")


async def webcam(_request: web.Request) -> web.FileResponse:
    return await _page("webcam.html")


# The kinds of robot with a Monitor page of their own (quick job 147): kind → its title. A new
# kind is one more entry here and in KINDS (web/arm/kinds.js).
MONITOR_KINDS = {"so101": "SO-101 Monitor", "xarm": "xArm Monitor"}


async def monitor_list(_request: web.Request) -> web.FileResponse:
    return await _page("monitor-list.html")


async def monitor(request: web.Request) -> web.FileResponse:
    if request.match_info["kind"] not in MONITOR_KINDS:
        raise web.HTTPNotFound(text=f"No Monitor page for {request.match_info['kind']!r}.")
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
    if kind == "hello":  # input pages and view-only ones (another screen's Quest) alike
        log.info("input page connected: %s", raw.get("agent", "?"))
        if ws is not None:  # its device name: the other pages say who has control (quick job 76)
            app[NAMES][ws] = str(raw.get("device") or "")[:32]
            if ws in app[LINKS]:
                app[LINKS][ws] |= {
                    "agent": str(raw.get("agent") or "")[:300],
                    "device": app[NAMES][ws],
                }
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
        app[WATCHERS][ws] = request.remote or ""
    if is_input and not app[ACCEPT_INPUT]:
        await ws.send_json({"type": "error", "message": "replay running; live input disabled"})
        await ws.close()
        return ws

    app[CLIENTS].add(ws)
    app[LINKS][ws] = {"remote": request.remote or "", "agent": "", "device": ""}
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
        app[NAMES].pop(ws, None)
        app[LINKS].pop(ws, None)
        app[WATCHERS].pop(ws, None)
        if is_input:
            app[INPUTS].discard(ws)
            _release_control(app, ws)  # dead-man: the driver's connection is gone → freeze
    return ws


async def close_sockets(sockets) -> None:
    """Close these WebSockets now, all together, waiting at most CLOSE_WAIT_S for the pages to
    answer: a stopping server would otherwise wait for every open page (quick job 44). The pages
    were told first (`brain_off`) and reconnect by themselves once the brain is back."""
    closing = [
        asyncio.ensure_future(ws.close(code=WSCloseCode.GOING_AWAY, message=b"lab-os is off"))
        for ws in list(sockets)
        if not ws.closed
    ]
    if closing:
        await asyncio.wait(closing, timeout=CLOSE_WAIT_S)


def brain_off_message(by: str = "", restart: bool = False) -> dict:
    """{"type": "brain_off"}: lab-os is off (or restarting); `by` is the device that asked."""
    msg = {"type": "brain_off", "from": by, "time_ms": round(time.time() * 1000)}
    if restart:
        msg["restart"] = True
    return msg


async def _close_pages(app: web.Application) -> None:
    if not app[OFF_TOLD]["told"]:  # Ctrl+C: the pages say "lab-os is off", not "not reachable"
        app[OFF_TOLD]["told"] = True
        app[OUTBOX].put_nowait(brain_off_message())
        await asyncio.sleep(OFF_TELL_S)
    await close_sockets(app[CLIENTS])


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
                # quick job 76: who drives (its device name), and may this page drive at all
                who = app[NAMES].get(driver, "") if control == "other" else ""
                mine = {"control": control, "driver": who, "may_drive": ws in app[INPUTS]}
                if ws in app[WATCHERS]:  # view-only as another computer: its address
                    mine["address"] = app[WATCHERS][ws]
                await ws.send_str(json.dumps(msg | mine))
            else:
                await ws.send_str(text)


async def _background(app: web.Application):
    app[LOOP].on_command = app[OUTBOX].put_nowait
    tasks = [asyncio.create_task(app[LOOP].run()), asyncio.create_task(_broadcaster(app))]
    if app[LOOP].left:  # two arms at once: its arm_* messages too (pages tell them by `device`)
        app[LOOP].left.on_command = app[OUTBOX].put_nowait
        tasks.append(asyncio.create_task(app[LOOP].left.run()))
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
    app[NAMES] = {}
    app[LINKS] = {}
    app[WATCHERS] = {}
    app[SHUTDOWN] = asyncio.Event()
    app[OFF_TOLD] = {"told": False}
    app[LOCAL_CONTROL_ONLY] = local_control_only
    app[DRIVE_FROM] = set(drive_from)
    if root_page:
        app.router.add_get("/", index)
    app.router.add_get("/teleop", index)
    app.router.add_get("/monitor", monitor_list)
    app.router.add_get("/monitor/{kind}", monitor)
    app.router.add_get("/webcam", webcam)
    app.router.add_get("/theme.json", theme)
    app.router.add_get("/ws", websocket)
    app.router.add_static("/static", WEB_DIR)
    app.router.add_static("/web", SHARED_WEB_DIR)
    app.router.add_static("/models", MODELS_DIR)
    app.cleanup_ctx.append(_background)
    app.on_shutdown.append(_close_pages)
    app.on_response_prepare.append(_no_stale_files)
    return app
