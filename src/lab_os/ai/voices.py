"""Voice setups (models.yaml → `voices:`): which service hears (speech-to-text) and speaks
(text-to-speech), which models, which key, what a minute costs. A persona picks one by name
(`voice: main`); `voice: none` = no voice. `pick_voice()` follows `fallback` when a setup's key
isn't in the environment (.env), like the chat's setups (lab_os.ai.models).

Services (`service:`): `gemini` (streamed hearing over Gemini's Live API, speech from a TTS model),
`openai` (/audio/transcriptions after the release, /audio/speech). Switching = a config edit.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml

from lab_os import config

log = logging.getLogger(__name__)

SERVICES = ("gemini", "openai")
VOICE_FIELDS = {
    "where",
    "service",
    "base_url",
    "hear",
    "speak",
    "speaker",
    "style",
    "speed",
    "key_env",
    "price_per_min",
    "fallback",
}


@dataclass(frozen=True)
class VoiceSetup:
    name: str
    service: str  # gemini | openai
    base_url: str
    hear: str  # the speech-to-text model
    speak: str  # the text-to-speech model (the first of `speak:` in models.yaml)
    speaker: str = ""  # the service's voice name (Gemini: Charon, Kore…; OpenAI: onyx, alloy…)
    key_env: str | None = None
    where: str = ""
    price_heard: float = 0.0  # US dollars per minute of audio heard
    price_spoken: float = 0.0  # ... per minute of audio spoken
    fallback: str | None = None
    speak_more: tuple[str, ...] = ()  # more TTS models, tried when one is over its limit
    style: str = ""  # how to speak (accent, mood), sent with each request (OpenAI's `instructions`)
    speed: float | None = None  # OpenAI: 0.25–4 (1 = normal)

    @property
    def speak_models(self) -> tuple[str, ...]:
        return (self.speak, *self.speak_more)

    @property
    def key(self) -> str | None:
        return os.environ.get(self.key_env) or None if self.key_env else None

    @property
    def usable(self) -> bool:
        return self.key_env is None or bool(self.key)

    @property
    def local(self) -> bool:
        host = urlparse(self.base_url).hostname or ""
        return host in ("localhost", "127.0.0.1", "::1") or host.endswith(".local")

    def cost(self, heard_s: float, spoken_s: float) -> float:
        return (heard_s * self.price_heard + spoken_s * self.price_spoken) / 60


class NoVoice(LookupError):
    """No usable voice setup. The message is a full sentence for the screen."""


def load_voices(path: Path | None = None) -> dict[str, VoiceSetup]:
    path = path or config.shared_path("models.yaml")
    raw = yaml.safe_load(path.read_text()) or {}
    voices = {}
    for name, spec in (raw.get("voices") or {}).items():
        for key in set(spec) - VOICE_FIELDS:
            log.warning("%s: voice %s: unknown field %r (ignored)", path, name, key)
        service = str(spec.get("service", ""))
        if service not in SERVICES:
            log.warning("%s: voice %s: service %r isn't one of %s", path, name, service, SERVICES)
            continue
        price = spec.get("price_per_min") or {}
        key_env = spec.get("key_env")
        speak = spec["speak"] if isinstance(spec["speak"], list) else [spec["speak"]]
        voices[name] = VoiceSetup(
            name=name,
            service=service,
            base_url=str(spec["base_url"]).rstrip("/"),
            hear=str(spec["hear"]),
            speak=str(speak[0]),
            speak_more=tuple(str(m) for m in speak[1:]),
            style=" ".join(str(spec.get("style") or "").split()),
            speed=float(spec["speed"]) if spec.get("speed") else None,
            speaker=str(spec.get("speaker") or ""),
            key_env=None if key_env in (None, "none", "") else str(key_env),
            where=str(spec.get("where", "")),
            price_heard=float(price.get("heard", 0)),
            price_spoken=float(price.get("spoken", 0)),
            fallback=spec.get("fallback"),
        )
    return voices


def pick_voice(name: str, voices: dict[str, VoiceSetup] | None = None) -> VoiceSetup:
    """The voice setup `name`, or the first usable one along its `fallback` chain."""
    if name in ("", "none"):
        raise NoVoice("This assistant has no voice (the persona's `voice: none`).")
    voices = load_voices() if voices is None else voices
    tried: list[VoiceSetup] = []
    current = name
    while current and current not in [t.name for t in tried]:
        setup = voices.get(current)
        if setup is None:
            raise NoVoice(f"There's no voice setup called {current!r} in models.yaml.")
        if setup.usable:
            return setup
        tried.append(setup)
        current = setup.fallback
    keys = " or ".join(t.key_env for t in tried if t.key_env)
    raise NoVoice(f"Voice isn't set up here yet: add {keys} to {config.env_file()}, then restart.")
