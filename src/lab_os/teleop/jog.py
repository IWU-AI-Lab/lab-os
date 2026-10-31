"""Joint jogging: each motor turns while its key (or mouse motion) says so. No IK, no clutch.

Input: per joint a speed from -1 to 1 (`JointFrame.rates`). Each tick the target moves by
`rate * jog_deg_per_s * speed_scale * dt`, inside the soft limits. It starts from the arm's
current joints (no snap) and then keeps its own commanded position until a freeze: the xArm
reports positions 0.25-0.8 s late, so restarting from a reading after each key press would jerk
the joint back. After a freeze (stale input, STOP, page left), every rate must go back
to 0 before anything moves again, like releasing the grip.
"""

from dataclasses import dataclass, field

from lab_os.robots.base import JointLimit
from lab_os.teleop.mapping import soft_bounds


@dataclass
class JogMapper:
    jog_deg_per_s: float = 60.0  # at speed_scale = 1 and rate = 1
    limit_margin_deg: float = 3.0
    active: bool = False  # something is being jogged right now
    needs_release: bool = False
    _commanded: dict[str, float] = field(default_factory=dict)
    _bounds: dict[str, tuple[float, float]] = field(default_factory=dict)

    def reset(self, require_release: bool = True) -> None:
        self.active = False
        self.needs_release = require_release
        self._commanded = {}

    def step(
        self,
        rates: dict[str, float],
        arm_joints: dict[str, float],
        dt: float,
        speed_scale: float,
        limits: dict[str, JointLimit] | None = None,
    ) -> dict[str, float] | None:
        """Joint targets for this tick, or None when nothing should move."""
        rates = {
            j: r for j, r in rates.items() if j in arm_joints and r
        }  # ignore other arms' joints
        if self.needs_release:
            if not rates:
                self.needs_release = False
            return None
        if not rates:
            self.active = False
            return None
        if not self._commanded:
            self._commanded = dict(arm_joints)
            self._bounds = soft_bounds(limits or {}, arm_joints, self.limit_margin_deg)
        self.active = True
        step = self.jog_deg_per_s * min(max(speed_scale, 0.0), 1.0) * dt
        for joint, rate in rates.items():
            target = self._commanded[joint] + rate * step
            lo, hi = self._bounds.get(joint, (-1e9, 1e9))
            self._commanded[joint] = min(max(target, lo), hi)
        return {j: self._commanded[j] for j in rates}
