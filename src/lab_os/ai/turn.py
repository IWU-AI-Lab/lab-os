"""Has the person finished the question? (quick job 110). Runs on this computer, nothing leaves it.

After the wake word (and in conversation mode), the question ended after 2 s of quiet (the page's
silence watch), so the person waited 2 s after each question. Now the brain looks at each short
quiet after speech: Pipecat's **Smart Turn v3.2** (models/smart-turn/, BSD 2-clause) hears the
last 8 s of the voice and says whether the turn is finished (the way the voice falls at the end of
a sentence) or only a pause ("37 times 48, … then add 199": the voice stays up). Finished → the
question ends at once (about 0.3 s after the last word, plus ~20 ms for the model). Not finished →
nothing happens, and the page's silence watch still ends it after its 2 s.

The model's input is Whisper's log-mel spectrogram (80 bands, 8 s = 800 frames). Pipecat makes it
with `transformers.WhisperFeatureExtractor`; `features()` is the same in numpy (tested against it).
"""

import logging
import math

import numpy as np

from lab_os import REPO_ROOT

log = logging.getLogger(__name__)

MODEL_PATH = REPO_ROOT / "models" / "smart-turn" / "smart-turn-v3.2-cpu.onnx"
RATE = 16_000
SECONDS = 8  # the model hears this much (the end of the question; shorter is padded at the start)
FINISHED = 0.5  # the model's score for "the turn is finished" (Pipecat's own threshold)
# The energy check that decides when to ask the model (16-bit PCM loudness, pieces of 50 ms).
SPEECH_RMS = 300.0  # a piece is speech from this loudness (as speech.SPEECH_RMS)...
OVER_ROOM = 3.0  # ... and when it's this many times the room's level
QUIET_S = 0.3  # ask the model after this much quiet after speech
MIN_SPEECH_S = 0.5  # ... once there was this much speech after the wake word (not the phrase's end)

_N_FFT, _HOP, _MELS = 400, 160, 80


def _mel_filters() -> np.ndarray:
    """Whisper's mel filters (Slaney scale and norm, 0–8 kHz): (201, 80)."""

    def to_mel(f):
        f = np.asarray(f, dtype=np.float64)
        lin = 3.0 * f / 200.0
        log_part = 15.0 + np.log(np.maximum(f, 1e-10) / 1000.0) * 27.0 / np.log(6.4)
        return np.where(f >= 1000.0, log_part, lin)

    def to_hz(m):
        m = np.asarray(m, dtype=np.float64)
        lin = 200.0 * m / 3.0
        log_part = 1000.0 * np.exp(np.log(6.4) * (m - 15.0) / 27.0)
        return np.where(m >= 15.0, log_part, lin)

    fft_freqs = np.linspace(0, RATE / 2, _N_FFT // 2 + 1)
    edges = to_hz(np.linspace(to_mel(0.0), to_mel(RATE / 2), _MELS + 2))
    diff = np.diff(edges)
    slopes = edges[None, :] - fft_freqs[:, None]
    down = -slopes[:, :-2] / diff[:-1]
    up = slopes[:, 2:] / diff[1:]
    filters = np.maximum(0.0, np.minimum(down, up))
    return filters * (2.0 / (edges[2 : _MELS + 2] - edges[:_MELS]))


_FILTERS = _mel_filters()
_WINDOW = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(_N_FFT) / _N_FFT)  # periodic Hann


def features(audio: np.ndarray) -> np.ndarray:
    """16 kHz float audio → the model's input (1, 80, 800): the last 8 s (zeros before a shorter
    one), normalized, as Whisper's log-mel spectrogram."""
    n = SECONDS * RATE
    x = np.asarray(audio, dtype=np.float64)[-n:]
    x = np.pad(x, (n - len(x), 0))
    x = (x - x.mean()) / np.sqrt(x.var() + 1e-7)
    x = np.pad(x, _N_FFT // 2, mode="reflect")
    frames = np.lib.stride_tricks.sliding_window_view(x, _N_FFT)[::_HOP]
    power = np.abs(np.fft.rfft(frames * _WINDOW, axis=1)) ** 2  # (801, 201)
    mel = np.log10(np.maximum(power @ _FILTERS, 1e-10)).T[:, :-1]  # (80, 800)
    mel = np.maximum(mel, mel.max() - 8.0)
    return ((mel + 4.0) / 4.0).astype(np.float32)[None]


class TurnModel:
    """Smart Turn, loaded once (the first question). `finished(pcm)` → the score 0–1."""

    def __init__(self, path=MODEL_PATH):
        self.path = path
        self._session = None
        self.why_not: str | None = None

    def _load(self):
        if self._session is None and self.why_not is None:
            try:
                import onnxruntime as ort

                opts = ort.SessionOptions()
                opts.inter_op_num_threads = opts.intra_op_num_threads = 1
                self._session = ort.InferenceSession(
                    str(self.path), opts, providers=["CPUExecutionProvider"]
                )
            except Exception as e:  # no model file, a broken one: the page's 2 s stays
                self.why_not = f"the turn model didn't load ({e})"
                log.warning("voice: %s; questions end after the page's silence", self.why_not)
        return self._session

    def finished(self, pcm: bytes) -> float:
        """How sure the model is that the person finished talking (16-bit 16 kHz mono PCM)."""
        session = self._load()
        if session is None:
            return 0.0
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        out = session.run(None, {"input_features": features(audio)})
        return float(np.asarray(out[0]).reshape(-1)[0])


def _rms(pcm: bytes) -> float:
    a = np.frombuffer(pcm, dtype=np.int16).astype(np.float64)
    return math.sqrt(float(np.mean(a * a))) if len(a) else 0.0


class TurnWatch:
    """One question's audio: `feed()` each piece; it returns True once per quiet after enough
    speech, when it's time to ask the model (`audio()` is what the model hears)."""

    def __init__(self, floor: float = 0.0, preroll: bytes = b""):
        self.floor = floor
        self.buf = bytearray(preroll[-SECONDS * RATE * 2 :])
        self.speech_s = 0.0  # speech heard after the wake word (the preroll doesn't count)
        self.quiet_s = 0.0
        self.asked = True  # nothing to ask before the first speech

    def feed(self, pcm: bytes) -> bool:
        self.buf += pcm
        del self.buf[: max(0, len(self.buf) - SECONDS * RATE * 2)]
        rms, secs = _rms(pcm), len(pcm) / 2 / RATE
        if rms >= max(SPEECH_RMS, self.floor * OVER_ROOM):
            self.speech_s += secs
            self.quiet_s = 0.0
            self.asked = False
            return False
        # the room's level: down fast, up slowly (quick job 98: soft syllables don't raise it much)
        k = 0.1 if rms < self.floor else 0.005
        self.floor = rms if self.floor == 0.0 else self.floor + k * (rms - self.floor)
        self.quiet_s += secs
        if not self.asked and self.speech_s >= MIN_SPEECH_S and self.quiet_s >= QUIET_S:
            self.asked = True
            return True
        return False

    def audio(self) -> bytes:
        return bytes(self.buf)
