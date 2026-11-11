# lab-os

**Lab JARVIS** for the IWU AI lab: one portable "brain" that connects the lab's robots so AI agents (and people) can see and control them. Working today: the Quest 3 teleop demo (a robot arm follows your controller or bare hand), the hub (a full-screen start page with a typed AI chat that knows the project), and AI tools such as Claude Code driving the `so101-white` arm through the brain, with a person approving every move. What's being worked on: `docs/current-focus.md`.

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
uv run lab-os serve                                      # the hub + teleop pages + fake arm
uv run lab-os-teleop serve                               # XR page + fake arm, live
uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl --loop   # no browser/headset
```
With `lab-os serve`, open http://localhost:8080/ for the hub (`docs/hub.md`). With `lab-os-teleop`, open http://localhost:8080/monitor to watch the fake arm. Testing at home with a browser emulator, and connecting the real Quest over USB: `docs/quest-setup.md`. Where the demo stands: `docs/archive/focus-2026-10-teleop-demo.md` (what's left: `docs/ideas.md` → "On hold").

## Repository map
| Path | What |
|---|---|
| `src/lab_os/` | The code. `devices.py` (robot registry + port safety), `robots/` (arm interface, fake arm), `teleop/` (WebXR page, WebSocket server, clutch mapping, record/replay, 3D arm view in `web/arm/`), `hub/` (the hub page and its endpoints), `ai/` (the hub's chat: AI setups, client, conversation, spend), `tools/` (robot and project tools for AI, MCP server), `web/` (files all pages share: vendored three.js and fonts, `theme.js`, the module pages' look in `design/`), `cli.py` (`lab-os serve`), `venues.py`, `personas.py`, `config.py` (the place's config folder), `settings.py` (the settings page), `green.py` (the training launcher) |
| `config/` | The lab's place (`docs/places.md`): `place.yaml` (the lab's name), `devices.yaml` (robot registry), `venues/` (lab, visit-day, …); shared by every place: `theme.yaml` (design tokens: colors, font), `poses.yaml`, `models.yaml` (AI setups, no keys), `personas/` |
| `models/` | Robot models (SO-101 URDF + meshes) for the 3D view and, later, inverse kinematics |
| `calibration/<robot>/` | Each arm's calibration files, so they travel with the arm |
| `tests/` | Automatic checks that run without hardware |
| `scripts/` | `install.sh` and other helpers |
| `docs/` | Plan, current focus, dev setup, gotchas |
| `SAFETY.md` | Stop procedures and limits. Read before any motion |

## Docs
- `docs/current-focus.md`: what's being worked on now
- `docs/hub.md`: running the hub, the two taps, other screens, the performance test
- `docs/quest-setup.md`: teleop at home (emulator, replay) and on the real Quest
- `docs/lab-checklist.md`: what to test in the lab, in order
- `docs/ai-control.md`: an AI tool (Claude Code, …) driving the arm through the brain's MCP tools
- `docs/chat.md`: the hub's typed chat, AI setups (`config/models.yaml`), keys, spend and the budget
- `docs/personas.md`: who the assistant is (lab-assistant, J.A.R.V.I.S.), switching, the greeting
- `docs/places.md`: running lab-os at home or in another lab (`--config`, `lab-os new-place`)
- `docs/green-launcher.md`: starting the SO-101 training setup (green arms + LeLab) in one click
- `docs/protocol.md`: the messages and endpoints between the pages, AI tools and the brain
- `docs/use-cases.md`: realistic workflows behind the features
- `docs/design/`: the approved hub design (`DESIGN.md`, `hub-concept.html`)
- `docs/lab-jarvis-log.md`: the master log (goals, decisions, devices)
- `docs/dev-setup.md`, `docs/network-setup-checklist.md`, `docs/project-scaffold.md`
- `docs/GOTCHAS.md`: surprises and their fixes
- `docs/ideas.md`: the ideas backlog (single source of truth for ideas)
- `CHANGELOG.md`: what changed, by date

CI (GitHub Actions, `.github/workflows/ci.yml`) runs the linter and tests on every push and pull request.

Private repository; license pending (asking the professor first).
