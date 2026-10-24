# Changelog

One line per meaningful change, newest first. Demo versions get a git tag (e.g. `demo-2026-11-15`).

## 2026-10-24
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
