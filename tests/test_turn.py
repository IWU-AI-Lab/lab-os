"""Quick job 110: the turn model ends a finished question at once, and waits through a pause in the
middle of one. The fixtures are macOS `say` (16 kHz): "What time is it?" and "Calculate 37 times
48, and then"."""

import wave
from pathlib import Path

import numpy as np
import pytest

from lab_os.ai.turn import FINISHED, MIN_SPEECH_S, QUIET_S, TurnModel, TurnWatch, features

FIXTURES = Path(__file__).parent / "fixtures"
LOUD = (np.ones(800) * 3000).astype(np.int16).tobytes()  # 50 ms of "speech"
QUIET = (np.ones(800) * 20).astype(np.int16).tobytes()  # 50 ms of the room


def pcm(name: str) -> bytes:
    with wave.open(str(FIXTURES / f"{name}.wav")) as w:
        assert w.getframerate() == 16000 and w.getsampwidth() == 2
        return w.readframes(w.getnframes())


def test_the_features_are_whispers():
    """Values from transformers' WhisperFeatureExtractor(chunk_length=8) on the same audio (what
    Pipecat's inference.py uses), 2026-11-25."""
    audio = np.frombuffer(pcm("turn_finished"), np.int16).astype(np.float32) / 32768
    f = features(audio)
    assert f.shape == (1, 80, 800) and f.dtype == np.float32
    assert f.mean() == pytest.approx(0.0738357, abs=1e-5)
    assert f[0, 10, 700] == pytest.approx(0.6980228, abs=1e-5)
    assert f[0, 40, 750] == pytest.approx(1.1319829, abs=1e-5)
    assert f[0, 70, 780] == pytest.approx(0.3515073, abs=1e-5)
    assert f.max() == pytest.approx(1.9919891, abs=1e-5)


def test_the_model_tells_a_finished_question_from_a_pause():
    model = TurnModel()
    after = b"\x00\x00" * int(16_000 * QUIET_S)  # what it hears when it's asked
    assert model.finished(pcm("turn_finished") + after) > 0.9
    assert model.finished(pcm("turn_goes_on") + after) < 0.1
    assert model.why_not is None


def test_no_model_file_means_the_page_ends_it(tmp_path):
    model = TurnModel(tmp_path / "none.onnx")
    assert model.finished(LOUD) == 0.0 and "didn't load" in model.why_not


def test_the_watch_asks_once_per_quiet_after_enough_speech():
    w = TurnWatch(floor=20)
    asked = [w.feed(LOUD) for _ in range(4)]  # 0.2 s: the end of the wake word, not a question
    asked += [w.feed(QUIET) for _ in range(10)]
    assert not any(asked)
    n = int(MIN_SPEECH_S / 0.05)
    asked = [w.feed(LOUD) for _ in range(n)] + [w.feed(QUIET) for _ in range(20)]
    assert asked.count(True) == 1
    assert asked.index(True) == n + int(round(QUIET_S / 0.05)) - 1  # after 0.3 s of quiet
    assert [w.feed(LOUD), w.feed(QUIET), *[w.feed(QUIET) for _ in range(6)]].count(True) == 1
    assert len(w.audio()) <= 8 * 32_000


def test_the_room_noise_is_not_speech():
    w = TurnWatch(floor=400)  # a loud room: 1000 is under 3 times it
    hum = (np.ones(800) * 1000).astype(np.int16).tobytes()
    assert not any(w.feed(hum) for _ in range(40)) and w.speech_s == 0


def test_the_threshold_is_pipecats():
    assert FINISHED == 0.5
