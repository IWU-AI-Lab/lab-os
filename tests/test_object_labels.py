"""Labels on what the Raspbot sees, in VR and AR (quick job 128). The detector itself ran in
headless Chrome on MediaPipe's test picture (the PR); here: which object gets the ultrasonic
distance, the label's words, and the rules of the VR window. Node tests skip without node."""

import hashlib
import json
import shutil
import subprocess

import pytest

from lab_os import REPO_ROOT

WEB = REPO_ROOT / "src/lab_os/web"
MODULE = WEB / "object-labels.js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node isn't installed")


def run(expr: str):
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
    assert run(f"m.frontIndex({f}, 0)") == 1  # the chair: over the middle, the biggest
    assert run(f"m.frontIndex({f}, -12)") == 1
    # the camera turned away: the sensor on the car's front does not measure what it sees
    assert run(f"m.frontIndex({f}, 40)") == -1
    assert run(f"m.frontIndex({f}, undefined)") == 1  # no angle known: the centre
    assert run(f"m.frontIndex({json.dumps([box('cup', 0.1, 0.2)])}, 0)") == -1
    assert run("m.frontIndex([], 0)") == -1


@needs_node
def test_the_label_says_the_name_how_sure_and_the_distance():
    f = json.dumps(box("cell phone", 0.1, 0.2, score=0.823))
    assert run(f"m.labelText({f}, null)") == "Cell phone   82%"
    assert run(f"m.labelText({f}, 342)") == "Cell phone   82%   34 cm"


def test_the_vr_window_has_the_switch_off_by_default():
    js = (REPO_ROOT / "src/lab_os/hub/web/xr/raspbot.js").read_text()
    assert '{ kind: "rasp", op: "labels", label: "LABELS", ico: "i-eye" }' in js
    opened = js.split("  open(now) {")[1].split("\n  }\n")[0]
    assert "this.labels = new ObjectLabels();" in opened and "setOn(true)" not in opened
    closed = js.split("  close() {")[1].split("\n  }\n")[0]
    assert "this.labels?.close();" in closed  # the worker stops with the window
    assert "frontIndex(found, s?.pan_deg)" in js and "s?.distance_mm" in js


def test_the_detector_runs_off_the_page_and_offline():
    lab = (WEB / "object-labels.js").read_text()
    assert 'new Worker("/web/object-labels-worker.js", { type: "module" })' in lab
    worker = (WEB / "object-labels-worker.js").read_text()
    assert "http" not in worker.replace("fetch(url)", "")  # nothing from the internet
    assert "/efficientdet_lite0.tflite" in worker and 'runningMode: "IMAGE"' in worker
    model = WEB / "vendor/mediapipe/efficientdet_lite0.tflite"
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    assert digest == "4b59100025bea1235a84c1038879a6cccc9f6c49f5e41144e91e74d99e780993"
    readme = (WEB / "vendor/README.md").read_text()
    assert "efficientdet_lite0/float16/1" in readme
