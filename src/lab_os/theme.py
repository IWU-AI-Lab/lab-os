"""Design tokens (config/theme.yaml): the one place for visual style. Served as /theme.json.
A place's own theme.yaml and its local/theme.yaml (the settings page's changes) are merged over the
repo's, value by value (`config.load_yaml`)."""

from pathlib import Path

import yaml

from lab_os import config


def load_theme(path: Path | None = None) -> dict:
    """The theme with every layer merged; `path`: that one file only."""
    if path:
        return yaml.safe_load(path.read_text()) or {}
    return config.load_yaml("theme.yaml", shared=True)
