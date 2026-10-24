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
    assert joints["elbow_flex"] == 90.0
    assert joints["gripper"] == -90.0


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
