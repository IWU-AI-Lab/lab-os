"""Personas (personas/<id>.yaml): who the assistant is. Chosen by `--persona`, else
$LAB_OS_PERSONA, else the venue's `persona:` (`default` = the place's), else the place's
`persona:` (place.yaml), else the plain `lab-assistant`. A persona changes the name on screen, how
it talks (a short text file next to it), which AI setup answers (models.yaml), the picture, voice,
lines and sounds. The theme (colors, fonts) stays the same for all.

Must stay extensible: the loader checks the fields it knows, keeps unknown ones and warns about
them (never crashes), so new fields can be added any time.
"""

import logging
import os
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

from lab_os import config

log = logging.getLogger(__name__)
_warned: set[str] = set()


def _warn(msg: str, *args) -> None:
    """Warn once per message: personas are re-read on every status poll."""
    text = msg % args
    if text not in _warned:
        _warned.add(text)
        log.warning(text)


DEFAULT_PERSONA = "lab-assistant"  # the plain one: plain name, simple circle, no character
KNOWN = {
    "version",
    "id",
    "display_name",
    "personality",
    "model",
    "voice",
    "speakers",
    "wake_word",
    "picture",
    "lines",
    "sounds",
}


@dataclass(frozen=True)
class Persona:
    id: str  # plain name (code, files)
    display_name: str  # show name (on screen)
    personality: str = ""  # the text of the personality file: how it talks
    model: str = "main"  # which AI setup (models.yaml)
    voice: str = "none"  # step 7
    # the voice's speaker for each service (quick job 100): {"openai": "onyx", "gemini": "Charon"};
    # a service not named here uses the voice setup's own `speaker`
    speakers: dict = field(default_factory=dict)
    wake_word: str = "none"  # later
    picture: dict = field(default_factory=lambda: {"type": "orb", "style": "plain"})
    lines: dict = field(default_factory=dict)  # things it says, e.g. greeting
    sounds: str = "default"
    extra: dict = field(default_factory=dict)  # fields this version doesn't know (kept)

    def public(self) -> dict:
        """What the pages get (no personality text: that's for the AI)."""
        return {
            "id": self.id,
            "display_name": self.display_name,
            "picture": self.picture,
            "voice": self.voice,
            "sounds": self.sounds,
        }


def persona_dir() -> Path:
    return config.shared_path("personas")


def persona_ids() -> list[str]:
    ids = {p.stem for p in (config.DEFAULT_DIR / "personas").glob("*.yaml")}
    ids |= {p.stem for p in (config.active_dir() / "personas").glob("*.yaml")}
    return sorted(ids)


def load_persona(persona_id: str | None = None, path: Path | None = None) -> Persona:
    """Load a persona by id (the place's own personas/ first, then the repo's)."""
    persona_id = persona_id or DEFAULT_PERSONA
    path = path or config.shared_path(f"personas/{persona_id}.yaml")
    if not path.is_file():
        raise config.ConfigError(
            f"no persona {persona_id!r} (personas/{persona_id}.yaml); "
            f"there are: {', '.join(persona_ids()) or 'none'}"
        )
    raw = yaml.safe_load(path.read_text()) or {}
    extra = {k: v for k, v in raw.items() if k not in KNOWN}
    for key in extra:
        _warn("%s: unknown field %r (kept, not used yet)", path, key)
    pid = str(raw.get("id") or path.stem)
    if pid != path.stem:
        _warn("%s: id %r differs from the file name; using %r", path, pid, path.stem)
        pid = path.stem
    personality = ""
    if raw.get("personality"):
        text_file = path.parent / str(raw["personality"])
        if text_file.is_file():
            personality = text_file.read_text().strip()
        else:
            _warn("%s: personality file %s is missing", path, text_file.name)
    speakers = raw.get("speakers") or {}
    if not isinstance(speakers, dict):
        _warn("%s: speakers should be a section (service: voice name); ignored", path)
        speakers = {}
    picture = raw.get("picture") or {"type": "orb", "style": "plain"}
    lines = raw.get("lines") or {}
    if not isinstance(picture, dict) or not isinstance(lines, dict):
        _warn("%s: picture and lines should be sections (key: value); ignored", path)
        picture = picture if isinstance(picture, dict) else {"type": "orb", "style": "plain"}
        lines = lines if isinstance(lines, dict) else {}
    return Persona(
        id=pid,
        display_name=str(raw.get("display_name") or pid),
        personality=personality,
        model=str(raw.get("model") or "main"),
        voice=str(raw.get("voice") or "none"),
        speakers={str(k): str(v) for k, v in speakers.items() if v},
        wake_word=str(raw.get("wake_word") or "none"),
        picture=dict(picture),
        lines={str(k): str(v) for k, v in lines.items()},
        sounds=str(raw.get("sounds") or "default"),
        extra=extra,
    )


def chosen_persona_id(override: str | None = None, venue: str | None = None) -> str:
    """`override` (--persona), else $LAB_OS_PERSONA, else the venue's `persona:` (unless
    `default`), else the place's `persona:`, else the plain one."""
    from lab_os.venues import load_venue

    if override:
        return override
    if os.environ.get("LAB_OS_PERSONA"):
        return os.environ["LAB_OS_PERSONA"]
    try:
        if venue and (own := load_venue(venue).persona):
            return own
        return config.load_place().persona or DEFAULT_PERSONA
    except (config.ConfigError, OSError, yaml.YAMLError) as e:
        _warn("%s; using the %s persona", e, DEFAULT_PERSONA)
        return DEFAULT_PERSONA


def current_persona(override: str | None = None, venue: str | None = None) -> Persona:
    """The chosen persona (`venue`: the venue's name), re-read from the files (switching = an edit
    + reload). A broken or unknown persona falls back to the plain one, with a warning, so the hub
    keeps working."""
    try:
        persona = load_persona(chosen_persona_id(override, venue))
    except (config.ConfigError, OSError, yaml.YAMLError) as e:
        _warn("%s; using the plain persona", e)
        return default_persona()
    return with_place_wake_word(persona)


def with_place_wake_word(persona: Persona) -> Persona:
    """The persona with the wake word chosen for it in ⚙ → Assistant (place.yaml → `wake_words`,
    quick job 90), else its file's own."""
    try:
        word = config.load_place().wake_words.get(persona.id)
    except (config.ConfigError, OSError, yaml.YAMLError):
        return persona
    return replace(persona, wake_word=word) if word else persona


def default_persona() -> Persona:
    """The plain persona, or a bare one if even its file is broken."""
    try:
        return load_persona(DEFAULT_PERSONA)
    except (config.ConfigError, OSError, yaml.YAMLError):
        return Persona(id=DEFAULT_PERSONA, display_name="Assistant")
