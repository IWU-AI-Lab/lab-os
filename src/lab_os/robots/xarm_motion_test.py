"""xArm motion test: small, slow moves of ONE joint. Moves the real arm. Only run after SAFETY.md:
arm clamped, area clear, power plug in reach.

    uv run python -m lab_os.robots.xarm_motion_test [--joint wrist_roll] [--degrees 5]

Steps: (1) one slow move of +degrees and back, reporting the direction it moved and the
command->first-motion delay; (2) a 2 s burst of tiny commands to count commands/second.
Ctrl+C returns the joint to where it started.
"""

import argparse
import time

from lab_os.robots.xarm import SERVO_IDS, XArm

MAX_DEGREES = 10.0  # hard cap for this test


def wait_for_motion(arm: XArm, joint: str, start: float, timeout_s: float = 3.0) -> float | None:
    """Seconds until the joint has moved more than 0.5 deg from `start`, or None."""
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout_s:
        try:
            if abs(arm.read_joints()[joint] - start) > 0.5:
                return time.perf_counter() - t0
        except TimeoutError:
            pass
    return None


def settle(arm: XArm, seconds: float) -> None:
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        time.sleep(0.05)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--joint", default="wrist_roll", choices=sorted(SERVO_IDS))
    parser.add_argument("--degrees", type=float, default=5.0)
    args = parser.parse_args()
    if not 0 < abs(args.degrees) <= MAX_DEGREES:
        raise SystemExit(f"--degrees must be within +-{MAX_DEGREES}")
    if input("Arm clamped, area clear, power plug in reach? Type 'yes': ") != "yes":
        raise SystemExit("aborted")

    arm = XArm(allow_motion=True)
    arm.connect()
    joint = args.joint
    start = arm.read_joints()[joint]
    print(f"{joint} starts at {start:.1f} deg (raw {arm.read_raw()[SERVO_IDS[joint]]})")
    try:
        t0 = time.perf_counter()
        arm.move_joints({joint: start + args.degrees}, speed_scale=0.1)  # slow: ~12 deg/s
        delay = wait_for_motion(arm, joint, start)
        print(f"first motion after {delay * 1000:.0f} ms" if delay else "NO MOTION seen")
        settle(arm, 1.5)
        end = arm.read_joints()[joint]
        print(f"moved {end - start:+.1f} deg for a {args.degrees:+.1f} deg command")
        print(f"command + first motion measured over {time.perf_counter() - t0:.2f} s")

        n, t1 = 0, time.perf_counter()
        while time.perf_counter() - t1 < 2:
            target = start + args.degrees + (1.0 if n % 2 else 0.0)
            arm.send_move({joint: target}, duration_ms=100)
            n += 1
        print(f"{n / (time.perf_counter() - t1):.0f} move commands/s (no waiting for replies)")
    finally:
        arm.move_joints({joint: start}, speed_scale=0.1)
        settle(arm, 2.0)
        print(f"back at {arm.read_joints()[joint]:.1f} deg")
        arm.close()


if __name__ == "__main__":
    main()
