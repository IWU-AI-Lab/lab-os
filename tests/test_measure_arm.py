"""lab-os measure-arm: the fit of an SO-101's shoulder offset and table height (quick job 121)."""

import shutil
from pathlib import Path

import yaml

from lab_os.devices import _read_devices
from lab_os.robots import measure_arm
from lab_os.robots.measure_arm import Fit, fit, tip_z_cm, write_device

DEVICES = Path(__file__).parent.parent / "config" / "devices.yaml"

# raw readings of poses near the base and far out, on both sides
POSES = [
    {"shoulder_pan": p, "shoulder_lift": lift, "elbow_flex": elbow, "wrist_flex": wrist}
    for p, lift, elbow, wrist in [
        (0, -60, 70, 70),
        (20, -30, 50, 70),
        (-25, 0, 30, 70),
        (10, 20, 0, 75),
        (-5, 35, -20, 80),
        (30, 10, 20, 60),
    ]
]


def _points(offset_deg: float, table_cm: float) -> list[tuple[dict, float]]:
    """What the hand measurement gives on an arm whose shoulder reads `offset_deg` wrong: each
    pose's real tip height above a table at `table_cm`."""
    out = []
    for raw in POSES:
        real = raw | {"shoulder_lift": raw["shoulder_lift"] + offset_deg}
        out.append((raw, tip_z_cm(real)[0] - table_cm))
    return out


def test_fit_finds_the_shoulder_offset_and_the_table():
    result = fit(_points(-4.7, -1.6))
    assert abs(result.shoulder_lift_deg + 4.7) <= 0.05
    assert abs(result.table_z_cm + 1.6) <= 0.1
    assert result.rms_cm < 0.05
    assert result.problem() == ""


def test_fit_with_no_error_changes_nothing():
    result = fit(_points(0.0, 0.0))
    assert abs(result.shoulder_lift_deg) <= 0.05 and abs(result.table_z_cm) <= 0.1


def test_problems_stop_the_write():
    assert "at least" in fit(_points(-3, 0)[:3]).problem()
    near = [(POSES[0] | {"shoulder_pan": p}, 0.0) for p in (-20, 0, 20, 30)]
    assert "apart in reach" in fit(near).problem()
    noisy = Fit(-3, 0, (1.0, -1.0, 1.0, -1.0), 20)
    assert "disagree" in noisy.problem()
    assert "too large" in Fit(20, 0, (0, 0, 0, 0), 20).problem()


def test_write_device_sets_the_two_numbers_and_keeps_the_rest(tmp_path):
    path = tmp_path / "devices.yaml"
    shutil.copy(DEVICES, path)
    before = _read_devices(path)
    result = Fit(-3.25, -0.4, (0.1, -0.1, 0.2, -0.2), 20)
    write_device(path, "so101-green", result, {})
    after = _read_devices(path)
    green = after["so101-green"]
    assert green.table_z_cm == -0.4
    assert dict(green.joint_offsets_deg) == {"shoulder_lift": -3.25}
    assert (
        green.borrowed and green.training_calibration == before["so101-green"].training_calibration
    )
    for name in before:  # every other device is as it was
        if name != "so101-green":
            assert after[name] == before[name]
    text = path.read_text()
    assert "measured by hand with lab-os measure-arm" in text
    # again: replaced, not added twice; another joint's offset kept
    write_device(path, "so101-green", result, {"elbow_flex": 1.5})
    again = _read_devices(path)["so101-green"]
    assert dict(again.joint_offsets_deg) == {"elbow_flex": 1.5, "shoulder_lift": -3.25}
    assert path.read_text().count("measured by hand with lab-os measure-arm") == 1
    assert yaml.safe_load(path.read_text())["devices"]["so101-white"]["table_z_cm"] == -1.6


def test_write_device_adds_lines_that_are_missing(tmp_path):
    path = tmp_path / "devices.yaml"
    path.write_text(
        "devices:\n  arm-a:\n    kind: so101\n    ports: []\n  arm-b:\n    kind: fake\n"
    )
    write_device(path, "arm-a", Fit(2, -1, (0, 0, 0, 0), 20), {})
    devices = _read_devices(path)
    assert devices["arm-a"].table_z_cm == -1 and dict(devices["arm-a"].joint_offsets_deg) == {
        "shoulder_lift": 2
    }
    assert devices["arm-b"].kind == "fake" and not devices["arm-b"].joint_offsets_deg


class _FakeArm:
    """The read-only SO-101 driver, without a bus: reads the next pose (with its offsets)."""

    offsets = {"shoulder_lift": -1.0}
    queue: list[dict] = []
    closed = False

    def __init__(self, name: str):
        self.name = name

    def connect(self):
        pass

    def read_measured(self):
        raw = self.queue[0]
        return {j: v + self.offsets.get(j, 0.0) for j, v in raw.items()}

    def close(self):
        _FakeArm.closed = True


def test_run_reads_each_point_and_writes(tmp_path, monkeypatch):
    import lab_os.robots.so101 as so101

    path = tmp_path / "devices.yaml"
    shutil.copy(DEVICES, path)
    monkeypatch.setattr(so101, "SO101Arm", _FakeArm)
    monkeypatch.setattr("lab_os.config.place_path", lambda name: tmp_path / name)
    points = _points(-4.0, 0.0)
    said = [f"{h:.4f}" for _, h in points] + ["d", "y"]
    order = iter(points)  # each answer reads the pose of the same point

    def ask_in_order(prompt):
        answer = said.pop(0)
        if prompt.startswith("Point") and answer != "d":
            _FakeArm.queue = [next(order)[0]]
        return answer

    assert measure_arm.run("so101-green", ask=ask_in_order) == 0
    assert _FakeArm.closed
    green = _read_devices(path)["so101-green"]
    assert abs(dict(green.joint_offsets_deg)["shoulder_lift"] + 4.0) <= 0.05
    assert abs(green.table_z_cm) <= 0.1
