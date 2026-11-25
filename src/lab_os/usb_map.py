"""`lab-os usb` (quick job 115): every USB device plugged in, under its USB controller, with the
lab-os name of each one that devices.yaml knows. Linux only (it reads /sys); opens nothing.

It answers the plugging questions in one look: which arm and cameras share a hub (the cameras'
`beside` and `hub_port`), and which devices share a controller. Cameras and USB microphones send
their data on a fixed timetable, and one USB 2.0 controller has room for only a few of them.
"""

import os
from dataclasses import dataclass, field

from lab_os import config, devices

# USB interface classes (usb.org): what a device is, in a word
KINDS = {"01": "sound", "02": "serial", "03": "keyboard/mouse", "08": "storage", "09": "hub",
         "0a": "serial", "0e": "camera", "e0": "wireless", "ff": "vendor"}  # fmt: skip


@dataclass
class UsbDevice:
    chain: str  # "7.2": socket 7, port 2 of its hub
    controller: str  # the PCI name, "0000:00:14.0"
    vendor_id: int = 0
    product_id: int = 0
    product: str = ""
    serial: str = ""
    speed_mbps: str = ""
    kinds: list[str] = field(default_factory=list)
    name: str = ""  # the lab-os name, "" when devices.yaml doesn't know it


def _read(folder: str, file: str) -> str:
    try:
        with open(os.path.join(folder, file)) as f:
            return f.read().strip()
    except OSError:
        return ""


def scan(sys_dir: str = devices.SYS_DIR) -> tuple[dict[str, str], list[UsbDevice]]:
    """({controller: its root hub's product}, the devices) from /sys/bus/usb/devices."""
    base = os.path.join(sys_dir, "bus", "usb", "devices")
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return {}, []
    roots: dict[str, str] = {}
    found = []
    for n in names:
        folder = os.path.realpath(os.path.join(base, n))
        if ":" in n:
            continue  # an interface, read with its device
        controller = devices.controller_of(folder)
        if n.startswith("usb"):
            roots.setdefault(controller, _read(folder, "product") or "USB controller")
            continue
        kinds = []
        for iface in sorted(os.listdir(folder)):
            if iface.startswith(n + ":"):
                kind = KINDS.get(_read(os.path.join(folder, iface), "bInterfaceClass").lower())
                if kind and kind not in kinds:
                    kinds.append(kind)
        found.append(
            UsbDevice(
                chain=devices.chain_of(folder),
                controller=controller,
                vendor_id=int(_read(folder, "idVendor") or "0", 16),
                product_id=int(_read(folder, "idProduct") or "0", 16),
                product=_read(folder, "product") or _read(folder, "manufacturer"),
                serial=_read(folder, "serial"),
                speed_mbps=_read(folder, "speed"),
                kinds=kinds,
            )
        )
    return roots, found


def name_devices(
    found: list[UsbDevice], registry: devices.Registry, sys_dir: str = devices.SYS_DIR
) -> None:
    """Fill in the lab-os name of each device devices.yaml knows: arms and boards by USB ID and
    serial, cameras by their socket or their port on the arm's hub."""
    for d in found:
        info = {"vendor_id": d.vendor_id, "product_id": d.product_id, "serial_number": d.serial,
                "product_string": d.product}  # fmt: skip
        for dev in registry.devices.values():
            if any(u.serial and u.matches(info) for u in dev.usb):  # a serial: this one board
                d.name = dev.name
    for dev in registry.devices.values():
        if dev.kind != "camera":
            continue
        if dev.beside:
            try:
                controller, chain = devices._beside_socket(dev, registry, sys_dir)
            except LookupError:
                continue  # its arm isn't plugged in or isn't on a hub
        elif dev.socket:
            controller, chain = "", dev.socket.removeprefix("usb-").removeprefix("0:")
        else:
            continue
        for d in found:
            if d.chain == chain and controller in ("", d.controller) and "camera" in d.kinds:
                d.name = f"{d.name}, {dev.name}" if d.name else dev.name


def report(sys_dir: str = devices.SYS_DIR, registry: devices.Registry | None = None) -> str:
    """The text `lab-os usb` prints."""
    roots, found = scan(sys_dir)
    if not roots and not found:
        return "No USB devices found (this reads /sys: it works on Linux only)."
    if registry is None:
        try:
            registry = devices.load_registry()
        except (OSError, ValueError, config.ConfigError):  # no devices.yaml: no names
            registry = devices.Registry({})
    name_devices(found, registry, sys_dir)
    arm_hubs = {  # the hub each arm is on: "7" for an arm at "7.1"
        d.chain.rsplit(".", 1)[0]: (d.controller, d.name)
        for d in found
        if d.name and "." in d.chain and "serial" in d.kinds
    }
    lines = []
    for controller in sorted(set(roots) | {d.controller for d in found}):
        mine = sorted(
            (d for d in found if d.controller == controller),
            key=lambda d: [int(p) for p in d.chain.split(".") if p.isdigit()],
        )
        lines.append(f"USB controller {controller} ({roots.get(controller, 'USB controller')})")
        if not mine:
            lines.append("  (nothing plugged in)")
        for d in mine:
            depth = d.chain.count(".")
            what = "/".join(d.kinds) or "device"
            speed = f", {d.speed_mbps} Mbit/s" if d.speed_mbps else ""
            label = d.name or "not in devices.yaml"
            line = (
                f"  {'  ' * depth}{d.chain:<8} {label}: {what}, {d.product or 'no name'} "
                f"({d.vendor_id:04x}:{d.product_id:04x}{speed})"
            )
            hub = d.chain.rpartition(".")[0]
            while hub:  # a camera below an arm's hub: say its hub_port for devices.yaml
                owner = arm_hubs.get(hub)
                if owner and owner[0] == controller and "camera" in d.kinds:
                    line += f'  [beside: {owner[1]}, hub_port: "{d.chain[len(hub) + 1 :]}"]'
                    break
                hub = hub.rpartition(".")[0]
            lines.append(line)
        streams = [d for d in mine if {"camera", "sound"} & set(d.kinds)]
        if sum("camera" in d.kinds for d in mine) >= 2 and len(streams) >= 3:
            lines.append(
                f"  ! {len(streams)} cameras and microphones share this controller: a USB 2.0 "
                "controller may not have room for all of them."
            )
    return "\n".join(lines)
