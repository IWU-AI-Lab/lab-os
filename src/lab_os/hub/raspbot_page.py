"""The Raspbot page (quick job 72): drive the Raspbot from a browser, through the brain.

GET /raspbot                 the page: forward, back, left, right (hold), Speed, STOP, the camera
WS  /ws/raspbot              the page's buttons → lab_os.robots.raspbot.RaspbotDesk; status at 5 Hz
GET /api/raspbot/camera.mjpg the Raspbot's camera, relayed (the page needs no route to the car)

Who may drive: the same rule as the arm. A page on this computer, or from an address in
`drive_from` (`--drive-from`, place.yaml), drives the real Raspbot; any other page watches and can
STOP. The fake Raspbot (no Raspbot in devices.yaml) may be driven from anywhere.
"""

import asyncio
import contextlib
import json
import logging
from pathlib import Path

import aiohttp
from aiohttp import WSMsgType, web

from lab_os.robots.raspbot import RaspbotDesk
from lab_os.teleop.server import DRIVE_FROM, is_local

log = logging.getLogger(__name__)

RASPBOT = web.AppKey("raspbot", RaspbotDesk)
PAGE = Path(__file__).parent / "web" / "raspbot.html"
STATUS_S = 0.2


async def raspbot_page(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(PAGE)


def may_drive(request: web.Request) -> bool:
    desk = request.app[RASPBOT]
    return desk.bot.is_fake or is_local(request) or request.remote in request.app[DRIVE_FROM]


async def raspbot_ws(request: web.Request) -> web.WebSocketResponse:
    desk = request.app[RASPBOT]
    ws = web.WebSocketResponse(heartbeat=5.0)
    await ws.prepare(request)
    drives = may_drive(request)
    if not drives:
        log.info("raspbot page from %s connected view-only", request.remote)

    async def send_status():
        while not ws.closed:
            msg = desk.status(ws) | {"may_drive": drives}
            if not drives:
                msg["address"] = request.remote or ""
            await ws.send_json(msg)
            await asyncio.sleep(STATUS_S)

    status = asyncio.create_task(send_status())
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            try:
                raw = json.loads(msg.data)
                kind = raw.get("type")
                if kind == "stop":  # any page, watchers too
                    await desk.stop(str(raw.get("device") or "")[:32])
                elif kind == "set_speed" and drives:  # the Speed slider
                    desk.set_speed(float(raw["speed"]))
                elif kind == "release" and drives:
                    await desk.release(ws)
                elif kind == "drive":
                    why = await desk.press(ws, str(raw.get("dir"))) if drives else "View only."
                    if why:
                        await ws.send_json({"type": "error", "message": why})
            except (ValueError, TypeError, AttributeError, KeyError) as e:
                log.warning("raspbot page: ignored a bad message: %s", e)
    finally:
        status.cancel()
        await desk.release(ws)  # the driver's page closed: the car stops
    return ws


async def raspbot_camera(request: web.Request) -> web.StreamResponse:
    """The Raspbot's MJPEG picture, passed through as it comes."""
    bot = request.app[RASPBOT].bot
    if bot.is_fake or not bot.camera_port or not bot.connected:
        raise web.HTTPNotFound(text="The Raspbot's camera is not there now.")
    url = f"http://{bot.host}:{bot.camera_port}/camera.mjpg"
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=3, sock_read=5)
    resp = None
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session, session.get(url) as up:
            resp = web.StreamResponse(
                headers={
                    "Content-Type": up.headers.get("Content-Type", "image/jpeg"),
                    "Cache-Control": "no-store",
                }
            )
            await resp.prepare(request)
            async for chunk in up.content.iter_any():
                await resp.write(chunk)
            return resp
    except (aiohttp.ClientError, TimeoutError, ConnectionResetError) as e:
        log.info("raspbot camera: %s", e)
        if resp is not None:  # the picture was coming: it just ends
            return resp
        raise web.HTTPBadGateway(text="The Raspbot's camera does not answer.") from None


async def _desk_tasks(app: web.Application):
    desk = app[RASPBOT]
    tasks = [asyncio.create_task(desk.run()), asyncio.create_task(desk.bot.run())]
    yield
    with contextlib.suppress(Exception):
        await desk.stop()
    for t in tasks:
        t.cancel()


def add_raspbot(app: web.Application, desk: RaspbotDesk) -> None:
    app[RASPBOT] = desk
    app.router.add_get("/raspbot", raspbot_page)
    app.router.add_get("/ws/raspbot", raspbot_ws)
    app.router.add_get("/api/raspbot/camera.mjpg", raspbot_camera)
    app.cleanup_ctx.append(_desk_tasks)
