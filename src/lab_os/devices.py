"""Robot registry (<place>/devices.yaml) and device-access safety checks.

Every real robot driver must get its port through `serial_port()` (or at least pass it through
`check_port_allowed()`), or its USB device through `find_usb_device()`, before opening it. That's
what keeps off-limits devices closed. Devices are identified by USB ID + serial number, the same on
Linux, Windows and macOS (decision 2026-10-27); OS paths are only resolved at run time.

The registry is the place's devices.yaml (lab_os.config). The off-limits and borrowed devices of
the repo's own config/devices.yaml are added at every place, so switching to another config folder
can never make them openable or take their rules away.

**Borrowed** devices (`borrowed: true`: the green arms and their cameras, another project's) may be
driven and used, with AGENTS.md's rules: no motor setup or calibration (lab_os.robots.so101_setup
refuses them), their training calibration read only from LeRobot's cache, and never a port or
camera that another program has open (`check_not_in_use`, used for every device we open,
borrowed or not).
"""

import logging
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from lab_os import config

log = logging.getLogger(__name__)

BY_ID_DIR = "/dev/serial/by-id/"
BY_PATH_DIR = "/dev/v4l/by-path/"  # cameras by USB socket: identical cameras share a serial
SYS_DIR = "/sys"  # Linux's device tree: which hub and USB controller a device is on (quick job 115)


class PortNotAllowed(RuntimeError):
    """Raised when code tries to use a port it must not open."""


class InUse(PortNotAllowed):
    """Raised when another program has the port or camera open (LeLab, a recording, ...)."""


@dataclass(frozen=True)
class UsbId:
    """How a device identifies itself over USB. Empty/None fields match anything."""

    vendor_id: int
    product_id: int | None = None
    product: str = ""
    serial: str = ""

    def matches(self, info: dict) -> bool:
        """Does a hidapi/pyserial-style info dict (vendor_id, product_id, ...) fit this entry?"""
        return (
            info.get("vendor_id") == self.vendor_id
            and self.product_id in (None, info.get("product_id"))
            and self.product in ("", info.get("product_string"))
            and self.serial in ("", info.get("serial_number"))
        )


@dataclass(frozen=True)
class Device:
    name: str
    kind: str
    off_limits: bool = False
    ports: tuple[str, ...] = ()
    usb: tuple[UsbId, ...] = ()
    notes: str = ""
    borrowed: bool = False  # another project's: drive/use it, never set it up (AGENTS.md)
    # borrowed arms: the training calibration in LeRobot's cache (read only, the source of truth),
    # e.g. "robots/so_follower/sheep.json"; lab-os drives with its copy in calibration/<name>/
    training_calibration: str = ""
    socket: str = ""  # cameras: the USB socket in /dev/v4l/by-path/ names, e.g. "usb-0:7"
    # cameras on an arm's USB hub (quick job 115): the arm, and the camera's port on that hub
    # ("2"; "4.1" for a hub inside the hub). The name then follows the arm to any socket.
    beside: str = ""
    hub_port: str = ""
    # arms: the table's height in the arm's own numbers (cm; its z = 0 is the bottom of its base).
    # An arm standing on a plate has a negative one (so101-white: -1.6, quick job 28).
    table_z_cm: float = 0.0
    # arms: degrees added to a joint's reading so the model matches the real arm (quick job 106:
    # so101-white's shoulder_lift reads 4.7° too far forward). Goals get the same back.
    # (joint, degrees) pairs: a tuple, so the frozen Device stays hashable.
    joint_offsets_deg: tuple[tuple[str, float], ...] = ()
    serial: str = ""  # headsets: the serial adb lists (the Quest's view, quick job 36)
    mirror: tuple[str, ...] = ()  # headsets: extra scrcpy options for its view (crop, window)
    host: str = ""  # network robots (the Raspbot): its name or address; "" = the device's name.
    # Headsets: the address on the router's Wi-Fi, for Quest view without the cable (quick job 103)
    port: int = 0  # network robots: the port its program listens on; 0 = the robot's default
    speed: float = 0.5  # the Raspbot: the Speed slider at start, 0 … 1 of its program's speed cap


@dataclass(frozen=True)
class Registry:
    devices: dict[str, Device] = field(default_factory=dict)

    def off_limits_ports(self) -> set[str]:
        return {p for d in self.devices.values() if d.off_limits for p in d.ports}

    def off_limits_serials(self) -> set[str]:
        """USB serial numbers of off-limits arms: the same on every OS, unlike port names."""
        return {u.serial for d in self.devices.values() if d.off_limits for u in d.usb if u.serial}

    def borrowed_serials(self) -> set[str]:
        """USB serial numbers of borrowed boards: the motor setup tool refuses them by serial too,
        whatever name a config gives them."""
        return {u.serial for d in self.devices.values() if d.borrowed for u in d.usb if u.serial}

    def off_limits_owner(self, info: dict) -> str | None:
        """Name of the off-limits device this USB device belongs to, or None. An entry without a
        serial blocks every device of that model (e.g. the training cameras share a serial)."""
        for d in self.devices.values():
            if d.off_limits and any(u.matches(info) for u in d.usb):
                return d.name
        return None


def check_usb_allowed(info: dict, registry: Registry | None = None) -> None:
    """Raise PortNotAllowed if this enumerated USB device belongs to an off-limits device."""
    registry = registry or load_registry()
    if (info.get("serial_number") or "") in registry.off_limits_serials():
        raise PortNotAllowed(f"USB device {info.get('path')!r} has an off-limits serial number.")
    owner = registry.off_limits_owner(info)
    if owner:
        raise PortNotAllowed(f"USB device {info.get('path')!r} belongs to {owner}. Never open it.")


def _read_devices(path: Path) -> dict[str, Device]:
    raw = yaml.safe_load(path.read_text()) or {}
    return {
        name: Device(
            name=name,
            kind=spec["kind"],
            off_limits=bool(spec.get("off_limits", False)),
            ports=tuple(spec.get("ports") or ()),
            usb=tuple(UsbId(**u) for u in (spec.get("usb") or ())),
            notes=spec.get("notes", ""),
            borrowed=bool(spec.get("borrowed", False)),
            training_calibration=spec.get("training_calibration", ""),
            socket=spec.get("socket", ""),
            beside=str(spec.get("beside") or ""),
            hub_port=str(spec.get("hub_port") or ""),
            table_z_cm=float(spec.get("table_z_cm", 0.0)),
            joint_offsets_deg=tuple(
                (str(j), float(v)) for j, v in (spec.get("joint_offsets_deg") or {}).items()
            ),
            serial=str(spec.get("serial") or ""),
            mirror=tuple(str(a) for a in (spec.get("mirror") or ())),
            host=str(spec.get("host") or ""),
            port=int(spec.get("port") or 0),
            speed=float(spec.get("speed", 0.5)),
        )
        for name, spec in (raw.get("devices") or {}).items()
    }


def load_registry(path: Path | None = None) -> Registry:
    """The place's devices, plus the lab's off-limits and borrowed ones (always: a config never
    weakens them)."""
    path = path or config.place_path("devices.yaml")
    if not path.is_file():
        raise config.ConfigError(
            f"{path.parent} has no devices.yaml: start one with `lab-os new-place {path.parent}`"
        )
    devices = _read_devices(path)
    lab = config.DEFAULT_DIR / "devices.yaml"
    if lab.is_file() and lab.resolve() != path.resolve():
        for name, device in _read_devices(lab).items():
            if not (device.off_limits or device.borrowed):
                continue
            mine = devices.get(name)
            if mine and mine.off_limits and mine != device:
                devices[f"{name} (repo config)"] = device  # both entries stay protected
            else:
                devices[name] = device  # added, or replaces a weaker entry
    return Registry(devices)


def table_z_cm(name: str, registry: Registry | None = None) -> float:
    """The table's height in this arm's own numbers (cm, `table_z_cm` in devices.yaml); 0 for an
    arm not listed (the software arms) or when the place has no devices.yaml."""
    try:
        registry = registry or load_registry()
    except (OSError, ValueError, config.ConfigError) as e:
        log.warning("devices.yaml: %s; heights measured from the arm's base", e)
        return 0.0
    device = registry.devices.get(name)
    return device.table_z_cm if device else 0.0


def default_device(kinds: tuple[str, ...], registry: Registry | None = None) -> str:
    """The name of the place's only usable device of these kinds (for command-line defaults), or
    a LookupError that lists the choices. Borrowed devices are never a default: name them."""
    registry = registry or load_registry()
    names = [
        d.name
        for d in registry.devices.values()
        if d.kind in kinds and not d.off_limits and not d.borrowed and (d.ports or d.usb)
    ]
    if len(names) != 1:
        found = ", ".join(names) or "none"
        raise LookupError(f"which {'/'.join(kinds)} device? Name one (devices.yaml has: {found})")
    return names[0]


def port_exists(path: str) -> bool:
    """Is this serial port there now (the device plugged in)? The tests replace it."""
    return os.path.exists(path)


def plugged_in_arms(
    registry: Registry, active: list[str] | tuple[str, ...], borrowed: bool = False
) -> list[str]:
    """The SO-101 followers plugged in now that `lab-os serve` may take without being told
    (quick job 61), in devices.yaml's order: active in the venue, not off limits, and not
    borrowed (the green set). `borrowed=True`: only the borrowed ones (the green set as the
    left arm beside another one, the builder 2026-11-21; never alone)."""
    return [
        d.name
        for d in registry.devices.values()
        if d.kind == "so101"
        and not d.off_limits
        and d.borrowed == borrowed
        and d.name in active
        and any(port_exists(p) for p in d.ports)
    ]


def check_port_allowed(port: str, registry: Registry | None = None) -> None:
    """Raise PortNotAllowed unless `port` is a by-id path that doesn't belong to an off-limits arm.

    Also compares resolved targets, so a by-id symlink that currently points at the same tty as a
    forbidden one is refused too.
    """
    registry = registry or load_registry()
    if not port.startswith(BY_ID_DIR):
        raise PortNotAllowed(
            f"{port!r}: use a {BY_ID_DIR} path; ttyACM/ttyUSB numbers swap (docs/dev/GOTCHAS.md)"
        )
    for serial in registry.off_limits_serials():
        if serial in port:
            raise PortNotAllowed(f"{port!r} has an off-limits arm's serial number. Never open it.")
    forbidden = registry.off_limits_ports()
    forbidden_targets = {os.path.realpath(p) for p in forbidden if os.path.exists(p)}
    if port in forbidden or (os.path.exists(port) and os.path.realpath(port) in forbidden_targets):
        raise PortNotAllowed(f"{port!r} belongs to an off-limits device. Never open it.")


def serial_port(name: str, registry: Registry | None = None) -> str:
    """Return the by-id serial port for device `name`, after the safety checks."""
    registry = registry or load_registry()
    device = registry.devices.get(name)
    if device is None:
        raise KeyError(f"unknown device {name!r}; add it to devices.yaml (docs/dev/places.md)")
    if device.off_limits:
        raise PortNotAllowed(f"{name} is off limits: {device.notes}")
    if len(device.ports) != 1:
        raise LookupError(f"{name} needs exactly one port in devices.yaml")
    port = device.ports[0]
    check_port_allowed(port, registry)
    return port


# ---- one program per port ---------------------------------------------------------------------
def _users_from_proc(target: str, proc: Path) -> list[str]:
    """Programs with `target` open, from /proc/<pid>/fd links (Linux; opens nothing). Processes
    we may not look into (other users, root) are skipped: on the lab desktop LeLab and training
    runs are the builder's own."""
    users = []
    me = str(os.getpid())
    for pid_dir in proc.iterdir():
        if not pid_dir.name.isdigit() or pid_dir.name == me:
            continue
        try:
            fds = list((pid_dir / "fd").iterdir())
        except OSError:
            continue
        for fd in fds:
            try:
                if os.path.realpath(os.readlink(fd)) == target:
                    break
            except OSError:
                continue
        else:
            continue
        try:
            name = (pid_dir / "comm").read_text().strip()
        except OSError:
            name = "a program"
        users.append(f"{name} (pid {pid_dir.name})")
    return users


def _users_from_lsof(target: str) -> list[str] | None:
    """macOS and others without /proc: `lsof -F pc <file>` (lists, opens nothing)."""
    lsof = shutil.which("lsof")
    if not lsof:
        return None
    try:
        out = subprocess.run(
            [lsof, "-F", "pc", target], capture_output=True, text=True, timeout=5
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    users, pid = [], ""
    for line in out.splitlines():
        if line.startswith("p"):
            pid = line[1:]
        elif line.startswith("c") and pid != str(os.getpid()):
            users.append(f"{line[1:]} (pid {pid})")
    return users


def users_of(path: str, proc: Path = Path("/proc")) -> list[str] | None:
    """Which other programs have this device open: ["lelab (pid 4242)", ...], [] for none, None
    when this computer can't tell. Follows symlinks (by-id / by-path names)."""
    target = os.path.realpath(path)
    if proc.is_dir():
        return _users_from_proc(target, proc)
    return _users_from_lsof(target)


def check_not_in_use(name: str, paths: list[str], proc: Path = Path("/proc")) -> None:
    """Raise InUse with a sentence if another program has any of these device files open.
    Run right before opening a port or a camera (AGENTS.md: one program per port)."""
    for path in paths:
        users = users_of(path, proc)
        if users is None:
            log.warning("%s: can't tell here whether another program uses %s", name, path)
        elif users:
            raise InUse(
                f"{name} is in use by {', '.join(users)}: one program per port. Stop that program "
                "(LeLab, a recording or a training run) first, then try again."
            )


# ---- cameras (by USB socket, or by their port on the arm's hub) -------------------------------
def usb_device_dir(port: str, sys_dir: str = SYS_DIR) -> str:
    """The sysfs folder of the USB device behind serial port `port` (a by-id link), for example
    /sys/devices/pci0000:00/0000:00:14.0/usb1/1-7/1-7.1. "" when it isn't there."""
    tty = os.path.basename(os.path.realpath(port))
    iface = os.path.join(sys_dir, "class", "tty", tty, "device")
    if not os.path.exists(iface):
        return ""
    return os.path.dirname(os.path.realpath(iface))


def controller_of(usb_dir: str) -> str:
    """The PCI name of the USB controller above a sysfs USB folder ("0000:00:14.0"): the part
    before "usbN", as /dev/v4l/by-path/ names start ("pci-0000:00:14.0-usb-…")."""
    parts = usb_dir.split(os.sep)
    for i, part in enumerate(parts):
        if part.startswith("usb") and part[3:].isdigit() and i:
            return parts[i - 1]
    return ""


def chain_of(usb_dir: str) -> str:
    """The port chain of a sysfs USB folder: "1-7.1" → "7.1" (socket 7, port 1 of its hub)."""
    name = os.path.basename(usb_dir)
    return name.split("-", 1)[1] if "-" in name else ""


def _beside_socket(device: Device, registry: Registry, sys_dir: str) -> tuple[str, str]:
    """(controller, chain) of a camera on its arm's hub: the arm's chain minus its own port, then
    the camera's `hub_port`. Raises LookupError with what to do."""
    arm = registry.devices.get(device.beside)
    if arm is None or not arm.ports:
        raise LookupError(
            f"{device.name}: beside {device.beside}, which has no port in devices.yaml"
        )
    if not device.hub_port:
        raise LookupError(f"{device.name}: beside {device.beside} needs a hub_port in devices.yaml")
    usb = usb_device_dir(arm.ports[0], sys_dir) if os.path.exists(arm.ports[0]) else ""
    if not usb:
        raise LookupError(
            f"{device.name}: {device.beside} is not plugged in, so its USB hub is not known"
        )
    chain = chain_of(usb)
    if "." not in chain:
        raise LookupError(
            f"{device.name}: {device.beside} is not on a USB hub (it is in the computer's socket "
            f"{chain}). Plug the arm and its cameras into one hub."
        )
    return controller_of(usb), f"{chain.rsplit('.', 1)[0]}.{device.hub_port}"


def camera_paths(
    name: str,
    registry: Registry | None = None,
    by_path: str = BY_PATH_DIR,
    sys_dir: str = SYS_DIR,
) -> list[str]:
    """Every /dev/v4l/by-path/ name of camera `name` (a camera has two: its picture and its
    metadata), picture first. Lists folders; opens nothing."""
    registry = registry or load_registry()
    device = registry.devices.get(name)
    if device is None:
        raise KeyError(f"unknown device {name!r}; add it to devices.yaml (docs/dev/places.md)")
    if device.off_limits:
        raise PortNotAllowed(f"{name} is off limits: {device.notes}")
    if device.kind != "camera" or not (device.socket or device.beside):
        raise LookupError(
            f"{name} needs kind: camera and a socket (e.g. usb-0:7) or beside + hub_port "
            "in devices.yaml"
        )
    if device.beside:
        controller, chain = _beside_socket(device, registry, sys_dir)
        where = f"port {device.hub_port} of {device.beside}'s hub"
    else:
        controller, chain = "", device.socket.removeprefix("usb-").removeprefix("0:")
        where = f"socket {device.socket}"
    try:
        entries = sorted(os.listdir(by_path))
    except OSError:
        entries = []
    # "pci-0000:00:14.0-usb-0:7:1.0-video-index0" (newer udev also adds "usbv2-0:7:...")
    mine = [e for e in entries if any(f"-{u}-0:{chain}:" in e for u in ("usb", "usbv2", "usbv3"))]
    if controller:
        mine = [e for e in mine if e.startswith(f"pci-{controller}-")]
    controllers = {e.split("-usb")[0] for e in mine}
    if not mine:
        raise LookupError(f"{name}: no camera in {where} (plugged in? lab-os usb shows them)")
    if len(controllers) > 1:
        raise LookupError(f"{name}: {where} matches several USB controllers")
    pictures = [e for e in mine if e.endswith("index0")]
    return [os.path.join(by_path, e) for e in pictures + [e for e in mine if e not in pictures]]


def camera_device(
    name: str,
    registry: Registry | None = None,
    by_path: str = BY_PATH_DIR,
    proc: Path = Path("/proc"),
    sys_dir: str = SYS_DIR,
) -> str:
    """The by-path name to open for camera `name`'s picture, after the checks: listed, not off
    limits, plugged in, and no other program using it (LeLab, a recording)."""
    paths = camera_paths(name, registry, by_path, sys_dir)
    check_not_in_use(name, paths, proc)
    return paths[0]


def hid_enumerate(vendor_id: int, product_id: int) -> list[dict]:
    """List HID devices with this USB ID (reads descriptors only; opens nothing)."""
    import hid  # imported late so tests and non-HID work don't need the native library

    return hid.enumerate(vendor_id, product_id)


def find_usb_device(
    name: str,
    registry: Registry | None = None,
    enumerate_fn: Callable[[int, int], list[dict]] = hid_enumerate,
) -> dict:
    """Return the hidapi info dict (with `path`) of HID device `name`, matched by USB ID + serial.

    Refuses off-limits devices, and anything whose serial belongs to one. Works the same on Linux,
    Windows and macOS; `enumerate_fn` is replaceable for tests.
    """
    registry = registry or load_registry()
    device = registry.devices.get(name)
    if device is None:
        raise KeyError(f"unknown device {name!r}; add it to devices.yaml (docs/dev/places.md)")
    if device.off_limits:
        raise PortNotAllowed(f"{name} is off limits: {device.notes}")
    if len(device.usb) != 1 or device.usb[0].product_id is None:
        raise LookupError(f"{name} needs exactly one usb entry with vendor_id and product_id")
    spec = device.usb[0]
    found = []
    for info in enumerate_fn(spec.vendor_id, spec.product_id):
        check_usb_allowed(info, registry)
        serial = info.get("serial_number") or ""
        if spec.serial and serial != spec.serial:
            continue
        if spec.product and info.get("product_string") != spec.product:
            continue
        found.append(info)
    if not found:
        raise LookupError(f"{name}: no USB device {spec} found (plugged in? docs/dev/GOTCHAS.md)")
    if len({info["path"] for info in found}) > 1:
        raise LookupError(f"{name}: several devices match {spec}; add a serial number")
    return found[0]
