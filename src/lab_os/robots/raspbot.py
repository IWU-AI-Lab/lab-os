"""The Yahboom Raspbot v2 (a small car with four wheels), from the brain's side (quick job 72).

The Raspbot runs one small program, `robots/raspbot/lab_os_raspbot.py` (deployed from this repo,
`lab-os raspbot deploy`). The brain connects to it over TCP and sends one JSON line per command:

    {"drive": [fl, rl, fr, rr]}  wheel speeds, -1.0 … 1.0 (a fraction of the Raspbot's own cap)
    {"drive": [left, right]}   same speed for both wheels on each side (legacy)
    {"stop": true}             all motors off
    {"look": [pan, tilt]}      the camera's pan-and-tilt servos, degrees from their centre
                               (pan + = left, tilt + = up); the Raspbot keeps their limits

The Raspbot sends hello on connect. New versions advertise their servo limits and answer
{"diagnostics": true} with the ultrasonic distance in mm (or null), and (quick job 135) the Pi's
power, temperature and Wi-Fi. The Raspbot stops
the motors by itself when no command came for WATCHDOG_S, or when the connection drops, so a brain
or network that hangs never leaves the car driving.

`FakeRaspbot` is the same without a car: tests and `lab-os serve` without a Raspbot use it.
"""

import asyncio
import json
import logging
import math
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

PORT = 8765  # the program on the Raspbot listens here
WATCHDOG_S = 0.5  # the Raspbot stops its motors when no command came for this long
RECONNECT_S = 3.0
DIAGNOSTICS_S = 0.1
LEGACY_DIAGNOSTICS_S = 1.0
DISTANCE_MAX_AGE_S = 0.3
OBSTACLE_STOP_MM = 200
AI_SPEED_LIMIT = 0.25  # a fraction of the onboard speed cap, independent of the page slider
LOOK_MAX = 90.0  # a look command may ask for at most 90 degrees from the centre
LOOK_LIMITS = ((-90.0, 90.0), (-25.0, 85.0))  # factory mount, for older programs
# the Pi's health in a diagnostics answer (quick job 135; newer programs): power ok / low / was_low
PI_KEYS = ("power", "input_v", "temp_c", "wifi_quality", "wifi_dbm")


@dataclass
class FakeRaspbot:
    """A Raspbot without a car: keeps the last command, for tests and the page without a car."""

    name: str = "fake-raspbot"
    connected: bool = True
    camera_port: int = 0
    sent: list = field(default_factory=list)
    looked: tuple = (0.0, 0.0)  # the camera's last look
    distance_mm: int | None = None
    look_limits = LOOK_LIMITS
    obstacle_stop_mm = OBSTACLE_STOP_MM
    drive_stop = ""
    mecanum = True
    host = ""
    round_trip_ms = 0
    # the diagnostics panel shows the same readings as a real car's (quick job 135)
    pi = {"power": "ok", "input_v": 5.1, "temp_c": 45.0, "wifi_quality": 70, "wifi_dbm": -40}

    @property
    def is_fake(self) -> bool:
        return True

    async def run(self) -> None:
        await asyncio.Event().wait()  # nothing to connect to

    @property
    def fresh_distance_mm(self) -> int | None:
        return self.distance_mm if self.connected else None

    async def drive(self, wheels: tuple[float, ...], *, require_clear: bool = False) -> None:
        self.sent.append(("drive", *(round(speed, 3) for speed in wheels)))

    async def stop(self) -> None:
        self.sent.append(("stop",))

    async def look(self, pan: float, tilt: float) -> None:
        self.looked = (round(pan, 1), round(tilt, 1))

    @property
    def last(self) -> tuple:
        return self.sent[-1] if self.sent else ("stop",)


class TcpRaspbot:
    """The real Raspbot: one TCP connection to its program, made again when it drops."""

    def __init__(self, name: str, host: str, port: int = PORT) -> None:
        self.name = name
        self.host = host
        self.port = port
        self.camera_port = 0
        self.distance_mm: int | None = None
        self.look_limits = LOOK_LIMITS
        self.obstacle_stop_mm: int | None = None
        self.drive_stop = ""
        self.mecanum = False
        self._distance_at = 0.0
        self._writer: asyncio.StreamWriter | None = None
        self.said = ""  # why it isn't connected, for the page
        self.round_trip_ms: int | None = (
            None  # a diagnostics question and its answer (quick job 135)
        )
        self.pi: dict = {}  # the Pi's power, temperature and Wi-Fi, from newer programs

    @property
    def is_fake(self) -> bool:
        return False

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def run(self) -> None:
        """Keep the connection: connect, wait until it drops, try again every RECONNECT_S."""
        while True:
            writer = None
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), timeout=RECONNECT_S
                )
                hello = json.loads(await asyncio.wait_for(reader.readline(), timeout=RECONNECT_S))
                self.camera_port = int(hello.get("camera_port") or 0)
                self.look_limits = hello.get("look_limits", LOOK_LIMITS)
                stop_mm = hello.get("obstacle_stop_mm")
                self.obstacle_stop_mm = stop_mm if type(stop_mm) is int and stop_mm > 0 else None
                self.mecanum = hello.get("mecanum") is True
                self._writer = writer
                self.said = ""
                log.info("%s connected (%s:%s)", self.name, self.host, self.port)
                if hello.get("diagnostics"):
                    await self._read_diagnostics(reader)
                else:
                    await reader.read()  # older programs send nothing else
                log.info("%s disconnected", self.name)
            except (OSError, TimeoutError, ValueError) as e:
                self.said = f"{self.name} does not answer. Is it on, and is its program running?"
                log.debug("%s: %s", self.name, e)
            finally:
                if writer:
                    writer.close()
                self._writer = None
                self.distance_mm = None
                self.obstacle_stop_mm = None
                self.drive_stop = ""
                self.mecanum = False
                self._distance_at = 0.0
                self.round_trip_ms, self.pi = None, {}
            await asyncio.sleep(RECONNECT_S)

    async def _read_diagnostics(self, reader: asyncio.StreamReader) -> None:
        while self.connected:
            asked = time.monotonic()
            await self._send({"diagnostics": True})
            line = await asyncio.wait_for(reader.readline(), timeout=RECONNECT_S)
            if not line:
                return
            report = json.loads(line)
            self.round_trip_ms = round((time.monotonic() - asked) * 1000)
            pi = report.get("pi")
            self.pi = {k: v for k, v in pi.items() if k in PI_KEYS} if isinstance(pi, dict) else {}
            distance = report.get("distance_mm")
            self.distance_mm = distance if type(distance) is int and 0 < distance < 0xFFFF else None
            reason = report.get("drive_stop")
            self.drive_stop = (
                reason if reason in ("obstacle", "sensor_unavailable", "input_timeout") else ""
            )
            self._distance_at = time.monotonic()
            await asyncio.sleep(DIAGNOSTICS_S if self.obstacle_stop_mm else LEGACY_DIAGNOSTICS_S)

    async def _send(self, msg: dict) -> None:
        if not self.connected:
            return
        writer = self._writer
        try:
            writer.write((json.dumps(msg) + "\n").encode())
            await asyncio.wait_for(writer.drain(), timeout=WATCHDOG_S)
        except (OSError, TimeoutError):  # the Raspbot's watchdog stops it; reconnect
            writer.close()

    @property
    def fresh_distance_mm(self) -> int | None:
        if self.connected and time.monotonic() - self._distance_at <= DISTANCE_MAX_AGE_S:
            return self.distance_mm
        return None

    async def drive(self, wheels: tuple[float, ...], *, require_clear: bool = False) -> None:
        msg = {"drive": wheels if self.mecanum else wheels[::2]}
        if require_clear:
            msg["require_clear"] = True
        await self._send(msg)

    async def stop(self) -> None:
        await self._send({"stop": True})

    async def look(self, pan: float, tilt: float) -> None:
        await self._send({"look": [round(pan, 1), round(tilt, 1)]})


# Each button → (forward, sideways right, turn right) before the speed cap.
DIRECTIONS = {
    "forward": (1.0, 0.0, 0.0),
    "back": (-1.0, 0.0, 0.0),
    "left": (0.0, 0.0, -1.0),
    "right": (0.0, 0.0, 1.0),
    "strafe-left": (0.0, -1.0, 0.0),
    "strafe-right": (0.0, 1.0, 0.0),
    "forward-left": (1.0, -1.0, 0.0),
    "forward-right": (1.0, 1.0, 0.0),
    "back-left": (-1.0, -1.0, 0.0),
    "back-right": (-1.0, 1.0, 0.0),
}
TURN = 0.6  # keep the existing slower turn speed
STOPPED_WHEELS = (0.0, 0.0, 0.0, 0.0)


def wheel_speeds(forward: float, sideways: float, turn: float) -> tuple[float, ...]:
    """Mix the three axes in motor order (front left, rear left, front right, rear right)."""
    if not all(math.isfinite(axis) for axis in (forward, sideways, turn)):
        raise ValueError("drive axes must be finite")
    forward, sideways, turn = (max(-1.0, min(axis, 1.0)) for axis in (forward, sideways, turn))
    turn *= TURN
    sideways_plus_turn, sideways_minus_turn = sideways + turn, sideways - turn
    wheels = (
        forward + sideways_plus_turn,
        forward - sideways_minus_turn,
        forward - sideways_plus_turn,
        forward + sideways_minus_turn,
    )
    peak = max(1.0, *(abs(speed) for speed in wheels))
    return tuple(speed / peak for speed in wheels)


class RaspbotDesk:
    """Drives one Raspbot for the pages and AI tools. They share control, STOP, the freeze,
    and the Speed slider (0 … 1 of the program's cap).

    A page drives by sending its button again and again while it is held (every 100 ms). The
    first page to drive while nobody does has control, until it lets go or closes. When the
    driver's input stops for INPUT_TIMEOUT_S (a page that hangs, a lost Wi-Fi), the car stops.
    STOP stops the car and frees control; the page must let go of the button before it drives
    again (a held button does not start the car again after STOP)."""

    INPUT_TIMEOUT_S = 0.3
    TICK_S = 0.1

    def __init__(self, bot, speed: float = 0.5) -> None:
        self.bot = bot
        self.speed = 0.5
        self.set_speed(speed)
        self.driver = None  # the page that drives, or None
        self.moving = ""  # the direction now, "" = stopped
        self._last_input = 0.0
        self._blocked: set = set()  # pages that held a button at STOP: they must let go first
        self._look = (0.0, 0.0)
        self._wheels = STOPPED_WHEELS
        self.stopped_by = ""  # the last STOP's page, for the status line

    def status(self, page=None) -> dict:
        control = "free" if self.driver is None else "you" if self.driver is page else "other"
        msg = {
            "type": "raspbot_status",
            "name": self.bot.name,
            "fake": self.bot.is_fake,
            "connected": self.bot.connected,
            "moving": self.moving,
            "control": control,
            "camera": bool(self.bot.camera_port),
            "speed": self.speed,
            "pan_deg": round(self._look[0], 1),
            "tilt_deg": round(self._look[1], 1),
            "wheel_speeds": (
                self._wheels if self.bot.connected and not self.bot.drive_stop else STOPPED_WHEELS
            ),
            "distance_mm": (
                self.bot.distance_mm
                if self.bot.connected and not self.bot.obstacle_stop_mm
                else self.bot.fresh_distance_mm
            ),
            "obstacle_stop_mm": self.bot.obstacle_stop_mm if self.bot.connected else None,
        }
        if not self.bot.connected:
            msg["message"] = getattr(self.bot, "said", "") or f"{self.bot.name} is not connected."
        return msg

    async def press(
        self,
        page,
        direction: str,
        stick: tuple[float, ...] | None = None,
        *,
        ai: bool = False,
    ) -> str:
        """Drive from a held button or stick. Return an empty string on success."""
        if direction == "stick" and stick is not None:
            if len(stick) not in (2, 3):
                raise ValueError("expected two or three drive axes")
            forward, turn = stick[0], stick[-1]
            sideways = stick[1] if len(stick) == 3 else 0.0
        elif direction in DIRECTIONS:
            forward, sideways, turn = DIRECTIONS[direction]
        else:
            raise ValueError(f"unknown direction {direction!r}")
        wheels = wheel_speeds(forward, sideways, turn)
        if page in self._blocked:
            return "Let go of the button after STOP, then press again."
        if self.driver is not None and self.driver is not page:
            return "Another page has control."
        if not self.bot.connected:
            return self.status()["message"]
        if sideways and not self.bot.mecanum:
            await self._halt()
            return "Deploy the current Raspbot program to drive sideways or diagonally."
        limit = self.bot.obstacle_stop_mm
        if ai and limit is None:
            return "Deploy the current Raspbot program before driving with AI."
        if (
            ai
            and self.driver is page
            and time.monotonic() - self._last_input > self.INPUT_TIMEOUT_S
        ):
            await self._halt()
            return "The drive input stopped."
        if forward > 0:
            distance = self.bot.fresh_distance_mm
            if limit is not None and distance is not None and distance <= limit:
                await self._halt()
                return "The ultrasonic sensor sees an obstacle ahead."
            if ai and distance is None:
                await self._halt()
                return "The ultrasonic sensor has no current distance."
        speed = min(self.speed, AI_SPEED_LIMIT) if ai else self.speed
        if ai and speed == 0:
            return "Set the Raspbot Speed above zero."
        if self.driver is None:
            self.driver = page
            log.info("raspbot: control taken by %s", "an AI tool" if ai else "a page")
        self._last_input = time.monotonic()
        self.moving = direction
        self._wheels = tuple(wheel * speed for wheel in wheels)
        await self.bot.drive(self._wheels, require_clear=ai)
        return ""

    async def look(self, page, pan: float, tilt: float, *, relative: bool = False) -> str:
        """Turn the camera (degrees from its centre). Any page that may drive, while no other page
        has control. It never takes control, and the freeze is for the wheels only: the camera
        stays where it was looking. Returns "" when sent, else why not."""
        if page in self._blocked:
            return "Let go of the stick after STOP, then move it again."
        if self.driver is not None and self.driver is not page:
            return "Another page has control."
        if not self.bot.connected:
            return self.status()["message"]
        if relative:
            pan += self._look[0]
            tilt += self._look[1]
        else:
            pan, tilt = (max(-LOOK_MAX, min(float(value), LOOK_MAX)) for value in (pan, tilt))
        limited = tuple(
            max(low, min(float(value), high))
            for value, (low, high) in zip((pan, tilt), self.bot.look_limits, strict=True)
        )
        if relative and limited == self._look:
            return ""
        self._look = limited
        await self.bot.look(*limited)
        return ""

    def set_speed(self, speed: float) -> float:
        """The Speed slider: 0 (none) … 1 (the program's own cap). A held button takes it at its
        next repeat (100 ms)."""
        self.speed = round(max(0.0, min(float(speed), 1.0)), 3)
        return self.speed

    async def release(self, page) -> None:
        """The page let go of every button (or closed): stop, and free control."""
        self._blocked.discard(page)
        if self.driver is page:
            self.driver = None
            await self._halt()

    async def stop(self, by: str = "") -> None:
        """STOP, from any page: the car stops now; whoever drove must let go and press again."""
        if self.driver is not None:
            self._blocked.add(self.driver)
        self.driver = None
        self.stopped_by = by
        log.info("raspbot: STOP pressed%s", f" ({by})" if by else "")
        await self._halt(always=True)

    async def _halt(self, always: bool = False) -> None:
        if self.moving or always:
            self.moving = ""
            self._wheels = STOPPED_WHEELS
            await self.bot.stop()

    async def tick(self) -> None:
        """The freeze: the driver's input stopped coming, so the car stops (it keeps control)."""
        if self.moving and time.monotonic() - self._last_input > self.INPUT_TIMEOUT_S:
            log.info("raspbot: input stopped, the car stops")
            await self._halt()

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self.TICK_S)
            await self.tick()


def from_registry(registry) -> RaspbotDesk:
    """The first `kind: raspbot` device in devices.yaml, or the fake one when there is none."""
    for d in registry.devices.values():
        if d.kind == "raspbot":
            return RaspbotDesk(TcpRaspbot(d.name, d.host or d.name, d.port or PORT), d.speed)
    return RaspbotDesk(FakeRaspbot())


ONBOARD_DIR = Path(__file__).parents[3] / "robots" / "raspbot"
SERVICE = "lab-os-raspbot"
HEALTH = "lab-os-health"  # the health log (lab_os_health.py), for raspbot1's stops
WIFI_FILES = ("lab-os-wifi.sh", "lab-os-wifi.service", "install-wifi.sh")


def deploy_commands(host: str) -> list[list[str]]:
    """rsync the program, the health log and their services to the Raspbot, then (re)start both
    services there. The program only listens: starting it never moves the car."""
    units = f"{SERVICE} {HEALTH}"
    start = (
        "mkdir -p ~/.config/systemd/user && "
        f"mv ~/lab-os/{SERVICE}.service ~/lab-os/{HEALTH}.service ~/.config/systemd/user/ && "
        "systemctl --user daemon-reload && "
        f"systemctl --user enable {units} && systemctl --user restart {units} && "
        f"sleep 1 && systemctl --user is-active {units}"
    )
    # the Wi-Fi files are only copied: install-wifi.sh needs sudo, once (docs/guides/raspbot.md)
    names = ["lab_os_raspbot.py", f"{SERVICE}.service", "lab_os_health.py", f"{HEALTH}.service"]
    names += WIFI_FILES
    files = [str(ONBOARD_DIR / n) for n in names]
    return [
        ["ssh", host, "mkdir -p ~/lab-os"],
        ["rsync", "-t", *files, f"{host}:lab-os/"],
        ["ssh", host, start],
    ]


def deploy(host: str = "raspbot1") -> int:
    """`lab-os raspbot deploy`: 0 when the program runs on the Raspbot."""
    for cmd in deploy_commands(host):
        if subprocess.run(cmd).returncode != 0:
            print(f"Failed: {' '.join(cmd[:2])} … (docs/guides/raspbot.md)")
            return 1
    print(f"lab-os's program runs on {host}. Open the Raspbot page: /raspbot")
    return 0
