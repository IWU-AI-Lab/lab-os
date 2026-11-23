# Dev Setup — Claude Code + robots

How development works for the Lab JARVIS project. Companions: `docs/plan/lab-jarvis-log.md`, `docs/plan/current-focus.md`, `docs/guides/network-setup-checklist.md`.

---

## The one rule: robots stay thin
**Never install editors, Claude Code, or other heavy dev tools *on* the robots.**

Why VS Code's SSH was unstable on the Raspbot: VS Code's "Remote-SSH" installs and runs a whole VS Code server program *on the robot*. That eats RAM and storage a small robot computer doesn't have. Plain terminal SSH only runs a tiny shell, so it was fine. The Claude desktop app's SSH mode does something similar (installs Claude Code on the remote machine, needs ~1 GB free) — fine for a full computer, not for a robot.

So: **all the heavy stuff lives on the Linux lab desktop** (or your laptop). Robots only receive files and run their small programs.

---

## The setup
```
 You ──► VS Code + Claude Code extension   (or Claude desktop app, "Local" session)
            │        running on the LINUX LAB DESKTOP ("brain"/dev machine) — or your laptop
            │
            ├── code lives here, in one git repository (also pushed to a private GitHub repo)
            │
            └── plain ssh / rsync ──► raspbot1, raspbot2, pi5-1, jetson1, …
                                      (robots only run small programs)
```

### 1. Home base: the Linux lab desktop
- Install **VS Code** + the **Claude Code extension** (graphical panel inside VS Code — no terminal needed for chatting with Claude).
- Optionally the **Claude desktop app**, using a **Local** session. The Linux version is in beta, so VS Code is the more dependable main option.
- **Don't use cloud sessions for robot work.** Cloud sessions (Claude Code on the web) run on Anthropic's servers, which can't reach devices on the lab's private network. (They're fine for pure-software work — see "Working away from the lab.")

### 2. Using the web UI or phone anyway: Remote Control
Claude Code's **Remote Control** lets you continue a session that's running on the lab desktop from claude.ai/code in a browser or from the Claude phone app. The work still runs on the lab desktop (so it can still reach the robots). Lab desktop must be on and online. (Confirmed working.)

### 3. How Claude reaches the robots
- **Run a command on a robot:** `ssh raspbot1 "command"` — Claude does this itself.
- **Send code to a robot:** a deploy script using `rsync`, then restart the robot's program.
- **Edit robot code:** always edit the copy in the git repo, then deploy. Never edit directly on the robot.

### 4. Making SSH robust
Add to `~/.ssh/config` on the desktop (Claude can do this):
```
Host *
    ServerAliveInterval 30        # keeps idle connections from silently dropping
    ServerAliveCountMax 4
    ControlMaster auto            # reuse one connection for many quick commands
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 10m
```
- **Long-running robot programs run as system services** (systemd), so they survive dropped connections and restart after crashes.
- For hands-on sessions on a robot, use `tmux`.

### 5. Guardrails for Claude
In the project's `.claude/settings.json` (permission rules):
- **Allow without asking:** `ssh` to known robots for read-only checks, `rsync` deploys, `git` commands, running tests.
- **Always ask first:** `sudo`, deleting files, rebooting devices, and (in a coding session) **running anything that makes a real robot move**. The brain's move tools themselves are allowed without asking since 2026-11-14 (`docs/guides/ai-control.md` → "Permissions").
- `AGENTS.md` in the repo tells every AI coding agent the rules (`CLAUDE.md` points to it, for Claude Code) and points to **docs/plan/current-focus.md** and **docs/plan/lab-jarvis-log.md**.
- **Git is the undo button:** commit often.

---

## Branches and folders (2026-10-28)
- **`main` always runs.** Every change reaches it through a pull request (PR).
- **One branch per coding task** (e.g. `xarm-driver`), merged to `main` when tested, then deleted. GitHub can delete merged branches automatically: repo **Settings → General → "Automatically delete head branches"**.
- **One folder per Claude session**, so sessions can't switch branches under each other (git worktrees: separate folders, same repo):
  - `~/lab-os` — coding sessions (the task branch).
  - `~/lab-os-design` — design sessions, branch `design` (`docs/design/`, `config/theme.yaml`).
  - `~/lab-os-planning` — planning/brainstorm sessions, branch `planning` (docs only). Open this folder in VS Code for planning. Merge `planning` into `main` by PR after each planning topic.
- Long-lived branches (`planning`, `design`): GitHub's auto-delete removes them after each merge. Recreate from the planning folder: `git fetch && git merge --ff-only origin/main && git push -u origin planning`.
- Create another folder when needed: `git worktree add ../lab-os-<name> -b <branch>`; list them: `git worktree list`.
- **Parallel coding sessions (2026-11-09):** one folder + branch per step (run `uv sync` in each new folder). Only run steps in parallel that don't share files (e.g. typed chat vs. MCP read tools vs. cameras; not chat vs. screens, which both change the hub page). Each session only edits its own step's lines in `docs/plan/current-focus.md`, and merges `main` into its branch and runs the full tests before its PR. Remove a folder when its branch is merged: `git worktree remove ../lab-os-<name>`.

## Working away from the lab
**Most of the system is plain software and can be built anywhere** — your own laptop at home. Give home its own config folder (its name, devices, venues, `.env`): `uv run lab-os new-place ~/my-lab-os`, then `uv run lab-os serve --config ~/my-lab-os` (`docs/dev/places.md`).

### What works at home
- The core: the brain, slots and plug-in structure, message protocol, model router, agent harness, GUI, boot animation, voice pipeline (with your laptop's mic), personas.
- **Fake ("mock") robots:** a plug-in that accepts the same commands as a real robot and just prints them or draws them on screen. Build every robot plug-in against a fake first — it's faster, safer, and forces a clean robot interface.
- **Simulation (optional):** physics simulators (e.g. MuJoCo) can run a virtual arm for testing inverse kinematics before touching the real one.
- **Quest without a Quest:** a browser WebXR emulator extension, or recorded hand-tracking data replayed into the system.
- **The webcam page without hands in front of it** (`/webcam`): your laptop's camera works. For a repeatable test, Chrome can use a video file as its camera: `--use-fake-device-for-media-stream --use-fake-ui-for-media-stream --use-file-for-fake-video-capture=hands.y4m` (make the `.y4m` with ffmpeg from any video or photo of hands; it loops).
- **Claude Code:** local sessions on your laptop; cloud sessions are also fine here because no lab devices are involved.

### What needs the lab
Real robots (calibration, real motion, delays), the Quest with the real arm, the network/router, the device census.

### How code moves between home and lab
- Keep the repository on **GitHub (private)**. Push from home, pull on the lab desktop (and the reverse).
- **Secrets never go in git** — each machine has its own local secrets file.
- Write code that runs on both your laptop and the lab desktop (Python works on Windows/macOS/Linux; on Windows, WSL gives you a Linux environment).
- **Optional:** if the professor allows, borrowing a small arm (the xArm) and a Quest lets you test real teleop at home.

### Rhythm
Build at home against fakes → test in the lab on real hardware → note surprises in the gotchas list → repeat.

---

## Standards
Device names, accounts, folders on robots, logs, secrets and principles: `docs/plan/lab-jarvis-log.md` → "Standards" (the one list). Hacks: `# HACK:` + a line in `docs/plan/current-focus.md` → "Hacks to clean up".

**Terminal output** (quick job 40, 2026-11-19): `src/lab_os/term.py` holds the one rule, after clig.dev and no-color.org. Colour goes only to a terminal. `NO_COLOR` (not empty) switches it off, and `FORCE_COLOR` switches it on. A new command calls `term.setup_logging()` for its log (the time, amber warnings, red errors; the `colorlog` library). It prints a warning with `print(term.warning(...))` and an error with `term.error(...)`. Its entry point in `pyproject.toml` is `run = term.exit_in_red(main)`, so a `SystemExit("...")` message shows in red. Keep each line's words: lab checks copy them. **The log file** (quick job 85): `lab-os serve` also writes its log to `config/local/logs/brain.log` (the place's `local/logs/` with `--config`), with the date and no colours (`src/lab_os/brainlog.py`). A new file starts at midnight, and 4 days are kept. `lab-os logs` prints the end, `lab-os logs --at 18:14` the minutes around that time. `print()` lines (the banner) are not in it.

---

## Sources
- Claude Code in VS Code: https://code.claude.com/docs/en/vs-code.md
- Claude desktop app (Local / Cloud / SSH sessions; Linux beta): https://code.claude.com/docs/en/desktop.md
- Remote Control: https://code.claude.com/docs/en/remote-control.md
- Claude Code on the web (cloud sessions): https://code.claude.com/docs/en/claude-code-on-the-web.md
