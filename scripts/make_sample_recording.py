"""Write tests/fixtures/sample_clutch.jsonl: a synthetic right-controller session for replay.

Story (~7 s): idle → grip → move right/up/forward + roll → squeeze trigger → release grip →
move hand back with grip released (arm must NOT follow) → grip again → move left → release → end.

    uv run python scripts/make_sample_recording.py
"""

import json
import math
from pathlib import Path

HZ = 60
OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sample_clutch.jsonl"
START = (0.20, 1.00, -0.30)


def ramp(t: float, t0: float, t1: float) -> float:
    """0 before t0, 1 after t1, smooth in between."""
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    x = (t - t0) / (t1 - t0)
    return x * x * (3 - 2 * x)


def state(t: float) -> dict:
    out = ramp(t, 1.0, 3.0) - ramp(t, 4.0, 5.0)  # hand goes out, then back (released)
    left = ramp(t, 5.5, 6.5)
    x = START[0] + 0.10 * out - 0.15 * left
    y = START[1] + 0.10 * out
    z = START[2] - 0.10 * out
    roll = math.radians(30) * out
    grip = ramp(t, 0.5, 0.7) - ramp(t, 3.6, 3.8) + ramp(t, 5.1, 5.3) - ramp(t, 6.7, 6.9)
    return {
        "pos": [round(x, 4), round(y, 4), round(z, 4)],
        "quat": [0.0, 0.0, round(math.sin(roll / 2), 5), round(math.cos(roll / 2), 5)],
        "trigger": round(ramp(t, 3.0, 3.5), 3),
        "grip": round(grip, 3),
        "buttons": {"a": False, "b": False, "thumbstick": False},
        "thumbstick": [0.0, 0.0],
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    n = int(7.2 * HZ)
    for i in range(n):
        t = i / HZ
        msg = {"type": "xr_input", "t": round(t * 1000, 1), "hands": {"right": state(t)}}
        lines.append(json.dumps({"dt": round(t, 4), "msg": msg}))
    lines.append(json.dumps({"dt": round(n / HZ, 4), "msg": {"type": "session_end"}}))
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT} ({n} frames)")


if __name__ == "__main__":
    main()
