"""What happened in the lab, newest first (quick job 149): for the Command Center's activity list.

A short list in the brain's memory (not kept over a restart): a device connected or went, a screen
opened a page or went back to the hub, STOP was pressed. The places that see the event add one line
in plain words ("Pi 3 opened Teleop", "so101-white connected", "STOP pressed on desk"). A device's
name stays as it is, also at the start of a line.
"""

import time
from collections import deque
from collections.abc import Callable

from aiohttp import web

MAX_EVENTS = 100


class Activity:
    """The newest events first; each `{"t": seconds since 1970, "text": ..., "kind": ...}`.
    `kind`: `device` (connected or went), `page` (a screen opened or closed a page), `stop`."""

    def __init__(self, clock: Callable[[], float] = time.time, size: int = MAX_EVENTS):
        self.clock = clock
        self.events: deque[dict] = deque(maxlen=size)

    def add(self, text: str, kind: str = "device") -> None:
        text = " ".join(str(text).split())[:160]
        if text:
            self.events.appendleft({"t": round(self.clock(), 1), "text": text, "kind": kind})

    def recent(self, n: int = 50) -> list[dict]:
        return list(self.events)[:n]


ACTIVITY = web.AppKey("activity", Activity)


def note(app: web.Application, text: str, kind: str = "device") -> None:
    """Add an event, when the app keeps an activity list (the teleop server on its own does not)."""
    if ACTIVITY in app:
        app[ACTIVITY].add(text, kind)
