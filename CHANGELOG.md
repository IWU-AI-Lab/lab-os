# Changelog

One line per meaningful change, newest first. Demo versions get a git tag (e.g. `demo-2026-11-15`).

## 2026-10-24
- Theme file seed: `config/theme.yaml` (design tokens), served as `/theme.json`; the 3D arm views (desktop + headset arm, markers, frozen tint, status-panel font) read their colors from it. Pages' CSS and the VR room are not themed yet (design phase).
- Docs: `docs/ideas.md` is now the single source of truth for ideas (earlier lists moved in); architecture shapes to design toward + decisions in the log; "Up next" = troubleshooting suite; mood-board folder `docs/design/references/`.
- XR session scene (`xr-scene.js`, three.js WebXR): arm on a table in front of you (see-through ghost in AR), controller markers + clutch line, floating status panel; VR gets a dim room. Shared `ArmFeed` keeps the desktop panel and the headset arm in sync. Tested in headless Brave with Meta's iwer Quest 3 emulation.
- xArm 1S 3D model rebuilt from Hiwonder's dimension drawing (65 / 101 / 95 / 168 mm, 154 × 140 base, suction cups, both gripper fingers move), same joint conventions as the SO-101. The 3D view frames each arm type when it loads.
- Desktop control on the teleop page: keyboard + trackpad drive a virtual controller (Space = clutch, C = gripper, X = stop, H = re-center), sending the same messages as the Quest. 3D view renders only on change.
- Fixed the teleop joint directions for the SO-101 (hand up was lowering the arm): per-joint signs, verified by forward kinematics on the URDF in the tests. Fake arm starts in a working pose; the 3D view starts behind the arm.
- Soft joint limits in the teleop mapping: commands stay 3° inside each limit and the clutch slips at a limit, so there's no wind-up and no jump when re-grabbing (seen in the WebXR emulator).
- 3D arm view on the teleop and monitor pages: draws exactly what the arm driver receives (new `arm_command` / `arm_stop` / `arm_resume` messages), flags driver clamping and out-of-limit commands, red tint when frozen. Models: SO-101 from its real URDF (meshes or stick figure), xArm 1S from boxes. three.js 0.186.1 + urdf-loader 0.13.1 vendored for offline use; SO-101 URDF in `models/so101/`. The model code is page-independent, for the Quest ghost arm later.
- FakeArm now uses the SO-101's real joint limits (from the URDF; a test keeps them in sync) and declares its 3D model.
- Monday lab checklist (raspbots, xarm1 identify/driver/measure, Quest developer mode + real Quest data test) added to `docs/current-focus.md`.
- Teleop step 2 groundwork: `lab-os-teleop` serves a plain-JS WebXR page that sends Quest controller data (pose, grip, trigger, buttons) over a WebSocket; live terminal readout and an arm monitor page. Message format in `docs/protocol.md`.
- Testing without a headset: record (`serve --record`) and replay (`replay`) controller sessions; synthetic sample in `tests/fixtures/`; browser-emulator and Quest-over-USB guide in `docs/quest-setup.md`.
- Teleop step 3 on the fake arm: clutch control (grip = move, relative to the arm's current pose), gentle ramps, tilt-for-rotation, trigger = gripper, A/X = stop; freezes on release, tracking loss, disconnect or stale input.
- Venue profiles are now read (`lab_os.venues`): the teleop speed comes from `max_speed_scale`.
- CI: GitHub Actions runs ruff (lint + format) and the tests on every push and pull request. No hardware needed.
- Repo scaffold: README, CLAUDE.md, SAFETY.md, docs/GOTCHAS.md, .gitignore, .env.example, config/ (device registry, venue profiles), calibration/, uv project + lock file, `scripts/install.sh`, ruff, tests.
- Robot interface (`Arm`) and a software-only `FakeArm` for testing without hardware.
- so101-green protected: off limits in `config/devices.yaml` (enforced by `lab_os.devices`), Claude Code guard hook, deny rules for the shared `lerobot` conda env. Serial ports referenced only by `/dev/serial/by-id/`.
- Lab desktop set up: uv, ruff, gh (signed in), tmux, SSH key + `~/.ssh/config` keepalive/connection-reuse settings.

## 2026-10-23
- Docs added: master log, current focus, dev setup, network checklist, project scaffold.
