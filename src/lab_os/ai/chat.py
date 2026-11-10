"""The conversation manager: owns the hub chat's turn and sets the assistant's state.

One turn at a time: `ask()` sets `thinking`, streams the answer (`speaking` from the first words),
logs what it cost, and goes back to `idle`. It refuses with a full sentence when no AI setup is
usable or this month's budget is used up. The hub's chat only reads and answers (rule 5): it gets
no tools that change anything.
"""

import logging
from collections.abc import AsyncIterator, Callable
from datetime import datetime

import aiohttp

from lab_os.ai.assistant import Assistant
from lab_os.ai.client import AiError, Reply, check, estimate, stream_chat
from lab_os.ai.models import NoSetup, Setup, load_setups, pick
from lab_os.ai.spend import SpendLog

log = logging.getLogger(__name__)

MAX_HISTORY = 20  # messages sent along with a question (older ones are left out: cost)

RULES = """\
You are the assistant on the hub screen of {place}. It is {now}.
You answer questions. From this screen you can't change or move anything.
Answer in plain text without markdown, in one to four short sentences unless asked for more."""


class Conversation:
    def __init__(
        self,
        assistant: Assistant,
        spend: SpendLog,
        setup_name: str = "main",
        personality: str = "",
        place_name: str = "",
        setups: Callable[[], dict[str, Setup]] = load_setups,
    ):
        self.assistant = assistant
        self.spend = spend
        self.setup_name = setup_name
        self.personality = personality.strip()
        self.place_name = place_name
        self._setups = setups
        self.messages: list[dict] = []  # what's on screen: {"role": "user"|"assistant", ...}
        self.busy = False
        self.connected: bool | None = None  # None = not checked yet
        self.problem: str | None = None  # the last failure, as a sentence
        self._session: aiohttp.ClientSession | None = None

    # ---------- setup and status ----------

    def setup(self) -> Setup:
        """The setup that would answer now (follows `fallback` when a key is missing)."""
        return pick(self.setup_name, self._setups())

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

    async def close(self) -> None:
        if self._session:
            await self._session.close()

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
        if internet is False and not setup.local:
            self.connected = False
        else:
            self.connected = await check(self._session_(), setup)
            if self.connected:
                self.problem = None
        self._settle()
        return self.connected

    # ---------- a turn ----------

    def system_prompt(self) -> str:
        now = datetime.now().strftime("%A %Y-%m-%d, %H:%M")
        rules = RULES.format(place=self.place_name or "this place", now=now)
        return f"{self.personality}\n\n{rules}" if self.personality else rules

    def clear(self) -> None:
        """Forget the conversation (the hub's reset: the next visitor starts fresh)."""
        if not self.busy:
            self.messages = []

    async def ask(self, text: str) -> AsyncIterator[dict]:
        """One turn. Yields events for the page: state, text (pieces of the answer), done or
        error. Never raises for AI trouble: an error event carries the sentence to show."""
        text = text.strip()
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
        sent = [{"role": "system", "content": self.system_prompt()}, *self.messages[-MAX_HISTORY:]]
        reply = Reply()
        error, completed = None, False
        try:
            self.assistant.set("thinking")
            yield {"type": "state", "state": "thinking"}
            async for piece in stream_chat(self._session_(), setup, sent, reply):
                if self.assistant.state != "speaking":
                    self.assistant.set("speaking", 1.0)
                    yield {"type": "state", "state": "speaking"}
                yield {"type": "text", "text": piece}
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
                if reply.text and not error:  # cut off: what was generated still cost money
                    usage = estimate(sent, reply.text)
                    cost = setup.cost(usage.tokens_in, usage.tokens_out)
                    self.spend.write(setup.name, setup.model, usage, cost)
                self._settle()
        if error:
            yield {"type": "error", "message": error}
            yield {"type": "state", "state": self.assistant.state}
            return
        cost = setup.cost(reply.usage.tokens_in, reply.usage.tokens_out, reply.usage.tokens_cached)
        self.spend.write(setup.name, setup.model, reply.usage, cost)
        log.info(
            "chat: %s/%s, %d in (%d cached) + %d out tokens%s = $%.5f",
            setup.name,
            setup.model,
            reply.usage.tokens_in,
            reply.usage.tokens_cached,
            reply.usage.tokens_out,
            " (estimated)" if reply.usage.estimated else "",
            cost,
        )
        self.messages.append({"role": "assistant", "content": reply.text})
        self.connected, self.problem = True, None
        self._settle()
        yield {"type": "state", "state": self.assistant.state}
        yield {"type": "done", "setup": setup.name, "cost_usd": round(cost, 6)}
