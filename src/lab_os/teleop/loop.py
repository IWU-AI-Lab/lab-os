"""The fixed-rate teleop loop: latest input → mapper → arm, plus the dead-man rule.

Pose input (XRFrame: Quest, glove, ...) goes through the ClutchMapper (IK when the arm has
kinematics); joint input (JointFrame: keyboard/mouse jogging) goes through the JogMapper. Switching
between the two resets both, so nothing carries over.

A third source: a `Motion` from the AI tools (lab_os.tools.robot): joint waypoints followed at a
capped speed. While one runs, the AI tools have control and teleop input is refused (the server
checks `motion_active`); STOP, like every freeze, ends it.

The arm's USB (quick job 27): for drivers that can tell (`port_present()`), the loop checks every
`link_check_s` that the port is still there. When it goes: freeze, end any move, let go of the
port without writing (`drop()`), and say so in `status`; teleop input is ignored. When it comes
back under the same /dev/serial/by-id/ name: `connect()` again, the same checks and the same
"goals = where the motors are, then torque" as at startup (a borrowed arm that LeLab took in the
meantime is refused, and tried again later). The clutch must be released and grabbed again.

Two arms at once (preview 3, 2026-11-19): `left` is a second loop for a second arm, driven by the
left controller (its mapper's `hand`), while this one follows the right. Both read the same
`InputState`, so the dead-man rule, one input page at a time and A/X freeze both. STOP, the speed
and a venue's caps and the mode (relative or 1:1) are passed on to it. The left arm is pose input
only (the Quest page measures the left hand from the left 3D arm, so 1:1 works for it too);
jogging and the AI tools drive only this loop's arm. Its `arm_*` messages carry its own `device`
(the pages' ArmFeed tells the two arms apart by it); its state is the `left_arm` part of `status`.

Shutting down (quick job 44): `shut_down()` freezes both arms and, from then on, nothing moves
until the program ends: no AI move starts, teleop and jogging input is ignored, and the USB is not
checked again (a reconnect would switch the torque on). `lab-os serve`'s cleanup then lets go.
"""

import asyncio
import json
import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from lab_os.robots.base import Arm
from lab_os.teleop.jog import JogMapper
from lab_os.teleop.mapping import MODES, ClutchMapper
from lab_os.teleop.messages import JointFrame, XRFrame

log = logging.getLogger(__name__)

# A servo this warm (°C) slows teleop's 1:1 mode down to relative speed. The STS3215 protects
# itself at its Max_Temperature_Limit (70 °C by default); this keeps well below it. A guess, not
# measured: the logs (logs/servo-health/) will tell what 1:1 really does.
HOT_C = 60.0


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
class Motion:
    """A move asked for by the AI tools: joint waypoints, followed one after another so that all
    joints arrive together, the furthest one moving at `deg_per_s` × the loop's speed scale."""

    path: list[dict[str, float]]
    deg_per_s: float = 60.0
    hold_s: float = 0.0  # after the last waypoint, keep sending it this long (servos catch up)
    result: str | None = None  # "arrived" / "stopped" once finished
    done: asyncio.Event = field(default_factory=asyncio.Event)
    _index: int = 0
    _held_s: float = 0.0
    _commanded: dict[str, float] = field(default_factory=dict)

    def finish(self, result: str) -> None:
        if self.result is None:
            self.result = result
            self.done.set()


@dataclass
class TeleopLoop:
    arm: Arm
    inputs: InputState
    mapper: ClutchMapper = field(default_factory=ClutchMapper)
    jog: JogMapper = field(default_factory=JogMapper)
    speed_scale: float = 0.5
    max_speed_scale: float = 1.0  # the venue's cap: set_speed never goes above it
    rate_hz: float = 50.0
    stale_after: float = 0.25  # seconds without input → freeze (dead-man)
    frozen: bool = False
    on_tick: Callable[["TeleopLoop"], None] | None = None
    # Called with every arm_command / arm_stop / arm_resume message: exactly what the driver got.
    on_command: Callable[[dict], None] | None = None
    command_seq: int = 0
    last_command: dict | None = None
    input_kind: str | None = None  # "pose" / "joints": which mapper the latest input used
    motion: Motion | None = None  # the AI tools' move in progress, if any
    # teleop's 1:1 mode: the venue's top joint speed (°/s; 0 = no 1:1 here, inf = no cap). Not
    # scaled by speed_scale: 1:1 is about keeping up with the hand.
    one_to_one_deg_per_s: float = 0.0
    # Servo health (drivers with read_health: temperature, load, voltage), read every few seconds
    # and logged, to see what 1:1 does to the motors. Hot servos slow 1:1 down to relative speed.
    health: dict | None = None
    health_ok: bool | None = None  # the last health read: answered (True), failed (False), not yet
    health_every_s: float = 5.0
    health_log: Path | None = None
    _health_t: float = 0.0
    # The arm's USB link (quick job 27): checked every link_check_s, reconnect tried every
    # reconnect_s while it's gone.
    arm_connected: bool = True
    arm_problem: str | None = None  # why it's disconnected, or why reconnecting was refused
    link_check_s: float = 0.5
    reconnect_s: float = 1.0
    _link_t: float = 0.0
    _last_joints: dict[str, float] = field(default_factory=dict)
    # Two arms at once (see the module docstring): the left controller's arm, and on that loop,
    # True (pose input only).
    left: "TeleopLoop | None" = None
    is_left: bool = False
    last_command_t: float = -1e9  # monotonic time of the last arm_command (quick job 73)
    # lab-os is shutting down or restarting (why), or None: nothing moves any more (quick job 44)
    shutting_down: str | None = None
    stops: int = 0  # how many times STOP was pressed: a running AI program ends on a new one (81)

    def _emit(self, msg: dict) -> None:
        self.command_seq += 1
        msg = {"seq": self.command_seq, "device": self.arm.name} | msg
        if msg["type"] == "arm_command":
            self.last_command = msg
            self.last_command_t = time.monotonic()
        if self.on_command:
            self.on_command(msg)

    @property
    def motion_active(self) -> bool:
        return self.motion is not None

    def start_motion(self, motion: Motion) -> None:
        """Run an AI move (the caller checked that nobody else has control)."""
        if self.shutting_down:
            raise RuntimeError(self.shutting_down)
        if not self.arm_connected:
            raise RuntimeError(f"{self.arm.name} is disconnected")
        if self.motion is not None:
            raise RuntimeError("another move is running")
        motion._commanded = self.arm.read_joints()
        self.motion = motion

    def _freeze(self, why: str = "stopped") -> None:
        if self.motion is not None:
            self.motion.finish(why)
            self.motion = None
        if not self.frozen:
            if self.arm_connected:
                try:
                    self.arm.stop()
                except Exception as e:  # e.g. the USB just went: the freeze itself must not fail
                    log.warning("%s: stop failed: %s", self.arm.name, e)
            self.frozen = True
            self._emit({"type": "arm_stop"})
        self.mapper.reset(require_release=True)
        self.jog.reset(require_release=True)

    def set_speed(self, scale: float) -> float:
        """The teleop page's speed control: 5 % up to the venue's cap. Returns what was set.
        The left arm (two arms at once) gets the same speed."""
        self.speed_scale = round(min(max(scale, 0.05), self.max_speed_scale), 3)
        if self.left:
            self.left.set_speed(scale)
        return self.speed_scale

    def use_caps(
        self, max_speed_scale: float, speed_scale: float, one_to_one_deg_per_s: float
    ) -> None:
        """Another venue's caps while running (the hub's visitor mode, quick job 35): its top
        speed, its starting speed and 1:1's top speed (0 = no 1:1: back to relative). The
        clutch drops, so the next grab starts under the new caps."""
        self.max_speed_scale = max_speed_scale
        self.speed_scale = round(min(max(speed_scale, 0.05), max_speed_scale), 3)
        self.one_to_one_deg_per_s = one_to_one_deg_per_s
        if self.mapper.config.mode not in self.modes():
            self.mapper.config.mode = "relative"
        self.mapper.reset(require_release=True)
        self.jog.reset(require_release=True)
        if self.left:
            self.left.use_caps(max_speed_scale, speed_scale, one_to_one_deg_per_s)

    def set_mode(self, mode: str) -> str:
        """The teleop page's mode: "relative" or "one_to_one" (1:1). A change drops the clutch:
        grip again (released first) to move in the new mode. Returns what was set."""
        if mode not in MODES:
            raise ValueError(f"mode: expected one of {MODES}, got {mode!r}")
        if mode == "one_to_one" and mode not in self.modes():
            raise ValueError("1:1 isn't available here (the venue has it off, or no kinematics)")
        if mode != self.mapper.config.mode:
            self.mapper.config.mode = mode
            self.mapper.reset(require_release=True)
        if self.left and mode in self.left.modes():  # two arms: the same mode for both
            self.left.set_mode(mode)
        return mode

    def _follows_fast(self) -> bool:
        """The venue's follow speed applies: kinematics and 1:1 not switched off."""
        return self.mapper.kinematics is not None and self.one_to_one_deg_per_s > 0

    def modes(self) -> list[str]:
        """1:1 where the venue and kinematics allow it."""
        return list(MODES) if self._follows_fast() else ["relative"]

    @property
    def servos_hot(self) -> bool:
        return bool(self.health) and max(h["temp_c"] for h in self.health.values()) >= HOT_C

    def one_to_one_cap(self) -> float:
        """The top joint speed for a 1:1 grab now: the venue's, or relative speed when hot."""
        if self.servos_hot:
            return min(self.one_to_one_deg_per_s, self.mapper.config.max_deg_per_s)
        return self.one_to_one_deg_per_s

    def relative_cap(self) -> float | None:
        """The top joint speed for a relative grab: the 1:1 follow speed scaled by the speed
        control (its top = the follow speed; half way = half). None where 1:1 isn't available
        (visit days, no kinematics): then the old `max_deg_per_s` × speed (decision 2026-11-16:
        the old 45°/s left the arm far behind the hand)."""
        if not self._follows_fast():
            return None
        share = self.speed_scale / self.max_speed_scale if self.max_speed_scale > 0 else 1.0
        return self.one_to_one_cap() * min(max(share, 0.0), 1.0)

    def check_health(self, now: float) -> None:
        """Every health_every_s: read the servos (if the driver can) and log it."""
        read = getattr(self.arm, "read_health", None)
        if read is None or not self.arm_connected or now - self._health_t < self.health_every_s:
            return
        self._health_t = now
        try:
            self.health = read()
        except Exception as e:  # a dropped packet: keep the last reading
            log.warning("servo health read failed: %s", e)
            self.health_ok = False  # the live device list: the motors don't answer
            return
        self.health_ok = True
        if self.health_log:
            entry = {
                "time": datetime.now().isoformat(timespec="seconds"),
                "mode": self.mapper.config.mode,
                "following_1to1": self.mapper.absolute and self.mapper.engaged,
                "speed_scale": self.speed_scale,
                "servos": self.health,
            }
            self.health_log.parent.mkdir(parents=True, exist_ok=True)
            with self.health_log.open("a") as f:
                f.write(json.dumps(entry) + "\n")

    def stop(self, why: str = "stopped") -> None:
        """STOP button on any page: freeze now; the driver must release and re-grab the clutch.
        `why`: what an AI move that was running is told. The left arm freezes too."""
        self.stops += 1
        self._freeze(why)
        if self.left:
            self.left.stop(why)

    def shut_down(self, why: str) -> None:
        """lab-os is shutting down (or restarting): freeze both arms now, and refuse every move
        from here on, whoever asks (see the module docstring). `why`: what a running AI move and
        any later one are told."""
        self.shutting_down = why
        self._freeze(why)
        if self.left:
            self.left.shut_down(why)

    def check_link(self, now: float, force: bool = False) -> None:
        """Is the arm's USB still there; is it back? (drivers with `port_present`, see above)
        `force`: check now (a step just failed), not only every link_check_s. Not while shutting
        down: a reconnect switches the torque on."""
        present = getattr(self.arm, "port_present", None)
        if present is None or self.shutting_down:
            return
        wait = self.link_check_s if self.arm_connected else self.reconnect_s
        if not force and now - self._link_t < wait:
            return
        self._link_t = now
        if self.arm_connected:
            if not present():
                self._lose_arm("its USB was unplugged")
        elif present():
            self._reconnect_arm()

    def _lose_arm(self, why: str) -> None:
        self.arm_connected = False  # first: nothing is written to a port that's gone
        self.arm_problem = why
        self._freeze("disconnected")
        try:
            getattr(self.arm, "drop", self.arm.close)()  # the port without writing: it's gone
        except Exception as e:
            log.warning("%s: letting go of the port: %s", self.arm.name, e)
        log.warning("%s disconnected (%s); reconnecting when it's back", self.arm.name, why)

    def _reconnect_arm(self) -> None:
        try:
            self.arm.connect()  # the startup's checks: by-id name, board, nobody else has it
        except Exception as e:
            problem = f"plugged back in, but not reopened: {e}"
            if problem != self.arm_problem:  # once per reason, not every second
                log.warning("%s: %s", self.arm.name, problem)
            self.arm_problem = problem
            return
        self.arm_connected = True
        self.arm_problem = None
        self.frozen = True  # held where it is; input starts it again (after a release)
        self.mapper.reset(require_release=True)
        self.jog.reset(require_release=True)
        self.health, self.health_ok = None, None
        log.info("%s reconnected", self.arm.name)

    def adopt(self, other: "TeleopLoop") -> Arm:
        """Drive `other`'s arm from now on, with its mapper (its floor, its kinematics) and its
        health log: an arm plugged in after the brain started on the fake arm (quick job 73).
        Held where it is until input starts it (after a release), as after a reconnect. Returns
        the arm it drove before (the caller closes it)."""
        old = self.arm
        self._freeze("stopped")
        self.arm, self.mapper, self.health_log = other.arm, other.mapper, other.health_log
        self.arm_connected, self.arm_problem, self.health = True, None, None
        self.health_ok = None
        self.frozen = True
        self.input_kind = None
        self._last_joints = {}
        self.mapper.reset(require_release=True)
        self.jog.reset(require_release=True)
        log.info(
            "now driving %s (plugged in after the start), instead of %s", self.arm.name, old.name
        )
        return old

    def _step_motion(self, dt: float) -> None:
        m = self.motion
        budget = m.deg_per_s * min(max(self.speed_scale, 0.0), 1.0) * dt
        while budget > 0 and m._index < len(m.path):
            target = m.path[m._index]
            remaining = {j: v - m._commanded[j] for j, v in target.items()}
            far = max((abs(d) for d in remaining.values()), default=0.0)
            if far <= budget:
                m._commanded.update(target)
                m._index += 1
                budget -= far
            else:
                k = budget / far
                for j, d in remaining.items():
                    m._commanded[j] += d * k
                budget = 0.0
        if self.frozen:
            self.arm.resume()
            self.frozen = False
            self._emit({"type": "arm_resume"})
        moving = {j for wp in m.path for j in wp}
        targets = {j: m._commanded[j] for j in moving}
        self.arm.move_joints(targets, self.speed_scale)
        self._emit(
            {
                "type": "arm_command",
                "joints": dict(targets),
                "speed_scale": self.speed_scale,
                "driver_joints": getattr(self.arm, "commanded_joints", self.arm.read_joints)(),
            }
        )
        if m._index >= len(m.path):
            # Hold the last waypoint a little longer before the freeze: a freeze holds where the
            # motors ARE, so a joint still trailing (load) would be locked short (GOTCHAS).
            if m._held_s < m.hold_s:
                m._held_s += dt
                return
            m.finish("arrived")
            self.motion = None  # the next tick has no input: freeze = hold here

    def step(self, now: float, dt: float) -> None:
        if self.shutting_down:
            return  # frozen by shut_down(); nothing may move again (quick job 44)
        if not self.arm_connected:
            return  # nothing to drive; check_link reconnects
        if self.motion is not None:
            self._step_motion(dt)
            return
        live = self.inputs.connected and now - self.inputs.received_at <= self.stale_after
        frame = self.inputs.latest
        kind = "joints" if isinstance(frame, JointFrame) else "pose"
        stop_pressed = isinstance(frame, XRFrame) and any(
            c.buttons.get("a") for c in frame.hands.values()
        )
        if not live or frame is None or stop_pressed or (self.is_left and kind == "joints"):
            self._freeze()  # the left arm: jogging is for the right arm only
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
                controller,
                self.arm.read_joints(),
                dt,
                self.speed_scale,
                self.arm.limits,
                arm_frame=frame.arm_frame,
                one_to_one_deg_per_s=self.one_to_one_cap()
                if "one_to_one" in self.modes()
                else None,
                relative_deg_per_s=self.relative_cap(),
            )
        if targets is None:
            return
        if self.frozen:
            self.arm.resume()
            self.frozen = False
            self._emit({"type": "arm_resume"})
        relative = self.relative_cap()
        if self.mapper.absolute and self.mapper.engaged and kind == "pose":
            self.arm.move_joints(targets, self.speed_scale, deg_per_s=self.one_to_one_cap())
        elif self.mapper.engaged and kind == "pose" and relative is not None:
            self.arm.move_joints(targets, self.speed_scale, deg_per_s=relative)
        else:
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

    def _needs_release(self) -> bool:
        """Does the arm wait for the input that drives it to be let go (grip, pinch or keys)?
        Only that input's flag counts: the keys' flag clears only with keys, so with a Quest or
        the webcam it stayed on after the grip was let go (quick job 66, GOTCHAS 2026-11-19)."""
        if self.input_kind == "joints":
            return self.jog.needs_release
        return self.mapper.needs_release

    def status(self) -> dict:
        """What the overlay / monitor shows (sent as a `status` message)."""
        if self.arm_connected:
            self._last_joints = self.arm.read_joints()
        joints = self._last_joints  # disconnected: the last reading (the 3D view stays put)
        return {
            "type": "status",
            "connected": self.inputs.connected,
            "frozen": self.frozen,
            "clutch": self.mapper.engaged or self.jog.active,
            "needs_release": self._needs_release(),
            "input_kind": self.input_kind,
            "ai_motion": self.motion_active,
            "shutting_down": self.shutting_down is not None,
            "speed_scale": self.speed_scale,
            "max_speed_scale": self.max_speed_scale,
            # hand → arm: "relative" or "one_to_one"; 1:1 only with kinematics (and a Quest page
            # that says where the arm is); while 1:1 waits for a grab: how far the hand is
            "mode": self.mapper.config.mode,
            "modes": self.modes(),
            "one_to_one_deg_per_s": None
            if math.isinf(self.one_to_one_deg_per_s)
            else self.one_to_one_deg_per_s,
            "servos": None
            if not self.health
            else {
                "max_temp_c": max(h["temp_c"] for h in self.health.values()),
                "hot": self.servos_hot,
                "joints": self.health,
            },
            "one_to_one": self.mapper.absolute and self.mapper.engaged,
            "hand_gap_cm": None
            if self.mapper.hand_gap_m is None
            else round(self.mapper.hand_gap_m * 100, 1),
            "capture_cm": round(self.mapper.config.capture_m * 100, 1),
            "arm": {
                "name": self.arm.name,
                "model": getattr(self.arm, "model", "unknown"),
                "connected": self.arm_connected,
                "problem": self.arm_problem,
            },
            "joints": joints,
            "last_command": self.last_command,
            "limits": {j: [lim.low, lim.high] for j, lim in self.arm.limits.items()},
            # two arms at once: the left controller's arm, or None
            "left_arm": self.left.left_status() if self.left else None,
        }

    def left_status(self) -> dict:
        """The left arm's part of the right arm's `status` (two arms at once)."""
        if self.arm_connected:
            self._last_joints = self.arm.read_joints()
        return {
            "name": self.arm.name,
            "model": getattr(self.arm, "model", "unknown"),
            "connected": self.arm_connected,
            "problem": self.arm_problem,
            "frozen": self.frozen,
            "clutch": self.mapper.engaged,
            "needs_release": self.mapper.needs_release,
            "mode": self.mapper.config.mode,
            "one_to_one": self.mapper.absolute and self.mapper.engaged,
            "hand_gap_cm": None
            if self.mapper.hand_gap_m is None
            else round(self.mapper.hand_gap_m * 100, 1),
            "capture_cm": round(self.mapper.config.capture_m * 100, 1),
            "joints": self._last_joints,
            "limits": {j: [lim.low, lim.high] for j, lim in self.arm.limits.items()},
        }

    async def run(self) -> None:
        period = 1.0 / self.rate_hz
        last = time.monotonic()
        while True:
            await asyncio.sleep(period)
            now = time.monotonic()
            try:
                self.check_link(now)
            except Exception:  # never let the USB check stop the arm loop
                log.exception("arm link check failed")
            try:
                self.step(now, now - last)
            except Exception:
                # E.g. the arm stopped answering. Freeze and keep running: a dead loop task would
                # leave every page "connected" but unable to move anything, with no message.
                self.check_link(now, force=True)  # unplugged? then say that, once
                if self.arm_connected:
                    log.exception("teleop step failed; arm frozen")
                self._freeze()
            last = now
            try:
                self.check_health(now)
            except Exception:  # never let a health reading stop the arm loop
                log.exception("servo health check failed")
            if self.on_tick:
                try:
                    self.on_tick(self)
                except Exception:  # a display bug must never stop the arm loop
                    log.exception("on_tick failed")
