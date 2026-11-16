# AI control: an AI tool drives the arm through the brain

The brain (`lab-os serve`) offers **robot tools** and the **project helper's read tools** (the docs, git, the device list; step 6) over MCP, the standard way AI tools (Claude Code, Codex, Claude Desktop, …) call tools. An AI can read the arm, move it a little at a time and stop it. Every move goes through the same safety path as teleop and is logged; Claude Code doesn't ask before each one (since 2026-11-14: section 3), so watch the arm with STOP in reach. The **fake arm** first (done 2026-11-10: Fable 5.2 did the pretend-cube task with broadly the right moves), then the real `so101-white`, with the builder present (SAFETY.md): "5. On the real arm".

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

## 3. Permissions
The repo's `.claude/settings.json` (decision 2026-11-13, built 2026-11-14) **allows every brain tool without asking**, for everyone who opens the project: the read tools (`arm_status`, `list_poses`, `pose_view`, `camera_snapshot`, the project tools below), `stop`, and the move tools (`move_joints`, `gripper`, `move_to`, `go_to_pose`). Nothing waits for a click; what keeps it safe is the brain itself: **STOP** on every screen, the soft joint limits and one controller at a time always stay, plus the per-move limit, the speed cap and the floor (safety rules below). Someone stays at a real arm with STOP in reach.

A coding session (one working on lab-os's code) still asks you before it runs anything that moves a real arm (CLAUDE.md); a session you started to drive the arm uses the tools freely. To be asked before each move anyway (in your own Claude Code settings only): add the four move tools as `"ask"` rules in `.claude/settings.local.json` (in Claude Code, ask beats allow).

## 4. Try it
In the Claude Code session, for example:
> Use the lab-os tools. Check the arm, then move the gripper 3 cm lower, pointing straight down.

or the step-2 goal:
> Pick up the cube that's 15 cm in front of the base and put it 10 cm to the left.

Watch **AI Control** (`/ai`, or the hub's AI Control button) while it moves: each call appears there as it happens, with what it did. **STOP** on any page (teleop, monitor) stops an AI move at once. The AI is then told not to move again until you say so.

## The tools
Positions are **cm from the arm's base**: x forward (where the arm faces with `shoulder_pan` at 0), y to the arm's left, z up, with 0 = the table under the base. **Tool angle:** the gripper's tilt, 0 = pointing up, 90 = forward, 180 = straight down. Joints use the shared names, in degrees.

| Tool | Tier | What it does |
|---|---|---|
| `arm_status` | read | Joints, gripper opening (%), gripper position (cm) and tool angle, limits, who has control (`free` / `teleop` / `ai`), held still or not, whether the venue allows motion, the per-call limits |
| `list_poses` | read | Named poses (`config/poses.yaml`: `home`, `rest`, …) |
| `pose_view` | read | A **picture** of the arm's 3D model as it is now (side + top, grid in cm, the table, the gripper point, the last `move_to` target), with optional `marks` where the AI thinks things are. No camera: see "Seeing the pose" |
| `move_joints` | move | Some joints to angles, or by amounts (`relative: true`) |
| `gripper` | move | 0 = closed … 100 = fully open |
| `move_to` | move | The gripper point in a **straight line** to (x, y, z), optionally with a tool angle. Says "can't reach" instead of guessing |
| `go_to_pose` | move | A named pose |
| `stop` | always | Stop now and hold still, whoever has control |

**Project tools** (read; the hub's own chat uses the same ones):
| Tool | What it does |
|---|---|
| `project_status` | The current focus: every step, done or not, and the next one |
| `list_docs` / `read_doc` / `search_docs` | The docs (one doc, or one section of it, e.g. `read_doc("ideas", "On hold")`), and a search. Includes `docs/design/` (since 2026-11-12) |
| `git_status` / `git_log` | Branch, changed files, recent commits (nothing is fetched) |
| `list_devices` | The place's device list (off limits, borrowed, active in the venue) |

For example: "Use the lab-os tools: what's next, and what's on hold? Then draft a plan for the next step."

Every move returns where the arm **really** ended up (joints, gripper %, position, tool angle), plus a `clipped` list saying what was limited.

## Safety rules (the brain clips and refuses; it never trusts the numbers it's given)
- **Same path as teleop:** moves run through the teleop loop: the arm's soft limits (3° inside the real ones), the venue's `max_speed_scale`, and a capped speed (all joints arrive together).
- **Small steps per call** (`ai_tools` in `config/venues/<venue>.yaml`): at most **30° per joint** (`move_joints`, `go_to_pose`; the gripper is exempt) or **10 cm** (`move_to`). A bigger request goes part of the way and says so, and the AI calls again.
- **Never into the table:** nothing may go below `min_z_cm` (−0.5 cm in both venues since 2026-11-14, 1 cm before: the arm stands on the stand camera's base, so the table is below its zero; teleop uses the same number), checked along the whole path. An arm already lower than that (moved by hand) may move up, never further down.
- **Refused, nothing moves:** the venue has `motion_allowed: false`; **teleop has control** (a teleop page or the Quest is driving); another AI move is still running; an unknown arm, joint or pose; a point out of reach or a path where the arm would flip; anything that isn't a number.
- **One controller at a time:** while an AI move runs, teleop input is refused ("the AI tools have control") and the pages show control "the AI tools". The hub doesn't reset to its start screen mid-move.
- **Switching limits off** (lab only, on by default): the per-move limit, the speed cap and the floor can each be set to `off` under `limits:` in the venue file or on the hub's Settings page (→ Safety limits; restart the brain). `arm_status` then says `"off"` for that number. Never on a public venue or the visit-day venue (`limits_locked: true`). The soft joint limits, one controller at a time and STOP always stay. SAFETY.md → "Limits".
- **Stopping:** `stop`, STOP on any page, or the tool call being cancelled mid-move all freeze the arm.

## 5. On the real arm (`so101-white`, in the lab)
Only with the builder at the arm, hand near STOP. Ask before the first real move (CLAUDE.md). The green follower works the same way (below: "The green arm").

**Once, on the lab desktop** (the `so101` extra is LeRobot, ~5 GB; plain `uv sync` removes it again):
```bash
cd ~/lab-os && git pull && uv sync --extra so101
ls -l /dev/serial/by-id/      # so101-white is …5B41532410-if00; the green follower …3501, its leader …1599
```

**Each time:**
1. Clear the table around the arm; put the cube where you'll describe it (measure from the middle of the base: cm in front, cm to the left).
2. Start the brain with the real arm, slowly:
   ```bash
   uv run --extra so101 lab-os serve --arm so101-white --speed 0.3
   ```
   It prints "AI tools can move the REAL so101-white". Open **http://localhost:8080/ai** (AI Control: the arm from the side, where each move aims, every call and its outcome, STOP) or `/monitor` (3D) to watch; on a second monitor of this computer they can stay open full screen (`docs/guides/hub.md` → "Other monitors"). To show the hub on the Newline at the same time, add `--host 0.0.0.0`: other screens are then view-only (their STOP works).
3. In the Claude Code session (VS Code): `/mcp` → `lab-os` → reconnect (the brain restarted), `/model` → Fable 5.2.
4. Small steps first (Claude Code doesn't ask before moves: watch, with STOP in reach):
   > Use the lab-os tools. Read the arm's status and tell me where the gripper is.

   > Go to the home pose.

   > Move the gripper 3 cm lower, pointing straight down.

   Then the step-2 task, with your real measurements:
   > There's a cube 15 cm in front of the base and 5 cm to the left. Pick it up and put it down 10 cm to the left of where it was. Go slowly, one move at a time, and tell me before each move what you'll do.
5. **Stop:** STOP on any page (or Esc on the teleop page) stops it at once; Ctrl+C in the brain's terminal stops the brain (the SO-101 then goes limp, so hold it if it's lifted).
6. Afterwards: `logs/ai-tools/` has every call of this run. Note in `docs/plan/current-focus.md` (step 2) what worked and what didn't.

### The green arm (`so101-green`, since step 11)
The training set's follower, borrowed from the training project (CLAUDE.md, "Hard rules"). The same tools and safety as the white arm, plus:
```bash
uv run --extra so101 lab-os serve --arm so101-green --speed 0.3
```
- **Close LeLab first** (and any recording or training run). If another program has the green port open, the brain refuses with a sentence naming it ("so101-green is in use by lelab (pid …): one program per port") and opens nothing.
- **Its calibration is LeRobot's**, read from `~/.cache/huggingface/lerobot/calibration/robots/<type>/<id>.json` (the only file there, or the one named by `calibration_id` in `devices.yaml`). lab-os copies it into a temporary folder and gives LeRobot the copy, so the original can't be written. If the motors disagree with the file, the brain stops and says to check the arm in LeLab: lab-os never recalibrates it, and `so101_setup` refuses the green arms outright.
- **Name it:** the green arm is never a default (`--arm` without a name, `python -m lab_os.robots.so101`), so the white arm can't be swapped for it by accident. Read-only check: `uv run --extra so101 python -m lab_os.robots.so101 so101-green --watch`.
- It's active in the `lab` venue only (`config/venues/lab.yaml`), not on visit days.
- Connecting with motion on writes LeRobot's usual settings (PID gains, acceleration, the gripper's current limit) to the motors, like LeLab does when it connects. Never IDs, baud rate, firmware or calibration.

Not checked on the real arm yet: the `rest` pose (computed only; `docs/plan/current-focus.md` → "Hacks to clean up"). Prefer `home` until it is.

## Looking through a camera (`camera_snapshot`)
`camera_snapshot(camera, width_px=640)` (read tier) takes one real picture from a camera in `devices.yaml` and returns it as a JPEG. The hub's chat doesn't get it (text only). A camera another program has open is refused. These cameras start black and then flash white, so it waits (up to ~6 s) until the brightness settles. The white arm's: `so101-white-cam-stand` (the stand camera, about 2 ft up behind the arm, looking forward and down) and `so101-white-cam-wrist` (the wrist camera, along the jaws); called `-cam-a`/`-cam-b` until 2026-11-16. They share USB sockets with the green set's cameras for now (`docs/plan/current-focus.md` → "Hacks to clean up").

## Seeing the pose (`pose_view`)
Without a camera the AI can't see the arm. `pose_view` draws the arm's 3D model (`models/so101`) in the pose its motors report, as a picture the AI looks at:
- **left, side view in the arm's own plane** (it turns with `shoulder_pan`, so the arm is never seen end-on): across = reach from the base's turning axis, up = height; the table is the brown band;
- **right, top view**, as if standing behind the arm: forward (x) up the picture, the arm's left (+y) on the left;
- a **red dot** at the gripper point (with a dotted line down to the table), a **magenta ×** at the last `move_to` target, and **blue marks** the AI passes in `marks`, e.g. `[{"x_cm": 15, "y_cm": 5, "z_cm": 1.5, "label": "cube", "size_cm": 3}]` (at most 10). A mark with `size_cm` is a square of that size.

It only knows what the joints say: objects appear only as the AI's own marks. Use it after a move and before gripping: "Look with pose_view, with a mark where the cube is, before you close the gripper." **To see the same picture yourself:** open http://localhost:8080/api/pose-view.png (no marks; reload for a new one). The first picture after the brain starts takes about a second (the meshes load), then about 0.2 s. The hub's own chat doesn't get it (it reads text only). Only arms with a 3D model (the SO-101s); others are refused.

## "Arrived" or "stopped short"
After each move the brain holds the target for half a second (so a slow joint can catch up), then reads where the motors really are and compares that with the target. Within 0.5 cm (2° per joint) the result is `arrived`; otherwise `stopped_short` with how far off (`off_by_cm`), which joints fell short (`joints_short_deg`) and a sentence (`message`). A gripper that closes on something says "stopped at 30 % open instead of 0 % (it may be holding something)". The AI Control page (`/ai`) shows these as "short". Why: blind on the real arm, `move_to` used to say "arrived" 1.6 cm short (GOTCHAS 2026-11-10).

## The log
Every call (time, tool, arguments, outcome `ok` / `clipped` / `short` / `refused` / `stopped` / `error`, and the result) goes to `logs/ai-tools/<date>_<time>.jsonl`, one file per brain run (not in git). Use it to compare runs later.

## Other AI tools
Anything that speaks MCP over "streamable HTTP" can connect to `http://127.0.0.1:8081/mcp` on this computer (Codex, Claude Desktop, …). Its own permission settings decide whether it asks before a move tool; the brain's limits and STOP apply either way.

## Later
- Access from other computers with a token (`docs/plan/lab-jarvis-log.md` → "AI-assisted development").

Code: `src/lab_os/tools/robot.py` (the tools and their rules), `tools/mcp_server.py` (MCP), `tools/calllog.py`; tests in `tests/test_robot_tools.py`.
