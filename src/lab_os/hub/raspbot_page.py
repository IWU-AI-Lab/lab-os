"""The Raspbot Control page (quick job 72): drive the Raspbot from a browser, through the brain.

GET /raspbot                 the touch controller: Drive, camera, Pan and Tilt, STOP, diagnostics
GET /monitor/raspbot         read-only view of the camera, model and status, with STOP
WS  /ws/raspbot              the page's buttons → lab_os.robots.raspbot.RaspbotDesk; status at 5 Hz
GET /api/raspbot/camera.mjpg the Raspbot's camera, relayed (the page needs no route to the car)

The brain keeps one connection to the camera (`CameraShare`), however many pages, recordings and
labels use it: the Raspbot's Wi-Fi carries the picture once. Each reader gets the newest picture;
a slow page skips pictures and never falls behind.

Labels (quick job 128): a page sends {"type": "labels", "on": true}; the brain's detector
(`lab_os.object_labels.LabelFeed`) then sends it {"type": "labels", "found": [...]} for each
picture.

The hub's VR Raspbot (quick job 107) uses the same socket: a stick drives ("drive" with "stick"),
the head and the other stick turn the camera ("look"). Both pages use "picture" and "record" to
save the camera's picture on this computer (`RaspbotCamera`, in recordings/raspbot/, not in git).
A recording ends as an .mp4 that every player and browser plays (`to_mp4`, quick job 122).

Who may drive: the same rule as the arm. A page on this computer, or from an address in
`drive_from` (`--drive-from`, place.yaml), drives the real Raspbot; any other page watches and can
STOP. The fake Raspbot (no Raspbot in devices.yaml) may be driven from anywhere.
"""

import asyncio
import contextlib
import json
import logging
import shutil
import time
from collections.abc import AsyncIterator, Callable
from pathlib import Path

import aiohttp
from aiohttp import WSMsgType, web

from lab_os.activity import note
from lab_os.config import recordings_dir
from lab_os.object_labels import LabelFeed
from lab_os.robots.raspbot import RaspbotDesk
from lab_os.teleop.server import DRIVE_FROM, is_local

log = logging.getLogger(__name__)

RASPBOT = web.AppKey("raspbot", RaspbotDesk)
PAGE = Path(__file__).parent / "web" / "raspbot.html"
MONITOR_PAGE = PAGE.with_name("raspbot-monitor.html")
STATUS_S = 0.2
NO_CAMERA = "The Raspbot's camera is not there now."


def split_jpegs(buf: bytes) -> tuple[list[bytes], bytes]:
    """The whole JPEG pictures in an MJPEG stream's bytes, and the bytes left for the next read."""
    out = []
    while True:
        a = buf.find(b"\xff\xd8")
        if a < 0:
            return out, buf[-1:]
        b = buf.find(b"\xff\xd9", a + 2)
        if b < 0:
            return out, buf[a:]
        out.append(buf[a : b + 2])
        buf = buf[b + 2 :]


async def mjpeg_frames(url: str) -> AsyncIterator[bytes]:
    """Each JPEG picture of the MJPEG stream at `url`, as it comes."""
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=3, sock_read=5)
    async with (
        aiohttp.ClientSession(timeout=timeout) as session,
        session.get(url, raise_for_status=True) as up,
    ):
        rest = b""
        async for chunk in up.content.iter_any():
            frames, rest = split_jpegs(rest + chunk)
            for f in frames:
                yield f


async def to_mp4(mjpeg: Path, frames: int, seconds: float) -> Path:
    """The recording's JPEGs as an H.264 .mp4 at the rate they came, with ffmpeg. A raw .mjpeg has
    no times, and most players do not open it (quick job 122). Keeps the .mjpeg when ffmpeg is not
    there or fails."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        log.warning("raspbot recording: no ffmpeg on this computer, so it stays %s", mjpeg.name)
        return mjpeg
    mp4 = mjpeg.with_suffix(".mp4")
    fps = f"{max(1.0, frames / max(seconds, 0.1)):.2f}"
    proc = await asyncio.create_subprocess_exec(
        *(ffmpeg, "-y", "-loglevel", "error", "-f", "mjpeg", "-framerate", fps, "-i", str(mjpeg)),
        *("-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0 or not mp4.exists():
        log.warning("raspbot recording: ffmpeg failed, so it stays %s: %s", mjpeg.name, err[-300:])
        mp4.unlink(missing_ok=True)
        return mjpeg
    mjpeg.unlink()
    return mp4


class _Upstream:
    """One connection to a camera stream, and its newest JPEG."""

    def __init__(self, source: Callable[[str], AsyncIterator[bytes]], url: str) -> None:
        self.jpeg, self.seq, self.readers = b"", 0, 0
        self.error: BaseException | None = None
        self.ended = False
        self.cond = asyncio.Condition()
        self.task = asyncio.create_task(self._read(source, url))

    async def _read(self, source, url: str) -> None:
        try:
            async with contextlib.aclosing(source(url)) as frames:
                async for jpeg in frames:
                    async with self.cond:
                        self.jpeg, self.seq = jpeg, self.seq + 1
                        self.cond.notify_all()
        except Exception as e:  # noqa: BLE001 (each reader gets it)
            self.error = e
        finally:
            self.ended = True
            async with self.cond:
                self.cond.notify_all()


class CameraShare:
    """One connection to each camera stream, shared by every reader on the brain. It opens with
    the first reader and closes when the last one leaves."""

    def __init__(self, source: Callable[[str], AsyncIterator[bytes]] = mjpeg_frames) -> None:
        self.source = source
        self._ups: dict[str, _Upstream] = {}

    def readers(self, url: str) -> int:
        up = self._ups.get(url)
        return up.readers if up and not up.ended else 0

    async def frames(self, url: str) -> AsyncIterator[bytes]:
        """The newest JPEG of the stream at `url`, each time a new one comes. Ends with the stream's
        error (or at its end)."""
        up = self._ups.get(url)
        if up is None or up.ended:
            up = self._ups[url] = _Upstream(self.source, url)
        up.readers += 1
        seen = 0
        try:
            while True:
                async with up.cond:
                    await up.cond.wait_for(lambda s=seen: up.seq != s or up.ended)
                    if up.seq == seen:
                        if up.error:
                            raise up.error
                        return
                    seen, jpeg = up.seq, up.jpeg
                yield jpeg
        finally:
            up.readers -= 1
            if up.readers == 0:
                up.task.cancel()
                if self._ups.get(url) is up:
                    del self._ups[url]


class RaspbotCamera:
    """Pictures and recordings of the Raspbot's camera, saved on the brain's computer (quick job
    107). A picture is one JPEG. A recording collects the camera's JPEGs in an .mjpeg, and at its
    end becomes an .mp4 (`to_mp4`). One recording at a time; it ends when the page that started
    it closes or the camera stops."""

    def __init__(self, desk: RaspbotDesk, folder: Callable[[], Path] | None = None, frames=None):
        self.desk = desk
        self.folder = folder or (lambda: recordings_dir() / "raspbot")
        self.share = CameraShare()
        self.frames = frames or self.share.frames  # url → async JPEGs (tests give their own)
        self.convert = to_mp4  # (mjpeg, frames, seconds) → the saved file (tests give their own)
        self.recording: Path | None = None
        self.by = None  # the page that started the recording
        self._started_at = 0.0
        self._count = 0  # the JPEGs in the recording so far
        self._task: asyncio.Task | None = None

    def _url(self) -> str:
        bot = self.desk.bot
        if not getattr(bot, "camera_port", 0) or not bot.connected or not hasattr(bot, "host"):
            raise LookupError(NO_CAMERA)
        return f"http://{bot.host}:{bot.camera_port}/camera.mjpg"

    def _path(self, ext: str) -> Path:
        folder = self.folder()
        folder.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        return folder / f"{self.desk.bot.name}_{stamp}.{ext}"

    async def stream(self) -> AsyncIterator[bytes]:
        """The camera's JPEGs, as they come. LookupError when there is no camera picture."""
        async with contextlib.aclosing(self.frames(self._url())) as frames:
            async for jpeg in frames:
                yield jpeg

    async def snapshot(self) -> bytes:
        """Read one JPEG from the same camera stream as the page."""
        url = self._url()
        try:
            async with asyncio.timeout(5), contextlib.aclosing(self.frames(url)) as frames:
                async for jpeg in frames:
                    return jpeg
        except (aiohttp.ClientError, TimeoutError, OSError) as e:
            log.info("raspbot picture: %s", e)
        raise LookupError("The Raspbot's camera does not answer.")

    async def picture(self) -> Path:
        """Save the camera's next picture."""
        jpeg = await self.snapshot()
        path = self._path("jpg")
        path.write_bytes(jpeg)
        log.info("raspbot: picture saved: %s", path)
        return path

    def start(self, page) -> Path:
        """Start a recording. LookupError when there is no camera picture."""
        if self.recording:
            return self.recording
        url = self._url()
        self.recording, self.by = self._path("mjpeg"), page
        self._started_at, self._count = time.monotonic(), 0
        self._task = asyncio.create_task(self._record(url, self.recording))
        log.info("raspbot: recording to %s", self.recording)
        return self.recording

    async def _record(self, url: str, path: Path) -> None:
        try:
            with path.open("wb") as f:
                async with contextlib.aclosing(self.frames(url)) as frames:
                    async for jpeg in frames:
                        f.write(jpeg)
                        self._count += 1
        except (aiohttp.ClientError, TimeoutError, OSError) as e:
            log.info("raspbot recording ended: %s", e)
        if self.recording == path:  # the camera stopped by itself: the recording ends and is saved
            self.recording, self.by, self._task = None, None, None
            with contextlib.suppress(LookupError):
                await self._finish(path)

    async def _finish(self, path: Path) -> Path:
        """The ended recording as a video. LookupError when the camera sent no picture."""
        count, seconds = self._count, time.monotonic() - self._started_at
        if count == 0:
            path.unlink(missing_ok=True)
            log.info("raspbot: recording %s had no pictures, deleted", path.name)
            raise LookupError("The recording has no pictures. The Raspbot's camera sent none.")
        saved = await self.convert(path, count, seconds)
        log.info("raspbot: recording saved: %s (%d pictures in %.1f s)", saved, count, seconds)
        return saved

    async def stop(self, page=None) -> Path | None:
        """End the recording and save it (only the page that started it, when `page` is given).
        None when no recording was on. LookupError when it has no pictures."""
        if not self.recording or (page is not None and page is not self.by):
            return None
        path, task = self.recording, self._task
        self.recording, self.by, self._task = None, None, None
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        return await self._finish(path)

    def status(self) -> dict:
        name = self.recording.name if self.recording else ""
        return {
            "recording": name,
            "recording_seconds": int(time.monotonic() - self._started_at) if name else None,
            "folder": str(self.folder()),
        }


CAMERA = web.AppKey("raspbot_camera", RaspbotCamera)
LABELS = web.AppKey("raspbot_labels", LabelFeed)


async def raspbot_page(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(PAGE)


async def monitor_page(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(MONITOR_PAGE)


def may_drive(request: web.Request) -> bool:
    desk = request.app[RASPBOT]
    return desk.bot.is_fake or is_local(request) or request.remote in request.app[DRIVE_FROM]


async def raspbot_ws(request: web.Request) -> web.WebSocketResponse:
    desk, cam, labels = request.app[RASPBOT], request.app[CAMERA], request.app[LABELS]
    ws = web.WebSocketResponse(heartbeat=5.0)
    await ws.prepare(request)
    monitor = request.query.get("role") == "monitor"
    drives = not monitor and may_drive(request)
    if not drives and not monitor:
        log.info("raspbot page from %s connected view-only", request.remote)

    async def send_status():
        while not ws.closed:
            msg = desk.status(ws) | {"may_drive": drives} | cam.status()
            if not drives and not monitor:
                msg["address"] = request.remote or ""
            await ws.send_json(msg)
            await asyncio.sleep(STATUS_S)

    async def reply_saved(kind: str, raw: dict) -> None:
        with contextlib.suppress(ConnectionError, RuntimeError):  # the page closed meanwhile
            await ws.send_json(await _save(cam, ws, kind, raw))

    status = asyncio.create_task(send_status())
    saves: set[asyncio.Task] = set()
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            try:
                raw = json.loads(msg.data)
                kind = raw.get("type")
                if kind == "stop":  # any page, watchers too
                    who = str(raw.get("device") or "")[:32]
                    await desk.stop(who)
                    note(
                        request.app,
                        f"STOP pressed for {desk.bot.name} on {who or request.remote}",
                        "stop",
                    )
                elif kind == "set_speed" and drives:  # the Speed slider
                    desk.set_speed(float(raw["speed"]))
                elif kind == "release" and drives:
                    await desk.release(ws)
                elif kind == "drive":
                    stick = raw.get("stick")
                    if stick is not None:
                        if not isinstance(stick, list) or len(stick) not in (2, 3):
                            raise ValueError("expected two or three drive axes")
                        stick = tuple(float(axis) for axis in stick)
                    why = "View only."
                    if drives:
                        why = await desk.press(ws, str(raw.get("dir")), stick)
                    if why:
                        await ws.send_json({"type": "error", "message": why})
                elif kind == "look" and drives:
                    why = await desk.look(
                        ws,
                        float(raw["pan"]),
                        float(raw["tilt"]),
                        relative=raw.get("relative") is True,
                    )
                    if why:
                        await ws.send_json({"type": "error", "message": why})
                elif kind == "labels":  # a page that only watches may see them too
                    await labels.want(ws, raw.get("on") is True, ws.send_json)
                elif kind in ("picture", "record") and drives:  # a save never holds up a STOP
                    task = asyncio.create_task(reply_saved(kind, raw))
                    saves.add(task)
                    task.add_done_callback(saves.discard)
            except (ValueError, TypeError, AttributeError, KeyError) as e:
                log.warning("raspbot page: ignored a bad message: %s", e)
    finally:
        status.cancel()
        await labels.want(ws, False, ws.send_json)
        await desk.release(ws)  # the driver's page closed: the car stops
        with contextlib.suppress(LookupError):
            await cam.stop(ws)  # and its recording ends and is saved
    return ws


async def _save(cam: RaspbotCamera, page, kind: str, raw: dict) -> dict:
    """A picture, or a recording's start or end → the message that says where it is."""
    try:
        if kind == "picture":
            return {"type": "saved", "what": "picture", "path": str(await cam.picture())}
        if raw.get("on"):
            return {"type": "saved", "what": "recording", "on": True, "path": str(cam.start(page))}
        path = await cam.stop()
        return {"type": "saved", "what": "recording", "on": False, "path": str(path or "")}
    except (LookupError, OSError) as e:
        return {"type": "error", "message": str(e)}


async def raspbot_camera(request: web.Request) -> web.StreamResponse:
    """The Raspbot's picture as MJPEG, from the brain's one connection to the camera."""
    bot = request.app[RASPBOT].bot
    if bot.is_fake or not bot.camera_port or not bot.connected:
        raise web.HTTPNotFound(text=NO_CAMERA)
    url = f"http://{bot.host}:{bot.camera_port}/camera.mjpg"
    resp = None
    try:
        async with contextlib.aclosing(request.app[CAMERA].frames(url)) as frames:
            async for jpeg in frames:
                if resp is None:
                    resp = web.StreamResponse(
                        headers={
                            "Content-Type": "multipart/x-mixed-replace; boundary=frame",
                            "Cache-Control": "no-store",
                        }
                    )
                    await resp.prepare(request)
                head = b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n"
                await resp.write(head % len(jpeg) + jpeg + b"\r\n")
    except (aiohttp.ClientError, TimeoutError, OSError) as e:  # OSError: the page left
        log.info("raspbot camera: %s", e)
    if resp is None:
        raise web.HTTPBadGateway(text="The Raspbot's camera does not answer.")
    return resp


async def _desk_tasks(app: web.Application):
    desk = app[RASPBOT]
    tasks = [asyncio.create_task(desk.run()), asyncio.create_task(desk.bot.run())]
    yield
    with contextlib.suppress(Exception):
        await desk.stop()
    with contextlib.suppress(Exception):
        await app[CAMERA].stop()
    with contextlib.suppress(Exception):
        await app[LABELS].stop()
    for t in tasks:
        t.cancel()


def add_raspbot(app: web.Application, desk: RaspbotDesk) -> None:
    app[RASPBOT] = desk
    app[CAMERA] = RaspbotCamera(desk)
    app[LABELS] = LabelFeed(app[CAMERA].stream)
    app.router.add_get("/raspbot", raspbot_page)
    app.router.add_get("/monitor/raspbot", monitor_page)
    app.router.add_get("/ws/raspbot", raspbot_ws)
    app.router.add_get("/api/raspbot/camera.mjpg", raspbot_camera)
    app.cleanup_ctx.append(_desk_tasks)
