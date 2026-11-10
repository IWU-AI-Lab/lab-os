"""Keeps the hub's conversation for a short while, so an accidental reset, a closed page or a
restart doesn't lose what someone was working on.

Two files in the place's logs folder (`logs/chat/`): `current.json` (saved after every answer;
read back when the brain starts) and `previous.json` (the conversation a reset or the start press
put aside; "Bring back" on the hub swaps it in). Both are deleted once they're older than the
place's `chat_keep_minutes` (30 by default, 0 = keep nothing): on a public screen the next visitor
shouldn't find them for long. A conversation without a question (only the greeting) never
replaces a kept one.
"""

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path

from lab_os import config

log = logging.getLogger(__name__)

KEEP_MINUTES = 30.0


def has_question(messages: list[dict]) -> bool:
    return any(m.get("role") == "user" for m in messages)


class ChatStore:
    def __init__(
        self,
        folder: Path | None = None,
        keep_minutes: float = KEEP_MINUTES,
        clock: Callable[[], float] = time.time,
    ):
        self.folder = folder or config.logs_dir() / "chat"
        self.keep_s = keep_minutes * 60
        self.clock = clock

    def _path(self, name: str) -> Path:
        return self.folder / f"{name}.json"

    def _read(self, name: str) -> dict | None:
        path = self._path(name)
        try:
            data = json.loads(path.read_text())
            fresh = self.clock() - float(data["saved_at"]) <= self.keep_s
            if fresh and isinstance(data.get("messages"), list):
                return data
        except FileNotFoundError:
            return None
        except (OSError, ValueError, KeyError, TypeError) as e:
            log.warning("chat history %s unreadable (%s); dropped", path, e)
        path.unlink(missing_ok=True)  # too old (or broken): gone
        return None

    def _write(self, name: str, messages: list[dict], saved_at: float | None = None) -> None:
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            tmp = self._path(name).with_suffix(".tmp")
            data = {"saved_at": saved_at or self.clock(), "messages": messages}
            tmp.write_text(json.dumps(data, ensure_ascii=False))
            tmp.replace(self._path(name))  # never half a file, even if the power goes
        except OSError as e:
            log.warning("chat history not saved (%s)", e)

    def save(self, messages: list[dict]) -> None:
        """The conversation as it is now."""
        self._write("current", messages)

    def load(self) -> list[dict]:
        """The conversation saved last, if it's recent enough (after a restart)."""
        data = self._read("current")
        return data["messages"] if data else []

    def put_aside(self, messages: list[dict]) -> None:
        """Keep `messages` as the one to bring back (only if there's a question in it)."""
        if has_question(messages):
            self._write("previous", messages)

    def previous(self) -> dict | None:
        """{"questions": n, "saved_at": epoch seconds} of the conversation put aside, or None."""
        data = self._read("previous")
        if not data:
            return None
        questions = sum(m.get("role") == "user" for m in data["messages"])
        return {"questions": questions, "saved_at": data["saved_at"]}

    def take_previous(self) -> list[dict] | None:
        data = self._read("previous")
        self._path("previous").unlink(missing_ok=True)
        return data["messages"] if data else None

    def forget(self) -> None:
        for name in ("current", "previous"):
            self._path(name).unlink(missing_ok=True)
