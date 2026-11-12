"""What the AI has cost: one JSON line per chat turn (and per voice turn: seconds heard and spoken)
in <logs>/ai-spend/<YYYY-MM>.jsonl, the month's total,
and the monthly budget (place.yaml → ai_budget_usd_month) that pauses the chat."""

import json
from datetime import datetime
from pathlib import Path

from lab_os import config


class SpendLog:
    def __init__(self, folder: Path | None = None, budget_usd: float | None = None):
        """`folder=None`: the place's logs/ai-spend/. `budget_usd=None`: no cap."""
        self.folder = folder or config.logs_dir() / "ai-spend"
        self.budget_usd = budget_usd

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
            "cost_usd": round(cost_usd, 6),
        }
        self.folder.mkdir(parents=True, exist_ok=True)
        with self._file(now).open("a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def month(self, now: datetime | None = None) -> dict:
        """This month so far: total, per setup, the budget and what's left."""
        entries = self.entries(now)
        by_setup: dict[str, float] = {}
        for e in entries:
            by_setup[e["setup"]] = by_setup.get(e["setup"], 0.0) + float(e["cost_usd"])
        total = sum(by_setup.values())
        return {
            "month": f"{now or datetime.now():%Y-%m}",
            "spent_usd": round(total, 6),
            "budget_usd": self.budget_usd,
            "chats": sum(1 for e in entries if e.get("kind", "chat") == "chat"),
            "voice_minutes": round(
                sum(e.get("heard_s", 0) + e.get("spoken_s", 0) for e in entries) / 60, 2
            ),
            "by_setup": {k: round(v, 6) for k, v in by_setup.items()},
        }

    def over_budget(self, now: datetime | None = None) -> bool:
        return self.budget_usd is not None and self.month(now)["spent_usd"] >= self.budget_usd
