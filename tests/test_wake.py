# ruff: noqa: F811 (`key` is a fixture from test_voice, used as an argument)
"""The wake word (step 7): openWakeWord's models on the brain, and a hands-free turn over /ws/voice.
The recordings in fixtures/ were made with Gemini's TTS (2026-11-12): "Hey Jarvis!" and "Hey, can
you show me the arm? Thanks, Jordan." No microphone, no internet (a fake voice service)."""

import asyncio
import base64
import json
import wave
from pathlib import Path

import numpy as np
import pytest
from aiohttp import WSMsgType
from test_voice import HEARD, SECOND, key, until, voice_app  # noqa: F401 (key is a fixture)

from lab_os.ai.wake import (
    SENSITIVITY,
    THRESHOLD,
    WakeDetector,
    WakeModels,
    sensitivity_level,
)
from lab_os.hub.voice import TurnTiming, strip_wake
from lab_os.venues import Venue

FIXTURES = Path(__file__).parent / "fixtures"


def pcm(name: str) -> bytes:
    with wave.open(str(FIXTURES / f"{name}.wav")) as w:
        assert w.getframerate() == 16000 and w.getsampwidth() == 2
        return w.readframes(w.getnframes())


def pieces(data: bytes, size: int = 1600):  # 50 ms, as the page sends them
    return [data[i : i + size] for i in range(0, len(data), size)]


@pytest.fixture(scope="module")
def models():
    return WakeModels()


def best(models, data: bytes) -> float:
    d = WakeDetector(models)
    return max(d.feed(p) for p in pieces(data))


def test_hey_jarvis_is_heard(models):
    assert models.why_not("hey_jarvis") is None
    assert best(models, pcm("hey_jarvis")) > 0.9  # openWakeWord itself: 0.999


def test_other_words_are_not(models):
    assert best(models, pcm("not_jarvis")) < 0.05
    assert best(models, b"\x00\x00" * 32000) < 0.05  # silence


def test_an_unknown_phrase_says_why(models):
    assert "no wake word model" in models.why_not("hey_computer")
    assert "is missing" in WakeModels(FIXTURES).why_not("hey_jarvis")


def test_strip_wake():
    assert strip_wake("Hey Jarvis, what's next?", "hey Jarvis") == "what's next?"
    assert strip_wake("jarvis open teleop", "hey Jarvis") == "open teleop"
    assert strip_wake("What does Jarvis do?", "hey Jarvis") == "What does Jarvis do?"
    # the audio from just before the detection may hold only the phrase's end
    assert strip_wake("vis, pull up teleop", "hey Jarvis") == "pull up teleop"
    assert strip_wake("Rvis. What's next?", "hey Jarvis") == "What's next?"
    assert strip_wake("visit the lab page", "hey Jarvis") == "visit the lab page"


# ---------- sensitivity: openWakeWord's threshold and patience, per device ----------


def noisy(name: str, gain: float, noise: float, seed: int) -> bytes:
    """A recording made quieter in a noisy room (white noise: harsher than a real room)."""
    x = np.frombuffer(pcm(name), np.int16).astype(float)
    r = np.random.default_rng(seed)
    return np.clip(x * gain + r.normal(0, noise, len(x)), -32768, 32767).astype(np.int16).tobytes()


def fires(models, data: bytes, sensitivity: int) -> bool:
    d = WakeDetector(models, sensitivity=sensitivity)
    heard = False
    for p in pieces(data):
        d.feed(p)
        heard = heard or d.fired
    return heard


def test_sensitivity_levels():
    assert SENSITIVITY[5] == (THRESHOLD, 1)  # the default is openWakeWord's
    thresholds = [SENSITIVITY[i][0] for i in range(1, 10)]
    assert thresholds == sorted(thresholds, reverse=True)  # higher = hears more readily
    assert sensitivity_level("7") == 7 and sensitivity_level(None) == 5
    assert sensitivity_level(0) == 5 and sensitivity_level("loud") == 5


def test_a_noisy_room_needs_a_higher_sensitivity(models):
    quiet_voice_loud_room = noisy("hey_jarvis", 0.1, 2000, 0)  # peaks at ~0.40
    assert not fires(models, quiet_voice_loud_room, 5)
    assert fires(models, quiet_voice_loud_room, 8)
    assert fires(models, pcm("hey_jarvis"), 1)  # a clear "hey Jarvis" even at the lowest


def test_even_the_highest_doesnt_wake_on_other_speech_in_noise(models):
    for noise in (300, 1000, 3000):
        for seed in range(3):
            assert not fires(models, noisy("not_jarvis", 1, noise, seed), 9)


def test_patience_wants_chunks_in_a_row(models):
    d = WakeDetector(models, sensitivity=9)
    assert d.patience == 2
    d.set_sensitivity(3)
    assert (d.threshold, d.patience) == (0.6, 1)


def test_the_turn_timing_line():
    t = TurnTiming("wake word", "quest", warm=True, ended_by="pause")
    for i, step in enumerate(["detected", "picked", "listening", "connected", "ended", "words"]):
        t.mark(step, 100.0 + i * 0.1)
    t.mark("first_text", 103.0)
    t.mark("first_audio", 104.5)
    t.mark("playing", 104.6)
    line = t.line()
    assert line.startswith("voice timing (quest, wake word, warm, ended by the pause): heard the")
    assert "first text +2.50 s" in line and "first word playing +100 ms" in line
    assert line.endswith("waited 4.20 s after the question")
    assert t.summary()["ms"]["playing"] == 4600 and t.summary()["waited_ms"] == 4200


def test_the_venue_decides():
    def venue(**kw):
        return Venue("v", (), True, 0.5, **kw)

    assert venue().wake_word_on and not venue(public=True).wake_word_on
    assert venue(public=True, wake_word=True).wake_word_on
    assert not venue(wake_word=False).wake_word_on


def test_the_lab_venues_and_personas_have_it():
    from lab_os.personas import load_persona
    from lab_os.venues import load_venue

    assert load_venue("lab").wake_word is None  # default: on (not public)
    assert load_persona("jarvis").wake_word == "hey_jarvis"


# ---------- over /ws/voice ----------


async def events_until(ws, kinds, timeout=5.0):
    out = []
    while True:
        msg = await asyncio.wait_for(ws.receive(), timeout)
        assert msg.type == WSMsgType.TEXT, msg
        ev = json.loads(msg.data)
        out.append(ev)
        if ev["type"] in kinds:
            return out


async def stream(ws, data: bytes):
    for p in pieces(data):
        await ws.send_bytes(p)
        await asyncio.sleep(0)


async def test_the_wake_word_starts_a_turn(aiohttp_client, aiohttp_server, key, tmp_path):
    app, conv, assistant = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    st = await (await client.get("/api/status")).json()
    assert st["voice"]["wake"] == {"available": True, "why": None, "phrase": "hey Jarvis"}
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "wake", "on": True})
    on = await events_until(ws, {"wake_on", "wake_off"}, timeout=20)  # loads the models
    assert on[-1] == {"type": "wake_on", "phrase": "hey Jarvis"}
    await stream(ws, pcm("not_jarvis"))  # other words: nothing
    await stream(ws, pcm("hey_jarvis"))
    evs = await events_until(ws, {"listening"})
    assert [e["type"] for e in evs][-2:] == ["wake", "listening"]
    assert assistant.state == "listening"
    await ws.send_bytes(b"\x01\x00" * 16000)  # the question
    await ws.send_json({"type": "end"})
    evs = await events_until(ws, {"audio_end"})
    assert {"type": "heard", "text": HEARD, "final": True} in evs
    assert conv.messages[-2] == {"role": "user", "content": HEARD}
    await ws.close()


async def test_one_screen_answers_at_once_warm_and_timed(
    aiohttp_client,
    aiohttp_server,
    key,
    tmp_path,
):
    """One screen listening: no waiting for others; the hearing was connected ahead of time; each
    step's time is logged and kept for /api/voice/timings."""
    seen: list = []
    app, conv, _ = await voice_app(aiohttp_server, tmp_path, seen=seen)
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice?device=quest")
    await ws.send_json({"type": "wake", "on": True, "sensitivity": 7})
    await events_until(ws, {"wake_on"}, timeout=20)
    await stream(ws, pcm("not_jarvis"))  # meanwhile the brain connects a hearing ahead of time
    for _ in range(50):
        if sum("setup" in s for s in seen) >= 1:
            break
        await asyncio.sleep(0.05)
    assert sum("setup" in s for s in seen) == 1  # the warm one, before anyone said the phrase
    await stream(ws, pcm("hey_jarvis"))
    evs = await events_until(ws, {"listening"})
    assert [e["type"] for e in evs][-2:] == ["wake", "listening"]
    await ws.send_bytes(SECOND)
    await ws.send_json({"type": "end"})
    evs = await events_until(ws, {"audio_end"})
    assert conv.messages[-2] == {"role": "user", "content": HEARD}
    await ws.send_json({"type": "playing", "seq": 0})  # the page plays the first piece
    from lab_os.hub.server import BRAIN

    for _ in range(50):
        if app[BRAIN].voice.timings:
            break
        await asyncio.sleep(0.02)
    timings = (await (await client.get("/api/voice/timings")).json())["timings"]
    t = timings[-1]
    assert (t["how"], t["device"], t["warm"], t["ended_by"]) == ("wake word", "quest", True, "page")
    steps = list(t["ms"])
    assert steps[:2] == ["detected", "picked"] and steps[-1] == "playing"
    assert t["ms"]["picked"] < 100  # no 0.25 s wait for other screens
    assert t["ms"]["connected"] == t["ms"]["listening"]  # warm: nothing to wait for
    await ws.close()


async def test_the_service_hearing_a_pause_ends_the_question(
    aiohttp_client,
    aiohttp_server,
    key,
    tmp_path,
):
    """No "end" from the page: the voice service heard the pause after the question (a noisy room's
    hum can keep the page's own silence watch from ever ending it)."""
    app, conv, _ = await voice_app(aiohttp_server, tmp_path, pause_at=8)
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "wake", "on": True})
    await events_until(ws, {"wake_on"}, timeout=20)
    await stream(ws, pcm("hey_jarvis"))
    await events_until(ws, {"listening"})
    await stream(ws, SECOND)  # the question, then the room keeps humming
    evs = await events_until(ws, {"audio_end"})
    kinds = [e["type"] for e in evs]
    assert "ended" in kinds and kinds.index("ended") < kinds.index("audio_end")
    assert conv.messages[-2] == {"role": "user", "content": HEARD}
    await ws.close()


async def test_the_sensitivity_comes_from_the_page(
    aiohttp_client,
    aiohttp_server,
    key,
    tmp_path,
):
    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    from lab_os.hub.server import BRAIN

    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "wake", "on": True, "sensitivity": 8})
    await events_until(ws, {"wake_on"}, timeout=20)
    (link,) = app[BRAIN].voice.links
    assert (link.detector.threshold, link.detector.patience) == SENSITIVITY[8]
    await ws.send_json({"type": "wake", "on": True, "sensitivity": 2})  # changed in Settings
    await events_until(ws, {"wake_on"})
    assert link.detector.threshold == SENSITIVITY[2][0]
    await ws.close()


async def test_while_the_answer_plays_the_wake_word_stops_it(
    aiohttp_client, aiohttp_server, key, tmp_path
):
    """Quick job 57: "Hey Jarvis" during an answer stops it ("stopped" first, so the page ends
    that turn) and hears the new question at once. Before, it was ignored until the end."""
    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "wake", "on": True})
    await events_until(ws, {"wake_on"}, timeout=20)
    await ws.send_json({"type": "played", "loudness": 0.5})  # its answer plays
    await stream(ws, pcm("hey_jarvis"))
    evs = await events_until(ws, {"listening"})
    assert [e["type"] for e in evs][-3:] == ["stopped", "wake", "listening"]
    await ws.close()


async def test_a_new_question_stops_the_answer_being_thought_of(
    aiohttp_client, aiohttp_server, key, tmp_path
):
    """Quick job 57: the mic pressed (or the wake word) while the AI still writes the answer: that
    answer stops, says nothing more, and the new question is heard. Another screen's too."""
    app, conv, _ = await voice_app(aiohttp_server, tmp_path, ai_delay=0.4)
    client = await aiohttp_client(app)
    a, b = await client.ws_connect("/ws/voice"), await client.ws_connect("/ws/voice")
    await a.send_json({"type": "listen", "mode": "ask"})
    await events_until(a, {"listening"})
    await a.send_bytes(b"\x01\x00" * 16000)
    await a.send_json({"type": "end"})
    await events_until(a, {"state"})  # the AI is thinking
    await b.send_json({"type": "listen", "mode": "ask"})  # another screen's mic
    assert (await events_until(b, {"listening", "error"}))[-1]["type"] == "listening"
    evs = await events_until(a, {"stopped"})
    assert "audio" not in [e["type"] for e in evs]
    with pytest.raises(TimeoutError):  # nothing more from the stopped answer
        await events_until(a, {"audio", "audio_end", "done"}, timeout=1.0)
    assert not conv.busy
    for ws in (a, b):
        await ws.close()


async def test_an_answer_that_says_the_phrase_doesnt_wake_itself(
    aiohttp_client, aiohttp_server, key, tmp_path
):
    """The greeting's hint says "hey Jarvis": the microphones hear it from the speaker."""
    app, _, _ = await voice_app(aiohttp_server, tmp_path, words=("Say hey Jarvis to talk.",))
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "wake", "on": True})
    await events_until(ws, {"wake_on"}, timeout=20)
    await ws.send_json({"type": "listen", "mode": "ask"})
    await events_until(ws, {"listening"})
    await ws.send_bytes(b"\x01\x00" * 16000)
    await ws.send_json({"type": "end"})
    await events_until(ws, {"audio_end"})
    await stream(ws, pcm("hey_jarvis"))  # its own voice, from the speaker
    with pytest.raises(TimeoutError):
        await events_until(ws, {"wake", "stopped"}, timeout=0.6)
    await ws.close()


async def test_two_screens_hear_it_one_answers(aiohttp_client, aiohttp_server, key, tmp_path):
    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    a, b = await client.ws_connect("/ws/voice"), await client.ws_connect("/ws/voice")
    for ws in (a, b):
        await ws.send_json({"type": "wake", "on": True})
        await events_until(ws, {"wake_on"}, timeout=20)
    loud = pcm("hey_jarvis")
    await asyncio.gather(stream(a, loud), stream(b, loud))
    got = await asyncio.gather(
        events_until(a, {"wake", "wake_elsewhere"}), events_until(b, {"wake", "wake_elsewhere"})
    )
    assert sorted(evs[-1]["type"] for evs in got) == ["wake", "wake_elsewhere"]
    for ws in (a, b):
        await ws.close()


async def test_off_on_a_public_venue(aiohttp_client, aiohttp_server, key, tmp_path):
    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    from lab_os.hub.server import BRAIN

    app[BRAIN].voice.venue_wake = lambda: False
    client = await aiohttp_client(app)
    st = await (await client.get("/api/status")).json()
    assert st["voice"]["wake"]["available"] is False and "public" in st["voice"]["wake"]["why"]
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "wake", "on": True})
    evs = await events_until(ws, {"wake_off"})
    assert "off in this venue" in evs[-1]["why"]
    await ws.close()


def test_threshold_is_openwakewords():
    assert THRESHOLD == 0.5


def test_the_pages_have_the_wake_word():
    src = Path(__file__).resolve().parents[1] / "src" / "lab_os"
    design = (src / "hub/web/design.html").read_text()
    assert 'id="f-wake"' in design and "syncWake" in design and "silenceWatch" in design
    assert 'id="f-wake"' in (src / "hub/web/index.html").read_text()
    assert "syncWake" in (src / "hub/web/hub.js").read_text()
    assert '"wake word"' in (src / "hub/web/settings.js").read_text()
    js = (src / "web/voice.js").read_text()
    assert '"wake word": "wake_word"' in js and "export function silenceWatch" in js
    # snappier (2026-11-14): the sensitivity, the Quest's stalled microphone, the brain's "ended"
    assert "wakeSensitivity()" in js and "watchMic" in js and '"ended"' in js
    assert "wake_sensitivity" in (src / "hub/web/settings.js").read_text()
    for page in ("hub/web/design.html", "hub/web/hub.js", "hub/web/xr/ask.js"):
        text = (src / page).read_text()
        assert '"ended"' in text and "WAKE_QUIET_MS" in text and "noiseFloor" in text, page
    assert "voice.chime()" in (src / "hub/web/hub.js").read_text()


async def test_a_screen_that_never_says_it_played_doesnt_block_the_wake_word(
    aiohttp_client, aiohttp_server, key, tmp_path, caplog
):
    """Quick job 42: one screen got a spoken answer and never said it played it (a second window, a
    paused tab). Every screen's wake word waits for it, but only for the audio's length and a short
    margin (it was 120 s). Since quick job 57 it waits for nothing: the wake word stops that
    answer ("stopped" on its page) and hears the new question at once."""
    import time

    from lab_os.hub import voice as hub_voice
    from lab_os.hub.server import BRAIN

    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    quiet = await client.ws_connect("/ws/voice?device=newline")
    await quiet.send_json({"type": "listen", "mode": "ask"})
    await events_until(quiet, {"listening"})
    await quiet.send_bytes(SECOND)
    await quiet.send_json({"type": "end"})
    evs = await events_until(quiet, {"audio_end"})  # the answer came; this page never plays it
    spoken = sum(
        hub_voice.wav_seconds(base64.b64decode(e["data"])) for e in evs if e["type"] == "audio"
    )
    (link,) = [lk for lk in app[BRAIN].voice.links if lk.device == "newline"]
    left = link.playing_until - time.monotonic()
    assert 0 < left <= spoken + hub_voice.PLAYBACK_MARGIN_S + 0.5

    desk = await client.ws_connect("/ws/voice?device=desk")
    await desk.send_json({"type": "wake", "on": True})
    await events_until(desk, {"wake_on"}, timeout=20)
    await stream(desk, pcm("hey_jarvis"))
    assert (await events_until(desk, {"wake"}))[-1]["type"] == "wake"
    assert (await events_until(quiet, {"stopped"}))[-1]["type"] == "stopped"
    assert link.playing_until == 0.0
    for ws in (quiet, desk):
        await ws.close()


def test_the_designed_hub_speaks_a_second_greeting_at_once():
    """Quick job 42 (lab check 9.2): back from the start screen, the startup has been seen, so the
    greeting plays when it arrives instead of after the jump (checked in headless Chrome: 0.15 s
    after the press instead of 6.5 s)."""
    page = (Path(__file__).resolve().parents[1] / "src/lab_os/hub/web/design.html").read_text()
    assert "if (VS.greeting && S.startedBefore) V.playHeld();" in page
    assert "S.startedBefore = true;" in page.split("function toStart(why) {", 1)[1][:200]
