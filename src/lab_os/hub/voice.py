"""Voice on the hub (focus step 7): the page records and plays, the brain hears, thinks and speaks.

One WebSocket per page, `/ws/voice` (docs/dev/protocol.md → "Voice"). While the person holds the
mic, the page sends 16 kHz PCM; the brain passes it to the voice service (lab_os.ai.speech), which
hears the words. On release, the words go to the same conversation as typing (persona, read tools,
history, spend cap: lab_os.ai.chat), and the answer comes back as text **and** speech: the first
sentence is spoken as soon as it's written, the rest while that one plays. API keys never leave the
brain.

The assistant's state follows: `listening` while the mic is held, then the chat's `thinking`, and
`speaking` (with the loudness the page reports) until the page has played the last word.

The wake word: a page that chose it streams its microphone while the hub is awake; the brain listens
for the phrase itself (lab_os.ai.wake, nothing leaves the computer) and only then starts hearing,
like a push-to-talk press. If several screens hear it, the one that heard it best answers.
"""

import asyncio
import base64
import contextlib
import logging
import re
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

import aiohttp
from aiohttp import web

from lab_os.ai.assistant import Assistant
from lab_os.ai.chat import Conversation
from lab_os.ai.speech import VoiceError, hearing_for, speak_any, wav_seconds
from lab_os.ai.voices import NoVoice, VoiceSetup, load_voices, pick_voice
from lab_os.ai.wake import PHRASES, THRESHOLD, WakeDetector, WakeModels
from lab_os.personas import Persona

log = logging.getLogger(__name__)

SPEAK_MAX_CHARS = 900  # longer answers: the rest is on the screen
PLAYBACK_GRACE_S = 120.0  # a page that never says it finished playing doesn't hold `in_use` forever
GREET_EVERY_S = 10.0
MAX_UTTERANCE_S = 60.0  # a mic held longer than this is stopped (a stuck key)
WAKE_UTTERANCE_S = 20.0  # after the wake word: the longest question
WAKE_WINDOW_S = 0.25  # several screens heard it: wait this long for the others, best one answers
WAKE_QUIET_S = 2.0  # after a wake, ignore the phrase for this long (the same words, other screens)
WAKE_PREROLL_BYTES = 9_600  # 0.3 s of audio from just before the wake goes to the hearing
HINTS = {  # how to talk to it, said after the greeting (by this screen's way in)
    "push_to_talk": "You can talk to me: hold the mic.",
    "dictation": "You can talk to me: tap the mic.",
    "wake_word": "You can talk to me: say {phrase}.",
    "none": "",  # no microphone on this screen: the greeting alone
}
SENTENCE_END = re.compile(r"[.!?…](?=[\s\"')\]]|$)|\n")


def strip_wake(text: str, phrase: str) -> str:
    """The question without the wake phrase heard at its start ("Hey Jarvis, what's next?")."""
    words = [re.escape(w) for w in phrase.split()]
    if not words:
        return text
    optional = "".join(rf"(?:{w}\W+)?" for w in words[:-1])
    return re.sub(rf"^\W*{optional}{words[-1]}\b\W*", "", text, flags=re.I).strip()


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
    greeting: Callable[[], str] = lambda: ""
    links: set = field(default_factory=set)
    resting: dict = field(default_factory=dict)  # TTS models over their limit → until when
    venue_wake: Callable[[], bool] = lambda: True  # the venue allows the wake word
    wake_models: WakeModels = field(default_factory=WakeModels)
    _session: aiohttp.ClientSession | None = None
    _wake_candidates: dict | None = None  # screens that heard the phrase in this window → score
    _wake_quiet_until: float = 0.0

    def setup(self) -> VoiceSetup:
        return pick_voice(self.persona().voice, self.voices())

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

    def wake_heard(self, link: "VoiceLink", score: float) -> None:
        now = time.monotonic()
        busy = self.chat.busy or any(lk.active() for lk in self.links)
        if now < self._wake_quiet_until or busy:
            return
        if self._wake_candidates is None:
            self._wake_candidates = {}
            asyncio.get_running_loop().call_later(WAKE_WINDOW_S, self._wake_pick)
        self._wake_candidates[link] = max(score, self._wake_candidates.get(link, 0.0))

    def _wake_pick(self) -> None:
        heard, self._wake_candidates = self._wake_candidates or {}, None
        heard = {lk: s for lk, s in heard.items() if lk in self.links and lk.wake_on}
        if not heard:
            return
        winner = max(heard, key=heard.get)
        self._wake_quiet_until = time.monotonic() + WAKE_QUIET_S
        for lk in self.links:
            if lk is not winner and lk.wake_on:
                lk.wake_elsewhere()
        asyncio.get_running_loop().create_task(winner.woken(heard[winner]))

    def active(self) -> bool:
        return any(link.active() for link in self.links)

    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
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
            wav = await speak_any(desk.session(), self.setup, text, desk.resting)
        except VoiceError as e:
            self.stopped = True
            self.link.send({"type": "voice_error", "message": str(e)})
            return
        self.said_chars += len(text)
        self.seconds += wav_seconds(wav)
        self.link.send_audio(self.sent, text, wav)
        self.sent += 1


class VoiceLink:
    """One page's voice connection."""

    def __init__(self, desk: VoiceDesk, ws: web.WebSocketResponse):
        self.desk, self.ws = desk, ws
        self.hearing = None
        self._starting: asyncio.Task | None = None  # connecting to the service (audio waits)
        self.mode = "ask"
        self.task: asyncio.Task | None = None  # hearing's end + the turn
        self.playing_until = 0.0  # the page plays audio until it says it's done (or this time)
        self.wake_on = False  # this page streams its microphone for the wake word
        self.detector: WakeDetector | None = None
        self.from_wake = False  # this hearing began with the wake word
        self._recent: deque[bytes] = deque()  # the last audio before a wake (its tail is kept)
        self.last_greet = 0.0
        self.started_at = 0.0
        self._out: asyncio.Queue = asyncio.Queue()
        self._writer = asyncio.create_task(self._write())

    # ---------- sending (one writer, so messages keep their order) ----------

    def send(self, msg: dict) -> None:
        self._out.put_nowait(msg)

    def send_audio(self, seq: int, text: str, wav: bytes) -> None:
        self.playing_until = time.monotonic() + PLAYBACK_GRACE_S
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

    def _settle(self) -> None:
        """Back to rest, unless another page's voice turn runs or this page still plays (called
        from this link's own turn, so its task doesn't count)."""
        others = any(link.active() for link in self.desk.links if link is not self)
        if not others and self.hearing is None and time.monotonic() >= self.playing_until:
            self.desk.chat.settle()

    # ---------- from the page ----------

    async def on_text(self, msg: dict) -> None:
        kind = msg.get("type")
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
        elif kind == "wake":
            await self.wake(bool(msg.get("on")))

    def on_audio(self, pcm: bytes) -> None:
        if self.hearing is not None:
            self.hearing.feed(pcm)
            limit = WAKE_UTTERANCE_S if self.from_wake else MAX_UTTERANCE_S
            if time.monotonic() - self.started_at > limit:
                self.end()
            return
        if not self.wake_on or self.detector is None or self.active():
            return  # not listening for the phrase (or a turn runs, or the answer plays)
        self._recent.append(pcm)
        while sum(map(len, self._recent)) > WAKE_PREROLL_BYTES:
            self._recent.popleft()
        if self.detector.feed(pcm) >= THRESHOLD:
            self.desk.wake_heard(self, self.detector.last)

    # ---------- the wake word ----------

    async def wake(self, on: bool) -> None:
        """The page starts or stops streaming its microphone for the wake word."""
        if not on:
            self.wake_on, self.detector = False, None
            return
        why = self.desk.wake_why_not()
        if why:
            self.wake_on = False
            self.send({"type": "wake_off", "why": why})
            return
        word = self.desk.wake_word()
        if self.detector is None or self.detector.word != word:
            # loading the models the first time takes a moment: not on the brain's main loop
            self.detector = await asyncio.to_thread(WakeDetector, self.desk.wake_models, word)
        self.wake_on = True
        self.send({"type": "wake_on", "phrase": self.desk.wake_phrase()})

    def wake_elsewhere(self) -> None:
        if self.detector:
            self.detector.reset()
        self.send({"type": "wake_elsewhere"})

    async def woken(self, score: float) -> None:
        """This screen heard the phrase best: hear the question, like a push-to-talk press."""
        log.info("voice: wake word heard (%.2f)", score)
        if self.detector:
            self.detector.reset()
        preroll, self._recent = list(self._recent), deque()
        self.send({"type": "wake", "score": round(score, 2)})
        await self.listen("ask")
        if self.hearing is not None:
            self.from_wake = True
            for pcm in preroll:  # the words right after the phrase may already be here
                self.hearing.feed(pcm)

    async def listen(self, mode: str) -> None:
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

        hearing = self.hearing = hearing_for(self.desk.session(), setup, words)
        self.started_at = time.monotonic()
        self.desk.assistant.set("listening")
        self.send({"type": "listening", "mode": self.mode})
        # connect in the background: the audio arriving meanwhile is kept and sent after
        self._starting = asyncio.create_task(self._start(hearing))

    async def _start(self, hearing) -> bool:
        try:
            await hearing.start()
            return True
        except VoiceError as e:
            if self.hearing is hearing:
                self.hearing = None
            self.send({"type": "error", "message": str(e)})
            self._settle()
            return False

    def end(self) -> None:
        if self.hearing is None:
            return
        hearing, self.hearing = self.hearing, None
        self.task = asyncio.create_task(self._after_hearing(hearing, self._starting))

    async def _after_hearing(self, hearing, starting: asyncio.Task | None) -> None:
        setup = hearing.setup
        if starting is not None and not await starting:
            return  # couldn't connect: already said why
        try:
            text = await hearing.finish()
        except VoiceError as e:
            self.send({"type": "error", "message": str(e)})
            self._settle()
            return
        finally:
            self.desk.log_spend(setup, hearing.seconds, 0, "heard")
        if self.from_wake:
            self.from_wake = False
            text = strip_wake(text, self.desk.wake_phrase())
        self.send({"type": "heard", "text": text, "final": True})
        if self.mode == "dictate" or not text:
            self._settle()
            return
        await self._turn(text, setup)

    async def _turn(self, text: str, setup: VoiceSetup) -> None:
        speaker = Speaker(self, setup)
        try:
            async for ev in self.desk.chat.ask(text):
                self.send(ev)
                if ev["type"] == "text":
                    speaker.add(ev["text"])
        finally:
            speaker.close()
            await speaker.task
            self.send({"type": "audio_end", "count": speaker.sent})
            self.desk.log_spend(setup, 0, speaker.seconds, "spoken")
            if speaker.sent:
                self.desk.assistant.set("speaking", 0.5)
            else:
                self._settle()

    async def cancel(self) -> None:
        self.from_wake = False
        if self.hearing is not None:
            hearing, self.hearing = self.hearing, None
            if self._starting and not self._starting.done():
                self._starting.cancel()
            await hearing.close()
            self.desk.log_spend(hearing.setup, hearing.seconds, 0, "heard")
        self.playing_until = 0.0
        self._settle()

    def played(self, msg: dict) -> None:
        if msg.get("done"):
            self.playing_until = 0.0
            self._settle()
        elif not self.desk.chat.busy:
            self.playing_until = time.monotonic() + PLAYBACK_GRACE_S
            self.desk.assistant.set("speaking", float(msg.get("loudness") or 0))

    def greet(self, way: str) -> None:
        """The spoken greeting after the jump: the greeting's text and a hint how to talk."""
        if self.task and not self.task.done():
            return  # a turn runs: it ends with its own audio_end
        if time.monotonic() - self.last_greet < GREET_EVERY_S or self.desk.why_not():
            self.send({"type": "audio_end", "count": 0, "greeting": True})
            return
        self.last_greet = time.monotonic()
        hint = HINTS.get(way, HINTS["push_to_talk"]).format(phrase=self.desk.wake_phrase())
        text = f"{self.desk.greeting()} {hint}".strip()
        if not text:
            self.send({"type": "audio_end", "count": 0, "greeting": True})
            return
        self.task = asyncio.create_task(self._greet(text))

    async def _greet(self, text: str) -> None:
        setup = self.desk.setup()
        speaker = Speaker(self, setup, split_first=False)
        speaker.add(text)
        speaker.close()
        await speaker.task
        self.send({"type": "audio_end", "count": speaker.sent, "greeting": True})
        self.desk.log_spend(setup, 0, speaker.seconds, "greeting")

    async def close(self) -> None:
        await self.cancel()
        if self.task and not self.task.done():
            self.task.cancel()
        self._writer.cancel()


async def voice_ws(request: web.Request, desk: VoiceDesk) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=4 * 1024 * 1024)
    await ws.prepare(request)
    link = VoiceLink(desk, ws)
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
        await link.close()
        link._settle()
    return ws
