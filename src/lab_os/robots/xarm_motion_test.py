"""xArm motion test: small, slow moves of ONE joint. Moves the real arm. Only run after SAFETY.md:
arm clamped, area clear, power plug in reach. If the servos are limp after power-on, press the
board's "Run" button first (it poses the arm upright; docs/GOTCHAS.md).

    uv run python -m lab_os.robots.xarm_motion_test [--joint wrist_roll] [--degrees 10]

Steps: (1) one 1 s move of +degrees and back, polling every 0.25 s (faster polling makes the
board drop moves), reporting first-motion delay and where it stopped; (2) a 2 s ramp streamed at
20 and 50 commands/s. Ctrl+C sends the joint back to where it started.
"""

import argparse
import time

from lab_os.devices import default_device
from lab_os.robots.xarm import SERVO_IDS, XArm

MAX_DEGREES = 10.0  # hard cap for this test


def read(arm: XArm, joint: str) -> float | None:
    try:
        return arm.read_measured()[joint]
    except TimeoutError:  # common while servos move
        return None


def single_move(arm: XArm, joint: str, start: float, target: float) -> None:
    arm.send_move({joint: target}, duration_ms=1000)
    t0 = time.monotonic()
    first = None
    while time.monotonic() - t0 < 2.0:
        time.sleep(0.25)
        now = read(arm, joint)
        if first is None and now is not None and abs(now - start) > 1.0:
            first = time.monotonic() - t0
    end = read(arm, joint)
    moved = "no motion seen" if first is None else f"first motion seen by {first * 1000:.0f} ms"
    end_text = f"{end:.1f}" if end is not None else "?"
    print(f"  {start:.1f} -> {target:.1f} deg: {moved}, stopped at {end_text}")


def stream_ramp(arm: XArm, joint: str, a: float, b: float, hz: int) -> None:
    n, t0 = 2 * hz, time.monotonic()
    for i in range(1, n + 1):
        arm.send_move({joint: a + (b - a) * i / n}, duration_ms=100)
        time.sleep(max(0.0, t0 + i / hz - time.monotonic()))
    time.sleep(0.6)
    end = read(arm, joint)
    end_text = f"{end:.1f}" if end is not None else "?"
    print(f"  {hz} Hz ramp {a:.1f} -> {b:.1f} deg: ended at {end_text}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--joint", default="wrist_roll", choices=sorted(SERVO_IDS))
    parser.add_argument("--degrees", type=float, default=10.0)
    args = parser.parse_args()
    if not 0 < abs(args.degrees) <= MAX_DEGREES:
        raise SystemExit(f"--degrees must be within +-{MAX_DEGREES}")
    if input("Arm clamped, area clear, power plug in reach? Type 'yes': ") != "yes":
        raise SystemExit("aborted")

    name = default_device(("xarm1s",))
    arm = XArm(name=name, device_name=name, allow_motion=True)
    arm.connect()
    joint, step = args.joint, args.degrees
    start = None
    while start is None:
        start = read(arm, joint)
    print(f"{joint} starts at {start:.1f} deg")
    try:
        print("single moves:")
        single_move(arm, joint, start, start + step)
        time.sleep(0.5)
        single_move(arm, joint, start + step, start)
        print("streamed ramps:")
        for hz in (20, 50):
            time.sleep(0.8)
            stream_ramp(arm, joint, start, start + step, hz)
            time.sleep(0.8)
            stream_ramp(arm, joint, start + step, start, hz)
    finally:
        arm.send_move({joint: start}, duration_ms=1000)
        time.sleep(1.5)
        arm.close()


if __name__ == "__main__":
    main()
