"""The assistant's state (the information layer). The rest of the system sets it; the picture on
the page only reads it (docs/plan/log.md → "How it fits together")."""

from dataclasses import dataclass

ASSISTANT_STATES = ("idle", "listening", "thinking", "speaking", "offline", "error")
# a conversation's states: only the screen that has it shows them (quick job 58)
TALK_STATES = ("listening", "thinking", "speaking")


@dataclass
class Assistant:
    state: str = "offline"  # offline until an AI setup answers
    loudness: float = 0.0  # 0–1 while speaking
    device: str = ""  # the screen that has the conversation ("" = not named, or none)

    def set(self, state: str, loudness: float = 0.0, device: str | None = None) -> None:
        """`device`: the screen that listens, thinks or speaks (None keeps the one before)."""
        if state not in ASSISTANT_STATES:
            raise ValueError(f"unknown assistant state {state!r}")
        self.state, self.loudness = state, max(0.0, min(1.0, loudness))
        if state not in TALK_STATES:
            self.device = ""
        elif device is not None:
            self.device = device
