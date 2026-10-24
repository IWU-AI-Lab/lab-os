"""Hand motion must move the SO-101's gripper the same way, checked with forward kinematics on the
real URDF (models/so101). Guards the mapping's joint signs."""

import math
import xml.etree.ElementTree as ET

import pytest

from lab_os import REPO_ROOT
from lab_os.teleop.mapping import ClutchMapper
from lab_os.teleop.messages import ControllerState

URDF = REPO_ROOT / "models/so101/so101_new_calib.urdf"


def _mat(rpy):
    r, p, y = rpy
    cr, sr, cp, sp = math.cos(r), math.sin(r), math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    return [
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ]


def _axis(ax, a):
    x, y, z = ax
    c, s, t = math.cos(a), math.sin(a), 1 - math.cos(a)
    return [
        [t * x * x + c, t * x * y - s * z, t * x * z + s * y],
        [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
        [t * x * z - s * y, t * y * z + s * x, t * z * z + c],
    ]


def _mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mv(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]


def gripper_tip(joints_deg: dict[str, float]) -> list[float]:
    """Position (m, Z up, arm faces +x) of gripper_frame_link for the given joint angles."""
    root = ET.parse(URDF).getroot()
    by_child = {j.find("child").get("link"): j for j in root.findall("joint")}
    chain, link = [], "gripper_frame_link"
    while link in by_child:
        chain.append(by_child[link])
        link = by_child[link].find("parent").get("link")
    rot, pos = [[1, 0, 0], [0, 1, 0], [0, 0, 1]], [0.0, 0.0, 0.0]
    for j in reversed(chain):
        o = j.find("origin")
        xyz = [float(v) for v in o.get("xyz").split()]
        pos = [p + d for p, d in zip(pos, _mv(rot, xyz), strict=True)]
        rot = _mm(rot, _mat([float(v) for v in o.get("rpy").split()]))
        if j.get("type") == "revolute":
            ax = [float(v) for v in j.find("axis").get("xyz").split()]
            rot = _mm(rot, _axis(ax, math.radians(joints_deg.get(j.get("name"), 0.0))))
    return pos


START = {  # a typical working pose: upper arm level, forearm angled down toward the table
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
