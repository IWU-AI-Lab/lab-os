"""Shared test setup: no test ever sees a real API key (no .env, none from the shell), and each
test starts with the repo's own config/ as the place."""

import pytest

from lab_os import config


@pytest.fixture(autouse=True)
def _no_env_file_and_default_place(monkeypatch, tmp_path_factory):
    nowhere = tmp_path_factory.mktemp("no-env") / ".env"
    monkeypatch.setattr(config, "env_file", lambda: nowhere)
    monkeypatch.setattr(config, "_active", None)
    monkeypatch.delenv("LAB_OS_CONFIG", raising=False)
    monkeypatch.delenv("LAB_OS_VENUE", raising=False)
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(key, raising=False)  # a key in the shell never reaches a test
