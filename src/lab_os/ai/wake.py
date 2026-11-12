"""The wake word (focus step 7): "hey jarvis" heard on the brain's own CPU, nothing sent anywhere.

openWakeWord's models (models/openwakeword/, Apache 2.0 code, CC BY-NC-SA 4.0 models) run here
with onnxruntime, the way openWakeWord 0.6 runs them in streaming mode, without its package (on
Linux it needs tflite-runtime, which has no Python 3.12 build):
16 kHz audio in 80 ms chunks → a mel spectrogram (8 frames a chunk) → a speech embedding over the
last 76 frames (one per chunk) → the phrase's model over the last 16 embeddings → a score 0–1.

`WakeModels` loads the files once for the brain; each screen's audio gets its own `WakeDetector`.
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
# the phrase a persona's `wake_word:` names → its model file in MODELS_DIR, and how it's said
PHRASES = {"hey_jarvis": ("hey_jarvis_v0.1.onnx", "hey Jarvis")}


class WakeModels:
    """The model files, loaded once (onnxruntime sessions are safe to share)."""

    def __init__(self, folder: Path = MODELS_DIR):
        self.folder = folder
        self._sessions: dict[str, object] = {}
        self._problem: str | None = None

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

    def __init__(self, models: WakeModels, word: str = "hey_jarvis", seed: int = 0):
        self.models, self.word = models, word
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

    def feed(self, pcm: bytes) -> float:
        samples = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype=np.int16)
        self._pending = np.concatenate([self._pending, samples])
        best = 0.0
        while self._pending.shape[0] >= CHUNK:
            chunk, self._pending = self._pending[:CHUNK], self._pending[CHUNK:]
            best = max(best, self._step(chunk))
        self.last = best
        return best

    def _step(self, chunk: np.ndarray) -> float:
        self._audio = np.concatenate([self._audio, chunk])[-(CHUNK + 160 * 3) :]
        self._mel = np.vstack([self._mel, self.models.mel(self._audio)])[-10 * 97 :]
        window = self._mel[-MEL_FRAMES:][None]
        self._features = np.vstack([self._features, self.models.embed(window)])[-120:]
        self._chunks += 1
        score = self.models.score(self.word, self._features[-FEATURES:])
        return score if self._chunks > WARMUP else 0.0

    def reset(self) -> None:
        """Forget what was heard (after a wake, or while the answer is spoken)."""
        self._pending = np.zeros(0, np.int16)
        self._chunks = 0
