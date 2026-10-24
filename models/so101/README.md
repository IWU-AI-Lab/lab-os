# SO-101 robot model

Used by the 3D view (`/models/so101/…`, drawn by `web/arm/arm-model.js`) and later by inverse kinematics (step 4).

| | |
|---|---|
| Source | [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100), `Simulation/SO101/` |
| Commit | `a758567c3978dfeefe282ede0500085a48fe8f78` (downloaded 2026-10-24) |
| License | Apache-2.0 (`LICENSE`, copied from that repository) |
| Files | `so101_new_calib.urdf` + the 13 STL meshes it references (`assets/`), unmodified |

`new_calib` matches LeRobot's current calibration convention. Joint names (`shoulder_pan` … `gripper`) are the ones lab-os uses for every arm. The joint limits are mirrored in `lab_os.robots.fake.SO101_LIMITS_RAD`; a test keeps them in sync.

To update: download the new URDF + its referenced STLs from the same folder, record the new commit here, re-run the tests.
