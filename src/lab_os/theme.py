"""Design tokens (config/theme.yaml): the one place for visual style. Served as /theme.json."""

from pathlib import Path

import yaml

from lab_os import CONFIG_DIR


def load_theme(path: Path | None = None) -> dict:
    return yaml.safe_load((path or CONFIG_DIR / "theme.yaml").read_text()) or {}
