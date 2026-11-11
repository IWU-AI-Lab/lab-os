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
    """Joints use shared names across arms (shoulder_pan, shoulder_lift, elbow_flex, wrist_flex,
    wrist_roll, gripper), in degrees; each driver maps them to its own servos/units."""

    name: str
    model: str  # 3D model for the viewer: "so101", "xarm1s", ... (web/arm/arm-model.js)
    joint_names: tuple[str, ...]
    limits: dict[str, JointLimit]

    def connect(self) -> None: ...

    def read_joints(self) -> dict[str, float]:
        """Current joint positions in degrees."""
        ...

    def move_joints(
        self, targets: dict[str, float], speed_scale: float, deg_per_s: float | None = None
    ) -> None:
        """Move toward `targets` (degrees). Implementations clamp to limits and speed_scale ≤ 1.
        `deg_per_s`: this command's top joint speed instead of the driver's own × speed_scale
        (teleop's 1:1 mode; inf = no cap). A driver may keep a lower hardware cap."""
        ...

    def stop(self) -> None:
        """Freeze immediately (dead-man rule). Further moves are ignored until `resume()`."""
        ...

    def resume(self) -> None: ...

    def close(self) -> None: ...
