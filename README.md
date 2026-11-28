# lab-os

**lab-os** for the IWU AI lab. It is one portable "brain" that connects the lab's robots. AI tools and people use it to see and control the robots.

What works today:
- **Arm Control:** a robot arm follows your Quest 3 controller or your bare hand.
- **The hub:** a full-screen start page with an AI assistant that knows the project. You can type to it or talk to it.
- **AI control:** AI tools such as Claude Code drive the SO-101 arms through the brain and look through their cameras.

The full list, with the lab projects that are not connected yet, is in [`FEATURES.md`](FEATURES.md). What is being built now is in `docs/plan/current-focus.md`.

*(A photo or GIF of the demo goes here.)*

## Install
On a new Linux computer (the lab desktop or a laptop), run:
```bash
git clone https://github.com/IWU-AI-Lab/lab-os.git
cd lab-os
./scripts/install.sh
```
The script installs [uv](https://docs.astral.sh/uv/) if it is missing. It makes the project's own environment in `.venv/` (Python 3.12, with LeRobot for the SO-101 arms). It never changes conda and never runs `sudo`. Then it runs `uv run lab-os setup`: that checks each part the brain needs and says in one line what it found or did. At the end it prints the `sudo` commands to paste, and the other steps (for example the real AI keys in `.env`). Do them, then run `uv run lab-os setup` again. The list of parts is in `docs/dev/dev-setup.md` → "A new brain computer". On a computer that drives no SO-101 arm, run `./scripts/install.sh --no-so101` (about 5 GB less).

## Run
```bash
uv run pytest                                            # the tests (no hardware needed)
uv run pytest -n auto                                    # the same, in parallel (faster)
uv run lab-os serve                                      # the brain: the hub, the Arm Control pages and the arm plugged in (else the fake arm)
uv run lab-os-teleop serve                               # Arm Control only: the headset page and the fake arm
uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl --loop   # replay a recording (no browser, no headset)
```
- After `lab-os serve`, open http://localhost:8080/ for the hub. The options are in `docs/archive/guides-2026-11-25/hub.md` → "Start it".
- After `lab-os-teleop serve`, open http://localhost:8080/monitor/so101 to watch the fake arm (`/monitor` lists the Monitor pages).
- To test Arm Control at home, or to connect the real Quest over USB, read `docs/guides/quest-setup.md`.

## Repository map
| Path | What |
|---|---|
| `src/lab_os/` | The code. `devices.py`: the device list and port safety. `robots/`: the arm interface and the fake arm. `teleop/`: the headset page, its server, the clutch mapping, recording and replay, and the 3D arm (`web/arm/`). `hub/`: the hub pages and their endpoints. `ai/`: the hub's chat (AI setups, the client, the conversation, the spend). `tools/`: the robot and project tools for AI, and the MCP server. `web/`: files that every page uses (three.js, fonts, `theme.js`, the module pages' look in `design/`). `cli.py`: `lab-os serve`. Also `venues.py`, `personas.py`, `config.py` (the place's config folder), `settings.py` (the settings page), `green.py` (the training launcher), `quest_view.py` (the Quest's view on another screen). |
| `config/` | The lab's place (`docs/dev/places.md`): `place.yaml` (the lab's name), `devices.yaml` (the device list), `venues/` (lab, visit-day). Every place shares `theme.yaml` (the design's colors and fonts), `poses.yaml`, `gestures.yaml` (the hub's wave), `models.yaml` (the AI setups, without keys) and `personas/`. |
| `models/` | Robot models (the SO-101 URDF and meshes) for the 3D view and the kinematics. |
| `calibration/<robot>/` | Each arm's calibration files. They move with the arm. |
| `tests/` | The automatic tests. They need no hardware. |
| `scripts/` | `install.sh` and other helpers. |
| `docs/` | `plan/`, `guides/`, `dev/`, `design/`, `archive/` (below). |
| `SAFETY.md` | How to stop the robots, and the limits. Read it before any motion. |

## Docs
The docs are in folders by who reads them:
- **Top level:** `FEATURES.md` (what works today), `CHANGELOG.md` (what changed, by date), `SAFETY.md`, `AGENTS.md` (the rules for AI coding agents), `CLAUDE.md` (points Claude Code to `AGENTS.md`).
- **`docs/plan/`, what we build and why:** `current-focus.md` (the work until the demo on 2026-12-03), `quick-jobs.md` (small decided jobs), `ideas.md` (the only list of ideas, with "On hold"), `vision.md` (the long-term direction), `log.md` (goals, decisions, devices, facts about the lab), `use-cases.md` (real workflows behind the features).
- **`docs/guides/`, how to use it:** `ai-control.md` (an AI tool drives an arm through the brain), `lab-inventory.md` (every device in the lab), `quest-setup.md` (Arm Control at home and on the real Quest), `raspbot.md` (the Raspbot), `lab-checklist.md` (what to test in the lab before the demo) and `lab-checklist-after-demo.md` (the rest). The other guides are paused until a stable version: they are in `docs/archive/guides-2026-11-25/` (`hub.md`, `voice.md`, `quest-view.md`, `tic-tac-toe.md`, `green-launcher.md`, `webcam-teleop.md`, `network-setup-checklist.md`).
- **`docs/dev/`, how to work on it:** `dev-setup.md` (branches and folders), `project-scaffold.md` (what the repository contains), `protocol.md` (messages, MCP tools and HTTP endpoints), `places.md` (config folders, devices, other places), `personas.md`, `chat.md` (AI setups, keys, spend), `GOTCHAS.md` (surprises and their fixes).
- **`docs/design/`:** the approved hub design (`DESIGN.md`, `hub-concept.html`). **`docs/device_manuals/`:** manuals (the Newline). **`docs/archive/`:** closed focuses and other history, by date.

GitHub Actions (`.github/workflows/ci.yml`) runs the linter and the tests once for each push to `main` and once for each push to a pull request's branch. A branch without a pull request gets no run. The tests run in parallel (`pytest -n auto`) and take about 15 s.

The repository is private. The license is not decided yet: we ask the professor first.
