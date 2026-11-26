"""Measure an SO-101's height error by hand (quick job 121, the way quick job 106 measured
so101-white): `uv run --extra so101 lab-os measure-arm so101-green`.

READ-ONLY: the motors stay off (no torque, no goal). You put the closed jaw tips on the table (or
on something of a known height) at a few places, near the base and far out, and press Enter at
each. The command fits two numbers so that the model's jaw tips are where you put them:
- `shoulder_lift`'s offset (degrees added to its reading; so101-white: -4.7). Its error grows with
  the reach, so you need points near the base and far out.
- `table_z_cm`: the table's height in the arm's own numbers (0 = the bottom of its base).
With both right, the floor (the venue's `min_z_cm`, from the table) is the same for every arm: the
jaw tips stop 0.2 cm above the table. It then writes them to config/devices.yaml, if you say yes.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from lab_os.kinematics import so101_kinematics

TIP_PAST_CM = 0.6  # the jaw tips reach this far past the gripper point (quick job 106)
MIN_POINTS = 4
MIN_REACH_SPREAD_CM = 10.0  # near and far points: else the offset and the table can't be told apart
OFFSET_RANGE_DEG = 12.0  # a fit outside these is a wrong point, not the arm: not written
TABLE_RANGE_CM = 4.0
MAX_RMS_CM = 0.7
SAMPLES = 5  # readings averaged for each point


@dataclass(frozen=True)
class Fit:
    shoulder_lift_deg: float  # the offset to add to shoulder_lift's raw reading
    table_z_cm: float
    errors_cm: tuple[float, ...]  # each point's height after the fix minus where it really was
    reach_spread_cm: float

    @property
    def rms_cm(self) -> float:
        return math.sqrt(sum(e * e for e in self.errors_cm) / len(self.errors_cm))

    def problem(self) -> str:
        """Why these numbers should not be written ("" = they can be)."""
        if len(self.errors_cm) < MIN_POINTS:
            return f"Only {len(self.errors_cm)} points. Put the tips on at least {MIN_POINTS}."
        if self.reach_spread_cm < MIN_REACH_SPREAD_CM:
            return (
                f"The points are only {self.reach_spread_cm:.0f} cm apart in reach. Add a point "
                "near the base and a point far out."
            )
        if abs(self.shoulder_lift_deg) > OFFSET_RANGE_DEG or abs(self.table_z_cm) > TABLE_RANGE_CM:
            return "The numbers are too large for a real arm. A point was probably wrong."
        if self.rms_cm > MAX_RMS_CM:
            return (
                f"The points disagree by {self.rms_cm:.1f} cm on average. Do them again, "
                "with the jaws closed and the tips touching."
            )
        return ""


def tip_z_cm(joints: dict[str, float]) -> tuple[float, float]:
    """The model's jaw tips: (height, reach from the base's z axis), cm, in the arm's own numbers.
    The tips are TIP_PAST_CM past the gripper point, along the line from the wrist_flex axis."""
    f = so101_kinematics().frames(joints)
    g, p = f["tip"][0], f["wrist_flex"][0]
    d = [a - b for a, b in zip(g, p, strict=True)]
    n = math.sqrt(sum(x * x for x in d)) or 1.0
    t = [(a + TIP_PAST_CM / 100 * x / n) for a, x in zip(g, d, strict=True)]
    return t[2] * 100, math.hypot(t[0], t[1]) * 100


def fit(points: list[tuple[dict[str, float], float]]) -> Fit:
    """Fit from (raw joints without any offset, the tips' real height above the table in cm).
    For each shoulder_lift offset (0.05° steps) the best table height is the mean difference;
    the offset with the smallest error wins."""
    best = None
    for k in range(-int(OFFSET_RANGE_DEG * 2 * 20), int(OFFSET_RANGE_DEG * 2 * 20) + 1):
        s = k / 20
        tips = [tip_z_cm(j | {"shoulder_lift": j["shoulder_lift"] + s})[0] - h for j, h in points]
        t = sum(tips) / len(tips)
        sq = sum((z - t) ** 2 for z in tips)
        if best is None or sq < best[0] - 1e-12:
            best = (sq, s, t, tips)
    _, s, t, tips = best
    reaches = [tip_z_cm(j | {"shoulder_lift": j["shoulder_lift"] + s})[1] for j, _ in points]
    return Fit(
        shoulder_lift_deg=round(s, 2),
        table_z_cm=round(t, 1),
        errors_cm=tuple(round(z - t, 2) for z in tips),
        reach_spread_cm=max(reaches) - min(reaches),
    )


def write_device(path: Path, name: str, result: Fit, others: dict[str, float]) -> None:
    """Set `table_z_cm` and `joint_offsets_deg` of device `name` in a devices.yaml, keeping every
    other line and comment. `others`: the arm's offsets of other joints, kept."""
    lines = path.read_text().splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if ln.rstrip() == f"  {name}:"), None)
    if start is None:
        raise KeyError(f"{name} is not in {path}")
    # the block ends at the next line that is not indented under it (a device, or its comment)
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if lines[i].strip() and len(lines[i]) - len(lines[i].lstrip()) <= 2
        ),
        len(lines),
    )
    offsets = others | {"shoulder_lift": result.shoulder_lift_deg}
    note = (
        f"    # measured by hand with lab-os measure-arm: {len(result.errors_cm)} points, "
        f"{result.rms_cm:.1f} cm average error (quick job 121)\n"
    )
    new = {
        "table_z_cm": f"    table_z_cm: {result.table_z_cm:g}\n",
        "joint_offsets_deg": "    joint_offsets_deg: {"
        + ", ".join(f"{j}: {v:g}" for j, v in offsets.items())
        + "}\n",
    }
    block = lines[start:end]
    for key in ("table_z_cm", "joint_offsets_deg"):
        at = next((i for i, ln in enumerate(block) if ln.startswith(f"    {key}:")), None)
        if at is None:
            kind = next(i for i, ln in enumerate(block) if ln.startswith("    kind:"))
            block.insert(kind + 1, new[key])
        else:
            block[at] = new[key]
    at = next(i for i, ln in enumerate(block) if ln.startswith("    joint_offsets_deg:"))
    if not block[at - 1].startswith("    # measured by hand with lab-os measure-arm"):
        block.insert(at, note)
    else:
        block[at - 1] = note
    path.write_text("".join(lines[:start] + block + lines[end:]))


def run(name: str, ask: Callable[[str], str] = input) -> int:
    """The interactive measurement (see the module's docstring). 0 = written or nothing to do."""
    from lab_os import config
    from lab_os.devices import PortNotAllowed
    from lab_os.robots.so101 import SO101Arm

    arm = SO101Arm(name=name)  # allow_motion False: nothing is written to the motors
    try:
        arm.connect()
    except (PortNotAllowed, LookupError, KeyError, RuntimeError) as e:
        print(f"Not opening {name}: {e}")
        return 1
    before = dict(arm.offsets)
    print(
        f"{name} is open, read only: its motors stay off. If the arm is stiff, press Ctrl+C.\n"
        "Close the jaws. Put the jaw tips on the table and press Enter. On something higher (the "
        "cube: 3), type its height in cm, then Enter.\n"
        f"Do at least {MIN_POINTS} places: near the base, far out, left and right. "
        "Type d and Enter when done."
    )
    points: list[tuple[dict[str, float], float]] = []
    try:
        while True:
            said = ask(f"Point {len(points) + 1} (Enter = on the table, d = done): ").strip()
            if said.lower() == "d":
                break
            try:
                height = float(said) if said else 0.0
            except ValueError:
                print("Type a height in cm, or nothing, or d.")
                continue
            reads = [arm.read_measured() for _ in range(SAMPLES)]
            raw = {j: sum(r[j] for r in reads) / SAMPLES - before.get(j, 0.0) for j in reads[0]}
            z, reach = tip_z_cm(raw)
            print(f"  tips {reach:.0f} cm out; the model (no fix) says {z:.1f} cm high")
            points.append((raw, height))
    finally:
        arm.close()
    if not points:
        return 0
    result = fit(points)
    print(
        f"Fit: shoulder_lift offset {result.shoulder_lift_deg:g}° "
        f"(now {before.get('shoulder_lift', 0.0):g}°), table at {result.table_z_cm:g} cm. "
        "After the fix, each point is off by: "
        + ", ".join(f"{e:+.1f}" for e in result.errors_cm)
        + " cm."
    )
    problem = result.problem()
    if problem:
        print(f"Not written. {problem}")
        return 1
    path = config.place_path("devices.yaml")
    if ask(f"Write these to {path} for {name}? (y/n): ").strip().lower() != "y":
        print("Not written.")
        return 0
    write_device(path, name, result, {j: v for j, v in before.items() if j != "shoulder_lift"})
    print(
        f"Written. Restart the brain to use them. {name}: {result.shoulder_lift_deg:g}°, "
        f"{result.table_z_cm:g} cm."
    )
    return 0
