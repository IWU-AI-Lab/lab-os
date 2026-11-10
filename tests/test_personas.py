"""Personas (step 4): the loader, the place's pick (not the venue's), the greeting's news line,
how the hub uses them."""

import logging
from datetime import date, datetime
from pathlib import Path

import pytest

from lab_os import config
from lab_os.ai.assistant import Assistant
from lab_os.ai.chat import Conversation
from lab_os.ai.models import Setup
from lab_os.ai.spend import SpendLog
from lab_os.hub.greeting import (
    calendar_news,
    commit_news,
    greeting,
    step_news,
    time_of_day,
)
from lab_os.personas import DEFAULT_PERSONA, Persona, current_persona, load_persona
from lab_os.venues import load_venue

FOCUS = """# Current Focus: test
## Steps
1. **Plain hub** (done 2026-11-01). Text.
2. **Robot tools** (done 2026-11-08). Text.
3. **Typed chat** (done 2026-11-09). Text.
4. **Personas.** Text.
## Next section
"""


@pytest.fixture
def home(tmp_path):
    folder = config.new_place(tmp_path / "home")
    config.use(folder)
    return folder


# ---------- the loader ----------


def test_the_two_personas():
    plain = load_persona()
    assert plain.id == DEFAULT_PERSONA == "lab-assistant"
    assert plain.display_name == "Lab Assistant"
    assert plain.model == "main"
    assert "plain, friendly and brief" in plain.personality
    assert plain.lines["greeting"]
    assert plain.picture["type"] == "orb"
    jarvis = load_persona("jarvis")
    assert jarvis.display_name == "J.A.R.V.I.S."
    assert jarvis.lines["greeting"] == "All local systems are up."
    assert "dry, understated wit" in jarvis.personality
    assert "personality" not in jarvis.public()  # the pages never get the AI's instructions


def test_unknown_fields_are_kept_with_a_warning(tmp_path, caplog):
    path = tmp_path / "robo.yaml"
    path.write_text(
        "version: 1\nid: robo\ndisplay_name: Robo\nmood: sunny\nlines: {greeting: Hi}\n"
        "personality: missing.md\n"
    )
    with caplog.at_level(logging.WARNING):
        p = load_persona("robo", path)
    assert p.extra == {"mood": "sunny"} and p.lines == {"greeting": "Hi"}
    assert p.personality == ""  # missing file: warned, not a crash
    assert "unknown field 'mood'" in caplog.text and "missing.md" in caplog.text


def test_a_bare_file_gets_defaults(tmp_path):
    path = tmp_path / "bare.yaml"
    path.write_text("version: 1\n")
    p = load_persona("bare", path)
    assert (p.id, p.display_name, p.model, p.voice) == ("bare", "bare", "main", "none")


def test_unknown_persona_says_which_exist():
    with pytest.raises(config.ConfigError, match="jarvis, lab-assistant"):
        load_persona("nobody")


def test_who_picks_the_persona(monkeypatch):
    """--persona, else $LAB_OS_PERSONA, else the venue's (`default`: the place's), else the
    place's."""
    assert current_persona(venue="lab").id == "lab-assistant"  # lab.yaml: default → place.yaml
    assert (
        current_persona(venue="visit-day").id == "lab-assistant"
    )  # same, until someone changes it
    monkeypatch.setenv("LAB_OS_PERSONA", "jarvis")
    assert current_persona(venue="lab").id == "jarvis"
    assert current_persona("lab-assistant", "lab").id == "lab-assistant"  # --persona wins


def test_a_venue_can_have_its_own_persona(home):
    venue = home / "venues" / "home.yaml"
    assert "persona: default" in venue.read_text()  # the starter: the place's persona
    assert load_venue("home").persona is None
    venue.write_text(venue.read_text().replace("persona: default", "persona: jarvis"))
    assert current_persona(venue="home").id == "jarvis"  # re-read: an edit + reload
    assert current_persona().id == "lab-assistant"  # without a venue: the place's


def test_a_place_can_have_its_own_persona_and_a_bad_pick_falls_back(home, caplog):
    (home / "personas").mkdir()
    (home / "personas" / "butler.yaml").write_text("id: butler\ndisplay_name: Jeeves\n")
    place = home / "place.yaml"
    place.write_text(place.read_text().replace("persona: lab-assistant", "persona: butler"))
    assert current_persona().display_name == "Jeeves"
    assert load_persona("jarvis").id == "jarvis"  # the repo's personas are still there
    place.write_text(place.read_text().replace("butler", "nobody"))
    with caplog.at_level(logging.WARNING):
        assert current_persona().id == "lab-assistant"  # the hub keeps working
    assert "no persona 'nobody'" in caplog.text


# ---------- the greeting ----------


@pytest.mark.parametrize(
    "hour, words",
    [(4, "evening"), (5, "morning"), (11, "morning"), (12, "afternoon"), (18, "evening")],
)
def test_time_of_day(hour, words):
    assert words in time_of_day(datetime(2026, 11, 9, hour))


def test_step_news():
    assert step_news(FOCUS, date(2026, 11, 9)) == "Step 3, Typed chat, was finished today."
    assert step_news(FOCUS, date(2026, 11, 10)) == "Step 3, Typed chat, was finished yesterday."
    assert step_news(FOCUS, date(2026, 11, 11)) is None  # two days ago is old news


def test_calendar_news():
    cal = [{"date": "2026-12-15", "what": "The semester ends"}, {"date": "bad"}]
    assert calendar_news(cal, date(2026, 12, 1)) == "The semester ends in 14 days."
    assert calendar_news(cal, date(2026, 12, 14)) == "The semester ends tomorrow."
    assert calendar_news(cal, date(2026, 12, 15)) == "The semester ends today."
    assert calendar_news(cal, date(2026, 11, 30)) is None  # more than two weeks away
    assert calendar_news(cal, date(2026, 12, 16)) is None  # past


def test_commit_news():
    day = [{"date": "2026-11-08", "count": 12}, {"date": "2026-11-09", "count": 3}]
    assert commit_news(day, date(2026, 11, 9)) == "Yesterday was a busy day: 12 commits."
    busy_today = [{"date": "2026-11-08", "count": 0}, {"date": "2026-11-09", "count": 10}]
    assert commit_news(busy_today, date(2026, 11, 9)) == "A busy day so far: 10 commits today."
    assert commit_news([{"date": "2026-11-08", "count": 9}], date(2026, 11, 9)) is None


def test_greeting_news_first_then_the_persona_line(tmp_path):
    focus = tmp_path / "focus.md"
    focus.write_text(FOCUS)
    no_repo = tmp_path / "not-a-repo"
    g = greeting("All local systems are up.", focus, no_repo, now=datetime(2026, 11, 9, 20))
    assert g == {
        "hello": "Good evening.",
        "news": "Step 3, Typed chat, was finished today.",
        "source": "step",
        "text": "Good evening. Step 3, Typed chat, was finished today.",
    }
    cal = [{"date": "2026-11-20", "what": "Demo day"}]
    g = greeting("Plain.", focus, no_repo, cal, now=datetime(2026, 11, 12, 9))
    assert g["text"] == "Good morning. Demo day in 8 days." and g["source"] == "calendar"
    g = greeting("All local systems are up.", focus, no_repo, now=datetime(2026, 11, 20, 14))
    assert g["text"] == "Good afternoon. All local systems are up." and g["news"] is None


# ---------- the chat and the hub ----------


def test_the_chat_uses_the_persona(tmp_path):
    persona = Persona(id="x", display_name="Robo", personality="Speak like a robot.", model="other")
    setups = {"other": Setup("other", "http://127.0.0.1:1/v1", "m")}
    conv = Conversation(
        Assistant(),
        SpendLog(tmp_path),
        place_name="Lab",
        setups=lambda: setups,
        persona=lambda: persona,
    )
    assert conv.setup().name == "other"  # the persona's model picks the setup
    prompt = conv.system_prompt()
    assert prompt.startswith("Speak like a robot.") and "Your name on the screen is Robo." in prompt


async def test_status_greeting_and_switching_without_restart(aiohttp_client, home):
    from lab_os.hub.server import create_brain_app
    from lab_os.robots.fake import FakeArm
    from lab_os.teleop.loop import InputState, TeleopLoop
    from lab_os.venues import load_venue

    arm = FakeArm()
    arm.connect()
    focus = home / "focus.md"
    focus.write_text(FOCUS)
    app = create_brain_app(
        TeleopLoop(arm=arm, inputs=InputState()), load_venue(), focus_file=focus, repo=home
    )
    client = await aiohttp_client(app)
    st = await (await client.get("/api/status")).json()
    assert st["persona"]["display_name"] == "Lab Assistant"

    place = home / "place.yaml"
    place.write_text(place.read_text().replace("persona: lab-assistant", "persona: jarvis"))  # edit
    st = await (await client.get("/api/status")).json()  # ...and a reload: no restart
    assert st["persona"]["id"] == "jarvis"

    g = await (await client.get("/api/greeting")).json()
    assert g["hello"].startswith("Good ") and g["text"].startswith(g["hello"])
    started = await (await client.post("/api/chat/start")).json()
    chat = await (await client.get("/api/chat")).json()
    assert chat["messages"] == [{"role": "assistant", "content": started["text"]}]


def test_the_page_shows_the_persona_and_the_greeting():
    web = Path(__file__).resolve().parents[1] / "src" / "lab_os" / "hub" / "web"
    html = (web / "index.html").read_text()
    assert 'id="f-persona"' in html and 'id="boot-greet"' in html
    js = (web / "hub.js").read_text()
    assert "/api/chat/start" in js and "st.persona.display_name" in js
