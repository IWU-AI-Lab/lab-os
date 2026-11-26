"""Quick job 151: the persona chooser as a 3D round table. The brain lists the personas with their
greeting, and speaks a persona's greeting in its own voice (kept once spoken, so the next preview
needs no service)."""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from test_hub_server import make_app

from lab_os.ai.voices import VoiceSetup
from lab_os.hub import voice as voice_mod
from lab_os.hub.voice import VoiceDesk, greeting_file, preview_text
from lab_os.personas import current_persona

SRC = Path(__file__).resolve().parents[1] / "src" / "lab_os"
MORNING = datetime(2026, 11, 26, 9, 0)


def test_the_preview_says_the_time_of_day_and_the_persona_line():
    jarvis = current_persona("jarvis")
    assert preview_text(jarvis, MORNING) == "Good morning. All local systems are up."


def desk(tmp_path, spent):
    setup = VoiceSetup(name="main", service="openai", base_url="http://x", hear="h", speak="s")
    chat = SimpleNamespace(
        paused=lambda: None,
        spend=SimpleNamespace(write_voice=lambda *a: spent.append(a)),
    )
    return VoiceDesk(
        chat, None, lambda: current_persona("lab-assistant"),
        voices=lambda: {"main": setup}, recordings=lambda: tmp_path,
    )  # fmt: skip


async def test_the_preview_is_spoken_once_then_played_from_its_recording(tmp_path, monkeypatch):
    calls, spent = [], []

    async def speak_any(session, setup, text, resting, prefer=None, used=None):
        calls.append((setup.speaker, text))
        used.append(setup.speak_models[0])
        return b"RIFF-fake-wav"

    monkeypatch.setattr(voice_mod, "speak_any", speak_any)
    monkeypatch.setattr(voice_mod, "wav_seconds", lambda wav: 2.0)
    d = desk(tmp_path, spent)
    jarvis = current_persona("jarvis")
    text, wav = await d.preview(jarvis, MORNING)
    assert (text, wav) == ("Good morning. All local systems are up.", b"RIFF-fake-wav")
    assert calls == [("fable", text)]  # J.A.R.V.I.S.'s own speaker, not the active persona's
    assert len(spent) == 1
    assert greeting_file(tmp_path, d.setup(jarvis), text, "jarvis").is_file()
    assert await d.preview(jarvis, MORNING) == (text, wav)
    assert len(calls) == 1 and len(spent) == 1  # the second time: the recording, no service


async def test_the_brain_lists_the_personas_and_explains_a_missing_voice(aiohttp_client):
    client = await aiohttp_client(make_app())
    out = await (await client.get("/api/personas")).json()
    assert out["active"] == "lab-assistant"
    by_id = {p["id"]: p for p in out["personas"]}
    assert by_id["jarvis"]["display_name"] == "J.A.R.V.I.S."
    assert by_id["jarvis"]["greeting"].endswith("All local systems are up.")
    assert by_id["jarvis"]["picture"]["style"] == "calm-ring"
    resp = await client.get("/api/personas/jarvis/preview")
    assert resp.status == 503  # tests have no API key: a sentence, not a crash
    assert "OPENAI_API_KEY" in (await resp.json())["message"]
    assert (await client.get("/api/personas/nobody/preview")).status == 404


def test_the_table_is_only_on_the_full_and_maximal_looks():
    js = (SRC / "hub/web/settings.js").read_text()
    assert 'look !== "full" && look !== "maximal"' in js
    html = (SRC / "hub/web/settings.html").read_text()
    assert '"three":"/web/vendor/three/three.module.js"' in html  # vendored: works offline
