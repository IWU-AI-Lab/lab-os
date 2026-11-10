"""Venue profiles (<place>/venues/<name>.yaml): which devices are active, how cautious to be."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from lab_os import config


@dataclass(frozen=True)
class Venue:
    name: str
    active_devices: tuple[str, ...]
    motion_allowed: bool
    max_speed_scale: float
    reset_after_s: float | None = None  # hub: back to the start screen; None = the theme's value
    ai_tools: dict = field(default_factory=dict)  # limits for the AI tools (lab_os.tools.robot)
    public: bool = False  # a public screen: the hub hides internal details (AI spend, later IPs)


def venue_names(config_dir: Path | None = None) -> list[str]:
    folder = (config_dir or config.active_dir()) / "venues"
    return sorted(p.stem for p in folder.glob("*.yaml"))


def default_venue_name(config_dir: Path | None = None) -> str:
    """$LAB_OS_VENUE, else the place's `venue` (place.yaml), else its only venue."""
    if os.environ.get("LAB_OS_VENUE"):
        return os.environ["LAB_OS_VENUE"]
    folder = config_dir or config.active_dir()
    if (folder / "place.yaml").is_file():
        place = config.load_place(folder / "place.yaml")
        if place.venue:
            return place.venue
    names = venue_names(folder)
    if len(names) == 1:
        return names[0]
    raise config.ConfigError(
        f"which venue? Set `venue:` in {folder / 'place.yaml'} or use --venue ({', '.join(names)})"
    )


def load_venue(name: str | None = None, config_dir: Path | None = None) -> Venue:
    """Load a venue of the place (default: `default_venue_name()`)."""
    folder = config_dir or config.active_dir()
    name = name or default_venue_name(folder)
    path = folder / "venues" / f"{name}.yaml"
    if not path.is_file():
        known = ", ".join(venue_names(folder)) or "none"
        raise config.ConfigError(f"no venue {name!r} in {folder / 'venues'} (there: {known})")
    raw = yaml.safe_load(path.read_text())
    return Venue(
        name=raw["name"],
        active_devices=tuple(raw.get("active_devices") or ()),
        motion_allowed=bool(raw.get("motion_allowed", False)),
        max_speed_scale=float(raw.get("max_speed_scale", 0.3)),
        reset_after_s=float(raw["reset_after_s"]) if raw.get("reset_after_s") else None,
        ai_tools=dict(raw.get("ai_tools") or {}),
        public=bool(raw.get("public", False)),
    )
