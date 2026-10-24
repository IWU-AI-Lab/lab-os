# lab-os

**Lab JARVIS** for the IWU AI lab: one portable "brain" that connects the lab's robots so AI agents (and people) can see and control them. The first milestone is a Quest 3 teleop demo, where a visitor's bare hand drives a robot arm live and picks up a block within ~30 seconds.

*(Photo / GIF of the demo goes here once it works.)*

## Install
On a fresh Linux machine (lab desktop or laptop):
```bash
git clone https://github.com/IWU-AI-Lab/lab-os.git
cd lab-os
./scripts/install.sh
cp .env.example .env     # then fill in real keys
```
This installs [uv](https://docs.astral.sh/uv/) if needed and creates the project's own environment in `.venv/` (Python 3.12). It never touches conda.

## Run
```bash
uv run pytest                                            # checks, no hardware needed
uv run lab-os-teleop serve                               # XR page + fake arm, live
uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl --loop   # no browser/headset
```
Open http://localhost:8080/monitor to watch the fake arm. Testing at home with a browser emulator, and connecting the real Quest over USB: `docs/quest-setup.md`. Where the demo stands: `docs/current-focus.md`.

## Repository map
| Path | What |
|---|---|
| `src/lab_os/` | The code. `devices.py` (robot registry + port safety), `robots/` (arm interface, fake arm), `teleop/` (WebXR page, WebSocket server, clutch mapping, record/replay, 3D arm view in `web/arm/`, vendored three.js in `web/vendor/`), `venues.py` |
| `config/` | `devices.yaml` (robot registry), `venues/` (lab, visit-day, …) |
| `models/` | Robot models (SO-101 URDF + meshes) for the 3D view and, later, inverse kinematics |
| `calibration/<robot>/` | Each arm's calibration files, so they travel with the arm |
| `tests/` | Automatic checks that run without hardware |
| `scripts/` | `install.sh` and other helpers |
| `docs/` | Plan, current focus, dev setup, gotchas |
| `SAFETY.md` | Stop procedures and limits. Read before any motion |

## Docs
- `docs/current-focus.md`: what's being worked on now
- `docs/lab-jarvis-log.md`: the master log (goals, decisions, devices)
- `docs/dev-setup.md`, `docs/network-setup-checklist.md`, `docs/project-scaffold.md`
- `docs/GOTCHAS.md`: surprises and their fixes
- `CHANGELOG.md`: what changed, by date

CI (GitHub Actions, `.github/workflows/ci.yml`) runs the linter and tests on every push and pull request.

Private repository; license pending (asking the professor first).
