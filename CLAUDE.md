# CLAUDE.md — lab-os

Lab JARVIS: one portable "brain" that connects the lab's robots. Right now: the Quest → robot-arm teleop demo.

## Read first, every session
1. `docs/current-focus.md` — what to work on now (and "Up next").
2. `docs/lab-jarvis-log.md` — plan, decisions, device names.
3. `docs/GOTCHAS.md` — surprises already found.

Setup and conventions: `docs/dev-setup.md`, `docs/project-scaffold.md`. Safety: `SAFETY.md`.

## Hard rules: so101-green and the shared LeRobot setup
`so101-green` belongs to another training project. It is **not ours**.
- **Never open the green arm's ports.** Serial devices `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41531599-if00` and `…5B41533501-if00`. No reading, no probing, no "just checking" — opening the port can disturb a running training session. They're marked `off_limits` in `config/devices.yaml`, and `lab_os.devices` refuses to return them.
- **Never recalibrate it** or touch `~/.cache/huggingface/lerobot/calibration/`.
- **Never modify the `lerobot` conda env** (`~/miniforge3/envs/lerobot`) or the `~/lerobot` checkout. Don't install into it, don't activate it for lab-os work.
- The green arm may be unplugged during lab-os testing. Don't assume it's there or gone.

A hook (`.claude/hooks/guard.sh`) blocks the obvious violations, but these rules apply even where the hook can't see them.

## Environment
- lab-os has its **own uv environment** (`.venv/`, Python 3.12, uv-managed — never conda). `uv sync` to set up; `uv run …` to run.
- LeRobot for `so101-white` is the **optional extra `so101`** of this project (`uv sync --extra so101`), never the shared conda env. CI and other machines don't install it; import it lazily.
- Refer to serial devices **only by `/dev/serial/by-id/…`** names. `ttyACM0/1` swap after reboots/re-plugging.

## Project rules
- **Robots stay thin**: no editors / Claude Code / heavy tools on robots. Edit in this repo, then deploy (rsync). Never edit code on a robot.
- **Fake robot first** (`lab_os.robots.fake.FakeArm`), then the real one. Every robot plug-in declares its requirements.
- **Ask before**: anything that makes a real robot move, `sudo`, deleting files, rebooting devices.
- **Hacks are labeled**: `# HACK: …` + a line in `docs/current-focus.md` → "Hacks to clean up".
- **Every surprise** goes in `docs/GOTCHAS.md`.
- **New ideas go into `docs/ideas.md`, not code**, unless they are part of the current focus in `docs/current-focus.md`. `ideas.md` is the single source of truth for ideas; don't list them in other docs.
- **Secrets never in git**: real values in `.env` (gitignored); `.env.example` lists names with fake values.
- **Works offline**: no CDN or internet-loaded code in the web pages. Browser libraries are vendored in `src/lab_os/teleop/web/vendor/` (versions + licenses in its README); robot models in `models/`.
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
uv run lab-os-teleop serve   # teleop: XR page + fake arm (docs/quest-setup.md)
```
Message format between clients and the brain: `docs/protocol.md`. Keep it updated when adding message types. The JARVIS core (brain, slots, plug-ins) should grow out of the teleop code, not be designed up front.

## Style
Python 3.12, ruff-formatted (line length 100), type hints on public functions, short docstrings. Keep things small and readable — this is a solo project that a future student will inherit.

## The builder
Prefers VS Code and graphical tools over the terminal. When a step needs them to run something, give the exact command to paste.
