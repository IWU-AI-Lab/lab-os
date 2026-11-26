"""Offline checks for the official Raspbot V2 model."""

from xml.etree import ElementTree as ET

from lab_os.teleop.server import MODELS_DIR

MODEL_DIR = MODELS_DIR / "raspbot"
URDF = MODEL_DIR / "Raspbot-V2.urdf"


def test_raspbot_meshes_are_local_binary_stls():
    xml = URDF.read_text(encoding="utf-8")
    robot = ET.fromstring(xml)
    assert robot.tag == "robot"
    assert robot.attrib["name"] == "Raspbot-V2"
    assert "package://" not in xml

    paths = {mesh.attrib["filename"] for mesh in robot.iter("mesh")}
    assert len(paths) == 7
    assets = MODEL_DIR / "assets"
    for filename in paths:
        assert filename.startswith("assets/")
        path = (MODEL_DIR / filename).resolve(strict=True)
        assert path.is_relative_to(assets)
        assert path.suffix.lower() == ".stl"
        with path.open("rb") as stl:
            stl.seek(80)
            triangles = int.from_bytes(stl.read(4), "little")
        assert triangles > 0
        assert path.stat().st_size == 84 + triangles * 50
    assert paths == {path.relative_to(MODEL_DIR).as_posix() for path in assets.iterdir()}


def test_raspbot_has_four_moving_wheels_and_two_camera_joints():
    robot = ET.parse(URDF).getroot()
    joints = {joint.attrib["name"]: joint for joint in robot.findall("joint")}
    for name in ("l1_Joint", "l2_Joint", "r1_Joint", "r2_Joint"):
        assert joints[name].attrib["type"] == "continuous"
    for name in ("arm1_Joint", "arm2_Joint"):
        assert joints[name].attrib["type"] == "continuous"
