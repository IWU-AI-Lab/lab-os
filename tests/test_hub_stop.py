"""STOP on the hubs (quick job 43): shown while a real arm is connected, on the designed hub, the
plain hub and the VR hub, and a press freezes the arm. The show rule runs the page's own module
with node (skipped without node); the look was checked in Chrome and the VR preview."""

import asyncio
import json
import re
import shutil
import subprocess

import pytest
from test_hub_server import SRC, make_app

from lab_os import REPO_ROOT
from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, Motion, TeleopLoop
from lab_os.teleop.server import LOOP

MODULE = REPO_ROOT / "src/lab_os/web/stop-state.js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node isn't installed")


def stop_state(status):
    script = (
        f"import({json.dumps(MODULE.as_uri())}).then(m => "
        f"console.log(JSON.stringify(m.stopState({json.dumps(status)}))))"
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


REAL = {"name": "so101-white", "connected": True, "real": True}
SOFT = {"name": "fake-arm", "connected": True, "real": False}


@needs_node
@pytest.mark.parametrize(
    "status, show, moving",
    [
        (None, False, False),  # no status yet
        ({"arm": SOFT, "clutch": True}, False, False),  # the fake arm: no STOP
        ({"arm": REAL}, True, False),  # a real arm, holding still
        ({"arm": REAL | {"connected": False}}, False, False),  # its USB is unplugged
        ({"arm": REAL, "ai_motion": True}, True, True),  # an AI move (the wave too)
        ({"arm": REAL, "clutch": True, "frozen": False}, True, True),  # teleop drives
        ({"arm": REAL, "clutch": True, "frozen": True}, True, False),
        # two arms at once: a real left arm alone is enough, and its teleop counts
        ({"arm": SOFT, "left_arm": REAL | {"clutch": True, "frozen": False}}, True, True),
    ],
)
def test_when_the_hubs_show_stop(status, show, moving):
    assert stop_state(status) == {"show": show, "moving": moving}


def test_the_status_says_whether_an_arm_is_real():
    class Real(FakeArm):
        software = False  # like the SO-101 and xArm drivers, which don't set it

    soft, real = FakeArm(), Real(name="so101-white")
    soft.connect()
    real.connect()
    assert TeleopLoop(arm=soft, inputs=InputState()).status()["arm"]["real"] is False
    loop = TeleopLoop(arm=real, inputs=InputState())
    loop.left = TeleopLoop(arm=FakeArm(name="fake-left"), inputs=loop.inputs, is_left=True)
    loop.left.arm.connect()
    s = loop.status()
    assert s["arm"]["real"] is True and s["left_arm"]["real"] is False


def test_the_real_drivers_count_as_real():
    from lab_os.robots.so101 import SO101Arm
    from lab_os.robots.xarm import XArm

    for cls in (SO101Arm, XArm):
        assert not getattr(cls, "software", False), cls


def test_every_hub_has_stop():
    for page in ("hub/web/design.html", "hub/web/hub.js"):
        assert "/web/hub-stop.js" in (SRC / page).read_text(), page
    xr = (SRC / "hub/web/xr/hub.js").read_text()
    assert "new StopButton()" in xr and "stopShown()" in xr and "depthTest = false" in xr
    assert "stopState(s)" in (SRC / "hub/web/xr-hub.js").read_text()
    js = (SRC / "web/hub-stop.js").read_text()
    assert 'getLink("monitor")' in js and '{ type: "stop" }' in js
    # above every card, panel, module page and the start screen of the designed hub
    css = (SRC / "hub/web/design.html").read_text()
    layers = [int(z) for z in re.findall(r"z-index:\s*(\d+)", css)]
    stop_z = int(css.split("#hub-stop-wrap {")[1].split("z-index:")[1].split(";")[0])
    assert stop_z == max(z for z in layers if z < 1000)


async def test_a_watchers_stop_ends_an_ai_move(aiohttp_client):
    """What the hubs' STOP sends: {"type": "stop"} on /ws?role=monitor."""
    app = make_app()
    client = await aiohttp_client(app)
    hub = await client.ws_connect("/ws?role=monitor")
    motion = Motion(path=[{"shoulder_pan": 45.0}], deg_per_s=1.0)
    app[LOOP].start_motion(motion)
    await hub.send_json({"type": "stop"})
    await asyncio.wait_for(motion.done.wait(), 2)
    assert motion.result != "arrived" and app[LOOP].frozen
    await hub.close()
