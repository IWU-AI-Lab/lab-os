"""Venue profiles (config/venues/<name>.yaml): which devices are active, how cautious to be."""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from lab_os import CONFIG_DIR


@dataclass(frozen=True)
class Venue:
    name: str
    active_devices: tuple[str, ...]
    motion_allowed: bool
    max_speed_scale: float


def load_venue(name: str | None = None, config_dir: Path = CONFIG_DIR) -> Venue:
    """Load a venue by name; defaults to $LAB_OS_VENUE, then "lab"."""
    name = name or os.environ.get("LAB_OS_VENUE", "lab")
    raw = yaml.safe_load((config_dir / "venues" / f"{name}.yaml").read_text())
    return Venue(
        name=raw["name"],
        active_devices=tuple(raw.get("active_devices") or ()),
        motion_allowed=bool(raw.get("motion_allowed", False)),
        max_speed_scale=float(raw.get("max_speed_scale", 0.3)),
    )
