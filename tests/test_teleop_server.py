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
        "/web/theme.js",
        "/web/vendor/three/three.module.js",
        "/web/vendor/urdf-loader/URDFLoader.js",
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
        "/web/vendor/three/examples/jsm/loaders/STLLoader.js",
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


def frame_at(x, grip=0.0):
    return FRAME | {"hands": {"right": FRAME["hands"]["right"] | {"pos": [x, 1, 0], "grip": grip}}}


async def next_of(ws, kind, timeout=1.0):
    for _ in range(50):
        msg = await ws.receive_json(timeout=timeout)
        if msg["type"] == kind:
            return msg
    raise AssertionError(f"no {kind} message")


async def test_only_one_page_drives_and_control_is_handed_over(aiohttp_client):
    app, loop = make_app()
    client = await aiohttp_client(app)
    a = await client.ws_connect("/ws")
    b = await client.ws_connect("/ws")
    await a.send_json(frame_at(0.1))
    assert await wait_for(lambda: loop.inputs.latest is not None)
    assert (await next_of(a, "status"))["control"] == "you"
    assert (await next_of(b, "status"))["control"] == "other"

    await b.send_json(frame_at(0.9))  # ignored: a has control
    assert (await next_of(b, "error"))["message"] == "another page has control"
    assert loop.inputs.latest.hands["right"].pos[0] == 0.1

    await b.send_json({"type": "session_end"})  # b's session ending must not freeze a
    await asyncio.sleep(0.05)
    assert loop.inputs.connected

    await a.send_json({"type": "session_end"})  # a hands control over
    assert await wait_for(lambda: not loop.inputs.connected)
    await b.send_json(frame_at(0.5))
    assert await wait_for(lambda: loop.inputs.latest.hands["right"].pos[0] == 0.5)
    assert (await next_of(b, "status"))["control"] == "you"


async def test_driver_disconnect_frees_control(aiohttp_client):
    app, loop = make_app()
    client = await aiohttp_client(app)
    a = await client.ws_connect("/ws")
    b = await client.ws_connect("/ws")
    await a.send_json(frame_at(0.1))
    assert await wait_for(lambda: loop.inputs.connected)
    await a.close()
    assert await wait_for(lambda: not loop.inputs.connected)  # dead-man freeze
    await b.send_json(frame_at(0.3))
    assert await wait_for(lambda: loop.inputs.connected)


async def test_stop_works_from_a_monitor(aiohttp_client):
    app, loop = make_app()
    client = await aiohttp_client(app)
    driver = await client.ws_connect("/ws")
    monitor = await client.ws_connect("/ws?role=monitor")
    for x in (0.0, 0.01, 0.02):
        await driver.send_json(frame_at(x, grip=1.0))
        await asyncio.sleep(0.03)
    assert await wait_for(lambda: loop.mapper.engaged)
    await monitor.send_json({"type": "stop"})
    assert await wait_for(lambda: loop.frozen and loop.mapper.needs_release)


async def test_joint_input_follows_the_same_control_rules(aiohttp_client):
    app, loop = make_app()
    client = await aiohttp_client(app)
    a = await client.ws_connect("/ws")
    b = await client.ws_connect("/ws")
    await a.send_json({"type": "joint_input", "t": 0, "rates": {"gripper": 0.5}})
    assert await wait_for(lambda: loop.inputs.latest is not None)
    await b.send_json({"type": "joint_input", "t": 0, "rates": {"gripper": -0.5}})
    assert (await next_of(b, "error"))["message"] == "another page has control"
    assert loop.inputs.latest.rates == {"gripper": 0.5}


async def test_teleop_input_is_refused_while_the_ai_tools_move(aiohttp_client):
    from lab_os.teleop.loop import Motion

    app, loop = make_app()
    client = await aiohttp_client(app)
    loop.start_motion(Motion(path=[{"shoulder_pan": 45.0}], deg_per_s=1.0))
    ws = await client.ws_connect("/ws")
    await ws.send_json({"type": "joint_input", "t": 1, "rates": {"gripper": 0.5}})
    for _ in range(50):
        m = await ws.receive_json(timeout=1)
        if m["type"] == "error":
            break
    assert m["message"] == "the AI tools have control"
    assert loop.inputs.latest is None
    await ws.send_json({"type": "stop"})  # STOP from a page still wins
    assert await wait_for(lambda: not loop.motion_active)
    await ws.close()


async def test_other_computers_only_watch_a_real_arm(aiohttp_client, monkeypatch):
    """local_control_only (a real arm served to the network): a page from another computer is a
    watcher: its input never reaches the arm, it's told why, and its STOP still works."""
    import lab_os.teleop.server as srv

    app, loop = make_app(local_control_only=True)
    client = await aiohttp_client(app)
    monkeypatch.setattr(srv, "is_local", lambda request: False)  # the test client is localhost
    ws = await client.ws_connect("/ws")
    told = await next_of(ws, "error")
    assert "view only" in told["message"]
    await ws.send_json(FRAME)
    await asyncio.sleep(0.05)
    assert loop.inputs.latest is None and app[srv.CONTROL]["ws"] is None
    await ws.send_json({"type": "stop"})
    assert await wait_for(lambda: loop.frozen)
    await ws.close()

    monkeypatch.setattr(srv, "is_local", lambda request: True)  # this computer still drives
    ws = await client.ws_connect("/ws")
    await ws.send_json(FRAME)
    assert await wait_for(lambda: loop.inputs.latest is not None)
    await ws.close()


def test_what_counts_as_this_computer():
    from types import SimpleNamespace

    from lab_os.teleop.server import is_local

    for addr, local in [
        ("127.0.0.1", True),
        ("::1", True),
        ("::ffff:127.0.0.1", True),
        ("10.0.0.7", False),
        ("192.168.1.20", False),
        (None, False),
    ]:
        assert is_local(SimpleNamespace(remote=addr)) is local, addr
