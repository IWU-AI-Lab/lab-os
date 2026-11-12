# What lab-os can do

The features that are built and working today, plus a few lab robot projects that aren't connected to lab-os yet. What's being built now: `docs/current-focus.md`. Ideas not built yet: `docs/ideas.md`. Changes by date: `CHANGELOG.md`.

**Status key:** ✅ tried on the real hardware · 🧪 built and tested on the fake arm or in a browser, not yet on the real hardware · 🟡 works, with known rough edges

---

## The hub (the lab's start screen)
`uv run lab-os serve` → http://localhost:8080/ · `docs/hub.md`

| Feature | Status | Notes |
|---|---|---|
| Plain hub: start screen, status strip, module buttons, assistant circle, Current Project and Commits panels | ✅ | Ran on the lab desktop, `pi01` and the Newline. On the Newline it's laggy (`docs/current-focus.md` → step 1) |
| Designed hub preview (`/design`): hyperspace startup, network and core, panels with details pages, sounds | ✅ | Lab desktop and Pi screens. `/` still shows the plain hub by default (`hub.look: plain`), just in case; the design is no longer a surprise (2026-11-12) |
| The hub in VR (`/xr`): the hyperspace jump around you, then the network and the core | 🟡 | Watch-only for now: no buttons or chat inside VR |
| Settings page (⚙, `/settings`): writes the YAML config, keeps its comments; "This screen" settings per browser | 🧪 | Can only be changed from the brain's own computer |
| Drawing resolution per screen (`?res=`), detail levels (`?quality=`) for slow screens | 🧪 | Still to try on the Newline |
| Full-screen button on every page; Esc = Back without leaving full screen (Chrome/Edge) | ✅ | |
| Back to the start screen after 30 minutes with nobody there (never while teleop has the arm) | ✅ | |
| Show a module on another monitor of the brain's computer | 🧪 | Uses Chrome's Window Management API |
| Other computers on the network can view; only the brain's computer drives (`--drive-from <host>` lets one other computer drive) | ✅ | Tried with `pi01` and a second lab desktop |
| Performance test page (`/perf`) | 🧪 | Numbers from the Newline still missing |

## Talking to it (typed chat and personas)
`docs/chat.md`, `docs/personas.md`

| Feature | Status | Notes |
|---|---|---|
| Typed chat under the circle ("Ask anything"), answers stream and type themselves out, History page | ✅ | Tried with the free Gemini key; OpenAI is set up but untested without its key |
| Swap AI setups in `config/models.yaml` (OpenAI, Gemini, local Ollama); falls back to Gemini without an OpenAI key | ✅ | |
| Spend log per answer and a monthly budget that pauses the chat | ✅ | $20/month at the lab |
| The chat knows the project: reads the docs, git history and device list; drafts prompts for Claude Code / Codex (Copy button) | ✅ | Read-only: the chat can never move a robot |
| Personas: `lab-assistant` (default) and `jarvis`, picked per place, per venue or with `--persona` | ✅ | |
| A greeting with real news (a step finished, the calendar, a busy day of commits) | ✅ | |
| The conversation is kept for 30 minutes; "Bring back the last conversation" after a reset or restart | ✅ | |

## Teleop (drive an arm with a Quest 3)
`uv run lab-os serve`, then the teleop page · `docs/quest-setup.md` · demo tag `demo-2026-10-30`

| Feature | Status | Notes |
|---|---|---|
| Quest 3 controllers drive `so101-white` through inverse kinematics: grip = clutch, trigger = gripper, A/X = stop | ✅ | The working demo |
| Bare-hand tracking: right wrist drives, left pinch = clutch, right pinch = gripper | 🟡 | Works but is hard to steer |
| 1:1 mode ("Hand → arm"): the gripper goes exactly where your hand is | 🧪 | Fake arm only so far |
| Speed slider and right thumbstick (capped by the venue); the arm stays 1 cm above the table | ✅ | |
| 3D arm in the headset (see-through ghost in AR), movable onto the real arm | ✅ | |
| Desktop control without a headset: keyboard + trackpad act as a controller | ✅ | |
| Record and replay controller sessions (`--record`, `lab-os-teleop replay`) | ✅ | For testing without a headset |
| Redesigned teleop and monitor pages (3D on the left, controls on the right, STOP in the bar) | ✅ | Old pages at `/classic/…` |
| Freezes on release, lost tracking, disconnect or stale input; STOP on every page | ✅ | |

## AI tools driving the arm (MCP)
http://127.0.0.1:8081/mcp · `docs/ai-control.md`

| Feature | Status | Notes |
|---|---|---|
| Robot tools for an AI agent (Claude Code, Codex, …): `arm_status`, `list_poses`, `move_joints`, `gripper`, `move_to`, `go_to_pose`, `stop` | ✅ | `so101-white`, blind, with a person approving every move |
| Safety built into the tools: soft limits, max 30° / 10 cm per call, table floor, "can't reach" instead of guessing, "stopped short" with by how much | ✅ | Every call logged to `logs/ai-tools/` |
| `pose_view`: a picture of the arm's 3D model in its current pose, with the AI's marks for where it thinks things are | 🧪 | Stands in for cameras until they're added; also at `/api/pose-view.png` |
| AI Control page (`/ai`): the arm from the side, every AI tool call live, STOP | ✅ | |
| Project read tools for developers' AI tools: `project_status`, `read_doc`, `search_docs`, `git_log`, `list_devices`, … | ✅ | |

## Robots and drivers
| Robot | Status | Notes |
|---|---|---|
| `so101-white` (SO-101 arm, LeRobot) | ✅ | Driver, guarded motor setup and calibration, read-only `--watch` mode. `uv sync --extra so101` |
| `xarm1` (Hiwonder xArm 1S, USB) | ✅ | Driver, jogging, inverse kinematics, hand calibration of the limits. `--arm xarm1` |
| Fake arm | ✅ | Every feature runs on it first; no hardware needed |
| 3D models: SO-101 (from its URDF) and the xArm 1S (rebuilt from Hiwonder's drawing) | ✅ | Bundled, work offline |

## Running it anywhere
| Feature | Status | Notes |
|---|---|---|
| Places: run at home or in another lab with its own config folder (`--config`, `lab-os new-place`) | ✅ | `docs/places.md` |
| Venues (lab, visit-day, …) set speed limits, persona and what's shown to the public | ✅ | `config/venues/` |
| Works offline: every web library and font is bundled | ✅ | |
| One-line install on a fresh Linux machine (`scripts/install.sh`) | ✅ | |
| Tests and lint on every push (GitHub Actions), no hardware needed | ✅ | |

## Training launcher (so101-green)
| Feature | Status | Notes |
|---|---|---|
| `lab-os green` (desktop icon, hub's Training page): checks the green arms' ports, then starts LeLab | 🧪 | Not yet tried with the green arms plugged in. lab-os never opens the green arm's ports. `docs/green-launcher.md` |

---

## Lab projects not connected to lab-os (yet)
Separate projects using the lab's robots. They don't run through the brain and their code isn't in this repo.

### xArm control with the Hiwonder Bluetooth glove
- **What:** the Hiwonder glove (5 finger sensors, a motion sensor, Bluetooth) pairs straight to `xarm1` and drives it. Tilt the hand to turn the wrist; the number of bent fingers picks which motor moves.
- **Status:** ✅ works with Hiwonder's own firmware (tested 2026-10-23). Little lag; tilt to rotate works well.
- **Rough edges:** needs extreme gestures; the arm snaps when switching motors (absolute tilt → angle); picking motors by counting fingers is clumsy. These lessons shaped lab-os teleop (clutch, relative control, gentle ramps, per-user calibration). Notes: `docs/lab-jarvis-log.md` → "Hiwonder glove findings".
- **Connecting it later:** `docs/ideas.md` → "Fix the Hiwonder glove".

### Raspbot voice control
- **What:** on a Yahboom Raspbot v2, press a button on the IR remote and speak. After 3 seconds it transcribes the speech, and if it hears a known word (forward, backward, left, right) it moves a little that way.
- **Status:** ✅ worked (the builder's project, before lab-os). Where its code lives: still to note.
- **Notes:** `docs/lab-jarvis-log.md` → "Robots". lab-os voice is focus step 7; the IR-remote trigger is in `docs/ideas.md` → "Voice beyond push-to-talk".

### xArm camera demos (`xarm_1s_demo`, June 2026)
- **What:** Python scripts that drive the xArm 1S from a webcam: follow a green ball with the base (`arm_follow_ball.py`), follow it in 2D with the base and reach (`arm_2d_follow.py`), and grab an object at a camera point after a 3-point camera-to-servo calibration (`test_safe_grab_v2.py`).
- **Status:** a separate folder on the builder's Mac, not in a git repo here. lab-os's xArm default limits come from its grab script.
- **Connecting it later:** `docs/ideas.md` → "Ways to teach a robot" (look-then-reach).
