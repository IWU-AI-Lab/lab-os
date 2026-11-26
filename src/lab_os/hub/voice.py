"""Voice on the hub (focus step 7): the page records and plays, the brain hears, thinks and speaks.

One WebSocket per page, `/ws/voice` (docs/dev/protocol.md → "Voice"). While the person holds the
mic, the page sends 16 kHz PCM; the brain passes it to the voice service (lab_os.ai.speech), which
hears the words. On release, the words go to the same conversation as typing (persona, read tools,
history, spend cap: lab_os.ai.chat), and the answer comes back as text **and** speech: the first
sentence is spoken as soon as it's written, the rest while that one plays. API keys never leave the
brain.

The assistant's state follows: `listening` while the mic is held, then the chat's `thinking`, and
`speaking` (with the loudness the page reports) until the page has played the last word.

The spoken greeting (decision 2026-11-13): only the time of day and the hint how to talk, never
the news line (that stays on the screen). Each voice says each one once; the WAV is kept in the
place's `recordings/greetings/` and played from there at every later start, with no voice request.
A new voice or a changed line has a new file name (a hash of both), so it's made again.

The wake word: a page that chose it streams its microphone while the hub is awake; the brain listens
for the phrase itself (lab_os.ai.wake, nothing leaves the computer) and only then starts hearing,
like a push-to-talk press. If several screens hear it, the one that heard it best answers.

Snappier (2026-11-14): one screen listening answers at once (no wait for others); a hearing is kept
connected ahead of time while a screen listens for the phrase (Gemini's Live API takes a moment to
connect); the audio from just before the phrase was detected goes to the hearing (no lost first
words); the question ends when the service hears a pause after it, when the turn model hears
a finished sentence (quick job 110, lab_os.ai.turn), or after the page's silence; the chat's and
the voice's connections are opened while the person talks. Each turn's timing is logged
("voice timing …") and kept for `GET /api/voice/timings`.
"""

import asyncio
import base64
import contextlib
import dataclasses
import hashlib
import json
import logging
import math
import os
import re
import struct
import time
import unicodedata
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import aiohttp
from aiohttp import web

from lab_os.ai.assistant import Assistant
from lab_os.ai.chat import Conversation
from lab_os.ai.languages import LANGUAGES, clean_language
from lab_os.ai.speech import Hearing, VoiceError, hearing_for, speak_any, wav_seconds
from lab_os.ai.turn import FINISHED, TurnModel, TurnWatch
from lab_os.ai.voices import NoVoice, VoiceSetup, load_voices, pick_voice
from lab_os.ai.wake import (
    DEFAULT_SENSITIVITY,
    PHRASES,
    VERIFY_FROM,
    WakeDetector,
    WakeModels,
    sensitivity_level,
)
from lab_os.hub.greeting import HELLOS, time_of_day
from lab_os.personas import Persona
from lab_os.teleop.server import is_local

log = logging.getLogger(__name__)

SPEAK_MAX_CHARS = 900  # longer answers: the rest is on the screen
# a page says when it has played the answer; until then the brain counts the pieces' own length plus
# this much (a held greeting waits for the startup), so a page that never says so blocks the wake
# word on every screen for seconds, not minutes (quick job 42; it was a flat 120 s)
PLAYBACK_MARGIN_S = 10.0
# The answer says the wake word itself (the greeting's hint "say hey Jarvis", or another persona's
# word): the microphones hear it from the speaker, so the phrase is ignored until that piece
# has played, plus this much
SAID_PHRASE_MARGIN_S = 1.5
# Conversation mode (quick job 68): after each answer the brain listens again by itself, as after
# the wake word, until one of these is said, the button ends it, or voice stops working
CONVERSE_START = ("start a conversation", "conversation mode", "let's have a conversation")
CONVERSE_END = (
    "that's all",
    "that is all",
    "end the conversation",
    "stop the conversation",
    "stop listening",
    "goodbye",
    "bye",  # was "bye jarvis": every persona (quick job 92)
)
CONVERSE_NEXT_S = 0.3  # after the answer has played: the next question's listening starts
PLAYING_HOLD_S = 3.0  # "still playing" from the page holds this much longer
IGNORED_LOG_EVERY_S = 10.0  # a heard wake word that was ignored (a screen busy): logged this often
GREET_EVERY_S = 10.0
MAX_UTTERANCE_S = 60.0  # a mic held longer than this is stopped (a stuck key)
WAKE_UTTERANCE_S = 20.0  # after the wake word: the longest question
WAKE_WINDOW_S = 0.3  # several screens listen: wait this long for the others, best one answers
# Wake scores of clear speech are all near 1.0, so scores this close count as a tie, and the screen
# whose microphone heard the phrase loudest above its own room noise answers (quick job 70; smart
# speakers decide by signal energy too)
WAKE_SCORE_TIE = 0.05
WAKE_QUIET_S = 2.0  # after a wake, ignore the phrase for this long (the same words, other screens)
WAKE_PREROLL_BYTES = 9_600  # 0.3 s of audio from before the phrase was detected goes to the hearing
WAKE_RING_BYTES = 32_000  # 1 s of the latest audio kept while listening for the phrase
WAKE_END_HOLD_S = 0.35  # the service heard a pause after the question: end if it stays quiet
# ... but the words so far don't end a sentence ("37 times 48, then"): wait longer (quick job 83;
# 1.2 s until quick job 98)
WAKE_MID_HOLD_S = 1.6
# Quick job 110: the turn model doesn't end a question whose words so far (Gemini's, while it hears)
# stop on one of these: the person goes on ("37 times 48, … then add 199")
GOES_ON = re.compile(r"(,|\b(and|then|or|but|plus|minus|times|so|um|uh|er))\s*$", re.I)
STANDBY_MAX_S = 240.0  # a hearing kept connected ahead of time is renewed after this long
STANDBY_RETRY_S = 30.0  # it couldn't connect: try again after this long
WARM_EVERY_S = 5.0  # how often a listening screen checks the warm hearing
# quick job 99: each second that didn't wake it is logged with its best score, when the score was at
# least NEAR_MISS or the sound was MISS_LOUD_DB over the room (a try that scored near 0 shows too)
NEAR_MISS = 0.05
MISS_LOUD_DB = 10.0
MISS_EVERY_S = 1.0
AUDIO_GAP_S = 2.0  # a screen listening for the phrase sent no audio this long: logged
WORD_CHECK_S = 2.0  # how often a listening screen checks that the persona's wake word is the same
TIMINGS_KEPT = 20
HINTS = {  # how to talk to it, said after the greeting (by this screen's way in)
    "push_to_talk": "You can talk to me: hold the mic.",
    "dictation": "You can talk to me: tap the mic.",
    "wake_word": "You can talk to me: say {phrase}.",
    "none": "",  # no microphone on this screen: the greeting alone
}
SENTENCE_END = re.compile(r"[.!?…](?=[\s\"')\]]|$)|\n")


def spoken_greeting(opening: str, hint: str, now: datetime | None = None) -> str:
    """What the greeting says aloud: the opening's "Good morning." (else the time of day now) and
    the hint. Never the news or the persona's line, so it can be said from a recording."""
    hello = next((h for h in HELLOS if opening.startswith(h)), None)
    return f"{hello or time_of_day(now or datetime.now())} {hint}".strip()


def preview_text(persona: Persona, now: datetime | None = None) -> str:
    """What the persona chooser's preview says (quick job 151): the time of day and the persona's
    own greeting line, as its greeting on the hub when there's no news."""
    line = persona.lines.get("greeting", "")
    return f"{time_of_day(now or datetime.now())} {line}".strip()


def greeting_file(folder: Path, setup: VoiceSetup, text: str, persona: str = "") -> Path:
    """Where this voice's recording of `text` is kept: the name is a hash of the persona, the
    voice and the words, so another persona, a new voice or a changed line makes a new file (a
    persona never plays another's recording, quick job 84)."""
    voice = [setup.service, setup.base_url, setup.speak, setup.speaker, setup.style, setup.speed]
    # "v2": recordings from before quick job 47 may come from a fallback model (another person's
    # sound): they are made again once, by the first model; "v3": quiet edges (quick job 111)
    key = ["v3", voice, text] + ([persona] if persona else [])
    digest = hashlib.sha256(json.dumps(key).encode()).hexdigest()[:16]
    return folder / f"{setup.name}-{digest}.wav"


def voice_words(setup: VoiceSetup, models: list[str]) -> str:
    """Which voice spoke, for the log (quick job 47): the setup, the service, the TTS model(s) and
    the speaker. Two models in one answer can sound like two people."""
    spoke = sorted(set(models), key=models.index) or setup.speak_models[:1]
    many = " and ".join(spoke) + (
        " (two models: it may sound like two people)" if len(spoke) > 1 else ""
    )
    return (
        f"{setup.name} ({setup.where or setup.service}, {many}, voice {setup.speaker or 'default'})"
    )


def strip_wake(text: str, phrase: str) -> str:
    """The question without the wake phrase heard at its start ("Hey Jarvis, what's next?"). The
    audio from just before the detection may hold only the phrase's end ("…vis, what's next?")."""
    words = [re.escape(w) for w in phrase.split()]
    if not words:
        return text
    optional = "".join(rf"(?:{w}\W+)?" for w in words[:-1])
    last = phrase.split()[-1]
    tails = "|".join(re.escape(last[i:]) for i in range(len(last) - 3, 0, -1))  # "vis", "rvis"…
    end = rf"(?:{words[-1]}|{tails})" if tails else words[-1]
    return re.sub(rf"^\W*{optional}{end}\b\W*", "", text, flags=re.I).strip()


# the steps of a voice turn, in order, and how the log names them
STEPS = (
    ("detected", "heard the phrase"),
    ("picked", "this screen picked"),
    ("listening", "listening"),
    ("connected", "voice service ready"),
    ("ended", "question over"),
    ("words", "words final"),
    ("first_text", "first text"),
    ("first_audio", "first audio sent"),
    ("playing", "first word playing"),
)


def _s(seconds: float) -> str:
    return f"{seconds * 1000:.0f} ms" if seconds < 1 else f"{seconds:.2f} s"


@dataclass
class TurnTiming:
    """When each step of one voice turn happened (time.monotonic()): where the time goes from the
    end of "hey Jarvis" (its detection: on the recordings, ~0.1 s before the last sound) to the
    first spoken word."""

    how: str  # "wake word", "push-to-talk", "dictation"
    device: str = ""
    warm: bool = False  # the hearing was connected ahead of time
    ended_by: str = ""  # "pause" (the service), "turn model" (job 110), "page" (silence, a release)
    marks: dict = field(default_factory=dict)

    def mark(self, step: str, at: float | None = None) -> None:
        self.marks.setdefault(step, time.monotonic() if at is None else at)

    def summary(self) -> dict:
        order = [k for k, _ in STEPS if k in self.marks]
        t0 = self.marks[order[0]] if order else 0.0
        out = {"how": self.how, "device": self.device, "warm": self.warm}
        out |= {"ended_by": self.ended_by, "at": round(time.time(), 1)}
        out["ms"] = {k: round((self.marks[k] - t0) * 1000) for k in order}
        if "ended" in self.marks and "playing" in self.marks:
            out["waited_ms"] = round((self.marks["playing"] - self.marks["ended"]) * 1000)
        return out

    def line(self) -> str:
        parts, prev = [], None
        for key, label in STEPS:
            if key not in self.marks:
                continue
            if prev is not None:
                parts.append(f"{label} +{_s(self.marks[key] - prev)}")
            else:
                parts.append(label)
            prev = self.marks[key]
        extra = [self.device or "no name", self.how] + (["warm"] if self.warm else [])
        if self.ended_by:
            extra.append(f"ended by the {self.ended_by}")
        line = f"voice timing ({', '.join(extra)}): " + " · ".join(parts)
        if "ended" in self.marks and "playing" in self.marks:
            waited = self.marks["playing"] - self.marks["ended"]
            line += f" · waited {_s(waited)} after the question"
        return line


def pause_hold(text: str) -> float:
    """How long a pause after the words must last before the question ends: short after the end of
    a sentence, longer in the middle of one (a comma, "then", no full stop yet)."""
    return WAKE_END_HOLD_S if re.search(r"[.!?…]['\")\]]*\s*$", text) else WAKE_MID_HOLD_S


def said_any(text: str, phrases: tuple[str, ...]) -> bool:
    """One of the phrases, in a short sentence ("That's all, thanks!"): not inside a question."""
    words = re.sub(r"[^a-z' ]+", " ", text.lower().replace("’", "'")).split()
    plain = " ".join(words)
    return len(words) <= 8 and any(p in plain for p in phrases)


def pick_nearest(heard: dict) -> object:
    """The screen that answers: the best wake score; among scores within WAKE_SCORE_TIE of it, the
    loudest above its own room noise (`heard`: screen → (score, dB above its noise))."""
    best = max(s for s, _ in heard.values())
    close = {k: v for k, v in heard.items() if v[0] >= best - WAKE_SCORE_TIE}
    return max(close, key=lambda k: (close[k][1], close[k][0]))


def pcm_rms(pcm: bytes) -> float:
    """The loudness of 16-bit mono PCM (0 to 32768)."""
    n = len(pcm) // 2
    if not n:
        return 0.0
    samples = struct.unpack(f"<{n}h", pcm[: n * 2])
    return math.sqrt(sum(x * x for x in samples) / n)


def _script(c: str) -> str:
    """The writing system of a letter, roughly: "Latin", "Cyrillic", "CJK", … (for the log)."""
    try:
        name = unicodedata.name(c)
    except ValueError:
        return "unknown"
    return "CJK" if name.startswith("CJK") else name.split(" ")[0].title()


def speakable(text: str) -> str:
    """The answer as it should sound: no markdown marks, code as words."""
    text = re.sub(r"```.*?(```|$)", " ", text, flags=re.S)
    text = re.sub(r"[`*_#>]+", "", text)
    text = re.sub(r"https?://\S+", "the link on the screen", text)
    return re.sub(r"\s+", " ", text).strip()


def take_speech(buf: str, first: bool, final: bool) -> tuple[str, str]:
    """Split off what to speak now: the first sentence alone (so speech starts soon, even when the
    whole answer is already there), later every finished sentence, at the end everything. Returns
    (to speak, the rest)."""
    ends = [m.end() for m in SENTENCE_END.finditer(buf)]
    ends = [e for e in ends if buf[:e].strip() and buf[e:].strip()]  # a sentence with more after it
    if first and ends:
        return buf[: ends[0]].strip(), buf[ends[0] :]
    if final:
        return buf.strip(), ""
    if not ends:
        return "", buf
    return buf[: ends[-1]].strip(), buf[ends[-1] :]


@dataclass
class VoiceDesk:
    """The brain's voice: which setup speaks for the persona, whether voice works now, and
    whether a voice turn is running anywhere (the hub never resets during one)."""

    chat: Conversation
    assistant: Assistant
    persona: Callable[[], Persona]
    internet: Callable[[], bool | None] = lambda: None
    voices: Callable[[], dict[str, VoiceSetup]] = load_voices
    greeting: Callable[[], str] = lambda: ""  # the conversation's opening ("Good evening. …")
    recordings: Callable[[], Path | None] = lambda: None  # where greetings are kept; None = not
    links: set = field(default_factory=set)
    resting: dict = field(default_factory=dict)  # TTS models over their limit → until when
    venue_wake: Callable[[], bool] = lambda: True  # the venue allows the wake word
    # a typed turn's answer to speak (visitor mode's welcome, quick job 35), taken once; None = none
    say: Callable[[], str | None] = lambda: None
    wake_models: WakeModels = field(default_factory=WakeModels)
    turn_model: TurnModel = field(default_factory=TurnModel)  # a finished question? (quick job 110)
    timings: deque = field(default_factory=lambda: deque(maxlen=TIMINGS_KEPT))
    _session: aiohttp.ClientSession | None = None
    _wake_candidates: dict | None = None  # screens that heard the phrase in this window → score
    _wake_quiet_until: float = 0.0
    _phrase_said_until: float = 0.0  # an answer says the wake word itself: ignore it until then
    _ignored_logged: float = 0.0
    _standby: Hearing | None = None  # a hearing connected ahead of time (the wake word)
    _standby_task: asyncio.Task | None = None
    _standby_retry_at: float = 0.0
    _closing: set = field(default_factory=set)  # warm hearings being let go

    def setup(self, persona: Persona | None = None) -> VoiceSetup:
        """The persona's voice setup (the active one, else `persona`), with the persona's own
        speaker for that service (quick job 100: J.A.R.V.I.S. a male voice, the Lab Assistant a
        female one)."""
        persona = persona or self.persona()
        setup = pick_voice(persona.voice, self.voices())
        speaker = persona.speakers.get(setup.service)
        return dataclasses.replace(setup, speaker=speaker) if speaker else setup

    async def preview(self, persona: Persona, now: datetime | None = None) -> tuple[str, bytes]:
        """The persona's greeting in its own voice, for the persona chooser (quick job 151): the
        words and a WAV. From its recording when it said them before (offline, free), else spoken
        now and saved. Raises VoiceError (or NoVoice) with a sentence for the page."""
        text = preview_text(persona, now)
        setup = self.setup(persona)  # NoVoice: the persona has none
        folder = self.recordings()
        saved = greeting_file(folder, setup, text, persona.id) if folder else None
        if saved and saved.is_file():
            return text, saved.read_bytes()
        if self.internet() is False and not setup.local:
            raise VoiceError("No internet, so no voice preview for now.")
        if why := self.chat.paused():
            raise VoiceError(why)
        used: list[str] = []
        wav = await speak_any(self.session(), setup, text, self.resting, used=used)
        self.log_spend(setup, 0, wav_seconds(wav), "greeting")
        log.info("voice: the %s preview, spoken by %s", persona.id, voice_words(setup, used))
        # kept only when the first model spoke it: another can sound like another person (47)
        if saved and used[:1] == list(setup.speak_models[:1]):
            try:
                saved.parent.mkdir(parents=True, exist_ok=True)
                part = saved.with_suffix(".part")
                part.write_bytes(wav)
                os.replace(part, saved)
            except OSError as e:
                log.warning("voice: couldn't save the %s preview (%s)", persona.id, e)
        return text, wav

    def why_not(self) -> str | None:
        """Why there's no voice right now (a sentence), or None."""
        try:
            setup = self.setup()
        except NoVoice as e:
            return str(e)
        if self.internet() is False and not setup.local:
            return "No internet, so no voice for now. Typing works when the AI does."
        return self.chat.paused()

    def wake_word(self) -> str:
        return self.persona().wake_word

    def wake_phrase(self) -> str:
        return PHRASES.get(self.wake_word(), ("", self.wake_word().replace("_", " ")))[1]

    def wake_why_not(self) -> str | None:
        """Why no screen can use the wake word now (a sentence), or None."""
        why = self.why_not()
        if why:
            return why
        if self.wake_word() in ("", "none"):
            return "This assistant has no wake word (the persona's `wake_word: none`)."
        if not self.venue_wake():
            return (
                "The wake word is off in this venue (`wake_word:` in its file; off by default "
                "on a public venue)."
            )
        return self.wake_models.why_not(self.wake_word())

    def status(self) -> dict:
        why = self.why_not()
        try:
            s = self.setup()
            where = {"setup": s.name, "where": s.where, "service": s.service}
        except NoVoice:
            where = {"setup": None, "where": None, "service": None}
        wake_why = self.wake_why_not()
        wake = {"available": wake_why is None, "why": wake_why, "phrase": self.wake_phrase()}
        return {"available": why is None, "why": why} | where | {"wake": wake}

    # ---------- the wake word: several screens may hear it, one answers ----------

    def wake_heard(self, link: "VoiceLink", score: float, snr_db: float = 0.0) -> None:
        """A screen heard the phrase. A spoken answer that runs or plays doesn't stop it: the new
        question stops that answer (quick job 57). Someone asking now, or a typed answer, does."""
        now = time.monotonic()
        busy = self._asking_now()
        if now < self._phrase_said_until:
            log.info(
                "voice: %s heard the wake word in the answer itself: ignored",
                link.device or "a screen",
            )
            return
        if now < self._wake_quiet_until or busy:
            if busy and now - self._ignored_logged > IGNORED_LOG_EVERY_S:
                self._ignored_logged = now
                log.info(
                    "voice: %s heard the wake word, ignored: %s",
                    link.device or "a screen",
                    self.busy_why(),
                )
            return
        if self._wake_candidates is None:
            self._wake_candidates = {}
            if sum(lk.wake_on for lk in self.links) > 1:  # others may have heard it too
                asyncio.get_running_loop().call_later(WAKE_WINDOW_S, self._wake_pick)
            else:  # the only screen listening: no one to wait for
                self._wake_candidates[link] = (score, snr_db)
                self._wake_pick()
                return
        before = self._wake_candidates.get(link)
        if before is None or score > before[0]:
            self._wake_candidates[link] = (score, snr_db)

    def _asking_now(self) -> bool:
        """A question is being heard, or a typed question answered (no voice turn runs): the wake
        word waits. A spoken answer doesn't: the wake word stops it."""
        hearing = any(lk.hearing is not None for lk in self.links)
        typed = self.chat.busy and not any(lk.answering() for lk in self.links)
        return hearing or typed

    def said_phrase(self, text: str, ends: float) -> None:
        """An answer's piece says the wake word ("say hey Jarvis"): every screen ignores it until
        the piece has played."""
        word = self.wake_phrase().split()[-1:] or [""]
        if word[0] and word[0].lower() in text.lower():
            self._phrase_said_until = max(self._phrase_said_until, ends + SAID_PHRASE_MARGIN_S)

    async def stop_answers(self, why: str) -> None:
        """A new question (the wake word or a mic press): stop every spoken answer that is
        thought of or played now, on every screen (quick job 57)."""
        for lk in list(self.links):
            await lk.stop_answer(why)

    def busy_why(self) -> str:
        """What keeps the wake word from starting a question now, for the log."""
        why = ["the chat is answering"] if self.chat.busy else []
        now = time.monotonic()
        for lk in self.links:
            name = lk.device or "a screen"
            if lk.hearing is not None:
                why.append(f"{name} is hearing a question")
            elif lk.task is not None and not lk.task.done():
                why.append(f"{name} is answering")
            elif now < lk.playing_until:
                left = lk.playing_until - now
                why.append(f"{name} hasn't said it finished playing ({left:.0f} s more)")
        return "; ".join(why) or "nothing now"

    def _wake_pick(self) -> None:
        heard, self._wake_candidates = self._wake_candidates or {}, None
        heard = {lk: s for lk, s in heard.items() if lk in self.links and lk.wake_on}
        if not heard:
            return
        winner = pick_nearest(heard)
        if len(heard) > 1:
            log.info(
                "voice: %s heard the wake word: %s answers",
                ", ".join(
                    f"{lk.device or 'a screen'} ({s:.2f}, {snr:.0f} dB)"
                    for lk, (s, snr) in sorted(heard.items(), key=lambda kv: -kv[1][0])
                ),
                winner.device or "a screen",
            )
        self._wake_quiet_until = time.monotonic() + WAKE_QUIET_S
        for lk in self.links:
            if lk is not winner and lk.wake_on:
                lk.wake_elsewhere()
        asyncio.get_running_loop().create_task(winner.woken(heard[winner][0]))

    # ---------- warm connections: no waiting for the voice service after the phrase ----------

    def warm(self) -> None:
        """While a screen listens for the wake word, keep one hearing connected ahead of time
        (Gemini's Live API: OpenAI's hears after the question, so there's nothing to connect)."""
        if not any(lk.wake_on for lk in self.links):
            self.cool()
            return
        if self._standby_task and not self._standby_task.done():
            return
        try:
            if self.why_not():
                return
            setup = self.setup()
        except NoVoice:
            return
        sb = self._standby
        if sb is not None and self._usable(sb, setup):
            return
        if setup.service != "gemini" or time.monotonic() < self._standby_retry_at:
            return
        self._standby_task = asyncio.get_running_loop().create_task(self._make_standby(setup))

    def _usable(self, h: Hearing, setup: VoiceSetup) -> bool:
        fresh = h.started_at is not None and time.monotonic() - h.started_at < STANDBY_MAX_S
        return h.setup == setup and h.alive() and fresh

    async def _make_standby(self, setup: VoiceSetup) -> None:
        old, self._standby = self._standby, None
        if old is not None:
            await old.close()
        h = hearing_for(self.session(), setup, lambda text: None)
        try:
            await h.start()
        except VoiceError as e:
            log.info("voice: couldn't connect a hearing ahead of time (%s)", e)
            self._standby_retry_at = time.monotonic() + STANDBY_RETRY_S
            return
        if any(lk.wake_on for lk in self.links) and not self._session_closing:
            self._standby = h
        else:
            await h.close()

    def cool(self) -> None:
        """No screen listens for the phrase: let the warm hearing go."""
        sb, self._standby = self._standby, None
        if sb is not None:
            self._let_go(sb)

    def _let_go(self, h: Hearing) -> None:
        task = asyncio.get_running_loop().create_task(h.close())
        self._closing.add(task)
        task.add_done_callback(self._closing.discard)

    def take_hearing(
        self, setup: VoiceSetup, on_words, language: str | None = None
    ) -> tuple[Hearing, bool]:
        """A hearing for this turn: the warm one if it's still good (True), else a new one."""
        sb, self._standby = self._standby, None
        if sb is not None and self._usable(sb, setup):
            sb.on_words, sb.language = on_words, language
            asyncio.get_running_loop().call_soon(self.warm)  # the next one
            return sb, True
        if sb is not None:
            self._let_go(sb)
        return hearing_for(self.session(), setup, on_words, language), False

    def prewarm_speech(self, setup: VoiceSetup) -> None:
        """The answer will be spoken soon: open the connection to the voice service now (listing
        its models: free, nothing generated), so the first sentence doesn't wait for it."""

        async def touch() -> None:
            hdr = {"x-goog-api-key": setup.key or ""} if setup.service == "gemini" else {}
            if setup.service != "gemini" and setup.key:
                hdr = {"Authorization": f"Bearer {setup.key}"}
            try:
                async with self.session().get(
                    f"{setup.base_url}/models", headers=hdr, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    await resp.read()
            except (aiohttp.ClientError, TimeoutError, OSError):
                pass  # only a head start

        asyncio.get_running_loop().create_task(touch())

    def chat_warm(self) -> None:
        """A question is coming: open the chat's connection while the person talks."""
        asyncio.get_running_loop().create_task(self.chat.warm())

    async def say_text(self, text: str, device: str | None = None) -> str:
        """Speak a sentence aloud on a screen with the hub open (the MCP tool `say_aloud`, quick
        job 80): the named device, else one on the brain's own computer, else any. A sentence
        for the caller: what it did, or "Error: ..." and why not."""
        text = " ".join(str(text or "").split())[:SPEAK_MAX_CHARS]
        if not text:
            return "Error: there's nothing to say."
        why = self.why_not()
        if why:
            return f"Error: {why}"
        links = [lk for lk in self.links if not device or lk.device == device]
        if not links:
            where = f"called {device!r} " if device else ""
            return f"Error: no screen {where}has the hub open, so nobody would hear it."
        link = sorted(links, key=lambda lk: (not lk.local, lk.device))[0]
        if link.task is not None and not link.task.done():
            return f"Error: {link.device or 'that screen'} is talking or listening now."
        link.task = asyncio.get_running_loop().create_task(link._say(self.setup(), text))
        log.info("voice: saying a sentence on %s (asked by a tool)", link.device or "a screen")
        return f"Saying it on {link.device or 'the screen'}."

    def keep_timing(self, timing: "TurnTiming") -> None:
        self.timings.append(timing.summary())
        log.info("%s", timing.line())

    def active(self) -> bool:
        return any(link.active() for link in self.links)

    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            # connections kept a minute (default 15 s): the voice's, from the warm-up to the answer
            conn = aiohttp.TCPConnector(keepalive_timeout=60)
            self._session = aiohttp.ClientSession(connector=conn)
        return self._session

    _session_closing: bool = False

    async def close(self) -> None:
        self._session_closing = True
        if self._standby_task and not self._standby_task.done():
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await asyncio.wait_for(self._standby_task, 3)
        if self._standby is not None:
            await self._standby.close()
            self._standby = None
        if self._closing:
            await asyncio.gather(*self._closing, return_exceptions=True)
        if self._session:
            await self._session.close()

    def log_spend(self, setup: VoiceSetup, heard_s: float, spoken_s: float, what: str) -> None:
        if heard_s <= 0 and spoken_s <= 0:
            return
        cost = setup.cost(heard_s, spoken_s)
        self.chat.spend.write_voice(setup.name, setup.service, heard_s, spoken_s, cost, what)


class Speaker:
    """Speaks an answer while it's still being written: text in with `add()`, WAVs out to the page
    in order. One request at a time, so at most a sentence waits for the service."""

    def __init__(self, link: "VoiceLink", setup: VoiceSetup, split_first: bool = True):
        """`split_first=False`: no hurry (the greeting): one request for all of it."""
        self.link, self.setup, self.split_first = link, setup, split_first
        self.buf, self.said_chars, self.sent, self.seconds = "", 0, 0, 0.0
        self.closed = self.stopped = False
        self.cut = False  # a drafted prompt began: the rest is for the screen
        self.models: list[str] = []  # the TTS model of each piece (one voice: the same, if it can)
        self._wake = asyncio.Event()
        self.task = asyncio.create_task(self._run())

    def add(self, text: str) -> None:
        if self.cut or self.stopped:
            return
        self.buf += text
        if "Prompt:" in self.buf:
            self.buf = self.buf.split("Prompt:", 1)[0] + "\nThe prompt is on the screen."
            self.cut = True
        self._wake.set()

    def close(self) -> None:
        self.closed = True
        self._wake.set()

    async def _run(self) -> None:
        while True:
            await self._wake.wait()
            self._wake.clear()
            while True:
                first = self.sent == 0 and self.split_first
                text, self.buf = take_speech(self.buf, first, self.closed)
                text = speakable(text)
                if not text:
                    break
                if self.said_chars + len(text) > SPEAK_MAX_CHARS:
                    text = "The rest is on the screen."
                    self.stopped, self.buf = True, ""
                await self._say(text)
                if self.stopped:
                    break
            if self.closed or self.stopped:
                return

    async def _say(self, text: str) -> None:
        try:
            desk = self.link.desk
            wav = await speak_any(
                desk.session(),
                self.setup,
                text,
                desk.resting,
                self.models[-1] if self.models else None,
                self.models,
            )
        except VoiceError as e:
            self.stopped = True
            self.link.send({"type": "voice_error", "message": str(e)})
            if self.link.converse:  # no voice: the conversation ends (quick job 68)
                await self.link.converse_off(f"the voice service didn't answer ({e})")
            return
        self.said_chars += len(text)
        self.seconds += wav_seconds(wav)
        if self.link.timing:
            self.link.timing.mark("first_audio")
        self.link.send_audio(self.sent, text, wav)
        self.sent += 1


class VoiceLink:
    """One page's voice connection."""

    def __init__(
        self, desk: VoiceDesk, ws: web.WebSocketResponse, device: str = "", local: bool = False
    ):
        self.desk, self.ws, self.device = desk, ws, device
        self.local = local  # the page runs on the brain's computer (visitor mode's tools)
        self.hearing = None
        self._starting: asyncio.Task | None = None  # connecting to the service (audio waits)
        self.mode = "ask"
        self.task: asyncio.Task | None = None  # hearing's end + the turn
        self.playing_until = 0.0  # the page plays audio until it says it's done (or this time)
        self._audio_ends = 0.0  # when the audio sent so far ends, if it plays at once
        self.wake_on = False  # this page streams its microphone for the wake word
        self.detector: WakeDetector | None = None
        self.from_wake = False  # this hearing began with the wake word
        self.sensitivity = DEFAULT_SENSITIVITY  # this device's (Settings → This device)
        self._ring: deque[tuple[int, bytes]] = deque()  # the latest audio: (its offset, PCM)
        self._ring_total = 0  # bytes of wake audio received so far
        self._detected_at: tuple[float, int] | None = None  # when, and the audio offset
        self._floor = 0.0  # this microphone's room noise (loudness, slowly followed)
        self._last_audio = 0.0
        self._next_warm = 0.0
        self._second: list = [0.0, 0.0, 0.0, False]  # this second: start, best score, loudest, woke
        self._word_checked = 0.0
        self._rewaking: asyncio.Task | None = None
        self._turn_watch: TurnWatch | None = None  # the question after the wake word: finished yet?
        self.timing: TurnTiming | None = None  # this turn's steps
        self.pages: dict | None = None  # what this page can show (the assistant opens them)
        self.hear_in: str | None = None  # this device's assistant languages (None = any)
        self.answer_in: str | None = None
        self.last_greet = 0.0
        self.started_at = 0.0
        self._stopping = False  # stop_answer() cancels the turn: it sends nothing more
        self.converse = False  # conversation mode: listen again after each answer (quick job 68)
        self._out: asyncio.Queue = asyncio.Queue()
        self._writer = asyncio.create_task(self._write())

    # ---------- sending (one writer, so messages keep their order) ----------

    def send(self, msg: dict) -> None:
        self._out.put_nowait(msg)

    def send_audio(self, seq: int, text: str, wav: bytes) -> None:
        # the answer's pieces play one after the other: this one ends after the ones before it
        self._audio_ends = max(time.monotonic(), self._audio_ends) + wav_seconds(wav)
        self.playing_until = self._audio_ends + PLAYBACK_MARGIN_S
        self.desk.said_phrase(text, self._audio_ends)
        self.send(
            {
                "type": "audio",
                "seq": seq,
                "text": text,
                "mime": "audio/wav",
                "data": base64.b64encode(wav).decode(),
            }
        )

    async def _write(self) -> None:
        while True:
            msg = await self._out.get()
            if self.ws.closed:
                continue
            with contextlib.suppress(ConnectionResetError, RuntimeError):
                await self.ws.send_json(msg)

    # ---------- state ----------

    def active(self) -> bool:
        busy = self.hearing is not None or (self.task is not None and not self.task.done())
        return busy or time.monotonic() < self.playing_until

    def answering(self) -> bool:
        """The question was heard: its words, the answer or its audio are on the way or play."""
        running = self.hearing is None and self.task is not None and not self.task.done()
        return running or time.monotonic() < self.playing_until

    async def stop_answer(self, why: str) -> bool:
        """Stop this screen's answer now: the turn (the words, the AI, the speech) and its audio
        on the page ("stopped"). False when there was none."""
        if not self.answering():
            return False
        task = self.task
        if task is not None and not task.done():
            self._stopping = True
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            self._stopping = False
        self.playing_until = 0.0
        self.timing = None
        self.send({"type": "stopped"})
        log.info("voice: %s's answer stopped: %s", self.device or "a screen", why)
        return True

    def _settle(self) -> None:
        """Back to rest, unless another page's voice turn runs or this page still plays (called
        from this link's own turn, so its task doesn't count)."""
        others = any(link.active() for link in self.desk.links if link is not self)
        if not others and self.hearing is None and time.monotonic() >= self.playing_until:
            self.desk.chat.settle()

    # ---------- from the page ----------

    async def on_text(self, msg: dict) -> None:
        kind = msg.get("type")
        if isinstance(msg.get("pages"), dict):  # with listen and wake: what the page can show
            self.pages = msg["pages"]
        if isinstance(msg.get("lang"), dict):  # with listen and wake: "This device" → languages
            self.hear_in = clean_language(msg["lang"].get("hear"))
            self.answer_in = clean_language(msg["lang"].get("answer"))
        if kind == "listen":
            await self.listen(str(msg.get("mode") or "ask"))
        elif kind == "end":
            self.end()
        elif kind == "cancel":
            await self.cancel()
        elif kind == "played":
            self.played(msg)
        elif kind == "greet":
            self.greet(str(msg.get("way") or "push_to_talk"))
        elif kind == "say":
            self.say()
        elif kind == "wake":
            await self.wake(bool(msg.get("on")), msg.get("sensitivity"))
        elif kind == "converse":
            if msg.get("on"):
                await self.converse_on("the button")
            else:
                await self.converse_off("you pressed the button")
        elif kind == "playing":
            if self.timing and msg.get("seq") == 0:
                self.timing.mark("playing")
                self._timing_done()
        elif kind == "wake_mic":  # the page's microphone stopped or came back (the Quest)
            why = msg.get("why") or "ok"
            log.info("voice: %s's microphone: %s", self.device or "a screen", why)

    def on_audio(self, pcm: bytes) -> None:
        now = time.monotonic()
        if self.hearing is not None:
            self.hearing.feed(pcm)
            if self._turn_watch is not None and self.from_wake and self._turn_watch.feed(pcm):
                asyncio.get_running_loop().create_task(
                    self._ask_turn(self.hearing, self._turn_watch)
                )
            limit = WAKE_UTTERANCE_S if self.from_wake else MAX_UTTERANCE_S
            if now - self.started_at > limit:
                self.end()
            return
        if not self.wake_on or self.detector is None:
            return  # not listening for the phrase (an answer that runs or plays doesn't stop it)
        if self._last_audio and now - self._last_audio > AUDIO_GAP_S:
            log.info(
                "voice: %s sent no audio for the wake word for %.1f s (its microphone paused?)",
                self.device or "a screen",
                now - self._last_audio,
            )
        self._last_audio = now
        if now - self._word_checked > WORD_CHECK_S:  # another persona or word (⚙, quick job 90)
            self._word_checked = now
            if self.detector.word != self.desk.wake_word() and not self._rewaking:
                self._rewaking = asyncio.get_running_loop().create_task(self._rewake())
        if now >= self._next_warm:
            self._next_warm = now + WARM_EVERY_S
            self.desk.warm()
        self._ring.append((self._ring_total, pcm))
        self._ring_total += len(pcm)
        while self._ring and self._ring[0][0] + WAKE_RING_BYTES < self._ring_total:
            self._ring.popleft()
        score = self.detector.feed(pcm)
        rms = pcm_rms(pcm)
        if not self.detector.fired:
            self._follow_floor(rms)
        self._log_second(now, score, rms, self.detector.fired)
        if self.detector.fired:
            if self._detected_at is None or now - self._detected_at[0] > 1.0:
                self._detected_at = (now, self._ring_total)
            if self.detector.verified:
                log.info(
                    'voice: %s heard "%s" at %.2f, under %.2f: the verifier took it for the word',
                    self.device or "a screen",
                    self.desk.wake_phrase(),
                    score,
                    self.detector.threshold,
                )
            self.desk.wake_heard(self, score, self._snr_db())

    def _log_second(self, now: float, score: float, rms: float, fired: bool) -> None:
        """Each second: if it didn't wake, its best score in the log (quick job 99: how close a
        missed try came)."""
        sec = self._second
        if now - sec[0] >= MISS_EVERY_S:
            start, best, loudest, woke = sec
            db = 20 * math.log10(max(loudest, 1.0) / max(self._floor, 1.0))
            playing = now < self.playing_until  # its own answer, not a try of the word
            if start and not woke and not playing and (best >= NEAR_MISS or db >= MISS_LOUD_DB):
                log.info(
                    'voice: %s missed "%s"? best %.2f in this second (it takes %.2f at '
                    "sensitivity %d%s; %.0f dB over the room)",
                    self.device or "a screen",
                    self.desk.wake_phrase(),
                    best,
                    self.detector.threshold,
                    self.detector.sensitivity,
                    f", or the verifier from {VERIFY_FROM:.2f}" if self.detector.verifier else "",
                    db,
                )
            sec[:] = [now, 0.0, 0.0, False]
        sec[1], sec[2] = max(sec[1], score), max(sec[2], rms)
        sec[3] = sec[3] or fired

    def _follow_floor(self, rms: float) -> None:
        """The room's noise at this microphone: down fast, up slowly (speech doesn't count much)."""
        if self._floor == 0.0:
            self._floor = rms
        else:
            k = 0.1 if rms < self._floor else 0.005
            self._floor += k * (rms - self._floor)

    def _snr_db(self) -> float:
        """How loud the last second (the phrase) was above this microphone's room noise, in dB."""
        level = pcm_rms(b"".join(p for _, p in self._ring))
        return 20 * math.log10(max(level, 1.0) / max(self._floor, 1.0))

    # ---------- the wake word ----------

    async def wake(self, on: bool, sensitivity=None) -> None:
        """The page starts or stops streaming its microphone for the wake word (`sensitivity`:
        this device's setting, 1–9)."""
        if not on:
            self.wake_on, self.detector = False, None
            self._last_audio = 0.0
            self.desk.warm()  # lets the warm hearing go when no screen listens
            return
        self.sensitivity = sensitivity_level(sensitivity)
        why = self.desk.wake_why_not()
        if why:
            self.wake_on = False
            self.send({"type": "wake_off", "why": why})
            return
        word = self.desk.wake_word()
        if self.detector is None or self.detector.word != word:
            # loading the models the first time takes a moment: not on the brain's main loop
            self.detector = await asyncio.to_thread(WakeDetector, self.desk.wake_models, word)
        self.detector.set_sensitivity(self.sensitivity)
        if not self.wake_on:
            log.info(
                "voice: %s listens for the wake word (sensitivity %d)",
                self.device or "a screen",
                self.sensitivity,
            )
        self.wake_on = True
        self.send({"type": "wake_on", "phrase": self.desk.wake_phrase()})
        self.desk.warm()

    async def _rewake(self) -> None:
        """The persona's wake word changed: listen for the new one (no restart)."""
        try:
            log.info(
                "voice: %s now listens for %s", self.device or "a screen", self.desk.wake_phrase()
            )
            await self.wake(True, self.sensitivity)
        finally:
            self._rewaking = None

    def wake_elsewhere(self) -> None:
        if self.detector:
            self.detector.reset()
        self.send({"type": "wake_elsewhere"})

    async def woken(self, score: float) -> None:
        """This screen heard the phrase best: hear the question, like a push-to-talk press. A
        spoken answer that runs stops first (its page hears "stopped" before "wake")."""
        await self.desk.stop_answers("the wake word")
        self.send({"type": "wake", "score": round(score, 2)})  # first: the page's sound
        log.info("voice: wake word heard on %s (%.2f)", self.device or "a screen", score)
        if self.detector:
            self.detector.reset()
        detected = self._detected_at or (time.monotonic(), self._ring_total)
        self._detected_at = None
        start = detected[1] - WAKE_PREROLL_BYTES  # from just before the detection, to now
        preroll = [pcm for off, pcm in self._ring if off + len(pcm) > start]
        self._ring.clear()
        self.timing = TurnTiming("wake word", self.device)
        self.timing.mark("detected", detected[0])
        self.timing.mark("picked")
        await self.listen("ask")
        if self.hearing is None:
            self.timing = None  # refused (busy, no voice): already said why
        else:
            self.from_wake = True
            self.hearing.on_pause = lambda h=self.hearing: self._question_paused(h)
            self._turn_watch = TurnWatch(self._floor, b"".join(preroll))
            for pcm in preroll:  # the words right after the phrase may already be here
                self.hearing.feed(pcm)
            self.desk.chat_warm()

    # ---------- conversation mode (quick job 68) ----------

    async def converse_on(self, how: str) -> None:
        """Keep listening and answering, no wake word, until it's ended."""
        why = self.desk.why_not()
        if why:
            self.send({"type": "converse", "on": False, "why": why})
            return
        if not self.converse:
            log.info("voice: %s: conversation mode on (%s)", self.device or "a screen", how)
        self.converse = True
        self.send({"type": "converse", "on": True})
        if not self.active():
            await self._converse_turn()
        else:  # asked inside a turn (the phrase), or the answer still plays: once it's done
            self._converse_next()

    async def converse_off(self, why: str) -> None:
        if not self.converse:
            return
        self.converse = False
        log.info("voice: %s: conversation mode off (%s)", self.device or "a screen", why)
        self.send({"type": "converse", "on": False, "why": why})
        if self.hearing is not None and self.from_wake:  # its listening, not a question: drop it
            await self.cancel()

    async def _converse_turn(self) -> None:
        """The next question of the conversation: hear it as after the wake word."""
        if not self.converse or self.active():
            return
        others = any(lk.active() for lk in self.desk.links if lk is not self)
        if others or self.desk.chat.busy:  # another screen's turn: wait for it, don't stop it
            loop = asyncio.get_running_loop()
            loop.call_later(1.0, lambda: loop.create_task(self._converse_turn()))
            return
        self.send({"type": "wake", "conversation": True})  # the page streams and watches again
        self.timing = TurnTiming("conversation", self.device)
        self.timing.mark("picked")
        await self.listen("ask", stop_others=False)
        if self.hearing is None:  # refused (busy, no voice): it already said why
            self.timing = None
            await self.converse_off("voice isn't working now")
            return
        self.from_wake = True
        self.hearing.on_pause = lambda h=self.hearing: self._question_paused(h)
        self._turn_watch = TurnWatch(self._floor)

    def _converse_next(self) -> None:
        """After an answer (or nothing heard), listen again, a moment later."""
        if self.converse:
            loop = asyncio.get_running_loop()
            loop.call_later(CONVERSE_NEXT_S, lambda: loop.create_task(self._converse_turn()))

    def _question_paused(self, hearing: Hearing) -> None:
        """The service heard a pause after words: the question may be over (not if only the
        phrase was said so far)."""
        if self.hearing is not hearing or not strip_wake(hearing.text, self.desk.wake_phrase()):
            return
        loop = asyncio.get_running_loop()
        loop.call_later(pause_hold(hearing.text), self._end_if_quiet, hearing)

    async def _ask_turn(self, hearing: Hearing, watch: TurnWatch) -> None:
        """A short quiet after speech: ask the turn model if the question is finished (quick job
        110). Finished → it ends now; not → the page's silence watch still ends it later."""
        model = self.desk.turn_model
        if model.why_not:
            return  # it didn't load (logged once)
        loop = asyncio.get_running_loop()  # the first question loads it (~0.2 s), off the loop
        score = await loop.run_in_executor(None, model.finished, watch.audio())
        if (
            model.why_not
            or self.hearing is not hearing
            or self._turn_watch is not watch
            or watch.quiet_s <= 0
        ):
            return  # ended meanwhile, or the person talks again
        text = getattr(hearing, "text", "") or ""
        if text and not strip_wake(text, self.desk.wake_phrase()):
            return  # only the phrase so far
        going_on = bool(text and GOES_ON.search(text))
        log.info(
            "voice: %s: the turn model says %s (%.2f)%s",
            self.device or "a screen",
            "finished" if score >= FINISHED else "not finished",
            score,
            ", but the words go on" if going_on and score >= FINISHED else "",
        )
        if score >= FINISHED and not going_on:
            if self.timing:
                self.timing.ended_by = "turn model"
            self.send({"type": "ended"})  # the page stops its own silence watch
            self.end()

    def _end_if_quiet(self, hearing: Hearing) -> None:
        if self.hearing is hearing and not hearing.in_speech:
            if self.timing:
                self.timing.ended_by = "pause"
            self.send({"type": "ended"})  # the page stops its own silence watch
            self.end()

    async def listen(self, mode: str, stop_others: bool = True) -> None:
        if mode != "dictate" and stop_others:  # a new question stops a spoken answer (job 57)
            await self.desk.stop_answers("a new question")
        if self.hearing is not None or (self.task and not self.task.done()):
            self.send({"type": "error", "message": "I'm still on the last one."})
            return
        why = self.desk.why_not()
        if why:
            self.send({"type": "error", "message": why})
            return
        if mode == "ask" and self.desk.chat.busy:
            self.send({"type": "error", "message": "I'm still answering the last question."})
            return
        setup = self.desk.setup()
        self.mode = mode if mode in ("ask", "dictate") else "ask"
        self.playing_until = 0.0
        last = {"text": None}

        def words(text: str) -> None:
            if text != last["text"]:
                last["text"] = text
                self.send({"type": "heard", "text": text, "final": False})

        hearing, warm = self.desk.take_hearing(setup, words, self.hear_in)
        hearing.assistant_name = self.desk.persona().display_name
        self.hearing = hearing
        self.started_at = time.monotonic()
        if self.timing is None or "listening" in self.timing.marks:  # else: the wake word's
            how = "dictation" if self.mode == "dictate" else "push-to-talk"
            self.timing = TurnTiming(how, self.device)
        self.timing.warm = warm
        self.timing.mark("listening")
        self.desk.assistant.set("listening", device=self.device or "")
        self.send({"type": "listening", "mode": self.mode})
        if warm:
            self.timing.mark("connected")
            self._starting = None
            return
        # connect in the background: the audio arriving meanwhile is kept and sent after
        self._starting = asyncio.create_task(self._start(hearing))

    async def _start(self, hearing) -> bool:
        try:
            await hearing.start()
            if self.timing:
                self.timing.mark("connected")
            return True
        except VoiceError as e:
            if self.hearing is hearing:
                self.hearing = None
            self.send({"type": "error", "message": str(e)})
            self._settle()
            if self.converse:  # the voice service is gone: the conversation ends (quick job 68)
                await self.converse_off(f"the voice service didn't answer ({e})")
            return False

    def end(self) -> None:
        if self.hearing is None:
            return
        hearing, self.hearing = self.hearing, None
        self._turn_watch = None
        if self.timing:
            self.timing.ended_by = self.timing.ended_by or "page"
            self.timing.mark("ended")
        if self.mode == "ask":
            self.desk.prewarm_speech(hearing.setup)
        self.task = asyncio.create_task(self._after_hearing(hearing, self._starting))

    async def _after_hearing(self, hearing, starting: asyncio.Task | None) -> None:
        setup = hearing.setup
        if starting is not None and not await starting:
            return  # couldn't connect: already said why
        try:
            text = await hearing.finish()
        except asyncio.CancelledError:  # stopped for a new question: let the service go
            with contextlib.suppress(Exception):
                await hearing.close()
            raise
        except VoiceError as e:
            self.send({"type": "error", "message": str(e)})
            self._settle()
            return
        finally:
            self.desk.log_spend(setup, hearing.seconds, 0, "heard")
        self._log_question(setup, text)
        if self.from_wake:
            self.from_wake = False
            text = strip_wake(text, self.desk.wake_phrase())
        if self.timing:
            self.timing.mark("words")
        # "That's all" and "conversation mode" are not questions: the page shows them and ends the
        # turn (quick job 83: it waited for an answer, on the thinking core)
        command = self.mode != "dictate" and (
            (self.converse and said_any(text, CONVERSE_END))
            or (not self.converse and said_any(text, CONVERSE_START))
        )
        self.send(
            {"type": "heard", "text": text, "final": True} | ({"command": True} if command else {})
        )
        if self.mode == "dictate" or not text:
            self._timing_done()
            self._settle()
            self._converse_next()
            return
        if self.converse and said_any(text, CONVERSE_END):
            self._timing_done()
            self._settle()
            await self.converse_off(f'you said "{text}"')
            return
        if not self.converse and said_any(text, CONVERSE_START):
            self._timing_done()
            self._settle()
            await self.converse_on(f'you said "{text}"')
            return
        await self._turn(text, setup)

    def _log_question(self, setup: VoiceSetup, text: str) -> None:
        """Each spoken question: the device's language settings and the transcriber, so a lab
        check can say which setting a strange result had (quick job 46). Not the words."""
        other = sorted({_script(c) for c in text if c.isalpha()} - {"Latin"})
        log.info(
            "voice: question on %s: expects %s, answers %s, heard by %s (%s)%s",
            self.device or "a screen",
            LANGUAGES.get(self.hear_in or "", "any language"),
            LANGUAGES.get(self.answer_in or "", "any language"),
            setup.where,
            setup.hear,
            f"; letters not in English: {', '.join(other)}" if other else "",
        )
        if not text.strip():  # quick job 112: say so, the page shows "I didn't hear a question"
            log.info("voice: no words in the question on %s", self.device or "a screen")

    def _timing_done(self) -> None:
        timing, self.timing = self.timing, None
        if timing is not None:
            self.desk.keep_timing(timing)

    async def _turn(self, text: str, setup: VoiceSetup) -> None:
        speaker = Speaker(self, setup)
        try:
            async for ev in self.desk.chat.ask(
                text, self.pages, self.answer_in, local=self.local, device=self.device or ""
            ):
                self.send(ev)
                if ev["type"] == "text":
                    if self.timing:
                        self.timing.mark("first_text")
                    speaker.add(ev["text"])
        finally:
            if self._stopping:  # a new question stopped it: say nothing more
                speaker.stopped = True
                speaker.task.cancel()
                self.desk.log_spend(setup, 0, speaker.seconds, "spoken")
            else:
                speaker.close()
                await speaker.task
                self.desk.chat.take_say()  # a spoken welcome was just said: nothing left to say
                self.send({"type": "audio_end", "count": speaker.sent})
                self.desk.log_spend(setup, 0, speaker.seconds, "spoken")
                if speaker.sent:
                    log.info(
                        "voice: answer on %s spoken by %s",
                        self.device or "a screen",
                        voice_words(setup, speaker.models),
                    )
                if speaker.sent:
                    self.desk.assistant.set("speaking", 0.5)
                else:
                    self._timing_done()  # nothing to play: done here
                    self._settle()
                    self._converse_next()

    async def cancel(self) -> None:
        self.from_wake = False
        self._turn_watch = None
        self.timing = None
        if self.hearing is not None:
            hearing, self.hearing = self.hearing, None
            if self._starting and not self._starting.done():
                self._starting.cancel()
            await hearing.close()
            self.desk.log_spend(hearing.setup, hearing.seconds, 0, "heard")
        self.playing_until = 0.0
        self._settle()
        self._converse_next()  # conversation mode: nothing was asked, listen again

    def played(self, msg: dict) -> None:
        if msg.get("done"):
            self._timing_done()  # (a page that never said "playing")
            self.playing_until = 0.0
            self._settle()
            self._converse_next()
        elif not self.desk.chat.busy:
            self.playing_until = max(self.playing_until, time.monotonic() + PLAYING_HOLD_S)
            self.desk.assistant.set(
                "speaking", float(msg.get("loudness") or 0), device=self.device or ""
            )

    def greet(self, way: str) -> None:
        """The spoken greeting after the jump: the time of day and a hint how to talk, from its
        recording when this voice has said it before (no request, works offline), else spoken
        now and saved."""
        if self.task and not self.task.done():
            return  # a turn runs: it ends with its own audio_end
        if time.monotonic() - self.last_greet < GREET_EVERY_S:
            self._greeted(0)
            return
        try:
            setup = self.desk.setup()
        except NoVoice:
            self._greeted(0)
            return
        hint = HINTS.get(way, HINTS["push_to_talk"]).format(phrase=self.desk.wake_phrase())
        text = spoken_greeting(self.desk.greeting(), hint)
        folder = self.desk.recordings()
        # the active persona's: its wake word in the hint, its own recording (quick job 84)
        saved = greeting_file(folder, setup, text, self.desk.persona().id) if folder else None
        if saved and saved.is_file():
            self.last_greet = time.monotonic()
            log.info("voice: the greeting, from its recording by %s", voice_words(setup, []))
            self.send_audio(0, text, saved.read_bytes())
            self._greeted(1)
            return
        if self.desk.why_not():
            self._greeted(0)
            return
        self.last_greet = time.monotonic()
        self.task = asyncio.create_task(self._greet(setup, text, saved))

    def say(self) -> None:
        """Speak the welcome a typed turn left waiting (visitor mode, typed on this screen): only
        that answer, once, and only on the brain's own computer."""
        text = self.desk.say() if self.local else None
        if not text or (self.task and not self.task.done()) or self.desk.why_not():
            self.send({"type": "audio_end", "count": 0})
            return
        self.task = asyncio.create_task(self._say(self.desk.setup(), text))

    async def _say(self, setup: VoiceSetup, text: str) -> None:
        speaker = Speaker(self, setup, split_first=False)
        speaker.add(text)
        speaker.close()
        await speaker.task
        self.send({"type": "audio_end", "count": speaker.sent})
        self.desk.log_spend(setup, 0, speaker.seconds, "spoken")
        if speaker.sent:
            self.desk.assistant.set("speaking", 0.5)
        else:
            self._settle()

    def _greeted(self, count: int) -> None:
        self.send({"type": "audio_end", "count": count, "greeting": True})

    async def _greet(self, setup: VoiceSetup, text: str, saved: Path | None) -> None:
        try:
            used: list[str] = []
            wav = await speak_any(self.desk.session(), setup, text, self.desk.resting, used=used)
        except VoiceError as e:
            self.send({"type": "voice_error", "message": str(e)})
            self._greeted(0)
            return
        log.info("voice: the greeting, spoken now by %s", voice_words(setup, used))
        if saved and used[:1] != list(setup.speak_models[:1]):
            # another model spoke it (the first was over its limit): it can sound like another
            # person, so it isn't kept as this voice's recording (quick job 47)
            log.info(
                "voice: greeting not saved: %s spoke it, not %s", used[0], setup.speak_models[0]
            )
            saved = None
        if saved:
            try:
                saved.parent.mkdir(parents=True, exist_ok=True)
                part = saved.with_suffix(".part")
                part.write_bytes(wav)
                os.replace(part, saved)  # never a half-written recording
                log.info("voice: greeting saved to %s", saved)
            except OSError as e:
                log.warning(
                    "voice: couldn't save the greeting (%s): it's spoken again next time", e
                )
        self.send_audio(0, text, wav)
        self._greeted(1)
        self.desk.log_spend(setup, 0, wav_seconds(wav), "greeting")

    async def close(self) -> None:
        self.converse = False
        await self.cancel()
        if self.task and not self.task.done():
            self.task.cancel()
        self._writer.cancel()


async def voice_ws(request: web.Request, desk: VoiceDesk) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=4 * 1024 * 1024)
    await ws.prepare(request)
    device = re.sub(r"[^a-z0-9-]", "", request.query.get("device", "").lower())[:32]
    link = VoiceLink(desk, ws, device, local=is_local(request))
    desk.links.add(link)
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.BINARY:
                link.on_audio(msg.data)
            elif msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = msg.json()
                except ValueError:
                    log.info("voice: not JSON: %.80s", msg.data)
                    continue
                if isinstance(data, dict):
                    await link.on_text(data)
    finally:
        desk.links.discard(link)

        async def let_go() -> None:
            await link.close()
            link._settle()
            desk.warm()  # the last listening screen left: the warm hearing goes

        # its own task, waited for at shutdown: the server cancels this handler when the page's
        # connection drops, and a cancelled close leaves the voice service's socket open
        task = asyncio.get_running_loop().create_task(let_go())
        desk._closing.add(task)
        task.add_done_callback(desk._closing.discard)
        await asyncio.shield(task)
    return ws
