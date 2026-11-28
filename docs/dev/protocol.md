# Message protocol

JSON messages over a WebSocket. This is the seed of the "one standard message protocol for all clients" in the architecture sketch (docs/plan/log.md). It grows as new clients appear; add message types here when you add them in code.

Every message has a `type`. Unknown or malformed messages are ignored (logged), never fatal.

## Connection
- `ws://<host>:8080/ws`: input clients (the XR page).
- `ws://<host>:8080/ws?role=monitor`: watchers. They receive `status`; the only message they may send is `stop`, so a monitor can never drive the arm.
- **A real arm served to the network** (`lab-os serve --host 0.0.0.0 --arm so101-white`): an input page from another computer is treated as a watcher (it's told once, `error` "view only: …"); only pages on the brain's computer (and the Quest through `adb reverse`, which arrives as that computer) can drive. Its `stop` still works.

**One driver at a time.** Several input pages may be connected (desktop tab, Quest, emulator), but only the page that **has control** moves the arm. A page takes control by sending `xr_input` while control is free. Other pages' `xr_input` is ignored (they get one `error` "another page has control"), and their `session_end` changes nothing. Control is **handed over, not grabbed**: it's freed only when the driving page sends `session_end` or disconnects (both freeze the arm, dead-man). `stop` works from every page.

## Client → server

### `hello`
Sent once on connect.
```json
{"type": "hello", "agent": "<browser user agent>", "device": "desk"}
```
`device`: the page's device name (empty when it has none). The other pages show it as the one with control (quick job 76).

### `xr_input`
Sent every XR frame (72–120 Hz on a Quest).
```json
{
  "type": "xr_input",
  "t": 123456.7,
  "hands": {
    "right": {
      "pos": [0.21, 1.05, -0.33],
      "quat": [0.0, 0.0, 0.13, 0.99],
      "trigger": 0.0,
      "grip": 0.95,
      "buttons": {"a": false, "b": false, "thumbstick": false},
      "thumbstick": [0.0, 0.0]
    },
    "left": { "...": "same shape" }
  }
}
```
- `t`: the page's XR frame time in ms. Only differences between frames mean anything; it's not synced to the server clock.
- `pos`: metres, WebXR `local-floor` space: **+x right, +y up, −z forward** (the way the user faced when the session started), **turned with the 3D arm**: when the user has turned the XR page's arm (left grip), the page rotates `pos` and `quat` about the vertical by the opposite angle, so "forward" is the arm's forward. `quat` = orientation `[x, y, z, w]` of the controller's grip.
- `frame` (optional, since 2026-11-11): `"arm"` when `pos` is measured **from the 3D arm's base** (the Quest page: from where its 3D arm stands, after the left-grip line-up, then turned as above). The 1:1 mode needs it (the gripper goes where the hand is); without it (older recordings, desktop control) only differences between frames count and 1:1 falls back to relative.
- `source` (optional): `"hands"` when the bare hands drive (Hands chosen in the Arm Control options, or "Switch to Hands by Itself" on and the controllers down; quick job 114). The page then sends the right wrist as the right "controller", with `grip` = the **left** hand's pinch (the clutch) and `trigger` = the right hand's pinch (the gripper); no buttons. The server treats it like controllers.
  `"webcam"` from the webcam page (`/webcam`, preview 2, 2026-11-19; `docs/archive/guides-2026-11-25/webcam-teleop.md`): the same as `"hands"` (`grip` = the left pinch or Space held), but only `hands.right`, no `frame` (relative only) and `quat` the hand's turn from the camera (since 2026-11-22, quick job 88; `[0, 0, 0, 1]` when it can't be measured, so the wrist holds). `pos` counts the hand's moves 0.8 times, toward and away 0.4 times (1.5 from quick job 88 to quick job 120). `pivot` is `"wrist"` (below). `trigger` is 1 from a right pinch or a fist, and stays 1 until the hand opens (quick job 120). `pos` is in metres estimated from one camera (toward/away from the hand's size in the picture). It's `null` while the right hand is out of the picture; after that the page sends `grip` 0 until the clutch is let go and pressed again. The server doesn't read `source`.
- `pivot` (optional, since 2026-11-25, quick job 120): `"wrist"` when a turn of the hand turns the gripper about the wrist (the hand moves the wrist point; only `wrist_flex` moves for a tilt). Without it the gripper point stays and the whole arm moves to tilt it (the Quest). Only a relative grab on an arm with kinematics uses it.
- `pos` / `quat` are `null` when tracking is lost (treated like releasing the clutch).
- `trigger`, `grip`: 0..1 (analog).
- `buttons.a` is the lower face button on **either** controller (A on the right, X on the left); `buttons.b` is the upper one (B / Y). With two arms, either one stops both arms.
- Two arms at once (`lab-os serve --left-arm`, preview 3, 2026-11-19): the same message. `hands.right` drives the first arm, `hands.left` the second (its own `grip` and `trigger`). Each hand's `pos` / `quat` is measured from its own 3D arm (the left hand from the left 3D arm). While Y is held (the grips move the 3D arms), and after it until each grip is let go, the page sends both grips as 0, so the arms hold.
- A missing hand key means that controller isn't present.

### `joint_input`
Joint jogging from a keyboard/mouse page: how fast to turn each motor, sent every ~16 ms while active (also when nothing is pressed, as a heartbeat for the dead-man rule). Never goes through IK.
```json
{"type": "joint_input", "t": 123456.7, "source": "desktop-keys", "rates": {"shoulder_pan": 1.0, "gripper": -0.3}}
```
- `rates`: shared joint names → −1..1, a fraction of the jog speed (60 °/s × the venue speed scale). Missing joints hold still; joints the arm doesn't have are ignored (pages can stay generic across arms).
- After any freeze, all rates must return to 0 before anything moves again (like releasing the grip).
- Same control rules as `xr_input`. Switching between `xr_input` and `joint_input` freezes once and starts clean.

### `set_speed`
The Arm Control page's speed slider, or the right thumbstick in XR. From input pages only (watchers can't).
```json
{"type": "set_speed", "speed_scale": 0.3}
```
- Kept between 0.05 and the venue's `max_speed_scale`; `status.speed_scale` says what was set. Doesn't take control.

### `set_mode`
How the hand drives the arm, from the Arm Control page's "Hand → arm" choice. From input pages only (watchers can't).
```json
{"type": "set_mode", "mode": "one_to_one"}
```
- `"relative"` (the default): the gripper moves by how far the hand moved since the grab, at the same scale (`tip_m_per_hand_m`, 1.0 since 2026-11-16; half before); limits and the table slip, so hand and arm can drift apart over a session.
- `"one_to_one"` (1:1, arms with kinematics, venues with `one_to_one_max_deg_per_s` set, `xr_input` with `"frame": "arm"`): the gripper point goes where the hand is, at scale 1, as fast as the venue's 1:1 cap allows (not the Speed slider). The clutch engages only with the hand within `capture_cm` (8) of the gripper point, keeping that small offset (no jump); nothing slips (out of reach, the arm waits as close as it gets). Orientation stays relative.
- A change drops the clutch: release and grip again. `status.mode` says what's set. Doesn't take control.

### `session_end`
The XR session ended (user exited, headset removed, Esc in desktop control). From the driving page: the server freezes the arm and frees control. From any other page: ignored.
```json
{"type": "session_end"}
```

### `stop`
The STOP button, from any page (input or monitor). Freezes the arm (both arms with `--left-arm`) like A/X; the driver must release the clutch and press it again to continue. Control stays where it is.
```json
{"type": "stop"}
```

## Server → client

### `status`
Broadcast to all clients at 10 Hz.
```json
{
  "type": "status",
  "connected": true,
  "frozen": false,
  "clutch": true,
  "needs_release": false,
  "speed_scale": 0.5,
  "max_speed_scale": 0.5,
  "mode": "one_to_one", "modes": ["relative", "one_to_one"], "one_to_one": false,
  "hand_gap_cm": 14.2, "capture_cm": 8.0,
  "arm": {"name": "fake-arm", "model": "so101", "connected": true, "problem": null},
  "joints": {"shoulder_pan": -12.0, "...": 0.0},
  "limits": {"shoulder_pan": [-110.0, 110.0], "...": [0, 0]},
  "last_command": { "...": "the latest arm_command, or null" },
  "left_arm": null
}
```
- `frozen`: dead-man freeze is active (input stale > 250 ms, disconnected, session ended, or A/X pressed).
- `needs_release`: after a freeze, the operator must release the grip and press it again before the arm moves.
- `speed_scale` / `max_speed_scale`: the speed now (`set_speed` changes it) and the venue's cap, the slider's end.
- `mode` / `modes`: `"relative"` or `"one_to_one"` (`set_mode`), and which ones this arm and venue have (no kinematics, or the venue's 1:1 off: relative only). `one_to_one_deg_per_s`: 1:1's top joint speed (the venue's `one_to_one_max_deg_per_s`; null = no software cap). `servos` (real servos only, else null): `{"max_temp_c", "hot" (≥ 60 °C: 1:1 slowed), "joints": {name: {"temp_c", "load_pct", "volts"}}}`, read every 5 s. `one_to_one`: true while a 1:1 grab is following the hand. `hand_gap_cm`: in 1:1 while not holding, how far the hand is from the gripper point (null otherwise); `capture_cm`: how close it must be to grab.
- `arm.model`: which 3D model viewers draw (`so101`, `xarm1s`; see `web/arm/arm-model.js`).
- `arm.connected`: `false` while the arm's USB is unplugged (quick job 27; drivers that can tell: the SO-101s, the fake arm); `arm.problem` says why in a sentence (unplugged, or plugged back in but not reopened, e.g. LeLab has the port). Meanwhile the arm is frozen, input is ignored and `joints` is the last reading. The brain reconnects by itself when the same `/dev/serial/by-id/` name is back; then it's still frozen until the grip is released and pressed again.
- `joints`: what the driver currently reports (degrees). The xArm driver reports where each servo *should* be while it moves (it doesn't read the board during motion) and a real reading once idle.
- `input_kind`: `"pose"` (xr_input), `"joints"` (joint_input) or `null`: which kind of input drives now.
- `clutch`: pose input: grip held; joint input: something is being jogged.
- `control`: per receiving page: `"you"` (this page drives), `"other"` (another page drives), `"free"`. Also per receiving page (quick job 76): `driver`, the device name of the page that drives when `control` is `"other"` (`""` when it has none, or when no other page drives), and `may_drive`, false for a page that may only watch (a real arm served to the network, or a monitor page). A page that may only watch because it is on another computer also gets `address`, its own address as the brain sees it (quick job 95): its line says to add it to `drive_from` in `place.yaml`. A page grays its control buttons when `control` is `"other"` or `"ai"`, or when `may_drive` is false.
- `left_arm`: `null`, or with two arms at once (`--left-arm`, 2026-11-19) the left controller's arm: `{"name", "model", "connected", "problem", "frozen", "clutch", "needs_release", "mode", "one_to_one", "hand_gap_cm", "capture_cm", "joints", "limits"}`, each as above for that arm. `set_mode` sets the mode of both arms. Only pose input drives it. Every other field is the right arm's.

### `arm_command`, `arm_stop`, `arm_resume`
Sent the moment the Arm Control loop calls the arm driver, one message per call, so viewers (3D view, later the Quest ghost arm) show **exactly what the driver received**.
```json
{"type": "arm_command", "seq": 412, "device": "fake-arm",
 "joints": {"shoulder_pan": -12.3, "...": 0.0}, "speed_scale": 0.5,
 "driver_joints": {"shoulder_pan": -12.3, "...": 0.0}}
{"type": "arm_stop", "seq": 413, "device": "fake-arm"}
{"type": "arm_resume", "seq": 414, "device": "fake-arm"}
```
- `joints` / `speed_scale`: the arguments of `Arm.move_joints(...)`, unmodified (degrees, shared joint names).
- `driver_joints`: what the driver reported right after that call. Differences = the driver clamped the command.
- `seq` increases by one per message; a gap means a viewer missed something.
- With two arms at once, both arms send these, each with its own `device`. A page's 3D arm takes only its own arm's messages (`ArmFeed` in `web/arm/arm-feed.js`, one for each arm), so check `device` in any new viewer.

### `error`
```json
{"type": "error", "message": "replay running; live input disabled"}
{"type": "error", "message": "another page has control"}
{"type": "error", "message": "view only: the arm is driven from the brain's computer"}
```

## MCP tools (AI tools → the brain)
Served by `lab-os serve` on `http://127.0.0.1:8081/mcp` (MCP over streamable HTTP, this computer only; `--mcp-port`). Setup, rules and examples: `docs/guides/ai-control.md`. Positions in cm from the arm's base (x forward, y left, z up from the table: the arm's `table_z_cm`, quick job 28), angles in degrees.

| Tool | Arguments | Tier |
|---|---|---|
| `arm_status` | `arm?` | read |
| `list_poses` | `arm?` | read |
| `pose_view` | `marks?` ([{`x_cm`, `y_cm`, `z_cm`, `label?`, `size_cm?`}], ≤ 10), `arm?` | read |
| `camera_snapshot` | `camera` (a name in `devices.yaml`), `width_px?` (640; 160–1280), `grid?` (true), `board?` (false: the tic-tac-toe board drawn on it) | read |
| `move_joints` | `joints` ({name: degrees}), `relative?` (false), `arm?` | move |
| `gripper` | `open_pct` (0 closed … 100 open), `arm?` | move |
| `move_to` | `x_cm`, `y_cm`, `z_cm`, `tool_angle_deg?` (0 up, 90 forward, 180 down; default: keep), `arm?` | move |
| `go_to_pose` | `name`, `arm?` | move |
| `stop` | `arm?` | always allowed |

**Project tools (read, step 6):**
| Tool | Arguments | Returns |
|---|---|---|
| `project_status` | — | the current focus: `focus`, `step`, `of`, `next`, `steps` (`n`, `title`, `done`, `done_on`) |
| `list_docs` | — | `docs`: `name`, `file`, `title` (docs/** incl. `docs/design/`, README, CHANGELOG, SAFETY, CLAUDE) |
| `read_doc` | `name`, `section?` | `text` (≤ 12,000 characters; `truncated` + `sections` when cut off) |
| `search_docs` | `text` | `hits`: `doc`, `line`, `heading`, `text` (≤ 30) |
| `git_status` | — | `branch` (with ahead/behind as of the last fetch), `changed`, `last_commit` |
| `git_log` | `count?` (15, ≤ 50), `path?` | `commits`: `hash`, `date`, `author`, `subject` |
| `list_devices` | — | the place's devices: `name`, `kind`, `off_limits`, `borrowed`, `active_in_venue`, `notes` |

Unknown docs or sections are tool errors starting with `Not found:` that list what exists. The hub's own chat gets exactly the tools annotated read-only (these and `arm_status`, `list_poses`), never a move tool or `stop`, and not `pose_view` or `camera_snapshot` (their answers are pictures). Its own tools for moving the arm are not MCP tools: the wave in visitor mode, and `move_arm_to_pose`, `hand_me_the_cube` and `let_go_of_the_cube` when `place.yaml` has `assistant_moves_arm: true` (`lab_os/hub/arm_desk.py`), each on the brain's own computer only; their moves are robot tool calls.

`pose_view` returns two content blocks: a PNG (`image/png`, 1000×470: side view in the arm's plane on the left, top view on the right, grid in cm) and the text of `{"arm", "joints_deg", "gripper_open_pct", "gripper_point_cm", "tool_angle_deg", "last_target_cm"?, "views"}` (`views`: one sentence saying what's where in the picture). The call log keeps the picture's size only. The same picture without marks: `GET /api/pose-view.png`. `camera_snapshot` returns a JPEG (`image/jpeg`) and `{"camera", "width_px", "table_grid"?, "board"?}`; a camera another program has open is refused. With `board: true` (tic-tac-toe, `docs/archive/guides-2026-11-25/tic-tac-toe.md`), the picture has the board's cells and the robot's start spots on it, and `board` has `cells_cm` (A1–C3), `robot_start_cm`, the colours, the piece height and how to take and put down a piece; refused without `config/games/tic-tac-toe.yaml` or a table map.

Moves return `{"result": "arrived" | "stopped_short" | "stopped" | "disconnected", "clipped": [notes], "joints_deg", "gripper_open_pct", "gripper_point_cm", "tool_angle_deg"}`, read from the motors after the move (`read_measured` where the driver has it). `"stopped_short"`: the arm ended more than 0.5 cm from the target (move_to), a joint more than 2° from its target, or the gripper more than 5 % from the opening asked for; then also `"joints_short_deg"` (target − measured, only the joints that fell short) and `"message"` (one sentence: how far, which joints). `move_to` always adds `"target_cm"`, `"target_tool_angle_deg"` and `"off_by_cm"` (the target of this call, after the per-call clipping). `"disconnected"`: the arm's USB went during the move (then `"problem"` and no position); while it's gone every move is refused and `arm_status` returns `{"connected": false, "problem"}`. Refusals are tool errors whose text starts with `Refused:` and says why. While an AI move runs, `status.control` on the WebSocket is `"ai"`, Arm Control input gets the `error` "the AI tools have control", and `/api/status` lists `"ai"` in `in_use`.

## HTTP endpoints (the hub)
Served by `lab-os serve` (`src/lab_os/hub/server.py`). Plain JSON over `GET` (the chat also uses `POST`), never cached. The hub page reads only these and `/theme.json`, and also `/api/arm` and `/api/devices`.

### `/api/status`
Polled every 3 s by the hub.
```json
{
  "venue": "lab",
  "visitors": null,
  "persona": {"id": "lab-assistant", "display_name": "Lab Assistant",
              "picture": {"type": "orb", "style": "plain", "color": "primary"},
              "voice": "main", "sounds": "default"},
  "internet": true,
  "ai": {"setup": "main", "where": "OpenAI", "model": "gpt-6-luna", "connected": true,
         "paused": null, "problem": null, "busy": false},
  "voice": {"available": true, "why": null, "setup": "backup", "where": "Gemini, free key",
            "service": "gemini", "wake": {"available": true, "why": null, "phrase": "hey Jarvis"}},
  "assistant": {"state": "idle", "loudness": 0.0, "device": ""},
  "arm": {"name": "fake-arm", "connected": true, "control": "free"},
  "left_arm": null,
  "in_use": [],
  "time_ms": 1794264745533
}
```
- `assistant.device` (quick job 58): the screen that has the conversation while the state is `listening`, `thinking` or `speaking` (`""` otherwise, or when that screen has no name). The pages show those three states only when it is their own name; another screen's turn shows as `idle`.
- `visitors`: `null`, or in visitor mode (quick job 35) `{"cards": [{"say": "Ask me to wave", "ask": "Please wave hello to us"}, {"say": "Open the VR hub", "line": "Put on the headset, then say it"}]}`: the venue's "try this" cards (`ask`: what tapping the card asks; without it the card is only read).
- `persona`: the chosen persona (`--persona`, `$LAB_OS_PERSONA`, the venue's, or `place.yaml`; `docs/dev/personas.md`), re-read every time; the designed hub draws `picture`.
- `internet`: `true` / `false`, or `null` until the first background check (every 30 s) has finished.
- `ai`: the chat's AI setup (`docs/dev/chat.md`; `setup` is `null` when none is usable), `connected` (`null` until the first check, then `true`/`false`), `paused` (a full sentence when the chat can't answer: no key, budget used up), `problem` (the last failure, a sentence), `busy` (a turn is running).
- `voice`: whether this brain can hear and speak now (`docs/archive/guides-2026-11-25/voice.md`): `available`, else `why` (a full sentence: the persona has no voice, no key, no internet, the chat is paused), the voice setup in use, and `wake`: `{"available", "why", "phrase"}` for the wake word (the persona's `wake_word:`, the venue's `wake_word:`, the models). The hub shows the mic button only when it's `available` (and the page is secure and has a microphone).
- `assistant.state`: `idle`, `listening`, `thinking`, `speaking`, `offline`, `error`; `loudness` 0–1 while speaking (a spoken answer: the loudness the page reports). `offline` while no AI is connected; `error` after a failed answer until the service answers again.
- `arm.connected`: `false` while the arm's USB is unplugged (as in `status.arm.connected`).
- `arm.control`: `taken` while an Arm Control page (in the hub or on the Quest) drives the arm, `ai` while an AI tool's move runs, else `free`.
- `left_arm`: `null`, or with two arms at once `{"name", "connected"}` of the second arm (Arm Control only).
- `in_use`: what's in use right now (`"teleop"`, `"ai"`, `"chat"` while an answer streams, `"voice"` from a mic press until the answer's last spoken word); the hub never goes back to the start screen while it isn't empty.
- `time_ms`: the brain's clock (ms since 1970), so every screen shows the same time.

### `/api/project`
The Current Project panel, from the Steps list in `docs/plan/current-focus.md`.
```json
{"available": true, "focus": "The hub, voice, and AI driving the SO-101 arms", "step": 2, "of": 12,
 "next": "Robot tools for AI", "steps": [{"n": 0, "title": "Settle before coding", "done": true}, "…"]}
```
`step` is the first step that isn't done (`next` its title, `null` when all are done). `{"available": false}` when the file is missing or has no steps.

### `/api/commits?days=14`
Commits per day for the last `days` days (1–90; today included, oldest first), all local and remote branches, merges left out.
```json
{"available": true, "days": 14, "total": 84, "per_day": [{"date": "2026-10-27", "count": 9}, "…"],
 "recent": [{"hash": "1e73bd0", "date": "2026-11-10", "subject": "Personas: …"}, "…"]}
```
`recent`: the latest 8 commits (same branches, no merges), newest first. `{"available": false, "days": 14, "recent": []}` when git or the repository is missing.

### `/api/arm`
The arm the brain drives, for the designed hub's readouts (polled 4 times a second while the hub is open; real arms rate-limit their reads).
```json
{"name": "fake-arm", "model": "so101", "connected": true,
 "joints": {"shoulder_pan": 0.0, "shoulder_lift": -20.0, "elbow_flex": 40.0, "wrist_flex": 40.0, "wrist_roll": 0.0, "gripper": 30.0},
 "held": true, "control": "free"}
```
`joints`: degrees, shared joint names. `held`: held still (dead-man; true whenever nothing drives it). `control`: `free`, `teleop` or `ai`. Where the arm has kinematics also `gripper_point_cm` (`{x, y, z}` from the base), `gripper_open_pct`, and (SO-101) `side_cm`: every joint seen from the arm's side, `[{"name": "base", "r": 0, "z": 0}, …, {"name": "tip", "r": 25.8, "z": 4.9}]` (`r` = cm forward along the way the arm faces, `z` = cm up from the table: the base's bottom is at `-table_z_cm`, 1.6 for `so101-white` on its plate), for AI Control's drawing. `gripper_point_cm.z` is from the table too. When the arm stops answering: `{"name": …, "model": …, "connected": false, "problem": "<why>"}`.

### `/api/ai-calls?after=T`
The robot tools' calls this brain run (the last 50 after `T`, epoch seconds), for AI Control, polled once a second:
```json
{"calls": [{"time": "2026-11-10T12:44:04.120", "t": 1794336244.12, "tool": "move_to",
            "args": {"x_cm": 60, "y_cm": 0, "z_cm": 5}, "outcome": "clipped", "result": {"result": "arrived", "clipped": ["went 26% of the way: …"], "…": "…"}}],
 "mcp": "http://127.0.0.1:8081/mcp", "motion_allowed": true, "control": "free"}
```
`outcome`: `ok`, `clipped`, `short` (the move ended `stopped_short`), `refused` (then `result` is the sentence why), `stopped`, `error`. `mcp`: null when the AI tools are off (`--mcp-port 0`, or their port was taken).

### `/api/green`, `/api/green/start`
The training launcher (`docs/archive/guides-2026-11-25/green-launcher.md`). `GET /api/green` → `{"ok": false, "lines": [{"ok": true, "text": "nothing else on a serial port (the white arm is unplugged)"}, …], "running": false, "url": "http://127.0.0.1:8000", "here": true}`: the port check (names in `/dev/serial/by-id/` and LeLab's saved settings only; nothing is opened), `running` = LeLab already answers, `here` = this page is on the brain's computer. `POST /api/green/start` checks again and, if every line is fine, opens a terminal on the brain's computer that starts LeLab: the same answer plus `"started": true | false`. Only from the brain's computer (`403` otherwise).

### `/api/shutdown`
Quick job 6 (`docs/archive/guides-2026-11-25/hub.md` → "Shut down lab-os"). `GET` → `{"allowed": true, "why_not": null, "warning": "so101-white goes limp: if it's lifted, it drops. Put it down (home) or hold it first.", "limp": ["so101-white"]}` (`warning` null and `limp` empty when nothing drops; with two arms it names both: "so101-white and so101-green go limp …"). `POST {"from": "desk"}` → `{"ok": true, "message": "lab-os is shutting down."}`: any move stops (an AI move ends with "lab-os is shutting down"), and from then on nothing moves (quick job 44): AI moves and the wave are refused ("lab-os is shutting down: nothing moves any more"), Arm Control input is ignored, the arm's USB is not checked again (a reconnect switches the torque on), and `status` has `"shutting_down": true`. Every page gets `brain_off` (below); half a second later the brain stops as with Ctrl+C: it closes every page's WebSocket (close code 1001, "lab-os is off") and ends each AI tool's MCP session, so it ends in about a second. `403` (and `allowed: false` with `why_not`) from another computer.

**`brain_off`**, on `/ws` (every Arm Control, monitor and AI Control page) and `/ws/hub-device` (every hub page): `{"type": "brain_off", "from": "desk", "time_ms": 1795038737206}` (`from`: the device that asked, `""` without a name). Ctrl+C in the brain's terminal sends it too, with `from` `""`, 0.2 s before the sockets close (quick job 64). Without `restart`, the page leaves full screen (`document.exitFullscreen`, a page may do it without a press) and calls `window.close()` only in a window that a script opened (`window.opener`; elsewhere it did nothing, or left an empty view in VS Code's browser). A page still open shows a small "lab-os is off" card (a Close button only where it can close) (`src/lab_os/web/off.js`; since 2026-11-21), closes its microphone, and reloads once the brain answers again. With `restart`, it stays full screen and says "lab-os is restarting". After the brain stops, `lab-os serve` closes the pages of lab-os's own browser (`launch.close_hub_windows`, through its DevTools port), but not on a restart. In the headset the page's cover isn't seen, so the VR/AR hub (`/xr`, which listens on `/ws?role=monitor`) draws a card in front of you (`hub/web/xr/off.js`), and the Arm Control status panel says "lab-os is off" (`offMessage()` in `off.js`).
### `/api/window-state`
Full screen without a press, for a window of lab-os's own browser (quick job 74). `POST {"url": "http://localhost:8080/monitor/so101?screen=1", "state": "fullscreen"}` (`state`: `fullscreen`, `normal` or `keep`; `url`: the page's address, `location.href`, or the start of it) → `{"ok": true, "why": ""}`. Optional `"bounds": {"left", "top", "width", "height"}` (screen pixels, quick job 138): the window moves there first, as for "Open on…" → "Another monitor of this computer"; `keep` then puts it in full screen again only if it was. The brain finds the page through the browser's DevTools port and sets its window (`Browser.setWindowBounds`). `{"ok": false, "why": "…"}` when the page isn't in lab-os's own browser or the asking page isn't on the brain's computer: the page then asks for a press. `400` without `url`.

### `/api/quest-view`
What the Quest sees (quick job 36, `docs/archive/guides-2026-11-25/quest-view.md`). `GET` → `{"installed": true, "running": false, "headset": "", "via": "", "headsets": [{"name": "quest-a", "connected": true, "via": "usb", "host": "192.168.8.180"}], "why_not": null, "here": true}` (`via`: `usb`, `wifi` or none, how adb reaches the headset, and for `running`, how the window gets its picture; `host`: its Wi-Fi address from devices.yaml, quick job 103; `why_not`: a sentence when it can't start; `here`: the asking page is on the brain's computer, where the window opens). `POST /api/quest-view/start` with `{"headset": "quest-a"}` (optional: default the first one connected) → `{"ok": true, "headset": "quest-a"}` or `400 {"ok": false, "message"}`; `POST /api/quest-view/stop` → `{"ok": true, "stopped": true}`. Both only from the brain's computer (`403` otherwise). One window at a time.

### `/api/settings`
`GET`: `{"sections": [{"id", "title", "help", "fields": [{"key": "theme:clock", "file", "label", "kind", "help", "choices", "min", "max", "step", "unit", "applies", "value", "default", "changed", "safety", "locked"}], "risky": false}], "writable": true, "why_not": null, "venue": "lab", "restart_needed": ["Top Speed"]}` (from `src/lab_os/settings.py`). `POST {"key": "theme:clock", "value": "12h"}` changes one value in its file (comments kept): `{"ok": true, "key", "value", "applies": "reload" | "next" | "restart"}`, or `400 {"ok": false, "message": "<why>"}`. `safety: true` marks a switchable safety limit (its `value` is `true` unless it's off); `locked` says why it can't be switched off in this venue ("" = it can), and switching it off is then a `400`. Only from the brain's computer: `403` otherwise, and `writable: false`. Also `"visitor_mode": {"on": false, "venue": "visit-day", "back_to": "lab", "here": true}` (`null` when the place has no venue for visitors; `here`: the asking page is on the brain's computer, where it can be switched). While visitor mode is on: `"sections": []`, `"writable": false`, `why_not` a sentence, and a `POST` is a `403`. Sections come in their order on the page (quick job 38); `risky: true` is the group shown apart at the bottom; `restart_needed`: labels of settings changed since the brain started that apply on a restart (for "Restart Now"). `default`: the value without this place's changes (the files below `local/`, else the setting's own default); `changed`: the place's `local/` copy has a value for it (quick job 161).

`POST /api/settings/reset {"keys": ["theme:clock", ...]}` (quick job 161, Settings' "Reset to default"): each key's line leaves the place's `local/` copy (comments kept; a section left empty goes too), so the files below decide again. `{"ok": true, "values": {"theme:clock": "24h"}, "message": "1 setting back to the default.", "restart_needed", "restart_keys"}`, or `400 {"ok": false, "message"}` for a key that isn't a setting. Only from the brain's computer (`403` otherwise), not in visitor mode (`403`).

### `/api/restart`
`POST {"from": "desk"}` (quick job 38, Settings' "Restart Now"): as `POST /api/shutdown`, and the `brain_off` message carries `"restart": true`; then `lab-os serve` starts again by itself with the same options (without `--open`). `{"ok": true, "message": "lab-os is restarting."}`. Only from the brain's computer (`403` otherwise).

### `/api/venue`
`POST {"to": "visitors"}` or `{"to": "normal"}` → `{"ok": true, "venue": "visit-day", "visitors": true}`: Settings → Visitor mode, start or exit it without asking the assistant (no welcome). `normal` goes back to the venue the brain started with. Only from the brain's computer (`403` otherwise); `400` for anything else, or when the brain's arm isn't one of that venue's robots.

### `/api/devices`
The place's devices from `devices.yaml` (no ports, nothing opened or probed):
```json
{"arm": "fake-arm",
 "devices": [{"name": "so101-green", "kind": "so101", "off_limits": false, "borrowed": true, "active_in_venue": true, "notes": "…", "linked": false},
             {"name": "fake-arm", "kind": "fake", "off_limits": false, "borrowed": false, "active_in_venue": true, "notes": "…", "linked": true}]}
```
`linked`: the arm this brain drives. `borrowed`: another project's device that lab-os may use with its rules (`docs/dev/places.md`). What is connected now: `/api/live-devices` (below). The system diagram and the VR hub's panels use this list.

### `/api/live-devices` (quick job 109)
The brain's live device list (`src/lab_os/hub/live_devices.py`): every device seen here, connected or not. The brain looks every 2 s (Linux: `/sys`, and `adb devices`; it opens nothing). The Devices panel, the Cameras page and the assistant's `list_devices` use it.
```json
{"devices": [{"id": "so101-white", "name": "so101-white", "kind": "arm", "known": true, "connected": true,
              "what": "Follower.", "via": "USB", "driven": true, "power": "on", "volts": 12.1, "problem": null,
              "first_seen": "2026-11-25 14:02", "last_seen": "2026-11-25 14:02"},
             {"id": "usb:0c45:7403:usb-0:4", "name": "Reader", "kind": "usb", "known": false, "connected": false,
              "what": "Unknown: Card Reader (USB 0c45:7403)", "via": "USB", "last_seen": "2026-11-25 14:10"}]}
```
`kind`: `arm`, `camera` (with `names`: every name for its USB socket; a camera `devices.yaml` doesn't list is `camera-usb-<bus>-<port>`), `headset` (a Quest that adb lists, by cable or Wi-Fi), `robot` (raspbot1 while connected), `screen` (`screen:<name>`: the hub open there), `usb` (any other USB device; hubs are left out). `power` (arms the brain drives only): `on`, `off` (the motors don't answer), or `null` (not known). Connected devices come first. Off-limits devices are never listed. The seen devices are kept in the place's `local/seen-devices.yaml` (not in git).
A connected arm also has `model`: its kind in `devices.yaml` (`so101`, `so101-leader`, `xarm1s`; quick job 134, for the Command Center's Monitor module).
`POST /api/live-devices/remove` `{"id": "…"}` → `{"ok": true, "devices": […]}`; `404` when it is not on the list. A device that is connected stays off the list until it connects again. Every hub page gets the new list.

### `/api/hub`
```json
{"title": "AI Comp Lab",
 "modules": [{"id": "teleop", "title": "Arm Control", "page": "/teleop"},
             {"id": "monitor", "title": "Monitor", "page": "/monitor"}],
 "reset_after_s": 1800,
 "here": true}
```
`here` (quick job 140): the page is on the brain's own computer; the hub then shows the Command Center's way in. `title`: the place's name (`name` in `place.yaml`, `docs/dev/places.md`), shown top left and in the startup. `modules`: the theme's `hub.modules` in order, only those with a page. `reset_after_s`: the venue's value, else the theme's `hub.reset_after_s`.

### Greeting
- `GET /api/greeting` → `{"hello": "Good evening.", "news": "Step 5, Typed chat, was finished today." | null, "source": "step" | "calendar" | "commits" | "persona", "text": "<hello + news, or hello + the persona's line>"}`.
- `GET /api/personas` (quick job 151, the persona chooser) → `{"active": "lab-assistant", "personas": [{"id", "display_name", "picture", "voice", "sounds", "greeting": "Good morning. <the persona's greeting line>"}]}`: every persona (`persona_ids()`); `active` is the one the brain uses now (the venue's may win over the place's).
- `GET /api/personas/{id}/preview` → that persona's `greeting` spoken in its own voice (`audio/wav`), from its recording when it said it before (in the place's `recordings/greetings/`), else spoken now and kept. `404` for no such persona; `503` + `{"ok": false, "message": "<a sentence>"}` when there's no voice for it now (no key, no internet, the budget used up).
- `POST /api/chat/start` → the same plus `"previous"` (as in `GET /api/chat`), and the conversation starts fresh with `text` as the assistant's first message (the hub calls it on the start press). A conversation with a question in it is put aside first.

### Chat
- `GET /api/chat` → `{"messages": [{"role": "user" | "assistant", "content": "…"}], "status": {…same as status.ai…}, "previous": {"questions": 2, "saved_at": <epoch seconds>} | null}`: the conversation the brain holds (one per brain; the hub's reset puts it aside) and the one put aside, if any (kept `chat_keep_minutes`, `docs/dev/chat.md`).
- `POST /api/chat` with `{"text": "…", "pages": {"hub": "the hub", "teleop": "Arm Control", "spend": "AI Spend"}, "lang": {"answer": "en"}}` (text at most 2000 characters; `pages`: what the asking page can show, id → title, optional: without it there's no `open_page` tool; `lang.answer`: the device's output language, `"en"` or `""`/missing = any, since 2026-11-18; `device`: the asking screen's name, for `assistant.device`, since 2026-11-20) → one turn, streamed as **JSON lines** (`application/x-ndjson`), one event per line:
  ```
  {"type": "state", "state": "thinking"}
  {"type": "tool", "name": "project_status"}     (the assistant looks something up; 0–4 per turn)
  {"type": "state", "state": "speaking"}
  {"type": "text", "text": "Next is "}          (pieces of the answer, in order)
  {"type": "text", "text": "step 5."}
  {"type": "state", "state": "idle"}
  {"type": "done", "setup": "main", "cost_usd": 0.000164, "tools": 1}
  ```
  When the assistant opens a page: `{"type": "tool", "name": "open_page"}`, then `{"type": "open", "page": "teleop", "title": "Arm Control"}` (show it on this screen; `hub` = close what's open; for `diagnostics` also `"device": "the Raspbot"`, the words the person used, quick job 135), usually followed by the text "Here's Arm Control." with no second round.
  **Screens by name** (quick job 124): every asker's model also gets the tool `show_on_screens` (`{"page": "<a view of Open on…, or hub>", "screens": ["newline", "brain"]}`; no screens = `brain`, the brain's own computer). It opens the page on each screen like Open on… (`open` with `from: "assistant"`; `hub` sends `close`). The phone's remote (`/remote`) sends `"pages": null`, so it has no `open_page` tool, and a page with no screen named opens on the brain's computer.
  **Visitor mode** (quick job 35): asked on the brain's computer, the model also gets the tools `start_visitor_mode` (visitor mode off) or `exit_visitor_mode` and `wave` (visitor mode on). Like any tool, each shows as `{"type": "tool", "name": …}`; then `{"type": "venue", "venue": "visit-day", "visitors": true}` (the venue changed: read `/api/status` again; on a typed turn that started visitor mode, the page sends voice `say` after `done` to have the welcome spoken) or `{"type": "wave"}` (the wave started). The model then answers as usual.
  or `{"type": "error", "message": "<a full sentence for the screen>"}` (no key, budget used up, the service refused or didn't answer, "I'm still answering the last question."). One turn at a time.
- `POST /api/chat/clear` → `{"ok": true}`: start over; the conversation is put aside (if it has a question).
- `POST /api/chat/restore` → `{"ok": true | false, "messages": […], "previous": … | null}`: bring back the conversation put aside; the current one is put aside in its place (if it has a question), so a second call swaps back. `ok: false` when there's none (or a turn is running).

### `/api/spend`
This month's AI spend (`logs/ai-spend/`), for the AI Spend panel.
```json
{"available": true, "month": "2026-11", "spent_usd": 0.0123, "budget_usd": 20.0, "chats": 7,
 "by_setup": {"main": 0.0123, "backup": 0.0}, "estimated": true, "counted_on": "lab-desktop",
 "less_exact_usd": 0.002}
```
`{"available": false}` on a venue with `public: true`, or in visitor mode (`visitors: true`). `budget_usd` is `null` when the place sets none. Also `"voice_minutes"` (heard + spoken this month); `chats` counts chat turns only. Since 2026-11-19 (quick job 41): `estimated` is always `true` (lab-os calculates the cost; `docs/archive/guides-2026-11-25/hub.md` → "AI Spend"), `counted_on` is the brain's computer name (only this brain's log is counted), and `less_exact_usd` is the part from voice and from counted tokens (entries with `estimated: true`).

### Voice (`/ws/voice`)
A WebSocket per page (`docs/archive/guides-2026-11-25/voice.md`): `ws://<host>:8080/ws/voice?device=<name>` (`device`: the page's device name, for the brain's log and its mute and solo; may be left out). `&own=1`: the Quest's page, which keeps its own sound (quick job 166). Every hub page connects when the brain's status comes, also without a microphone (since quick job 166).

**Where the sound plays** (quick job 166): each device's settings may say `"sound": false` (muted) or `"solo": true` (the Command Center's **M** and **S**). When a soloed device that is not muted has a page connected, every answer, spoken sentence and greeting plays there (one page of each soloed device), whichever page asked. Else an answer plays on the page that asked, and nothing plays when that device is muted (no speech is made then). A greeting plays once for all the pages that ask within 10 s: on the first device of `greeting_from` in `place.yaml` (⚙ → The Lab → Greeting Plays On; `brain` = a page on the brain's own computer) that is connected and not muted, else on the page that asked, else on any page that is not muted. An `own=1` page always plays its own, and counts for none of this. `GET /api/status` → `voice.solo`: the soloed devices connected now (the hub pages then make no sound of their own). The page records and plays; the brain hears, answers through the chat above, and speaks. One utterance at a time per page; the chat's one turn at a time still holds.

**Page → brain**
- `{"type": "listen", "mode": "ask" | "dictate", "pages": {…}, "lang": {"hear": "en", "answer": ""}}`: the mic is pressed (`pages` as in `POST /api/chat`; `lang`: the device's assistant languages, `"en"` or `""` = any: `hear` for speech-to-text, `answer` for the answer; both also sent with `wake`, for questions after the wake word). Then **binary messages**: the microphone as 16-bit PCM, 16 kHz, mono (little-endian), e.g. 50 ms each. `ask` = push-to-talk (the words become a question); `dictate` = words only, nothing is asked. Held longer than 60 s, the brain ends it itself.
- `{"type": "end"}`: let go. `{"type": "cancel"}`: stop, ask nothing.
- `{"type": "played", "loudness": 0.42}` while the answer plays (~5 per second), `{"type": "played", "done": true}` after its last word (or when it was cut short). The assistant's state stays `speaking` until then; `in_use` has `"voice"`.
- `{"type": "wake", "on": true | false, "sensitivity": 5}`: listen for the wake word: the page then streams its microphone (binary, as above) while it isn't playing an answer; the brain runs the detector on it (nothing leaves the brain). `sensitivity`: this device's setting, 1–9 (missing or invalid = 5); sent again with `on: true` when it, `pages` or `lang` changes. Answered with `{"type": "wake_on", "phrase": "hey Jarvis"}` or `{"type": "wake_off", "why": "…"}`.
- `{"type": "playing", "seq": 0}`: the page started playing that spoken piece (the brain's timing: the first word heard).
- `{"type": "wake_mic", "ok": false, "why": "the page's sound is suspended"}`: while the wake word is on, the microphone stopped giving audio and the page couldn't wake it (`ok: true` once it's back). Only logged.
- `{"type": "say"}`: speak the answer of the typed turn that started visitor mode (the welcome), once; only from the brain's computer. Answered with the audio and `audio_end` (`count: 0` when there's nothing to say or no voice).
- `{"type": "greet", "way": "push_to_talk" | "dictation" | "wake_word" | "none"}`: say the greeting: the time of day of the conversation's first message (set by `POST /api/chat/start`), never its news, and a hint how to talk (`none`: no hint, the screen has no microphone). One piece, from the place's `recordings/greetings/` when this voice said it before (no voice request), else spoken and saved. At most every 10 s for all the pages together (quick job 166; for each page before), on the device that "Where the sound plays" names; a refused greet, or one that plays on another page, gets `audio_end` with `count: 0`.

**Brain → page**
- `{"type": "listening", "mode": "ask"}`; `{"type": "heard", "text": "what is the next", "final": false}` while hearing (the words so far), then `{"type": "heard", "text": "…", "final": true}` after `end` (`""`: nothing was said; nothing is asked). `"command": true` with it: the words were "that's all" or "start a conversation", not a question, so no answer comes (the page ends the turn; quick job 83).
- Then, for `ask`, the chat's events as in `POST /api/chat` (`state`, `tool`, `text`, `open`, `done` or `error`).
- `{"type": "audio", "seq": 0, "text": "Next is step 7.", "mime": "audio/wav", "data": "<base64>"}`: the spoken answer, a sentence or a few at a time, in order; then `{"type": "audio_end", "count": 2}` (`"greeting": true` for the greeting; `count: 0` when nothing was spoken, or when it played on another page).
- `{"type": "audio_begin"}` (quick job 166): another page's answer or greeting plays here (this device is soloed, or speaks the greeting). Its `audio` pieces and `audio_end` follow; the page answers with `played` as for its own.
- `{"type": "converse", "on": true}` from the page (with `pages` and `lang`, as `listen`): conversation mode on (quick job 68); `on: false` ends it. The brain answers `{"type": "converse", "on": true}` or `{"type": "converse", "on": false, "why": "you said \"that's all\""}`. While it is on, the brain sends `{"type": "wake", "conversation": true}` and listens (as after the wake word) at the start and after each answer has played (`played` with `done`) or a question with no words. A spoken "start a conversation" turns it on; "that's all" turns it off (only in a short sentence).
- `{"type": "stopped"}` (quick job 57): a new question (the wake word or a mic press, on any screen) stopped this page's spoken answer. Nothing more comes for it: no more `text`, `audio` or `audio_end`. The page stops its audio and ends that turn. On the screen that asks, it comes before `wake` or `listening`.
- `{"type": "wake", "score": 0.98}`: this page heard the wake word best (others got `{"type": "wake_elsewhere"}`); the brain is already hearing (then `listening`, `heard` as above). The page ends the question with `end` (after a silence) or drops it with `cancel`. The wake phrase is taken off the start of the words.
- `{"type": "ended"}`: after `wake` only: the voice service heard the pause after the question, or the turn model (quick job 110, `lab_os.ai.turn`) heard a finished question, so the brain ended it itself (the page stops waiting for silence; don't send `end`).
- `GET /api/voice/timings` → `{"timings": [{"how": "wake word" | "push-to-talk" | "dictation", "device": "desk", "warm": true, "ended_by": "pause" | "turn model" | "page", "at": <epoch s>, "ms": {"detected": 0, "picked": 1, "listening": 2, "connected": 2, "ended": 2310, "words": 2710, "first_text": 5810, "first_audio": 8010, "playing": 8070}, "waited_ms": 5760}]}`: the last 20 voice turns, each step in milliseconds from the first (steps that didn't happen are left out). The same as the brain's "voice timing" log lines.
- `{"type": "voice_error", "message": "…"}`: speaking failed; the answer stays on the screen. `{"type": "error", "message": "…"}`: no voice now, the service refused, or "I'm still on the last one."

### Devices (`/ws/hub-device`)
Focus step 8 (`docs/archive/guides-2026-11-25/hub.md` → "Devices"). Every hub page keeps one WebSocket open: `ws://<host>:8080/ws/hub-device?device=<name>&window=<id>`. `device`: the name in the page's address (lowercase letters, digits, dashes, up to 32; empty or invalid = no name: since quick job 101 the page is listed by its address, as `addr-192-168-8-167` with `"title": "192.168.8.167 (no device name)"` and `"named": false`, and it can be opened on like a named device; it keeps no settings). `window`: the id the brain gave this page last time (kept in the tab's `sessionStorage`), so after a brain restart it's the same window again; a new or already-connected id gets a fresh one. The page reconnects by itself (1 s, then up to 5 s apart). The code: `src/lab_os/hub/hub_devices.py`, `src/lab_os/web/device.js`.

**Brain → page**
- `{"type": "welcome", "device": "desk", "found": false, "display_name": "Windows desktop 3", "window": "w-AbC123", "settings": {"res": "0.5"}, "devices": [...], "why_no_name": ""}`: on connect. `settings`: this device's own (below); `devices`: the list as in `GET /api/hub-devices`. `display_name`: the device's display name, else its name (quick job 132). `key` (quick job 169): its device name, else its address key (`addr-127-0-0-1`); a page with no name gets only its `sound` and `solo` in `settings`, kept under `key` (`POST /api/hub-devices/<key>/settings` takes only those two). `found: true`: the page came without `?device=`, and the brain gave it the name that its address last used (not on the brain's own computer); the page then opens again under that name.
- `{"type": "renamed", "device": "desk-3"}` (quick job 132): this device has a new device name (`POST /api/hub-devices/<name>/rename`); the page opens again under it.
- `{"type": "devices", "devices": [...]}`: the list changed (a page came or went, or shows something else).
- `{"type": "open", "module": "monitor", "from": "newline", "from_window": "w-…"}`: show this module now (sent from another device: "Open on…"). From the start screen too, without a startup or a new conversation; an open module gives way.
- `{"type": "close"}`: close the module at the brain’s request.
- `{"type": "card"}`: the brain read a card swipe (a plain number) on its own computer's card reader (quick job 113). Only the pages on the brain's computer get it (a loopback address, or the address the page reached the brain at). A page on its start screen starts as with a swipe there. The card's data is never sent. The other pages on their start screen get `start` (`"how": "card"`, `"from": "the card reader"`; quick job 139).
- `{"type": "start", "how": "tap" | "card", "from": "desk"}` (quick job 139): a person started the start screen on another device (`from`: its display name, else its device name or address), or the Command Center did (`"the Command Center"`). Only the windows on their start screen get it, never the window that started. The page plays the same unlock (`card`: the card's) and startup, with "Started from desk" under the core. It starts no new conversation and speaks no greeting: it shows the conversation the other screen started. Without a press on the page, the browser allows full screen only at the next tap or key, and sound only with `--autoplay-policy=no-user-gesture-required` (lab-os's own browser and the "Lab Hub" icon have it).
- `{"type": "idle", "from": "the Command Center"}` (quick job 168): go back to the start screen, as ⏻ → Back to the start screen does (`POST /api/hub-devices/idle` with `windows`). Only the windows that have started get it.
- `{"type": "settings", "settings": {...}}`: this device's settings changed (every window of it gets them).
- `{"type": "live-devices", "devices": [...]}` (quick job 109): the live device list changed (a plug, an unplug, a connect or a disconnect, a Remove); the list as in `GET /api/live-devices`.

**Page → brain**
- `{"type": "hello", "stage": "start" | "hub", "showing": "monitor" | null, "from": "newline", "from_window": "w-…", "screen": {"label": "DELL U2720Q", "left": 1920, "top": 0, "width": 1920, "height": 1080, "ratio": 1.25}}`: after the welcome. `showing`: the module page open there (null: none, or a chat or details page); `from`: who sent it (`""`: opened there). `screen`: which monitor (position in the desktop; `label` only where the browser already allowed "window management"; `ratio`: the browser's pixel ratio, so `width × ratio` is the monitor's resolution, quick job 134).
- `{"type": "state", ...}`: the same fields when they change (a module opened or closed, the start screen, the reset).
- `{"type": "start", "how": "tap" | "card"}` (quick job 139): a person started this window's start screen (a tap, a click, a key or a card swipe). The brain sends `start` to every other window on its start screen and marks them `"stage": "hub"`. A page started by `start` or `card` does not send it.

**HTTP**
- `GET /api/hub-devices` →
  ```json
  {"devices": [{"name": "desk", "address": "192.168.1.20",
                "windows": [{"id": "w-AbC123", "label": "left monitor", "stage": "hub",
                             "showing": {"id": "monitor", "title": "Monitor"}, "from": "newline", "from_window": "w-…"}]}],
   "sent": [{"device": "desk", "window": "w-AbC123", "label": "left monitor", "showing": {"id": "monitor", "title": "Monitor"},
             "from": "newline", "from_window": "w-…"}]}
  ```
  Each device also has `title` (its display name, else its name; a page with no name: its address), `display_name` (`""` = none), `named` and `here` (true: the brain's own computer; quick job 134), `sound` (its setting: `false` = muted, else `true` or `null`), `solo` and `own_sound` (true: the Quest's page, which keeps its own sound; quick job 166). Each window also has `screen` (as in `hello`). Windows left to right. `label`: `""` when the device has one window, else the monitor's name, `left monitor` / `right monitor`, `monitor 3`, or `window 2`. `sent`: pages opened from another device.
- `POST /api/hub-devices/open` `{"module": "monitor", "device": "desk", "window": "" , "from": "newline", "from_window": "w-…"}` → `{"ok": true, "device": "desk", "window": "w-…", "label": "", "message": "Monitor is open on desk."}` (the message uses the display name); or, when the device has two monitors free (or none), `{"ok": false, "ask": [<windows as above>], "message": "desk has 2 monitors free: which one?", "device": "desk"}`: send again with `window`. `module` may be any view id of `/api/hub` → `views` (since 2026-11-21: the module pages, `webcam`, `cameras` (since 2026-11-23), `settings`, the details pages `project`, `spend`, `commits`, `devices`, `system`, `chat`, `xr`), and a page's `showing` state may be any of them. `device` may also be a display name, in any case (quick job 132). `400 {"ok": false, "message"}`: not such a view, not a name, no hub open there. Never the window that sent it.
- `POST /api/hub-devices/close` `{"device": "desk", "window": "w-…"}` → `{"ok": true, "device", "module"}` (the page there gets `close`).
- `POST /api/hub-devices/start` `{"windows": ["w-…"]}` (quick job 139; no `windows`: every window) → `{"ok": true, "started": 2, "message": "Started 2 screens."}`: each of those windows on its start screen gets `start` (`"from": "the Command Center"`); a started window does not change (`"started": 0`, `"message": "No screen shows the start screen."`). Any page may: it only starts the hub there.
- `POST /api/hub-devices/idle` `{"windows": ["w-…"]}` (quick job 168) → `{"ok": true, "idle": 2, "message": "2 screens on the start screen."}`: each of those windows that has started gets `idle` and goes back to its start screen; one on its start screen does not change. Any page may: it only changes what the screens show.
- `POST /api/room/setup` (quick job 71) → `{"ok", "opened": [{"device", "page", "title"}], "skipped": [{"device", "page", "why"}], "message"}`: each `device: page` of the place's `room.yaml`, in order. `core` closes what the device shows (the page gets `close`); any other view opens on the device's leftmost window (`open`, `from: "room"`). A device without the hub open, or an unknown page, is skipped with the reason. The assistant's `set_up_room` tool and `lab-os room` call the same.
- `GET /api/hub-devices/<name>/settings` → `{"ok": true, "settings": {...}}`. `POST` `{"res": "0.5", "sound": false}` changes some (`""` or `null` = back to the default) → `{"ok": true, "settings": {...all of them}}`, and every window of that device gets `settings`. Keys: `quality` (`maximal` / `full` / `reduced` / `minimal`), `res` (`auto` / `1` / `0.75` / `0.5`), `sound` (false = muted: nothing plays there), `solo` (true / false, quick job 166: see "Voice" → "Where the sound plays"), `full` (true / false), `voice` (`push-to-talk` / `dictation` / `wake word`), `wake_sensitivity` (a number 1–9), `cameras_hidden` (since 2026-11-23: a list of up to 32 camera names that the Cameras page hides on this device; `[]` = back to the default, every camera shown), `display_name` (quick job 132: up to 40 characters, one line; two devices can't have the same one; every page gets `devices` again); anything else is `400`. `<name>` may be a display name. Kept in the place's `local/hub-devices.yaml`, with the name each address last used (`addresses`). Any page may (as before, when they were per browser).
- `POST /api/hub-devices/<name>/rename` `{"to": "desk-3"}` (quick job 132, ⚙ → This Device → Device Name) → `{"ok": true, "settings": {...}}`: the settings and the remembered addresses move to the new name (where the new name has settings already, its own values stay), and every window of the device gets `renamed`. `400`: not a name.

### Diagnostics (quick job 135)
`GET /api/diagnostics` → `{"devices": [{"id": "so101-white", "name": "so101-white", "kind": "arm", "connected": true, "what": "", "panel": {...}}]}`: every device (the brain's arms, the Raspbot, then the live list, the ones off now too with `last_seen`), connected first. `panel` fits the kind: an arm `{"model", "fake", "connected", "problem", "frozen", "health": "ok" | "no_answer" | "waiting" | "none", "read_s_ago", "motors": [{"joint", "position_deg", "temp_c", "load_pct", "volts", "errors": ["temperature", "overload"], "state": "ok" | "warn" | "bad"}]}` (`errors`: the Feetech status register's bits); the Raspbot `{"fake", "connected", "address", "round_trip_ms", "message", "pi": {...}, "distance_mm", "moving", "control", "camera", "speed"}`; a camera `{"open": true, "fps", "sent_fps", "width", "height", "error"}` (only while open); a screen `{"address", "here", "windows": [{"label", "width", "height", "stage", "showing"}]}`. Only reads. The page `/diagnostics?show=<words>` shows one device.

### The Command Center (quick job 134)
The page `/command-center` (`src/lab_os/hub/command_center.py`, `src/lab_os/hub/web/command-center.js`). It reads `GET /api/hub-devices` and `GET /api/live-devices` every 1.5 s, and its Pages list from `GET /api/hub` → `views` (quick job 148), and changes the real devices with `POST /api/hub-devices/open` (`"from": "the Command Center"`), `/close`, `/start` (quick job 139) and `/<name>/settings`. Its own endpoints answer only to the brain's own computer (else `403 {"ok": false, "message"}`), and so does the page:
- `GET /api/command-center` → `{"layout": {"places": {"d:desk": [x, y]}, "hidden": ["l:raspbot1"], "groups": {"s:desk#2": "d:pi03"}}, "drive_from": ["192.168.8.180"]}`. Item keys: `d:<device name>` (a device with the hub open), `l:<live device id>` (a device of the live list), `s:<device name>#<n>` (a screen: the device's window n, left to right). `groups`: a screen grouped under another device (or under itself: on its own). `drive_from`: the addresses that may drive a real arm now.
- `POST /api/command-center/layout` `{"places", "hidden", "groups"}` → `{"ok": true, "layout"}`: the workspace's layout, kept in the place's `local/command-center.yaml`. It changes no device.
- The opening (quick job 140) plays its sounds through the hub when it is in the hub's module frame: the page sends `postMessage({"type": "lab-os-sfx", "name": "lock", "arg": 1})` to the hub, which plays its own sound of that name (`tick`, `sweep`, `lock`, `shock`, `decode`, `title`, `land`) only for its module frame. On its own screen the page plays them itself.
- `GET /api/command-center/activity` → `{"events": [{"t": 1764140000.0, "text": "pi7 opened Arm Control (from desk)", "kind": "page"}]}`: the activity list (quick job 149), newest first, at most 50. `kind`: `device` (connected or disconnected), `page` (a screen opened the hub or a page, went back to the hub, or closed the hub), `stop`. Kept in the brain's memory only (the last 100).
- `POST /api/command-center/drive` `{"addresses": ["192.168.8.50"], "allowed": true}` → `{"ok": true, "drive_from": [...]}`: those devices may (or may not) drive a real arm, at once and after a restart (`drive_from` in the place's `local/place.yaml`; a name there that stands for the address goes too). An Arm Control or Raspbot Control page checks it when it connects.

## The Raspbot Control page (quick job 72)
`WS /ws/raspbot` serves **Raspbot** at `/raspbot`. **Raspbot Monitor** at `/monitor/raspbot` uses `WS /ws/raspbot?role=monitor`. It receives the same status with `may_drive: false`. Only STOP can affect the Raspbot on this connection. `GET /api/raspbot/camera.mjpg` sends the camera's newest picture as MJPEG (`multipart/x-mixed-replace; boundary=frame`). The brain keeps one connection to the camera for every page, recording and the labels; a slow page skips pictures. Page → brain:
- `{"type": "drive", "dir": "<direction>"}`: sent every 100 ms while a button is held. The first page that drives has control. `forward`, `back`, `strafe-left`, `strafe-right`, `forward-left`, `forward-right`, `back-left` and `back-right` move the car. `left` and `right` turn it in place.
- `{"type": "set_speed", "speed": 0.3}`: the Speed slider, 0 (none) … 1 (the program's cap); one speed for every page. Only a page that may drive.
- `{"type": "release"}`: every button let go; the car stops and control is free.
- `{"type": "stop", "device": "<name>"}`: STOP, from any page (also a view-only page). The page that drove must send `release` before it drives again.
- `{"type": "drive", "dir": "stick", "stick": [forward, sideways, turn]}`: held stick input (each axis −1 … 1). Positive values drive forward, move right or turn right. `[forward, turn]` also works and sets sideways to zero.
- `{"type": "look", "pan": 20.0, "tilt": -5.0}`: turn the camera, degrees from its centre (pan + = left, tilt + = up), at most 90. With optional `"relative": true`, add these degrees to the last camera target and keep the servo limits. It never takes control. The brain refuses it while another page has control, or after STOP until `release`.
- `{"type": "picture"}`, `{"type": "record", "on": true | false}`: save a picture or start / end a recording on the brain's computer (`recordings/raspbot/`). Answer: `{"type": "saved", "what": "picture" | "recording", "on": …, "path": "<the file>"}`, or an `error` without a camera. A recording also ends when the page that started it closes. The end's `path` is an `.mp4` (an `.mjpeg` without ffmpeg); a recording without pictures is deleted and the answer is an `error` (quick job 122).
- `{"type": "labels", "on": true | false}`: labels on what the camera sees (quick job 128; the Raspbot Control page and the VR Raspbot; also from a page that only watches). The brain's detector (`lab_os.object_labels`, the words in `config/labels.yaml`) runs while a page has them on. Answer, for each detected picture (about 6 a second): `{"type": "labels", "state": "loading" | "ready" | "failed", "found": [{"name": "cup", "score": 0.82, "box": {"x": 0.4, "y": 0.3, "w": 0.1, "h": 0.2}}], "why": "<the reason: no model, no camera>"}`. The box is in fractions of the picture, from its top left. The page puts the ultrasonic distance on the object in front itself (`/web/object-labels.js`).

Brain → page, every 0.2 s: `{"type": "raspbot_status", "name": "raspbot1", "fake": false, "connected": true, "moving": "" | "<dir>", "control": "free" | "you" | "other", "camera": true, "speed": 0.5, "pan_deg": 20.0, "tilt_deg": -5.0, "wheel_speeds": [0.5, -0.5, -0.5, 0.5], "distance_mm": 325 | null, "obstacle_stop_mm": 200 | null, "may_drive": true, "message": "<why not connected>", "address": "<a view-only page's address>", "recording": "<file name>" | "", "recording_seconds": 0 | null, "folder": "<where pictures go>"}`. `recording_seconds` is the number of whole seconds since the recording started, or `null` when idle. A refused `drive` gets `{"type": "error", "message": "Another page has control."}`. The brain stops the car when a driver's input stops for 0.3 s.

`pan_deg` and `tilt_deg` give the last camera target in degrees from the centre, after the servo limits. Positive pan turns left. Positive tilt points up. Both start at zero and keep their values when the wheels stop.

`wheel_speeds` gives the last drive command as four signed fractions of the motor speed cap after the Speed slider. The order is front left, rear left, front right, rear right. All four values are zero when the brain stops the drive, when the Raspbot reports a drive stop, or while the Raspbot is disconnected. The values come from commands.

On TCP port 8765, the program on the Raspbot can advertise `"diagnostics": true` and `"look_limits": [[-90, 90], [-25, 85]]` in its hello. The limits are degrees from the centre for pan and tilt. The current hello includes `"obstacle_stop_mm": 200` and `"mecanum": true`. The brain sends `{"diagnostics": true}` every 0.1 s to the current program, and once per second to older programs. The reply gives `distance_mm` (a number or null) and can give `drive_stop` (an empty string, `obstacle`, `sensor_unavailable` or `input_timeout`). Since quick job 135 it can also give `"pi": {"power": "ok", "input_v": 5.1, "temp_c": 48.3, "wifi_quality": 58, "wifi_dbm": -52}`: the Pi's health, read every 5 s (`power`: `ok`, `low` = under-voltage now, `was_low` = since the start, `?`). The brain times each question and its answer (the Diagnostics page's round trip). Only drive commands refresh the motor watchdog.

### The Wake Word page (quick job 99, `hub/wake_clips.py`)
Only from the brain's computer (else `403`). `{word}` is a key of `PHRASES` in `ai/wake.py` (else `404`).
- `GET /api/wake-word` → `{"active": "hey_jarvis", "here": true, "need_word": 8, "need_other_s": 20, "words": [{"id", "phrase", "word_clips", "other_s", "trained": null | {training result}}]}`.
- `POST /api/wake-word/{word}/clip?kind=word|other`, the body raw 16-bit 16 kHz mono PCM (0.5 to 4 s for `word`, to 15 s for `other`) → the word's summary plus `"score"` (the word model's best score in the clip).
- `POST /api/wake-word/{word}/train?sensitivity=9` → `{"ok", "tries", "word_before", "word_now", "other_s", "other_before", "other_now", "checked_other", "sensitivity", "at", "summary"}` (the counts are held-out checks), or `400` with `"message"` when there are too few clips.
- `POST /api/wake-word/{word}/clear` → the clips and the verifier are deleted; the summary.

`GET /api/raspbot/camera.mjpg`: the Raspbot's camera (`multipart/x-mixed-replace` JPEGs), relayed from the Raspbot's port 8766; `404` without a camera.

Brain → the program on the Raspbot (`robots/raspbot/lab_os_raspbot.py`, TCP port 8765), one JSON line each: `{"drive": [front_left, rear_left, front_right, rear_right]}` (motor IDs 0–3, each −1.0 … 1.0 of the speed cap), `{"stop": true}`, or `{"look": [pan, tilt]}` (the camera's servos, degrees from their centre; the program keeps each servo's limits and leaves the wheels as they are). `{"drive": [left, right]}` still works and applies each value to both wheels on that side. The brain uses this form if the hello omits `"mecanum": true`. It refuses sideways and diagonal commands until the current program is deployed. The program answers once at connect: `{"hello": "<hostname>", "camera_port": 8766 | 0}`. It stops the motors after 0.5 s without a command, when the connection drops, and for a line it does not understand. A new connection replaces the old one. The current program stops any movement with a forward component at the ultrasonic threshold, including forward diagonals. An AI drive adds `"require_clear": true`. It also stops forward motion if the sensor gives no reading. After the car stops an AI drive for either reason or a timeout, a stop command clears that drive before the next one starts.

## Recording files (`.jsonl`)
One line per received message: `{"dt": <seconds since recording start>, "msg": <message>}`. Written by `lab-os-teleop serve --record`, read by `lab-os-teleop replay`.
