"""The settings page's schema: which config values the hub can show and change, and how.

Each setting is a `Field` (a value in one config file, a kind of input, a label); fields come in
`Section`s. The settings page (`/settings`) draws whatever is listed here, so **adding a setting is
adding a Field**, and a new module adds its own section with `register(Section(...))` when it's
imported. A change goes into the place's `local/` folder (not in git), and only the changed value:
`local/theme.yaml`, `local/place.yaml` or `local/venues/<name>.yaml` (the venue this brain runs).
The brain merges them over the files below (`config.load_yaml`), so a new field in the repo's files
reaches every place. A local file keeps its comments when a value changes (ruamel.yaml).
`applies` says when a change takes effect: `reload` (reload the page), `next` (the next question
or status poll), `restart` (restart `lab-os serve`).
"""

import difflib
import io
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from ruamel.yaml import YAML

from lab_os import config

QUALITY = ("maximal", "full", "reduced", "minimal")


class SettingError(ValueError):
    """A value the field doesn't accept (the message is a full sentence for the page)."""


@dataclass(frozen=True)
class Field:
    file: str  # theme | place | venue
    path: str  # dotted, e.g. "hub.layout"
    label: str
    kind: str  # choice | bool | number | text | color | list (an ordered subset of choices)
    help: str = ""
    choices: tuple | Callable[[], list] = ()
    min: float | None = None
    max: float | None = None
    step: float | None = None
    unit: str = ""
    applies: str = "reload"
    # what the brain uses when the file leaves it out (shown: the current value is always visible)
    default: Any = None
    # a safety limit (bool): the page shows clearly when it's off, and it can't be switched off
    # in a public venue or one with `limits_locked: true`
    safety: bool = False

    @property
    def key(self) -> str:
        return f"{self.file}:{self.path}"

    def options(self) -> list:
        return list(self.choices() if callable(self.choices) else self.choices)


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    fields: tuple[Field, ...]
    help: str = ""
    risky: bool = False  # switching off or stopping: shown apart, at the bottom (quick job 38)


def _personas() -> list[str]:
    from lab_os.personas import persona_ids

    return persona_ids()


def _wake_word_fields() -> tuple[Field, ...]:
    """One Wake Word row for each persona in the repo's config/personas/ (quick job 90): each
    persona listens for its own word only. Written to place.yaml → wake_words."""
    from lab_os.ai.wake import PHRASES

    out = []
    for path in sorted((config.DEFAULT_DIR / "personas").glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text()) or {}
        except (OSError, yaml.YAMLError):
            continue
        name = str(raw.get("display_name") or path.stem)
        out.append(
            Field(
                "place",
                f"wake_words.{path.stem}",
                f"Wake Word: {name}",
                "choice",
                f"What {name} listens for. One word for each persona: more words would wake it "
                "by mistake more often.",
                (*PHRASES, "none"),
                applies="next",
                default=str(raw.get("wake_word") or "none"),
            )
        )
    return tuple(out)


def _modules() -> list[str]:
    from lab_os.hub.server import MODULES

    return list(MODULES)


# Grouped by what a setting affects, most-used first (quick job 38): the assistant, the lab (its hub
# and its name), the robots, then the risky ones apart (`risky`: switching a safety limit off; the
# page adds "Shut down" there). "This device" is the page's own (settings.js). Labels in Title Case;
# a help line only where a setting isn't obvious.
SECTIONS: list[Section] = [
    Section(
        "assistant",
        "Assistant",
        (
            Field(
                "place",
                "persona",
                "Persona",
                "choice",
                "Its name, how it talks and which AI it uses.",
                _personas,
                applies="next",
            ),
            Field(
                "venue",
                "persona",
                "Persona in This Venue",
                "choice",
                "Default: the same as above.",
                lambda: ["default", *_personas()],
                applies="next",
            ),
            Field(
                "place",
                "ai_budget_usd_month",
                "Monthly AI Budget",
                "number",
                "The chat pauses when this month's spend reaches it.",
                min=0,
                max=1000,
                step=1,
                unit="$",
                applies="next",
            ),
            Field(
                "venue",
                "wake_word",
                "Wake Word in This Venue",
                "choice",
                "Devices that chose the wake word listen for the persona's word. Default: off on a "
                "public venue.",
                choices=("default", "on", "off"),
                applies="restart",
            ),
            *_wake_word_fields(),
            Field(
                "place",
                "assistant_full_access",
                "Full Access",
                "bool",
                "On: the assistant gets every tool of the brain: it moves the arms, looks through "
                "the cameras, changes settings and more, asked on any screen. The robot safety "
                "limits stay. Off by default.",
                default=False,
                applies="next",
            ),
            Field(
                "place",
                "chat_keep_minutes",
                "Keep a Conversation For",
                "number",
                "So a reset by mistake can be undone. 0 keeps nothing.",
                min=0,
                max=1440,
                step=5,
                unit="min",
                applies="restart",
            ),
        ),
    ),
    Section(
        "lab",
        "The Lab",
        (
            Field("place", "name", "Name", "text", "The hub's title and the startup's."),
            Field(
                "theme",
                "quality.default",
                "Level of Detail",
                "choice",
                "For devices that don't pick their own.",
                QUALITY,
            ),
            Field(
                "theme",
                "hub.modules",
                "Buttons Around the Core",
                "list",
                "In this order, left and right of the core.",
                _modules,
            ),
            Field("theme", "startup.style", "Startup", "choice", "", ("hyperspace", "assemble")),
            Field(
                "theme",
                "startup.hyperspace.impact_frame",
                "Impact Frame Before the Flash",
                "bool",
                "Black lines on white for a moment.",
            ),
            Field("theme", "clock", "Clock", "choice", "", ("24h", "12h")),
            Field(
                "theme",
                "hub.reset_after_s",
                "Back to the Start Screen After",
                "number",
                "With nobody using it. Never during teleop, a move or a voice turn.",
                min=60,
                max=7200,
                step=60,
                unit="s",
            ),
            Field(
                "theme",
                "motion.idle.sleep_after_s",
                "Dim After",
                "number",
                "Only if shorter than the time above.",
                min=60,
                max=7200,
                step=60,
                unit="s",
            ),
            Field("theme", "hub.type_to_chat", "Typing Anywhere Goes to the Ask Line", "bool"),
            Field(
                "theme",
                "colors.primary",
                "Main Color",
                "color",
                "Lines, rings and the assistant; the rest is tinted to match.",
            ),
        ),
    ),
    Section(
        "robots",
        "Robots",
        (
            Field(
                "venue",
                "motion_allowed",
                "Robots May Move",
                "bool",
                "Off: teleop and the AI tools refuse every move.",
                applies="restart",
            ),
            Field(
                "place",
                "assistant_moves_arm",
                "The Assistant May Move the Arm",
                "bool",
                "On: asked on this computer, it moves the arm to a named pose and hands over the "
                "cube. In every venue.",
                default=False,
                applies="next",
            ),
            Field(
                "venue",
                "max_speed_scale",
                "Top Speed",
                "number",
                "A share of each arm's full speed (1 = full).",
                min=0.05,
                max=1,
                step=0.05,
                applies="restart",
            ),
            Field(
                "venue",
                "one_to_one_max_deg_per_s",
                "Teleop 1:1 Top Joint Speed",
                "choice",
                "°/s. None: the servos' own top speed. Off: relative only.",
                choices=("off", "90", "120", "180", "240", "none"),
                applies="restart",
            ),
            Field(
                "venue",
                "ai_tools.max_joint_change_deg",
                "AI: Largest Joint Turn per Move",
                "number",
                "",
                default=30,
                min=1,
                max=90,
                step=1,
                unit="°",
                applies="restart",
            ),
            Field(
                "venue",
                "ai_tools.max_move_cm",
                "AI: Largest Gripper Move",
                "number",
                "",
                default=10,
                min=1,
                max=30,
                step=1,
                unit="cm",
                applies="restart",
            ),
        ),
        help="In this venue. These apply when the brain restarts.",
    ),
    Section(
        "limits",
        "Safety Limits and Shut Down",
        (
            Field(
                "venue",
                "limits.per_move",
                "AI: Limit Each Move",
                "bool",
                "Off: an AI tool may move any distance in one call.",
                applies="restart",
                safety=True,
            ),
            Field(
                "venue",
                "limits.speed_cap",
                "Speed Cap",
                "bool",
                "Off: up to each arm's full speed, and 1:1 at the servos' top speed.",
                applies="restart",
                safety=True,
            ),
            Field(
                "venue",
                "limits.floor",
                "Floor (Stay Above the Table)",
                "bool",
                "Off: teleop and the AI tools may take the gripper below the table line.",
                applies="restart",
                safety=True,
            ),
        ),
        help="Always kept, whatever is set here: STOP on every screen, the soft joint limits "
        "and one controller at a time.",
        risky=True,
    ),
]


def register(section: Section) -> None:
    """A module adds its own settings (replacing a section with the same id)."""
    SECTIONS[:] = [s for s in SECTIONS if s.id != section.id] + [section]


def find(key: str) -> Field:
    for s in SECTIONS:
        for f in s.fields:
            if f.key == key:
                return f
    raise SettingError(f"There's no setting {key!r}.")


# ---------- files ----------


def file_name(file: str, venue: str | None = None) -> str:
    """The config file a settings file stands for, as `config.load_yaml` names it."""
    if file == "theme":
        return "theme.yaml"
    if file == "place":
        return "place.yaml"
    if file == "venue":
        from lab_os.venues import default_venue_name

        return f"venues/{venue or default_venue_name()}.yaml"
    raise SettingError(f"Unknown settings file {file!r}.")


def file_path(file: str, venue: str | None = None) -> Path:
    """Where a change to `file` goes: the place's local/ copy (made on the first change)."""
    return config.local_dir() / file_name(file, venue)


def values(file: str, venue: str | None = None) -> dict:
    """What the brain uses: every layer of the file merged."""
    return config.load_yaml(file_name(file, venue), shared=file == "theme")


LOCAL_HEAD = (
    "# This place's own settings: the settings page writes the values that changed here, and they\n"
    "# win over {name} in the folder above. Not in git. Delete a line to go back to that value.\n"
)


def _get(data: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(data, dict) or part not in data:
            return None
        data = data[part]
    return data


def problems(venue: str | None = None) -> list[str]:
    """A sentence for each settings file that can't be read (the file and the line), for the top
    of the settings page (quick job 45)."""
    out = []
    for file in ("theme", "place", "venue"):
        try:
            values(file, venue)
        except config.ConfigError as e:
            out.append(str(e))
        except (OSError, SettingError) as e:
            out.append(f"{file_name(file, venue)} can't be read: {e}")
    return out


def read(venue: str | None = None) -> list[dict]:
    """Every section with its fields' current values (what /api/settings sends)."""
    cache: dict[str, Any] = {}

    def data(file: str):
        if file not in cache:
            try:
                cache[file] = values(file, venue)
            except (OSError, yaml.YAMLError, config.ConfigError):
                cache[file] = {}
        return cache[file]

    locked = limits_locked_why(data("venue"))
    out = []
    for s in SECTIONS:
        fields = []
        for f in s.fields:
            value = _get(data(f.file), f.path)
            if value is None:
                value = f.default
            if f.safety:
                value = value is not False and str(value).lower() not in ("off", "false", "no")
            fields.append(
                {
                    "key": f.key,
                    "file": f.file,
                    "label": f.label,
                    "kind": f.kind,
                    "help": f.help,
                    "choices": f.options(),
                    "min": f.min,
                    "max": f.max,
                    "step": f.step,
                    "unit": f.unit,
                    "applies": f.applies,
                    "value": value,
                    "safety": f.safety,
                    "locked": locked if f.safety else "",
                }
            )
        out.append(
            {"id": s.id, "title": s.title, "help": s.help, "risky": s.risky, "fields": fields}
        )
    return out


def limits_locked_why(venue_data: dict) -> str:
    """Why the safety limits can't be switched off in this venue ("" = they can)."""
    if venue_data.get("public"):
        return "a public venue: the limits always stay on"
    if venue_data.get("limits_locked"):
        return "this venue has limits_locked: true: the limits always stay on"
    return ""


def check(f: Field, value: Any) -> Any:
    """The value as it will be written, or SettingError with a sentence why not."""
    if f.kind == "bool":
        if not isinstance(value, bool):
            raise SettingError(f"{f.label}: on or off.")
        return value
    if f.kind == "number":
        try:
            n = float(value)
        except (TypeError, ValueError):
            raise SettingError(f"{f.label}: a number, please.") from None
        if (f.min is not None and n < f.min) or (f.max is not None and n > f.max):
            raise SettingError(f"{f.label}: between {f.min:g} and {f.max:g}{f.unit}.")
        return int(n) if n.is_integer() and (f.step or 1) >= 1 else round(n, 4)
    if f.kind == "choice":
        if value not in f.options():
            raise SettingError(f"{f.label}: one of {', '.join(map(str, f.options()))}.")
        return value
    if f.kind == "list":
        options = f.options()
        if not isinstance(value, list) or any(v not in options for v in value):
            raise SettingError(f"{f.label}: pick from {', '.join(options)}.")
        return list(dict.fromkeys(value))
    if f.kind == "color":
        if not (isinstance(value, str) and len(value) == 7 and value.startswith("#")):
            raise SettingError(f"{f.label}: a color like #29d4ff.")
        try:
            int(value[1:], 16)
        except ValueError:
            raise SettingError(f"{f.label}: a color like #29d4ff.") from None
        return value.lower()
    if f.kind == "text":
        text = str(value).strip()
        if not text or len(text) > 60:
            raise SettingError(f"{f.label}: 1 to 60 characters.")
        return text
    raise SettingError(f"{f.label}: can't be changed here.")


def write(key: str, value: Any, venue: str | None = None) -> Any:
    """Change one setting in the place's local/ copy of its file (made on the first change),
    keeping that file's comments and layout."""
    f = find(key)
    value = check(f, value)
    if f.safety and value is False:
        why = limits_locked_why(values("venue", venue))
        if why:
            raise SettingError(f"{f.label} can't be switched off here: {why}.")
    return write_value(f.file, f.path, value, venue, flow=f.kind == "list")


def write_value(
    file: str, dotted: str, value: Any, venue: str | None = None, flow: bool = False
) -> Any:
    """Write one value at `dotted` into the place's local/ copy of `file` (made on the first
    change), keeping that file's comments and layout. `flow`: a list in the one-line [a, b]
    style. For values with no Field too (the Command Center's `drive_from`, quick job 134)."""
    values(file, venue)  # a layer that can't be read: ConfigError with the file and the line
    path = file_path(file, venue)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(LOCAL_HEAD.format(name=file_name(file, venue)))
    rt = YAML()
    rt.preserve_quotes = True
    rt.width = 4096  # never re-wrap long comment lines
    before = path.read_text()
    try:
        loaded = rt.load(before)
    except Exception as e:  # ruamel's own errors: the same sentence as a broken layer
        raise config.ConfigError(config.broken_yaml(path, e)) from None
    data = loaded if loaded is not None else {}
    *parents, last = dotted.split(".")
    node = data
    for part in parents:
        if part not in node or not isinstance(node[part], dict):
            node[part] = {}
        node = node[part]
    if flow:  # keep the one-line [a, b] style
        from ruamel.yaml.comments import CommentedSeq

        seq = CommentedSeq(value)
        seq.fa.set_flow_style()
        value_out = seq
    else:
        value_out = value
    node[last] = value_out
    out = io.StringIO()
    rt.dump(data, out)
    if loaded is None:  # a new local file: its head comment, then the first value
        path.write_text(before + out.getvalue())
    else:
        path.write_text(_keep_untouched_lines(before, out.getvalue()))
    return value


def _same(line: str) -> str:
    """A line's meaning, ignoring the spacing ruamel changes (`{ a: 1 }` → `{a: 1}`)."""
    return re.sub(r"\s+", " ", line).replace("{ ", "{").replace(" }", "}").strip()


def _keep_untouched_lines(before: str, after: str) -> str:
    """Every line that didn't change in meaning stays exactly as it was written."""
    old, new = before.splitlines(), after.splitlines()
    out: list[str] = []
    matcher = difflib.SequenceMatcher(None, [_same(x) for x in old], [_same(x) for x in new])
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        out += old[i1:i2] if op == "equal" else new[j1:j2]
    return "\n".join(out) + ("\n" if after.endswith("\n") else "")
