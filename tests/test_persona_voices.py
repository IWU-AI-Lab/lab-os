"""Quick job 100: each persona has its own speaker (J.A.R.V.I.S. male, the Lab Assistant female),
the greeting recordings follow it, and the answers never talk about the language rule."""

from pathlib import Path

from lab_os.ai.chat import ANSWER_IN, ANY_LANGUAGE, SHORT_FIRST, SHORT_LATER, UNSPOKEN
from lab_os.ai.voices import VoiceSetup
from lab_os.hub.voice import VoiceDesk, greeting_file
from lab_os.personas import Persona, current_persona


def setup(service: str) -> VoiceSetup:
    return VoiceSetup(
        name="main", service=service, base_url="http://x", hear="h", speak="s", speaker="fable"
    )


def desk(persona: Persona, service: str = "openai") -> VoiceDesk:
    return VoiceDesk(None, None, lambda: persona, voices=lambda: {"main": setup(service)})


def test_the_personas_speak_with_their_own_voices():
    jarvis, plain = current_persona("jarvis"), current_persona("lab-assistant")
    assert jarvis.speakers == {"openai": "onyx", "gemini": "Charon"}
    assert plain.speakers == {"openai": "nova", "gemini": "Kore"}
    assert desk(jarvis).setup().speaker == "onyx"
    assert desk(plain).setup().speaker == "nova"
    assert desk(jarvis, "gemini").setup().speaker == "Charon"
    assert desk(plain, "gemini").setup().speaker == "Kore"
    # a persona without speakers keeps the setup's own
    bare = Persona(id="p", display_name="P", voice="main")
    assert desk(bare).setup().speaker == "fable"


def test_the_greeting_recording_follows_the_voice():
    folder = Path("/r")
    a = greeting_file(folder, desk(current_persona("jarvis")).setup(), "Good morning.", "jarvis")
    b = greeting_file(folder, setup("openai"), "Good morning.", "jarvis")  # the old fable one
    assert a != b


def test_the_answer_never_talks_about_the_language():
    for rule in (ANY_LANGUAGE, SHORT_FIRST, SHORT_LATER, ANSWER_IN.format(name="English")):
        assert rule.endswith(UNSPOKEN)
    assert "Never say which language" in UNSPOKEN
