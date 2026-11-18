# What lab-os can do

The features that are built and working today, plus a few lab robot projects that aren't connected to lab-os yet. What's being built now: `docs/plan/current-focus.md`. Ideas not built yet: `docs/plan/ideas.md`. Changes by date: `CHANGELOG.md`.

**Status key:** ✅ tried on the real hardware · 🧪 built and tested on the fake arm or in a browser, not yet on the real hardware · 🟡 works, with known rough edges

---

## The hub (the lab's start screen)
`uv run lab-os serve` → http://localhost:8080/ · `docs/guides/hub.md`

| Feature | Status | Notes |
|---|---|---|
| Plain hub: start screen, status strip, module buttons, assistant circle, Current Project and Commits panels | ✅ | Ran on the lab desktop, `pi01` and the Newline. On the Newline it lags (`docs/plan/current-focus.md` → step 12) |
| Designed hub preview (`/design`): hyperspace startup, network and core, panels with details pages, sounds; the ask line's mic and history icons centred between their lines (2026-11-17); the core's arrival lighter (2026-11-17: the sound's noise made at load, the jump makes no garbage per frame) | ✅ | Lab desktop and Pi screens. `/` still shows the plain hub by default (`hub.look: plain`), just in case; the design is no longer a surprise (2026-11-12) |
| The hub in VR (`/xr`): the designed hub's startup around you (ignition, the hyperspace jump, the core assembling, checks, title, greeting), then the hub around you: callouts with their details, strip, ⏻, log | 🟡 | Matches `/design` since 2026-11-12. Module buttons: Teleop in VR, Monitor and AI Control as holograms. Asking by voice (push-to-talk on the ask line, the wake word on the headset). Works in the headset (2026-11-13); a far-away cluster of dots (quick job 10); the chat scrolls since 2026-11-16 (quick job 11) |
| Settings page (⚙, `/settings`): writes the YAML config, keeps its comments; the hub's ⚙ shows every section, the AI budget and the safety limits included (scrolls down; 2026-11-17) | 🧪 | Can only be changed from the brain's own computer |
| **Named devices** (`/?device=desk`): the brain lists the devices with the hub open (each monitor a window); "This device" settings (detail, drawing resolution, sound, voice's way in) kept by the brain under the name; pages reconnect by themselves when the brain restarts | 🧪 | Built 2026-11-14, tried with headless browser pages as devices (`docs/guides/hub.md` → "Devices") |
| **Open on…** a module on another device's hub (the free monitor, or it asks which); Back there or **Bring it back** here closes it. Only devices with the hub open are listed | 🧪 | Both looks. Still to try desk ↔ Newline in the lab (`docs/guides/lab-checklist.md` part 9) |
| One tap per device: "Start lab-os" on the brain's computer (`lab-os icon`, `lab-os serve --open desk`), a "Lab hub" icon for other computers (⚙ → This device), a home-screen icon on the Newline | 🧪 | Linux icons; macOS/Windows get the command |
| Drawing resolution per screen (`?res=`), detail levels (`?quality=`) for slow screens | 🧪 | Still to try on the hub on the Newline (`/perf` there: 44–59 fps) |
| Full-screen button on every page; Esc = Back without leaving full screen (Chrome/Edge) | ✅ | |
| Back to the start screen after 30 minutes with nobody there (never while teleop has the arm) | ✅ | |
| Show a module on another monitor of the brain's computer (Open on… → Another monitor of this computer) | 🧪 | Uses Chrome's Window Management API |
| Other computers on the network can view; only the brain's computer drives (`--drive-from <host>` lets one other computer drive) | ✅ | Tried with `pi01`, a second lab desktop and the Newline (its STOP stopped the arm) |
| Performance test page (`/perf`) | ✅ | The Newline's own Chrome: 44 fps with 3000 stars, 59 with 1000 (2026-11-13) |

## Talking to it (typed chat, voice and personas)
`docs/dev/chat.md`, `docs/guides/voice.md`, `docs/dev/personas.md`

| Feature | Status | Notes |
|---|---|---|
| Typed chat under the circle ("Ask anything"), answers stream and type themselves out, History page | ✅ | Tried with the free Gemini key; OpenAI is set up but untested without its key |
| Swap AI setups in `config/models.yaml` (OpenAI, Gemini, local Ollama); falls back to Gemini without an OpenAI key | ✅ | |
| Spend log per answer and a monthly budget that pauses the chat (the designed hub says why once, at the top); the budget can be changed on Settings and applies at once | ✅ | $20/month at the lab |
| The chat knows the project: reads the docs, git history and device list; drafts prompts for Claude Code / Codex (Copy button) | ✅ | Read-only: the chat can never move a robot |
| **Push-to-talk:** hold the mic button (or Space), talk, let go; the words appear while you talk, the answer is spoken sentence by sentence and the core follows its loudness. Same conversation as typing (tools, history, budget) | ✅ | On the free Gemini key (~15–20 spoken answers a day). Works at the lab desktop with a USB microphone and on the Quest (2026-11-13). No mic button without a secure page (localhost/https), a microphone, or voice at the brain |
| **Dictation:** tap the mic (or Space); the words go into the ask line as you talk, it stops after a short silence or a second tap; fix and send like typing | 🧪 | Chosen per device: ⚙ → This device → Talking to it (push-to-talk is the default) |
| **Wake word:** say "hey Jarvis" from anywhere in the room, then the question; it answers aloud. Heard on the brain's own CPU (openWakeWord), nothing sent until the phrase; a small dot in the status strip while it listens; several screens: one answers | 🟡 | Chosen per device; off by default on public venues. Works at the desk with the lab's USB microphone (sometimes only spoken louder); on the Quest it sometimes misses (2026-11-13) |
| **Snappier wake word, adjustable** (2026-11-14): a quiet sound the moment it hears the phrase; the voice service connected ahead of time; no lost first words; the question ends on the service's pause (or 1 s of quiet); a **sensitivity slider per device** (⚙ → This device, 1–9, default 5); each turn's timing logged and at `/api/voice/timings`; the Quest's paused microphone woken by itself (orange dot while it can't) | 🧪 | Tested with the recordings and the fake voice service, not yet in the lab (`docs/guides/lab-checklist.md` part 9e) |
| **Assistant language per device** (2026-11-18): ⚙ → This device → Assistant language: Input and Output, each Any or English. Output English answers in English, typed or spoken, whatever it was asked in; Input English tells speech-to-text to expect English | 🧪 | Tested without hardware. Input only works with OpenAI's voice (Gemini's free transcriber has no language setting), so at the lab today only Output does something |
| **"Give me a status report"** (2026-11-16): one look-up (`lab_status`) with the arm, the devices with the hub open, voice, AI, spend, the next step and warnings, said in a few sentences | 🧪 | Tested with the fake arm; the spoken answer not yet tried |
| **The assistant opens pages** (2026-11-14): "pull up the teleop page", "show me the AI spend", "open the settings", "go back to the hub", typed or spoken, on the screen that asked, with a short answer ("Here's Teleop.") right away. Designed hub, plain hub and VR. The docked core on an open page: hold it to talk, its reply beside it; the wake word keeps listening with a page open | 🧪 | Tested with a fake chat service, the fake voice service and headless Chrome (`docs/guides/lab-checklist.md` part 9g) |
| **Spoken greeting** after the start tap: the time of day plus "You can talk to me: hold the mic." (no hint without a microphone; the news stays on the screen); on the designed hub it plays while the greeting is typed after the jump | 🧪 | Recorded once per voice (`recordings/greetings/`), then played with no voice request (2026-11-14). Silent where the screen's sound is off, or not recorded yet and no voice |
| Voice setups in `config/models.yaml` (`voices:`): OpenAI falls back to Gemini's free key; the persona's `voice:` picks one | 🧪 | OpenAI's voice untested without its key |
| Personas: `lab-assistant` (default) and `jarvis`, picked per place, per venue or with `--persona` | ✅ | |
| A greeting with real news (a step finished, the calendar, a busy day of commits) | ✅ | |
| The conversation is kept for 30 minutes; "Bring back the last conversation" after a reset or restart | ✅ | |

## Teleop (drive an arm with a Quest 3)
`uv run lab-os serve`, then the teleop page · `docs/guides/quest-setup.md` · demo tag `demo-2026-10-30`

| Feature | Status | Notes |
|---|---|---|
| Quest 3 controllers drive `so101-white` through inverse kinematics: grip = clutch, trigger = gripper, A/X = stop | ✅ | The working demo |
| Bare-hand tracking: right wrist drives, left pinch = clutch, right pinch = gripper | 🟡 | Works but is hard to steer |
| 1:1 mode ("Hand → arm"): the gripper goes exactly where your hand is | 🧪 | Fake arm only so far |
| Speed slider and right thumbstick (capped by the venue); the gripper and wrist stay above the venue's floor (`min_z_cm`, −0.5 cm since 2026-11-14) | ✅ | |
| Relative mode at scale 1 (10 cm of hand = 10 cm of gripper) and the 1:1 follow speed (up to 180°/s in the lab, scaled by the Speed slider), 2026-11-16 | 🧪 | Fake arm only so far (`docs/guides/lab-checklist.md` 7.7) |
| 3D arm in the headset (see-through ghost in AR), movable onto the real arm | ✅ | |
| Desktop control without a headset: keyboard + trackpad act as a controller; **X** = STOP in every mode, shown as "X = STOP" beside the STOP button while it's on (2026-11-17); **`** (backtick) or Esc leaves it and frees the pointer (2026-11-17) | ✅ | The "X = STOP" label is 🧪 (headless browser) |
| Record and replay controller sessions (`--record`, `lab-os-teleop replay`) | ✅ | For testing without a headset |
| Redesigned teleop and monitor pages (3D on the left, controls on the right, STOP in the bar) | ✅ | Old pages at `/classic/…`. Teleop: the 3D view in a fixed box with the joint readout in its own column, so it no longer resizes while jogging (2026-11-14). "Outside the arm's limits" is judged against the driver's limits in force, at the angle the driver holds (2026-11-17; before, a command clamped to the limit also read "outside model limits") |
| Freezes on release, lost tracking, disconnect or stale input; STOP on every page | ✅ | |

## AI tools driving the arm (MCP)
http://127.0.0.1:8081/mcp · `docs/guides/ai-control.md`

| Feature | Status | Notes |
|---|---|---|
| Robot tools for an AI agent (Claude Code, Codex, …): `arm_status`, `list_poses`, `move_joints`, `gripper`, `move_to`, `go_to_pose`, `stop` | ✅ | `so101-white`. Claude Code runs every tool without asking, moves included (repo settings, 2026-11-14); STOP and the brain's limits are the brake. Poses: `ready` (the working pose, teleop's start) and `home` (folded, gripper slightly open; computed only until lab check 8.16), since 2026-11-17. The cube pick on 2026-11-12 closed just past the cube: the height reads 1–2 cm low |
| Safety built into the tools: soft limits, max 30° / 10 cm per call, table floor, "can't reach" instead of guessing, "stopped short" with by how much | ✅ | Every call logged to `logs/ai-tools/` |
| Named poses: `ready` (the working pose) and `home`, the folded pose the arm is left in: since 2026-11-18 the builder's own (lab check 8.16), hovering just above the rest (quick job 30) | 🧪 | Fake arm only; two joints stop at their soft limits and the move says so. Lab check F.3 |
| **Heights from the table** (2026-11-18, quick job 28): an arm on a plate has its table height in `devices.yaml` (`so101-white`: −1.6 cm); `move_to`, `pick_at`, the floor (1.1 cm above the table), `arm_status`, `pose_view`, AI Control and teleop's floor all measure from the table | 🧪 | Fake arm only; lab check F.2 (touch the table, read z ≈ 0) |
| The per-move limit, the speed cap and the floor can each be switched off (venue file or Settings → Safety limits); never on public or visit-day venues | ✅ | Tested on the fake arm (2026-11-14). STOP, the soft limits and one controller at a time always stay |
| `pose_view`: a picture of the arm's 3D model in its current pose, with the AI's marks for where it thinks things are | ✅ | Used in the cube pick on the real arm (2026-11-12); also at `/api/pose-view.png` |
| `pick_at`: a whole pick in one call (open, above, straight down, close, lift), each step shown on AI Control before it moves; says holding or missed (2026-11-16) | 🧪 | Fake arm only (`docs/guides/lab-checklist.md` 3b.5) |
| Table map: the stand camera's pictures get a cm grid of the table, from a printed sheet (`lab-os table-map`); `table_point` turns a pixel into cm (2026-11-16) | 🧪 | A drawn sheet in perspective only so far (`docs/guides/lab-checklist.md` part 3b) |
| `camera_snapshot`: one real picture from a camera (the white arm's: `so101-white-cam-wrist` in socket 7 and `-cam-stand` in socket 8, the same sockets as the green set's; swapped 2026-11-18, quick job 29, from lab check 3.9) | ✅ | Used in the cube pick (2026-11-12). The stand camera's picture gives a direction, not a place (it doesn't know where the camera is) |
| AI Control page (`/ai`): the arm from the side, every AI tool call live, STOP | ✅ | |
| Project read tools for developers' AI tools: `project_status`, `read_doc`, `search_docs`, `git_log`, `list_devices`, … | ✅ | `docs/design/` included since 2026-11-12 |

## Robots and drivers
| Robot | Status | Notes |
|---|---|---|
| `so101-white` (SO-101 arm, LeRobot) | ✅ | Driver, guarded motor setup and calibration, read-only `--watch` mode. `uv sync --extra so101` |
| `so101-green` (the training set's follower, borrowed) | 🧪 | `--arm so101-green`: same driver, calibration read only from LeRobot's cache (since 2026-11-17 the file that equals what the motors hold, whichever LeLab setup wrote it; it says which), motor setup refused, refused while LeLab has the port. The arm itself was driven in the lab 2026-11-16 (checklist part 8); the matching is tested without hardware only (lab: part 8b). `docs/guides/ai-control.md` → "The green arm" |
| The training cameras (`so101-green-cam-wrist` in socket 7, `so101-green-cam-stand` in socket 8; named 2026-11-17 from lab check 8.15) | 🧪 | Listed by USB socket; a camera another program uses is refused. `camera_snapshot` can use them |
| `xarm1` (Hiwonder xArm 1S, USB) | ✅ | Driver, jogging, inverse kinematics, hand calibration of the limits. `--arm xarm1` |
| **An SO-101 unplugged and plugged back in** (2026-11-18, quick job 27): within about half a second the brain freezes it, ends any AI move ("disconnected"), and every page says the arm is disconnected; when the same USB name comes back it reconnects by itself, the way it does at startup (goals = where the motors are, then torque). Grab again to drive. A green arm that LeLab took meanwhile isn't reopened | 🧪 | Fake arm and a stand-in port only; lab check F.4–F.5. The xArm doesn't notice yet |
| Fake arm | ✅ | Every feature runs on it first; no hardware needed |
| 3D models: SO-101 (from its URDF) and the xArm 1S (rebuilt from Hiwonder's drawing) | ✅ | Bundled, work offline |

## Running it anywhere
| Feature | Status | Notes |
|---|---|---|
| Places: run at home or in another lab with its own config folder (`--config`, `lab-os new-place`) | ✅ | `docs/dev/places.md` |
| Venues (lab, visit-day, …) set speed limits, persona and what's shown to the public | ✅ | `config/venues/` |
| Works offline: every web library and font is bundled | ✅ | |
| One-line install on a fresh Linux machine (`scripts/install.sh`) | ✅ | |
| Tests and lint on every push (GitHub Actions), no hardware needed | ✅ | |

## Training launcher (so101-green)
| Feature | Status | Notes |
|---|---|---|
| `lab-os green` (desktop icon, hub's Training page): checks the green arms' ports, then starts LeLab; **Stop LeLab** / `--stop` stops only the LeLab it started (2026-11-16) | 🧪 | Not yet tried with the green arms plugged in. The launcher opens no green port; it refuses while any program other than LeLab (e.g. the brain driving `so101-green`) has one open, even when LeLab is already running (2026-11-17, quick job 17). `docs/guides/green-launcher.md` |

---

## Lab projects not connected to lab-os (yet)
Separate projects using the lab's robots. They don't run through the brain and their code isn't in this repo.

### xArm control with the Hiwonder Bluetooth glove
- **What:** the Hiwonder glove (5 finger sensors, a motion sensor, Bluetooth) pairs straight to `xarm1` and drives it. Tilt the hand to turn the wrist; the number of bent fingers picks which motor moves.
- **Status:** ✅ works with Hiwonder's own firmware (tested 2026-10-23). Little lag; tilt to rotate works well.
- **Rough edges:** needs extreme gestures; the arm snaps when switching motors (absolute tilt → angle); picking motors by counting fingers is clumsy. These lessons shaped lab-os teleop (clutch, relative control, gentle ramps, per-user calibration). Notes: `docs/plan/lab-jarvis-log.md` → "Hiwonder glove findings".
- **Connecting it later:** `docs/plan/ideas.md` → "Fix the Hiwonder glove".

### Raspbot voice control
- **What:** on a Yahboom Raspbot v2, press a button on the IR remote and speak. After 3 seconds it transcribes the speech, and if it hears a known word (forward, backward, left, right) it moves a little that way.
- **Status:** ✅ worked (the builder's project, before lab-os). Where its code lives: still to note.
- **Notes:** `docs/plan/lab-jarvis-log.md` → "Facts about the lab". lab-os voice is focus step 7; the IR-remote trigger is in `docs/plan/ideas.md` → "Voice beyond push-to-talk".

### xArm camera demos (`xarm_1s_demo`, June 2026)
- **What:** Python scripts that drive the xArm 1S from a webcam: follow a green ball with the base (`arm_follow_ball.py`), follow it in 2D with the base and reach (`arm_2d_follow.py`), and grab an object at a camera point after a 3-point camera-to-servo calibration (`test_safe_grab_v2.py`).
- **Status:** a separate folder on the builder's Mac, not in a git repo here. lab-os's xArm default limits come from its grab script.
- **Connecting it later:** `docs/plan/ideas.md` → "Ways to teach a robot" (look-then-reach).
