"""The place's config folder (docs/plan/current-focus.md rule 9: nothing place-specific in code).

A *place* is where a brain runs: the lab, someone's home. Everything about it lives in one folder:

- **place files**, only ever read from the place's own folder: `place.yaml` (the place's name,
  its domain, the default venue), `devices.yaml` (what's there, what's off limits), `venues/`;
- **shared files**, read from the place's folder if it has them, else from the repo's `config/`:
  `theme.yaml`, `poses.yaml`, `models.yaml`, `personas/`;
- its own **`.env`** with the API keys (the repo's `.env` for the repo's `config/`);
- its **`local/`** folder (not in git): what the place changed itself. The settings page writes only
  the changed values there (`local/theme.yaml`, `local/place.yaml`, `local/venues/<name>.yaml`), and
  they are merged over the files above (`load_yaml`). Each device's settings and the table maps are
  there too.

The repo's `config/` is the lab's place and also the shared defaults; the lab's own changes are in
`config/local/`. Pick another one with
`lab-os serve --config ~/my-lab-os` (or `$LAB_OS_CONFIG`); `lab-os new-place ~/my-lab-os` writes a
starter. Setup: docs/dev/places.md.
"""

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from lab_os import CONFIG_DIR, REPO_ROOT

log = logging.getLogger(__name__)

DEFAULT_DIR = CONFIG_DIR
TEMPLATE_DIR = Path(__file__).parent / "place_template"
PLACE_FILES = ("place.yaml", "devices.yaml", "venues")

_active: Path | None = None


class ConfigError(RuntimeError):
    """The place's config folder is missing something it needs. The message says what to do."""


def use(path: str | Path | None) -> Path:
    """Make `path` the place for this run (None: $LAB_OS_CONFIG, else the repo's config/) and load
    its `.env`. Returns the folder."""
    global _active
    folder = Path(path).expanduser().resolve() if path else None
    if folder and not folder.is_dir():
        raise ConfigError(f"config folder {folder} doesn't exist (lab-os new-place {path})")
    _active = folder
    found = load_env(env_file())
    if found:
        log.info("config %s: read %s from %s", active_dir(), ", ".join(found), env_file())
    elif not env_file().is_file():
        log.warning("no %s: no API keys, so no AI chat (docs/dev/places.md)", env_file())
    return active_dir()


def active_dir() -> Path:
    """The place's folder: set by `use()`, else $LAB_OS_CONFIG, else the repo's config/."""
    if _active:
        return _active
    env = os.environ.get("LAB_OS_CONFIG")
    return Path(env).expanduser().resolve() if env else DEFAULT_DIR


def is_default() -> bool:
    """Is this the repo's own config/ (the lab)?"""
    return active_dir().resolve() == DEFAULT_DIR.resolve()


def place_path(name: str) -> Path:
    """A place file (place.yaml, devices.yaml, venues/...): from the place's own folder only, so a
    home brain never borrows the lab's name, devices or venues."""
    return active_dir() / name


def shared_path(name: str) -> Path:
    """A shared file (theme.yaml, poses.yaml, models.yaml, personas/...): the place's own copy if
    it has one, else the repo's config/."""
    own = active_dir() / name
    return own if own.exists() else DEFAULT_DIR / name


# ---------- the place's own changes: local/ ----------

LOCAL = "local"  # the folder in a place's folder; config/local/ for the lab (not in git)


def local_dir(folder: Path | None = None) -> Path:
    """Where this place keeps what it changed itself: the settings page's changes (only the values
    that differ from the files below them), each device's settings, the table maps. Never in git:
    a new field in the repo's files reaches every place, and the place's changes stay."""
    return (folder or active_dir()) / LOCAL


def layers(name: str, folder: Path | None = None, shared: bool = False) -> list[Path]:
    """The files that make up config file `name`, lowest first, the ones that exist: for a shared
    file the repo's config/, then the place's own; then the place's local/ copy."""
    folder = folder or active_dir()
    paths = [DEFAULT_DIR / name] if shared and folder.resolve() != DEFAULT_DIR.resolve() else []
    paths += [folder / name, local_dir(folder) / name]
    return [p for p in paths if p.is_file()]


def merge(base: dict, over: dict) -> dict:
    """`over` on top of `base`: sections merge key by key; a value or a list replaces."""
    out = dict(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = value
    return out


def read_yaml(path: Path) -> dict:
    """One YAML file as a dict ({} when empty). ConfigError names the file when it's broken."""
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise ConfigError(f"{path} is not valid YAML: {e}") from None
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must hold `name: value` lines")
    return data


def load_yaml(name: str, folder: Path | None = None, shared: bool = False) -> dict:
    """Config file `name` with every layer merged (see `layers`): what the brain uses."""
    out: dict = {}
    for path in layers(name, folder, shared):
        out = merge(out, read_yaml(path))
    return out


def logs_dir() -> Path:
    """Where this place's logs go (AI spend, ...): the repo's logs/ for the repo's config/, else
    <folder>/logs, so a home brain's spend never counts against the lab's budget."""
    return REPO_ROOT / "logs" if is_default() else active_dir() / "logs"


def recordings_dir() -> Path:
    """Where this place's recordings go (the spoken greetings, ...): like `logs_dir()`, not in
    git."""
    return REPO_ROOT / "recordings" if is_default() else active_dir() / "recordings"


def env_file() -> Path:
    """The place's .env: next to its config files, or the repo's .env for the repo's config/."""
    return REPO_ROOT / ".env" if is_default() else active_dir() / ".env"


def load_env(path: Path) -> list[str]:
    """Read KEY=value lines into os.environ (variables already set win). Returns the names read.
    Blank lines, `# comments` and an `export ` prefix are fine; quotes around a value go."""
    if not path.is_file():
        return []
    names = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
            names.append(key)
    return names


@dataclass(frozen=True)
class Place:
    """place.yaml: what makes this place this place."""

    name: str  # shown as the hub's title and the startup title (the same for every persona)
    venue: str | None = None  # the venue used when neither --venue nor $LAB_OS_VENUE says
    domain: str | None = None  # the brain's address name; not used yet (the secure address is
    # deferred: docs/guides/voice.md → "Secure pages")
    ai_budget_usd_month: float | None = None  # the hub's chat pauses when this month's AI spend
    # reaches it; None = no cap (fine for a local model, not for a paid key)
    calendar: tuple = ()  # dates the greeting may mention: ({"date": "2026-12-15", "what": ...},)
    persona: str | None = None  # who the assistant is (personas/<id>.yaml); None = the plain one
    chat_keep_minutes: float = 30  # the hub keeps a reset or interrupted conversation this long
    about: str = ""  # what the place is, in a few words: the welcome for visitors (quick job 35)
    extra: dict = field(default_factory=dict)  # fields this version doesn't know (kept, warned)


PLACE_FIELDS = {
    "version",
    "name",
    "venue",
    "domain",
    "ai_budget_usd_month",
    "calendar",
    "persona",
    "chat_keep_minutes",
    "about",
    "assistant_moves_arm",
}


def ai_budget() -> float | None:
    """place.yaml's `ai_budget_usd_month` as it is now (the Settings page changes it while the
    brain runs); None = no cap."""
    budget = load_yaml("place.yaml").get("ai_budget_usd_month")
    return float(budget) if budget is not None else None


def assistant_moves_arm() -> bool:
    """place.yaml's `assistant_moves_arm` as it is now (Settings changes it while the brain runs):
    the hub's assistant may move the arm to a pose and hand over the cube (preview 4). Off when
    left out."""
    return load_yaml("place.yaml").get("assistant_moves_arm") is True


def load_place(folder: Path | None = None) -> Place:
    """The place's place.yaml with its local/ changes (default: the active place)."""
    folder = folder or active_dir()
    path = folder / "place.yaml"
    if not path.is_file():
        raise ConfigError(f"{folder} has no place.yaml: start one with `lab-os new-place {folder}`")
    raw = load_yaml("place.yaml", folder)
    extra = {k: v for k, v in raw.items() if k not in PLACE_FIELDS}
    for key in extra:
        log.warning("%s: unknown field %r (kept, not used)", path, key)
    if not raw.get("name"):
        raise ConfigError(f'{path}: `name` is missing (the place\'s name, e.g. "My lab")')
    budget = raw.get("ai_budget_usd_month")
    return Place(
        name=str(raw["name"]),
        venue=raw.get("venue"),
        domain=raw.get("domain"),
        ai_budget_usd_month=float(budget) if budget is not None else None,
        calendar=tuple(c for c in (raw.get("calendar") or []) if isinstance(c, dict)),
        persona=str(raw["persona"]) if raw.get("persona") else None,
        chat_keep_minutes=float(raw.get("chat_keep_minutes", 30)),
        about=" ".join(str(raw.get("about") or "").split()),
        extra=extra,
    )


def _secret(path: Path) -> bool:
    """A .env (not .env.example): someone's real keys, never copied into a new place."""
    return path.name.startswith(".env") and path.name != ".env.example"


def new_place(folder: str | Path) -> Path:
    """Write the starter files (place.yaml, devices.yaml with the fake arm, venues/home.yaml,
    .env.example) into `folder`. Never overwrites: refuses if the folder has a place.yaml."""
    folder = Path(folder).expanduser().resolve()
    if (folder / "place.yaml").exists():
        raise ConfigError(f"{folder} already has a place.yaml; nothing written")
    folder.mkdir(parents=True, exist_ok=True)
    for src in TEMPLATE_DIR.rglob("*"):
        if src.is_file() and "__pycache__" not in src.parts and not _secret(src):
            dest = folder / src.relative_to(TEMPLATE_DIR)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copyfile(src, dest)
    return folder
