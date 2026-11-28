"""Venue profiles (<place>/venues/<name>.yaml, with the place's local/venues/<name>.yaml merged over
it): which devices are active, how cautious to be."""

import math
import os
from dataclasses import dataclass, field
from pathlib import Path

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
    persona: str | None = None  # this venue's persona; None (`default` or left out) = the place's
    # teleop's 1:1 mode: the fastest a joint may turn (°/s). 0 = no 1:1 here; inf = no software cap
    # (the servos' own top speed). `one_to_one_max_deg_per_s` in the venue file.
    one_to_one_deg_per_s: float = 0.0
    # the wake word on screens that chose it; None (`default`) = off on a public venue
    wake_word: bool | None = None
    # Safety limits that can be switched off (`limits:` in the venue file; on by default). Never off
    # on a public venue or one with `limits_locked: true`. The soft joint limits and one
    # controller at a time can't be switched off at all.
    per_move_limit: bool = True  # the AI tools: max_joint_change_deg / max_move_cm per call
    speed_cap: bool = True  # max_speed_scale and one_to_one_max_deg_per_s
    floor: bool = True  # the AI tools' min_z_cm and teleop's floor (the same number)
    limits_locked: bool = False
    # a venue for visitors (quick job 35): the hub hides Settings and the AI spend, shows the
    # "try this" cards, and the wave works. "Say hello to our visitors" switches to it.
    visitors: bool = False
    cards: tuple[dict, ...] = ()  # the "try this" cards: {"say", "ask"?, "line"?} (`try_this:`)

    @property
    def wake_word_on(self) -> bool:
        return (not self.public) if self.wake_word is None else self.wake_word

    @property
    def hides_spend(self) -> bool:
        """The hub doesn't say what the AI costs here (a public screen, or visitors)."""
        return self.public or self.visitors

    @property
    def limits_fixed(self) -> bool:
        """The limits can't be switched off here (a public venue, or `limits_locked: true`)."""
        return self.public or self.limits_locked

    @property
    def limits_off(self) -> list[str]:
        """Which switchable limits are off: `per_move`, `speed_cap`, `floor`."""
        on = {"per_move": self.per_move_limit, "speed_cap": self.speed_cap, "floor": self.floor}
        return [name for name, is_on in on.items() if not is_on]

    @property
    def speed_cap_scale(self) -> float:
        """The highest speed scale teleop and the AI tools may use (1 = the cap is off)."""
        return self.max_speed_scale if self.speed_cap else 1.0

    @property
    def one_to_one_cap(self) -> float:
        """Arm Control 1:1's top joint speed: the venue's, or none (inf) with the cap off. 1:1
        that's switched off (`off`, 0) stays off: that's a mode, not a limit."""
        if self.speed_cap or self.one_to_one_deg_per_s == 0:
            return self.one_to_one_deg_per_s
        return math.inf

    @property
    def floor_cm(self) -> float:
        """The lowest the gripper and wrist may go (cm above the table); -inf with the floor off."""
        return float(self.ai_tools.get("min_z_cm", 1.0)) if self.floor else -math.inf


def one_to_one_speed(value) -> float:
    """`one_to_one_max_deg_per_s`: a number (°/s), `off` (or left out, 0) or `none` (no cap)."""
    if value is None or value is False:
        return 0.0
    text = str(value).strip().lower()
    if text in ("", "off", "0"):
        return 0.0
    if text == "none":
        return float("inf")
    speed = float(text)
    if speed < 0:
        raise config.ConfigError(
            f"one_to_one_max_deg_per_s must be ≥ 0, off or none, not {value!r}"
        )
    return speed


def _on_off(value, key: str) -> bool | None:
    """`on` / `off` (YAML may read them as true/false), or `default` / left out → None."""
    if value is None or str(value).strip().lower() in ("", "default"):
        return None
    text = str(value).strip().lower()
    if text in ("on", "true", "yes"):
        return True
    if text in ("off", "false", "no"):
        return False
    raise config.ConfigError(f"{key} must be on, off or default, not {value!r}")


LIMITS = ("per_move", "speed_cap", "floor")


def _limits(raw: dict, name: str, fixed: bool) -> dict[str, bool]:
    """The venue file's `limits:` section: each `on` (default) or `off`."""
    given = raw.get("limits") or {}
    if not isinstance(given, dict):
        raise config.ConfigError(f"venue {name}: limits must be a section (per_move, speed_cap, …)")
    if unknown := set(given) - set(LIMITS):
        raise config.ConfigError(
            f"venue {name}: unknown limit {', '.join(sorted(unknown))} (known: {', '.join(LIMITS)})"
        )
    out = {k: _on_off(given.get(k), f"limits.{k}") is not False for k in LIMITS}
    if fixed and not all(out.values()):
        off = ", ".join(k for k, v in out.items() if not v)
        raise config.ConfigError(
            f"venue {name}: the limits can't be switched off here (a public venue or "
            f"limits_locked: true), but limits.{off} is off. Set it to on."
        )
    return out


def _cards(raw: dict, name: str) -> tuple[dict, ...]:
    """`try_this:` the hub's cards while visitors are here: what to say (`say`), what tapping the
    card asks (`ask`, optional: without it the card is only read), a short line (`line`)."""
    given = raw.get("try_this") or []
    if not isinstance(given, list) or not all(isinstance(c, dict) and c.get("say") for c in given):
        raise config.ConfigError(f'venue {name}: try_this must be a list of {{say: "..."}} cards')
    keep = ("say", "ask", "line")
    return tuple({k: str(c[k]) for k in keep if c.get(k)} for c in given)


def _persona(value) -> str | None:
    text = str(value).strip() if value else ""
    return None if text in ("", "default") else text


def venue_names(config_dir: Path | None = None) -> list[str]:
    folder = (config_dir or config.active_dir()) / "venues"
    return sorted(p.stem for p in folder.glob("*.yaml"))


def visitors_venue_name(config_dir: Path | None = None) -> str | None:
    """The place's venue for visitors (`visitors: true`; the first by name), or None."""
    for name in venue_names(config_dir):
        if config.load_yaml(f"venues/{name}.yaml", config_dir).get("visitors"):
            return name
    return None


def default_venue_name(config_dir: Path | None = None) -> str:
    """$LAB_OS_VENUE, else the place's `venue` (place.yaml), else its only venue."""
    if os.environ.get("LAB_OS_VENUE"):
        return os.environ["LAB_OS_VENUE"]
    folder = config_dir or config.active_dir()
    if (folder / "place.yaml").is_file():
        place = config.load_place(folder)
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
    raw = config.load_yaml(f"venues/{name}.yaml", folder)
    public, locked = bool(raw.get("public", False)), bool(raw.get("limits_locked", False))
    limits = _limits(raw, raw["name"], public or locked)
    return Venue(
        name=raw["name"],
        active_devices=tuple(raw.get("active_devices") or ()),
        motion_allowed=bool(raw.get("motion_allowed", False)),
        max_speed_scale=float(raw.get("max_speed_scale", 0.3)),
        reset_after_s=float(raw["reset_after_s"]) if raw.get("reset_after_s") else None,
        ai_tools=dict(raw.get("ai_tools") or {}),
        public=public,
        persona=_persona(raw.get("persona")),
        one_to_one_deg_per_s=one_to_one_speed(raw.get("one_to_one_max_deg_per_s")),
        wake_word=_on_off(raw.get("wake_word"), "wake_word"),
        per_move_limit=limits["per_move"],
        speed_cap=limits["speed_cap"],
        floor=limits["floor"],
        limits_locked=locked,
        visitors=bool(raw.get("visitors", False)),
        cards=_cards(raw, raw["name"]),
    )
