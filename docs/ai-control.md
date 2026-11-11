# AI control: an AI tool drives the arm through the brain

The brain (`lab-os serve`) offers **robot tools** and the **project helper's read tools** (the docs, git, the device list; step 6) over MCP, the standard way AI tools (Claude Code, Codex, Claude Desktop, …) call tools. An AI can read the arm, move it a little at a time and stop it. Every move goes through the same safety path as teleop, asks you first, and is logged. The **fake arm** first (done 2026-11-10: Fable 5.2 did the pretend-cube task with broadly the right moves), then the real `so101-white`, with the builder present (SAFETY.md): "5. On the real arm".

## 1. Start the brain
In a terminal, in the `lab-os` folder:
```bash
uv run lab-os serve
```
It prints the addresses. The one for AI tools is `http://127.0.0.1:8081/mcp` (this computer only; nothing on the network can reach it). Open **http://localhost:8080/monitor** in a browser to watch the arm move. Stop the brain with **Ctrl+C**.

Another port: `uv run lab-os serve --mcp-port 8091` (then use that port below). Without the AI tools: `--mcp-port 0`.

## 2. Connect Claude Code (once per computer)
In a terminal, in the `lab-os` folder:
```bash
claude mcp add --transport http lab-os http://127.0.0.1:8081/mcp
```
This adds the brain to Claude Code for this folder only (scope `local`, stored in your own Claude Code settings, not in git). Check it with `claude mcp list` (it shows "connected" while the brain runs) or `/mcp` inside a Claude Code session. Remove it with `claude mcp remove lab-os`.

Then start a Claude Code session in this folder (the VS Code extension or `claude`). The brain must be running first. If it wasn't, start it and type `/mcp` → `lab-os` → reconnect.

**Which model:** type `/model` and pick Fable 5.2 if it's in the list (the builder's access ends 2026-11-16). Any model works; nothing is tied to Fable.

## 3. Permissions: every move asks
The repo's `.claude/settings.json` sets this for everyone who opens the project:
- **allowed without asking:** `arm_status`, `list_poses` (read only) and `stop` (stopping must never wait for a click). The project tools (below) are read only too and may be added here; until they are, Claude Code asks once per tool;
- **always asks:** `move_joints`, `gripper`, `move_to`, `go_to_pose`. These are "ask" rules, so they ask even if someone allows them elsewhere. **Never allow-list the move tools.** Approve each move only after reading what it will do.

## 4. Try it
In the Claude Code session, for example:
> Use the lab-os tools. Check the arm, then move the gripper 3 cm lower, pointing straight down.

or the step-2 goal:
> Pick up the cube that's 15 cm in front of the base and put it 10 cm to the left.

Watch **AI Control** (`/ai`, or the hub's AI Control button) while you approve each move: each call appears there as it happens, with what it did. **STOP** on any page (teleop, monitor) stops an AI move at once. The AI is then told not to move again until you say so.

## The tools
Positions are **cm from the arm's base**: x forward (where the arm faces with `shoulder_pan` at 0), y to the arm's left, z up, with 0 = the table under the base. **Tool angle:** the gripper's tilt, 0 = pointing up, 90 = forward, 180 = straight down. Joints use the shared names, in degrees.

| Tool | Tier | What it does |
|---|---|---|
| `arm_status` | read | Joints, gripper opening (%), gripper position (cm) and tool angle, limits, who has control (`free` / `teleop` / `ai`), held still or not, whether the venue allows motion, the per-call limits |
| `list_poses` | read | Named poses (`config/poses.yaml`: `home`, `rest`, …) |
| `move_joints` | move | Some joints to angles, or by amounts (`relative: true`) |
| `gripper` | move | 0 = closed … 100 = fully open |
| `move_to` | move | The gripper point in a **straight line** to (x, y, z), optionally with a tool angle. Says "can't reach" instead of guessing |
| `go_to_pose` | move | A named pose |
| `stop` | always | Stop now and hold still, whoever has control |

**Project tools** (read; the hub's own chat uses the same ones):
| Tool | What it does |
|---|---|
| `project_status` | The current focus: every step, done or not, and the next one |
| `list_docs` / `read_doc` / `search_docs` | The docs (one doc, or one section of it, e.g. `read_doc("ideas", "On hold")`), and a search. `docs/design/` is left out until the reveal |
| `git_status` / `git_log` | Branch, changed files, recent commits (nothing is fetched) |
| `list_devices` | The place's device list (off limits, active in the venue) |

For example: "Use the lab-os tools: what's next, and what's on hold? Then draft a plan for the next step."

Every move returns where the arm **really** ended up (joints, gripper %, position, tool angle), plus a `clipped` list saying what was limited.

## Safety rules (the brain clips and refuses; it never trusts the numbers it's given)
- **Same path as teleop:** moves run through the teleop loop: the arm's soft limits (3° inside the real ones), the venue's `max_speed_scale`, and a capped speed (all joints arrive together).
- **Small steps per call** (`ai_tools` in `config/venues/<venue>.yaml`): at most **30° per joint** (`move_joints`, `go_to_pose`; the gripper is exempt) or **10 cm** (`move_to`). A bigger request goes part of the way and says so, and the AI calls again (with another approval).
- **Never into the table:** nothing may go below `min_z_cm` (1 cm), checked along the whole path. An arm already lower than that (moved by hand) may move up, never further down.
- **Refused, nothing moves:** the venue has `motion_allowed: false`; **teleop has control** (a teleop page or the Quest is driving); another AI move is still running; an unknown arm, joint or pose; a point out of reach or a path where the arm would flip; anything that isn't a number.
- **One controller at a time:** while an AI move runs, teleop input is refused ("the AI tools have control") and the pages show control "the AI tools". The hub doesn't reset to its start screen mid-move.
- **Stopping:** `stop`, STOP on any page, or the tool call being cancelled mid-move all freeze the arm.

## 5. On the real arm (`so101-white`, in the lab)
Only with the builder at the arm, hand near STOP. Ask before the first real move (CLAUDE.md). The green arm (`so101-green`) is never touched: the brain refuses its ports.

**Once, on the lab desktop** (the `so101` extra is LeRobot, ~5 GB; plain `uv sync` removes it again):
```bash
cd ~/lab-os && git pull && uv sync --extra so101
ls -l /dev/serial/by-id/      # so101-white is …5B41532410-if00; leave the …1599 and …3501 ones (green) alone
```

**Each time:**
1. Clear the table around the arm; put the cube where you'll describe it (measure from the middle of the base: cm in front, cm to the left).
2. Start the brain with the real arm, slowly:
   ```bash
   uv run --extra so101 lab-os serve --arm so101-white --speed 0.3
   ```
   It prints "AI tools can move the REAL so101-white". Open **http://localhost:8080/ai** (AI Control: the arm from the side, where each move aims, every call and its outcome, STOP) or `/monitor` (3D) to watch; on a second monitor of this computer they can stay open full screen (`docs/hub.md` → "Other monitors"). To show the hub on the Newline at the same time, add `--host 0.0.0.0`: other screens are then view-only (their STOP works).
3. In the Claude Code session (VS Code): `/mcp` → `lab-os` → reconnect (the brain restarted), `/model` → Fable 5.2.
4. Small steps first, approving each one after reading it:
   > Use the lab-os tools. Read the arm's status and tell me where the gripper is.

   > Go to the home pose.

   > Move the gripper 3 cm lower, pointing straight down.

   Then the step-2 task, with your real measurements:
   > There's a cube 15 cm in front of the base and 5 cm to the left. Pick it up and put it down 10 cm to the left of where it was. Go slowly, one move at a time, and tell me before each move what you'll do.
5. **Stop:** STOP on any page (or Esc on the teleop page) stops it at once; Ctrl+C in the brain's terminal stops the brain (the SO-101 then goes limp, so hold it if it's lifted). **Never "always allow"** a move tool.
6. Afterwards: `logs/ai-tools/` has every call of this run. Note in `docs/current-focus.md` (step 2) what worked and what didn't.

Not checked on the real arm yet: the `rest` pose (computed only; `docs/current-focus.md` → "Hacks to clean up"). Prefer `home` until it is.

## "Arrived" or "stopped short"
After each move the brain holds the target for half a second (so a slow joint can catch up), then reads where the motors really are and compares that with the target. Within 0.5 cm (2° per joint) the result is `arrived`; otherwise `stopped_short` with how far off (`off_by_cm`), which joints fell short (`joints_short_deg`) and a sentence (`message`). A gripper that closes on something says "stopped at 30 % open instead of 0 % (it may be holding something)". The AI Control page (`/ai`) shows these as "short". Why: blind on the real arm, `move_to` used to say "arrived" 1.6 cm short (GOTCHAS 2026-11-10).

## The log
Every call (time, tool, arguments, outcome `ok` / `clipped` / `short` / `refused` / `stopped` / `error`, and the result) goes to `logs/ai-tools/<date>_<time>.jsonl`, one file per brain run (not in git). Use it to compare runs later.

## Other AI tools
Anything that speaks MCP over "streamable HTTP" can connect to `http://127.0.0.1:8081/mcp` on this computer (Codex, Claude Desktop, …). Make it ask before each move tool, as above.

## Later
- Cameras (focus step 3), access from other computers with a token (after this focus).

Code: `src/lab_os/tools/robot.py` (the tools and their rules), `tools/mcp_server.py` (MCP), `tools/calllog.py`; tests in `tests/test_robot_tools.py`.
