"""Talk to a voice service: hear (speech-to-text) and speak (text-to-speech). Plain aiohttp.

Audio in is what the hub page sends: 16-bit PCM, 16 kHz, mono (`RATE`). Audio out is a WAV file.

- `hearing_for()` starts hearing one utterance: `feed()` audio while the person talks, `finish()`
  when they're done → the words. Gemini hears while the audio streams in (its Live API, a
  transcription model), so `on_words` gets the words so far as they come (dictation shows them);
  OpenAI hears the whole recording after the release.
- `speak()` turns a piece of text into a WAV.
"""

import asyncio
import base64
import contextlib
import dataclasses
import io
import json
import logging
import time
import wave
from collections.abc import Callable
from urllib.parse import urlparse

import aiohttp

from lab_os.ai.voices import VoiceSetup

log = logging.getLogger(__name__)

RATE = 16_000  # audio from the page: samples per second (16-bit, mono)
CONNECT_TIMEOUT_S = 10.0
SPEAK_TIMEOUT_S = 15.0  # a sentence takes 2–4 s; longer = that model is stuck (the next one tries)
FINISH_TIMEOUT_S = 6.0  # after the release, the longest wait for the last words
NO_SPEECH_WAIT_S = 1.5  # ... when the service hasn't noticed any speech at all
GEMINI_LIVE_PATH = "/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"


class VoiceError(RuntimeError):
    """The voice service didn't do it. The message is a full sentence for the screen."""


class OverLimit(VoiceError):
    """The service's limit for this model is used up for now (HTTP 429): try again after
    `retry_s` seconds, or another model."""

    def __init__(self, message: str, retry_s: float = 60.0):
        super().__init__(message)
        self.retry_s = retry_s


class ModelTrouble(VoiceError):
    """This model is busy (HTTP 5xx) or didn't answer in time: another model may."""


def _retry_s(body: str) -> float:
    """Gemini's 429 says how long to wait ("retryDelay": "53s"); else a minute."""
    try:
        for detail in json.loads(body).get("error", {}).get("details", []):
            if str(detail.get("retryDelay", "")).endswith("s"):
                return float(detail["retryDelay"][:-1])
    except (ValueError, AttributeError, TypeError):
        pass
    return 60.0


def wav_bytes(pcm: bytes, rate: int = RATE) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return out.getvalue()


def wav_seconds(data: bytes) -> float:
    """How long a WAV plays (0 if it can't be read). Counted from the bytes really there: a streamed
    WAV (OpenAI's) says "as long as possible" in its header (GOTCHAS)."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            frame = w.getsampwidth() * w.getnchannels()
            return len(w.readframes(w.getnframes())) / frame / float(w.getframerate())
    except (wave.Error, EOFError, ZeroDivisionError):
        return 0.0


def _rewrap(data: bytes) -> bytes:
    """A WAV with a correct header (a streamed one's says it's endless)."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            if w.getsampwidth() != 2 or w.getnchannels() != 1:
                return data
            return wav_bytes(w.readframes(w.getnframes()), w.getframerate())
    except (wave.Error, EOFError):
        return data


def _who(setup: VoiceSetup) -> str:
    return setup.where or setup.name


def _http_error(setup: VoiceSetup, status: int, body: str) -> VoiceError:
    who = _who(setup)
    if status in (401, 403):
        return VoiceError(f"{who} refused the API key ({setup.key_env}), so voice is off.")
    if status == 429:
        return OverLimit(
            f"{who} says we're sending too much voice (the free key has a limit per minute and "
            "per day). The answer is on the screen.",
            _retry_s(body),
        )
    if status in (500, 502, 503, 504):
        return ModelTrouble(f"{who}'s voice is busy or having trouble right now (HTTP {status}).")
    if status == 404:
        return VoiceError(f"{who} doesn't know the voice model (models.yaml → voices).")
    log.warning("%s voice: HTTP %s: %s", setup.name, status, body[:500])
    return VoiceError(f"{who}'s voice answered with an error (HTTP {status}).")


def _unreachable(setup: VoiceSetup) -> VoiceError:
    where = "is the local voice server running?" if setup.local else "is there internet?"
    return VoiceError(f"I can't reach {_who(setup)} for the voice ({where}).")


# ---------- hearing ----------

Words = Callable[[str], None]


class Hearing:
    """One utterance. `text` is everything heard so far."""

    def __init__(self, session: aiohttp.ClientSession, setup: VoiceSetup, on_words: Words):
        self.session, self.setup, self.on_words = session, setup, on_words
        self.audio_bytes = 0  # for the spend log: how much was heard

    @property
    def seconds(self) -> float:
        return self.audio_bytes / (2 * RATE)

    async def start(self) -> None:
        """Get ready (connect). Audio fed before it's ready is kept and sent after."""

    def feed(self, pcm: bytes) -> None:
        self.audio_bytes += len(pcm)

    async def finish(self) -> str:
        """The person is done: the words (may be empty: nothing was said)."""
        raise NotImplementedError

    async def close(self) -> None:
        """Stop without waiting for the words (cancel)."""


class GeminiHearing(Hearing):
    """Gemini's Live API with a transcription model: the words come while the audio streams in.
    Each pause ends a segment with its final text; the next segment's words start fresh."""

    def __init__(self, session, setup, on_words):
        super().__init__(session, setup, on_words)
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._tasks: list[asyncio.Task] = []
        self._finals: list[str] = []
        self._interim = ""
        self._speech = False  # the service noticed speech
        self._in_activity = False
        self._changed = asyncio.Event()
        self._failed: VoiceError | None = None

    @property
    def text(self) -> str:
        return " ".join(t for t in (*self._finals, self._interim) if t).strip()

    def _url(self) -> str:
        u = urlparse(self.setup.base_url)
        scheme = "wss" if u.scheme == "https" else "ws"
        return f"{scheme}://{u.netloc}{GEMINI_LIVE_PATH}"

    async def start(self) -> None:
        try:
            self._ws = await self.session.ws_connect(
                self._url(),
                headers={"x-goog-api-key": self.setup.key or ""},
                timeout=aiohttp.ClientWSTimeout(ws_close=5),
                heartbeat=20,
            )
            await self._ws.send_json({"setup": {"model": f"models/{self.setup.hear}"}})
            msg = await asyncio.wait_for(self._ws.receive(), CONNECT_TIMEOUT_S)
        except (aiohttp.ClientError, TimeoutError, OSError) as e:
            log.warning("%s hearing: %s", self.setup.name, e)
            await self.close()
            raise _unreachable(self.setup) from None
        if "setupComplete" not in _json(msg):
            await self.close()
            raise self._closed(msg)
        self._tasks = [asyncio.create_task(self._send()), asyncio.create_task(self._receive())]

    def _closed(self, msg) -> VoiceError:
        reason = (getattr(msg, "extra", None) or "") if msg is not None else ""
        log.warning("%s hearing closed: %s %s", self.setup.name, getattr(msg, "data", ""), reason)
        low = str(reason).lower()
        if "quota" in low or "exceed" in low or "rate" in low:
            return _http_error(self.setup, 429, str(reason))
        if "key" in low or "permission" in low or "auth" in low:
            return _http_error(self.setup, 401, str(reason))
        if "model" in low and "not found" in low:
            return _http_error(self.setup, 404, str(reason))
        return VoiceError(f"{_who(self.setup)} stopped listening ({reason or 'no reason given'}).")

    def feed(self, pcm: bytes) -> None:
        super().feed(pcm)
        self._queue.put_nowait(pcm)

    async def _send(self) -> None:
        assert self._ws is not None
        try:
            while (pcm := await self._queue.get()) is not None:
                data = base64.b64encode(pcm).decode()
                audio = {"data": data, "mimeType": f"audio/pcm;rate={RATE}"}
                await self._ws.send_json({"realtimeInput": {"audio": audio}})
            await self._ws.send_json({"realtimeInput": {"audioStreamEnd": True}})
        except (aiohttp.ClientError, ConnectionResetError, RuntimeError) as e:
            log.info("%s hearing: send stopped (%s)", self.setup.name, e)

    async def _receive(self) -> None:
        assert self._ws is not None
        async for msg in self._ws:
            if msg.type not in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
                break
            data = _json(msg)
            content = data.get("serverContent") or {}
            activity = (data.get("voiceActivity") or {}).get("type")
            if activity == "ACTIVITY_START":
                self._speech = self._in_activity = True
            elif activity == "ACTIVITY_END":
                self._in_activity = False
            if "interimInputTranscription" in content:
                self._interim = (content["interimInputTranscription"].get("text") or "").strip()
                self.on_words(self.text)
            if "inputTranscription" in content:
                final = (content["inputTranscription"].get("text") or "").strip()
                if final:
                    self._finals.append(final)
                    self._speech = True
                self._interim = ""
                self.on_words(self.text)
            self._changed.set()
        if self._ws.close_code not in (None, 1000):
            self._failed = self._closed(
                aiohttp.WSMessage(aiohttp.WSMsgType.CLOSE, self._ws.close_code, None)
            )
        self._changed.set()

    def _settled(self, ended_at: float) -> bool:
        if self._failed or self._ws is None or self._ws.closed:
            return True
        if self._in_activity or self._interim:
            return False  # words still on their way
        return self._speech or time.monotonic() - ended_at > NO_SPEECH_WAIT_S

    async def finish(self) -> str:
        self._queue.put_nowait(None)
        ended = time.monotonic()
        while time.monotonic() - ended < FINISH_TIMEOUT_S and not self._settled(ended):
            self._changed.clear()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._changed.wait(), 0.1)
        text = self.text
        await self.close()
        if self._failed and not text:
            raise self._failed
        return text

    async def close(self) -> None:
        for t in self._tasks:
            t.cancel()
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()


class RecordedHearing(Hearing):
    """OpenAI-style /audio/transcriptions: the whole recording after the release."""

    def __init__(self, session, setup, on_words):
        super().__init__(session, setup, on_words)
        self._pcm = bytearray()

    def feed(self, pcm: bytes) -> None:
        super().feed(pcm)
        self._pcm += pcm

    async def finish(self) -> str:
        if not self._pcm:
            return ""
        form = aiohttp.FormData()
        form.add_field("model", self.setup.hear)
        form.add_field(
            "file", wav_bytes(bytes(self._pcm)), filename="speech.wav", content_type="audio/wav"
        )
        try:
            async with self.session.post(
                f"{self.setup.base_url}/audio/transcriptions",
                data=form,
                headers={"Authorization": f"Bearer {self.setup.key}"} if self.setup.key else {},
                timeout=aiohttp.ClientTimeout(sock_connect=CONNECT_TIMEOUT_S, total=30),
            ) as resp:
                if resp.status != 200:
                    raise _http_error(self.setup, resp.status, await resp.text())
                text = str((await resp.json()).get("text") or "").strip()
        except (aiohttp.ClientError, TimeoutError):
            raise _unreachable(self.setup) from None
        self.on_words(text)
        return text


def hearing_for(session: aiohttp.ClientSession, setup: VoiceSetup, on_words: Words) -> Hearing:
    cls = GeminiHearing if setup.service == "gemini" else RecordedHearing
    return cls(session, setup, on_words)


def _json(msg) -> dict:
    try:
        if msg.type == aiohttp.WSMsgType.TEXT:
            return json.loads(msg.data)
        if msg.type == aiohttp.WSMsgType.BINARY:
            return json.loads(msg.data.decode())
    except (ValueError, UnicodeDecodeError):
        pass
    return {}


# ---------- speaking ----------


def _pcm_rate(mime: str) -> int | None:
    """`audio/L16;codec=pcm;rate=24000` → 24000 (raw samples to wrap); a WAV → None."""
    if "wav" in mime:
        return None
    for part in mime.split(";"):
        if part.strip().startswith("rate="):
            return int(part.split("=", 1)[1])
    return 24_000


async def speak_any(
    session: aiohttp.ClientSession, setup: VoiceSetup, text: str, resting: dict[str, float]
) -> bytes:
    """Like `speak()`, trying the setup's TTS models in order: one over its limit (HTTP 429) rests
    until its retry time (`resting`: model → time.monotonic() it may be used again, kept by the
    caller across calls); a busy or stuck one (5xx, no answer in time) is skipped this once.
    Gemini's free key allows 3 requests a minute and 10 a day per model (GOTCHAS)."""
    last: VoiceError | None = None
    for model in setup.speak_models:
        if resting.get(model, 0) > time.monotonic():
            continue
        try:
            return await speak(session, dataclasses.replace(setup, speak=model), text)
        except OverLimit as e:
            log.info("%s voice: %s is over its limit for %.0f s", setup.name, model, e.retry_s)
            resting[model] = time.monotonic() + e.retry_s
            last = e
        except ModelTrouble as e:
            log.info("%s voice: %s: %s", setup.name, model, e)
            last = e
    raise last or _http_error(setup, 429, "")


async def speak(session: aiohttp.ClientSession, setup: VoiceSetup, text: str) -> bytes:
    """`text` spoken, as a WAV file (with the setup's first TTS model)."""
    timeout = aiohttp.ClientTimeout(sock_connect=CONNECT_TIMEOUT_S, total=SPEAK_TIMEOUT_S)
    try:
        if setup.service == "gemini":
            body = {
                "contents": [{"parts": [{"text": text}]}],
                "generationConfig": {"responseModalities": ["AUDIO"]},
            }
            if setup.speaker:
                body["generationConfig"]["speechConfig"] = {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": setup.speaker}}
                }
            async with session.post(
                f"{setup.base_url}/models/{setup.speak}:generateContent",
                json=body,
                headers={"x-goog-api-key": setup.key or ""},
                timeout=timeout,
            ) as resp:
                if resp.status != 200:
                    raise _http_error(setup, resp.status, await resp.text())
                data = await resp.json()
            try:
                inline = data["candidates"][0]["content"]["parts"][0]["inlineData"]
            except (KeyError, IndexError, TypeError):
                raise VoiceError(f"{_who(setup)} sent no audio for that.") from None
            audio = base64.b64decode(inline["data"])
            rate = _pcm_rate(str(inline.get("mimeType", "")))
            return wav_bytes(audio, rate) if rate else audio
        body = {"model": setup.speak, "input": text, "response_format": "wav"}
        if setup.speaker:
            body["voice"] = setup.speaker
        if setup.style:
            body["instructions"] = setup.style  # accent, mood (gpt-4o-mini-tts and newer)
        if setup.speed:
            body["speed"] = setup.speed
        async with session.post(
            f"{setup.base_url}/audio/speech",
            json=body,
            headers={"Authorization": f"Bearer {setup.key}"} if setup.key else {},
            timeout=timeout,
        ) as resp:
            if resp.status != 200:
                raise _http_error(setup, resp.status, await resp.text())
            return _rewrap(await resp.read())
    except VoiceError:
        raise
    except TimeoutError:
        raise ModelTrouble(f"{_who(setup)}'s voice didn't answer in time.") from None
    except aiohttp.ClientError:
        raise _unreachable(setup) from None
