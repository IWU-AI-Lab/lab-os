"""A software-only arm: same interface as a real one; records every command, moves nothing."""

from dataclasses import dataclass, field

from lab_os.robots.base import JointLimit

SO101_JOINTS = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)


@dataclass
class FakeArm:
    name: str = "fake-arm"
    joint_names: tuple[str, ...] = SO101_JOINTS
    limits: dict[str, JointLimit] = field(
        default_factory=lambda: {j: JointLimit(-90.0, 90.0) for j in SO101_JOINTS}
    )
    connected: bool = False
    stopped: bool = False
    joints: dict[str, float] = field(default_factory=lambda: dict.fromkeys(SO101_JOINTS, 0.0))
    log: list[tuple[str, dict[str, float], float]] = field(default_factory=list)

    def connect(self) -> None:
        self.connected = True

    def read_joints(self) -> dict[str, float]:
        self._require_connected()
        return dict(self.joints)

    def move_joints(self, targets: dict[str, float], speed_scale: float) -> None:
        self._require_connected()
        if self.stopped:
            return
        unknown = set(targets) - set(self.joint_names)
        if unknown:
            raise KeyError(f"unknown joints: {sorted(unknown)}")
        speed_scale = min(max(speed_scale, 0.0), 1.0)
        clamped = {j: self.limits[j].clamp(v) for j, v in targets.items()}
        self.joints.update(clamped)  # the fake arm arrives instantly
        self.log.append(("move", clamped, speed_scale))

    def stop(self) -> None:
        self.stopped = True
        self.log.append(("stop", {}, 0.0))

    def resume(self) -> None:
        self.stopped = False

    def close(self) -> None:
        self.connected = False

    def _require_connected(self) -> None:
        if not self.connected:
            raise RuntimeError(f"{self.name} is not connected")
