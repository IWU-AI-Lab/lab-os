"""Labels on what the Raspbot sees, in VR and AR (quick job 128; the detector on the brain since
2026-11-26). Here: the model's output → the objects, the feed that runs the detector while a page
wants labels, the socket, which object gets the ultrasonic distance, the label's words and the
rules of the VR window. The real model (not in git) is tried only when it is built. Node tests skip
without node."""

import asyncio
import io
import json
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image
from test_hub_server import make_app

from lab_os import REPO_ROOT, object_labels
from lab_os.hub.raspbot_page import LABELS
from lab_os.object_labels import (
    MODEL,
    NO_MODEL,
    OLD_MODEL,
    Detector,
    LabelFeed,
    decode,
    letterbox,
    load_words,
)

WEB = REPO_ROOT / "src/lab_os/web"
MODULE = WEB / "object-labels.js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node isn't installed")


def jpeg(w=640, h=480, color=(200, 30, 30)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (w, h), color).save(out, "JPEG")
    return out.getvalue()


# ---- the model's output → the objects ----


def test_the_picture_keeps_its_shape_in_the_models_input():
    white = Image.new("RGB", (640, 480), (255, 255, 255))
    x, scale, px, py = letterbox(white)  # the Raspbot's picture fills the 640 × 480 input
    assert x.shape == (1, 3, 480, 640) and x.dtype == np.float32
    assert (scale, px, py) == (1.0, 0, 0) and float(x.min()) == 1.0
    x, scale, px, py = letterbox(white, (640, 640))  # a square model: grey bars
    assert x.shape == (1, 3, 640, 640) and (scale, px, py) == (1.0, 0, 80)
    assert x[0, :, 0, 320].tolist() == pytest.approx([114 / 255] * 3)  # the grey bar on top
    assert x[0, :, 320, 320].tolist() == pytest.approx([1.0] * 3)  # the picture
    x, scale, px, py = letterbox(Image.new("RGB", (480, 640)))  # upright: bars at the sides
    assert x.shape == (1, 3, 480, 640) and (scale, px, py) == (0.75, 140, 0)


def test_overlapping_boxes_become_one_object_with_fractions_of_the_picture():
    names = ["cup", "bowl", "blue cube"]
    out = np.zeros((4 + 3, 8400), dtype=np.float32)

    def put(i, cx, cy, w, h, word, score):
        out[:4, i] = (cx, cy, w, h)
        out[4 + names.index(word), i] = score

    # a 640 × 480 picture in the 640 square: 80 px of grey above it
    put(0, 320, 80 + 240, 100, 120, "cup", 0.8)
    put(1, 322, 80 + 242, 100, 120, "bowl", 0.6)  # the same object, less sure: dropped
    put(2, 100, 80 + 100, 40, 40, "blue cube", 0.5)
    put(3, 500, 300, 50, 50, "cup", 0.1)  # not sure enough
    found = decode(out[None], names, 1.0, 0, 80, 640, 480)
    assert [f["name"] for f in found] == ["cup", "blue cube"]
    assert found[0]["score"] == 0.8
    want = {"x": 270 / 640, "y": 180 / 480, "w": 100 / 640, "h": 120 / 480}
    assert found[0]["box"] == pytest.approx(want)
    assert found[1]["box"]["x"] == pytest.approx(80 / 640)
    assert decode(np.zeros((1, 7, 8400), np.float32), names, 1.0, 0, 80, 640, 480) == []


def test_the_words_include_the_labs_own_things():
    words = load_words()
    assert {"blue cube", "LEGO brick", "cup", "person"} <= set(words)
    assert len(words) == len(set(words))


@pytest.mark.skipif(not MODEL.is_file(), reason="the labels model is not built here")
def test_the_built_model_runs_on_a_picture():
    det = Detector()
    assert det.names == load_words()  # built from today's words
    assert det.size == (640, 480)
    assert det.detect(jpeg()) == []  # a plain red picture: nothing


def test_without_the_model_the_reason_names_the_command(tmp_path):
    with pytest.raises(FileNotFoundError, match="uv run lab-os labels build"):
        Detector(tmp_path / "none.onnx")


# ---- the feed: the detector runs while a page wants labels ----


class FakeDetector:
    def __init__(self, names=("cup",)):
        self.names = list(names)
        self.pictures = 0

    def detect(self, _jpeg):
        self.pictures += 1
        return [{"name": "cup", "score": 0.9, "box": {"x": 0.4, "y": 0.3, "w": 0.2, "h": 0.2}}]


def camera(count=None):
    async def frames():
        n = 0
        while count is None or n < count:
            n += 1
            yield jpeg()
            await asyncio.sleep(0.01)

    return frames


async def until(msgs, test, s=2.0):
    async with asyncio.timeout(s):
        while not any(test(m) for m in msgs):
            await asyncio.sleep(0.01)


async def test_a_page_gets_the_objects_while_its_labels_are_on():
    det = FakeDetector()
    feed = LabelFeed(camera(), detector=lambda: det, words=lambda: ["cup"])
    got = []

    async def send(m):
        got.append(m)

    await feed.want("page", True, send)
    await until(got, lambda m: m["found"])
    assert [m["state"] for m in got[:2]] == ["loading", "ready"]
    assert got[-1]["found"][0]["name"] == "cup"
    await feed.want("page", False, send)
    assert feed._task is None and not feed.pages
    seen = det.pictures
    await asyncio.sleep(0.2)
    assert det.pictures == seen  # stopped with the last page
    # on again: the detector stays loaded, no "loading"
    got.clear()
    await feed.want("page", True, send)
    await until(got, lambda m: m["found"])
    assert "loading" not in [m["state"] for m in got]
    await feed.stop()


async def test_no_camera_or_no_model_is_a_sentence_for_the_page():
    got = []

    async def send(m):
        got.append(m)

    async def no_camera():
        raise LookupError("The Raspbot's camera is not there now.")
        yield b""

    feed = LabelFeed(no_camera, detector=FakeDetector, words=lambda: ["cup"])
    await feed.want("page", True, send)
    await until(got, lambda m: "camera" in m["why"])
    await feed.stop()

    def missing():
        raise FileNotFoundError(NO_MODEL)

    got.clear()
    feed = LabelFeed(camera(), detector=missing)
    await feed.want("page", True, send)
    await until(got, lambda m: m["state"] == "failed")
    assert got[-1]["why"] == NO_MODEL

    got.clear()  # the words changed after the build
    feed = LabelFeed(camera(), detector=FakeDetector, words=lambda: ["cup", "blue cube"])
    await feed.want("page", True, send)
    await until(got, lambda m: m["state"] == "failed")
    assert got[-1]["why"] == OLD_MODEL and feed.detector is None


async def test_the_socket_sends_labels_to_the_page_that_asked(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    feed = app[LABELS]
    feed.frames, feed.make, feed.words = camera(), FakeDetector, lambda: ["cup"]
    async with client.ws_connect("/ws/raspbot?role=monitor") as ws:  # a watcher may see them too
        await ws.send_json({"type": "labels", "on": True})
        async with asyncio.timeout(3):
            while not ((m := await ws.receive_json()).get("type") == "labels" and m["found"]):
                pass
        assert m["found"][0]["name"] == "cup"
    for _ in range(100):  # the page closed: the detector stops
        if not app[LABELS].pages:
            break
        await asyncio.sleep(0.01)
    assert not app[LABELS].pages


def test_the_build_runs_outside_lab_os_environment(monkeypatch, tmp_path):
    calls = []

    def run(cmd, check, env):
        calls.append((cmd, env))
        (tmp_path / "m.onnx").write_bytes(b"x")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setenv("VIRTUAL_ENV", str(REPO_ROOT / ".venv"))
    assert object_labels.build(["cup"], tmp_path / "m.onnx") == 0
    cmd, env = calls[0]
    assert cmd[1:4] == ["run", "--isolated", "--no-project"]
    assert object_labels.ULTRALYTICS in cmd and cmd[-4].endswith("labels_build.py")
    assert "VIRTUAL_ENV" not in env


# ---- the headset draws ----


def run_js(expr: str):
    script = (
        f"import({json.dumps(MODULE.as_uri())}).then(m => {{"
        f"console.log(JSON.stringify({expr})); }})"
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def box(name, x, w, score=0.8, y=0.2, h=0.5):
    return {"name": name, "score": score, "box": {"x": x, "y": y, "w": w, "h": h}}


@needs_node
def test_the_object_in_front_is_the_biggest_over_the_middle():
    found = [box("cup", 0.1, 0.2), box("chair", 0.3, 0.4), box("bottle", 0.45, 0.1, h=0.2)]
    f = json.dumps(found)
    assert run_js(f"m.frontIndex({f}, 0)") == 1  # the chair: over the middle, the biggest
    assert run_js(f"m.frontIndex({f}, -12)") == 1
    # the camera turned away: the sensor on the car's front does not measure what it sees
    assert run_js(f"m.frontIndex({f}, 40)") == -1
    assert run_js(f"m.frontIndex({f}, undefined)") == 1  # no angle known: the centre
    assert run_js(f"m.frontIndex({json.dumps([box('cup', 0.1, 0.2)])}, 0)") == -1
    assert run_js("m.frontIndex([], 0)") == -1


@needs_node
def test_the_label_says_the_name_how_sure_and_the_distance():
    f = json.dumps(box("cell phone", 0.1, 0.2, score=0.823))
    assert run_js(f"m.labelText({f}, null)") == "Cell phone   82%"
    assert run_js(f"m.labelText({f}, 342)") == "Cell phone   82%   34 cm"
    assert run_js(f"m.labelText({json.dumps(box('LEGO brick', 0, 1))}, null)") == "LEGO brick   80%"


@needs_node
def test_the_labels_look_like_a_hud():
    g = (
        "{save(){}, restore(){}, strokeRect(){}, fillRect(){}, letterSpacing: '0px',"
        " measureText: (t) => ({width: t.length * 10}),"
        " fillText(t) { (this.said ||= []).push(t); }}"
    )
    found = json.dumps([box("cell phone", 0.3, 0.4, score=0.823), box("LEGO brick", 0.0, 0.1)])
    out = run_js(
        f"(() => {{ const g = {g};"
        f" m.drawLabels(g, 640, 480, {found}, {{front: 0, distanceMm: 342}});"
        " return [g.said, g.font, g.letterSpacing]; })()"
    )
    said, font, spacing = out
    assert said == ["CELL PHONE   82%   34 cm", "LEGO BRICK   80%"]  # the name in capitals
    assert "Chakra Petch" in font and spacing != "0px"  # the design's UI font, spaced out


def test_the_raspbot_page_and_the_monitor_have_the_switch_off_by_default():
    hub = REPO_ROOT / "src/lab_os/hub/web"
    page = (hub / "raspbot.html").read_text()
    monitor = (hub / "raspbot-monitor.html").read_text()
    for html in (page, monitor):
        assert 'id="labels-btn"' in html and 'aria-pressed="false"' in html
        assert ">Labels off<" in html and '<canvas id="labels"' in html
    assert 'import { labelsSwitch } from "/web/object-labels.js";' in page
    assert "ws.onopen = () => labels.reconnect();" in page  # labels on again after a reconnect
    js = (hub / "raspbot-monitor.js").read_text()
    assert "labelsSwitch({" in js and "send: link.send" in js and "labels?.reconnect()" in js
    lab = MODULE.read_text()
    assert 'send({ type: "labels", on })' in lab and "frontIndex(L.found, s?.pan_deg)" in lab
    assert 'if (L.on) send({ type: "labels", on: true })' in lab


def test_the_vr_window_asks_the_brain_and_is_off_by_default():
    js = (REPO_ROOT / "src/lab_os/hub/web/xr/raspbot.js").read_text()
    assert '{ kind: "rasp", op: "labels", label: "LABELS", ico: "i-eye" }' in js
    opened = js.split("  open(now) {")[1].split("\n  }\n")[0]
    assert "this.labels = { on: false" in opened
    assert 'this._send({ type: "labels", on })' in js
    assert 'if (this.labels.on) this._send({ type: "labels", on: true })' in js  # a reconnect
    assert "frontIndex(found, s?.pan_deg)" in js and "s?.distance_mm" in js
    assert not (WEB / "object-labels-worker.js").exists()
    assert "Worker" not in MODULE.read_text()
