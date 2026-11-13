"""The assistant's state (the information layer). The rest of the system sets it; the picture on
the page only reads it (docs/plan/current-focus.md → "How it fits together")."""

from dataclasses import dataclass

ASSISTANT_STATES = ("idle", "listening", "thinking", "speaking", "offline", "error")


@dataclass
class Assistant:
    state: str = "offline"  # offline until an AI setup answers
    loudness: float = 0.0  # 0–1 while speaking

    def set(self, state: str, loudness: float = 0.0) -> None:
        if state not in ASSISTANT_STATES:
            raise ValueError(f"unknown assistant state {state!r}")
        self.state, self.loudness = state, max(0.0, min(1.0, loudness))
