"""Voice (step 7): setups, the voice service clients, and a whole push-to-talk turn over /ws/voice.
A fake voice service stands in for Gemini (its Live API's transcription and its TTS) and OpenAI's
audio endpoints: no internet, no keys, no microphone."""

import asyncio
import base64
import json
from pathlib import Path

import pytest
from aiohttp import WSMsgType, web
from test_chat import conversation, fake_service, setup_for

from lab_os.ai.assistant import Assistant
from lab_os.ai.speech import (
    GEMINI_LIVE_PATH,
    VoiceError,
    hearing_for,
    speak,
    wav_bytes,
    wav_seconds,
)
from lab_os.ai.voices import NoVoice, VoiceSetup, load_voices, pick_voice
from lab_os.hub.voice import speakable, take_speech
from lab_os.personas import Persona

SRC = Path(__file__).resolve().parents[1] / "src" / "lab_os"
SECOND = b"\x01\x00" * 16_000  # one second of (nearly silent) 16 kHz audio
HEARD = "what is the next step"


# ---------- a fake voice service ----------


def fake_voice(heard=HEARD, live_close=None, tts_status=200, seen=None, limited=(), pause_at=None):
    """Gemini's Live transcription (WebSocket) and TTS (generateContent), OpenAI's audio endpoints.
    The Live fake sends the words so far after each audio frame, and the final words after the
    audio ends, like the real one (checked 2026-11-12). `pause_at`: at that audio frame it hears a
    pause instead (the final words and ACTIVITY_END while the audio still streams)."""
    seen = seen if seen is not None else []
    words = heard.split()

    async def live(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        seen.append({"live_key": request.headers.get("x-goog-api-key")})
        setup = await ws.receive_json()
        seen.append({"setup": setup})
        if live_close:
            await ws.close(code=1008, message=live_close.encode())
            return ws
        await ws.send_json({"setupComplete": {}})
        frames = 0
        async for msg in ws:
            data = json.loads(msg.data)
            ri = data.get("realtimeInput") or {}
            if "audio" in ri:
                frames += 1
                if pause_at and frames == pause_at:
                    await ws.send_json({"serverContent": {"inputTranscription": {"text": heard}}})
                    await ws.send_json({"voiceActivity": {"type": "ACTIVITY_END"}})
                    continue
                if pause_at and frames > pause_at:
                    continue  # quiet after the question
                if frames == 1 and words:
                    await ws.send_json({"voiceActivity": {"type": "ACTIVITY_START"}})
                part = " ".join(words[:frames])
                if words:
                    await ws.send_json(
                        {"serverContent": {"interimInputTranscription": {"text": part}}}
                    )
            if ri.get("audioStreamEnd"):
                if words and not (pause_at and frames >= pause_at):
                    await ws.send_json({"serverContent": {"inputTranscription": {"text": heard}}})
                    await ws.send_json({"voiceActivity": {"type": "ACTIVITY_END"}})
                await ws.send_json({"serverContent": {"generationComplete": True}})
        return ws

    async def tts(request):
        body = await request.json()
        model = request.match_info["model"].split(":")[0]
        seen.append({"tts": body, "key": request.headers.get("x-goog-api-key"), "model": model})
        if model in limited:  # like Gemini's free key after 3 requests in a minute
            details = [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "53s"}]
            return web.json_response({"error": {"code": 429, "details": details}}, status=429)
        if tts_status != 200:
            return web.json_response({"error": {"message": "nope"}}, status=tts_status)
        text = body["contents"][0]["parts"][0]["text"]
        audio = wav_bytes(b"\x00\x00" * 2400 * len(text), 24_000)  # 0.1 s per character
        part = {"inlineData": {"mimeType": "audio/wav", "data": base64.b64encode(audio).decode()}}
        return web.json_response({"candidates": [{"content": {"parts": [part]}}]})

    async def transcriptions(request):
        form = await request.post()
        lang = {"language": form["language"]} if "language" in form else {}
        if "prompt" in form:
            seen.append({"prompt": form["prompt"]})
        seen.append(
            {"transcribe": form["model"], "auth": request.headers.get("Authorization")} | lang
        )
        return web.json_response({"text": heard})

    async def openai_speech(request):
        body = await request.json()
        seen.append({"speech": body})
        return web.Response(body=wav_bytes(b"\x00\x00" * 16_000), content_type="audio/wav")

    app = web.Application()
    app.router.add_get(GEMINI_LIVE_PATH, live)
    app.router.add_post("/v1beta/models/{model}", tts)
    app.router.add_post("/v1/audio/transcriptions", transcriptions)
    app.router.add_post("/v1/audio/speech", openai_speech)
    return app


def gemini_setup(server, **kw) -> VoiceSetup:
    return VoiceSetup(
        name=kw.pop("name", "test"),
        service="gemini",
        base_url=str(server.make_url("/v1beta")),
        hear="test-hear",
        speak="test-speak",
        speaker="Charon",
        key_env="LAB_TEST_KEY",
        where="Test voice",
        **kw,
    )


def openai_setup(server) -> VoiceSetup:
    return VoiceSetup(
        name="oa",
        service="openai",
        base_url=str(server.make_url("/v1")),
        hear="test-transcribe",
        speak="test-tts",
        speaker="onyx",
        key_env="LAB_TEST_KEY",
        style="Lively, British.",
        speed=1.15,
        price_heard=0.006,
        price_spoken=0.06,
    )


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("LAB_TEST_KEY", "test-key")


# ---------- setups ----------


def test_models_yaml_voices():
    voices = load_voices()
    assert "British" in voices["main"].style and voices["main"].speed == 1.15
    assert voices["main"].service == "openai" and voices["main"].fallback == "backup"
    assert voices["backup"].service == "gemini" and voices["backup"].key_env == "GEMINI_API_KEY"
    assert voices["main"].cost(60, 60) == pytest.approx(0.018)


def test_voice_fallback_and_sentences(monkeypatch):
    voices = load_voices()
    with pytest.raises(NoVoice, match="OPENAI_API_KEY or GEMINI_API_KEY"):
        pick_voice("main", voices)
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    assert pick_voice("main", voices).name == "backup"
    with pytest.raises(NoVoice, match="no voice"):
        pick_voice("none", voices)
    with pytest.raises(NoVoice, match="'nope'"):
        pick_voice("nope", voices)


def test_the_personas_have_a_voice():
    from lab_os.personas import load_persona

    voices = load_voices()
    for pid in ("lab-assistant", "jarvis"):
        assert load_persona(pid).voice in voices


# ---------- what is spoken, and when ----------


def test_speakable_drops_markdown_and_links():
    assert (
        speakable("Run `uv sync` **now**: see https://x.y/z.")
        == "Run uv sync now: see the link on the screen"
    )


def test_take_speech_starts_with_the_first_sentence():
    assert take_speech("Hello there", True, False) == ("", "Hello there")
    assert take_speech("Hello. How are", True, False) == ("Hello.", " How are")
    assert take_speech("One. Two. Thr", False, False) == ("One. Two.", " Thr")
    assert take_speech("It's 3.5 cm", True, False) == ("", "It's 3.5 cm")  # not a sentence end
    assert take_speech("Last bit", False, True) == ("Last bit", "")
    assert take_speech("Done. All here.", True, True) == ("Done.", " All here.")  # still split
    assert take_speech("Done.", True, False) == ("", "Done.")  # the answer may go on


# ---------- the service clients ----------


def test_a_streamed_wav_counts_its_real_length():
    from lab_os.ai.speech import _rewrap

    wav = bytearray(wav_bytes(b"\x00\x00" * 24_000, 24_000))  # 1 s
    wav[4:8] = wav[40:44] = b"\xff\xff\xff\xff"  # OpenAI's streamed header: "endless"
    assert wav_seconds(bytes(wav)) == pytest.approx(1.0)
    fixed = _rewrap(bytes(wav))
    assert fixed[40:44] == (48_000).to_bytes(4, "little") and wav_seconds(fixed) == 1.0


async def test_gemini_hears_while_the_audio_streams(aiohttp_server, key):
    seen = []
    server = await aiohttp_server(fake_voice(seen=seen))
    words = []
    async with __import__("aiohttp").ClientSession() as session:
        h = hearing_for(session, gemini_setup(server), words.append)
        await h.start()
        for _ in range(3):
            h.feed(SECOND)
        text = await h.finish()
    assert text == HEARD
    assert words[0] == "what" and words[-1] == HEARD  # the words so far, as they came
    assert h.seconds == pytest.approx(3.0)
    assert {"live_key": "test-key"} in seen  # the key goes in a header, not the address
    assert {"setup": {"setup": {"model": "models/test-hear"}}} in seen


async def test_gemini_nothing_said_is_empty(aiohttp_server, key):
    server = await aiohttp_server(fake_voice(heard=""))
    async with __import__("aiohttp").ClientSession() as session:
        h = hearing_for(session, gemini_setup(server), lambda t: None)
        await h.start()
        h.feed(SECOND)
        assert await h.finish() == ""


async def test_gemini_refusal_is_a_sentence(aiohttp_server, key):
    server = await aiohttp_server(fake_voice(live_close="API key not valid"))
    async with __import__("aiohttp").ClientSession() as session:
        h = hearing_for(session, gemini_setup(server), lambda t: None)
        with pytest.raises(VoiceError, match="refused the API key"):
            await h.start()


async def test_gemini_unreachable(key, unused_tcp_port):
    setup = VoiceSetup(
        "x",
        "gemini",
        f"http://127.0.0.1:{unused_tcp_port}/v1beta",
        "h",
        "s",
        key_env="LAB_TEST_KEY",
    )
    async with __import__("aiohttp").ClientSession() as session:
        with pytest.raises(VoiceError, match="can't reach"):
            await hearing_for(session, setup, lambda t: None).start()
        with pytest.raises(VoiceError, match="can't reach"):
            await speak(session, setup, "Hi.")


async def test_gemini_speaks_a_wav(aiohttp_server, key):
    seen = []
    server = await aiohttp_server(fake_voice(seen=seen))
    async with __import__("aiohttp").ClientSession() as session:
        wav = await speak(session, gemini_setup(server), "Hello.")
    assert wav[:4] == b"RIFF" and wav_seconds(wav) == pytest.approx(0.6)
    tts = next(s for s in seen if "tts" in s)
    voice = tts["tts"]["generationConfig"]["speechConfig"]["voiceConfig"]
    assert voice == {"prebuiltVoiceConfig": {"voiceName": "Charon"}} and tts["key"] == "test-key"


async def test_raw_pcm_from_a_tts_model_is_wrapped():
    from lab_os.ai.speech import _pcm_rate

    assert _pcm_rate("audio/L16;codec=pcm;rate=24000") == 24000
    assert _pcm_rate("audio/wav") is None


async def test_tts_rate_limit_is_a_sentence(aiohttp_server, key):
    server = await aiohttp_server(fake_voice(tts_status=429))
    async with __import__("aiohttp").ClientSession() as session:
        with pytest.raises(VoiceError, match="free key has a limit"):
            await speak(session, gemini_setup(server), "Hello.")


async def test_a_model_over_its_limit_hands_over_to_the_next(aiohttp_server, key):
    import dataclasses
    import time

    from lab_os.ai.speech import speak_any

    seen = []
    server = await aiohttp_server(fake_voice(seen=seen, limited=("tts-a",)))
    setup = dataclasses.replace(gemini_setup(server), speak="tts-a", speak_more=("tts-b",))
    resting = {}
    async with __import__("aiohttp").ClientSession() as session:
        wav = await speak_any(session, setup, "Hi.", resting)
        assert wav[:4] == b"RIFF"
        assert [s["model"] for s in seen if "tts" in s] == ["tts-a", "tts-b"]
        assert 50 < resting["tts-a"] - time.monotonic() <= 53  # its retry time
        await speak_any(session, setup, "Again.", resting)  # tts-a rests: not asked again
        assert [s["model"] for s in seen if "tts" in s] == ["tts-a", "tts-b", "tts-b"]
        busy = await aiohttp_server(fake_voice(tts_status=503))
        stuck = dataclasses.replace(gemini_setup(busy), speak="x", speak_more=("y",))
        with pytest.raises(VoiceError, match="busy"):
            await speak_any(session, stuck, "Busy.", {})
        assert [s for s in resting] == ["tts-a"]  # a busy model doesn't rest
        resting["tts-b"] = time.monotonic() + 60
        with pytest.raises(VoiceError, match="free key has a limit"):
            await speak_any(session, setup, "All resting.", resting)


def test_speak_can_list_models():
    assert load_voices()["backup"].speak_models[:2] == (
        "gemini-3.8-flash-lite-tts",
        "gemini-3.8-flash-tts",
    )
    assert load_voices()["main"].speak_models == ("gpt-4o-mini-tts",)


async def test_openai_hears_the_recording_and_speaks(aiohttp_server, key):
    seen = []
    server = await aiohttp_server(fake_voice(seen=seen))
    setup = openai_setup(server)
    words = []
    async with __import__("aiohttp").ClientSession() as session:
        h = hearing_for(session, setup, words.append)
        await h.start()
        h.feed(SECOND)
        assert await h.finish() == HEARD and words == [HEARD]
        wav = await speak(session, setup, "Hello.")
    assert wav_seconds(wav) == pytest.approx(1.0)
    assert {"transcribe": "test-transcribe", "auth": "Bearer test-key"} in seen
    speech = next(s for s in seen if "speech" in s)["speech"]
    assert speech == {
        "model": "test-tts",
        "input": "Hello.",
        "response_format": "wav",
        "voice": "onyx",
        "instructions": "Lively, British.",
        "speed": 1.15,
    }


# ---------- a whole turn over /ws/voice ----------


async def voice_app(
    aiohttp_server, tmp_path, words=("It is. ", "Step seven", ": voice."), ai_delay=0.0, **kw
):
    from lab_os.hub.server import create_brain_app
    from lab_os.robots.fake import FakeArm
    from lab_os.teleop.loop import InputState, TeleopLoop
    from lab_os.venues import Venue

    ai = await aiohttp_server(fake_service(words=words, delay=ai_delay))
    voice = await aiohttp_server(fake_voice(**kw))
    assistant = Assistant()
    conv = conversation(setup_for(ai), tmp_path, assistant=assistant)
    setup = gemini_setup(voice)
    arm = FakeArm()
    arm.connect()
    app = create_brain_app(
        TeleopLoop(arm=arm, inputs=InputState()),
        Venue("v", ("fake-arm",), True, 0.5),
        chat=conv,
        persona=lambda: Persona(id="p", display_name="P", voice="test", wake_word="hey_jarvis"),
        voices=lambda: {"test": setup},
    )
    return app, conv, assistant


async def until(ws, kind, events, timeout=5.0):
    while True:
        msg = await asyncio.wait_for(ws.receive(), timeout)
        assert msg.type == WSMsgType.TEXT, msg
        ev = json.loads(msg.data)
        events.append(ev)
        if ev["type"] == kind:
            return ev


async def test_push_to_talk_turn(aiohttp_client, aiohttp_server, key, tmp_path):
    app, conv, assistant = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    st = await (await client.get("/api/status")).json()
    assert st["voice"] | {"wake": None} == {
        "wake": None,
        "available": True,
        "why": None,
        "setup": "test",
        "where": "Test voice",
        "service": "gemini",
    }
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "listen", "mode": "ask"})
    events = []
    await until(ws, "listening", events)
    assert assistant.state == "listening"
    assert (await (await client.get("/api/status")).json())["in_use"] == ["voice"]
    for _ in range(2):
        await ws.send_bytes(SECOND)
    await ws.send_json({"type": "end"})
    heard = await until(ws, "audio_end", events)
    kinds = [e["type"] for e in events]
    assert {"type": "heard", "text": HEARD, "final": True} in events
    assert kinds.index("heard") < kinds.index("text") < kinds.index("done")
    audio = [e for e in events if e["type"] == "audio"]
    # the first sentence is spoken alone (so it starts soon), the rest after it
    assert [a["text"] for a in audio] == ["It is.", "Step seven: voice."]
    assert heard["count"] == 2
    assert base64.b64decode(audio[0]["data"])[:4] == b"RIFF"
    assert conv.messages[-2] == {"role": "user", "content": HEARD}  # the same conversation
    # the page plays it: speaking with its loudness, then idle and nothing in use
    await ws.send_json({"type": "played", "loudness": 0.7})
    for _ in range(50):
        if assistant.loudness == 0.7:
            break
        await asyncio.sleep(0.02)
    assert assistant.state == "speaking" and assistant.loudness == 0.7
    assert (await (await client.get("/api/status")).json())["in_use"] == ["voice"]
    await ws.send_json({"type": "played", "done": True})
    for _ in range(50):
        st = await (await client.get("/api/status")).json()
        if not st["in_use"]:
            break
        await asyncio.sleep(0.02)
    assert st["in_use"] == [] and assistant.state != "speaking"
    spend = conv.spend.entries()
    assert [e.get("what") for e in spend if e["kind"] == "voice"] == ["heard", "spoken"]
    assert next(e for e in spend if e.get("what") == "heard")["heard_s"] == 2.0
    assert conv.spend.month()["chats"] == 1
    await ws.close()


async def test_a_drafted_prompt_is_not_read_out(aiohttp_client, aiohttp_server, key, tmp_path):
    words = ("Here you go.\n", "Prompt:\n", "Read CLAUDE.md first. Then build the thing.")
    app, conv, _ = await voice_app(aiohttp_server, tmp_path, words=words)
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "listen", "mode": "ask"})
    await ws.send_bytes(SECOND)
    await ws.send_json({"type": "end"})
    events = []
    await until(ws, "audio_end", events)
    said = " ".join(e["text"] for e in events if e["type"] == "audio")
    assert said == "Here you go. The prompt is on the screen."
    assert "CLAUDE.md" in conv.messages[-1]["content"]  # still on the screen
    await ws.close()


async def test_dictation_only_hears(aiohttp_client, aiohttp_server, key, tmp_path):
    app, conv, assistant = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "listen", "mode": "dictate"})
    events = []
    await until(ws, "listening", events)
    for _ in range(3):
        await ws.send_bytes(SECOND)
    await ws.send_json({"type": "end"})
    final = None
    while not final:
        ev = await until(ws, "heard", events)
        final = ev if ev["final"] else None
    assert final["text"] == HEARD
    assert [e["text"] for e in events if e["type"] == "heard" and not e["final"]][:2] == [
        "what",
        "what is",
    ]
    assert conv.messages == []  # nothing asked: the words go into the ask line
    await asyncio.sleep(0.05)
    assert assistant.state != "listening"
    await ws.close()


async def test_nothing_heard_asks_nothing(aiohttp_client, aiohttp_server, key, tmp_path):
    app, conv, _ = await voice_app(aiohttp_server, tmp_path, heard="")
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "listen", "mode": "ask"})
    await ws.send_bytes(SECOND)
    await ws.send_json({"type": "end"})
    ev = await until(ws, "heard", [])
    assert ev == {"type": "heard", "text": "", "final": True}
    assert conv.messages == []
    await ws.close()


async def test_a_tts_failure_keeps_the_text(aiohttp_client, aiohttp_server, key, tmp_path):
    app, conv, _ = await voice_app(aiohttp_server, tmp_path, tts_status=429)
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "listen", "mode": "ask"})
    await ws.send_bytes(SECOND)
    await ws.send_json({"type": "end"})
    events = []
    end = await until(ws, "audio_end", events)
    assert end["count"] == 0
    assert [e["type"] for e in events].count("voice_error") == 1
    assert any(e["type"] == "done" for e in events)
    assert conv.messages[-1]["content"] == "It is. Step seven: voice."
    await ws.close()


async def test_no_voice_says_why(aiohttp_client, aiohttp_server, tmp_path):
    app, _, _ = await voice_app(aiohttp_server, tmp_path)  # no key in the environment
    client = await aiohttp_client(app)
    st = await (await client.get("/api/status")).json()
    assert st["voice"]["available"] is False and "LAB_TEST_KEY" in st["voice"]["why"]
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "listen", "mode": "ask"})
    ev = await until(ws, "error", [])
    assert "LAB_TEST_KEY" in ev["message"]
    await ws.close()


async def test_the_budget_pauses_voice_too(aiohttp_client, aiohttp_server, key, tmp_path):
    app, conv, _ = await voice_app(aiohttp_server, tmp_path)
    conv.spend.budget_usd = 0.0
    client = await aiohttp_client(app)
    st = await (await client.get("/api/status")).json()
    assert st["voice"]["available"] is False and "budget" in st["voice"]["why"]


async def test_the_spoken_greeting(aiohttp_client, aiohttp_server, key, tmp_path):
    seen = []
    app, conv, _ = await voice_app(aiohttp_server, tmp_path, seen=seen)
    conv.clear(opening="Good evening. All local systems are up.")
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "greet", "way": "push_to_talk"})
    events = []
    end = await until(ws, "audio_end", events)
    assert end["greeting"] is True
    said = " ".join(e["text"] for e in events if e["type"] == "audio")
    assert said == "Good evening. You can talk to me: hold the mic."  # not the persona's line
    await ws.send_json({"type": "greet", "way": "push_to_talk"})  # not again right away
    await asyncio.sleep(0.2)
    assert sum(1 for s in seen if "tts" in s) == 1  # one request: the free key's limits
    await ws.close()


async def test_the_second_start_plays_the_recording(aiohttp_client, aiohttp_server, key, tmp_path):
    """Quick job 4: each greeting is spoken once per voice, saved, then played from the file."""
    from lab_os import config

    seen = []
    app, conv, _ = await voice_app(aiohttp_server, tmp_path, seen=seen)
    client = await aiohttp_client(app)

    async def start(opening, way="push_to_talk"):
        conv.clear(opening=opening)
        ws = await client.ws_connect("/ws/voice")  # a new start: a new page connection
        await ws.send_json({"type": "greet", "way": way})
        events = []
        end = await until(ws, "audio_end", events)
        await ws.close()
        audio = [e for e in events if e["type"] == "audio"]
        assert end["count"] == len(audio) == 1
        return audio[0]

    first = await start("Good evening. Step 8, Devices, was finished today.")
    second = await start("Good evening. 25 commits today.")  # other news: the same recording
    assert first["text"] == second["text"] == "Good evening. You can talk to me: hold the mic."
    assert first["data"] == second["data"]
    assert sum(1 for s in seen if "tts" in s) == 1  # the second start made no request
    saved = list((config.recordings_dir() / "greetings").glob("*.wav"))
    assert len(saved) == 1 and saved[0].name.startswith("test-")
    spoken_s = sum(e.get("spoken_s", 0) for e in conv.spend.entries())
    assert spoken_s > 0  # the first one counted; the recording costs nothing

    await start("Good morning. All local systems are up.")  # another time of day: a new file
    await start("Good evening.", way="wake_word")  # another hint: a new file
    assert sum(1 for s in seen if "tts" in s) == 3
    assert len(list((config.recordings_dir() / "greetings").glob("*.wav"))) == 3


def test_a_new_voice_or_line_makes_a_new_recording(tmp_path):
    from lab_os.hub.voice import greeting_file, spoken_greeting

    setup = VoiceSetup("main", "openai", "http://x/v1", "h", "tts-1", speaker="fable")
    text = spoken_greeting("Good evening. News.", "You can talk to me: hold the mic.")
    assert text == "Good evening. You can talk to me: hold the mic."
    path = greeting_file(tmp_path, setup, text)
    assert path == greeting_file(tmp_path, setup, text)
    assert path != greeting_file(
        tmp_path, VoiceSetup("main", "openai", "http://x/v1", "h", "tts-1", speaker="onyx"), text
    )
    assert path != greeting_file(tmp_path, setup, text.replace("hold", "tap"))
    assert spoken_greeting("", "Hi.").split()[0] == "Good"  # no opening: the time of day now


async def test_a_saved_greeting_plays_while_voice_is_paused(
    aiohttp_client, aiohttp_server, key, tmp_path
):
    seen = []
    app, conv, _ = await voice_app(aiohttp_server, tmp_path, seen=seen)
    conv.clear(opening="Good evening.")
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "greet", "way": "push_to_talk"})
    await until(ws, "audio_end", [])
    await ws.close()
    conv.spend.budget_usd = 0.0  # voice paused (the budget): the recording still plays
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "greet", "way": "push_to_talk"})
    end = await until(ws, "audio_end", [])
    assert end["count"] == 1 and sum(1 for s in seen if "tts" in s) == 1
    await ws.close()


def test_the_pages_have_the_voice_parts():
    js = (SRC / "web" / "voice.js").read_text()
    assert "/ws/voice" in js and "isSecureContext" in js and "enumerateDevices" in js
    assert (SRC / "web" / "voice-worklet.js").is_file()
    for page in ("hub/web/design.html", "hub/web/index.html"):
        assert 'id="mic"' in (SRC / page).read_text(), page


async def test_the_greeting_without_a_microphone_has_no_hint(
    aiohttp_client, aiohttp_server, key, tmp_path
):
    app, conv, _ = await voice_app(aiohttp_server, tmp_path)
    conv.clear(opening="Good morning. Step 7, Voice, was finished today.")
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "greet", "way": "none"})
    events = []
    await until(ws, "audio_end", events)
    said = [e["text"] for e in events if e["type"] == "audio"]
    assert said == ["Good morning."]  # no hint, and the news stays on the screen
    await ws.close()


def test_the_hubs_speak_the_greeting():
    design = (SRC / "hub/web/design.html").read_text()
    assert "spokenGreeting" in design and "V.playHeld()" in design
    assert "S.sound" in design.split("function spokenGreeting")[1][:200]  # this screen's sound
    assert "voice.playHeld()" in (SRC / "hub/web/hub.js").read_text()


async def test_the_greeting_hint_follows_the_way_in(aiohttp_client, aiohttp_server, key, tmp_path):
    app, conv, _ = await voice_app(aiohttp_server, tmp_path)
    conv.clear(opening="Good evening.")
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "greet", "way": "dictation"})
    events = []
    await until(ws, "audio_end", events)
    said = " ".join(e["text"] for e in events if e["type"] == "audio")
    assert said == "Good evening. You can talk to me: tap the mic."
    await ws.close()


def test_the_way_in_is_a_screen_setting():
    js = (SRC / "web" / "voice.js").read_text()
    assert '"push-to-talk": "push_to_talk", dictation: "dictation"' in js
    assert "export function wayIn" in js and "export async function screenCanHear" in js
    settings = (SRC / "hub/web/settings.js").read_text()
    assert 'choices: ["push-to-talk", "dictation"]' in settings and "screenCanHear" in settings
    for page in ("hub/web/design.html", "hub/web/hub.js"):
        text = (SRC / page).read_text()
        assert "dictateStart" in text and 'press("dictate")' in text, page


# ---------- the assistant's languages per device (quick job 33) ----------


async def test_openai_hearing_is_told_the_language(aiohttp_server, key):
    seen = []
    server = await aiohttp_server(fake_voice(seen=seen))
    async with __import__("aiohttp").ClientSession() as session:
        h = hearing_for(session, openai_setup(server), lambda t: None, "en")
        await h.start()
        h.feed(SECOND)
        await h.finish()
    assert {"transcribe": "test-transcribe", "auth": "Bearer test-key", "language": "en"} in seen


async def test_the_device_languages_reach_the_turn(aiohttp_client, aiohttp_server, key, tmp_path):
    app, conv, _ = await voice_app(aiohttp_server, tmp_path)
    asked, real = [], conv.ask

    def ask(text, pages=None, answer_in=None, local=False, device=""):
        asked.append(answer_in)
        return real(text, pages, answer_in, local=local, device=device)

    conv.ask = ask
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    lang = {"hear": "en", "answer": "en"}
    await ws.send_json({"type": "listen", "mode": "ask", "lang": lang})
    events = []
    await until(ws, "listening", events)
    await ws.send_bytes(SECOND)
    await ws.send_json({"type": "end"})
    await until(ws, "done", events)
    await ws.close()
    for answer in ("en", "xx", None):  # typed: only languages the brain knows
        await (
            await client.post("/api/chat", json={"text": "hi", "lang": {"answer": answer}})
        ).read()
    assert asked == ["en", "en", None, None]
    assert "Always answer in English" in conv.system_prompt(None, "en")
    assert "Always answer in" not in conv.system_prompt(None, None)


def test_the_mic_button_comes_back_when_the_microphone_is_plugged_in_again():
    """Quick job 73 (was 48): one count at the browser's "devicechange" can come before the sound
    system lists the microphone, so the page counts again a few times after each change, and every
    few seconds while it sees none."""
    from pathlib import Path

    js = (Path(__file__).resolve().parents[1] / "src/lab_os/web/voice.js").read_text()
    assert 'addEventListener?.("devicechange", micsChanged)' in js
    changed = js.split("function micsChanged() {", 1)[1].split("\n  }", 1)[0]
    assert "setTimeout(countMics" in changed
    assert "if (!st.mics) countMics();" in js


async def test_only_the_screen_that_talks_shows_it(aiohttp_client, aiohttp_server, key, tmp_path):
    """Quick job 58: the Newline spoke, and the desk's core showed it too. The brain's state now
    names the screen with the conversation; the pages show another screen's turn as idle."""
    app, _, assistant = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice?device=newline")
    await ws.send_json({"type": "listen", "mode": "ask"})
    await until(ws, "listening", [])
    st = (await (await client.get("/api/status")).json())["assistant"]
    assert st["state"] == "listening" and st["device"] == "newline"
    await ws.send_bytes(SECOND)
    await ws.send_json({"type": "end"})
    await until(ws, "audio_end", [])
    await ws.send_json({"type": "played", "loudness": 0.4})
    for _ in range(50):
        if assistant.loudness == 0.4:
            break
        await asyncio.sleep(0.02)
    assert (assistant.state, assistant.device) == ("speaking", "newline")
    await ws.send_json({"type": "played", "done": True})
    for _ in range(50):
        if assistant.state != "speaking":
            break
        await asyncio.sleep(0.02)
    assert assistant.device == ""  # idle belongs to every screen
    # a typed question names its screen too
    resp = await client.post("/api/chat", json={"text": "hi", "device": "Desk"})
    assert resp.status == 200
    seen = []
    old = assistant.set

    def spy(state, loudness=0.0, device=None):
        old(state, loudness, device)
        seen.append((state, assistant.device))

    assistant.set = spy
    await (await client.post("/api/chat", json={"text": "hi", "device": "desk"})).read()
    assert ("thinking", "desk") in seen
    await ws.close()


def test_the_pages_show_only_their_own_turn():
    from test_hub_server import SRC

    design = (SRC / "hub" / "web" / "design.html").read_text()
    assert "function shownState(a)" in design and "device: myName()" in design
    hub = (SRC / "hub" / "web" / "hub.js").read_text()
    assert "st.assistant.device" in hub and "device: deviceName()" in hub
    assert "a.device" in (SRC / "hub" / "web" / "xr-hub.js").read_text()


async def test_expects_english_is_said_twice_to_openai(aiohttp_server, key):
    """Quick job 46: "test" came back in Cyrillic a few times. The language code and a prompt in
    English both go to the transcriber."""
    seen = []
    server = await aiohttp_server(fake_voice(seen=seen))
    async with __import__("aiohttp").ClientSession() as session:
        h = hearing_for(session, openai_setup(server), lambda t: None, "en")
        await h.start()
        h.feed(SECOND)
        await h.finish()
    assert any("English" in e.get("prompt", "") for e in seen)


async def test_the_answer_language_goes_with_the_question(
    aiohttp_client, aiohttp_server, key, tmp_path, caplog
):
    """Quick job 46: with Answers: English, a typed Spanish question got a Spanish answer. The
    rule now goes with the question as sent (not into the kept conversation), and each question
    logs its language settings and transcriber."""
    import logging

    app, conv, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    sent = []
    import lab_os.ai.chat as chat_mod

    real = chat_mod.stream_chat

    def spy(session, setup, messages, reply, tools):
        sent.append([dict(m) for m in messages])
        return real(session, setup, messages, reply, tools)

    chat_mod.stream_chat = spy
    try:
        await (
            await client.post("/api/chat", json={"text": "¿Hola?", "lang": {"answer": "en"}})
        ).read()
        assert sent[-1][-1]["content"].startswith("¿Hola?") and "English" in sent[-1][-1]["content"]
        assert conv.messages[-2] == {"role": "user", "content": "¿Hola?"}  # kept as asked
        await (await client.post("/api/chat", json={"text": "Hi", "lang": {}})).read()
        assert sent[-1][-1]["content"] == "Hi"
    finally:
        chat_mod.stream_chat = real
    ws = await client.ws_connect("/ws/voice?device=desk")
    with caplog.at_level(logging.INFO, logger="lab_os.hub.voice"):
        await ws.send_json({"type": "listen", "mode": "ask", "lang": {"hear": "en"}})
        await until(ws, "listening", [])
        await ws.send_bytes(SECOND)
        await ws.send_json({"type": "end"})
        await until(ws, "audio_end", [])
    assert "question on desk: expects English, answers any language, heard by" in caplog.text
    await ws.close()


def test_expects_is_named_for_what_it_does():
    from test_hub_server import SRC

    js = (SRC / "hub" / "web" / "settings.js").read_text()
    assert '["hear_in", "Expects"]' in js and "It still hears other languages" in js
