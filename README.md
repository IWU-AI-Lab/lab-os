# lab-os

**Lab JARVIS** for the IWU AI lab: one portable "brain" that connects the lab's robots so AI agents (and people) can see and control them. Working today: the Quest 3 teleop demo (a robot arm follows your controller or bare hand), the hub (a full-screen start page with an AI assistant that knows the project, typed or by voice), and AI tools such as Claude Code driving the SO-101 arms through the brain, looking through their cameras. What's being worked on: `docs/plan/current-focus.md`. **Everything that works today, plus lab projects not connected yet: [`FEATURES.md`](FEATURES.md).**

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
With `lab-os serve`, open http://localhost:8080/ for the hub (`docs/guides/hub.md`). With `lab-os-teleop`, open http://localhost:8080/monitor to watch the fake arm. Testing at home with a browser emulator, and connecting the real Quest over USB: `docs/guides/quest-setup.md`. Teleop's leftovers: `docs/plan/ideas.md` → "On hold".

## Repository map
| Path | What |
|---|---|
| `src/lab_os/` | The code. `devices.py` (robot registry + port safety), `robots/` (arm interface, fake arm), `teleop/` (WebXR page, WebSocket server, clutch mapping, record/replay, 3D arm view in `web/arm/`), `hub/` (the hub page and its endpoints), `ai/` (the hub's chat: AI setups, client, conversation, spend), `tools/` (robot and project tools for AI, MCP server), `web/` (files all pages share: vendored three.js and fonts, `theme.js`, the module pages' look in `design/`), `cli.py` (`lab-os serve`), `venues.py`, `personas.py`, `config.py` (the place's config folder), `settings.py` (the settings page), `green.py` (the training launcher) |
| `config/` | The lab's place (`docs/dev/places.md`): `place.yaml` (the lab's name), `devices.yaml` (robot registry), `venues/` (lab, visit-day, …); shared by every place: `theme.yaml` (design tokens: colors, font), `poses.yaml`, `models.yaml` (AI setups, no keys), `personas/` |
| `models/` | Robot models (SO-101 URDF + meshes) for the 3D view and, later, inverse kinematics |
| `calibration/<robot>/` | Each arm's calibration files, so they travel with the arm |
| `tests/` | Automatic checks that run without hardware |
| `scripts/` | `install.sh` and other helpers |
| `docs/` | `plan/`, `guides/`, `dev/`, `design/`, `archive/` (below) |
| `SAFETY.md` | Stop procedures and limits. Read before any motion |

## Docs
In folders by who reads them:
- **Top level:** `FEATURES.md` (what works today, and lab projects not connected yet), `CHANGELOG.md` (what changed, by date), `SAFETY.md`, `CLAUDE.md` (rules for Claude Code sessions).
- **`docs/plan/`, what's being built and why:** `current-focus.md` (now, until the 2026-12-03 demo), `quick-jobs.md` (small decided jobs), `ideas.md` (the backlog, incl. "On hold"; the only home for ideas), `vision.md` (the long-term direction), `lab-jarvis-log.md` (goals, decisions, devices, facts about the lab), `use-cases.md` (realistic workflows behind the features).
- **`docs/guides/`, using it:** `hub.md` (the hub, its pages, other screens, `/perf`), `voice.md` (talking to it, secure pages), `ai-control.md` (an AI tool driving an arm through the brain's MCP tools), `quest-setup.md` (teleop at home and on the real Quest), `green-launcher.md` (the SO-101 training setup in one click), `lab-checklist.md` (what to test in the lab), `network-setup-checklist.md` (devices on the network).
- **`docs/dev/`, working on it:** `dev-setup.md` (how development works, branches and folders), `project-scaffold.md` (what the repo should contain), `protocol.md` (messages, MCP tools and HTTP endpoints), `places.md` (config folders, devices, running elsewhere), `personas.md`, `chat.md` (AI setups, keys, spend), `GOTCHAS.md` (surprises and their fixes).
- **`docs/design/`:** the approved hub design (`DESIGN.md`, `hub-concept.html`). **`docs/device_manuals/`:** manuals (the Newline). **`docs/archive/`:** closed focuses and other history, dated.

CI (GitHub Actions, `.github/workflows/ci.yml`) runs the linter and tests on every push and pull request.

Private repository; license pending (asking the professor first).
