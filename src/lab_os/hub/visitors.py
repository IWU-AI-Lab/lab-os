"""Visitors' mode (quick job 35): "Hey Jarvis, say hello to our visitors" on the brain's own screen.

A few fixed phrases are caught before the AI (so they work offline and cost nothing):
- "say hello to our visitors", "demo time", "we have visitors": switch to the place's venue for
  visitors (`visitors: true`, e.g. visit-day: the limits locked, Settings and the AI spend hidden),
  speak a short welcome (what the place is, which robots are really plugged in) and show the
  venue's "try this" cards;
- "wave" (only while visitors are here): the arm plays gestures.yaml's fixed wave;
- "back to normal": the venue the brain started with again.
The switch lasts until "back to normal" or a restart. Only from the brain's own computer (or a
headset on its USB): other screens may be in a hallway.
"""

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from lab_os.devices import Registry
from lab_os.venues import Venue

log = logging.getLogger(__name__)

TO_VISITORS = re.compile(
    r"\b(say (hello|hi) to (our|the) (visitors|guests)|demo time|"
    r"we('ve got| have got| have| got) (some )?(visitors|guests))\b"
)
TO_NORMAL = re.compile(r"\b(back to normal|normal mode)\b")
WAVE = re.compile(r"\bwave\b")

ARM_KINDS = {"so101": "SO-101 arm", "xarm1s": "xArm"}  # robots the welcome names, as said aloud


def heard(text: str) -> str | None:
    """Which fixed phrase this is: "visitors", "normal", "wave", or None (a question for the AI)."""
    t = " ".join(re.sub(r"[^a-z' ]", " ", text.lower().replace("’", "'")).split())
    if TO_VISITORS.search(t):
        return "visitors"
    if TO_NORMAL.search(t):
        return "normal"
    if WAVE.search(t):
        return "wave"
    return None


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


def _and(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def welcome(place: str, about: str, robots: list[str], cards: int) -> str:
    """The short welcome, from real facts only."""
    first = f"Hello, and welcome to the {place}" + (f", {about}." if about else ".")
    if robots:
        verb = "is" if len(robots) == 1 else "are"
        line = f"{_and(robots)[0].upper()}{_and(robots)[1:]} {verb} here today."
    else:
        line = "No robot arm is plugged in right now, but you can still talk to me."
    try_line = " Try one of the cards on the screen." if cards else ""
    return f"{first} {line}{try_line}"


@dataclass
class Handled:
    """A fixed phrase's answer: the line said and shown, and events for the asking page."""

    text: str
    events: list[dict] = field(default_factory=list)


@dataclass
class VisitorDesk:
    """The fixed phrases. `switch(name)` puts the brain in another venue (None = the one it
    started with) and returns it; `venue()` is the venue now; `wave()` checks and starts the
    wave (raises with a sentence if the arm can't); `welcome()` is the welcome's text."""

    venue: Callable[[], Venue]
    visitors_venue: Callable[[], str | None]
    switch: Callable[[str | None], Venue]
    welcome: Callable[[Venue], str]
    wave: Callable[[], Awaitable[None]]
    started_in: str = ""
    to_say: str | None = None  # the last welcome, for a typed turn's page to have it spoken

    def take_say(self) -> str | None:
        """The welcome waiting to be spoken (a typed turn's page asks for it once)."""
        line, self.to_say = self.to_say, None
        return line

    async def handle(self, text: str, local: bool) -> Handled | None:
        what = heard(text)
        now = self.venue()
        if what is None or (what == "wave" and not now.visitors):
            return None  # a question for the AI
        if not local:
            return Handled("Visitors' mode is switched on and off from the brain's own screen.")
        if what == "visitors":
            name = self.visitors_venue()
            if name is None:
                return Handled(
                    "This place has no venue for visitors yet (visitors: true in a venue file)."
                )
            try:
                venue = now if now.name == name else await asyncio.to_thread(self.switch, name)
            except ValueError as e:
                return Handled(str(e))
            line = self.welcome(venue)
            self.to_say = line
            return Handled(line, [{"type": "venue", "venue": venue.name, "visitors": True}])
        if what == "normal":
            if not now.visitors:
                return Handled("We're already in the normal mode.")
            venue = await asyncio.to_thread(self.switch, None)
            return Handled(
                f"Back to normal: the {venue.name} venue again.",
                [{"type": "venue", "venue": venue.name, "visitors": venue.visitors}],
            )
        try:
            await self.wave()
        except ValueError as e:
            return Handled(f"I can't wave right now: {e}")
        return Handled("Hello there!", [{"type": "wave"}])
