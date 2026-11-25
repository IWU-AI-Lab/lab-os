"""The card swipe without the page in focus (quick job 113).

The lab's USB card reader types the card's data like a keyboard, then Enter. A browser page sees
those keys only while it has the focus. So on Linux the brain reads the reader's own input device
(`/dev/input/event*`) and tells the hub pages on its own computer "card". It takes the device for
itself (EVIOCGRAB): the card's data then goes to no window.

Which device is the reader: the `kind: card-reader` entry's `usb` ids in `config/devices.yaml`,
else an input device whose name says card, reader, MSR or magnetic. A plain keyboard is never
read. Reading `/dev/input/` needs the `input` group (`docs/guides/plug-in.md`).

As on the start screen (`design.html`, quick job 79): only a plain number (a student ID, with or
without the stripe's ; and ? marks) is a swipe. The data is only tested here: never stored, logged
or sent. Python-evdev does the same, but it is built from C; this needs 24 bytes per key.
"""

import asyncio
import logging
import os
import re
import struct
from collections.abc import Awaitable, Callable
from pathlib import Path

from lab_os.devices import Registry

log = logging.getLogger(__name__)

INPUT_SYS = Path("/sys/class/input")
DEV_INPUT = Path("/dev/input")
NAME_HINT = re.compile(r"card|reader|\bmsr\b|magnetic|swipe", re.I)
EVENT = struct.Struct("llHHi")  # struct input_event: time (2 longs), type, code, value
EV_KEY = 1
EVIOCGRAB = 0x40044590  # _IOW('E', 0x90, int)
LOOK_EVERY_S = 3.0
GAP_S = 0.5  # a swipe's keys come a few ms apart: a longer gap starts over
MIN_DIGITS = 4
# key codes (linux/input-event-codes.h): 1…9, 0, ; and / (? with Shift), Enter, keypad Enter
DIGITS = {2 + i: str((i + 1) % 10) for i in range(10)}
SEMICOLON, SLASH, ENTER, KP_ENTER = 39, 53, 28, 96
SHIFTS = {42, 54}
PLAIN = re.compile(rf"^;?\d{{{MIN_DIGITS},}}\??$")


def reader_ids(registry: Registry) -> set[tuple[int, int | None]]:
    """(vendor, product) of each `kind: card-reader` in devices.yaml."""
    return {
        (u.vendor_id, u.product_id)
        for d in registry.devices.values()
        if d.kind == "card-reader"
        for u in d.usb
    }


def _hex(p: Path) -> int | None:
    try:
        return int(p.read_text().strip(), 16)
    except (OSError, ValueError):
        return None


def find_readers(ids: set[tuple[int, int | None]], root: Path = INPUT_SYS) -> list[str]:
    """The event devices of the card readers plugged in ("event7"), from sysfs: one with a
    listed USB id, else one whose name says it is a card reader. Only devices with keys."""
    out = []
    for ev in sorted(root.glob("event*")):
        dev = ev / "device"
        try:
            name = (dev / "name").read_text().strip()
        except OSError:
            continue
        vendor, product = _hex(dev / "id" / "vendor"), _hex(dev / "id" / "product")
        listed = any(vendor == v and p in (None, product) for v, p in ids)
        if not (listed or NAME_HINT.search(name)):
            continue
        try:
            keys = (dev / "capabilities" / "key").read_text()
        except OSError:
            keys = ""
        if keys.strip("0 \n"):
            out.append(ev.name)
    return out


class Swipe:
    """Turns key events into swipes: `key()` returns True when Enter ends a plain number."""

    def __init__(self) -> None:
        self.data, self.shift, self.last = "", False, 0.0

    def key(self, code: int, value: int, t: float) -> bool:
        if code in SHIFTS:
            self.shift = value != 0
            return False
        if value != 1:  # 0 = up, 2 = held: only the press counts
            return False
        if t - self.last > GAP_S:
            self.data = ""
        self.last = t
        if code in (ENTER, KP_ENTER):
            data, self.data = self.data, ""
            return bool(PLAIN.match(data))
        if code in DIGITS and not self.shift:
            self.data += DIGITS[code]
        elif code == SEMICOLON and not self.shift:
            self.data += ";"
        elif code == SLASH and self.shift:
            self.data += "?"
        else:
            self.data += "\0"  # anything else: not a plain number
        return False


def _read_events(fd: int) -> list[tuple[float, int, int]]:
    """The key events waiting: (time, code, value)."""
    raw = os.read(fd, EVENT.size * 64)
    out = []
    for i in range(0, len(raw) - EVENT.size + 1, EVENT.size):
        sec, usec, typ, code, value = EVENT.unpack_from(raw, i)
        if typ == EV_KEY:
            out.append((sec + usec / 1e6, code, value))
    return out


async def _watch(path: Path, on_swipe: Callable[[], Awaitable[None]]) -> None:
    """Read one reader until it is unplugged."""
    import fcntl  # not on Windows

    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    loop = asyncio.get_running_loop()
    ready: asyncio.Queue[None] = asyncio.Queue()
    loop.add_reader(fd, ready.put_nowait, None)
    try:
        try:
            fcntl.ioctl(fd, EVIOCGRAB, 1)  # the card's data goes to no window
        except OSError as e:
            log.info("card reader %s: could not take it for the brain alone (%s)", path.name, e)
        log.info("card reader %s: the brain reads its swipes (quick job 113)", path.name)
        swipe = Swipe()
        while True:
            await ready.get()
            try:
                events = _read_events(fd)
            except BlockingIOError:
                continue
            for t, code, value in events:
                if swipe.key(code, value, t):
                    log.info("card reader: a swipe")
                    await on_swipe()
    except OSError as e:  # unplugged (ENODEV)
        log.info("card reader %s: gone (%s)", path.name, e)
    finally:
        loop.remove_reader(fd)
        os.close(fd)


async def run(
    registry: Registry,
    on_swipe: Callable[[], Awaitable[None]],
    root: Path = INPUT_SYS,
    dev: Path = DEV_INPUT,
) -> None:
    """Look for card readers every few seconds and read each one while it is plugged in."""
    ids = reader_ids(registry)
    watching: dict[str, asyncio.Task] = {}
    told: set[str] = set()
    try:
        while True:
            _look(ids, root, dev, watching, told, on_swipe)
            await asyncio.sleep(LOOK_EVERY_S)
    finally:
        for t in watching.values():
            t.cancel()


def _look(
    ids: set[tuple[int, int | None]],
    root: Path,
    dev: Path,
    watching: dict[str, asyncio.Task],
    told: set[str],
    on_swipe: Callable[[], Awaitable[None]],
) -> None:
    """Start reading each card reader that was plugged in since the last look."""
    for name in find_readers(ids, root):
        if name in watching and not watching[name].done():
            continue
        if not os.access(dev / name, os.R_OK):
            if name not in told:
                told.add(name)
                log.warning(
                    "card reader %s: no permission to read it, so a swipe starts the hub only "
                    "when its page has the focus. Run: sudo usermod -aG input $USER, then log "
                    "out and in (docs/guides/plug-in.md)",
                    name,
                )
            continue
        watching[name] = asyncio.create_task(_watch(dev / name, on_swipe))
