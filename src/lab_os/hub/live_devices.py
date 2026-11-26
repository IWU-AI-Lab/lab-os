"""The brain's live device list (quick job 109): what is plugged in or connected now, and every
device seen here since the list was last cleared.

One list for the Devices panel, Monitor, the Cameras page and the assistant: the arms (and their
motors' power, for the arms the brain drives), the cameras, every other USB device (an unknown one
shows what the system says it is: its maker and product), raspbot1, the Quest (adb) and every open
hub screen. The brain looks every `EVERY_S` (Linux: `/sys`, opens nothing), so a plug, an unplug,
a connect or a disconnect shows within a few seconds.

**Seen devices** are kept in the place's `local/seen-devices.yaml` (not in git): the list starts
empty in each place and gets each device the first time it is seen. A person can take one off the
list ("Remove"); a device that is still connected then stays off it until it connects again.
`config/devices.yaml` stays the list of known devices: how lab-os recognizes and drives each one.
"""

import logging
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from lab_os import config
from lab_os.activity import Activity
from lab_os.devices import Registry, socket_on_hub, unknown_camera_name

log = logging.getLogger(__name__)

EVERY_S = 2.0
FILE_NAME = "seen-devices.yaml"
USB_SYS = Path("/sys/bus/usb/devices")
VIDEO_SYS = Path("/sys/class/video4linux")
HUB_CLASS = "09"  # USB hubs: not a device a person plugs in for itself
# built into the computer (the desktop's Bluetooth, its keyboard light; quick job 141): not listed
FIXED = "fixed"
ARM_KINDS = ("so101", "so101-leader", "xarm1s")
DETAILS = ("name", "kind", "known", "what", "via", "model")
STORED = (*DETAILS, "first_seen", "last_seen")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")


# ---------- what the computer sees (Linux; elsewhere nothing) ----------
def _read(p: Path) -> str:
    try:
        return p.read_text().strip()
    except OSError:
        return ""


def socket_of(usb_name: str) -> str:
    """The USB socket of a sysfs device name, as /dev/v4l/by-path/ writes it: "1-7.2" → "usb-0:7.2"
    (by-path leaves out the bus number; the controller tells two buses apart)."""
    return "usb-0:" + usb_name.split("-", 1)[1] if "-" in usb_name else ""


def usb_devices(root: Path = USB_SYS) -> list[dict]:
    """Every USB device plugged in (not the hubs, not the parts built into the computer), from
    sysfs: vendor_id, product_id, serial_number, manufacturer, product_string (hidapi's names), usb
    (its sysfs name), socket."""
    out = []
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        return out
    for name in entries:
        if ":" in name or name.startswith("usb"):
            continue  # an interface, or a controller's root hub
        d = root / name
        if _read(d / "bDeviceClass") == HUB_CLASS or _read(d / "removable") == FIXED:
            continue
        try:
            vid, pid = int(_read(d / "idVendor"), 16), int(_read(d / "idProduct"), 16)
        except ValueError:
            continue
        out.append(
            {
                "vendor_id": vid,
                "product_id": pid,
                "serial_number": _read(d / "serial"),
                "manufacturer": _read(d / "manufacturer"),
                "product_string": _read(d / "product"),
                "usb": name,
                "socket": socket_of(name),
            }
        )
    return out


def video_cameras(root: Path = VIDEO_SYS) -> list[dict]:
    """Every USB camera's picture device: video ("/dev/video0"), title (its own name), usb (the
    USB device it belongs to, a sysfs name) and socket. Opens nothing."""
    out = []
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        return out
    for name in entries:
        v = root / name
        if _read(v / "index") not in ("", "0"):
            continue  # the metadata half of a camera
        usb = (v / "device").resolve().parent.name  # the interface's parent: "1-7"
        if not re.match(r"^\d+-[\d.]+$", usb):
            continue  # not a USB camera
        out.append({"video": f"/dev/{name}", "title": _read(v / "name"), "usb": usb})
    seen, uniq = set(), []
    for c in out:  # one picture device per camera
        if c["usb"] not in seen:
            seen.add(c["usb"])
            uniq.append(c | {"socket": socket_of(c["usb"])})
    return uniq


# ---------- known or unknown ----------
def _maker(info: dict) -> str:
    words = " ".join(w for w in (info.get("manufacturer"), info.get("product_string")) if w)
    ids = f"USB {info['vendor_id']:04x}:{info['product_id']:04x}"
    return f"{words} ({ids})" if words else ids


def _serial_in(info: dict, ports: tuple[str, ...]) -> bool:
    serial = info.get("serial_number") or ""
    return bool(serial) and any(serial in p for p in ports)


def identify(
    registry: Registry, usb: list[dict], cameras: list[dict], prefer: Callable[[str], int]
) -> list[dict]:
    """The USB devices plugged in now, each as a list entry: a device in devices.yaml by its name,
    every other one as unknown. A camera is one entry (its USB device isn't listed again). Two
    names for one camera's socket (or port of an arm's hub): the lowest `prefer` rank (the camera
    of the arm in use), then not borrowed, then devices.yaml's order. Off-limits ones are left
    out."""
    out = []
    arm_socket: dict[str, str] = {}
    cam_usb = {c["usb"]: c for c in cameras}
    for info in usb:
        cam = cam_usb.get(info["usb"])
        if cam:
            continue  # below, as a camera
        dev = next(
            (
                d
                for d in registry.devices.values()
                if d.kind != "camera"
                and (
                    any(u.matches(info) for u in d.usb)
                    or _serial_in(info, d.ports)
                    or (d.serial and d.serial == info.get("serial_number"))
                )
            ),
            None,
        )
        if dev and dev.off_limits:
            continue
        if dev:
            arm_socket[dev.name] = info["socket"]  # its cameras may be on its hub (quick job 115)
        if dev:
            kind = (
                "arm" if dev.kind in ARM_KINDS else "headset" if dev.kind == "quest" else dev.kind
            )
            out.append(
                {
                    "id": dev.name,
                    "name": dev.name,
                    "kind": kind,
                    "known": True,
                    "what": _first_line(dev.notes) or dev.kind,
                    "via": "USB",
                    "borrowed": dev.borrowed,
                    "leader": dev.kind == "so101-leader",
                    "model": dev.kind,  # devices.yaml's kind (the Command Center's modules)
                }
            )
        else:
            out.append(
                {
                    "id": f"usb:{info['vendor_id']:04x}:{info['product_id']:04x}:"
                    + (info["serial_number"] or info["socket"]),
                    "name": info["product_string"] or "Unknown USB device",
                    "kind": "usb",
                    "known": False,
                    "what": f"Unknown: {_maker(info)}",
                    "via": "USB",
                }
            )
    for cam in cameras:
        names = [
            d.name
            for d in registry.devices.values()
            if d.kind == "camera"
            and cam["socket"] in (d.socket, socket_on_hub(arm_socket.get(d.beside, ""), d.hub_port))
        ]
        if any(registry.devices[n].off_limits for n in names):
            continue
        if names:
            names.sort(key=lambda n: (prefer(n), registry.devices[n].borrowed))  # then yaml order
            dev = registry.devices[names[0]]
            out.append(
                {
                    "id": f"camera:{cam['socket']}",
                    "name": names[0],
                    "names": names,
                    "kind": "camera",
                    "known": True,
                    "what": _first_line(dev.notes) or cam["title"],
                    "via": "USB",
                    "borrowed": dev.borrowed,
                }
            )
        else:
            out.append(
                {
                    "id": f"camera:{cam['socket']}",
                    "name": unknown_camera_name(cam["socket"]),
                    "names": [unknown_camera_name(cam["socket"])],
                    "kind": "camera",
                    "known": False,
                    "what": f"Unknown camera: {cam['title'] or 'no name'}",
                    "via": "USB",
                }
            )
    return out


def _first_line(text: str) -> str:
    text = " ".join((text or "").split())
    m = re.match(r"^(.{1,140}?[.!?])(\s|$)", text)
    return m.group(1) if m else text[:140]


# ---------- the list, and the seen devices ----------
def seen_file() -> Path:
    return config.local_dir() / FILE_NAME


class SeenStore:
    """The seen devices, by id, in a small YAML file (written whole on each change)."""

    def __init__(self, path: Callable[[], Path] | None = None):
        self._path = path or seen_file

    def read(self) -> dict[str, dict]:
        p = self._path()
        try:
            raw = yaml.safe_load(p.read_text()) if p.is_file() else None
        except (OSError, yaml.YAMLError) as e:
            log.warning("%s: %s; starting from an empty list", p, e)
            raw = None
        devices = raw.get("devices") if isinstance(raw, dict) else None
        if not isinstance(devices, dict):
            return {}
        return {str(k): dict(v) for k, v in devices.items() if isinstance(v, dict)}

    def write(self, devices: dict[str, dict]) -> None:
        p = self._path()
        head = (
            "# Every device the brain has seen here (the Devices panel). Written by the brain;\n"
            "# remove a device on the panel, or delete this file to start the list again.\n"
        )
        body = yaml.safe_dump({"devices": devices}, sort_keys=True, allow_unicode=True)
        tmp = p.with_suffix(".tmp")
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(head + body)
            tmp.replace(p)
        except OSError as e:
            log.warning("%s: %s; the seen devices are not kept", p, e)


@dataclass
class LiveDevices:
    """The devices connected now (`now`, by id) and the ones seen before (`seen`). `update()` takes
    a fresh look and says whether the list changed."""

    store: SeenStore = field(default_factory=SeenStore)
    clock: Callable[[], float] = time.time
    now: dict[str, dict] = field(default_factory=dict)
    seen: dict[str, dict] | None = None  # read on first use
    dismissed: set[str] = field(default_factory=set)  # removed while connected
    activity: Activity | None = None  # the Command Center's activity list (quick job 149)

    def _seen(self) -> dict[str, dict]:
        if self.seen is None:
            self.seen = self.store.read()
        return self.seen

    def update(self, found: list[dict]) -> bool:
        """The devices connected now. New ones are added to the seen list; one that went keeps its
        last time. True: something a page shows changed."""
        seen, stamp = self._seen(), _stamp(self.clock())
        fresh = {d["id"]: d for d in found if ID.match(str(d.get("id", "")))}
        came, went = fresh.keys() - self.now.keys(), self.now.keys() - fresh.keys()
        wrote = False
        for i in came:
            self.dismissed.discard(i)  # connected again: back on the list
            d = fresh[i]
            entry = seen.get(i, {"first_seen": stamp})
            entry |= {k: d[k] for k in DETAILS if k in d}
            entry["last_seen"] = stamp
            seen[i] = entry
            wrote = True
            log.info("device %s connected (%s)", d.get("name", i), d.get("what", ""))
            if self.activity is not None and d.get("kind") != "screen":  # screens: "opened the hub"
                self.activity.add(f"{d.get('name') or i} connected")
        for i in went:
            if i in seen:
                seen[i]["last_seen"] = stamp
                wrote = True
            log.info("device %s disconnected", self.now[i].get("name", i))
            if self.activity is not None and self.now[i].get("kind") != "screen":
                self.activity.add(f"{self.now[i].get('name') or i} disconnected")
        for i in fresh.keys() & self.now.keys():  # a camera's name can change with its arm
            for k in DETAILS:
                if i in seen and k in fresh[i] and seen[i].get(k) != fresh[i][k]:
                    seen[i][k] = fresh[i][k]
                    wrote = True
        changed = bool(came or went) or fresh != self.now
        self.now = fresh
        if wrote:
            self.store.write({i: {k: e[k] for k in STORED if k in e} for i, e in seen.items()})
        return changed

    def remove(self, device_id: str) -> bool:
        """Take a device off the list. A device that is connected now stays off it until it
        connects again. False: no such device on the list."""
        seen = self._seen()
        if device_id not in seen:
            return False
        del seen[device_id]
        if device_id in self.now:
            self.dismissed.add(device_id)
        self.store.write({i: {k: e[k] for k in STORED if k in e} for i, e in seen.items()})
        return True

    def listing(self) -> list[dict]:
        """Every seen device (not removed), with `connected` and what is known now: connected
        first, then by kind and name."""
        out = []
        for i, entry in self._seen().items():
            live = self.now.get(i)
            out.append(
                {"id": i, **{k: entry.get(k) for k in STORED}}
                | (live or {})
                | {"connected": live is not None}
            )
        out.sort(key=lambda d: (not d["connected"], d.get("kind") or "", d.get("name") or ""))
        return out

    def connected(self) -> list[dict]:
        """The devices connected now (removed ones too: they are still there)."""
        return [d | {"connected": True} for d in self.now.values()]


def _stamp(t: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t))
