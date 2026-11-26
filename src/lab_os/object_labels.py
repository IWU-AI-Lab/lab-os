"""Labels on what the Raspbot's camera sees: the detector on the brain (quick job 128, moved to the
brain 2026-11-26). The headset only draws the boxes (`web/object-labels.js`).

The detector is YOLOE-26m (Ultralytics, AGPL-3.0), an open-vocabulary model: it finds the objects
that the words in `config/labels.yaml` name, also words outside the usual 80 kinds ("blue cube",
"LEGO brick"). `uv run lab-os labels build` turns the words into the model file
`models/labels/yoloe-26m.onnx` once (it needs the internet and Ultralytics then, never after).
lab-os runs that file with onnxruntime on the processor (6 threads): about 100 ms a picture on the
lab desktop, no GPU, no PyTorch.

    det = Detector()              # FileNotFoundError: the model is not built
    det.detect(jpeg)              # [{name, score, box: {x, y, w, h}}], the box as fractions
    feed = LabelFeed(frames)      # frames: () -> async JPEGs of the camera
    feed.want(page, on, send)     # a page switches its labels on or off; send(msg) gets them
"""

import ast
import asyncio
import contextlib
import io
import logging
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

import numpy as np
from PIL import Image

from lab_os import REPO_ROOT
from lab_os.config import load_yaml

log = logging.getLogger(__name__)

MODEL = REPO_ROOT / "models" / "labels" / "yoloe-26m.onnx"
BUILD = "uv run lab-os labels build"
NO_MODEL = f"The labels model is not on this computer. Run `{BUILD}` on the brain's computer."
OLD_MODEL = f"The words in config/labels.yaml changed. Run `{BUILD}` again."
SIZE = 640  # the model's square input, in pixels
EVERY_S = 0.15  # at most this often (the picture comes at about 30 a second)


def load_words() -> list[str]:
    """The words the detector looks for (config/labels.yaml → words)."""
    words = load_yaml("labels.yaml", shared=True).get("words") or []
    return [str(w).strip() for w in words if str(w).strip()]


ULTRALYTICS = "ultralytics==8.4.219"  # the version the model was tried with (2026-11-26)


def build(words: list[str] | None = None, out: Path = MODEL) -> int:
    """Make the model file from the words (`lab-os labels build`): labels_build.py in a temporary
    environment with Ultralytics, never in lab-os's own. The exit code."""
    import json
    import shutil
    import subprocess
    import tempfile

    words = load_words() if words is None else words
    if not words:
        print("config/labels.yaml has no words.")
        return 1
    uv = shutil.which("uv")
    if not uv:
        print("uv is not on this computer.")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    count = f"{len(words)} word" + ("" if len(words) == 1 else "s")
    print(f"Building the labels model with {count}. The first time, it downloads")
    print("Ultralytics, PyTorch and the model's weights (a few GB). This takes some minutes.")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(words, f)
    script = Path(__file__).with_name("labels_build.py")
    cmd = [uv, "run", "--isolated", "--no-project", "--python", "3.12"]
    cmd += ["--with", ULTRALYTICS, "--with", "onnx", "--with", "onnxslim"]
    cmd += ["python", str(script), f.name, str(out), str(out.parent / "build")]
    try:
        # not on top of lab-os's .venv (`uv run lab-os` sets it): its PyTorch does not fit
        env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "PYTHONPATH")}
        code = subprocess.run(cmd, check=False, env=env).returncode
    finally:
        Path(f.name).unlink(missing_ok=True)
    if code == 0 and out.is_file():
        print(f"Built {out}. Start the brain again to use it.")
        return 0
    print("The build failed. Read the lines above.")
    return code or 1


def letterbox(img: Image.Image, size: int = SIZE) -> tuple[np.ndarray, float, int, int]:
    """The picture scaled into a `size` square without changing its shape (grey bars around it,
    as the model learnt), as the model's input; and the scale and the bars' widths."""
    w, h = img.size
    scale = min(size / w, size / h)
    nw, nh = round(w * scale), round(h * scale)
    px, py = (size - nw) // 2, (size - nh) // 2
    canvas = Image.new("RGB", (size, size), (114, 114, 114))
    canvas.paste(img.convert("RGB").resize((nw, nh), Image.BILINEAR), (px, py))
    x = np.asarray(canvas, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
    return x, scale, px, py


def nms(boxes: np.ndarray, scores: np.ndarray, iou: float) -> list[int]:
    """The boxes to keep, best first: each one that does not overlap a better one by more than
    `iou` (boxes as x1, y1, x2, y2)."""
    order, keep = scores.argsort()[::-1], []
    area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    while order.size:
        i, rest = order[0], order[1:]
        keep.append(int(i))
        x1 = np.maximum(boxes[i, 0], boxes[rest, 0])
        y1 = np.maximum(boxes[i, 1], boxes[rest, 1])
        x2 = np.minimum(boxes[i, 2], boxes[rest, 2])
        y2 = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
        order = rest[inter / (area[i] + area[rest] - inter + 1e-9) <= iou]
    return keep


def decode(
    out: np.ndarray,
    names: list[str],
    scale: float,
    px: int,
    py: int,
    w: int,
    h: int,
    min_score: float = 0.3,
    iou: float = 0.5,
    most: int = 8,
) -> list[dict]:
    """The model's output (4 + one score per word, for each of its 8400 places: centre x, y,
    width, height in input pixels) → the objects, with boxes as fractions of the `w` × `h`
    picture. An object found as two words keeps only the surer one."""
    out = out.reshape(4 + len(names), -1).T
    cls = out[:, 4:].argmax(1)
    score = out[np.arange(len(out)), 4 + cls]
    sure = score >= min_score
    if not sure.any():
        return []
    out, cls, score = out[sure], cls[sure], score[sure]
    cx, cy, bw, bh = out[:, 0], out[:, 1], out[:, 2], out[:, 3]
    xyxy = np.stack([cx - bw / 2 - px, cy - bh / 2 - py, cx + bw / 2 - px, cy + bh / 2 - py], 1)
    xyxy = xyxy / scale / np.array([w, h, w, h], dtype=np.float32)
    xyxy = np.clip(xyxy, 0.0, 1.0)
    found = []
    for i in nms(xyxy, score, iou)[:most]:
        x1, y1, x2, y2 = (float(v) for v in xyxy[i])
        if x2 - x1 <= 0 or y2 - y1 <= 0:
            continue
        found.append(
            {
                "name": names[int(cls[i])],
                "score": round(float(score[i]), 3),
                "box": {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1},
            }
        )
    return found


class Detector:
    """The YOLOE model, run with onnxruntime on the processor."""

    def __init__(self, path: Path = MODEL, threads: int = 6, min_score: float = 0.3) -> None:
        import onnxruntime as ort

        if not path.is_file():
            raise FileNotFoundError(NO_MODEL)
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads  # leave the other cores to the brain (8: 76 ms, 4: 137)
        self.session = ort.InferenceSession(str(path), opts, providers=["CPUExecutionProvider"])
        meta = self.session.get_modelmeta().custom_metadata_map
        names = ast.literal_eval(meta.get("names", "{}"))
        self.names = [names[i] for i in sorted(names)]
        self.input = self.session.get_inputs()[0].name
        self.min_score = min_score

    def detect(self, jpeg: bytes) -> list[dict]:
        img = Image.open(io.BytesIO(jpeg))
        x, scale, px, py = letterbox(img)
        out = self.session.run(None, {self.input: x})[0]
        return decode(out, self.names, scale, px, py, *img.size, min_score=self.min_score)


Send = Callable[[dict], Awaitable[None]]


class LabelFeed:
    """Runs the detector on the camera's newest picture while a page wants labels, and sends each
    result to those pages: {"type": "labels", "state", "found", "why"}. The detector loads at the
    first "on" and stays loaded. One reader of the camera; an old picture is never detected."""

    def __init__(
        self,
        frames: Callable[[], AsyncIterator[bytes]],
        detector: Callable[[], Detector] = Detector,
        words: Callable[[], list[str]] = load_words,
    ) -> None:
        self.frames = frames  # () → the camera's JPEGs; LookupError: no camera
        self.make = detector
        self.words = words
        self.detector: Detector | None = None
        self.pages: dict[object, Send] = {}
        self.state, self.why = "off", ""
        self._task: asyncio.Task | None = None

    async def want(self, page, on: bool, send: Send) -> None:
        """Page `page` switches its labels on or off."""
        if not on:
            self.pages.pop(page, None)
            if not self.pages:
                await self.stop()
            return
        self.pages[page] = send
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())
        else:
            await self._tell(self._msg([]), only=page)

    async def stop(self) -> None:
        self.pages.clear()
        task, self._task = self._task, None
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    def _msg(self, found: list[dict]) -> dict:
        return {"type": "labels", "state": self.state, "found": found, "why": self.why}

    async def _tell(self, msg: dict, only=None) -> None:
        for page, send in list(self.pages.items()):
            if only is not None and page is not only:
                continue
            try:
                await send(msg)
            except (ConnectionError, RuntimeError):  # the page closed meanwhile
                self.pages.pop(page, None)

    async def _set(self, state: str, why: str = "") -> None:
        self.state, self.why = state, why
        await self._tell(self._msg([]))

    async def _run(self) -> None:
        if self.detector is None:
            await self._set("loading")
            try:
                self.detector = await asyncio.to_thread(self.make)
            except Exception as e:  # noqa: BLE001 (any load error is a sentence for the page)
                log.warning("labels: the detector did not load: %s", e)
                return await self._set("failed", str(e))
            if self.words() and self.detector.names and self.words() != self.detector.names:
                log.warning("labels: %s", OLD_MODEL)
                self.detector = None
                return await self._set("failed", OLD_MODEL)
        await self._set("ready")
        while self.pages:
            try:
                await self._detect_stream()
            except LookupError as e:
                await self._set("ready", str(e))
            except Exception as e:  # noqa: BLE001 (the camera stopped: try again)
                log.info("labels: the camera stream ended: %s", e)
            await asyncio.sleep(2.0)

    async def _detect_stream(self) -> None:
        """Read the camera; detect the newest picture whenever the detector is free."""
        newest: list[bytes | None] = [None]
        fresh = asyncio.Event()

        async def read() -> None:
            async with contextlib.aclosing(self.frames()) as frames:
                async for jpeg in frames:
                    newest[0] = jpeg
                    fresh.set()

        reader = asyncio.create_task(read())
        try:
            if self.why:
                await self._set("ready")
            while self.pages:
                waiting = asyncio.ensure_future(fresh.wait())
                done, _ = await asyncio.wait({reader, waiting}, return_when="FIRST_COMPLETED")
                waiting.cancel()
                if reader in done:
                    reader.result()  # the camera ended: its error, if any
                    return
                fresh.clear()
                jpeg, t = newest[0], time.monotonic()
                try:
                    found = await asyncio.to_thread(self.detector.detect, jpeg)
                except Exception as e:  # noqa: BLE001 (a broken picture: skip it)
                    log.info("labels: a picture failed: %s", e)
                    continue
                await self._tell(self._msg(found))
                await asyncio.sleep(max(0.0, EVERY_S - (time.monotonic() - t)))
        finally:
            reader.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await reader
