"""Joint-space fallback: hand motion must move the SO-101's gripper the same way, checked with
forward kinematics on the real URDF (models/so101). Guards the mapping's joint signs."""

import math

import pytest

from lab_os.kinematics import so101_kinematics
from lab_os.teleop.mapping import ClutchMapper
from lab_os.teleop.messages import ControllerState


def gripper_tip(joints_deg: dict[str, float]) -> list[float]:
    """Position (m, Z up, arm faces +x) of gripper_frame_link for the given joint angles."""
    return list(so101_kinematics().fk(joints_deg)[0])


START = {  # a typical working pose: upper arm up, forearm angled down toward the table
    "shoulder_pan": 0.0,
    "shoulder_lift": 0.0,
    "elbow_flex": 60.0,
    "wrist_flex": 0.0,
    "wrist_roll": 0.0,
    "gripper": 30.0,
}


def moved(dpos):
    """Joint targets after moving the hand by dpos (WebXR axes) with the clutch held."""
    m = ClutchMapper()
    hand = lambda p: ControllerState(p, (0, 0, 0, 1), 0.0, 1.0, {}, (0.0, 0.0))  # noqa: E731
    base = (0.0, 1.0, -0.3)
    m.step(hand(base), START, 0.02, 1.0)
    joints = dict(START)
    for _ in range(200):
        joints |= m.step(
            hand(tuple(b + d for b, d in zip(base, dpos, strict=True))), joints, 0.02, 1.0
        )
    return joints


@pytest.mark.parametrize(
    ("dpos", "check"),
    [
        ((0, 0.05, 0), lambda a, b: b[2] > a[2] + 0.01),  # hand up → tip up
        ((0, -0.05, 0), lambda a, b: b[2] < a[2] - 0.01),  # hand down → tip down
        ((0.05, 0, 0), lambda a, b: b[1] < a[1] - 0.01),  # hand right → tip to the arm's right (-y)
        ((0, 0, -0.05), lambda a, b: math.hypot(b[0], b[1]) > math.hypot(a[0], a[1]) + 0.005),
    ],
    ids=["up", "down", "right", "forward-reaches-out"],
)
def test_hand_motion_moves_gripper_the_same_way(dpos, check):
    before = gripper_tip(START)
    after = gripper_tip(moved(dpos))
    assert check(before, after), (before, after)
