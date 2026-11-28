"""Quick job 72: the Raspbot Control page, the brain's controller and the program on the Raspbot."""

import asyncio
import base64
import importlib.util
import io
import json
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
from PIL import Image
from test_hub_server import SRC, make_app

from lab_os.devices import Device, Registry
from lab_os.hub.raspbot_page import CAMERA, RASPBOT, CameraShare
from lab_os.hub.server import BRAIN
from lab_os.robots import raspbot
from lab_os.robots.raspbot import FakeRaspbot, RaspbotDesk, TcpRaspbot

ONBOARD = Path(raspbot.ONBOARD_DIR) / "lab_os_raspbot.py"


def onboard():
    spec = importlib.util.spec_from_file_location("lab_os_raspbot", ONBOARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- the brain's controller ----


async def test_one_page_drives_at_the_speed_cap():
    bot = FakeRaspbot()
    desk = RaspbotDesk(bot, speed=0.5)
    a, b = object(), object()
    assert await desk.press(a, "forward") == ""
    assert bot.last == ("drive", 0.5, 0.5, 0.5, 0.5)
    assert await desk.press(b, "back") == "Another page has control."
    assert bot.last == ("drive", 0.5, 0.5, 0.5, 0.5)
    assert desk.status(a)["control"] == "you" and desk.status(b)["control"] == "other"
    await desk.press(a, "left")
    assert bot.last == ("drive", -0.3, -0.3, 0.3, 0.3)  # turns spin in place, slower
    await desk.release(a)
    assert bot.last == ("stop",) and desk.status(b)["control"] == "free"
    assert await desk.press(b, "back") == ""


async def test_the_car_stops_when_input_stops():
    bot = FakeRaspbot()
    desk = RaspbotDesk(bot)
    page = object()
    await desk.press(page, "forward")
    await desk.tick()
    assert bot.last[0] == "drive"  # input is still fresh
    desk._last_input -= desk.INPUT_TIMEOUT_S + 0.1
    await desk.tick()
    assert bot.last == ("stop",) and desk.moving == ""
    assert desk.status()["wheel_speeds"] == (0, 0, 0, 0)
    assert await desk.press(page, "forward") == ""  # it kept control: a new press drives


async def test_stop_from_any_page_needs_a_new_press():
    bot = FakeRaspbot()
    desk = RaspbotDesk(bot)
    driver, watcher = object(), object()
    await desk.press(driver, "forward")
    await desk.stop("pi01")
    assert bot.last == ("stop",) and desk.driver is None
    assert "Let go" in await desk.press(driver, "forward")  # the button still held: no restart
    assert bot.last == ("stop",)
    await desk.release(driver)
    assert await desk.press(driver, "forward") == ""
    assert watcher  # (the watcher's STOP is the same call: the page sends {"type": "stop"})


async def test_not_connected_says_why():
    desk = RaspbotDesk(TcpRaspbot("raspbot1", "127.0.0.1", 9))
    why = await desk.press(object(), "forward")
    assert "raspbot1" in why and desk.moving == ""


def test_devices_yaml_gives_the_real_raspbot_else_the_fake():
    reg = Registry({"r": Device("raspbot1", "raspbot", host="10.0.0.5", port=8765, speed=0.3)})
    desk = raspbot.from_registry(reg)
    assert isinstance(desk.bot, TcpRaspbot) and desk.bot.host == "10.0.0.5"
    assert desk.speed == 0.3
    assert isinstance(raspbot.from_registry(Registry({})).bot, FakeRaspbot)


def test_deploy_copies_and_restarts_the_service():
    cmds = raspbot.deploy_commands("raspbot1")
    assert cmds[1][0] == "rsync" and cmds[1][-1] == "raspbot1:lab-os/"
    assert all(Path(f).is_file() for f in cmds[1][2:-1])
    assert "systemctl --user restart lab-os-raspbot" in cmds[2][-1]
    assert not any("sudo" in " ".join(c) for c in cmds)


# ---- the program on the Raspbot ----


def test_onboard_watchdog_and_speed_cap():
    mod = onboard()
    board = mod.FakeBoard()
    car = mod.Car(board, watchdog_s=0.05)
    car.handle({"drive": [2.0, -0.5]})  # clamped to 1.0
    assert board.speeds == {0: mod.SPEED_CAP, 1: mod.SPEED_CAP, 2: -60, 3: -60}
    assert not car.check_watchdog()
    time.sleep(0.08)
    assert car.check_watchdog() and set(board.speeds.values()) == {0}
    car.handle({"drive": [1, 1]})
    car.handle({"what": 1})  # not understood: stop
    assert set(board.speeds.values()) == {0}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def test_brain_drives_the_onboard_program_and_a_drop_stops_it():
    mod = onboard()
    board = mod.FakeBoard()
    board.distance = 325
    port = _free_port()
    server = mod.CommandServer(("127.0.0.1", port), mod.Car(board), 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    bot = TcpRaspbot("raspbot1", "127.0.0.1", port)
    task = asyncio.create_task(bot.run())
    try:
        for _ in range(50):
            if bot.distance_mm is not None:
                break
            await asyncio.sleep(0.02)
        assert bot.connected and RaspbotDesk(bot).status()["distance_mm"] == 325
        await bot.drive((0.5, -0.5, -0.5, 0.5))
        for _ in range(50):
            if board.speeds[0]:
                break
            await asyncio.sleep(0.02)
        assert tuple(board.speeds.values()) == (60, -60, -60, 60)
        task.cancel()  # the brain goes away: its connection drops
        bot._writer.close()
        for _ in range(50):
            if not board.speeds[0]:
                break
            await asyncio.sleep(0.02)
        assert set(board.speeds.values()) == {0}
    finally:
        task.cancel()
        server.shutdown()
        server.server_close()


def test_onboard_program_uses_only_the_standard_library_and_yahboom():
    src = ONBOARD.read_text()
    imports = {
        line.split()[1].split(".")[0]
        for line in src.splitlines()
        if line.strip().startswith(("import ", "from ")) and not line.startswith("    #")
    }
    allowed = (
        "argparse contextlib json logging math signal socket socketserver sys threading time http"
        " pathlib"
    )
    # lab_os_health: deployed next to it (the Pi's health for the diagnostics, quick job 135)
    assert imports <= {*allowed.split(), "cv2", "Raspbot_Lib", "lab_os_health"}, imports


# ---- the page ----


async def test_the_page_drives_the_fake_raspbot(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    html = await (await client.get("/raspbot")).text()
    assert 'id="stop"' in html and 'data-dir="forward"' in html
    bot = app[RASPBOT].bot
    async with client.ws_connect("/ws/raspbot") as ws:
        status = await ws.receive_json()
        assert status["type"] == "raspbot_status" and status["may_drive"] and status["fake"]
        assert status["pan_deg"] == status["tilt_deg"] == 0
        assert status["wheel_speeds"] == [0, 0, 0, 0]
        await ws.send_json({"type": "look", "pan": 20, "tilt": -90})
        for command, label, wheels in (
            ({"dir": "forward-left"}, "forward-left", (0, 0.5, 0.5, 0)),
            ({"dir": "stick", "stick": [0, 1, 0]}, "stick", (0.5, -0.5, -0.5, 0.5)),
        ):
            await ws.send_json({"type": "drive", **command})
            async with asyncio.timeout(2):
                while (status := await ws.receive_json()).get("moving") != label:
                    pass
            assert bot.last == ("drive", *wheels)
            assert status["wheel_speeds"] == list(wheels)
            assert (status["pan_deg"], status["tilt_deg"]) == (20, -25)
        await ws.send_str(json.dumps({"type": "stop"}))
        for _ in range(50):
            if bot.last == ("stop",):
                break
            await asyncio.sleep(0.01)
        assert bot.last == ("stop",)
        await ws.send_str(json.dumps({"type": "drive", "dir": "up"}))  # ignored, no crash
        async with asyncio.timeout(2):
            while (status := await ws.receive_json()).get("moving") != "":
                pass
        assert status["type"] == "raspbot_status"
        assert status["wheel_speeds"] == [0, 0, 0, 0]
        assert (status["pan_deg"], status["tilt_deg"]) == (20, -25)
    assert (await client.get("/api/raspbot/camera.mjpg")).status == 404


async def test_raspbot_monitor_can_stop_and_cannot_drive(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    desk = app[RASPBOT]
    async with client.ws_connect("/ws/raspbot?role=monitor") as monitor:
        status = await monitor.receive_json()
        assert status["fake"] and not status["may_drive"]
        await monitor.send_json({"type": "set_speed", "speed": 1})
        await monitor.send_json({"type": "look", "pan": 20, "tilt": 10})
        await monitor.send_json({"type": "drive", "dir": "forward"})
        async with asyncio.timeout(2):
            while (reply := await monitor.receive_json())["type"] != "error":
                pass
        assert reply["message"] == "View only."
        assert desk.speed == 0.5 and desk.bot.looked == (0, 0) and desk.driver is None
        driver = object()
        assert await desk.press(driver, "forward-right") == ""
        assert desk.bot.last == ("drive", 0.5, 0, 0, 0.5)
        await monitor.send_json({"type": "stop", "device": "observer"})
        async with asyncio.timeout(2):
            while desk.stopped_by != "observer":
                await asyncio.sleep(0.01)
        assert desk.bot.last == ("stop",) and desk.driver is None


async def test_a_real_raspbot_is_view_only_from_another_computer(aiohttp_client):
    from lab_os.hub import raspbot_page

    app = make_app(raspbot=RaspbotDesk(TcpRaspbot("raspbot1", "127.0.0.1", 9)))
    client = await aiohttp_client(app)
    req = type("R", (), {"app": app, "remote": "192.168.8.50"})()
    assert not raspbot_page.may_drive(req)
    req.remote = "127.0.0.1"
    assert raspbot_page.may_drive(req)
    assert client  # served


def test_the_page_lets_go_when_it_loses_the_keys():
    html = (SRC / "hub" / "web" / "raspbot.html").read_text()
    assert 'addEventListener("blur", releasePads)' in html and "visibilitychange" in html
    assert "pointercancel" in html and "setInterval" in html


async def test_the_camera_picture_is_relayed(aiohttp_client):
    mod = onboard()

    class StubCamera:
        def frames(self):
            yield b"\xff\xd8one\xff\xd9"  # whole JPEGs: the brain reads each picture
            yield b"\xff\xd8two\xff\xd9"

    port = _free_port()
    srv = mod.camera_server(StubCamera(), port)
    srv.server_address = ("127.0.0.1", port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    class Bot(FakeRaspbot):
        host = "127.0.0.1"

        @property
        def is_fake(self):
            return False

    bot = Bot(camera_port=port)
    client = await aiohttp_client(make_app(raspbot=RaspbotDesk(bot)))
    try:
        resp = await client.get("/api/raspbot/camera.mjpg")
        assert resp.status == 200 and "multipart/x-mixed-replace" in resp.headers["Content-Type"]
        body = await resp.read()
        # the newest picture, as one MJPEG part (both came in one read: "one" is skipped)
        assert b"Content-Length: 7\r\n\r\n\xff\xd8two\xff\xd9\r\n" in body
    finally:
        srv.shutdown()
        srv.server_close()


async def test_one_camera_connection_for_every_reader():
    opened, closed = [], []

    async def source(url):
        opened.append(url)
        try:
            for n in range(1000):
                yield b"\xff\xd8%d" % n
                await asyncio.sleep(0.01)
        finally:
            closed.append(url)

    share = CameraShare(source)

    async def read(n):
        got = []
        async for jpeg in share.frames("cam"):
            got.append(jpeg)
            if len(got) == n:
                return got

    a, b = await asyncio.gather(read(5), read(20))
    assert opened == ["cam"]  # the page, the labels and a recording: one connection
    assert len(a) == 5 and len(b) == 20 and len(set(b)) == 20  # each picture once, in order
    await asyncio.sleep(0.05)
    assert closed == ["cam"] and share.readers("cam") == 0  # the last reader left: closed
    await read(1)
    assert opened == ["cam", "cam"]  # a new reader opens it again

    async def broken(url):
        raise ConnectionError("no camera")
        yield b""

    share = CameraShare(broken)
    with pytest.raises(ConnectionError):
        await read(1)


async def test_a_slow_reader_skips_pictures_and_never_falls_behind():
    async def source(url):
        for n in range(30):
            yield b"%d" % n
            await asyncio.sleep(0.01)

    share = CameraShare(source)
    got = []
    async for jpeg in share.frames("cam"):
        got.append(int(jpeg))
        await asyncio.sleep(0.05)  # a page on slow Wi-Fi
    assert len(got) < 25 and got[-1] == 29 and got == sorted(got)  # skipped some, ends current


async def test_the_speed_slider_from_none_to_the_cap(aiohttp_client):
    bot = FakeRaspbot()
    desk = RaspbotDesk(bot, speed=0.5)
    page = object()
    assert desk.set_speed(1.5) == 1.0 and desk.set_speed(-1) == 0.0
    await desk.press(page, "forward")
    assert bot.last == ("drive", 0.0, 0.0, 0.0, 0.0)  # none: the wheels don't turn
    desk.set_speed(0.8)
    await desk.press(page, "forward")  # the held button's next repeat
    assert bot.last == ("drive", 0.8, 0.8, 0.8, 0.8) and desk.status()["speed"] == 0.8

    app = make_app()
    client = await aiohttp_client(app)
    async with client.ws_connect("/ws/raspbot") as ws:
        await ws.send_str(json.dumps({"type": "set_speed", "speed": 0.25}))
        for _ in range(30):
            status = await ws.receive_json()
            if status.get("speed") == 0.25:
                break
        assert app[RASPBOT].speed == 0.25
    html = (SRC / "hub" / "web" / "raspbot.html").read_text()
    assert 'id="speed"' in html and '"set_speed"' in html


# ---- the Raspbot's Wi-Fi at start ----


def _run_wifi(tmp_path, seen: str, active: str = "", up_fails: bool = False):
    """lab-os-wifi.sh with a fake nmcli: `seen` = the Wi-Fi names it finds."""
    import os
    import subprocess

    calls = tmp_path / "calls"
    fake = tmp_path / "nmcli"
    fake.write_text(
        "#!/bin/sh\n"
        f'echo "$*" >> {calls}\n'
        'case "$*" in\n'
        f'  *"show --active"*) printf "{active}\\n" ;;\n'
        f'  *"wifi list"*) printf "{seen}\\n" ;;\n'
        f'  *"connection up"*) exit {1 if up_fails else 0} ;;\n'
        "esac\n"
    )
    fake.chmod(0o755)
    env = os.environ | {"PATH": f"{tmp_path}:{os.environ['PATH']}", "WAIT_S": "2", "STEP_S": "1"}
    script = raspbot.ONBOARD_DIR / "lab-os-wifi.sh"
    out = subprocess.run(["sh", str(script)], env=env, capture_output=True, text=True, timeout=20)
    return out.stdout, calls.read_text().splitlines()


def test_wifi_joins_the_router_when_it_is_there(tmp_path):
    out, calls = _run_wifi(tmp_path, seen="Yahboom3\\nGL-B7-5G")
    assert "joined GL-B7-5G" in out and "connection up GL-B7-5G" in calls
    assert not any("Raspbot" in c for c in calls)


def test_wifi_already_on_the_router_does_nothing(tmp_path):
    out, calls = _run_wifi(tmp_path, seen="GL-B7-5G", active="GL-B7-5G\\nlo")
    assert "on GL-B7-5G" in out and not any("up" in c for c in calls)


def test_wifi_starts_the_hotspot_only_when_the_router_is_not_found(tmp_path):
    out, calls = _run_wifi(tmp_path, seen="GL-B7-5G-other\\nYahboom3")
    assert "starting the hotspot Raspbot" in out
    assert calls[-1] == "connection up Raspbot" and "connection up GL-B7-5G" not in calls


def test_wifi_install_turns_off_the_hotspots_own_start():
    src = (raspbot.ONBOARD_DIR / "install-wifi.sh").read_text()
    assert "modify Raspbot connection.autoconnect no" in src
    assert "systemctl enable lab-os-wifi.service" in src
    assert all(Path(f).is_file() for f in raspbot.deploy_commands("raspbot1")[1][2:-1])


# ---- the health log on the Raspbot ----


def _health():
    spec = importlib.util.spec_from_file_location(
        "lab_os_health", raspbot.ONBOARD_DIR / "lab_os_health.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_health_reads_raspbot1s_outputs():
    h = _health()
    adc = "     EXT5V_V volt(24)=5.19786000V\n  VDD_CORE_A current(7)=0.94657990A\n"
    assert h.pmic(adc, "EXT5V_V") == "5.198V" and h.pmic(adc, "VDD_CORE_A") == "0.947A"
    assert h.pmic("", "EXT5V_V") == "?"
    assert h.throttled("throttled=0x50005\n") == "0x50005" and h.throttled("") == "?"
    assert h.temperature("temp=48.3'C\n") == "48.3C"
    wireless = (
        "Inter-| sta-|   Quality\n face | tus | link level noise\n"
        " wlan0: 0000   70.  -23.  -256        0      0      0      0      0        0\n"
    )
    assert h.wifi(wireless) == "q70 -23dBm" and h.wifi("") == "none"


def test_health_log_is_kept_small(tmp_path):
    h = _health()
    log = tmp_path / "health.log"
    for i in range(5):
        h.write(f"line {i} " + "x" * 40, log, max_bytes=100)
    assert log.with_name("health.log.1").is_file() and log.stat().st_size <= 150
    assert (
        "systemctl --user restart lab-os-raspbot lab-os-health"
        in raspbot.deploy_commands("r")[2][-1]
    )


# ---- quick job 107: the hub's VR Raspbot (a stick, the camera's servos, pictures, recordings) ----


async def test_a_stick_drives_and_turns_slower():
    bot = FakeRaspbot()
    desk = RaspbotDesk(bot, speed=1.0)
    page = object()
    assert await desk.press(page, "stick", (1.0, 0.0)) == ""
    assert bot.last == ("drive", 1.0, 1.0, 1.0, 1.0)
    await desk.press(page, "stick", (0.0, 1.0))  # full right: spins like the "right" button
    assert bot.last == ("drive", 0.6, 0.6, -0.6, -0.6)
    await desk.press(page, "stick", (1.0, 1.0))  # never past the cap
    assert bot.last == ("drive", 1.0, 1.0, 0.25, 0.25)
    assert raspbot.wheel_speeds(5, 0, 0) == (1.0, 1.0, 1.0, 1.0)


async def test_look_turns_the_camera_but_never_takes_control():
    bot = FakeRaspbot()
    desk = RaspbotDesk(bot)
    a, b = object(), object()
    assert await desk.look(a, 30, -10) == "" and bot.looked == (30, -10)
    assert desk.driver is None
    await desk.look(a, 500, 0)
    assert bot.looked == (raspbot.LOOK_MAX, 0)
    await desk.press(a, "forward")
    assert await desk.look(b, 0, 0) == "Another page has control."
    await desk.stop()
    assert "STOP" in await desk.look(a, 0, 0)
    await desk.release(a)
    assert await desk.look(a, 0, 0) == ""


async def test_touch_camera_controls_hold_at_the_limit_and_reverse_at_once(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    async with client.ws_connect("/ws/raspbot") as ws:
        await ws.send_json({"type": "look", "pan": 20, "tilt": 90})
        for _ in range(3):
            await ws.send_json({"type": "look", "pan": 0, "tilt": 4, "relative": True})
        await ws.send_json({"type": "look", "pan": -4, "tilt": -4, "relative": True})
        bot = app[RASPBOT].bot
        async with asyncio.timeout(2):
            while (status := await ws.receive_json())["pan_deg"] != 16:
                pass
        assert status["tilt_deg"] == 81
        assert bot.looked == (16, 81)
        assert not bot.sent and app[RASPBOT].driver is None


def test_onboard_look_keeps_the_servo_limits():
    mod = onboard()
    board = mod.FakeBoard()
    car = mod.Car(board)
    car.handle({"drive": [1, 1]})
    car.handle({"look": [0, 0]})
    assert board.servos == {1: mod.PAN_CENTRE, 2: mod.TILT_CENTRE}
    assert board.speeds[0] == mod.SPEED_CAP  # a look keeps the wheels as they are
    car.handle({"look": [200, 200]})
    assert board.servos == {1: mod.PAN_RANGE[1], 2: mod.TILT_RANGE[1]}
    car.handle({"look": [-200, -200]})
    assert board.servos == {1: mod.PAN_RANGE[0], 2: mod.TILT_RANGE[0]}


def test_split_jpegs_keeps_a_part_picture_for_the_next_read():
    from lab_os.hub.raspbot_page import split_jpegs

    one, two = b"\xff\xd8one\xff\xd9", b"\xff\xd8two\xff\xd9"
    frames, rest = split_jpegs(b"--frame\r\n" + one + b"\r\n--frame\r\n" + two[:4])
    assert frames == [one] and rest == two[:4]
    frames, rest = split_jpegs(rest + two[4:])
    assert frames == [two]


async def test_pictures_and_recordings_are_saved_here(aiohttp_client, tmp_path):
    from lab_os.hub.raspbot_page import CAMERA

    jpeg = b"\xff\xd8pic\xff\xd9"

    async def frames(url):
        assert url == "http://127.0.0.1:8766/camera.mjpg"
        while True:
            yield jpeg
            await asyncio.sleep(0.01)

    bot = TcpRaspbot("raspbot1", "127.0.0.1", 9)
    bot.camera_port = 8766
    bot._writer = type("W", (), {"is_closing": lambda self: False})()  # connected
    bot.run = lambda: asyncio.Event().wait()  # no reconnect tries in this test
    app = make_app(raspbot=RaspbotDesk(bot))
    cam = app[CAMERA]
    cam.folder, cam.frames = (lambda: tmp_path), frames
    converted = []

    async def convert(mjpeg, count, seconds):
        converted.append((count, seconds))
        return mjpeg

    cam.convert = convert
    client = await aiohttp_client(app)
    async with client.ws_connect("/ws/raspbot") as ws:

        async def answer():
            while (m := await ws.receive_json())["type"] == "raspbot_status":
                pass
            return m

        await ws.send_json({"type": "picture"})
        m = await answer()
        assert m["what"] == "picture" and Path(m["path"]).read_bytes() == jpeg
        assert Path(m["path"]).parent == tmp_path and m["path"].startswith(str(tmp_path))
        await ws.send_json({"type": "record", "on": True})
        m = await answer()
        assert m["on"] and m["path"].endswith(".mjpeg")
        await asyncio.sleep(0.1)
        assert cam.status()["recording"]
        assert cam.status()["recording_seconds"] >= 0
        await ws.send_json({"type": "record", "on": False})
        m = await answer()
        assert not m["on"] and Path(m["path"]).read_bytes().startswith(jpeg * 2)
        assert converted and converted[0][0] >= 2 and converted[0][1] > 0
        assert cam.status()["recording"] == ""
        assert cam.status()["recording_seconds"] is None
        await ws.send_json({"type": "record", "on": True})
        await answer()
    for _ in range(50):  # the page closed: its recording ends
        if not cam.recording:
            break
        await asyncio.sleep(0.01)
    assert cam.recording is None
    bot._writer = None


async def test_a_recording_without_pictures_is_not_kept(tmp_path):
    from lab_os.hub.raspbot_page import RaspbotCamera

    async def frames(url):
        await asyncio.Event().wait()
        yield b""

    bot = TcpRaspbot("raspbot1", "127.0.0.1", 9)
    bot.camera_port = 8766
    bot._writer = type("W", (), {"is_closing": lambda self: False})()
    cam = RaspbotCamera(RaspbotDesk(bot), folder=lambda: tmp_path, frames=frames)
    path = cam.start(page=None)
    await asyncio.sleep(0.01)
    with pytest.raises(LookupError, match="no pictures"):
        await cam.stop()
    assert not path.exists() and cam.recording is None
    bot._writer = None


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
async def test_a_recording_becomes_an_mp4_at_its_real_rate(tmp_path):
    """Quick job 122: the raw .mjpeg played in no app on the lab desktop; the .mp4 plays."""
    import io

    from PIL import Image

    from lab_os.hub.raspbot_page import to_mp4

    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (200, 30, 30)).save(buf, "JPEG")
    mjpeg = tmp_path / "raspbot1_test.mjpeg"
    mjpeg.write_bytes(buf.getvalue() * 20)
    mp4 = await to_mp4(mjpeg, 20, 2.0)  # 20 pictures in 2 s → 10 per second, 2 s long
    assert mp4.suffix == ".mp4" and mp4.stat().st_size > 0 and not mjpeg.exists()
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert abs(float(out.stdout) - 2.0) < 0.3


async def test_without_ffmpeg_the_recording_stays_mjpeg(tmp_path, monkeypatch):
    from lab_os.hub import raspbot_page

    monkeypatch.setattr(raspbot_page.shutil, "which", lambda _name: None)
    mjpeg = tmp_path / "r.mjpeg"
    mjpeg.write_bytes(b"\xff\xd8x\xff\xd9")
    assert await raspbot_page.to_mp4(mjpeg, 1, 1.0) == mjpeg and mjpeg.exists()


async def test_the_fake_raspbot_has_no_camera_to_save(aiohttp_client):
    client = await aiohttp_client(make_app())
    async with client.ws_connect("/ws/raspbot") as ws:
        await ws.send_json({"type": "picture"})
        while (m := await ws.receive_json())["type"] == "raspbot_status":
            pass
        assert m == {"type": "error", "message": "The Raspbot's camera is not there now."}


async def _raspbot_tool(server, name: str, **args) -> dict:
    result = await server.call_tool(name, args)
    assert not result.is_error
    return result.structured_content or json.loads(result.content[0].text)


async def test_ai_approaches_object_and_reads_the_same_camera():
    class Bot(FakeRaspbot):
        host = "fake-camera"

    bot = Bot(distance_mm=500, camera_port=8766)
    desk = RaspbotDesk(bot, speed=1)
    app = make_app(raspbot=desk)
    server = app[BRAIN].chat.tools.server
    rgb = Image.new("RGB", (8, 8))
    image = io.BytesIO()
    rgb.save(image, format="JPEG")
    jpeg = image.getvalue()

    async def frames(url):
        assert url == "http://fake-camera:8766/camera.mjpg"
        yield jpeg

    app[CAMERA].frames = frames
    picture = await server.call_tool("raspbot_camera", {})
    assert base64.b64decode(picture.content[0].data) == jpeg
    status = await _raspbot_tool(server, "raspbot_status")
    assert status["distance_mm"] == 500 and status["camera"]

    task = asyncio.create_task(_raspbot_tool(server, "raspbot_approach"))
    try:
        async with asyncio.timeout(2):
            while not desk.moving:
                await asyncio.sleep(0.01)
        assert bot.last == ("drive", 0.25, 0.25, 0.25, 0.25)
        assert await desk.press(object(), "forward") == "Another page has control."
        bot.distance_mm = 200
        out = await asyncio.wait_for(task, 2)
        assert out["result"] == "obstacle" and out["distance_mm"] == 200
        assert bot.last == ("stop",) and desk.driver is None
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


async def test_ai_drive_stops_from_the_page_and_when_cancelled(aiohttp_client):
    bot = FakeRaspbot(distance_mm=1000)
    desk = RaspbotDesk(bot)
    app = make_app(raspbot=desk)
    server = app[BRAIN].chat.tools.server
    client = await aiohttp_client(app)
    async with await client.ws_connect("/ws/raspbot") as ws:
        for stop_from_page in (True, False):
            task = asyncio.create_task(_raspbot_tool(server, "raspbot_approach"))
            try:
                async with asyncio.timeout(2):
                    while bot.last[0] != "drive":
                        await asyncio.sleep(0.01)
                if stop_from_page:
                    await ws.send_json({"type": "stop"})
                    assert (await asyncio.wait_for(task, 2))["result"] == "stopped"
                else:
                    task.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await task
                assert bot.last == ("stop",) and desk.driver is None
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)


async def test_ai_drive_refuses_forward_without_distance_or_control():
    bot = FakeRaspbot()
    desk = RaspbotDesk(bot)
    server = make_app(raspbot=desk)[BRAIN].chat.tools.server
    out = await _raspbot_tool(server, "raspbot_drive", direction="forward")
    assert out["result"] == "refused" and "distance" in out["message"]
    assert not bot.sent
    page = object()
    await desk.press(page, "back")
    out = await _raspbot_tool(server, "raspbot_drive", direction="right", seconds=0.01)
    assert out["result"] == "refused" and "control" in out["message"]
    await desk.release(page)
    out = await _raspbot_tool(server, "raspbot_drive", direction="right", seconds=0.01)
    assert out["result"] == "done"
    assert bot.sent[-2:] == [("drive", 0.15, 0.15, -0.15, -0.15), ("stop",)]


def test_onboard_front_sensor_stops_both_drivers():
    mod = onboard()
    board = mod.FakeBoard()
    car = mod.Car(board)
    for ai in (False, True):
        board.distance = 500
        car.handle({"drive": [0.25, 0.25], "require_clear": ai})
        assert set(board.speeds.values()) == {30}
        board.distance = 200
        assert car.check_watchdog()
        assert set(board.speeds.values()) == {0}
        car.handle({"drive": [0.25, 0.25], "require_clear": ai})
        assert set(board.speeds.values()) == {0}
        board.distance = 500
        if ai:
            assert car.diagnostics()["drive_stop"] == "obstacle"
            car.handle({"drive": [0.25, 0.25], "require_clear": True})
            assert set(board.speeds.values()) == {0}
        car.stop()
    board.distance = None
    car.handle({"drive": [0.25, 0.25], "require_clear": True})
    assert car.diagnostics()["drive_stop"] == "sensor_unavailable"
    assert set(board.speeds.values()) == {0}


async def test_manual_mecanum_motion_and_front_clearance():
    bot = FakeRaspbot(distance_mm=200)
    desk = RaspbotDesk(bot, speed=1.0)
    page = object()
    assert await desk.press(page, "strafe-left") == ""
    assert bot.last == ("drive", -1, 1, 1, -1)
    assert "obstacle" in await desk.press(page, "forward-right")
    assert bot.last == ("stop",)
    assert await desk.press(page, "back-left") == ""
    assert bot.last == ("drive", -1, 0, 0, -1)
    bot.distance_mm = 500
    assert await desk.press(page, "stick", (1, 1, 1)) == ""
    assert bot.last == ("drive", 1, 0.231, -0.231, 0.538)
    bot.mecanum = False
    assert "Deploy" in await desk.press(page, "strafe-right")
    assert bot.last == ("stop",)
    assert await desk.press(page, "stick", (0, 1)) == ""
    assert bot.last == ("drive", 0.6, 0.6, -0.6, -0.6)


def test_onboard_mecanum_checks_front_clearance_during_a_diagonal():
    mod = onboard()
    board = mod.FakeBoard()
    car = mod.Car(board)
    board.distance = 500
    car.handle({"drive": [1, 0, 0, 1]})
    assert tuple(board.speeds.values()) == (120, 0, 0, 120)

    board.distance = 200
    assert car.check_watchdog()
    car.handle({"drive": [1, 0, 0, 1]})
    assert set(board.speeds.values()) == {0}
    car.handle({"drive": [1, -1, -1, 1]})
    assert tuple(board.speeds.values()) == (120, -120, -120, 120)
    assert not car.check_watchdog()
    car.handle({"drive": [0, -1, -1, 0]})
    assert tuple(board.speeds.values()) == (0, -120, -120, 0)
    assert not car.check_watchdog()


def test_the_pis_health_for_the_diagnostics():
    """Quick job 135: the program reads the Pi's power, temperature and Wi-Fi with the health
    log's parsers, and sends them with its diagnostics answer."""
    import sys

    sys.path.insert(0, str(ONBOARD.parent))
    try:
        spec = importlib.util.spec_from_file_location("lab_os_raspbot_dx", ONBOARD)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out = {
            ("vcgencmd", "get_throttled"): "throttled=0x50000\n",
            ("vcgencmd", "pmic_read_adc"): "     EXT5V_V volt(24)=5.09812000V\n",
            ("vcgencmd", "measure_temp"): "temp=48.3'C\n",
        }
        wireless = "Inter-| sta-|\n face | tus |\n wlan0: 0000   58.  -52.  -256\n"
        got = mod.pi_health(run=lambda *cmd: out[cmd], read=lambda p: wireless)
        assert got == {
            "power": "was_low",
            "input_v": 5.1,
            "temp_c": 48.3,
            "wifi_quality": 58,
            "wifi_dbm": -52,
        }
        car = mod.Car(mod.FakeBoard())
        assert "pi" not in car.diagnostics()  # nothing read yet: no pi
        mod.PI_HEALTH.update(got)
        assert car.diagnostics()["pi"]["power"] == "was_low"
        mod.PI_HEALTH.clear()
    finally:
        sys.path.remove(str(ONBOARD.parent))
