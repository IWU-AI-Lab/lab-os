"""The teleop joint readout's notes (quick job 24): "outside" means outside the limit in force,
at the angle the driver holds. Runs the page's own module with node; skipped without node."""

import json
import shutil
import subprocess

import pytest

from lab_os import REPO_ROOT

MODULE = REPO_ROOT / "src/lab_os/teleop/web/arm/joint-flags.js"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node isn't installed")


def flags(cmd, drv=None, limit=None, out_of_model=False, unknown=False) -> list[str]:
    args = json.dumps([cmd, drv, limit, {"outOfModel": out_of_model, "unknown": unknown}])
    script = (
        f"import({json.dumps(MODULE.as_uri())}).then(m => {{"
        f"const a = {args}.map(v => v === null ? undefined : v);"  # null → not reported
        "console.log(JSON.stringify(m.jointFlags(...a))); })"
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_held_at_the_limit_is_not_outside():
    # lab check 8.9 on so101-green: 97.4 commanded, the driver held it at its limit of 96.8
    got = flags(97.4, drv=96.8, limit=[-96.8, 96.8], out_of_model=True)
    assert got == ["clamped by driver → 96.8°"]


def test_held_past_the_limit_in_force_is_outside():
    # a joint already outside its limits may stay there (the driver only lets it come back)
    got = flags(100.0, drv=100.0, limit=[-90.0, 90.0])
    assert got == ["outside the arm's limits (-90.0…90.0°)"]


def test_narrower_limits_than_the_model_count():
    # calibration narrowed the range to ±80: 85 is inside the model, outside the arm
    assert flags(85.0, drv=85.0, limit=[-80.0, 80.0]) == ["outside the arm's limits (-80.0…80.0°)"]


def test_without_the_drivers_limits_the_model_decides():
    assert flags(120.0, out_of_model=True) == ["outside model limits"]
    assert flags(10.0, unknown=True) == ["not in this model"]
    assert flags(10.0, drv=10.0, limit=[-90.0, 90.0]) == []
