# Message protocol

JSON messages over a WebSocket. This is the seed of the "one standard message protocol for all clients" in the architecture sketch (lab-jarvis-log.md). It grows as new clients appear; add message types here when you add them in code.

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
{"type": "hello", "agent": "<browser user agent>"}
```

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
- `source` (optional): `"hands"` when the Quest tracks bare hands instead of controllers. The page then sends the right wrist as the right "controller", with `grip` = the **left** hand's pinch (the clutch) and `trigger` = the right hand's pinch (the gripper); no buttons. The server treats it like controllers.
- `pos` / `quat` are `null` when tracking is lost (treated like releasing the clutch).
- `trigger`, `grip`: 0..1 (analog).
- `buttons.a` is the lower face button on **either** controller (A on the right, X on the left); `buttons.b` is the upper one (B / Y).
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
The teleop page's speed slider, or the right thumbstick in XR. From input pages only (watchers can't).
```json
{"type": "set_speed", "speed_scale": 0.3}
```
- Kept between 0.05 and the venue's `max_speed_scale`; `status.speed_scale` says what was set. Doesn't take control.

### `set_mode`
How the hand drives the arm, from the teleop page's "Hand → arm" choice. From input pages only (watchers can't).
```json
{"type": "set_mode", "mode": "one_to_one"}
```
- `"relative"` (the default): the gripper moves by how far the hand moved since the grab, at half scale (`tip_m_per_hand_m`); limits and the table slip, so hand and arm drift apart over a session.
- `"one_to_one"` (1:1, arms with kinematics, venues with `one_to_one_max_deg_per_s` set, `xr_input` with `"frame": "arm"`): the gripper point goes where the hand is, at scale 1, as fast as the venue's 1:1 cap allows (not the Speed slider). The clutch engages only with the hand within `capture_cm` (8) of the gripper point, keeping that small offset (no jump); nothing slips (out of reach, the arm waits as close as it gets). Orientation stays relative.
- A change drops the clutch: release and grip again. `status.mode` says what's set. Doesn't take control.

### `session_end`
The XR session ended (user exited, headset removed, Esc in desktop control). From the driving page: the server freezes the arm and frees control. From any other page: ignored.
```json
{"type": "session_end"}
```

### `stop`
The STOP button, from any page (input or monitor). Freezes the arm like A/X; the driver must release the clutch and press it again to continue. Control stays where it is.
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
  "arm": {"name": "fake-arm", "model": "so101"},
  "joints": {"shoulder_pan": -12.0, "...": 0.0},
  "limits": {"shoulder_pan": [-110.0, 110.0], "...": [0, 0]},
  "last_command": { "...": "the latest arm_command, or null" }
}
```
- `frozen`: dead-man freeze is active (input stale > 250 ms, disconnected, session ended, or A/X pressed).
- `needs_release`: after a freeze, the operator must release the grip and press it again before the arm moves.
- `speed_scale` / `max_speed_scale`: the speed now (`set_speed` changes it) and the venue's cap, the slider's end.
- `mode` / `modes`: `"relative"` or `"one_to_one"` (`set_mode`), and which ones this arm and venue have (no kinematics, or the venue's 1:1 off: relative only). `one_to_one_deg_per_s`: 1:1's top joint speed (the venue's `one_to_one_max_deg_per_s`; null = no software cap). `servos` (real servos only, else null): `{"max_temp_c", "hot" (≥ 60 °C: 1:1 slowed), "joints": {name: {"temp_c", "load_pct", "volts"}}}`, read every 5 s. `one_to_one`: true while a 1:1 grab is following the hand. `hand_gap_cm`: in 1:1 while not holding, how far the hand is from the gripper point (null otherwise); `capture_cm`: how close it must be to grab.
- `arm.model`: which 3D model viewers draw (`so101`, `xarm1s`; see `web/arm/arm-model.js`).
- `joints`: what the driver currently reports (degrees). The xArm driver reports where each servo *should* be while it moves (it doesn't read the board during motion) and a real reading once idle.
- `input_kind`: `"pose"` (xr_input), `"joints"` (joint_input) or `null`: which kind of input drives now.
- `clutch`: pose input: grip held; joint input: something is being jogged.
- `control`: per receiving page: `"you"` (this page drives), `"other"` (another page drives), `"free"`.

### `arm_command`, `arm_stop`, `arm_resume`
Sent the moment the teleop loop calls the arm driver, one message per call, so viewers (3D view, later the Quest ghost arm) show **exactly what the driver received**.
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

### `error`
```json
{"type": "error", "message": "replay running; live input disabled"}
{"type": "error", "message": "another page has control"}
{"type": "error", "message": "view only: the arm is driven from the brain's computer"}
```

## MCP tools (AI tools → the brain)
Served by `lab-os serve` on `http://127.0.0.1:8081/mcp` (MCP over streamable HTTP, this computer only; `--mcp-port`). Setup, rules and examples: `docs/ai-control.md`. Positions in cm from the arm's base (x forward, y left, z up), angles in degrees.

| Tool | Arguments | Tier |
|---|---|---|
| `arm_status` | `arm?` | read |
| `list_poses` | `arm?` | read |
| `pose_view` | `marks?` ([{`x_cm`, `y_cm`, `z_cm`, `label?`, `size_cm?`}], ≤ 10), `arm?` | read |
| `move_joints` | `joints` ({name: degrees}), `relative?` (false), `arm?` | move |
| `gripper` | `open_pct` (0 closed … 100 open), `arm?` | move |
| `move_to` | `x_cm`, `y_cm`, `z_cm`, `tool_angle_deg?` (0 up, 90 forward, 180 down; default: keep), `arm?` | move |
| `go_to_pose` | `name`, `arm?` | move |
| `stop` | `arm?` | always allowed |

**Project tools (read, step 6):**
| Tool | Arguments | Returns |
|---|---|---|
| `project_status` | — | the current focus: `focus`, `step`, `of`, `next`, `steps` (`n`, `title`, `done`, `done_on`) |
| `list_docs` | — | `docs`: `name`, `file`, `title` (docs/**, README, CHANGELOG, SAFETY, CLAUDE; never `docs/design/`) |
| `read_doc` | `name`, `section?` | `text` (≤ 12,000 characters; `truncated` + `sections` when cut off) |
| `search_docs` | `text` | `hits`: `doc`, `line`, `heading`, `text` (≤ 30) |
| `git_status` | — | `branch` (with ahead/behind as of the last fetch), `changed`, `last_commit` |
| `git_log` | `count?` (15, ≤ 50), `path?` | `commits`: `hash`, `date`, `author`, `subject` |
| `list_devices` | — | the place's devices: `name`, `kind`, `off_limits`, `active_in_venue`, `notes` |

Unknown docs or sections are tool errors starting with `Not found:` that list what exists. The hub's own chat gets exactly the tools annotated read-only (these and `arm_status`, `list_poses`), never a move tool or `stop`, and not `pose_view` (its answer is a picture).

`pose_view` returns two content blocks: a PNG (`image/png`, 1000×470: side view in the arm's plane on the left, top view on the right, grid in cm) and the text of `{"arm", "joints_deg", "gripper_open_pct", "gripper_point_cm", "tool_angle_deg", "last_target_cm"?, "views"}` (`views`: one sentence saying what's where in the picture). The call log keeps the picture's size only. The same picture without marks: `GET /api/pose-view.png`.

Moves return `{"result": "arrived" | "stopped_short" | "stopped", "clipped": [notes], "joints_deg", "gripper_open_pct", "gripper_point_cm", "tool_angle_deg"}`, read from the motors after the move (`read_measured` where the driver has it). `"stopped_short"`: the arm ended more than 0.5 cm from the target (move_to), a joint more than 2° from its target, or the gripper more than 5 % from the opening asked for; then also `"joints_short_deg"` (target − measured, only the joints that fell short) and `"message"` (one sentence: how far, which joints). `move_to` always adds `"target_cm"`, `"target_tool_angle_deg"` and `"off_by_cm"` (the target of this call, after the per-call clipping). Refusals are tool errors whose text starts with `Refused:` and says why. While an AI move runs, `status.control` on the WebSocket is `"ai"`, teleop input gets the `error` "the AI tools have control", and `/api/status` lists `"ai"` in `in_use`.

## HTTP endpoints (the hub)
Served by `lab-os serve` (`src/lab_os/hub/server.py`). Plain JSON over `GET` (the chat also uses `POST`), never cached. The hub page reads only these and `/theme.json`, so the designed hub (`/design`, focus step 10) reads the same ones (plus `/api/arm` and `/api/devices`).

### `/api/status`
Polled every 3 s by the hub.
```json
{
  "venue": "lab",
  "persona": {"id": "lab-assistant", "display_name": "Lab Assistant",
              "picture": {"type": "orb", "style": "plain", "color": "primary"},
              "voice": "none", "sounds": "default"},
  "internet": true,
  "ai": {"setup": "main", "where": "OpenAI", "model": "gpt-6-luna", "connected": true,
         "paused": null, "problem": null, "busy": false},
  "assistant": {"state": "idle", "loudness": 0.0},
  "arm": {"name": "fake-arm", "control": "free"},
  "in_use": [],
  "time_ms": 1794264745533
}
```
- `persona`: the chosen persona (`--persona`, `$LAB_OS_PERSONA`, the venue's, or `place.yaml`; `docs/personas.md`), re-read every time; the designed hub draws `picture`.
- `internet`: `true` / `false`, or `null` until the first background check (every 30 s) has finished.
- `ai`: the chat's AI setup (`docs/chat.md`; `setup` is `null` when none is usable), `connected` (`null` until the first check, then `true`/`false`), `paused` (a full sentence when the chat can't answer: no key, budget used up), `problem` (the last failure, a sentence), `busy` (a turn is running).
- `assistant.state`: `idle`, `listening`, `thinking`, `speaking`, `offline`, `error`; `loudness` 0–1 while speaking. `offline` while no AI is connected; `error` after a failed answer until the service answers again.
- `arm.control`: `taken` while a teleop page (in the hub or on the Quest) drives the arm, `ai` while an AI tool's move runs, else `free`.
- `in_use`: what's in use right now (`"teleop"`, `"ai"`, `"chat"` while an answer streams); the hub never goes back to the start screen while it isn't empty.
- `time_ms`: the brain's clock (ms since 1970), so every screen shows the same time.

### `/api/project`
The Current Project panel, from the Steps list in `docs/current-focus.md`.
```json
{"available": true, "focus": "The JARVIS hub + AI driving a robot arm", "step": 1, "of": 10,
 "next": "Plain hub", "steps": [{"n": 0, "title": "Settle before coding", "done": true}, "…"]}
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
`joints`: degrees, shared joint names. `held`: held still (dead-man; true whenever nothing drives it). `control`: `free`, `teleop` or `ai`. Where the arm has kinematics also `gripper_point_cm` (`{x, y, z}` from the base), `gripper_open_pct`, and (SO-101) `side_cm`: every joint seen from the arm's side, `[{"name": "base", "r": 0, "z": 0}, …, {"name": "tip", "r": 25.8, "z": 4.9}]` (`r` = cm forward along the way the arm faces, `z` = cm up), for AI Control's drawing. When the arm stops answering: `{"name": …, "model": …, "connected": false, "problem": "<why>"}`.

### `/api/ai-calls?after=T`
The robot tools' calls this brain run (the last 50 after `T`, epoch seconds), for AI Control, polled once a second:
```json
{"calls": [{"time": "2026-11-10T12:44:04.120", "t": 1794336244.12, "tool": "move_to",
            "args": {"x_cm": 60, "y_cm": 0, "z_cm": 5}, "outcome": "clipped", "result": {"result": "arrived", "clipped": ["went 26% of the way: …"], "…": "…"}}],
 "mcp": "http://127.0.0.1:8081/mcp", "motion_allowed": true, "control": "free"}
```
`outcome`: `ok`, `clipped`, `short` (the move ended `stopped_short`), `refused` (then `result` is the sentence why), `stopped`, `error`. `mcp`: null when the AI tools are off (`--mcp-port 0`, or their port was taken).

### `/api/green`, `/api/green/start`
The training launcher (`docs/green-launcher.md`). `GET /api/green` → `{"ok": false, "lines": [{"ok": true, "text": "nothing else on a serial port (the white arm is unplugged)"}, …], "running": false, "url": "http://127.0.0.1:8000", "here": true}`: the port check (names in `/dev/serial/by-id/` and LeLab's saved settings only; nothing is opened), `running` = LeLab already answers, `here` = this page is on the brain's computer. `POST /api/green/start` checks again and, if every line is fine, opens a terminal on the brain's computer that starts LeLab: the same answer plus `"started": true | false`. Only from the brain's computer (`403` otherwise).

### `/api/settings`
`GET`: `{"sections": [{"id", "title", "help", "fields": [{"key": "theme:hub.look", "file", "label", "kind", "help", "choices", "min", "max", "step", "unit", "applies", "value"}]}], "writable": true, "why_not": null, "venue": "lab"}` (from `src/lab_os/settings.py`). `POST {"key": "theme:hub.look", "value": "design"}` changes one value in its file (comments kept): `{"ok": true, "key", "value", "applies": "reload" | "next" | "restart"}`, or `400 {"ok": false, "message": "<why>"}`. Only from the brain's computer: `403` otherwise, and `writable: false`.

### `/api/devices`
The place's devices from `devices.yaml` (no ports, nothing opened or probed):
```json
{"arm": "fake-arm",
 "devices": [{"name": "so101-green", "kind": "so101", "off_limits": true, "active_in_venue": false, "notes": "…", "linked": false},
             {"name": "fake-arm", "kind": "fake", "off_limits": false, "active_in_venue": true, "notes": "…", "linked": true}]}
```
`linked`: the arm this brain drives. Whether a device is switched on isn't known until the roll call (lab router).

### `/api/hub`
```json
{"title": "AI Comp Lab",
 "modules": [{"id": "teleop", "title": "Teleop", "page": "/teleop"},
             {"id": "monitor", "title": "Monitor", "page": "/monitor"}],
 "reset_after_s": 1800}
```
`title`: the place's name (`name` in `place.yaml`, `docs/places.md`), shown top left and in the startup. `modules`: the theme's `hub.modules` in order, only those with a page. `reset_after_s`: the venue's value, else the theme's `hub.reset_after_s`.

### Greeting
- `GET /api/greeting` → `{"hello": "Good evening.", "news": "Step 5, Typed chat, was finished today." | null, "source": "step" | "calendar" | "commits" | "persona", "text": "<hello + news, or hello + the persona's line>"}`.
- `POST /api/chat/start` → the same plus `"previous"` (as in `GET /api/chat`), and the conversation starts fresh with `text` as the assistant's first message (the hub calls it on the start press). A conversation with a question in it is put aside first.

### Chat
- `GET /api/chat` → `{"messages": [{"role": "user" | "assistant", "content": "…"}], "status": {…same as status.ai…}, "previous": {"questions": 2, "saved_at": <epoch seconds>} | null}`: the conversation the brain holds (one per brain; the hub's reset puts it aside) and the one put aside, if any (kept `chat_keep_minutes`, `docs/chat.md`).
- `POST /api/chat` with `{"text": "…"}` (at most 2000 characters) → one turn, streamed as **JSON lines** (`application/x-ndjson`), one event per line:
  ```
  {"type": "state", "state": "thinking"}
  {"type": "tool", "name": "project_status"}     (the assistant looks something up; 0–4 per turn)
  {"type": "state", "state": "speaking"}
  {"type": "text", "text": "Next is "}          (pieces of the answer, in order)
  {"type": "text", "text": "step 5."}
  {"type": "state", "state": "idle"}
  {"type": "done", "setup": "main", "cost_usd": 0.000164, "tools": 1}
  ```
  or `{"type": "error", "message": "<a full sentence for the screen>"}` (no key, budget used up, the service refused or didn't answer, "I'm still answering the last question."). One turn at a time.
- `POST /api/chat/clear` → `{"ok": true}`: start over; the conversation is put aside (if it has a question).
- `POST /api/chat/restore` → `{"ok": true | false, "messages": […], "previous": … | null}`: bring back the conversation put aside; the current one is put aside in its place (if it has a question), so a second call swaps back. `ok: false` when there's none (or a turn is running).

### `/api/spend`
This month's AI spend (`logs/ai-spend/`), for the AI Spend panel.
```json
{"available": true, "month": "2026-11", "spent_usd": 0.0123, "budget_usd": 20.0, "chats": 7,
 "by_setup": {"main": 0.0123, "backup": 0.0}}
```
`{"available": false}` on a venue with `public: true`. `budget_usd` is `null` when the place sets none.

## Recording files (`.jsonl`)
One line per received message: `{"dt": <seconds since recording start>, "msg": <message>}`. Written by `lab-os-teleop serve --record`, read by `lab-os-teleop replay`.
