"""The page's silence watch (web/silence.js): when a spoken question ends (quick job 98).
Run with node; skipped without it. Each test feeds levels a piece each 50 ms, as the
microphone's worklet does."""

import json
import shutil
import subprocess

import pytest

from lab_os import REPO_ROOT

MODULE = REPO_ROOT / "src/lab_os/web/silence.js"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node isn't installed")


def ends_at(levels: list[float], **opts) -> float | None:
    """Feed the levels (one each 50 ms); the time (s) the watch ended, or None."""
    script = f"""
import({json.dumps(MODULE.as_uri())}).then(m => {{
  let t = 0, end = null;
  const w = m.silenceWatch(() => {{ if (end === null) end = t; }},
    Object.assign({{ now: () => t }}, {json.dumps(opts)}));
  for (const l of {json.dumps(levels)}) {{ t += 50; w.level(l); }}
  console.log(JSON.stringify(end === null ? null : end / 1000));
}})"""
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


ROOM = 0.008


def voice(seconds: float, fast: bool = True) -> list[float]:
    """Talking: loud syllables with short, still loud-ish dips between the words (a fast, steady
    voice with the browser's gain control has hardly any quiet between its words)."""
    n = round(seconds * 20)
    return [0.12 if i % 4 else (0.05 if fast else ROOM) for i in range(n)]


def quiet(seconds: float) -> list[float]:
    return [ROOM] * round(seconds * 20)


def test_a_long_fast_question_is_not_cut():
    # the 1200 km flight question, fast: about 6 s of talking, then the end
    levels = quiet(0.5) + voice(7.0) + quiet(3.0)
    end = ends_at(levels, floor=ROOM)
    assert end is not None and end > 7.5  # not while talking
    assert end < 7.5 + 2.2  # and soon after the real end


def test_a_pause_in_the_middle_does_not_end_it():
    # "Calculate 37 times 48, … then add 199": a pause of 1.5 s
    levels = quiet(0.3) + voice(2.0) + quiet(1.5) + voice(1.5) + quiet(3.0)
    end = ends_at(levels, floor=ROOM)
    assert end is not None and end > 0.3 + 2.0 + 1.5 + 1.5


def test_the_end_is_two_seconds_of_quiet():
    levels = quiet(0.3) + voice(1.0) + quiet(3.0)
    end = ends_at(levels, floor=ROOM)
    assert end == pytest.approx(1.3 + 2.0, abs=0.11)


def test_a_steady_noise_is_taken_for_the_room():
    # a fan comes on and stays: after a while it's the room, and the question ends
    levels = quiet(0.3) + voice(1.0) + [0.06] * 200
    end = ends_at(levels, floor=ROOM)
    assert end is not None and end < 1.3 + 4.0 + 2.5


def test_nothing_said_ends_after_idle():
    assert ends_at(quiet(7.0), floor=ROOM, idleMs=6000) == pytest.approx(6.0, abs=0.06)


def test_the_hub_pages_take_it_from_voice_js():
    voice_js = (REPO_ROOT / "src/lab_os/web/voice.js").read_text()
    assert 'export { WAKE_QUIET_MS, silenceWatch } from "/web/silence.js"' in voice_js
