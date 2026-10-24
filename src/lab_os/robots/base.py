"""The interface every arm plug-in implements (fake, xArm, SO-101, ...)."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class JointLimit:
    low: float  # degrees
    high: float

    def clamp(self, value: float) -> float:
        return min(max(value, self.low), self.high)


class Arm(Protocol):
    name: str
    joint_names: tuple[str, ...]
    limits: dict[str, JointLimit]

    def connect(self) -> None: ...

    def read_joints(self) -> dict[str, float]:
        """Current joint positions in degrees."""
        ...

    def move_joints(self, targets: dict[str, float], speed_scale: float) -> None:
        """Move toward `targets` (degrees). Implementations clamp to limits and speed_scale ≤ 1."""
        ...

    def stop(self) -> None:
        """Freeze immediately (dead-man rule). Further moves are ignored until `resume()`."""
        ...

    def resume(self) -> None: ...

    def close(self) -> None: ...
