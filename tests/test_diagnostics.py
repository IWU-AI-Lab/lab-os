"""Diagnostics for every device (quick job 135): the panels, the page, the ways in."""

from test_hub_server import SRC, make_app

from lab_os.camera_feed import _Feed
from lab_os.hub import diagnostics
from lab_os.hub.diagnostics import status_errors


def test_servo_error_flags_are_words():
    assert status_errors(0) == [] and status_errors(None) == []
    assert status_errors(0b100100) == ["temperature", "overload"]


async def test_every_device_has_a_panel(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    got = (await (await client.get("/api/diagnostics")).json())["devices"]
    arm = next(d for d in got if d["kind"] == "arm")
    assert arm["panel"]["fake"] is True and arm["panel"]["health"] == "none"
    assert [m["joint"] for m in arm["panel"]["motors"]][0] == "shoulder_pan"
    assert all(
        m["position_deg"] is not None for m in arm["panel"]["motors"]
    )  # the fake arm's positions
    robot = next(d for d in got if d["kind"] == "robot")
    assert robot["panel"]["pi"]["power"] == "ok"  # the fake Raspbot reads like a real one
    html = await (await client.get("/diagnostics")).text()
    assert 'id="grid"' in html and "/hub/diagnostics.js" in html
    assert (await client.get("/hub/diagnostics.js")).status == 200
    hub = await (await client.get("/api/hub")).json()
    assert "/diagnostics" in {p["path"] for p in hub["pages"]}  # All Pages
    assert {"id": "diagnostics", "title": "Diagnostics", "page": "/diagnostics"} in hub["views"]


def test_an_arms_motors_read_hot_and_errors():
    class Arm:
        name, model, joint_names = "so101-white", "so101", ("elbow_flex", "gripper")

        def read_health(self): ...

    class Loop:
        arm, arm_connected, arm_problem, frozen = Arm(), True, None, False
        health_ok, _health_t, _last_joints = True, 100.0, {"elbow_flex": 12.34, "gripper": 5.0}
        health = {
            "elbow_flex": {"temp_c": 61.0, "load_pct": 20.0, "volts": 12.0, "status": 0},
            "gripper": {"temp_c": 35.0, "load_pct": 3.0, "volts": 12.0, "status": 0b100000},
        }

    panel = diagnostics.arm_panel(Loop(), now=103.0)
    elbow, grip = panel["motors"]
    assert elbow["state"] == "bad" and elbow["position_deg"] == 12.3  # past HOT_C
    assert grip["errors"] == ["overload"] and grip["state"] == "bad"
    assert panel["health"] == "ok" and panel["read_s_ago"] == 3.0 and panel["fake"] is False


def test_a_cameras_picture_rate():
    class Cap:
        def release(self): ...

    feed = _Feed("/dev/video0", Cap(), encode=lambda f, w: b"")
    assert feed.rate() == 0.0
    import time

    now = time.monotonic()
    feed.reads.extend(now - 1.0 + i * 0.1 for i in range(11))  # 10 frames in a second
    assert feed.rate() == 10.0


def test_the_ways_in():
    """From the hub's device card, the Command Center's modules and by voice (pagesHere)."""
    hub = (SRC / "hub" / "web" / "design.html").read_text()
    assert "data-dx" in hub and 'S.pageArg = d.id.replace(/^screen:/, "")' in hub
    assert "?show=${encodeURIComponent(arg)}" in hub
    assert 'out.diagnostics = "Diagnostics' in hub and "showPage(ev.page, ev.device" in hub
    cc = (SRC / "hub" / "web" / "command-center.js").read_text()
    assert '"diagnostics"' in cc and "?show=" in cc
    page = (SRC / "hub" / "web" / "diagnostics.js").read_text()
    assert "export function pick(devices, words)" in page
