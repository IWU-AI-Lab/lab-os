# CLAUDE.md — lab-os

Lab JARVIS: one portable "brain" that connects the lab's robots. Right now: the JARVIS hub, voice, and AI driving the SO-101 arms through the brain's tools, for a demo of every feature on 2026-11-19 (`docs/plan/current-focus.md`). The Quest → robot-arm teleop demo works (tag `demo-2026-10-30`).

## Read first, every session
1. `docs/plan/current-focus.md` — what to work on now (and "Up next").
2. `docs/plan/lab-jarvis-log.md` — plan, decisions, device names.
3. `docs/dev/GOTCHAS.md` — surprises already found.
4. For any hub or page UI: `docs/design/DESIGN.md` and the approved concept `docs/design/hub-concept.html` (open it in a browser; add `#skip` to the address to jump to the hub). New and changed pages follow the design (the designed hub is at `/design`; the numbers come from `config/theme.yaml`). It's no longer a surprise (2026-11-12), but `/` still shows the plain hub by default (`hub.look: plain`), just in case.

Docs are in folders by who reads them: `docs/plan/` (focus, quick jobs, ideas, log, use cases), `docs/guides/` (using it), `docs/dev/` (working on it), `docs/design/`, `docs/archive/` (history, dated; nothing current goes there). Setup and conventions: `docs/dev/dev-setup.md`. Safety: `SAFETY.md`.

## Hard rules: so101-green and the shared LeRobot setup
`so101-green` is the builder's SO-101 training set (leader `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41531599-if00`, follower `…5B41533501-if00`, two training cameras). **Since 2026-11-12 (the builder) lab-os may drive the green arms and use their cameras**, like `so101-white` (focus step 11). Four rules stay:
- **Never change the greens' motor IDs, baud rates or firmware.** No motor setup on them.
- **Their calibration is read-only.** lab-os may read `~/.cache/huggingface/lerobot/calibration/` to drive them; it never writes there and never recalibrates the greens.
- **Never modify the `lerobot` conda env** (`~/miniforge3/envs/lerobot`) or the `~/lerobot` checkout. Don't install into it, don't activate it for lab-os work.
- **One program per port:** never open a green port while LeLab or a training or recording run is using it; check first, and refuse with a sentence if it's busy.

The green arms may be unplugged during lab-os testing. Don't assume they're there or gone. The training launcher (`lab-os green`, `docs/guides/green-launcher.md`) keeps its own checks. **How the code keeps the rules (step 11, 2026-11-12):** the greens and their two cameras are `borrowed: true` in `config/devices.yaml` (never `off_limits` now); `lab_os.robots.so101_setup` refuses borrowed arms (by name and board serial); the driver reads the calibration through a temporary copy; `lab_os.devices.check_not_in_use` refuses a port or camera another program has open; the hook (`.claude/hooks/guard.sh`) and `.claude/settings.json` deny writes to LeRobot's cache and changes to the `lerobot` env.

## Environment
- lab-os has its **own uv environment** (`.venv/`, Python 3.12, uv-managed — never conda). `uv sync` to set up; `uv run …` to run.
- LeRobot for the SO-101s is the **optional extra `so101`** of this project (`uv sync --extra so101`), never the shared conda env. CI and other machines don't install it; import it lazily.
- Refer to serial devices **only by `/dev/serial/by-id/…`** names. `ttyACM0/1` swap after reboots/re-plugging.

## Project rules
- **Robots stay thin**: no editors / Claude Code / heavy tools on robots. Edit in this repo, then deploy (rsync). Never edit code on a robot.
- **Look for existing work first.** Before building a feature or a big part of one, search for existing implementations (GitHub, LeRobot and its examples, papers, libraries). If you find a good one (maintained and actually used, e.g. an official project or one with real stars, not an empty repo), **stop and tell the builder** what it is and how it compares with what's planned, before writing code. Small fixes don't need a search.
- **Fake robot first** (`lab_os.robots.fake.FakeArm`), then the real one. Every robot plug-in declares its requirements.
- **Ask before**: anything that makes a real robot move, `sudo`, deleting files, rebooting devices.
- **Hacks are labeled**: `# HACK: …` + a line in `docs/plan/current-focus.md` → "Hacks to clean up".
- **Every surprise** goes in `docs/dev/GOTCHAS.md`.
- **New ideas go into `docs/plan/ideas.md`, not code**, unless they are part of the current focus in `docs/plan/current-focus.md`. `docs/plan/ideas.md` is the single source of truth for ideas; don't list them in other docs. The long-term direction is `docs/plan/vision.md` (areas, not tasks).
- **Secrets never in git**: real values in `.env` (gitignored); `.env.example` lists names with fake values.
- **Works offline**: no CDN or internet-loaded code in the web pages. Browser libraries are vendored in `src/lab_os/web/vendor/` (versions + licenses in its README); robot models in `models/`.
- **Shared joint names** for all arms (`shoulder_pan`, `shoulder_lift`, `elbow_flex`, `wrist_flex`, `wrist_roll`, `gripper`, degrees); each driver maps them to its own servos.
- **Small commits, branch per feature**; `main` always runs. Demo only from a tagged version.
- Update the docs when decisions change — part of "done".

## Commands
```bash
uv sync                      # install / update the environment
uv sync --extra so101        # same + LeRobot/PyTorch (~5 GB) for the SO-101s; plain `uv sync` removes them
uv run pytest                # tests (no hardware needed)
uv run ruff check --fix .    # lint
uv run ruff format .         # format
uv run lab-os serve          # the brain: hub at http://localhost:8080/ + fake arm (docs/guides/hub.md),
                             # robot tools for AI at http://127.0.0.1:8081/mcp (docs/guides/ai-control.md)
uv run lab-os-teleop serve   # teleop on its own: XR page + fake arm (docs/guides/quest-setup.md)
uv run lab-os serve --config ~/my-lab-os   # another place's config folder (docs/dev/places.md)
```
Message format between clients and the brain: `docs/dev/protocol.md`. Keep it updated when adding message types. The JARVIS core (brain, slots, plug-ins) should grow out of the teleop code, not be designed up front.

## Style
Python 3.12, ruff-formatted (line length 100), type hints on public functions, short docstrings. Keep things small and readable — this is a solo project that a future student will inherit.

## The builder
Prefers VS Code and graphical tools over the terminal. When a step needs them to run something, give the exact command to paste.
