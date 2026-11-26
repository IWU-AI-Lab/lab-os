"""Live camera pictures for the teleop page (quick job 63): a few frames a second from each camera
of the arm (stand and wrist). The brain opens a camera only while someone looks at it: the first
picture asked for opens it, and it closes `IDLE_S` after the last one. A camera another program has
open (LeLab, a recording: the green set's rule) is refused with a sentence, before it's opened.

One reader thread per camera keeps its newest frame; `jpeg(name)` gives it as a JPEG for a page,
`frame(name)` and `grab(name, path)` give the raw frame to `camera_snapshot` (two opens of one
camera in the same program can fail: quick job 116). Cameras are keyed by their device file: two
names for one camera (the white set's and the green set's for one socket) share one reader, so the
AI and the Cameras page see through one open camera.
Other programs still get "in use" (`devices.InUse`).
"""

import logging
import threading
import time
from collections import deque
from collections.abc import Callable

from lab_os import devices

log = logging.getLogger(__name__)

IDLE_S = 5.0  # no picture asked for this long: the camera closes
FPS = 4.0  # pictures a second, at most
WIDTH_PX = 480  # the pictures' width
FIRST_WAIT_S = 6.0  # the first picture after opening (the camera settles its exposure)
SETTLE_S = 6.0  # the AI's picture: wait at most this long for the exposure to hold still


class CameraError(Exception):
    """Why there's no picture, as a sentence for the page."""


def _open_capture(path: str):
    import cv2  # headless OpenCV, imported late

    cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap.release()
        raise CameraError(f"couldn't open the camera at {path}")
    # MJPEG, not the raw default: a raw picture takes much of a USB 2.0 controller's time, which
    # the other cameras and the USB microphone need (quick job 115). A camera without it ignores it.
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    return cap


def _level(frame) -> float:
    """A frame's brightness (0 to 255)."""
    return float(frame.mean())


def _locate(name: str) -> str:
    """The device file of camera `name`, with no check of who has it open (to find it here)."""
    return devices.camera_paths(name)[0]


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
    def __init__(self, path: str, cap, encode: Callable, level: Callable = _level):
        self.path, self.cap, self.encode, self.level = path, cap, encode, level
        self.frame = None
        self.settled = threading.Event()  # the exposure held still (or SETTLE_S went by)
        self.opened = time.monotonic()
        self._steady, self._last_level = 0, None
        self.jpeg: bytes | None = None
        self.error = ""
        self.asked = time.monotonic()
        self.reads: deque[float] = deque(maxlen=90)  # when each frame came (the picture rate)
        self.size = (0, 0)  # the camera's frame: width, height
        self.got = threading.Event()
        self.done = False
        self.thread = threading.Thread(target=self._run, name=f"camera {path}", daemon=True)

    def _settle(self, frame) -> None:
        """These cameras start black, then auto-exposure overshoots to white: settled once the
        brightness has held still for a few frames (as `tools.robot.grab_frame`)."""
        level = self.level(frame)
        before = self._last_level
        self._steady = self._steady + 1 if before is not None and abs(level - before) < 3 else 0
        self._last_level = level
        if (self._steady >= 4 and 8 < level < 245) or time.monotonic() - self.opened > SETTLE_S:
            self.settled.set()

    def _run(self) -> None:
        last = 0.0
        try:
            while not self.done and time.monotonic() - self.asked < IDLE_S:
                ok, frame = self.cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue
                self.frame = frame
                self.reads.append(time.monotonic())
                if not self.size[0] and hasattr(frame, "shape"):
                    self.size = (int(frame.shape[1]), int(frame.shape[0]))
                if not self.settled.is_set():
                    self._settle(frame)
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

    def rate(self, window_s: float = 2.0) -> float:
        """Frames a second the camera gave over the last `window_s` (0 when none came)."""
        now = time.monotonic()
        recent = [t for t in self.reads if now - t <= window_s]
        if len(recent) < 2:
            return 0.0
        return (
            round((len(recent) - 1) / (recent[-1] - recent[0]), 1)
            if recent[-1] > recent[0]
            else 0.0
        )


class CameraFeeds:
    """The brain's open cameras. `device` and `capture` are replaceable for tests."""

    def __init__(
        self,
        device: Callable[[str], str] = devices.camera_device,
        capture: Callable[[str], object] = _open_capture,
        encode: Callable = _encode,
        locate: Callable[[str], str] = _locate,
        level: Callable = _level,
    ):
        self.device, self.capture, self.encode = device, capture, encode
        self.locate, self.level = locate, level
        self.feeds: dict[str, _Feed] = {}  # by device file
        self.paths: dict[str, str] = {}  # camera name → its device file, once opened
        self.lock = threading.Lock()

    def _path_if_open(self, name: str, find: bool = False) -> str | None:
        """`name`'s device file while it's open here. `find`: also when it's open under another
        name for the same socket (the white and the green names: GOTCHAS 2026-11-24)."""
        path = self.paths.get(name)
        if path is None and find:
            try:
                path = self.locate(name)
            except (KeyError, LookupError, devices.PortNotAllowed):
                return None
        feed = self.feeds.get(path) if path else None
        if feed and not feed.done:
            self.paths[name] = path
            return path
        return None

    def _open(self, name: str, path: str, why: str) -> _Feed:
        """The reader of `path` (lock held): the one open now, or a new one."""
        self.paths[name] = path
        feed = self.feeds.get(path)
        if feed is None or feed.done:  # not open under another name for the same socket
            feed = _Feed(path, self.capture(path), self.encode, self.level)
            self.feeds[path] = feed
            feed.thread.start()
            log.info("camera %s (%s) opened for %s", name, path, why)
        feed.asked = time.monotonic()
        return feed

    def jpeg(self, name: str) -> bytes:
        """The newest picture of camera `name`, opening it if needed (blocks up to FIRST_WAIT_S).
        Raises CameraError with the reason (not listed, unplugged, in use by another program)."""
        with self.lock:
            path = self._path_if_open(name, find=True)
            if path is None:
                try:
                    path = self.device(name)  # the checks: listed, plugged in, nobody else has it
                except (KeyError, LookupError, devices.InUse, devices.PortNotAllowed) as e:
                    raise CameraError(str(e).strip("'\"")) from None
            feed = self._open(name, path, "a page")
        if not feed.got.wait(FIRST_WAIT_S):
            raise CameraError(f"{name} gave no picture yet")
        return feed.jpeg

    def frame(self, name: str):
        """The newest settled raw frame while `name`'s camera is open here, under any of its
        names, else None (then check it and `grab` it)."""
        with self.lock:
            path = self._path_if_open(name, find=True)
            feed = self.feeds[path] if path else None
            if feed is None or not feed.settled.is_set() or feed.frame is None:
                return None
            feed.asked = time.monotonic()
            return feed.frame

    def grab(self, name: str, path: str):
        """One settled raw frame of camera `name` at `path` (checked by the caller: nobody else
        has it). It stays open IDLE_S after, so a page that asks shares it. Blocks up to
        SETTLE_S + FIRST_WAIT_S. Raises CameraError."""
        with self.lock:
            feed = self._open(name, path, "the AI")
        end = time.monotonic() + SETTLE_S + FIRST_WAIT_S
        while not feed.settled.wait(0.5):
            feed.asked = time.monotonic()  # keep it open while it settles
            if feed.done or time.monotonic() > end:
                break
        if feed.frame is None:
            raise CameraError(f"{name} gave no picture")
        return feed.frame

    def stats(self, name: str) -> dict | None:
        """A camera that is open now: its picture rate, size and last error (quick job 135's
        diagnostics); None when it is closed."""
        with self.lock:
            path = self.paths.get(name)
            feed = self.feeds.get(path) if path else None
        if feed is None or feed.done:
            return None
        return {
            "fps": feed.rate(),
            "sent_fps": FPS,
            "width": feed.size[0],
            "height": feed.size[1],
            "error": feed.error,
        }

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
    """Every camera in devices.yaml for the Cameras page (quick job 93), one entry per USB socket
    (or port of an arm's hub): {"id": the first name (the one to ask pictures for), "names": every
    name for that place}. Two names for one place are one camera: one picture, not two.
    Off-limits cameras are left out. In devices.yaml order; opens and lists nothing."""
    registry = registry or devices.load_registry()
    out: dict[str, dict] = {}
    for d in registry.devices.values():
        if d.kind != "camera" or d.off_limits:
            continue
        # no socket: its own entry (the picture says what's missing)
        key = d.socket or (f"{d.beside}/{d.hub_port}" if d.beside else d.name)
        if key in out:
            out[key]["names"].append(d.name)
        else:
            out[key] = {"id": d.name, "names": [d.name]}
    return list(out.values())
