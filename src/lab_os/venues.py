"""Venue profiles (config/venues/<name>.yaml): which devices are active, how cautious to be."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from lab_os import CONFIG_DIR


@dataclass(frozen=True)
class Venue:
    name: str
    active_devices: tuple[str, ...]
    motion_allowed: bool
    max_speed_scale: float
    reset_after_s: float | None = None  # hub: back to the start screen; None = the theme's value
    ai_tools: dict = field(default_factory=dict)  # limits for the AI tools (lab_os.tools.robot)


def load_venue(name: str | None = None, config_dir: Path = CONFIG_DIR) -> Venue:
    """Load a venue by name; defaults to $LAB_OS_VENUE, then "lab"."""
    name = name or os.environ.get("LAB_OS_VENUE", "lab")
    raw = yaml.safe_load((config_dir / "venues" / f"{name}.yaml").read_text())
    return Venue(
        name=raw["name"],
        active_devices=tuple(raw.get("active_devices") or ()),
        motion_allowed=bool(raw.get("motion_allowed", False)),
        max_speed_scale=float(raw.get("max_speed_scale", 0.3)),
        reset_after_s=float(raw["reset_after_s"]) if raw.get("reset_after_s") else None,
        ai_tools=dict(raw.get("ai_tools") or {}),
    )
