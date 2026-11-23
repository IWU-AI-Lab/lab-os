"""What the AI has cost: one JSON line per chat turn (and per voice turn: seconds heard and spoken)
in <logs>/ai-spend/<YYYY-MM>.jsonl, the month's total,
and the monthly budget (place.yaml → ai_budget_usd_month) that pauses the chat.

Every cost here is an estimate made by this brain (quick job 41): chat = the token counts the
service sends back × the prices typed into models.yaml; voice = the seconds lab-os measured × a
price per minute. Entries that are less exact than that (voice, and chat whose tokens lab-os
counted itself) have `estimated: true`. Another brain that uses the same key keeps its own log, so
it isn't counted here. OpenAI's own costs need an Admin key (docs/guides/hub.md → "AI Spend")."""

import json
import logging
import socket
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from lab_os import config

log = logging.getLogger(__name__)


def short_host(name: str | None = None) -> str:
    """This computer's short name: "Mac", not "Mac.indy.rr.com" (on a home network the long name
    is the internet provider's, and it looked like a website; quick job 82)."""
    name = (name if name is not None else socket.gethostname()).strip()
    return name.split(".", 1)[0] or name or "this computer"


class SpendLog:
    def __init__(
        self,
        folder: Path | None = None,
        budget_usd: float | None = None,
        budget_from: Callable[[], float | None] | None = None,
    ):
        """`folder=None`: the place's logs/ai-spend/. `budget_usd=None`: no cap. `budget_from`:
        read the budget each time it's needed (place.yaml, changed on the Settings page), keeping
        the last good value if that fails."""
        self.folder = folder or config.logs_dir() / "ai-spend"
        self._budget = budget_usd
        self._budget_from = budget_from

    @property
    def budget_usd(self) -> float | None:
        if self._budget_from:
            try:
                self._budget = self._budget_from()
            except Exception as e:  # a half-edited place.yaml: keep the last good number
                log.warning("AI budget: couldn't read it (%s); still $%s", e, self._budget)
        return self._budget

    @budget_usd.setter
    def budget_usd(self, value: float | None) -> None:
        self._budget, self._budget_from = value, None

    def _file(self, now: datetime) -> Path:
        return self.folder / f"{now:%Y-%m}.jsonl"

    def entries(self, now: datetime | None = None) -> list[dict]:
        path = self._file(now or datetime.now())
        if not path.is_file():
            return []
        out = []
        for line in path.read_text().splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # a half-written line (the brain stopped mid-write)
        return out

    def write(self, setup: str, model: str, usage, cost_usd: float, kind: str = "chat") -> dict:
        now = datetime.now()
        entry = {
            "time": now.isoformat(timespec="seconds"),
            "kind": kind,
            "setup": setup,
            "model": model,
            "tokens_in": usage.tokens_in,
            "tokens_cached": usage.tokens_cached,
            "tokens_out": usage.tokens_out,
            "estimated": usage.estimated,
            "cost_usd": round(cost_usd, 6),
        }
        self.folder.mkdir(parents=True, exist_ok=True)
        with self._file(now).open("a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def write_voice(
        self, setup: str, service: str, heard_s: float, spoken_s: float, cost_usd: float, what: str
    ) -> dict:
        """A voice entry: `what` = heard, spoken or greeting; priced per minute of audio."""
        now = datetime.now()
        entry = {
            "time": now.isoformat(timespec="seconds"),
            "kind": "voice",
            "setup": setup,
            "model": service,
            "what": what,
            "heard_s": round(heard_s, 2),
            "spoken_s": round(spoken_s, 2),
            "estimated": True,  # seconds measured here, not what the service billed
            "cost_usd": round(cost_usd, 6),
        }
        self.folder.mkdir(parents=True, exist_ok=True)
        with self._file(now).open("a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def month(self, now: datetime | None = None) -> dict:
        """This month so far: total, per setup, the budget and what's left. `estimated` and
        `counted_on` say what the total is: this brain's own estimate (the pages show both)."""
        entries = self.entries(now)
        by_setup: dict[str, float] = {}
        for e in entries:
            by_setup[e["setup"]] = by_setup.get(e["setup"], 0.0) + float(e["cost_usd"])
        total = sum(by_setup.values())
        less_exact = sum(float(e["cost_usd"]) for e in entries if less_exact_entry(e))
        return {
            "month": f"{now or datetime.now():%Y-%m}",
            "spent_usd": round(total, 6),
            "estimated": True,
            "counted_on": short_host(),
            "less_exact_usd": round(less_exact, 6),
            "budget_usd": self.budget_usd,
            "chats": sum(1 for e in entries if e.get("kind", "chat") == "chat"),
            "voice_minutes": round(
                sum(e.get("heard_s", 0) + e.get("spoken_s", 0) for e in entries) / 60, 2
            ),
            "by_setup": {k: round(v, 6) for k, v in by_setup.items()},
        }

    def over_budget(self, now: datetime | None = None) -> bool:
        budget = self.budget_usd
        return budget is not None and self.month(now)["spent_usd"] >= budget


def less_exact_entry(entry: dict) -> bool:
    """Voice (measured seconds) and chat whose tokens lab-os counted itself. Voice entries written
    before quick job 41 have no `estimated` field."""
    return bool(entry.get("estimated")) or entry.get("kind") == "voice"
