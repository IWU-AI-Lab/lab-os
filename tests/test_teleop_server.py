import asyncio

from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.teleop.server import create_app

FRAME = {
    "type": "xr_input",
    "t": 1,
    "hands": {"right": {"pos": [0, 1, 0], "quat": [0, 0, 0, 1], "grip": 0.0, "trigger": 0.0}},
}


def make_app(**kw):
    arm = FakeArm()
    arm.connect()
    loop = TeleopLoop(arm=arm, inputs=InputState())
    return create_app(loop, **kw), loop


async def wait_for(cond, timeout=1.0):
    for _ in range(int(timeout / 0.01)):
        if cond():
            return True
        await asyncio.sleep(0.01)
    return False


async def test_pages_served(aiohttp_client):
    app, _ = make_app()
    client = await aiohttp_client(app)
    for path in (
        "/",
        "/monitor",
        "/static/teleop-page.js",
        "/static/link.js",
        "/static/xr.js",
        "/static/desktop-input.js",
        "/static/xr-scene.js",
        "/static/arm/arm-feed.js",
        "/static/monitor.js",
    ):
        resp = await client.get(path)
        assert resp.status == 200, path


async def test_input_reaches_loop_and_disconnect_freezes(aiohttp_client):
    app, loop = make_app()
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws")
    await ws.send_json({"type": "hello", "agent": "test"})
    await ws.send_json(FRAME)
    assert await wait_for(lambda: loop.inputs.latest is not None)
    assert loop.inputs.connected
    status = await ws.receive_json(timeout=1)
    assert status["type"] == "status"
    await ws.close()
    assert await wait_for(lambda: not loop.inputs.connected)


async def test_bad_messages_ignored(aiohttp_client):
    app, loop = make_app()
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws")
    await ws.send_str("not json")
    await ws.send_json({"type": "xr_input", "hands": "nope"})
    await ws.send_json(FRAME)
    assert await wait_for(lambda: loop.inputs.latest is not None)


async def test_monitor_cannot_drive(aiohttp_client):
    app, loop = make_app()
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws?role=monitor")
    await ws.send_json(FRAME)
    await ws.receive_json(timeout=1)  # gets status
    assert loop.inputs.latest is None


async def test_replay_mode_rejects_live_input(aiohttp_client):
    app, loop = make_app(accept_input=False)
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws")
    msg = await ws.receive_json(timeout=1)
    assert msg["type"] == "error"


async def test_model_files_served(aiohttp_client):
    app, _ = make_app()
    client = await aiohttp_client(app)
    for path in (
        "/models/so101/so101_new_calib.urdf",
        "/models/so101/assets/base_so101_v2.stl",
        "/static/vendor/three/three.module.js",
        "/static/vendor/urdf-loader/URDFLoader.js",
        "/static/arm/arm-panel.js",
    ):
        resp = await client.get(path)
        assert resp.status == 200, path


async def test_commands_broadcast_to_monitors(aiohttp_client):
    app, loop = make_app()
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws?role=monitor")
    loop._emit({"type": "arm_command", "joints": {"gripper": 12.5}, "speed_scale": 0.5})
    for _ in range(20):
        m = await ws.receive_json(timeout=1)
        if m["type"] == "arm_command":
            assert m["joints"] == {"gripper": 12.5} and m["device"] == "fake-arm"
            return
    raise AssertionError("no arm_command received")


async def test_theme_served_fresh(aiohttp_client):
    app, _ = make_app()
    client = await aiohttp_client(app)
    resp = await client.get("/theme.json")
    assert resp.status == 200
    assert resp.headers["Cache-Control"] == "no-store"
    assert (await resp.json())["colors"]["frozen"].startswith("#")


async def test_static_files_are_never_stale(aiohttp_client):
    app, _ = make_app()
    client = await aiohttp_client(app)
    for path in ("/", "/static/teleop-page.js", "/static/arm/arm-model.js"):
        resp = await client.get(path)
        assert resp.headers["Cache-Control"] == "no-cache", path
