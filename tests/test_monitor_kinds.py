"""Quick job 147: one Monitor page for each kind of robot (/monitor/so101, /monitor/xarm), and
/monitor the list of them. The kind filter (arm-feed.js → armView) runs with node (else skipped).
"""

import json
import re
import shutil
import subprocess

import pytest

from lab_os import REPO_ROOT
from lab_os.hub.server import DEVICE_VIEWS, MODULES, PAGES
from lab_os.teleop.server import MONITOR_KINDS

WEB = REPO_ROOT / "src/lab_os/teleop/web"
FEED = WEB / "arm/arm-feed.js"
KINDS = WEB / "arm/kinds.js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node isn't installed")


def run(module, call: str):
    script = f"import({json.dumps(module.as_uri())}).then(m => console.log(JSON.stringify({call})))"
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def status(right_model, left_model=None):
    """A brain's status with the right arm (and a left arm) of these models."""
    s = {"type": "status", "frozen": False, "joints": {"elbow_flex": 1.0}, "limits": {}}
    s["arm"] = {"name": f"r-{right_model}", "model": right_model, "connected": True}
    s["left_arm"] = None
    if left_model:
        s["left_arm"] = {
            "name": f"l-{left_model}",
            "model": left_model,
            "connected": True,
            "frozen": True,
            "joints": {"elbow_flex": 2.0},
            "limits": {},
        }
    return s


def view(raw, side, kind):
    """The arm's name that armView gives for that side and kind (None: no such arm)."""
    got = run(FEED, f"m.armView({json.dumps(raw)}, {json.dumps(side)}, {json.dumps(kind)})")
    return got and got["arm"]["name"]


@needs_node
def test_a_kind_shows_only_its_own_arms():
    two = status("so101", "so101")
    assert view(two, "right", "so101") == "r-so101" and view(two, "left", "so101") == "l-so101"
    assert view(two, "right", "xarm") is None and view(two, "left", "xarm") is None
    # an SO-101 and an xArm at once: each page shows its own one, as its first arm
    mixed = status("so101", "xarm1s")
    assert view(mixed, "right", "xarm") == "l-xarm1s" and view(mixed, "left", "xarm") is None
    assert view(mixed, "right", "so101") == "r-so101" and view(mixed, "left", "so101") is None
    got = run(FEED, f"m.armView({json.dumps(mixed)}, 'right', 'so101').left_arm")
    assert got is None  # the SO-101 page doesn't see the xArm as its left arm
    # no kind (Arm Control, AI Control, the VR Monitor): as before
    assert view(mixed, "right", None) == "r-so101" and view(mixed, "left", None) == "l-xarm1s"


@needs_node
def test_the_kinds_and_the_addresses():
    assert run(KINDS, "Object.keys(m.KINDS)") == list(MONITOR_KINDS)
    assert run(KINDS, "[m.kindOf('so101'), m.kindOf('xarm1s'), m.kindOf('raspbot')]") == [
        "so101",
        "xarm",
        None,
    ]
    paths = ["/monitor/so101", "/monitor/xarm/", "/monitor", "/monitor/nothing", "/teleop"]
    assert run(KINDS, f"{json.dumps(paths)}.map(m.pageKind)") == ["so101", "xarm", None, None, None]
    titles = run(KINDS, "Object.values(m.KINDS).map(k => k.title)")
    assert titles == list(MONITOR_KINDS.values())


def test_every_kind_is_a_page_a_module_and_a_view():
    """All Pages, the hub's modules, Open on… and the assistant's page names (DEVICE_VIEWS)."""
    pages = {path: title for path, title, _ in PAGES}
    assert pages["/monitor"] == "Monitor"
    for kind, title in MONITOR_KINDS.items():
        assert pages[f"/monitor/{kind}"] == title
        assert MODULES[f"monitor-{kind}"] == (title, f"/monitor/{kind}")
        assert DEVICE_VIEWS[f"monitor-{kind}"] == (title, f"/monitor/{kind}")
    assert pages["/monitor/raspbot"] == "Raspbot Monitor"
    raspbot = ("Raspbot Monitor", "/monitor/raspbot")
    assert MODULES["monitor-raspbot"] == DEVICE_VIEWS["monitor-raspbot"] == raspbot
    vr = (REPO_ROOT / "src/lab_os/hub/web/xr/modules.js").read_text()
    for kind in MONITOR_KINDS:
        assert re.search(rf'"monitor-{kind}": \["[^"]+ Monitor", "i-screen"\]', vr), kind


async def test_an_unknown_kind_has_no_page(aiohttp_client):
    from lab_os.robots.fake import FakeArm
    from lab_os.teleop.loop import InputState, TeleopLoop
    from lab_os.teleop.server import create_app

    arm = FakeArm()
    arm.connect()
    client = await aiohttp_client(create_app(TeleopLoop(arm=arm, inputs=InputState())))
    assert (await client.get("/monitor/raspbot")).status == 404
    assert (await client.get("/monitor/so101")).status == 200
    listing = await (await client.get("/monitor")).text()
    assert 'id="kinds"' in listing and "/static/monitor-list.js" in listing
    js = await (await client.get("/static/monitor-list.js")).text()
    assert "lab-os-open-view" in js and "EVERY_MS = 200" in js  # the hub's module; light on a Pi
