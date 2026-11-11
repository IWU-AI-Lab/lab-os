"""A log of every AI tool call: time, tool, arguments, outcome (ok / clipped / short / refused /
stopped / error) and the result, one JSON line each, one file per brain run in logs/ai-tools/, so
runs can be compared later."""

import json
import time
from datetime import datetime
from pathlib import Path

from lab_os import REPO_ROOT

LOG_DIR = REPO_ROOT / "logs" / "ai-tools"


class CallLog:
    def __init__(self, path: Path | None = None, keep: int = 200):
        """`path=None`: keep the entries in memory only (tests)."""
        self.path = path
        self.keep = keep
        self.entries: list[dict] = []

    @classmethod
    def for_this_run(cls, folder: Path = LOG_DIR) -> "CallLog":
        return cls(folder / f"{datetime.now():%Y-%m-%d_%H%M%S}.jsonl")

    def write(self, tool: str, args: dict, outcome: str, result) -> dict:
        entry = {
            "time": datetime.now().isoformat(timespec="milliseconds"),
            "t": round(time.time(), 3),
            "tool": tool,
            "args": args,
            "outcome": outcome,
            "result": result,
        }
        self.entries = [*self.entries[-(self.keep - 1) :], entry]
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        return entry
