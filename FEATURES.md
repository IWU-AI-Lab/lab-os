# What lab-os can do

This page lists the features that work today, and some lab robot projects that are not connected to lab-os yet. What we build now: `docs/plan/current-focus.md`. Ideas: `docs/plan/ideas.md`. Changes by date: `CHANGELOG.md`. How to use each feature: the guide named under each heading.

**Status:** ✅ tried on the real hardware · 🧪 built and tested on the fake arm or in a browser, not yet on the real hardware · 🟡 works, with known problems

---

## The hub (the lab's start screen)
`uv run lab-os serve` → http://localhost:8080/ · `docs/guides/hub.md`

| Feature | Status | Notes |
|---|---|---|
| The plain hub: start screen, status strip, module buttons, the assistant, the Current Project and Commits panels | ✅ | Ran on the lab desktop, `pi01` and the Newline. On the Newline it is slow (`docs/plan/current-focus.md` → step 12). |
| The designed hub (`/design`): the hyperspace startup, the network and the core, panels with details pages, sounds | ✅ | Lab desktop and Pi screens. `/` shows the plain hub by default (`hub.look: plain`). |
| **Startup as a video** (2026-11-18, a test): the designed hub plays a recording of the startup, with the words, the sounds and the hub after it live. Off by default (⚙ → This Device). | ✅ | Looks the same as the drawn startup on the Mac. Smoother on the lab desktop? Lab check F.8. |
| The hub in VR (`/xr`): the designed hub's startup around you, then the hub around you: the panels with their details, the strip, ⏻, the log. Teleop in VR; Monitor and AI Control as holograms; asking by voice. | 🟡 | Works in the headset (2026-11-13). The dark cluster of dots in AR was fixed 2026-11-18 (lab check F.10). |
| **System diagram** (2026-11-18): the network icon in the Devices panel shows how the brain, the screens, the robots and the AI connect, drawn from the real facts. A copy: `docs/dev/system-diagram.svg`. | 🧪 | Tried in Chrome on the Mac with the fake arm. |
| **Visitor mode** (2026-11-18): on the brain's own screen, tell the assistant that visitors are here, in any words ("hey Jarvis, it's demo time"). The AI switches to the visit-day venue, welcomes them in its own words from real facts, and the hub shows "try this" cards. When asked, it waves the arm (fixed poses) and exits visitor mode. ⚙ → The Lab starts and exits it without asking. | 🟡 | Tried with the real AI (OpenAI) on the fake arm: it selected each tool from different words. Real arm: lab check F.11. |
| **The assistant moves the arm** (preview, 2026-11-20): on the brain's own computer, "move the arm to home" (or ready, or handover) and "hand me the cube": the brain finds the blue cube in the stand camera's picture by its colour, the arm picks it up and holds it out; "let go" opens the gripper. Off unless ⚙ → Robots → The Assistant May Move the Arm. | 🧪 | The fake arm, through the hub's chat with a stand-in AI, and the cube found in test pictures. STOP ends it. Lab: check part H (2026-11-24). |
| **Settings** (⚙, `/settings`), new layout 2026-11-19: groups by what a setting affects, a sidebar, groups that fold, all values on one edge, "Saved" for a moment, **Restart Now**, safety limits and Shut Down apart at the bottom. It writes the config files and keeps their comments. | 🟡 | Changes only from the brain's own computer. Real arm: lab check F.14. |
| **Shut down lab-os** from the hub (2026-11-18): ⏻ on the brain's computer, or ⚙ → Safety Limits and Shut Down. It asks first, names each arm that goes limp (first line and on the button), stops any move and lets go of the arm as Ctrl+C does. From the moment it starts, nothing moves (AI tools, the wave, teleop) and the motors are never switched on again; it ends in about one second (2026-11-19, quick job 44: before, ~30 s, and the AI's next move ran). Every page says "lab-os is off", the VR/AR hub and the headset's teleop panel too, and comes back when the brain runs again. | 🟡 | Software arm, Chrome and the VR hub preview only. Allowed on any venue (2026-11-19). Real arm: lab check S.1 to S.5. |
| **Named devices** (`/?device=desk`): the brain lists the devices with the hub open (each monitor is a window) and keeps each device's settings under its name. Pages connect again by themselves when the brain restarts. | ✅ | Tried with headless browser pages as devices. Lab: checklist part 11. |
| **Open on…:** a module opens on another device's hub (the free monitor, or it asks which). Back there or **Bring it back** here closes it. Only devices with the hub open are listed. | ✅ | Both looks. Desk and Newline in the lab: checklist part 11. |
| One tap for each device: "Start lab-os" on the brain's computer (`lab-os icon`), a "Lab hub" icon for other computers (⚙ → This Device), a home-screen icon on the Newline | 🧪 | Linux icons; macOS and Windows get the command. |
| Drawing resolution for each screen (`?res=`) and levels of detail (`?quality=`) for slow screens | ✅ | The hub on the Newline: checklist part 2 (`/perf` there: 44 to 59 frames a second). |
| A Full screen button on every page; Esc = Back without leaving full screen (Chrome, Edge) | ✅ | |
| Back to the start screen after 30 minutes with nobody there (never while something is in use) | ✅ | |
| A module on another monitor of the brain's computer (Open on… → Another monitor of this computer) | 🧪 | Uses Chrome's Window Management API. |
| Other computers on the network can watch; only the brain's computer drives (`--drive-from <host>` lets one more computer drive) | ✅ | Tried with `pi01`, a second lab desktop and the Newline (its STOP stopped the arm). |
| Performance test page (`/perf`) | ✅ | The Newline's own Chrome: 44 frames a second with 3000 stars, 59 with 1000 (2026-11-13). |

## Talking to it (typed chat, voice and personas)
`docs/dev/chat.md`, `docs/guides/voice.md`, `docs/dev/personas.md`

| Feature | Status | Notes |
|---|---|---|
| Typed chat under the core ("Ask anything"); the answers show at a steady speed; the History page | ✅ | OpenAI (`main`) since 2026-11-18; the free Gemini key is the fallback. |
| AI setups in `config/models.yaml` (OpenAI, Gemini, a local Ollama); Gemini when there is no OpenAI key | ✅ | |
| A spend log for each answer and a monthly budget that pauses the chat; the budget changes in Settings and applies at once | ✅ | $20 a month in the lab. |
| The AI Spend panel says "Estimated · this computer's brain only"; its page says how the cost is calculated and how much of it is less exact (voice, counted tokens). The assistant says "estimated" with the number. | ✅ | Tested without hardware and in headless Chrome. The real cost from OpenAI needs an Admin key (`docs/guides/hub.md` → "AI Spend"). Lab: check F.15. |
| The chat knows the project: it reads the docs, the git history and the device list, and writes prompts for Claude Code or Codex (Copy button) | ✅ | Read tools only. The moves it can start: visitor mode's fixed wave, and (when Settings allows it) a named pose and the cube's hand-over. |
| **Push-to-talk:** hold the mic button (or Space), talk, release. The answer is spoken sentence by sentence, and the core follows its loudness. The same conversation as typing. | ✅ | Works at the lab desktop with a USB microphone and on the Quest. No mic button without a secure page, a microphone, or voice at the brain. |
| **Dictation:** tap the mic (or Space). The words go into the ask line while you talk; it stops after a short silence or a second tap. | 🧪 | Selected for each device: ⚙ → This Device → Talking to It. |
| **Wake word:** say "hey Jarvis" from anywhere in the room, then the question. The brain hears the phrase on its own CPU (openWakeWord) and sends nothing until then. A small dot in the strip while it listens. With more screens, one answers. A sensitivity slider for each device (1 to 9). | 🟡 | Off by default on public venues. Works at the desk with the USB microphone (sometimes only when spoken louder) and on the Quest (2026-11-17; its misses scored just under the line: lab check F.6). |
| **Assistant language for each device** (2026-11-18): Listens and Answers, each Any or English | 🟡 | Tested without hardware; lab checks 9.13 and 9.14. Listens works only with OpenAI's voice. |
| **"Give me a status report"** (`lab_status`): the arm, the devices with the hub open, voice, AI, spend, the next step and warnings, in a few sentences | 🧪 | Tested with the fake arm; the spoken answer not yet tried. |
| **The assistant opens pages:** "pull up the teleop page", "show me the AI spend", "go back to the hub", typed or spoken, on the screen that asked. Designed hub, plain hub and VR. | ✅ | Tested with a fake chat service and headless Chrome. Lab: checks 9.9 to 9.12. |
| **The spoken greeting** after the start tap: the time of day and how to talk (the news stays on the screen) | ✅ | Recorded once for each voice (`recordings/greetings/`), then played with no voice request. Silent where the screen's sound is off. |
| Voice setups in `config/models.yaml` (`voices:`); the persona's `voice:` selects one; OpenAI falls back to Gemini's free key | ✅ | OpenAI's key is in `.env` on the laptop and the lab desktop since 2026-11-18. |
| Personas: `lab-assistant` (default) and `jarvis`, selected for each place, each venue, or with `--persona` | ✅ | |
| A greeting with real news (a step finished, the calendar, a busy day of commits) | ✅ | |
| The brain keeps the conversation for 30 minutes; "Bring back the last conversation" after a reset or a restart | ✅ | |

## Teleop (drive an arm with a Quest 3)
`uv run lab-os serve`, then the teleop page · `docs/guides/quest-setup.md` · demo tag `demo-2026-10-30`

| Feature | Status | Notes |
|---|---|---|
| Quest 3 controllers drive `so101-white` through inverse kinematics: grip = clutch, trigger = gripper, A/X = stop | ✅ | The working demo. |
| Bare hands: the right wrist drives, a left pinch = clutch, a right pinch = gripper | 🟡 | Works, but is difficult to steer. |
| The relative mode at scale 1 (10 cm of hand = 10 cm of gripper), following at up to 180°/s scaled by the Speed slider | ✅ | On the real arm 2026-11-17. |
| The 1:1 mode ("Hand → arm"): the gripper goes where your hand is | ✅ | On the real arm 2026-11-17: "way more intuitive", about 0.5 s behind, a little shaking. |
| The Speed slider and the right thumbstick (limited by the venue); the gripper and the wrist stay above the floor (1.1 cm above the table since 2026-11-18) | ✅ | |
| The 3D arm in the headset (a see-through ghost in AR), which you can move onto the real arm | ✅ | |
| The headset's status panel in the hub's design (2026-11-18): the state as a colored label, the gripper and the speed in the digit font, the hint | ✅ | Checked on the Mac over dark and light backgrounds. In the headset: lab check F.13. |
| **What the Quest sees, on another screen** (2026-11-18): a button in the hub's strip (brain's computer) opens scrcpy's window with the headset's picture (watch only). `lab-os quest-view --install` downloads scrcpy, `--remove` deletes it. | 🟡 | Download, start and stop tried on the Mac without a headset. On the Quest: lab check F.12. |
| Desktop control without a headset: the keyboard and trackpad act as a controller. **X** = STOP in every mode; **`** or Esc leaves desktop control. | ✅ | |
| Record and replay controller sessions (`--record`, `lab-os-teleop replay`) | ✅ | For tests without a headset. |
| The redesigned teleop and monitor pages (3D on the left, controls on the right, STOP in the bar) | ✅ | Old pages at `/classic/…`. |
| The arm freezes on release, lost tracking, a lost connection or old input; STOP on every page | ✅ | |
| **Teleop with a webcam** (preview, 2026-11-19, `/webcam`, `docs/guides/webcam-teleop.md`): your bare hand in front of a webcam drives the arm, no headset. The right wrist moves the gripper, a left pinch or Space is the clutch, a right pinch closes the gripper; X = STOP. The hand out of the picture freezes the arm until the clutch is let go. Relative only, the wrist doesn't turn, one arm. | 🧪 | The fake arm, with a recorded video of hands as the camera in headless Chrome (30 frames a second, the arm followed, the freeze held). Lab: check part W (2026-11-24). The Kinect isn't used yet (it needs drivers that need `sudo`). |
| **Two arms at once** (preview, 2026-11-19): `--left-arm so101-green` next to `--arm so101-white`; each controller drives its own arm (grip = clutch, trigger = gripper); A, X and STOP stop both; the headset, the teleop page and the monitor show both 3D arms and both states; hold Y and a grip to move that hand's 3D arm; relative and 1:1 on both arms | 🧪 | Two software arms, and the headset session in headless Chrome (both 3D arms moved, a 1:1 grab with the left hand). Controllers only. Lab: check part T (2026-11-24). |

## AI tools drive the arm (MCP)
http://127.0.0.1:8081/mcp · `docs/guides/ai-control.md`

| Feature | Status | Notes |
|---|---|---|
| Robot tools for an AI tool (Claude Code, Codex, …): `arm_status`, `list_poses`, `move_joints`, `gripper`, `move_to`, `go_to_pose`, `pick_at`, `stop` | ✅ | `so101-white` (the cube was picked and put down 2026-11-17). Claude Code runs every tool without asking; STOP and the brain's limits are the brake. |
| Safety in the tools: soft limits, at most 30° or 10 cm for each call, the floor, "can't reach" instead of a guess, "stopped short" with how far | ✅ | The brain writes every call to `logs/ai-tools/`. |
| Named poses: `ready` (the working pose) and `home` (folded, the builder's own pose, just above the rest; quick job 30) | ✅ | `home` on the fake arm only; two joints stop at their soft limits and the move says so. Lab check F.3. |
| **Heights from the table** (2026-11-18): an arm on a plate has its table height in `devices.yaml` (`so101-white`: −1.6 cm); every height the tools and teleop use is from the table | ✅ | Software arm only. Lab check F.2. |
| The limit for each call, the speed cap and the floor can each be switched off (the venue file, or Settings → Safety Limits and Shut Down); never on a public venue or a venue with `limits_locked: true` | ✅ | Tested on the fake arm. STOP, the soft limits and one controller at a time always stay. |
| `pose_view`: a picture of the arm's 3D model in its pose now, with the AI's marks | ✅ | Used in the cube pick (2026-11-12). Also at `/api/pose-view.png`. |
| `pick_at`: a full pick in one call, each step shown on AI Control before it moves; says "holding" or "missed" | ✅ | Software arm only. Lab check 3b.5. |
| Table map: the stand camera's pictures get a cm grid of the table, from a printed sheet (`lab-os table-map`); `table_point` changes a pixel into cm | ✅ | Tried only with a drawn sheet. Lab: checklist part 3b. |
| `camera_snapshot`: one real picture from a camera (socket 7 = wrist, 8 = stand, on both sets) | ✅ | Used in the cube pick. Without the table map, the stand camera's picture gives a direction, not a place. |
| **Tic-tac-toe** (preview, 2026-11-20, `docs/guides/tic-tac-toe.md`): an AI tool plays against a person with LEGO pieces on a printed grid. `camera_snapshot` with `board: true` draws the cells and the robot's start spots on the stand camera's picture and gives the positions and the steps; the arm keeps to a route off the board. Played with Claude Code. | 🧪 | A robot turn to each of the 9 cells on the fake arm, through the tools' checks; the board drawn on a test picture. Without a camera (the fake arm), the person says the moves. Lab: check part G (2026-11-24). |
| The AI Control page (`/ai`): the arm from the side, every AI tool call live, STOP | ✅ | |
| Project tools for developers' AI tools: `project_status`, `read_doc`, `search_docs`, `git_log`, `list_devices`, `lab_status`, … | ✅ | |

## Robots and drivers
| Robot | Status | Notes |
|---|---|---|
| `so101-white` (SO-101 arm, LeRobot) | ✅ | The driver, a guarded motor setup and calibration, a read-only `--watch` mode. `uv sync --extra so101`. |
| `so101-green` (the training set's follower, borrowed) | ✅ | `--arm so101-green`. It drives with lab-os's copy of the training calibration and refuses if the copy or the motors are different; motor setup refused; refused while LeLab has the port (`AGENTS.md` → "Hard rules"). Lab checks parts 8 and 8b passed (2026-11-16, 11-17). |
| The green set's cameras (`so101-green-cam-wrist`, socket 7; `so101-green-cam-stand`, socket 8) | 🧪 | Listed by USB socket. A camera that another program uses is refused. |
| `xarm1` (Hiwonder xArm 1S, USB) | ✅ | The driver, joint movement, inverse kinematics, hand calibration of the limits. `--arm xarm1`. |
| **The brain finds the arm** (2026-11-20): `lab-os serve` (and the "Start lab-os" icon) with no `--arm` drives the SO-101 that is plugged in, or two as both hands. Never the green set unless named. No arm plugged in, or one that cannot open: the fake arm, and the terminal says why. `--arm` still names an arm. | ✅ | Tests with faked ports; on the lab desktop it found `so101-white`. Lab check part A. |
| **An SO-101 unplugged and plugged in again** (2026-11-18): in about half a second the brain freezes it, ends any AI move, and every page says that the arm is disconnected. When the same USB name comes back, the brain connects again by itself. Grab again to drive. | ✅ | Software arm and a test port only. Lab checks F.4 and F.5. The xArm does not notice yet. |
| The fake arm (`fake-arm`) | ✅ | Every feature runs on it first; no hardware needed. |
| 3D models: the SO-101 (from its URDF) and the xArm 1S (from Hiwonder's drawing) | ✅ | In the repository; they work offline. |

## Running it anywhere
| Feature | Status | Notes |
|---|---|---|
| Places: run at home or in another lab with its own config folder (`--config`, `lab-os new-place`) | ✅ | `docs/dev/places.md` |
| Venues (lab, visit-day) set the speed limits, the persona and what the hub hides | ✅ | `config/venues/`. visit-day is the venue for visitor mode. |
| Works offline: every web library and font is in the repository | ✅ | |
| A one-line install on a new Linux computer (`scripts/install.sh`) | ✅ | |
| Tests and lint once for each push to `main` or to a pull request (GitHub Actions), in parallel, no hardware needed | ✅ | |
| Colours in the terminal: each log line starts with the time, warnings are amber and errors red. There is no colour in a pipe or a log file, or when `NO_COLOR` is set. | ✅ | Tested without hardware and in a pseudo-terminal on macOS. Lab: check F.16. |

## Training launcher (so101-green)
| Feature | Status | Notes |
|---|---|---|
| `lab-os green` (desktop icon, the hub's Training page): checks the green arms' ports, then starts LeLab. **Stop LeLab** (or `--stop`) stops only the LeLab that it started. | ✅ | Tried in the lab 2026-11-16 and 11-17; it refuses while another program (for example the brain driving `so101-green`) has a green port. `docs/guides/green-launcher.md` |

---

## Lab projects not connected to lab-os (yet)
Separate projects with the lab's robots. They do not run through the brain, and their code is not in this repository.

### xArm control with the Hiwonder Bluetooth glove
- **What:** the Hiwonder glove (5 finger sensors, a motion sensor, Bluetooth) connects directly to `xarm1` and drives it. Tilt the hand to turn the wrist. The number of bent fingers selects the motor that moves.
- **Status:** ✅ works with Hiwonder's own firmware (tested 2026-10-23). Little delay; tilting to turn works well.
- **Problems:** it needs large gestures; the arm jumps when it changes motors (absolute tilt → angle); selecting motors by counting fingers is difficult. These lessons shaped lab-os teleop (clutch, relative control, gentle ramps, calibration for each user). Notes: `docs/plan/lab-jarvis-log.md` → "Hiwonder glove findings".
- **To connect it later:** `docs/plan/ideas.md` → "Fix the Hiwonder glove".

### Raspbot voice control
- **What:** on a Yahboom Raspbot v2, press a button on the IR remote and speak. After 3 seconds it changes the speech to text. If it hears a known word (forward, backward, left, right), it moves a little in that direction.
- **Status:** ✅ worked (the builder's project, before lab-os). Where its code is: not written down yet.
- **Notes:** `docs/plan/lab-jarvis-log.md` → "Facts about the lab". The IR-remote trigger is in `docs/plan/ideas.md` → "Voice beyond push-to-talk".

### xArm camera demos (`xarm_1s_demo`, June 2026)
- **What:** Python scripts that drive the xArm 1S from a webcam: follow a green ball with the base (`arm_follow_ball.py`), follow it in 2D with the base and the reach (`arm_2d_follow.py`), and grab an object at a point in the picture after a 3-point camera-to-servo calibration (`test_safe_grab_v2.py`).
- **Status:** a separate folder on the builder's Mac, not in a git repository here. lab-os's default xArm limits come from its grab script.
- **To connect it later:** `docs/plan/ideas.md` → "Ways to teach a robot" (look, then reach).
