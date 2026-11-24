"""The wake word (focus step 7): the persona's phrase ("hey Jarvis", "OK computer", …) heard on
the brain's own CPU, nothing sent anywhere.

openWakeWord's models (models/openwakeword/, Apache 2.0 code, CC BY-NC-SA 4.0 models) run here
with onnxruntime, the way openWakeWord 0.6 runs them in streaming mode, without its package (on
Linux it needs tflite-runtime, which has no Python 3.12 build):
16 kHz audio in 80 ms chunks → a mel spectrogram (8 frames a chunk) → a speech embedding over the
last 76 frames (one per chunk) → the phrase's model over the last 16 embeddings → a score 0–1.

`WakeModels` loads the files once for the brain; each screen's audio gets its own `WakeDetector`.

How sensitive (a setting per device, 1–9): openWakeWord's own two knobs, `threshold` (the score
that counts) and `patience` (that many 80 ms chunks in a row at or over it). Its other two options
were tried on the recordings and left out (docs/guides/voice.md → "Sensitivity"): its Silero VAD
filter zeroed a real "hey Jarvis" in loud noise (the opposite of what a noisy room needs), and its
Speex noise suppression is a Linux-only C package; the browser already suppresses noise before the
audio gets here.

A verifier for each word (quick job 99, openWakeWord's "custom verifier model"): a small model
trained on one speaker's own tries of the word, in many tones, and on their other talk (the Wake
Word page, `hub/wake_clips.py`). A score from VERIFY_FROM up to the threshold asks it; when it says
"the word", the chunk counts as one at the threshold. A score at the threshold still counts without
it, so other people wake it as before. openWakeWord's own version (scikit-learn's logistic
regression, a joblib file) is the same idea; this one is numpy only, and its file is
`config/local/wake/<word>/verifier.npz`.
"""

import logging
from pathlib import Path

import numpy as np

from lab_os import REPO_ROOT

log = logging.getLogger(__name__)

MODELS_DIR = REPO_ROOT / "models" / "openwakeword"
CHUNK = 1280  # samples: 80 ms at 16 kHz
THRESHOLD = 0.5  # openWakeWord's default
MEL_FRAMES = 76  # per embedding
FEATURES = 16  # embeddings per score
WARMUP = 5  # the first scores are noise (openWakeWord zeroes them too)
# sensitivity (1 = fewest false wakes … 9 = hears the most) → (threshold, patience). 5 is
# openWakeWord's default. On the recordings, noise alone scored up to ~0.2, so the most sensitive
# levels also want two chunks in a row.
SENSITIVITY = {
    1: (0.8, 1),
    2: (0.7, 1),
    3: (0.6, 1),
    4: (0.55, 1),
    5: (THRESHOLD, 1),
    6: (0.45, 1),
    7: (0.4, 1),
    8: (0.33, 2),
    9: (0.25, 2),
}
DEFAULT_SENSITIVITY = 5
VERIFY_FROM = 0.1  # a score this high but under the threshold asks the word's verifier, if any
VERIFIED = 0.5  # the verifier's chance that it was the word, for the chunk to count
# the phrase a persona's `wake_word:` names → its model file in MODELS_DIR, and how it's said.
# hey_jarvis is openWakeWord's; the others are from a community collection (quick job 90,
# models/openwakeword/README.md): trained by different people, so drop one that wakes badly.
PHRASES = {
    "hey_jarvis": ("hey_jarvis_v0.1.onnx", "hey Jarvis"),
    "ok_computer": ("ok_computer.onnx", "OK computer"),
    "tars": ("tars.onnx", "TARS"),
    "hey_friday": ("hey_friday.onnx", "hey Friday"),
}


def sensitivity_level(value) -> int:
    """A device's setting (1–9, a number or its text) → a level; anything else = the default."""
    try:
        level = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SENSITIVITY
    return level if level in SENSITIVITY else DEFAULT_SENSITIVITY


class Verifier:
    """A logistic regression over the phrase model's input (16 embeddings × 96): the chance that a
    window is this speaker saying the word."""

    def __init__(self, mean: np.ndarray, scale: np.ndarray, weights: np.ndarray, bias: float):
        self.mean, self.scale, self.weights, self.bias = mean, scale, weights, float(bias)

    def chance(self, features: np.ndarray) -> np.ndarray | float:
        """features: (16, 96) or (n, 16, 96) → the chance(s), 0–1."""
        x = (features.reshape(-1, self.mean.shape[0]) - self.mean) / self.scale
        p = 1 / (1 + np.exp(-np.clip(x @ self.weights + self.bias, -30, 30)))
        return float(p[0]) if features.ndim == 2 else p

    @classmethod
    def fit(cls, pos: np.ndarray, neg: np.ndarray, l2: float = 1.0, steps: int = 400) -> "Verifier":
        """Train on windows (n, 16, 96) of the word (pos) and of other sound (neg). Each side
        weighs the same, however many windows it has."""
        x = np.concatenate([pos, neg]).reshape(len(pos) + len(neg), -1).astype(np.float64)
        y = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
        mean, scale = x.mean(0), x.std(0) + 1e-3
        x = (x - mean) / scale
        sw = np.where(y == 1, 0.5 / len(pos), 0.5 / len(neg))
        w, b = np.zeros(x.shape[1]), 0.0
        rate = 0.5
        for _ in range(steps):  # plain gradient descent: small data, a convex problem
            p = 1 / (1 + np.exp(-np.clip(x @ w + b, -30, 30)))
            g = sw * (p - y)
            w -= rate * (x.T @ g + l2 * w / len(y))
            b -= rate * g.sum()
        return cls(mean, scale, w, b)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:  # np.savez adds ".npz" to a name without it
            np.savez(f, mean=self.mean, scale=self.scale, weights=self.weights, bias=self.bias)

    @classmethod
    def load(cls, path: Path) -> "Verifier":
        with np.load(path) as d:
            return cls(d["mean"], d["scale"], d["weights"], float(d["bias"]))


class WakeModels:
    """The model files, loaded once (onnxruntime sessions are safe to share)."""

    def __init__(self, folder: Path = MODELS_DIR, verifiers: Path | None = None):
        self.folder = folder
        self._sessions: dict[str, object] = {}
        self._problem: str | None = None
        self._verifiers_dir = verifiers  # None: the place's config/local/wake/
        self._verifiers: dict[str, tuple[float, Verifier | None]] = {}  # word → (file time, it)

    def verifier_path(self, word: str) -> Path:
        if self._verifiers_dir is not None:
            return self._verifiers_dir / word / "verifier.npz"
        from lab_os import config

        return config.local_dir() / "wake" / word / "verifier.npz"

    def verifier(self, word: str) -> Verifier | None:
        """The word's verifier, if one was trained here (read again when its file changes)."""
        path = self.verifier_path(word)
        try:
            when = path.stat().st_mtime
        except OSError:
            self._verifiers.pop(word, None)
            return None
        kept = self._verifiers.get(word)
        if kept is None or kept[0] != when:
            try:
                kept = (when, Verifier.load(path))
            except (OSError, ValueError, KeyError) as e:
                log.warning("wake word: the verifier %s can't be read (%s)", path, e)
                kept = (when, None)
            self._verifiers[word] = kept
        return kept[1]

    def why_not(self, word: str) -> str | None:
        """Why this phrase can't be heard here (a sentence), or None."""
        if word not in PHRASES:
            return f"There's no wake word model for {word!r} (models/openwakeword/README.md)."
        try:
            self._load(word)
        except (ImportError, OSError, RuntimeError) as e:
            return f"The wake word can't run here: {e}"
        return None

    def _session(self, name: str):
        if name not in self._sessions:
            import onnxruntime as ort  # a few MB to import: only when the wake word is used

            path = self.folder / name
            if not path.is_file():
                raise OSError(f"{path} is missing")
            opts = ort.SessionOptions()
            opts.inter_op_num_threads = opts.intra_op_num_threads = 1  # small; leave the CPU free
            self._sessions[name] = ort.InferenceSession(
                str(path), opts, providers=["CPUExecutionProvider"]
            )
        return self._sessions[name]

    def _load(self, word: str) -> None:
        for name in ("melspectrogram.onnx", "embedding_model.onnx", PHRASES[word][0]):
            self._session(name)

    def mel(self, audio: np.ndarray) -> np.ndarray:
        """int16 samples → mel frames (n, 32), scaled the way openWakeWord does (x / 10 + 2)."""
        out = self._session("melspectrogram.onnx").run(
            None, {"input": audio.astype(np.float32)[None, :]}
        )[0]
        return np.squeeze(out) / 10 + 2

    def embed(self, frames: np.ndarray) -> np.ndarray:
        """(n, 76, 32) mel windows → (n, 96) embeddings."""
        out = self._session("embedding_model.onnx").run(
            None, {"input_1": frames.astype(np.float32)[..., None]}
        )[0]
        return out.reshape(frames.shape[0], -1)

    def score(self, word: str, features: np.ndarray) -> float:
        model = self._session(PHRASES[word][0])
        name = model.get_inputs()[0].name
        return float(model.run(None, {name: features[None].astype(np.float32)})[0].squeeze())


class WakeDetector:
    """One screen's audio: `feed()` 16-bit 16 kHz PCM, get the best score in it."""

    def __init__(
        self,
        models: WakeModels,
        word: str = "hey_jarvis",
        seed: int = 0,
        sensitivity: int = DEFAULT_SENSITIVITY,
    ):
        self.models, self.word = models, word
        self.set_sensitivity(sensitivity)
        self._run = 0  # chunks in a row at or over the threshold
        self.fired = False  # the last feed heard the phrase (threshold and patience)
        self._pending = np.zeros(0, np.int16)
        self._audio = np.zeros(0, np.int16)  # the last chunk + 3 frames of context
        self._mel = np.ones((MEL_FRAMES, 32), np.float32)
        # like openWakeWord: start from embeddings of 4 s of quiet noise
        noise = np.random.default_rng(seed).integers(-1000, 1000, 16000 * 4).astype(np.int16)
        spec = models.mel(noise)
        windows = np.stack(
            [spec[i : i + MEL_FRAMES] for i in range(0, spec.shape[0] - MEL_FRAMES + 1, 8)]
        )
        self._features = models.embed(windows)
        self._chunks = 0
        self.last = 0.0  # the best score of the last feed
        self.verified = False  # the last feed fired only with the verifier's help
        self.windows: list[tuple[float, np.ndarray]] | None = None  # (score, window) of each chunk
        self.verifier = models.verifier(word)  # this speaker's tries of the word, if trained here

    def set_sensitivity(self, sensitivity) -> None:
        self.sensitivity = sensitivity_level(sensitivity)
        self.threshold, self.patience = SENSITIVITY[self.sensitivity]

    def feed(self, pcm: bytes) -> float:
        """Returns the best score in this audio; `fired` says whether the phrase counts as heard."""
        samples = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype=np.int16)
        self._pending = np.concatenate([self._pending, samples])
        best, self.fired, self.verified = 0.0, False, False
        while self._pending.shape[0] >= CHUNK:
            chunk, self._pending = self._pending[:CHUNK], self._pending[CHUNK:]
            score = self._step(chunk)
            best = max(best, score)
            hit = score >= self.threshold
            if not hit and score >= VERIFY_FROM and self.verifier is not None:
                hit = self.verifier.chance(self._features[-FEATURES:]) >= VERIFIED
                self.verified = self.verified or hit
            self._run = self._run + 1 if hit else 0
            self.fired = self.fired or self._run >= self.patience
        self.last = best
        return best

    def _step(self, chunk: np.ndarray) -> float:
        self._audio = np.concatenate([self._audio, chunk])[-(CHUNK + 160 * 3) :]
        self._mel = np.vstack([self._mel, self.models.mel(self._audio)])[-10 * 97 :]
        window = self._mel[-MEL_FRAMES:][None]
        self._features = np.vstack([self._features, self.models.embed(window)])[-120:]
        self._chunks += 1
        if self._chunks % 25 == 0:  # each 2 s: a verifier trained meanwhile works at once
            self.verifier = self.models.verifier(self.word)
        score = self.models.score(self.word, self._features[-FEATURES:])
        score = score if self._chunks > WARMUP else 0.0
        if self.windows is not None and self._chunks > WARMUP:  # training (hub/wake_clips.py)
            self.windows.append((score, self._features[-FEATURES:].copy()))
        return score

    def reset(self) -> None:
        """Forget what was heard (after a wake, or while the answer is spoken)."""
        self._pending = np.zeros(0, np.int16)
        self._chunks = self._run = 0
