"""The wake word (step 7): openWakeWord's models on the brain, and a hands-free turn over /ws/voice.
The recordings in fixtures/ were made with Gemini's TTS (2026-11-12): "Hey Jarvis!" and "Hey, can
you show me the arm? Thanks, Jordan." No microphone, no internet (a fake voice service)."""

import asyncio
import json
import wave
from pathlib import Path

import pytest
from aiohttp import WSMsgType
from test_voice import HEARD, key, until, voice_app  # noqa: F401 (key is a fixture)

from lab_os.ai.wake import THRESHOLD, WakeDetector, WakeModels
from lab_os.hub.voice import strip_wake
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


async def test_the_wake_word_starts_a_turn(aiohttp_client, aiohttp_server, key, tmp_path):  # noqa: F811
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


async def test_not_while_the_answer_plays(aiohttp_client, aiohttp_server, key, tmp_path):  # noqa: F811
    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "wake", "on": True})
    await events_until(ws, {"wake_on"}, timeout=20)
    await ws.send_json({"type": "played", "loudness": 0.5})  # its own voice in the room
    await stream(ws, pcm("hey_jarvis"))
    with pytest.raises(TimeoutError):
        await events_until(ws, {"wake"}, timeout=0.6)
    await ws.close()


async def test_two_screens_hear_it_one_answers(aiohttp_client, aiohttp_server, key, tmp_path):  # noqa: F811
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


async def test_off_on_a_public_venue(aiohttp_client, aiohttp_server, key, tmp_path):  # noqa: F811
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
