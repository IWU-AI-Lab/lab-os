# Project Scaffold — what the repository should contain

What the repo should contain. Solo project → keep everything **short and useful**, not corporate. "Day one" items were created at the kickoff (2026-10-23); the others when they're first needed. **Status (2026-11-13):** everything in "Day one" exists except `LICENSE` (waiting on the professor); from "Soon", `GOTCHAS.md`, CI, demo tags and `CHANGELOG.md` exist, `DEMO.md`, `decisions/` and a task board don't (the log's decisions table stands in for `decisions/`).

---

## Day one
| File / folder | What it's for |
|---|---|
| `README.md` | What this is (one paragraph + a photo/GIF later), how to install, how to run the demo, where the docs are. The first thing a future student reads. |
| `CLAUDE.md` | Instructions for Claude Code every session: read `docs/plan/current-focus.md` and `docs/plan/lab-jarvis-log.md` first; project rules (robots stay thin, edit-in-repo-then-deploy, fake robot first, hacks labeled, safety rules, ask before robot motion/sudo/deletes/reboots); coding style; how to run tests. Keep it short and point to docs rather than copying them. |
| `docs/` | In folders by who reads them: `plan/` (the log, the current focus, ideas), `guides/` (using it), `dev/` (working on it), `archive/` (history). The list: README → "Docs". |
| `SAFETY.md` | Stop procedures, speed/workspace limits, dead-man rule, visitor rules, remote-mode rule, drone rule. Short and printable. |
| `.gitignore` | Ignore secrets, logs, recordings, datasets, model weights, virtual environments, OS junk. |
| `.env.example` | Lists every secret/setting the system needs **with fake values**. The real `.env` (API keys, passwords) stays on each machine and is never committed. |
| `config/` | Settings files, separate from code: persona(s), model router, robot registry (`devices.yaml`), **venue profiles** (`lab`, `visit-day`, …). |
| `calibration/<robot-name>/` | Each arm's calibration files, so they travel with the arm (not stuck on one computer). |
| Dependency lock | One tool that pins exact versions (e.g. `uv` with a lock file) so the lab desktop, a laptop and a future student all get the same setup. |
| `scripts/install.sh` | One command that sets everything up on a fresh Linux machine (and is tested on a laptop too). |
| `tests/` + fake robots | Automatic checks that run **without hardware**, using the fake/mock robots. Start with a few; add one whenever a bug is fixed. |
| Formatter / linter | e.g. `ruff` for Python (and Prettier for web code), run automatically, so style never needs thinking about. |
| `LICENSE` | **Ask the professor first** — university projects may have rules about ownership. If free to choose, MIT is the simple default. Until then, keep the repo **private**. |

## Soon (first few weeks)
| File / folder | What it's for |
|---|---|
| `docs/dev/GOTCHAS.md` | Every on-the-ground surprise + its fix (the "papercuts only bite once" file). |
| `docs/DEMO.md` | The demo runbook: kit checklist, ≤10-minute setup steps, the 30-second visitor script, what to do if X fails. |
| `docs/decisions/` | Short decision records ("we chose X over Y because Z"), one file each, for big choices — the master log stays the summary. |
| GitHub Actions (CI) | Runs tests + linter automatically on every push. Catches breakage before it reaches the lab. |
| Git tags for demos | Tag a **known-good version** (e.g. `demo-2026-11-15`) after a successful rehearsal. **Always demo from a tagged version, never from untested latest code.** |
| `CHANGELOG.md` | One line per meaningful change, grouped by date/version. Doubles as a progress record (motivating!). |
| Issues / task board | GitHub Issues or Projects as the to-do list; link to it from the README. |

## Later (handoff, before May 2027)
| File | What it's for |
|---|---|
| `CONTRIBUTING.md` | How a new student gets started: setup, branch → test → pull request, coding style, where to ask. |
| `docs/HANDOFF.md` | What works, what's half-done, what's broken, where passwords/accounts live (not the passwords themselves), who to ask. |
| `docs/ARCHITECTURE.md` | One diagram + one page: brain, slots, plug-ins, message protocol, where each piece lives. |
| Demo video / GIF in README | Proof it works; also portfolio material. |

## Working habits
They're in `CLAUDE.md` ("Project rules"), the one list.
