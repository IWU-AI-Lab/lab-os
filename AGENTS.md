# AGENTS.md — lab-os

The rules for every AI coding agent in this repo (Claude Code, Codex, Cursor, …). This is the one copy: `CLAUDE.md` only points here, so change the rules here.

lab-os: one portable "brain" that connects the lab's robots. Its assistant has personas (J.A.R.V.I.S., the Lab Assistant, more later); use "lab-os" for the project, and a persona's name only for that persona. Right now: the hub, voice, and AI driving the SO-101 arms through the brain's tools, for a demo of every feature on 2026-12-03 (`docs/plan/current-focus.md`). The Quest → robot-arm teleop demo works (tag `demo-2026-10-30`).

## Read first, every session
1. `docs/plan/current-focus.md` — what to work on now (and "Up next").
2. `docs/plan/log.md` — plan, decisions, device names.
3. `docs/dev/GOTCHAS.md` — surprises already found.
4. For any hub or page UI: `docs/design/DESIGN.md` and the approved concept `docs/design/hub-concept.html` (open it in a browser; add `#skip` to the address to jump to the hub). New and changed pages follow the design (the hub at `/` is the designed hub since quick job 131; the numbers come from `config/theme.yaml`).

Docs are in folders by who reads them: `docs/plan/` (focus, quick jobs, ideas, log, use cases), `docs/guides/` (using it), `docs/dev/` (working on it), `docs/design/`, `docs/archive/` (history, dated; nothing current goes there, except the paused guides in `guides-2026-11-25/`). Setup and conventions: `docs/dev/dev-setup.md`. Safety: `SAFETY.md`.

## Hard rules: so101-green and the shared LeRobot setup
`so101-green` is the builder's SO-101 training set (leader `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41531599-if00`, follower `…5B41533501-if00`, two training cameras). **Since 2026-11-12 (the builder) lab-os may drive the green arms and use their cameras**, like `so101-white` (focus step 11). Four rules stay:
- **Never change the greens' motor IDs, baud rates or firmware.** No motor setup on them.
- **Their calibration is read-only.** The training files (`sheep.json` follower, `shepherd.json` leader, in `~/.cache/huggingface/lerobot/calibration/`) are the source of truth. lab-os drives with its own copy (`calibration/so101-green*/`) and checks it still equals them; LeLab uses its own copy (`lelab_green.json`, since 2026-11-17). lab-os never writes there and never recalibrates the greens.
- **Never modify the `lerobot` conda env** (`~/miniforge3/envs/lerobot`) or the `~/lerobot` checkout. Don't install into it, don't activate it for lab-os work.
- **One program per port:** never open a green port while LeLab or a training or recording run is using it; check first, and refuse with a sentence if it's busy.

The green arms may be unplugged during lab-os testing. Don't assume they're there or gone. The training launcher (`lab-os green`, `docs/archive/guides-2026-11-25/green-launcher.md`) keeps its own checks. **How the code keeps the rules (step 11, 2026-11-12):** the greens and their two cameras are `borrowed: true` in `config/devices.yaml` (never `off_limits` now); `lab_os.robots.so101_setup` refuses borrowed arms (by name and board serial); the driver reads the calibration through a temporary copy; `lab_os.devices.check_not_in_use` refuses a port or camera another program has open; the hook (`.claude/hooks/guard.sh`) and `.claude/settings.json` deny writes to LeRobot's cache and changes to the `lerobot` env. **That hook and those permissions guard Claude Code only.** Any other agent has no such guard here: keep the four rules yourself, and ask the builder before each action in "Ask before" below.

## Environment
- lab-os has its **own uv environment** (`.venv/`, Python 3.12, uv-managed — never conda). `uv sync` to set up; `uv run …` to run.
- LeRobot for the SO-101s is the **optional extra `so101`** of this project (`uv sync --extra so101`), never the shared conda env. CI and other machines don't install it; import it lazily.
- Refer to serial devices **only by `/dev/serial/by-id/…`** names. `ttyACM0/1` swap after reboots/re-plugging.

## Project rules
- **Robots stay thin**: no editors / AI coding agents / heavy tools on robots. Edit in this repo, then deploy (rsync). Never edit code on a robot.
- **Look for existing work first.** Before building a feature or a big part of one, search for existing implementations (GitHub, LeRobot and its examples, papers, libraries). If you find a good one (maintained and actually used, e.g. an official project or one with real stars, not an empty repo), use it when it clearly fits, or build as planned when it doesn't. **Don't stop to ask** (the builder, 2026-11-20): write one line in the report on what you found and what you chose. Small fixes don't need a search.
- **Fake robot first** (`lab_os.robots.fake.FakeArm`), then the real one. Every robot plug-in declares its requirements.
- **Ask before**: `sudo`, deleting files, rebooting devices, and (in a coding session) running anything that makes a real robot move. A session the builder started to drive an arm may use the brain's move tools freely: they're on the allow list since 2026-11-13 (`docs/guides/ai-control.md`); STOP, the soft limits and one controller at a time stay.
- **Write to the builder in ASD-STE100 (Simplified Technical English).** This applies to everything the builder reads from you: reports, questions, chat answers, pull request descriptions and the guides. The main rules: one instruction per sentence, with the verb first ("Open Settings."); procedure sentences of 20 words or fewer, descriptions of 25 or fewer; paragraphs of 6 sentences or fewer; active voice; present or simple past tense; one word for one meaning, and one name for one thing (the name the page shows); no idioms, slang or invented shorthand; keep articles ("the", "a"); give a warning or condition before the instruction it applies to. Names of commands, files, settings and devices stay as they are. `docs/guides/` already follows these rules (quick job 39).
- **Build only what the job says.** No extra features, buttons, modes or settings beyond the job. If something more seems needed, write it as one line at the end of the report: the builder decides (2026-11-20).
- **"Etc." and "for example" mean more than the list** (the builder, 2026-11-25). When the builder writes "etc.", "and more", "and the others" or "for example" in a job, the listed things are examples. Find and do every related thing of the same kind, and name in the report what you added.
- **The report at the end of a session fits on one screen (about 15 lines)**, in this form (the builder, 2026-11-20: longer reports don't get read):
  - **You will see:** what changed, as the builder meets it on the pages (their words), one line each.
  - **Test:** the lab checklist parts to run.
  - **Waiting for you:** only a critical pull request (see the merge rule), with one sentence on what it changes. Usually nothing.
  - **Choices:** the choices the builder will see or live with, one sentence each, so that it makes sense to someone who hasn't read the session: the thing's everyday name, what it does now and what it did before ("The Training page now opens LeLab. Before, it only showed the checks."). No shorthand, no labels invented during the session, no file or function names.

  Everything else (tests, causes, files, details) goes in the pull request, not in the report.
- **Hacks are labeled**: `# HACK: …` + a line in `docs/plan/current-focus.md` → "Hacks to clean up".
- **Every surprise** goes in `docs/dev/GOTCHAS.md`.
- **Read the brain's log when a lab result says something went wrong** (quick job 85): `uv run lab-os logs --at 18:14` (the time the builder wrote) prints the minutes around it; `uv run lab-os logs` prints the end. Run it on the computer that ran the brain. The log is in `config/local/logs/` (not in git, 4 days kept).
- **New ideas go into `docs/plan/ideas.md`, not code**, unless they are part of the current focus in `docs/plan/current-focus.md`. `docs/plan/ideas.md` is the single source of truth for ideas; don't list them in other docs. The long-term direction is `docs/plan/vision.md` (areas, not tasks).
- **Secrets never in git**: real values in `.env` (gitignored); `.env.example` lists names with fake values.
- **Works offline**: no CDN or internet-loaded code in the web pages. Browser libraries are vendored in `src/lab_os/web/vendor/` (versions + licenses in its README); robot models in `models/`.
- **Shared joint names** for all arms (`shoulder_pan`, `shoulder_lift`, `elbow_flex`, `wrist_flex`, `wrist_roll`, `gripper`, degrees); each driver maps them to its own servos.
- **Small commits, branch per feature**; `main` always runs. Demo only from a tagged version.
- **At most three coding sessions at once, one for each lane** of the queue in `docs/plan/quick-jobs.md` (the builder, 2026-11-25; two since 2026-11-20, before that one at a time). Do your lane's jobs in order, and merge each one before you start the next. Before you start, run `gh pr list` and `git branch -r`; stay out of files an open pull request changes when you can. **Before you merge, merge `main` into your branch and fix every conflict yourself; never ask the builder about a conflict.** In the docs, keep every side (new GOTCHAS entries, new checklist parts, jobs moved to Done). A planning session may run at the same time: it edits only `docs/plan/` and the lab checklist. Sessions never share a folder (each its own `git worktree`).
- **Merge your own pull request once the tests pass on GitHub** (`gh pr checks --watch`, then `gh pr merge --merge --delete-branch`). This includes new arm movement and new ways to drive an arm, when they go through the existing safety layer and the tests pass on the fake arm (the builder, 2026-11-20: "ensure I don't need to do this unless there's something super critical"). **Leave it open only when it is critical:** it changes the green arms' rules, or it changes `.claude/` (permissions, the hook). Then say in at most 3 sentences what it changes and what to check, and put it first in the report. **Until the demo, a change to a safety rule merges too** (STOP, the soft limits, the floor, the speed caps, one controller at a time, the freeze when input stops; the builder, 2026-11-25: no safety reviews while the builder works fast). Put one sentence on what it changes first in the report. Do the next job only if it doesn't touch the same files.
- **Agents without Git/GitHub access (such as sandboxed Gemini sessions):** If you cannot run `git push` or `gh`, create a local feature branch (`git checkout -b <branch>`), make your edits, and run local checks (`uv run pytest`, `uv run ruff check .`). Leave changes uncommitted (or committed locally if `user.name`/`user.email` are set) and skip `gh pr` steps. End your report with the branch name, changed files, and a note for the builder or a GitHub-enabled agent to commit, push, and open/merge the PR. Never edit in the same folder while another coding session is active.
- **Say each fact in one place** (what's waiting on whom in `docs/plan/current-focus.md`, devices in `config/devices.yaml`, decisions in the log) and point to it elsewhere, so there's one copy to keep right. When two docs disagree, the newest decision in `docs/plan/log.md` wins: fix the other one.
- **Most guides are paused until a stable version** (the builder, 2026-11-25, quick job 123: fewer output tokens). The paused guides are in `docs/archive/guides-2026-11-25/`. Until the builder says, do not write or update them, and do not add new guides. The builder asks a session for instructions instead. Keep updating the guides that stay in `docs/guides/` (the two lab checklists and the guides the demo run needs), `SAFETY.md` and `FEATURES.md`.
- **Update the docs in the same pull request, and leave no leftovers.** When you change how something works or what it's called, search every doc for the old name and wording (`grep -rn`) and fix or delete each place that's now wrong. Dated history (the log's decision rows, `docs/archive/`, GOTCHAS entries) stays as written; add a line saying what replaced it.

## Commands
```bash
uv sync                      # install / update the environment
uv sync --extra so101        # same + LeRobot/PyTorch (~5 GB) for the SO-101s; plain `uv sync` removes them
uv run pytest                # tests (no hardware needed)
uv run ruff check --fix .    # lint
uv run ruff format .         # format
uv run lab-os serve          # the brain: hub at http://localhost:8080/ + the SO-101 plugged in, else the
                             # fake arm (--arm names one; docs/archive/guides-2026-11-25/hub.md),
                             # robot tools for AI at http://127.0.0.1:8081/mcp (docs/guides/ai-control.md)
uv run lab-os-teleop serve   # teleop on its own: XR page + fake arm (docs/guides/quest-setup.md)
uv run lab-os serve --config ~/my-lab-os   # another place's config folder (docs/dev/places.md)
uv run lab-os icon --device desk           # the "Start lab-os" icon (devices: docs/archive/guides-2026-11-25/hub.md)
uv run lab-os logs --at 18:14              # the brain's log around a time (no --at: the end)
uv run lab-os usb                          # every USB device under its controller (docs/guides/plug-in.md)
uv run lab-os raspbot deploy               # the Raspbot page's program to raspbot1 (docs/guides/raspbot.md)
```
Message format between clients and the brain: `docs/dev/protocol.md`. Keep it updated when adding message types. The lab-os core (brain, slots, plug-ins) should grow out of the teleop code, not be designed up front.

## Style
Python 3.12, ruff-formatted (line length 100), type hints on public functions, short docstrings. Keep things small and readable — this is a solo project that a future student will inherit.

## The builder
Prefers VS Code and graphical tools over the terminal. When a step needs them to run something, give the exact command to paste.
