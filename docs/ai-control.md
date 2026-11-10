# AI control: an AI tool drives the arm through the brain

The brain (`lab-os serve`) offers **robot tools** over MCP, the standard way AI tools (Claude Code, Codex, Claude Desktop, …) call tools. An AI can read the arm, move it a little at a time and stop it. Every move goes through the same safety path as teleop, asks you first, and is logged. Today: the **fake arm**. The real `so101-white` comes later, with the builder present (SAFETY.md).

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
- **allowed without asking:** `arm_status`, `list_poses` (read only) and `stop` (stopping must never wait for a click);
- **always asks:** `move_joints`, `gripper`, `move_to`, `go_to_pose`. These are "ask" rules, so they ask even if someone allows them elsewhere. **Never allow-list the move tools.** Approve each move only after reading what it will do.

## 4. Try it
In the Claude Code session, for example:
> Use the lab-os tools. Check the arm, then move the gripper 3 cm lower, pointing straight down.

or the step-2 goal:
> Pick up the cube that's 15 cm in front of the base and put it 10 cm to the left.

Watch the monitor page while you approve each move. **STOP** on any page (teleop, monitor) stops an AI move at once. The AI is then told not to move again until you say so.

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

Every move returns where the arm **really** ended up (joints, gripper %, position, tool angle), plus a `clipped` list saying what was limited.

## Safety rules (the brain clips and refuses; it never trusts the numbers it's given)
- **Same path as teleop:** moves run through the teleop loop: the arm's soft limits (3° inside the real ones), the venue's `max_speed_scale`, and a capped speed (all joints arrive together).
- **Small steps per call** (`ai_tools` in `config/venues/<venue>.yaml`): at most **30° per joint** (`move_joints`, `go_to_pose`; the gripper is exempt) or **10 cm** (`move_to`). A bigger request goes part of the way and says so, and the AI calls again (with another approval).
- **Never into the table:** nothing may go below `min_z_cm` (1 cm), checked along the whole path. An arm already lower than that (moved by hand) may move up, never further down.
- **Refused, nothing moves:** the venue has `motion_allowed: false`; **teleop has control** (a teleop page or the Quest is driving); another AI move is still running; an unknown arm, joint or pose; a point out of reach or a path where the arm would flip; anything that isn't a number.
- **One controller at a time:** while an AI move runs, teleop input is refused ("the AI tools have control") and the pages show control "the AI tools". The hub doesn't reset to its start screen mid-move.
- **Stopping:** `stop`, STOP on any page, or the tool call being cancelled mid-move all freeze the arm.

## The log
Every call (time, tool, arguments, outcome `ok` / `clipped` / `refused` / `stopped` / `error`, and the result) goes to `logs/ai-tools/<date>_<time>.jsonl`, one file per brain run (not in git). Use it to compare runs later.

## Other AI tools
Anything that speaks MCP over "streamable HTTP" can connect to `http://127.0.0.1:8081/mcp` on this computer (Codex, Claude Desktop, …). Make it ask before each move tool, as above.

## Later
- **The real arm:** `uv run --extra so101 lab-os serve --arm so101-white`, only with the builder present. The brain then prints that AI tools can move a real arm. First moves small, watching, hand near STOP. The `rest` pose is computed, not yet checked on the real arm.
- Cameras (focus step 3), read tools for the project (step 6), access from other computers with a token (after this focus).

Code: `src/lab_os/tools/robot.py` (the tools and their rules), `tools/mcp_server.py` (MCP), `tools/calllog.py`; tests in `tests/test_robot_tools.py`.
