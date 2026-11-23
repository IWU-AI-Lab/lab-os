"""Quick job 72: the Raspbot page, the brain's controller and the program on the Raspbot."""

import asyncio
import importlib.util
import json
import socket
import threading
import time
from pathlib import Path

from test_hub_server import SRC, make_app

from lab_os.devices import Device, Registry
from lab_os.hub.raspbot_page import RASPBOT
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
    assert bot.last == ("drive", 0.5, 0.5)
    assert await desk.press(b, "back") == "Another page has control."
    assert bot.last == ("drive", 0.5, 0.5)
    assert desk.status(a)["control"] == "you" and desk.status(b)["control"] == "other"
    await desk.press(a, "left")
    assert bot.last == ("drive", -0.3, 0.3)  # turns spin in place, slower
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
    port = _free_port()
    server = mod.CommandServer(("127.0.0.1", port), mod.Car(board), 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    bot = TcpRaspbot("raspbot1", "127.0.0.1", port)
    task = asyncio.create_task(bot.run())
    try:
        for _ in range(50):
            if bot.connected:
                break
            await asyncio.sleep(0.02)
        assert bot.connected
        await bot.drive(0.5, 0.5)
        for _ in range(50):
            if board.speeds[0]:
                break
            await asyncio.sleep(0.02)
        assert board.speeds[0] == round(0.5 * mod.SPEED_CAP)
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
    allowed = "argparse contextlib json logging signal socket socketserver sys threading time http"
    assert imports <= {*allowed.split(), "cv2", "Raspbot_Lib"}, imports


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
        await ws.send_str(json.dumps({"type": "drive", "dir": "forward"}))
        for _ in range(50):
            if bot.sent:
                break
            await asyncio.sleep(0.01)
        assert bot.last[0] == "drive"
        await ws.send_str(json.dumps({"type": "stop"}))
        for _ in range(50):
            if bot.last == ("stop",):
                break
            await asyncio.sleep(0.01)
        assert bot.last == ("stop",)
        await ws.send_str(json.dumps({"type": "drive", "dir": "up"}))  # ignored, no crash
        assert (await ws.receive_json())["type"] == "raspbot_status"
    assert (await client.get("/api/raspbot/camera.mjpg")).status == 404


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
    assert 'addEventListener("blur", letGo)' in html and "visibilitychange" in html
    assert "pointercancel" in html and "setInterval" in html


async def test_the_camera_picture_is_relayed(aiohttp_client):
    mod = onboard()

    class StubCamera:
        def frames(self):
            yield b"\xff\xd8one"
            yield b"\xff\xd8two"

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
        assert b"one" in body and b"two" in body
    finally:
        srv.shutdown()
        srv.server_close()


async def test_the_speed_slider_from_none_to_the_cap(aiohttp_client):
    bot = FakeRaspbot()
    desk = RaspbotDesk(bot, speed=0.5)
    page = object()
    assert desk.set_speed(1.5) == 1.0 and desk.set_speed(-1) == 0.0
    await desk.press(page, "forward")
    assert bot.last == ("drive", 0.0, 0.0)  # none: the wheels don't turn
    desk.set_speed(0.8)
    await desk.press(page, "forward")  # the held button's next repeat
    assert bot.last == ("drive", 0.8, 0.8) and desk.status()["speed"] == 0.8

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
