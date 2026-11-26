"""The devices that have the hub open (focus step 8, docs/archive/guides-2026-11-25/hub.md →
"Devices").

A *device* is a computer or screen with the hub open under a name in its address: `/?device=desk`,
`/?device=newline`, `/?device=quest`. Each hub page (a *window*; one per monitor of a device) keeps
a WebSocket to the brain (`/ws/hub-device`, docs/dev/protocol.md → "Devices"), so the brain knows
which devices are there right now and what each window shows. Nothing is remembered about a window
after it closes: when the brain restarts, the pages reconnect and the list fills again.

- **"Open on…"**: a module page opened from one device on another one's hub (inside its hub, like a
  module opened there); Back on that screen closes it. Only windows with the hub
  open are offered, so a device used for something else is never taken over.
- **No name** (quick job 101): a hub page opened without `?device=` is listed too, by its address
  (`addr-192-168-8-167`, shown as "192.168.8.167 (no device name)"), so "Open on…" can reach it.
  It keeps no settings: those need a name.
- **Monitors**: a device with the hub open on two monitors has two windows. "Open on desk" picks
  the free one (no module open); when two are free, or none, the sender is asked which.
- **Each device's settings** ("This device": level of detail, drawing resolution, sound, full
  screen, the way in to voice) are kept by the brain under the name, in the place's
  `local/hub-devices.yaml`, so every window of the device (and the next browser under that
  name) gets them.

Not here (milestone 1, "Connected lab"): robots reporting in, one brain per network.
"""

import asyncio
import hashlib
import json
import logging
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from aiohttp import WSMsgType, web

from lab_os import config

log = logging.getLogger(__name__)

NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$")
NAME_IN_LIST = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"
)  # a devices.yaml name (cameras_hidden)
WINDOW_ID = re.compile(r"^[A-Za-z0-9_-]{4,40}$")
STAGES = ("start", "hub")
FILE_NAME = "hub-devices.yaml"

# "This device" settings: key → allowed values (None = a bool, list = a list of camera names). ""
# means "not set" (the default).
SETTINGS = {
    "quality": ("", "maximal", "full", "reduced", "minimal"),
    "res": ("", "auto", "1", "0.75", "0.5"),
    "sound": None,
    "full": None,
    "startup_video": None,  # the designed hub's startup as a recording (quick job 34); off
    "voice": ("", "push-to-talk", "dictation", "wake word"),
    "wake_sensitivity": ("", *range(1, 10)),  # 1–9 (lab_os.ai.wake.SENSITIVITY); "" = 5
    "hear_in": ("", "en"),  # the assistant's languages (lab_os.ai.languages); "" = any
    "answer_in": ("", "en"),
    "cameras_hidden": list,  # the Cameras page: the cameras this device doesn't show (quick job 93)
}
MAX_LIST = 32  # a list setting: at most this many names


class DeviceError(ValueError):
    """A request the brain can't carry out; the message says why, for the page to show."""


def clean_name(name: str) -> str:
    """A device name as given in the address, checked: lowercase letters, digits and dashes."""
    name = (name or "").strip().lower()
    if not NAME.match(name):
        raise DeviceError(
            f"{name!r} isn't a device name: use lowercase letters, digits and dashes (desk, "
            "newline, quest, pi01), up to 32"
        )
    return name


def settings_file() -> Path:
    """The place's local/hub-devices.yaml (each place names its own devices; not in git)."""
    return config.local_dir() / FILE_NAME


class DeviceSettings:
    """Each device's "This device" settings, by name, in a small YAML file (written whole on each
    change; the file only holds what pages set)."""

    def __init__(self, path: Callable[[], Path] | None = None):
        self._path = path or (lambda: settings_file())  # looked up each time (tests swap it)

    def _read(self) -> dict:
        p = self._path()
        try:
            raw = yaml.safe_load(p.read_text()) if p.is_file() else None
        except (OSError, yaml.YAMLError) as e:
            log.warning("%s: %s; starting from empty settings", p, e)
            raw = None
        devices = raw.get("devices") if isinstance(raw, dict) else None
        if not isinstance(devices, dict):
            return {}
        return {str(k): dict(v) for k, v in devices.items() if isinstance(v, dict)}

    def get(self, name: str) -> dict:
        return self._read().get(clean_name(name), {})

    def update(self, name: str, changes: dict) -> dict:
        """Change some of a device's settings ("" or None = back to the default). Returns all of
        them."""
        name = clean_name(name)
        if not isinstance(changes, dict) or not changes:
            raise DeviceError('send {"setting": value, …}')
        devices = self._read()
        mine = devices.get(name, {})
        for key, value in changes.items():
            if key not in SETTINGS:
                raise DeviceError(f"{key!r} isn't a device setting ({', '.join(SETTINGS)})")
            allowed = SETTINGS[key]
            if allowed is None:
                ok = isinstance(value, bool)
            elif allowed is list:  # camera names, as devices.yaml has them
                ok = isinstance(value, list) and len(value) <= MAX_LIST
                ok = ok and all(isinstance(v, str) and NAME_IN_LIST.match(v) for v in value)
                if ok:
                    value = sorted(set(value)) or None  # an empty list: back to the default
            else:  # (True == 1 in Python: a bool is never a number setting)
                ok = not isinstance(value, bool) and value in allowed
            if value is None or value == "":
                mine.pop(key, None)
            elif ok:
                mine[key] = value
            else:
                choices = (
                    str(a) for a in (allowed if isinstance(allowed, tuple) else ()) if a != ""
                )
                want = (
                    "true or false"
                    if allowed is None
                    else f"a list of up to {MAX_LIST} device names"
                    if allowed is list
                    else ", ".join(choices)
                )
                raise DeviceError(f"{key} can be {want}, not {value!r}")
        if mine:
            devices[name] = mine
        else:
            devices.pop(name, None)
        self._write(devices)
        return mine

    def _write(self, devices: dict) -> None:
        p = self._path()
        head = (
            "# Each device's own settings (Settings → This device), kept by the brain under the\n"
            "# device's name (the ?device= in its address). Written by the hub; edit if you like.\n"
            '# docs/archive/guides-2026-11-25/hub.md → "Devices".\n'
        )
        body = yaml.safe_dump({"devices": devices}, sort_keys=True, allow_unicode=True)
        tmp = p.with_suffix(".tmp")
        p.parent.mkdir(parents=True, exist_ok=True)  # a fresh copy has no local/ folder yet
        tmp.write_text(head + body)
        tmp.replace(p)


@dataclass
class Window:
    """One hub page of a device (one per monitor)."""

    id: str
    device: str  # "" = the page has no name: it can send, but isn't offered as a place to open
    ws: web.WebSocketResponse
    address: str  # where it connected from
    stage: str = "start"
    showing: str | None = None  # the module open there (a module id), or None
    sent_from: str = ""  # the device that opened it there ("" = opened there)
    sent_from_window: str = ""
    screen: dict = field(default_factory=dict)  # label, left, top, width, height (as the page saw)
    since: float = field(default_factory=time.time)
    here: bool = False  # open on the brain's own computer (the card reader there starts it)

    @property
    def key(self) -> str:
        """The name it is listed and opened under: its device name, else one from its address."""
        return self.device or address_key(self.address)


class HubDevices:
    """The windows connected right now, by id. `modules()` gives the module ids and titles that may
    be opened (the hub's buttons)."""

    def __init__(self, modules: Callable[[], dict[str, str]], store: DeviceSettings | None = None):
        self.windows: dict[str, Window] = {}
        self.modules = modules
        self.settings = store or DeviceSettings()

    # ---------- the list ----------
    def of(self, device: str) -> list[Window]:
        wins = [w for w in self.windows.values() if w.key == device]
        return sorted(wins, key=_place)  # left to right, so the labels stay put

    def labels(self, device: str) -> dict[str, str]:
        """A short name for each window of a device: "" when it has one; else the monitor's own
        label (where the browser told it), else left / right / monitor 2, else window 2."""
        wins = self.of(device)
        if len(wins) < 2:
            return {w.id: "" for w in wins}
        lefts = sorted({w.screen.get("left", 0) for w in wins})
        out, seen = {}, {}
        for i, w in enumerate(wins):
            label = str(w.screen.get("label") or "").strip()[:40]
            if not label and len(lefts) == 2:
                label = "left monitor" if w.screen.get("left", 0) == lefts[0] else "right monitor"
            elif not label and len(lefts) > 2:
                label = f"monitor {lefts.index(w.screen.get('left', 0)) + 1}"
            elif not label:
                label = f"window {i + 1}"
            seen[label] = seen.get(label, 0) + 1
            out[w.id] = label if seen[label] == 1 else f"{label} {seen[label]}"
        return out

    def listing(self) -> list[dict]:
        """The devices with the hub open, each with its windows (what they show). A page with no
        device name is listed by its address (`title` says so)."""
        titles = self.modules()
        out = []
        for name in sorted({w.key for w in self.windows.values()}):
            labels = self.labels(name)
            wins = self.of(name)
            named = bool(wins[0].device)
            out.append(
                {
                    "name": name,
                    "title": name if named else f"{wins[0].address or 'unknown'} (no device name)",
                    "named": named,
                    "address": wins[0].address,
                    "windows": [
                        {
                            "id": w.id,
                            "label": labels[w.id],
                            "stage": w.stage,
                            "showing": (
                                {"id": w.showing, "title": titles.get(w.showing, w.showing)}
                                if w.showing
                                else None
                            ),
                            "from": w.sent_from,
                            "from_window": w.sent_from_window,
                        }
                        for w in wins
                    ],
                }
            )
        return out

    def sent(self) -> list[dict]:
        """Modules that another device opened on these screens."""
        return [
            {
                "device": d["name"],
                "window": w["id"],
                "label": w["label"],
                "showing": w["showing"],
                "from": w["from"],
                "from_window": w["from_window"],
            }
            for d in self.listing()
            for w in d["windows"]
            if w["showing"] and (w["from"] or w["from_window"])
        ]

    # ---------- telling the pages ----------
    async def _send(self, w: Window, msg: dict) -> bool:
        try:
            await w.ws.send_str(json.dumps(msg))
            return True
        except (ConnectionError, RuntimeError) as e:  # closing: it drops out of the list itself
            log.info("device %s: couldn't send (%s)", w.device or w.id, e)
            return False

    async def broadcast(self) -> None:
        msg = {"type": "devices", "devices": self.listing()}
        await asyncio.gather(*(self._send(w, msg) for w in list(self.windows.values())))

    async def tell_all(self, msg: dict) -> None:
        """One message to every hub page (e.g. lab-os is off)."""
        await asyncio.gather(*(self._send(w, msg) for w in list(self.windows.values())))

    async def tell_here(self, msg: dict) -> None:
        """One message to every hub page on the brain's own computer (a swipe, quick job 113)."""
        await asyncio.gather(*(self._send(w, msg) for w in list(self.windows.values()) if w.here))

    async def push_settings(self, device: str, values: dict) -> None:
        msg = {"type": "settings", "settings": values}
        await asyncio.gather(*(self._send(w, msg) for w in self.of(device)))

    # ---------- open or close a module ----------
    def _choices(self, device: str) -> list[dict]:
        return next((d["windows"] for d in self.listing() if d["name"] == device), [])

    async def open_on(
        self, module: str, device: str, window: str = "", sender: str = "", sender_window: str = ""
    ) -> dict:
        """Open a module on a device's hub. Returns {"ok": True, …}, or {"ok": False, "ask": […]}
        when the sender has to pick a monitor; raises DeviceError when it can't."""
        titles = self.modules()
        if module not in titles:
            raise DeviceError(
                f"{module!r} isn't a page that opens on a device ({', '.join(titles)})"
            )
        device = clean_name(device)
        wins = [w for w in self.of(device) if w.id != sender_window]
        if not wins:
            raise DeviceError(
                f"{device} doesn't have the hub open (only devices with the hub open can show a "
                "page: open it there first)"
            )
        if window:
            target = next((w for w in wins if w.id == window), None)
            if target is None:
                raise DeviceError(f"that window of {device} closed in the meantime")
        else:
            free = [w for w in wins if not w.showing]
            if len(free) != 1:
                if free:
                    why = f"{device} has {len(free)} monitors free: which one?"
                elif len(wins) == 1:
                    shown = titles.get(wins[0].showing, wins[0].showing)
                    why = f"{device} is showing {shown}: replace it?"
                else:
                    why = f"{device} is showing something on every monitor: replace which one?"
                ask = [c for c in self._choices(device) if c["id"] != sender_window]
                for c in ask:
                    c["label"] = c["label"] or device
                return {"ok": False, "ask": ask, "message": why, "device": device}
            target = free[0]
        msg = {"type": "open", "module": module, "from": sender, "from_window": sender_window}
        if not await self._send(target, msg):
            raise DeviceError(f"{device} didn't answer: it may have just closed")
        # what it shows now (the page confirms with a state message; set here too, so the list
        # is right at once)
        target.showing, target.sent_from, target.sent_from_window = module, sender, sender_window
        target.stage = "hub"
        await self.broadcast()
        label = self.labels(device).get(target.id, "")
        shown = device if target.device else f"{target.address} (no device name)"
        where = f"{shown} ({label})" if label else shown
        return {
            "ok": True,
            "device": device,
            "window": target.id,
            "label": label,
            "message": f"{titles[module]} is open on {where}.",
        }

    async def close_on(self, device: str, window: str) -> dict:
        """Close the module on a device's window."""
        device = clean_name(device)
        target = next((w for w in self.of(device) if w.id == window), None)
        if target is None:
            raise DeviceError(f"that window of {device} isn't open any more")
        module = target.showing
        await self._send(target, {"type": "close"})
        target.showing, target.sent_from, target.sent_from_window = None, "", ""
        await self.broadcast()
        return {"ok": True, "device": device, "module": module}

    # ---------- the page's connection ----------
    def apply_state(self, w: Window, msg: dict) -> None:
        if msg.get("stage") in STAGES:
            w.stage = msg["stage"]
        if "showing" in msg:
            showing = msg.get("showing")
            w.showing = str(showing)[:40] if showing else None
            w.sent_from = str(msg.get("from") or "")[:32] if w.showing else ""
            w.sent_from_window = str(msg.get("from_window") or "")[:40] if w.showing else ""
        if isinstance(msg.get("screen"), dict):
            s = msg["screen"]
            w.screen = {
                "label": str(s.get("label") or "")[:40],
                **{k: _num(s.get(k)) for k in ("left", "top", "width", "height")},
            }

    async def connection(self, request: web.Request) -> web.WebSocketResponse:
        """`/ws/hub-device?device=<name>&window=<id>`: one hub page, for as long as it's open."""
        raw_name = request.query.get("device", "")
        try:
            name = clean_name(raw_name) if raw_name else ""
        except DeviceError:
            name = ""
        wid = request.query.get("window", "")
        if not WINDOW_ID.match(wid) or wid in self.windows:  # a copied tab keeps the same id
            wid = "w-" + secrets.token_urlsafe(6)
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        w = Window(wid, name, ws, request.remote or "", here=on_this_computer(request))
        self.windows[wid] = w
        log.info("device %s connected (%s, window %s)", name or "(no name)", w.address, wid)
        try:
            settings = self.settings.get(name) if name else {}
        except DeviceError:
            settings = {}
        await self._send(
            w,
            {
                "type": "welcome",
                "device": name,
                "window": wid,
                "settings": settings,
                "devices": self.listing(),
                "why_no_name": "" if name or not raw_name else clean_name_error(raw_name),
            },
        )
        try:
            async for m in ws:
                if m.type != WSMsgType.TEXT:
                    continue
                try:
                    msg = json.loads(m.data)
                except ValueError:
                    continue
                if isinstance(msg, dict) and msg.get("type") in ("hello", "state"):
                    self.apply_state(w, msg)
                    await self.broadcast()
        finally:
            self.windows.pop(wid, None)
            log.info("device %s left (window %s)", name or "(no name)", wid)
            await self.broadcast()
        return ws


def on_this_computer(request: web.Request) -> bool:
    """Is the page on the brain's own computer: from a loopback address, or from the address it
    reached the brain at (`http://192.168.8.130:8080/` opened on the brain itself)."""
    remote = request.remote or ""
    if remote in ("127.0.0.1", "::1") or remote.startswith("127."):
        return True
    sock = request.transport.get_extra_info("sockname") if request.transport else None
    return bool(remote and sock and sock[0] == remote)


def address_key(address: str) -> str:
    """A device name for a page with none, from its address: `addr-192-168-8-167` (a device name's
    rules: lower case, digits and dashes, at most 32 characters; a long IPv6 address is hashed)."""
    plain = re.sub(r"[^a-z0-9]+", "-", (address or "unknown").lower()).strip("-")
    key = f"addr-{plain}"
    if len(key) > 32:
        key = "addr-" + hashlib.sha256(address.encode()).hexdigest()[:12]
    return key


def clean_name_error(raw: str) -> str:
    try:
        clean_name(raw)
        return ""
    except DeviceError as e:
        return str(e)


def _place(w: Window) -> tuple:
    return (w.screen.get("left", 0), w.screen.get("top", 0), w.since)


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
