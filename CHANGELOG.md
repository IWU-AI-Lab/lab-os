# Changelog

One line per meaningful change, newest first. Demo versions get a git tag (e.g. `demo-2026-11-15`).

## 2026-10-24
- CI: GitHub Actions runs ruff (lint + format) and the tests on every push and pull request. No hardware needed.
- Repo scaffold: README, CLAUDE.md, SAFETY.md, docs/GOTCHAS.md, .gitignore, .env.example, config/ (device registry, venue profiles), calibration/, uv project + lock file, `scripts/install.sh`, ruff, tests.
- Robot interface (`Arm`) and a software-only `FakeArm` for testing without hardware.
- so101-green protected: off limits in `config/devices.yaml` (enforced by `lab_os.devices`), Claude Code guard hook, deny rules for the shared `lerobot` conda env. Serial ports referenced only by `/dev/serial/by-id/`.
- Lab desktop set up: uv, ruff, gh (signed in), tmux, SSH key + `~/.ssh/config` keepalive/connection-reuse settings.

## 2026-10-23
- Docs added: master log, current focus, dev setup, network checklist, project scaffold.
