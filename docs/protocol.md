# Message protocol

JSON messages over a WebSocket. This is the seed of the "one standard message protocol for all clients" in the architecture sketch (lab-jarvis-log.md). It grows as new clients appear; add message types here when you add them in code.

Every message has a `type`. Unknown or malformed messages are ignored (logged), never fatal.

## Connection
- `ws://<host>:8080/ws`: input clients (the XR page).
- `ws://<host>:8080/ws?role=monitor`: watchers. They receive `status`; the only message they may send is `stop`, so a monitor can never drive the arm.

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
- `pos`: metres, WebXR `local-floor` space: **+x right, +y up, −z forward** (the way the user faced when the session started). `quat` = orientation `[x, y, z, w]` of the controller's grip.
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
  "arm": {"name": "fake-arm", "model": "so101"},
  "joints": {"shoulder_pan": -12.0, "...": 0.0},
  "limits": {"shoulder_pan": [-110.0, 110.0], "...": [0, 0]},
  "last_command": { "...": "the latest arm_command, or null" }
}
```
- `frozen`: dead-man freeze is active (input stale > 250 ms, disconnected, session ended, or A/X pressed).
- `needs_release`: after a freeze, the operator must release the grip and press it again before the arm moves.
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
```

## MCP tools (AI tools → the brain)
Served by `lab-os serve` on `http://127.0.0.1:8081/mcp` (MCP over streamable HTTP, this computer only; `--mcp-port`). Setup, rules and examples: `docs/ai-control.md`. Positions in cm from the arm's base (x forward, y left, z up), angles in degrees.

| Tool | Arguments | Tier |
|---|---|---|
| `arm_status` | `arm?` | read |
| `list_poses` | `arm?` | read |
| `move_joints` | `joints` ({name: degrees}), `relative?` (false), `arm?` | move |
| `gripper` | `open_pct` (0 closed … 100 open), `arm?` | move |
| `move_to` | `x_cm`, `y_cm`, `z_cm`, `tool_angle_deg?` (0 up, 90 forward, 180 down; default: keep), `arm?` | move |
| `go_to_pose` | `name`, `arm?` | move |
| `stop` | `arm?` | always allowed |

Moves return `{"result": "arrived" | "stopped", "clipped": [notes], "joints_deg", "gripper_open_pct", "gripper_point_cm", "tool_angle_deg"}`. Refusals are tool errors whose text starts with `Refused:` and says why. While an AI move runs, `status.control` on the WebSocket is `"ai"`, teleop input gets the `error` "the AI tools have control", and `/api/status` lists `"ai"` in `in_use`.

## HTTP endpoints (the hub)
Served by `lab-os serve` (`src/lab_os/hub/server.py`). Plain JSON over `GET`, never cached. The hub page reads only these and `/theme.json`, so the designed page (focus step 9) can read the same ones.

### `/api/status`
Polled every 3 s by the hub.
```json
{
  "venue": "lab",
  "internet": true,
  "ai": {"connected": false},
  "assistant": {"state": "offline", "loudness": 0.0},
  "arm": {"name": "fake-arm", "control": "free"},
  "in_use": [],
  "time_ms": 1794264745533
}
```
- `internet`: `true` / `false`, or `null` until the first background check (every 30 s) has finished.
- `assistant.state`: `idle`, `listening`, `thinking`, `speaking`, `offline`, `error`; `loudness` 0–1 while speaking. `offline` while no AI is connected.
- `arm.control`: `taken` while a teleop page (in the hub or on the Quest) drives the arm, `ai` while an AI tool's move runs, else `free`.
- `in_use`: what's in use right now (`"teleop"`, `"ai"`); the hub never goes back to the start screen while it isn't empty.
- `time_ms`: the brain's clock (ms since 1970), so every screen shows the same time.

### `/api/project`
The Current Project panel, from the Steps list in `docs/current-focus.md`.
```json
{"available": true, "focus": "The JARVIS hub + AI driving a robot arm", "step": 1, "of": 9,
 "next": "Plain hub", "steps": [{"n": 0, "title": "Settle before coding", "done": true}, "…"]}
```
`step` is the first step that isn't done (`next` its title, `null` when all are done). `{"available": false}` when the file is missing or has no steps.

### `/api/commits?days=14`
Commits per day for the last `days` days (1–90; today included, oldest first), all local and remote branches, merges left out.
```json
{"available": true, "days": 14, "total": 84, "per_day": [{"date": "2026-10-27", "count": 9}, "…"]}
```
`{"available": false, "days": 14}` when git or the repository is missing.

### `/api/hub`
```json
{"title": "AI Comp Lab",
 "modules": [{"id": "teleop", "title": "Teleop", "page": "/teleop"},
             {"id": "monitor", "title": "Monitor", "page": "/monitor"}],
 "reset_after_s": 180}
```
`title`: the place's name (`name` in `place.yaml`, `docs/places.md`), shown top left and in the startup. `modules`: the theme's `hub.modules` in order, only those with a page. `reset_after_s`: the venue's value, else the theme's `hub.reset_after_s`.

## Recording files (`.jsonl`)
One line per received message: `{"dt": <seconds since recording start>, "msg": <message>}`. Written by `lab-os-teleop serve --record`, read by `lab-os-teleop replay`.
