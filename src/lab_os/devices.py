"""Robot registry (config/devices.yaml) and device-access safety checks.

Every real robot driver must get its port through `serial_port()` (or at least pass it through
`check_port_allowed()`), or its USB device through `find_usb_device()`, before opening it. That's
what keeps so101-green closed. Devices are identified by USB ID + serial number, which is the same
on Linux, Windows and macOS (decision 2026-10-27); OS paths are only resolved at run time.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from lab_os import CONFIG_DIR

BY_ID_DIR = "/dev/serial/by-id/"


class PortNotAllowed(RuntimeError):
    """Raised when code tries to use a port it must not open."""


@dataclass(frozen=True)
class UsbId:
    """How a device identifies itself over USB. Empty/None fields match anything."""

    vendor_id: int
    product_id: int | None = None
    product: str = ""
    serial: str = ""


@dataclass(frozen=True)
class Device:
    name: str
    kind: str
    off_limits: bool = False
    ports: tuple[str, ...] = ()
    usb: tuple[UsbId, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class Registry:
    devices: dict[str, Device] = field(default_factory=dict)

    def off_limits_ports(self) -> set[str]:
        return {p for d in self.devices.values() if d.off_limits for p in d.ports}

    def off_limits_serials(self) -> set[str]:
        """USB serial numbers of off-limits arms: the same on every OS, unlike port names."""
        return {u.serial for d in self.devices.values() if d.off_limits for u in d.usb if u.serial}


def load_registry(path: Path | None = None) -> Registry:
    path = path or CONFIG_DIR / "devices.yaml"
    raw = yaml.safe_load(path.read_text()) or {}
    devices = {
        name: Device(
            name=name,
            kind=spec["kind"],
            off_limits=bool(spec.get("off_limits", False)),
            ports=tuple(spec.get("ports") or ()),
            usb=tuple(UsbId(**u) for u in (spec.get("usb") or ())),
            notes=spec.get("notes", ""),
        )
        for name, spec in (raw.get("devices") or {}).items()
    }
    return Registry(devices)


def check_port_allowed(port: str, registry: Registry | None = None) -> None:
    """Raise PortNotAllowed unless `port` is a by-id path that doesn't belong to an off-limits arm.

    Also compares resolved targets, so a by-id symlink that currently points at the same tty as a
    forbidden one is refused too.
    """
    registry = registry or load_registry()
    if not port.startswith(BY_ID_DIR):
        raise PortNotAllowed(
            f"{port!r}: use a {BY_ID_DIR} path; ttyACM/ttyUSB numbers swap (docs/GOTCHAS.md)"
        )
    for serial in registry.off_limits_serials():
        if serial in port:
            raise PortNotAllowed(f"{port!r} has an off-limits arm's serial number. Never open it.")
    forbidden = registry.off_limits_ports()
    forbidden_targets = {os.path.realpath(p) for p in forbidden if os.path.exists(p)}
    if port in forbidden or (os.path.exists(port) and os.path.realpath(port) in forbidden_targets):
        raise PortNotAllowed(f"{port!r} belongs to an off-limits arm (so101-green). Never open it.")


def serial_port(name: str, registry: Registry | None = None) -> str:
    """Return the by-id serial port for device `name`, after the safety checks."""
    registry = registry or load_registry()
    device = registry.devices.get(name)
    if device is None:
        raise KeyError(f"unknown device {name!r}; add it to config/devices.yaml")
    if device.off_limits:
        raise PortNotAllowed(f"{name} is off limits: {device.notes}")
    if len(device.ports) != 1:
        raise LookupError(f"{name} needs exactly one port in config/devices.yaml")
    port = device.ports[0]
    check_port_allowed(port, registry)
    return port


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
        raise KeyError(f"unknown device {name!r}; add it to config/devices.yaml")
    if device.off_limits:
        raise PortNotAllowed(f"{name} is off limits: {device.notes}")
    if len(device.usb) != 1 or device.usb[0].product_id is None:
        raise LookupError(f"{name} needs exactly one usb entry with vendor_id and product_id")
    spec = device.usb[0]
    forbidden = registry.off_limits_serials()
    found = []
    for info in enumerate_fn(spec.vendor_id, spec.product_id):
        serial = info.get("serial_number") or ""
        if serial in forbidden:
            raise PortNotAllowed(f"{name}: matching device has an off-limits serial ({serial})")
        if spec.serial and serial != spec.serial:
            continue
        if spec.product and info.get("product_string") != spec.product:
            continue
        found.append(info)
    if not found:
        raise LookupError(f"{name}: no USB device {spec} found (plugged in? docs/GOTCHAS.md)")
    if len({info["path"] for info in found}) > 1:
        raise LookupError(f"{name}: several devices match {spec}; add a serial number")
    return found[0]
