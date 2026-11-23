"""Live camera pictures for the teleop page (quick job 63): a few frames a second from each camera
of the arm (stand and wrist). The brain opens a camera only while someone looks at it: the first
picture asked for opens it, and it closes `IDLE_S` after the last one. A camera another program has
open (LeLab, a recording: the green set's rule) is refused with a sentence, before it's opened.

One reader thread per camera keeps its newest frame; `jpeg(name)` gives it as a JPEG, `frame(name)`
gives the raw frame to `camera_snapshot` while the camera is open here (two opens of one camera in
the same program can fail). Cameras are keyed by their device file: two names for one socket (the
white and green sets share sockets 7 and 8, `config/devices.yaml`) share one reader.
"""

import logging
import threading
import time
from collections.abc import Callable

from lab_os import devices

log = logging.getLogger(__name__)

IDLE_S = 5.0  # no picture asked for this long: the camera closes
FPS = 4.0  # pictures a second, at most
WIDTH_PX = 480  # the pictures' width
FIRST_WAIT_S = 6.0  # the first picture after opening (the camera settles its exposure)


class CameraError(Exception):
    """Why there's no picture, as a sentence for the page."""


def _open_capture(path: str):
    import cv2  # headless OpenCV, imported late

    cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap.release()
        raise CameraError(f"couldn't open the camera at {path}")
    return cap


def _encode(frame, width_px: int) -> bytes:
    import cv2

    h, w = frame.shape[:2]
    if w > width_px:
        frame = cv2.resize(frame, (width_px, round(h * width_px / w)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    if not ok:
        raise CameraError("couldn't encode the picture")
    return buf.tobytes()


class _Feed:
    def __init__(self, path: str, cap, encode: Callable):
        self.path, self.cap, self.encode = path, cap, encode
        self.frame = None
        self.jpeg: bytes | None = None
        self.error = ""
        self.asked = time.monotonic()
        self.got = threading.Event()
        self.done = False
        self.thread = threading.Thread(target=self._run, name=f"camera {path}", daemon=True)

    def _run(self) -> None:
        last = 0.0
        try:
            while not self.done and time.monotonic() - self.asked < IDLE_S:
                ok, frame = self.cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue
                self.frame = frame
                now = time.monotonic()
                if now - last >= 1 / FPS:
                    last = now
                    try:
                        self.jpeg = self.encode(frame, WIDTH_PX)
                        self.got.set()
                    except Exception as e:  # one bad frame: say it, keep reading
                        self.error = str(e)
        finally:
            self.done = True
            self.cap.release()
            log.info("camera %s closed (nobody looks at it)", self.path)


class CameraFeeds:
    """The brain's open cameras. `device` and `capture` are replaceable for tests."""

    def __init__(
        self,
        device: Callable[[str], str] = devices.camera_device,
        capture: Callable[[str], object] = _open_capture,
        encode: Callable = _encode,
    ):
        self.device, self.capture, self.encode = device, capture, encode
        self.feeds: dict[str, _Feed] = {}  # by device file
        self.paths: dict[str, str] = {}  # camera name → its device file, once opened
        self.lock = threading.Lock()

    def _path_if_open(self, name: str) -> str | None:
        path = self.paths.get(name)
        feed = self.feeds.get(path) if path else None
        return path if feed and not feed.done else None

    def jpeg(self, name: str) -> bytes:
        """The newest picture of camera `name`, opening it if needed (blocks up to FIRST_WAIT_S).
        Raises CameraError with the reason (not listed, unplugged, in use by another program)."""
        with self.lock:
            path = self._path_if_open(name)
            if path is None:
                try:
                    path = self.device(name)  # the checks: listed, plugged in, nobody else has it
                except (KeyError, LookupError, devices.InUse, devices.PortNotAllowed) as e:
                    raise CameraError(str(e).strip("'\"")) from None
                self.paths[name] = path
                old = self.feeds.get(path)
                if old is None or old.done:  # not open under another name for the same socket
                    feed = _Feed(path, self.capture(path), self.encode)
                    self.feeds[path] = feed
                    feed.thread.start()
                    log.info("camera %s (%s) opened for a page", name, path)
            feed = self.feeds[path]
            feed.asked = time.monotonic()
        if not feed.got.wait(FIRST_WAIT_S):
            raise CameraError(f"{name} gave no picture yet")
        return feed.jpeg

    def frame(self, name: str):
        """The newest raw frame while `name` is open here, else None (then open it yourself)."""
        path = self._path_if_open(name)
        return self.feeds[path].frame if path else None

    def open_names(self) -> list[str]:
        """The cameras open now, by name (LeRobot's teleop must not open them: quick job 91)."""
        return [n for n in list(self.paths) if self._path_if_open(n)]

    def close_all(self) -> None:
        for feed in list(self.feeds.values()):
            feed.done = True
        for feed in list(self.feeds.values()):
            feed.thread.join(timeout=1.0)
        self.feeds.clear()


FEEDS = CameraFeeds()  # the brain's (camera_snapshot uses it too)


def arm_cameras(arm: str, registry: devices.Registry | None = None) -> list[str]:
    """The cameras of arm `arm`, by name (`<arm>-cam-…` in devices.yaml), stand before wrist."""
    registry = registry or devices.load_registry()
    names = [
        d.name
        for d in registry.devices.values()
        if d.kind == "camera" and not d.off_limits and d.name.startswith(f"{arm}-cam-")
    ]
    return sorted(names, key=lambda n: (not n.endswith("stand"), n))


def all_cameras(registry: devices.Registry | None = None) -> list[dict]:
    """Every camera in devices.yaml for the Cameras page (quick job 93), one entry per USB socket:
    {"id": the first name (the one to ask pictures for), "names": every name for that socket}.
    Two names for one socket (the white and green sets) are one camera: one picture, not two.
    Off-limits cameras are left out. In devices.yaml order; opens and lists nothing."""
    registry = registry or devices.load_registry()
    out: dict[str, dict] = {}
    for d in registry.devices.values():
        if d.kind != "camera" or d.off_limits:
            continue
        key = d.socket or d.name  # no socket: its own entry (the picture says what's missing)
        if key in out:
            out[key]["names"].append(d.name)
        else:
            out[key] = {"id": d.name, "names": [d.name]}
    return list(out.values())
