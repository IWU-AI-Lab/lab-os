import pytest

from lab_os.robots.fake import FakeArm


@pytest.fixture
def arm():
    a = FakeArm()
    a.connect()
    return a


def test_move_clamps_to_limits(arm):
    arm.move_joints({"elbow_flex": 500.0, "gripper": -500.0}, speed_scale=0.5)
    joints = arm.read_joints()
    assert joints["elbow_flex"] == arm.limits["elbow_flex"].high
    assert joints["gripper"] == arm.limits["gripper"].low


def test_limits_match_so101_urdf():
    """FakeArm limits must stay in sync with the URDF the 3D view draws."""
    import math
    import xml.etree.ElementTree as ET

    from lab_os import REPO_ROOT

    urdf = ET.parse(REPO_ROOT / "models/so101/so101_new_calib.urdf").getroot()
    limits = FakeArm().limits
    for joint in urdf.findall("joint"):
        if joint.get("type") != "revolute":
            continue
        lim = joint.find("limit")
        name = joint.get("name")
        assert limits[name].low == pytest.approx(math.degrees(float(lim.get("lower"))), abs=0.01)
        assert limits[name].high == pytest.approx(math.degrees(float(lim.get("upper"))), abs=0.01)


def test_speed_scale_clamped(arm):
    arm.move_joints({"wrist_roll": 10.0}, speed_scale=5.0)
    assert arm.log[-1][2] == 1.0


def test_stop_freezes_until_resume(arm):
    arm.stop()
    arm.move_joints({"shoulder_pan": 45.0}, speed_scale=0.5)
    assert arm.read_joints()["shoulder_pan"] == 0.0
    arm.resume()
    arm.move_joints({"shoulder_pan": 45.0}, speed_scale=0.5)
    assert arm.read_joints()["shoulder_pan"] == 45.0


def test_unknown_joint_rejected(arm):
    with pytest.raises(KeyError):
        arm.move_joints({"tail": 1.0}, speed_scale=0.5)


def test_must_connect_first():
    with pytest.raises(RuntimeError):
        FakeArm().read_joints()


def test_the_fake_arm_starts_at_the_ready_pose():
    """Teleop and the fake arm start at `ready`; `home` is the folded pose (quick job 20)."""
    from lab_os.robots.fake import SO101_READY
    from lab_os.tools.robot import load_poses

    poses = load_poses()["so101"]
    assert poses["ready"] == SO101_READY
    assert poses["home"]["shoulder_lift"] < -80 and poses["home"]["gripper"] == 10
