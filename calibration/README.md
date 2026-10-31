# Calibration

One folder per arm (`calibration/<device-name>/`), so calibration files travel with the arm instead of living on one computer.

- `so101-white/so101-white.json` and `so101-white-leader/so101-white-leader.json`: LeRobot's calibration format (per motor: id, homing offset, range min/max), written by `uv run --extra so101 python -m lab_os.robots.so101_setup calibrate [--arm so101-white-leader]`. The middle of each range is also stored in the motors themselves, so re-plugging into another computer just needs this file. Commit it after calibrating.
- `xarm1/`: limits / offsets measured during teleop step 1.

`so101-green`'s calibration is **not** here and must not be copied or changed. It belongs to the training project.
