"""The conversation manager: owns the hub chat's turn and sets the assistant's state.

One turn at a time: `ask()` sets `thinking`, streams the answer (`speaking` from the first words),
logs what it cost, and goes back to `idle`. It refuses with a full sentence when no AI setup is
usable or this month's budget is used up. With `tools` (the brain's MCP read tools: the docs,
git, devices; lab_os.ai.tools) the model may look things up first, up to MAX_TOOL_ROUNDS times.
The hub's chat reads and answers (rule 5), and opens pages on the screen that asked (decision
2026-11-14): the page sends what it can show (`pages`), the model gets an `open_page` tool for them,
and the turn yields an `open` event the page acts on. A round that only opens a page is answered
right away ("Here's Teleop."), without asking the model again.
With `actions` (the hub's visitor mode, lab_os.hub.visitors; the arm, lab_os.hub.arm_desk) the
model also gets the tools that start and exit visitor mode and wave the arm, and (when Settings
allows it) move the arm to a pose and hand over the cube, when the question comes from the brain's
own computer.
With a `store` (lab_os.ai.history) the conversation is kept for a short while: saved after every
answer, put aside by a reset, brought back with `restore()`.
"""

import asyncio
import contextlib
import json
import logging
import re
from collections.abc import AsyncIterator, Callable
from datetime import datetime

import aiohttp

from lab_os.ai.assistant import Assistant
from lab_os.ai.client import AiError, Reply, Usage, check, estimate, reach, stream_chat
from lab_os.ai.history import ChatStore
from lab_os.ai.languages import LANGUAGES, clean_language
from lab_os.ai.models import NoSetup, Setup, load_setups, pick
from lab_os.ai.spend import SpendLog
from lab_os.ai.tools import ChatTools
from lab_os.personas import Persona

log = logging.getLogger(__name__)

MAX_HISTORY = 20  # messages sent along with a question (older ones are left out: cost)
# the asking device's Answers language (quick job 33): in the system prompt and with the question
ANSWER_IN = (
    "Always answer in {name}, whatever language the question is in. "
    "If the question is in another language, still answer in {name}."
)
MAX_TOOL_ROUNDS = 4  # look-ups per question before the model must answer
CONFIRM_TRIES, CONFIRM_GAP_S = 2, 3.0  # a failed check while connected: ask again this often first

RULES = """\
You are the assistant on the hub screen of {place}. It is {now}.
You answer questions. Your tools are what you can do now: you can't move the robot arms from here
except with a tool made for it.
Answer in plain text without markdown, in one to four short sentences unless asked for more."""

# Harder questions to a stronger model (quick job 69): the quick model calls this tool, the brain
# asks the `strong` setup of models.yaml, and the quick model says the result
THINK = "think_hard"
STRONG_SETUP = "strong"
THINK_QUIET_S = 120.0  # the strong model thinks before it writes: no data for this long is fine
THINK_TOOL = {
    "type": "function",
    "function": {
        "name": THINK,
        "description": (
            "Ask a stronger, slower model. Use it for a hard question only: maths or a "
            "calculation, a plan with several steps, or a hard question not about the lab. Never "
            "for a simple or lab question. Give the whole problem, with every number. Then say "
            "its answer in your own words, briefly, for speaking aloud."
        ),
        "parameters": {
            "type": "object",
            "properties": {"problem": {"type": "string", "description": "the whole problem"}},
            "required": ["problem"],
        },
    },
}
THINK_SYSTEM = (
    "Solve the problem carefully. Then give the answer first, in at most 4 short sentences "
    "that can be spoken aloud: no tables, no markdown, no LaTeX; numbers written plainly."
)
THINK_SAY = "Let me think about that. "
# Answers: Any (quick job 55): the plain persona's prompt names no language, and short or misheard
# spoken questions (speech-to-text guesses, sometimes in another language) got answers in German,
# Turkish or Portuguese; JARVIS's English-sounding prompt kept it in English. One rule for every
# persona now:
ANY_LANGUAGE = (
    "Answer in English. Answer in another language only when the whole question is clearly "
    "in that language. A short, unclear or mixed question gets an English answer: spoken "
    "questions come from speech-to-text, which sometimes guesses words in another language."
)
# Answers: Any, and a question of one or two words ("Hi"): it still got answers in other languages
# (quick job 83). The rule goes with the question: the conversation's language so far, else English.
SHORT_WORDS = 2
SHORT_FIRST = "Answer in English."
SHORT_LATER = "Answer in the language of this conversation so far."


def short_question_rule(text: str, earlier_questions: int) -> str | None:
    """The language rule for a very short question with Answers: Any, or None for a longer one."""
    if len(text.split()) > SHORT_WORDS:
        return None
    return SHORT_LATER if earlier_questions else SHORT_FIRST


OPEN_PAGE = "open_page"
PAGE_RULES = """\
You can open pages on this screen, the one the person is talking to (open_page): {pages}.
When someone wants to see, open, pull up, show or go to one ("show me the AI spend", "go back to
the hub"), open it instead of describing it. "hub" closes whatever is open."""
PAGE_ID = re.compile(r"^[a-z][a-z0-9_-]{0,23}$")
MAX_PAGES = 24


def clean_pages(pages) -> dict[str, str]:
    """What the asking page says it can show: {id: title}, checked (anything odd is left out)."""
    if not isinstance(pages, dict):
        return {}
    out = {}
    for pid, title in list(pages.items())[:MAX_PAGES]:
        if isinstance(pid, str) and PAGE_ID.match(pid) and isinstance(title, str) and title.strip():
            out[pid] = title.strip()[:40]
    return out


def page_tool(pages: dict[str, str]) -> dict:
    listed = "; ".join(f"{pid} = {title}" for pid, title in pages.items())
    return {
        "type": "function",
        "function": {
            "name": OPEN_PAGE,
            "description": f"Open a page on this screen (the one being talked to): {listed}.",
            "parameters": {
                "type": "object",
                "properties": {"page": {"type": "string", "enum": list(pages)}},
                "required": ["page"],
            },
        },
    }


def opened_line(page: str, title: str) -> str:
    """The short answer after opening a page (spoken on a voice turn)."""
    return "Back to the hub." if page == "hub" else f"Here's {title}."


TOOL_RULES = """\
You can look things up with read tools: the project's docs (start with project_status for "what's
next?"; ideas has what's on hold), its git history, and the device list. Use them instead of
guessing, and say where an answer came from in a few words.
When someone wants to work on something, draft a prompt they can paste into a Claude Code or Codex
session in the lab-os repository: what to read first (AGENTS.md, docs/plan/current-focus.md), the
goal, the step and its "done when", anything to watch out for. Put it after a line "Prompt:" in
plain text; it may be longer than your usual answers."""


def _page_arg(arguments: str, pages: dict[str, str]) -> str | None:
    try:
        page = json.loads(arguments or "{}").get("page")
    except (ValueError, AttributeError):
        return None
    return page if isinstance(page, str) and page in pages else None


class Conversation:
    def __init__(
        self,
        assistant: Assistant,
        spend: SpendLog,
        setup_name: str = "main",
        personality: str = "",
        place_name: str = "",
        setups: Callable[[], dict[str, Setup]] = load_setups,
        persona: Callable[[], Persona] | None = None,
        tools: ChatTools | None = None,
        store: ChatStore | None = None,
        actions=None,
    ):
        """`actions`: more tools for this turn, `.tools(local)` → OpenAI-style tools and
        `await .call(name, local, arguments)` → (the result for the model, events for the page).
        `persona`: read before every turn, so a venue or persona edit applies without a restart;
        it then sets the setup (`model`) and the personality instead of the two arguments."""
        self.assistant = assistant
        self._persona = persona
        self.tools = tools
        self.display_name = ""
        self.spend = spend
        self.setup_name = setup_name
        self.personality = personality.strip()
        self.place_name = place_name
        self._setups = setups
        self.store = store
        self.actions = actions
        self.say_next: str | None = None  # a welcome a typed turn's page asks to hear (`say`)
        # what's on screen: {"role": "user"|"assistant", ...}; after a restart, the one kept last
        self.messages: list[dict] = store.load() if store else []
        self.busy = False
        self.connected: bool | None = None  # None = not checked yet
        self.problem: str | None = None  # the last failure, as a sentence
        self._session: aiohttp.ClientSession | None = None

    # ---------- setup and status ----------

    def _refresh(self) -> None:
        if self._persona:
            p = self._persona()
            self.setup_name, self.personality, self.display_name = (
                p.model,
                p.personality,
                p.display_name,
            )

    def setup(self) -> Setup:
        """The setup that would answer now (follows `fallback` when a key is missing)."""
        self._refresh()
        return pick(self.setup_name, self._setups())

    def strong_setup(self) -> Setup | None:
        """The stronger model for hard questions (models.yaml → `strong`), if it's set up here and
        isn't the setup that answers anyway."""
        try:
            strong = pick(STRONG_SETUP, self._setups())
            quick = self.setup()
        except NoSetup:
            return None
        same = (strong.base_url, strong.model, strong.options)
        return None if same == (quick.base_url, quick.model, quick.options) else strong

    async def _think_hard(self, strong: Setup, arguments: str) -> str:
        """Ask the stronger model; its answer for the quick model to say. Its cost goes in the
        spend log under its own setup (quick job 69)."""
        try:
            problem = str(json.loads(arguments or "{}").get("problem") or "").strip()
        except (ValueError, AttributeError):
            problem = ""
        if not problem:
            return "Error: give the whole problem in `problem`."
        sent = [{"role": "system", "content": THINK_SYSTEM}, {"role": "user", "content": problem}]
        reply, text = Reply(), ""
        try:
            async for piece in stream_chat(
                self._session_(), strong, sent, reply, None, quiet_s=THINK_QUIET_S
            ):
                text += piece
        except AiError as e:
            return f"Error: the stronger model didn't answer ({e}). Answer as well as you can."
        finally:
            usage = reply.usage if reply.usage.tokens_in else estimate(sent, text)
            cost = strong.cost(usage.tokens_in, usage.tokens_out, usage.tokens_cached)
            self.spend.write(strong.name, strong.model, usage, cost)
            log.info("chat: think_hard by %s/%s = $%.5f", strong.name, strong.model, cost)
        return f"The stronger model's answer: {text.strip()}\nSay it in your own words, briefly."

    def paused(self) -> str | None:
        """Why the chat can't answer right now (a full sentence), or None."""
        try:
            self.setup()
        except NoSetup as e:
            return str(e)
        if self.spend.over_budget():
            budget = self.spend.budget_usd
            return (
                f"This month's AI budget (${budget:.2f}) is used up, so the chat is paused until "
                "the 1st. Everything else on the hub still works."
            )
        return None

    def status(self) -> dict:
        try:
            s = self.setup()
            setup = {"setup": s.name, "where": s.where, "model": s.model}
        except NoSetup:
            setup = {"setup": None, "where": None, "model": None}
        return setup | {
            "connected": self.connected,
            "paused": self.paused(),
            "problem": self.problem,
            "busy": self.busy,
        }

    def _session_(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def warm(self) -> None:
        """Open the connection to the service ahead of a question (the wake word was heard):
        lists the models, free, nothing generated. Failures don't matter here."""
        with contextlib.suppress(NoSetup):
            await check(self._session_(), self.setup())

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    def settle(self) -> None:
        """Back to rest (also after a voice turn's last spoken word)."""
        self._settle()

    def _settle(self) -> None:
        """Back to rest: idle when the AI is reachable, else offline (error stays until it is)."""
        if self.busy:
            return
        if self.paused() or self.connected is False:
            self.assistant.set("error" if self.problem else "offline")
        else:
            self.assistant.set("idle")

    async def check(self, internet: bool | None = None) -> bool:
        """Is the AI reachable? (Lists the service's models: costs nothing.) Sets the state."""
        if self.busy:
            return bool(self.connected)
        try:
            setup = self.setup()
        except NoSetup:
            self.connected = False
            self._settle()
            return False
        was = self.connected
        if internet is False and not setup.local:
            why = "no internet"
        else:
            why = await reach(self._session_(), setup)
            # one failed check isn't "not connected" yet: a single slow name lookup or a hiccup on
            # the network used to grey the hub for 20 s while idle (quick job 32). Ask again first.
            for _ in range(CONFIRM_TRIES if why and was else 0):
                log.info("AI: %s didn't answer the check (%s); asking again", setup.name, why)
                await asyncio.sleep(CONFIRM_GAP_S)
                why = await reach(self._session_(), setup)
                if not why:
                    break
        self.connected = why is None
        if self.connected:
            self.problem = None
        if self.connected != was and was is not None:
            if self.connected:
                log.info("AI: %s answers again", setup.name)
            else:
                log.warning("AI: %s not reachable (%s): shown as not connected", setup.name, why)
        self._settle()
        return self.connected

    # ---------- a turn ----------

    def system_prompt(
        self, pages: dict[str, str] | None = None, answer_in: str | None = None
    ) -> str:
        self._refresh()
        now = datetime.now().strftime("%A %Y-%m-%d, %H:%M")
        rules = RULES.format(place=self.place_name or "this place", now=now)
        if self.display_name:
            rules = f"Your name on the screen is {self.display_name}.\n{rules}"
        if self.tools:
            rules = f"{rules}\n\n{TOOL_RULES}"
        if pages:
            listed = ", ".join(f"{title} ({pid})" for pid, title in pages.items())
            rules = f"{rules}\n\n{PAGE_RULES.format(pages=listed)}"
        if clean_language(answer_in):
            # the asking device's "Output language" (quick job 33)
            name = LANGUAGES[clean_language(answer_in)]
            rules = f"{rules}\n\n{ANSWER_IN.format(name=name)}"
        else:
            rules = f"{rules}\n\n{ANY_LANGUAGE}"
        return f"{self.personality}\n\n{rules}" if self.personality else rules

    def clear(self, opening: str | None = None) -> None:
        """Forget the conversation (the hub's reset: the next visitor starts fresh). `opening`:
        the assistant's first message (the greeting), sent along with later questions."""
        if self.busy:
            return
        if self.store:
            self.store.put_aside(self.messages)  # an accidental reset can be undone for a while
        self.messages = [{"role": "assistant", "content": opening}] if opening else []
        if self.store:
            self.store.save(self.messages)

    def previous(self) -> dict | None:
        """The conversation a reset put aside: {"questions", "saved_at"}, or None."""
        return self.store.previous() if self.store else None

    def restore(self) -> bool:
        """Bring back the conversation a reset put aside. The current one is put aside in its
        place (if it has a question), so pressing it twice changes nothing."""
        if self.busy or not self.store:
            return False
        kept = self.store.take_previous()
        if kept is None:
            return False
        self.store.put_aside(self.messages)
        self.messages = kept
        self.store.save(self.messages)
        return True

    def take_say(self) -> str | None:
        """The last welcome (the turn that started visitor mode), once: a typed turn's page asks
        for it to be spoken."""
        text, self.say_next = self.say_next, None
        return text

    async def ask(
        self,
        text: str,
        pages: dict | None = None,
        answer_in: str | None = None,
        local: bool = False,
        device: str = "",
    ) -> AsyncIterator[dict]:
        """One turn. Yields events for the page: state, text (pieces of the answer), open (show
        this page), done or error. Never raises for AI trouble: an error event carries the
        sentence to show. `pages`: what the asking page can show ({id: title}); none = no
        open_page tool. `local`: asked on the brain's own computer (visitor mode's tools). `device`:
        the screen that asked: only it shows thinking and speaking (quick job 58)."""
        text = text.strip()
        pages = clean_pages(pages)
        if not text:
            return
        if self.busy:
            yield {"type": "error", "message": "I'm still answering the last question."}
            return
        why = self.paused()
        if why:
            yield {"type": "error", "message": why}
            return
        setup = self.setup()
        self.busy = True
        self.messages.append({"role": "user", "content": text})
        system = self.system_prompt(pages, answer_in)
        sent = [{"role": "system", "content": system}, *self.messages[-MAX_HISTORY:]]
        if clean_language(answer_in):
            # the system prompt alone wasn't enough: a typed Spanish question got a Spanish answer
            # (lab check 9.13). The rule also goes with the question itself (only in what's sent).
            name = LANGUAGES[clean_language(answer_in)]
            sent[-1] = {"role": "user", "content": f"{text}\n\n({ANSWER_IN.format(name=name)})"}
        else:
            earlier = sum(m.get("role") == "user" for m in self.messages[:-1])
            rule = short_question_rule(text, earlier)
            if rule:
                sent[-1] = {"role": "user", "content": f"{text}\n\n({rule})"}
        answer, usage = "", Usage()
        tools = await self.tools.openai_tools() if self.tools else []
        strong = self.strong_setup()
        if strong:
            tools = [*tools, THINK_TOOL]
        if pages:
            tools = [*tools, page_tool(pages)]
        actions = self.actions.tools(local) if self.actions else []
        action_names = {t["function"]["name"] for t in actions}
        tools = [*tools, *actions]
        welcomed = False  # visitor mode started this turn: its answer is the welcome
        error, completed, rounds = None, False, 0
        try:
            self.assistant.set("thinking", device=device)
            yield {"type": "state", "state": "thinking"}
            while True:
                reply = Reply()
                offer = tools if tools and rounds < MAX_TOOL_ROUNDS else None
                try:
                    async for piece in stream_chat(self._session_(), setup, sent, reply, offer):
                        if self.assistant.state != "speaking":
                            self.assistant.set("speaking", 1.0)
                            yield {"type": "state", "state": "speaking"}
                        answer += piece
                        yield {"type": "text", "text": piece}
                finally:
                    usage = usage + reply.usage if reply.usage.tokens_in else usage
                if not reply.tool_calls or not offer:
                    break
                # the model wants to look something up: run the read tools, then ask again
                rounds += 1
                if self.assistant.state != "thinking":
                    self.assistant.set("thinking")
                    yield {"type": "state", "state": "thinking"}
                sent.append(
                    {
                        "role": "assistant",
                        "content": reply.text or None,
                        "tool_calls": [
                            {
                                "id": c.id,
                                "type": "function",
                                "function": {"name": c.name, "arguments": c.arguments or "{}"},
                            }
                            # Gemini refuses the next request without its thought_signature back
                            | ({"extra_content": c.extra} if c.extra else {})
                            for c in reply.tool_calls
                        ],
                    }
                )
                opened = None  # the last page this round opened, if it only opened pages
                only_pages = True
                for call in reply.tool_calls:
                    yield {"type": "tool", "name": call.name}
                    if call.name == THINK and strong:
                        only_pages = False
                        if not answer:  # said at once, while the stronger model thinks
                            answer += THINK_SAY
                            yield {"type": "text", "text": THINK_SAY}
                        result = await self._think_hard(strong, call.arguments)
                    elif call.name == OPEN_PAGE and pages:
                        page = _page_arg(call.arguments, pages)
                        if page:
                            yield {"type": "open", "page": page, "title": pages[page]}
                            opened = page
                            result = f"Opened {pages[page]} on this screen."
                        else:
                            only_pages = False
                            result = f"Error: not a page here (one of: {', '.join(pages)})."
                    elif call.name in action_names:
                        only_pages = False
                        result, events = await self.actions.call(call.name, local, call.arguments)
                        for ev in events:
                            welcomed = welcomed or (ev["type"] == "venue" and ev.get("visitors"))
                            yield ev
                    elif self.tools:
                        only_pages = False
                        result = await self.tools.call(call.name, call.arguments)
                    else:
                        only_pages = False
                        result = f"Error: {call.name!r} isn't a tool you have."
                    sent.append({"role": "tool", "tool_call_id": call.id, "content": result})
                if answer and not answer.endswith(("\n", " ")):
                    answer += "\n"
                    yield {"type": "text", "text": "\n"}
                if opened and only_pages:
                    # nothing left to look up: say so at once instead of asking the model again
                    line = opened_line(opened, pages[opened])
                    answer += line
                    if self.assistant.state != "speaking":
                        self.assistant.set("speaking", 1.0)
                        yield {"type": "state", "state": "speaking"}
                    yield {"type": "text", "text": line}
                    break
            completed = True
        except AiError as e:
            error = str(e)
            self.connected, self.problem = False, error
        finally:
            self.busy = False
            if not completed:
                # unanswered (an error, or the page went away first): don't send it along next time
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()
                if (answer or usage.tokens_in) and not error:  # cut off: it still cost money
                    usage = usage if usage.tokens_in else estimate(sent, answer)
                    cost = setup.cost(usage.tokens_in, usage.tokens_out, usage.tokens_cached)
                    self.spend.write(setup.name, setup.model, usage, cost)
                self._settle()
        if error:
            if usage.tokens_in:  # earlier rounds of this turn were answered and billed
                cost = setup.cost(usage.tokens_in, usage.tokens_out, usage.tokens_cached)
                self.spend.write(setup.name, setup.model, usage, cost)
            yield {"type": "error", "message": error}
            yield {"type": "state", "state": self.assistant.state}
            return
        cost = setup.cost(usage.tokens_in, usage.tokens_out, usage.tokens_cached)
        self.spend.write(setup.name, setup.model, usage, cost)
        log.info(
            "chat: %s/%s, %d tool round(s), %d in (%d cached) + %d out tokens%s = $%.5f",
            setup.name,
            setup.model,
            rounds,
            usage.tokens_in,
            usage.tokens_cached,
            usage.tokens_out,
            " (estimated)" if usage.estimated else "",
            cost,
        )
        self.messages.append({"role": "assistant", "content": answer.strip()})
        if welcomed:
            self.say_next = answer.strip()
        if self.store:
            self.store.save(self.messages)
        self.connected, self.problem = True, None
        self._settle()
        yield {"type": "state", "state": self.assistant.state}
        yield {"type": "done", "setup": setup.name, "cost_usd": round(cost, 6), "tools": rounds}
