"""Robot registry (config/devices.yaml) and serial-port safety checks.

Every real robot driver must get its port through `serial_port()` (or at least pass it through
`check_port_allowed()`) before opening it. That's what keeps so101-green's ports closed.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from lab_os import CONFIG_DIR

BY_ID_DIR = "/dev/serial/by-id/"


class PortNotAllowed(RuntimeError):
    """Raised when code tries to use a port it must not open."""


@dataclass(frozen=True)
class Device:
    name: str
    kind: str
    off_limits: bool = False
    ports: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class Registry:
    devices: dict[str, Device] = field(default_factory=dict)

    def off_limits_ports(self) -> set[str]:
        return {p for d in self.devices.values() if d.off_limits for p in d.ports}


def load_registry(path: Path | None = None) -> Registry:
    path = path or CONFIG_DIR / "devices.yaml"
    raw = yaml.safe_load(path.read_text()) or {}
    devices = {
        name: Device(
            name=name,
            kind=spec["kind"],
            off_limits=bool(spec.get("off_limits", False)),
            ports=tuple(spec.get("ports") or ()),
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
