"""One Python program serves the WebXR page and receives its input over a WebSocket.

GET /            the XR input page (Quest browser or a desktop browser + WebXR emulator)
GET /monitor     live view of the (fake) arm, for a second tab or the onlooker monitor
GET /models/...  robot models (URDF + meshes) for the 3D view
WS  /ws          input page connects here; /ws?role=monitor for watchers
"""

import asyncio
import json
import logging
import time
from pathlib import Path

from aiohttp import WSMsgType, web

from lab_os import REPO_ROOT
from lab_os.teleop.loop import TeleopLoop
from lab_os.teleop.messages import parse_frame
from lab_os.teleop.recording import Recorder

WEB_DIR = Path(__file__).parent / "web"
MODELS_DIR = REPO_ROOT / "models"
STATUS_HZ = 10

log = logging.getLogger(__name__)

LOOP = web.AppKey("loop", TeleopLoop)
RECORDER = web.AppKey("recorder", Recorder | None)
ACCEPT_INPUT = web.AppKey("accept_input", bool)
CLIENTS = web.AppKey("clients", set)
INPUTS = web.AppKey("inputs", set)
OUTBOX = web.AppKey("outbox", asyncio.Queue)


async def _page(name: str) -> web.FileResponse:
    return web.FileResponse(WEB_DIR / name)


async def index(_request: web.Request) -> web.FileResponse:
    return await _page("index.html")


async def monitor(_request: web.Request) -> web.FileResponse:
    return await _page("monitor.html")


def handle_message(app: web.Application, raw: dict) -> None:
    """Apply one message from an input client."""
    loop = app[LOOP]
    kind = raw.get("type")
    if kind == "xr_input":
        loop.inputs.update(parse_frame(raw))
        if app[RECORDER]:
            app[RECORDER].write(raw)
    elif kind == "session_end":
        loop.inputs.disconnect()
        if app[RECORDER]:
            app[RECORDER].write(raw)
    elif kind == "hello":
        log.info("input page connected: %s", raw.get("agent", "?"))
    else:
        raise ValueError(f"unknown message type {kind!r}")


async def websocket(request: web.Request) -> web.WebSocketResponse:
    app = request.app
    ws = web.WebSocketResponse(heartbeat=5.0)
    await ws.prepare(request)
    is_input = request.query.get("role", "input") == "input"
    if is_input and not app[ACCEPT_INPUT]:
        await ws.send_json({"type": "error", "message": "replay running; live input disabled"})
        await ws.close()
        return ws

    app[CLIENTS].add(ws)
    if is_input:
        app[INPUTS].add(ws)
    bad = 0
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT or not is_input:
                continue
            try:
                handle_message(app, json.loads(msg.data))
            except (ValueError, TypeError, KeyError) as e:
                bad += 1
                if bad == 1 or bad % 100 == 0:
                    log.warning("ignored bad message (%d so far): %s", bad, e)
    finally:
        app[CLIENTS].discard(ws)
        if is_input:
            app[INPUTS].discard(ws)
            if not app[INPUTS]:
                app[LOOP].inputs.disconnect()  # dead-man: connection gone → loop freezes
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
            msg = app[LOOP].status()
            next_status = time.monotonic() + period
        if not app[CLIENTS]:
            continue
        text = json.dumps(msg)
        for ws in list(app[CLIENTS]):
            if not ws.closed:
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
    loop: TeleopLoop, recorder: Recorder | None = None, accept_input: bool = True
) -> web.Application:
    app = web.Application()
    app[LOOP] = loop
    app[RECORDER] = recorder
    app[ACCEPT_INPUT] = accept_input
    app[CLIENTS] = set()
    app[INPUTS] = set()
    app[OUTBOX] = asyncio.Queue()
    app.router.add_get("/", index)
    app.router.add_get("/monitor", monitor)
    app.router.add_get("/ws", websocket)
    app.router.add_static("/static", WEB_DIR)
    app.router.add_static("/models", MODELS_DIR)
    app.cleanup_ctx.append(_background)
    return app
