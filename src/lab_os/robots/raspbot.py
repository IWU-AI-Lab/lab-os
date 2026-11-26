"""The Yahboom Raspbot v2 (a small car with four wheels), from the brain's side (quick job 72).

The Raspbot runs one small program, `robots/raspbot/lab_os_raspbot.py` (deployed from this repo,
`lab-os raspbot deploy`). The brain connects to it over TCP and sends one JSON line per command:

    {"drive": [left, right]}   wheel speeds, -1.0 … 1.0 (a fraction of the Raspbot's own cap)
    {"stop": true}             all motors off
    {"look": [pan, tilt]}      the camera's pan-and-tilt servos, degrees from their centre
                               (pan + = left, tilt + = up); the Raspbot keeps their limits

The Raspbot sends hello on connect. New versions advertise their servo limits and answer
{"diagnostics": true} with the ultrasonic distance in mm (or null). The Raspbot stops
the motors by itself when no command came for WATCHDOG_S, or when the connection drops, so a brain
or network that hangs never leaves the car driving.

`FakeRaspbot` is the same without a car: tests and `lab-os serve` without a Raspbot use it.
"""

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

PORT = 8765  # the program on the Raspbot listens here
WATCHDOG_S = 0.5  # the Raspbot stops its motors when no command came for this long
RECONNECT_S = 3.0
DIAGNOSTICS_S = 1.0
LOOK_MAX = 90.0  # a look command may ask for at most 90 degrees from the centre
LOOK_LIMITS = ((-90.0, 90.0), (-25.0, 85.0))  # factory mount, for older programs


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

    @property
    def is_fake(self) -> bool:
        return True

    async def run(self) -> None:
        await asyncio.Event().wait()  # nothing to connect to

    async def drive(self, left: float, right: float) -> None:
        self.sent.append(("drive", round(left, 3), round(right, 3)))

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
        self._writer: asyncio.StreamWriter | None = None
        self.said = ""  # why it isn't connected, for the page

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
            await asyncio.sleep(RECONNECT_S)

    async def _read_diagnostics(self, reader: asyncio.StreamReader) -> None:
        while self.connected:
            await self._send({"diagnostics": True})
            line = await asyncio.wait_for(reader.readline(), timeout=RECONNECT_S)
            if not line:
                return
            self.distance_mm = json.loads(line).get("distance_mm")
            await asyncio.sleep(DIAGNOSTICS_S)

    async def _send(self, msg: dict) -> None:
        if not self.connected:
            return
        writer = self._writer
        try:
            writer.write((json.dumps(msg) + "\n").encode())
            await asyncio.wait_for(writer.drain(), timeout=WATCHDOG_S)
        except (OSError, TimeoutError):  # the Raspbot's watchdog stops it; reconnect
            writer.close()

    async def drive(self, left: float, right: float) -> None:
        await self._send({"drive": [round(left, 3), round(right, 3)]})

    async def stop(self) -> None:
        await self._send({"stop": True})

    async def look(self, pan: float, tilt: float) -> None:
        await self._send({"look": [round(pan, 1), round(tilt, 1)]})


# Each button → (left, right) wheel speeds, before the speed cap. Turns spin in place, slower.
DIRECTIONS = {
    "forward": (1.0, 1.0),
    "back": (-1.0, -1.0),
    "left": (-0.6, 0.6),
    "right": (0.6, -0.6),
}
TURN = 0.6  # a stick turns as slowly as the buttons: full sideways = "left" or "right"


def stick_speeds(forward: float, turn: float) -> tuple[float, float]:
    """A stick (forward + = ahead, turn + = right; -1 … 1) → (left, right) wheel speeds, -1 … 1."""
    f, t = (max(-1.0, min(float(v), 1.0)) for v in (forward, turn))
    left, right = f + TURN * t, f - TURN * t
    big = max(1.0, abs(left), abs(right))
    return left / big, right / big


class RaspbotDesk:
    """Drives one Raspbot for the pages: one page at a time, STOP from any page, the freeze, and
    the Speed slider (one speed for every page, 0 … 1 of the program's cap).

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
            "distance_mm": self.bot.distance_mm if self.bot.connected else None,
        }
        if not self.bot.connected:
            msg["message"] = getattr(self.bot, "said", "") or f"{self.bot.name} is not connected."
        return msg

    async def press(self, page, direction: str, stick: tuple[float, float] | None = None) -> str:
        """The page holds a button, or a stick (direction "stick", `stick` = (forward, turn); the
        hub's VR Raspbot, quick job 107). Returns "" when it drives, else why not."""
        if direction not in DIRECTIONS and not (direction == "stick" and stick):
            raise ValueError(f"unknown direction {direction!r}")
        if page in self._blocked:
            return "Let go of the button after STOP, then press again."
        if self.driver is None:
            self.driver = page
            log.info("raspbot: control taken by a page")
        elif self.driver is not page:
            return "Another page has control."
        if not self.bot.connected:
            return self.status()["message"]
        self._last_input = time.monotonic()
        left, right = stick_speeds(*stick) if direction == "stick" else DIRECTIONS[direction]
        await self.bot.drive(left * self.speed, right * self.speed)
        self.moving = direction
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
        limited = tuple(
            max(low, min(float(value), high))
            for value, (low, high) in zip((pan, tilt), self.bot.look_limits, strict=True)
        )
        if relative and limited == self._look:
            return ""
        self._look = limited
        if relative:
            await self.bot.look(*limited)
        else:
            # Keep the absolute commands that the VR page already sends.
            await self.bot.look(*(max(-LOOK_MAX, min(float(v), LOOK_MAX)) for v in (pan, tilt)))
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
            await self.bot.stop()
        self.moving = ""

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
