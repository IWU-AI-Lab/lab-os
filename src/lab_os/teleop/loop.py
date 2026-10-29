"""The fixed-rate teleop loop: latest input → mapper → arm, plus the dead-man rule.

Pose input (XRFrame: Quest, glove, ...) goes through the ClutchMapper (IK when the arm has
kinematics); joint input (JointFrame: keyboard/mouse jogging) goes through the JogMapper. Switching
between the two resets both, so nothing carries over.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from lab_os.robots.base import Arm
from lab_os.teleop.jog import JogMapper
from lab_os.teleop.mapping import ClutchMapper
from lab_os.teleop.messages import JointFrame, XRFrame

log = logging.getLogger(__name__)


@dataclass
class InputState:
    """Written by the WebSocket handler (or a replay), read by the loop."""

    latest: XRFrame | JointFrame | None = None
    received_at: float = 0.0  # monotonic seconds
    connected: bool = False

    def update(self, frame: XRFrame | JointFrame, now: float | None = None) -> None:
        self.latest = frame
        self.received_at = time.monotonic() if now is None else now
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False


@dataclass
class TeleopLoop:
    arm: Arm
    inputs: InputState
    mapper: ClutchMapper = field(default_factory=ClutchMapper)
    jog: JogMapper = field(default_factory=JogMapper)
    speed_scale: float = 0.5
    rate_hz: float = 50.0
    stale_after: float = 0.25  # seconds without input → freeze (dead-man)
    frozen: bool = False
    on_tick: Callable[["TeleopLoop"], None] | None = None
    # Called with every arm_command / arm_stop / arm_resume message: exactly what the driver got.
    on_command: Callable[[dict], None] | None = None
    command_seq: int = 0
    last_command: dict | None = None
    input_kind: str | None = None  # "pose" / "joints": which mapper the latest input used

    def _emit(self, msg: dict) -> None:
        self.command_seq += 1
        msg = {"seq": self.command_seq, "device": self.arm.name} | msg
        if msg["type"] == "arm_command":
            self.last_command = msg
        if self.on_command:
            self.on_command(msg)

    def _freeze(self) -> None:
        if not self.frozen:
            self.arm.stop()
            self.frozen = True
            self._emit({"type": "arm_stop"})
        self.mapper.reset(require_release=True)
        self.jog.reset(require_release=True)

    def stop(self) -> None:
        """STOP button on any page: freeze now; the driver must release and re-grab the clutch."""
        self._freeze()

    def step(self, now: float, dt: float) -> None:
        live = self.inputs.connected and now - self.inputs.received_at <= self.stale_after
        frame = self.inputs.latest
        kind = "joints" if isinstance(frame, JointFrame) else "pose"
        stop_pressed = isinstance(frame, XRFrame) and any(
            c.buttons.get("a") for c in frame.hands.values()
        )
        if not live or frame is None or stop_pressed:
            self._freeze()
            return
        if kind != self.input_kind:
            if self.input_kind is not None:
                self._freeze()  # another kind of input took over: start clean
            self.input_kind = kind

        if kind == "joints":
            targets = self.jog.step(
                frame.rates, self.arm.read_joints(), dt, self.speed_scale, self.arm.limits
            )
        else:
            controller = frame.hands.get(self.mapper.config.hand)
            targets = self.mapper.step(
                controller, self.arm.read_joints(), dt, self.speed_scale, self.arm.limits
            )
        if targets is None:
            return
        if self.frozen:
            self.arm.resume()
            self.frozen = False
            self._emit({"type": "arm_resume"})
        self.arm.move_joints(targets, self.speed_scale)
        self._emit(
            {
                "type": "arm_command",
                "joints": dict(targets),
                "speed_scale": self.speed_scale,
                # What the driver accepted (or reports) right after, so viewers can spot clamping.
                # Drivers that lag (xArm) say what they accepted; others report their state.
                "driver_joints": getattr(self.arm, "commanded_joints", self.arm.read_joints)(),
            }
        )

    def status(self) -> dict:
        """What the overlay / monitor shows (sent as a `status` message)."""
        joints = self.arm.read_joints()
        return {
            "type": "status",
            "connected": self.inputs.connected,
            "frozen": self.frozen,
            "clutch": self.mapper.engaged or self.jog.active,
            "needs_release": self.mapper.needs_release or self.jog.needs_release,
            "input_kind": self.input_kind,
            "speed_scale": self.speed_scale,
            "arm": {"name": self.arm.name, "model": getattr(self.arm, "model", "unknown")},
            "joints": joints,
            "last_command": self.last_command,
            "limits": {j: [lim.low, lim.high] for j, lim in self.arm.limits.items()},
        }

    async def run(self) -> None:
        period = 1.0 / self.rate_hz
        last = time.monotonic()
        while True:
            await asyncio.sleep(period)
            now = time.monotonic()
            try:
                self.step(now, now - last)
            except Exception:
                # E.g. the arm stopped answering. Freeze and keep running: a dead loop task would
                # leave every page "connected" but unable to move anything, with no message.
                log.exception("teleop step failed; arm frozen")
                self._freeze()
            last = now
            if self.on_tick:
                try:
                    self.on_tick(self)
                except Exception:  # a display bug must never stop the arm loop
                    log.exception("on_tick failed")
