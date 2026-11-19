# AI control: an AI tool drives the arm through the brain

The brain (`lab-os serve`) gives AI tools two sets of tools over MCP (the standard way that AI tools such as Claude Code, Codex and Claude Desktop call tools):
- the **robot tools:** read the arm, move it a little at a time, stop it;
- the **project tools:** read the docs, git and the device list.

Every move goes through the same safety path as teleop, and the brain writes every call to a log. Claude Code does not ask before each move (section 3), so watch the arm and keep STOP near you. Use the **fake arm** first. Then use the real `so101-white` with the builder at the arm (`SAFETY.md`, section 5).

## 1. Start the brain
In a terminal, in the `lab-os` folder, run:
```bash
uv run lab-os serve
```
The brain shows its addresses. The address for AI tools is `http://127.0.0.1:8081/mcp`. Only this computer can use it; nothing on the network can connect to it. Open **http://localhost:8080/monitor** in a browser to watch the arm. To stop the brain, press **Ctrl+C**.

For another port, run `uv run lab-os serve --mcp-port 8091` and use that port below. To start the brain without the AI tools, add `--mcp-port 0`.

## 2. Connect Claude Code (one time for each computer)
In a terminal, in the `lab-os` folder, run:
```bash
claude mcp add --transport http lab-os http://127.0.0.1:8081/mcp
```
This adds the brain to Claude Code for this folder only (scope `local`, kept in your own Claude Code settings, not in git). To check it, run `claude mcp list` (it shows "connected" while the brain runs), or type `/mcp` in a Claude Code session. To remove it, run `claude mcp remove lab-os`.

Then start a Claude Code session in this folder (the VS Code extension or `claude`). Start the brain first. If the brain was not running, start it, then type `/mcp` → `lab-os` → reconnect.

**The model:** any model works. Nothing depends on one model. Type `/model` to change it.

## 3. Permissions
The repository's `.claude/settings.json` **allows every brain tool without asking**, for everyone who opens the project (decision 2026-11-13). That includes the read tools, `stop`, and the move tools (`move_joints`, `gripper`, `move_to`, `go_to_pose`, `pick_at`). Nothing waits for a click. The brain itself keeps it safe: STOP, the limits (below), and one controller at a time. A person stays at a real arm with STOP near.

A coding session (a session that works on lab-os's code) still asks you before it runs anything that moves a real arm (`CLAUDE.md`). A session that you started to drive the arm uses the tools freely.

To be asked before each move in your own Claude Code only: add the move tools as `"ask"` rules in `.claude/settings.local.json`. In Claude Code, "ask" wins over "allow".

## 4. Try it
In the Claude Code session, type for example:
> Use the lab-os tools. Check the arm, then move the gripper 3 cm lower, pointing straight down.

Or:
> Pick up the cube that's 15 cm in front of the base and put it 10 cm to the left.

Watch **AI Control** (`/ai`, or the hub's AI Control button) during the moves. It shows each call as it happens, with the result. **STOP** on any page stops an AI move immediately. The AI is then told not to move again until you say so.

## The tools
**Positions** are in cm from the arm's base:
- x: forward (where the arm points with `shoulder_pan` at 0);
- y: to the arm's left;
- z: up, with 0 at the table.

An arm on a plate has its table height in `config/devices.yaml` (`table_z_cm`; `so101-white`: −1.6). So every height that the tools take and give is from the table, not from the bottom of the base. `arm_status` says this in `frame` and `table_z_cm`.

**Tool angle:** the gripper's tilt. 0 = pointing up, 90 = forward, 180 = straight down. Joints use the shared names, in degrees.

| Tool | Tier | What it does |
|---|---|---|
| `arm_status` | read | The joints, the gripper's opening (%), the gripper's position (cm) and tool angle, the limits, who has control (`free`, `teleop`, `ai`), if it holds still, if the venue allows motion, the limits for each call |
| `list_poses` | read | The named poses (`config/poses.yaml`). `ready`: the working pose, where teleop starts. `home`: the folded pose where the arm stays |
| `pose_view` | read | A **picture** of the arm's 3D model in its pose now (side and top, a cm grid, the table, the gripper point, the last `move_to` target), with optional `marks` where the AI thinks things are. No camera ("Seeing the pose" below) |
| `camera_snapshot` | read | One real picture from a camera. A camera with a table map gets the table's **cm grid** ("Table map" below) |
| `table_point` | read | One pixel of such a picture → x and y on the table, in cm |
| `move_joints` | move | Some joints to angles, or by amounts (`relative: true`) |
| `gripper` | move | 0 = closed, 100 = fully open |
| `move_to` | move | The gripper point in a **straight line** to (x, y, z), with an optional tool angle. It says "can't reach" instead of a guess |
| `go_to_pose` | move | A named pose |
| `pick_at` | move | A full pick in one call: open, above, straight down, close, lift ("Picking up" below) |
| `stop` | always | Stop now and hold, for any controller |

**Project tools** (read; the hub's chat uses the same tools):
| Tool | What it does |
|---|---|
| `project_status` | The current focus: each step, done or not, and the next step |
| `list_docs`, `read_doc`, `search_docs` | The docs (one doc, or one section, for example `read_doc("ideas", "On hold")`) and a search. Includes `docs/design/` |
| `git_status`, `git_log` | The branch, the changed files, the recent commits (nothing is fetched) |
| `list_devices` | The place's device list (off limits, borrowed, active in the venue) |
| `lab_status` | The lab in one call: the arm, the devices with the hub open, voice, AI, spend, the next step, warnings |

For example: "Use the lab-os tools: what's next, and what's on hold? Then make a plan for the next step."

Each move gives back where the arm **really** stopped (joints, gripper %, position, tool angle), and a `clipped` list of what the brain limited.

## Limits
The brain limits and refuses. It never trusts the numbers that it gets. This section is the reference for these limits; `SAFETY.md` has the rules for people.
- **The same path as teleop:** moves go through the teleop loop: the arm's soft limits (3° inside the real limits), the venue's `max_speed_scale`, and a limited speed (all joints arrive together).
- **Small steps for each call** (`ai_tools` in `config/venues/<venue>.yaml`): at most **30° for each joint** (`move_joints`, `go_to_pose`; not the gripper) or **10 cm** (`move_to`). A larger request goes part of the way and says so. The AI then calls again.
- **The floor:** nothing goes below `min_z_cm`, in cm above the table. It is **1.1 cm** in both venues (since 2026-11-18, when heights started at the table). The brain checks the whole path. Teleop uses the same number. An arm that is already lower (moved by hand) can move up, but never further down. If the real arm still touches the table (it bends down under its own weight when stretched out), make the number higher.
- **Refused, nothing moves:** the venue has `motion_allowed: false`; **teleop has control** (a teleop page or the Quest drives); another AI move still runs; an unknown arm, joint or pose; a point out of reach or a path where the arm would flip; anything that is not a number.
- **One controller at a time:** while an AI move runs, teleop input is refused ("the AI tools have control"), and the pages show the AI tools as the controller. The hub does not go back to its start screen during a move.
- **Switching limits off:** the limit for each call, the speed cap and the floor are on by default. You can set each one to `off` under `limits:` in the venue file, or in Settings → Safety Limits and Shut Down. Then restart the brain. `arm_status` then shows `"off"` for that number. A public venue or a venue with `limits_locked: true` cannot switch them off (the lab has neither). The soft joint limits, one controller at a time and STOP always stay.
- **Stopping:** `stop`, STOP on any page, or a tool call that is cancelled during a move all freeze the arm.
- **Unplugged:** if an SO-101's USB cable is removed, the move ends with `"result": "disconnected"`. `arm_status` says `"connected": false`, with the reason. Every move is refused until the arm is back. The brain connects again by itself when the cable is back (quick job 27).

## 5. On the real arm (`so101-white`, in the lab)
Do this only with the builder at the arm, with a hand near STOP. In a coding session, ask before the first real move (`CLAUDE.md`). The green follower works the same way ("The green arm" below).

**One time, on the lab desktop:** the `so101` extra is LeRobot (about 5 GB). Plain `uv sync` removes it again.
```bash
cd ~/lab-os && git pull && uv sync --extra so101
ls -l /dev/serial/by-id/      # so101-white is …5B41532410-if00; the green follower …3501, its leader …1599
```

**Each time:**
1. Clear the table around the arm. Put the cube where you will describe it. Measure from the center of the base: cm in front, cm to the left.
2. Start the brain with the real arm, slowly:
   ```bash
   uv run --extra so101 lab-os serve --arm so101-white --speed 0.3
   ```
   It says "AI tools can move the REAL so101-white". To watch, open **http://localhost:8080/ai** (AI Control: the arm from the side, where each move goes, each call and its result, STOP) or `/monitor` (3D). On a second monitor of this computer they can stay open in full screen (`docs/guides/hub.md` → "Other monitors"). To show the hub on the Newline at the same time, add `--host 0.0.0.0`. Other screens then only watch (their STOP works).
3. In the Claude Code session, type `/mcp` → `lab-os` → reconnect (the brain restarted).
4. Start with small steps. Claude Code does not ask before moves, so watch with STOP near:
   > Use the lab-os tools. Read the arm's status and tell me where the gripper is.

   > Go to the ready pose.

   > Move the gripper 3 cm lower, pointing straight down.

   Then the full task, with your real measurements:
   > There's a cube 15 cm in front of the base and 5 cm to the left. Pick it up and put it down 10 cm to the left of where it was. Go slowly, one move at a time, and tell me before each move what you'll do.
5. **Stop:** STOP on any page (or Esc on the teleop page) stops it immediately. Ctrl+C in the brain's terminal stops the brain. The SO-101 then goes limp, so hold it if it is lifted.
6. After: `logs/ai-tools/` has every call of this run. Write in `docs/plan/current-focus.md` (step 2) what worked and what did not.

### The green arm (`so101-green`)
The training set's follower, borrowed from the training project. Its rules are in `CLAUDE.md` → "Hard rules". It has the same tools and limits as the white arm.
```bash
uv run --extra so101 lab-os serve --arm so101-green --speed 0.3
```
- **Close LeLab first,** and stop any recording or training run. If another program has the green port open, the brain refuses with a sentence that names it ("so101-green is in use by lelab (pid …): one program per port") and opens nothing.
- **The calibration:** lab-os drives with its own copy of the training calibration (`calibration/so101-green/so101-green.json`, and `calibration/so101-green-leader/`). It refuses with a sentence if the copy is different from the training file (the sentence gives the `cp` command to copy it again), or if the motors hold a different calibration. Then start teleop once in LeLab, or start LeRobot's command line and press ENTER at its calibration question (never `c`). `devices.yaml` names the training file (`training_calibration:`).
- **Name it:** the green arm is never the default arm, so the brain cannot use it instead of the white arm by mistake. To only read it: `uv run --extra so101 python -m lab_os.robots.so101 so101-green --watch`.
- It is active in the `lab` and `visit-day` venues.
- When the brain connects with motion on, it writes LeRobot's usual settings (PID gains, acceleration, the gripper's current limit) to the motors, as LeLab does. Never IDs, baud rate, firmware or calibration.

**Poses:** `ready` is the working pose (reaching forward, about 5 cm up; teleop and the fake arm start there). `home` is the folded pose where the builder leaves the arm, with the gripper a little open, just above where it rests (quick job 30). Two joints of `home` (`shoulder_lift`, `elbow_flex`) are past their soft limits by 6.3° and 3.6°, so the move stops at the limits and says so (`clipped`). `wrist_flex` is 55 instead of the real 75.9: with 75.9 the 3D model puts the gripper about 1 cm below the table, and the floor refuses the move. When the brain lets go of the arm, it settles into the real rest. Not yet tried on the real arm: lab check F.3.

## Looking through a camera (`camera_snapshot`)
`camera_snapshot(camera, width_px=640)` takes one real picture from a camera in `devices.yaml` and gives it back as a JPEG. The hub's chat does not get it (it takes text only). If another program has the camera open, the brain refuses. These cameras start black and then flash white, so the brain waits (up to about 6 s) until the brightness is stable.

The cameras:
- `so101-white-cam-stand`: the white arm's stand camera, about 60 cm up behind the arm, looking forward and down.
- `so101-white-cam-wrist`: the white arm's wrist camera, along the jaws.
- `so101-green-cam-stand` and `so101-green-cam-wrist`: the same for the green arm.

The white arm's cameras use the same USB sockets as the green set's for now (socket 7 = wrist, 8 = stand on both sets; `docs/plan/current-focus.md` → "Hacks to clean up").

## Table map: the stand camera's cm grid
A printed sheet tells lab-os where the stand camera's pixels are on the table. Then its pictures get a **cm grid** (yellow lines = x forward, blue = y, every 5 cm, numbers every 10 cm, a red dot at the center of the base). The AI reads where the cube is instead of a guess (the guess was 8 cm wrong: GOTCHAS 2026-11-12). `table_point(camera, x_px, y_px)` also changes a pixel into cm. This is Google's method (`docs/dev/existing-work-teleop-ai.md`). It is correct only on the table's surface: read the point where an object **touches** the table. The wrist camera makes the position more exact.

**Do this one time, and again when the camera or the arm moves:**
1. Print `models/charuco/calibration-sheet-letter.pdf` at **100 %** ("Actual size", not "Fit to page"). Measure one square: is it 35 mm? If not, add `--square-mm <your measurement>` in step 4.
2. Put the sheet flat in front of the arm, with the long edge pointing straight away from the arm, approximately in the center.
3. Find the sheet's **"Board origin" corner** (printed on it, top left, seen from the arm) in the arm's cm. Move the jaw tips onto it (teleop) and read the gripper's x and y (`/ai`, or `arm_status`). A ruler from the center of the base also works, but the AI uses the arm's own numbers.
4. Move the arm off the sheet. Then run (the brain can keep running; the camera opens only for a moment):
   ```bash
   uv run --extra so101 lab-os table-map so101-white-cam-stand --origin <x cm> <y cm>
   ```
   It says how many of the 24 corners it found and how far the worst corner is wrong (5 mm or less is good). It saves `config/table-maps/so101-white-cam-stand.yaml` and writes a picture with the grid to `logs/table-maps/`. Open the picture: the red dot must be on the base, and the lines must follow the squares.
5. Remove the sheet. From now on, `camera_snapshot` of that camera has the grid (`grid: false` gives the plain picture).

To try it without a camera, add `--image picture.jpg` to use a saved picture.

## Picking up (`pick_at`)
`pick_at(x_cm, y_cm, height_cm=2.5, open_pct=100)` picks up the object that stands at (x, y) on the table, in one call instead of about 17 small calls. It has five steps, each through the same safety path as `gripper` and `move_to`:
1. Open the gripper.
2. Go to `height_cm` + 6 cm above the object, pointing straight down.
3. Go straight down to half its height (never below the floor).
4. Close.
5. Lift back up.

Before anything moves, it checks that both points are in reach pointing down, that the point above is within `max_move_cm` (10 cm) of the gripper (if not, use `move_to` near it first), and the usual limits. AI Control (`/ai`) shows each step ("Pick · next · 2/5 go above it…") just before it moves. The pick ends early on STOP (`stopped`), or if a step stops more than 1.5 cm wrong (the gripper stays open). The result is `holding` (the gripper stopped more than 15 % open after the lift) or `missed` (it closed fully: the real arm reads about 8 % with nothing in it), with `steps`.

The x and y come from the stand camera's grid (above). The height reading and the elbow's sag (`docs/plan/ideas.md` → "AI picking") still decide if step 3 goes low enough: fix those first.

## Seeing the pose (`pose_view`)
Without a camera, the AI cannot see the arm. `pose_view` draws the arm's 3D model (`models/so101`) in the pose that its motors report, as a picture:
- **left: the side view, in the arm's own plane.** It turns with `shoulder_pan`, so you never see the arm end-on. Across = the reach from the base's axis. Up = the height from the table. The table is the brown band (an arm on a plate stands on a gray block).
- **right: the top view,** as if you stand behind the arm. Forward (x) is up in the picture, the arm's left (+y) is on the left.
- A **red dot** at the gripper point (with a dotted line down to the table), a **magenta ×** at the last `move_to` target, and **blue marks** that the AI gives in `marks`, for example `[{"x_cm": 15, "y_cm": 5, "z_cm": 1.5, "label": "cube", "size_cm": 3}]` (at most 10). A mark with `size_cm` is a square of that size.

It knows only what the joints say: objects show only as the AI's own marks. Use it after a move and before a grip: "Look with pose_view, with a mark where the cube is, before you close the gripper." To see the same picture yourself, open http://localhost:8080/api/pose-view.png (no marks; reload for a new picture). The first picture after the brain starts takes about one second (the meshes load), then about 0.2 s. Only arms with a 3D model (the SO-101s) have it; for other arms the brain refuses.

## "Arrived" or "stopped short"
After each move, the brain holds the target for half a second (so that a slow joint can arrive). Then it reads where the motors really are and compares that with the target. Within 0.5 cm (2° for each joint), the result is `arrived`. If not, it is `stopped_short`, with how far it is wrong (`off_by_cm`), which joints stopped early (`joints_short_deg`), and a sentence (`message`). A gripper that closes on something says "stopped at 30 % open instead of 0 % (it may be holding something)". AI Control (`/ai`) shows these as "short". The reason: without a camera, `move_to` once said "arrived" 1.6 cm short of the target (GOTCHAS 2026-11-10).

## The log
The brain writes every call (time, tool, arguments, result `ok`, `clipped`, `short`, `refused`, `stopped` or `error`, and the data) to `logs/ai-tools/<date>_<time>.jsonl`. It makes one file for each run of the brain (not in git). Use it to compare runs.

## Other AI tools
Any tool that speaks MCP over "streamable HTTP" can connect to `http://127.0.0.1:8081/mcp` on this computer (Codex, Claude Desktop, and others). Its own permission settings decide if it asks before a move tool. The brain's limits and STOP apply in all cases.

## Later
- Access from other computers with a token (`docs/plan/lab-jarvis-log.md` → "AI-assisted development").

The code: `src/lab_os/tools/robot.py` (the tools and their limits), `tools/table_map.py` (the cm grid), `tools/mcp_server.py` (MCP), `tools/calllog.py`. The tests: `tests/test_robot_tools.py`.
