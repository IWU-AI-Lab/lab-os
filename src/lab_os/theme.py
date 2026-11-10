"""Design tokens (config/theme.yaml): the one place for visual style. Served as /theme.json.
The same at every place (a place's own theme.yaml would win, but the design means one theme)."""

from pathlib import Path

import yaml

from lab_os import config


def load_theme(path: Path | None = None) -> dict:
    return yaml.safe_load((path or config.shared_path("theme.yaml")).read_text()) or {}
