"""AI setups (models.yaml): where an AI service is, which model, which key, what it costs.

Every setup speaks the OpenAI-style chat interface, so they differ only by address, model name and
key name. `pick()` follows `fallback` when a setup's key isn't in the environment (.env).
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import yaml

from lab_os import config

log = logging.getLogger(__name__)

SETUP_FIELDS = {"where", "base_url", "model", "key_env", "price_per_mtok", "options", "fallback"}


@dataclass(frozen=True)
class Setup:
    name: str
    base_url: str
    model: str
    key_env: str | None = None  # None = no key needed (a local server)
    where: str = ""  # a few words for people: "OpenAI", "On this computer"
    price_in: float = 0.0  # US dollars per 1M input tokens
    price_cached: float = 0.0  # ... per 1M cached input tokens
    price_out: float = 0.0  # ... per 1M output tokens (including reasoning)
    options: dict = field(default_factory=dict)  # added to every request
    fallback: str | None = None

    @property
    def key(self) -> str | None:
        return os.environ.get(self.key_env) or None if self.key_env else None

    @property
    def usable(self) -> bool:
        """Has what it needs to try: a key, or no key needed."""
        return self.key_env is None or bool(self.key)

    @property
    def local(self) -> bool:
        """Runs on this computer or the lab network (no internet needed)."""
        host = urlparse(self.base_url).hostname or ""
        return host in ("localhost", "127.0.0.1", "::1") or host.endswith(".local")

    def cost(self, tokens_in: int, tokens_out: int, tokens_cached: int = 0) -> float:
        fresh = max(0, tokens_in - tokens_cached)
        return (
            fresh * self.price_in + tokens_cached * self.price_cached + tokens_out * self.price_out
        ) / 1_000_000


class NoSetup(LookupError):
    """No usable AI setup. The message is a full sentence for the screen."""


def load_setups(path: Path | None = None) -> dict[str, Setup]:
    path = path or config.shared_path("models.yaml")
    raw = yaml.safe_load(path.read_text()) or {}
    setups = {}
    for name, spec in (raw.get("setups") or {}).items():
        for key in set(spec) - SETUP_FIELDS:
            log.warning("%s: setup %s: unknown field %r (ignored)", path, name, key)
        price = spec.get("price_per_mtok") or {}
        key_env = spec.get("key_env")
        setups[name] = Setup(
            name=name,
            base_url=str(spec["base_url"]).rstrip("/"),
            model=str(spec["model"]),
            key_env=None if key_env in (None, "none", "") else str(key_env),
            where=str(spec.get("where", "")),
            price_in=float(price.get("input", 0)),
            price_cached=float(price.get("cached_input", price.get("input", 0))),
            price_out=float(price.get("output", 0)),
            options=dict(spec.get("options") or {}),
            fallback=spec.get("fallback"),
        )
    return setups


def pick(name: str, setups: dict[str, Setup] | None = None) -> Setup:
    """The setup `name`, or the first usable one along its `fallback` chain."""
    setups = load_setups() if setups is None else setups
    tried, current = [], name
    while current and current not in [t.name for t in tried]:
        setup = setups.get(current)
        if setup is None:
            raise NoSetup(f"There's no AI setup called {current!r} in models.yaml.")
        if setup.usable:
            return setup
        tried.append(setup)
        current = setup.fallback
    keys = " or ".join(t.key_env for t in tried if t.key_env)
    raise NoSetup(f"The AI isn't set up here yet: add {keys} to {config.env_file()}, then restart.")
