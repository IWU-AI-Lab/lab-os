"""The conversation manager: owns the hub chat's turn and sets the assistant's state.

One turn at a time: `ask()` sets `thinking`, streams the answer (`speaking` from the first words),
logs what it cost, and goes back to `idle`. It refuses with a full sentence when no AI setup is
usable or this month's budget is used up. With `tools` (the brain's MCP read tools: the docs,
git, devices; lab_os.ai.tools) the model may look things up first, up to MAX_TOOL_ROUNDS times.
The hub's chat only reads and answers (rule 5): it gets no tools that change anything.
"""

import logging
from collections.abc import AsyncIterator, Callable
from datetime import datetime

import aiohttp

from lab_os.ai.assistant import Assistant
from lab_os.ai.client import AiError, Reply, Usage, check, estimate, stream_chat
from lab_os.ai.models import NoSetup, Setup, load_setups, pick
from lab_os.ai.spend import SpendLog
from lab_os.ai.tools import ChatTools
from lab_os.personas import Persona

log = logging.getLogger(__name__)

MAX_HISTORY = 20  # messages sent along with a question (older ones are left out: cost)
MAX_TOOL_ROUNDS = 4  # look-ups per question before the model must answer

RULES = """\
You are the assistant on the hub screen of {place}. It is {now}.
You answer questions. From this screen you can't change or move anything.
Answer in plain text without markdown, in one to four short sentences unless asked for more."""

TOOL_RULES = """\
You can look things up with read tools: the project's docs (start with project_status for "what's
next?"; ideas has what's on hold), its git history, and the device list. Use them instead of
guessing, and say where an answer came from in a few words.
When someone wants to work on something, draft a prompt they can paste into a Claude Code or Codex
session in the lab-os repository: what to read first (CLAUDE.md, docs/current-focus.md), the goal,
the step and its "done when", anything to watch out for. Put it after a line "Prompt:" in plain
text; it may be longer than your usual answers."""


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
    ):
        """`persona`: read before every turn, so a venue or persona edit applies without a restart;
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
        self.messages: list[dict] = []  # what's on screen: {"role": "user"|"assistant", ...}
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
        self._refresh()
        now = datetime.now().strftime("%A %Y-%m-%d, %H:%M")
        rules = RULES.format(place=self.place_name or "this place", now=now)
        if self.display_name:
            rules = f"Your name on the screen is {self.display_name}.\n{rules}"
        if self.tools:
            rules = f"{rules}\n\n{TOOL_RULES}"
        return f"{self.personality}\n\n{rules}" if self.personality else rules

    def clear(self, opening: str | None = None) -> None:
        """Forget the conversation (the hub's reset: the next visitor starts fresh). `opening`:
        the assistant's first message (the greeting), sent along with later questions."""
        if not self.busy:
            self.messages = [{"role": "assistant", "content": opening}] if opening else []

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
        answer, usage = "", Usage()
        tools = await self.tools.openai_tools() if self.tools else None
        error, completed, rounds = None, False, 0
        try:
            self.assistant.set("thinking")
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
                for call in reply.tool_calls:
                    yield {"type": "tool", "name": call.name}
                    result = await self.tools.call(call.name, call.arguments)
                    sent.append({"role": "tool", "tool_call_id": call.id, "content": result})
                if answer and not answer.endswith(("\n", " ")):
                    answer += "\n"
                    yield {"type": "text", "text": "\n"}
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
        self.connected, self.problem = True, None
        self._settle()
        yield {"type": "state", "state": self.assistant.state}
        yield {"type": "done", "setup": setup.name, "cost_usd": round(cost, 6), "tools": rounds}
