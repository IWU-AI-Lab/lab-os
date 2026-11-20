"""Visitor mode (quick job 35): "Hey Jarvis, it's demo time" on the brain's own screen.

The hub's assistant gets three tools, and the AI decides when to use them (no fixed phrases):
- `start_visitor_mode`: when told visitors are here, a demo or tour is starting, guests arrived…
  The brain switches to the place's venue for visitors (`visitors: true`, e.g. visit-day: Settings
  and the AI spend hidden, the "try this" cards shown). The tool returns facts for the welcome (the
  place, what it is, the robot arms really plugged in now); the assistant says it in its own words.
- `exit_visitor_mode`: when told to exit visitor mode, the visitors have left, the demo is over.
  Back to the venue the brain started with.
- `wave` (only while visitors are here): the arm plays gestures.yaml's fixed wave. The AI decides
  to wave; it never chooses the motion.
Only offered to a question asked on the brain's own computer (or a headset on its USB cable):
other screens may be in a hallway. Settings → Visitor mode does the same without asking.
The switch lasts until it's exited or the brain restarts.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from lab_os.devices import Registry
from lab_os.venues import Venue

log = logging.getLogger(__name__)

START, EXIT, WAVE = "start_visitor_mode", "exit_visitor_mode", "wave"
ARM_KINDS = {"so101": "SO-101 arm", "xarm1s": "xArm"}  # robots the welcome names, as said aloud

NO_ARGS = {"type": "object", "properties": {}}
TOOLS = {
    START: "Switch this hub to visitor mode. Use it when someone says visitors or guests are here, "
    "it's demo time, a tour or a demo is starting, or asks you to say hello to the visitors. It "
    "returns facts for your welcome: then welcome them in two or three short sentences (the place, "
    "what it is, the robots that are here if it lists any: only those) and point them to the cards "
    "on the screen, saying what they are.",
    EXIT: "Leave visitor mode: back to the lab's normal mode. Use it when someone asks to exit or "
    "stop visitor mode, says the visitors have left or the demo is over.",
    WAVE: "Wave hello with the robot arm: a fixed, gentle wave (the arm goes to its ready pose "
    "first). Use it when someone asks you or the robot to wave or say hi with the arm.",
}


def tool(name: str) -> dict:
    """A tool in the OpenAI-style format the chat sends."""
    return {
        "type": "function",
        "function": {"name": name, "description": TOOLS[name], "parameters": NO_ARGS},
    }


def spoken_name(name: str, kind: str) -> str:
    """A robot as said aloud: so101-white → "the white SO-101 arm"."""
    label = ARM_KINDS.get(kind, kind)
    rest = name.removeprefix(f"{kind}-")
    return f"the {rest.replace('-', ' ')} {label}" if rest != name else f"the {label} {name}"


def robots_here(
    registry: Registry, driven: str, driven_connected: bool, exists=lambda p: Path(p).exists()
) -> list[str]:
    """The robot arms really plugged in now, by device-list name: the one the brain drives (while
    it's connected) and any other arm whose serial port is there. Leaders, cameras and the
    software arm aren't robots here."""
    out = []
    for d in registry.devices.values():
        if d.kind not in ARM_KINDS:
            continue
        if (d.name == driven and driven_connected) or any(exists(p) for p in d.ports):
            out.append(d.name)
    return out


@dataclass
class VisitorDesk:
    """The visitor-mode tools for the hub's chat. `switch(name)` puts the brain in another venue
    (None = the one it started with) and returns it; `venue()` is the venue now; `facts(venue)` is
    what the welcome may say; `wave()` checks and starts the wave (raises ValueError with a
    sentence if the arm can't)."""

    venue: Callable[[], Venue]
    visitors_venue: Callable[[], str | None]
    switch: Callable[[str | None], Venue]
    facts: Callable[[Venue], dict]
    wave: Callable[[], Awaitable[None]]

    def tools(self, local: bool) -> list[dict]:
        """What the assistant may do now: start visitor mode, or (while it's on) exit it and wave.
        Nothing for a screen other than the brain's own."""
        if not local:
            return []
        if self.venue().visitors:
            return [tool(EXIT), tool(WAVE)]
        return [tool(START)] if self.visitors_venue() else []

    async def call(self, name: str, local: bool, arguments: str = "{}") -> tuple[str, list[dict]]:
        """Run one: (the result for the AI, events for the asking page). The tools take no
        arguments."""
        if not local or name not in TOOLS:
            return f"Error: {name} isn't a tool you have here.", []
        if name == START:
            target = self.visitors_venue()
            if target is None:
                return "Error: this place has no venue for visitors.", []
            now = self.venue()
            try:
                venue = now if now.name == target else await asyncio.to_thread(self.switch, target)
            except ValueError as e:
                return f"Error: visitor mode didn't start: {e}", []
            facts = self.facts(venue) | {"visitor_mode": "on"}
            return json.dumps(facts), [{"type": "venue", "venue": venue.name, "visitors": True}]
        if name == EXIT:
            if not self.venue().visitors:
                return "Visitor mode was already off.", []
            venue = await asyncio.to_thread(self.switch, None)
            return (
                f"Visitor mode is off: the {venue.name} venue again. Say so in a few words.",
                [{"type": "venue", "venue": venue.name, "visitors": venue.visitors}],
            )
        if not self.venue().visitors:
            return "Error: the wave is only for visitor mode.", []
        try:
            await self.wave()
        except ValueError as e:
            return f"Error: the arm can't wave right now: {e} Say so kindly.", []
        return "The arm is waving now (a few seconds). Say hello.", [{"type": "wave"}]
