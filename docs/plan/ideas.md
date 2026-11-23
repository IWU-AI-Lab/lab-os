# Ideas backlog

**The single source of truth for ideas.** New ideas land here, **not in code** and not in other docs, unless they're part of the current focus (`docs/plan/current-focus.md`). This keeps the project finishable and nothing gets lost. When an idea becomes the focus, move it into `docs/plan/current-focus.md` and delete it here. When an idea is decided (but not yet scheduled), record the decision in `docs/plan/lab-jarvis-log.md` and keep or delete the entry here.

**The long-term direction** (a real JARVIS, the lab unplugging it cleanly after May 2027) is in `docs/plan/vision.md`; concrete pieces of it come here as ideas.

Each idea: what it is · why · where it plugs in (slot/module, if known; slots are in `docs/plan/lab-jarvis-log.md` → "Architecture sketch"). "—" = not recorded yet.

**Not here because they're already decided plans:** the teleop second act (Gemini Robotics-ER "look, then reach" → SmolVLA → bigger VLAs via rented GPU; options table in `docs/archive/focus-2026-10-teleop-demo.md`) and teleop as data collection for the training project. Also offline lite mode, the portable demo kit, and the staged remote-access plan (`docs/plan/lab-jarvis-log.md` → "Mobility, portability & remote access").

---

## On hold: decided, will be built (2026-10-30)
Not ideas any more: agreed features, paused when the teleop focus closed (the demo is showable, "needs polishing"; tag `demo-2026-10-30`). Pick them up from here; the teleop focus's full context is in `docs/archive/focus-2026-10-teleop-demo.md` (step numbers below refer to it).

### Teleop demo: what's left
- **Hand tracking (step 6)**, the original goal: a visitor's bare hand drives the arm (pinch = gripper, open hand = release). Same pipeline as the controllers; per-user calibration with comfortable thresholds + hysteresis (the glove lessons). **First version built and tried 2026-11-10:** right wrist = the controller, left pinch = clutch, right pinch = gripper (fixed thresholds: 6 cm apart = 0, 1.5 cm = 1; `docs/guides/quest-setup.md`). It works but is hard to steer (builder). Left: tune it from recordings, per-user thresholds, and a one-handed clutch if two hands feel clumsy.
- **Speed and feel (step 7).** Builder, 2026-10-30, SO-101 + Quest at `--speed 0.2` (24 °/s per joint): "much more intuitive if it was much faster". Raise `--speed` step by step to the lab venue's 0.5 (60 °/s); then smoothing, end-to-end delay. (The hand-to-gripper scale: the 1:1 mode, built 2026-11-11, `docs/guides/quest-setup.md` → "1:1 mode".) Above 0.5 is the builder's call (`config/venues/lab.yaml`).
- **Quest display (step 5).** Visitor hint until the first grab; joints that turn red near their limits (= the workspace warning) on the 3D arm, which can now be moved onto the real one (2026-11-10; the lazy-follow HUD mini-arm of decision 2026-10-28 is the other option); the status panel lazy-follows.
- **Visitor polish + portability test (step 8).** Script, casting to a monitor, one run from the laptop away from the lab, tag, 60-second clip. The SO-101 port check uses Linux paths (`/dev/serial/by-id/`, sysfs): a Windows/macOS field laptop needs the USB-ID lookup `xarm1` already uses.
- **`so101-white-leader`.** Build and set it up (spare board `5B41532183`; `python -m lab_os.robots.so101_setup setup-motors --arm so101-white-leader` after its port is in `config/devices.yaml`). For recording training demonstrations (second act B), not needed for the visitor demo.
- **xarm1 leftovers.** Hand-measured limits (`python -m lab_os.robots.xarm calibrate`), Keys at `--speed 0.4`, a precise delay measurement, hold-position on stop, Mouse mode tried in a browser. Its HACK stays listed in `docs/plan/current-focus.md`.
- **A real-Quest recording as a test fixture** (`serve --record`, commit a short clip).
- **Check:** in the XR emulator, Shift+WASD moving the arm while the clutch is *released* would be a bug.

### Isaac Teleop as an input to the brain (decided 2026-11-16, after the demo)
- **What:** LeRobot's Isaac Teleop example (`examples/isaac_teleop_to_so101/`, Hugging Face + NVIDIA) reads the Quest through NVIDIA CloudXR. A thin layer runs its controller reader (`XRController.get_action()`: hand position and rotation, grip, trigger) inside the brain as another input source, converts it to our controller message and feeds our teleop loop, so our clutch, IK, floor, speed limits, STOP, dead-man and one-controller rule all stay. Optional second step: their Placo IK (soft full-orientation tracking) as a mapping option behind a switch. Their `teleoperate.py` alone (no recording) is the quick way to feel their mapping first.
- **Why:** the comparison (`docs/dev/existing-work-teleop-ai.md`, 2026-11-16): theirs is the best-engineered and maintained by HF + NVIDIA; ours keeps the brain's safety and pages.
- **Watch out:** CloudXR runtime + EULA; `isaacteleop` is Linux only and needs a newer LeRobot than our pinned 0.6.1 (all in our `so101` extra, never the lerobot conda env); always `HF_LEROBOT_HOME` set to a lab-os folder (it writes into LeRobot's cache: GOTCHAS 2026-11-16); `so101-white` only at first. In the headset you probably see CloudXR's view, not our Quest hub or 3D arm (unconfirmed). Recording training data through the brain is a separate piece ("Our own recording and training page").
- **Plugs into:** teleop inputs (`teleop/loop.py`, `InputState`), the SO-101 kinematics, the `so101` extra.
- **Cost:** about one session (faked first with recorded readings) + a lab day for CloudXR.

### Core plumbing (waits for the lab router)
From the first draft of the core focus (2026-10-30); the builder chose the hub first. Build when the router is here (Milestone 1):
- **Map what exists** → `docs/architecture.md`: the `Arm` protocol + drivers (fake, xArm, SO-101), device registry with off-limits devices, venue profiles, the WebSocket server with control handover + STOP, `docs/dev/protocol.md`, the theme file; which slot each belongs to, what's still teleop-specific.
- **Plug-in description:** name, slot, requirements (Python extra, OS, device in `devices.yaml`) and a read-only `check()` returning a short health report. Robot slot first.
- **Roll call:** `lab-os roll-call` and in the hub: plugged in? requirements met? off limits? A table + a report file (seed of the troubleshooting suite). Missing robots are normal (decision 2026-10-28). **Read-only**: never moves anything, never opens an off-limits port or camera. Include the checks we already know (Quest plugged in, xArm answers); microphone, network, accounts later.
- **Inputs as plug-ins:** Quest page, desktop control, replay picked in the page instead of command-line flags.
- **Robots report in:** a stand-in "network robot" over a WebSocket on `localhost` first, then real ones over the router. **`xarm1` is the second robot through the core.**
  - **Why it matters now (the builder, 2026-11-12):** the brain desktop's USB is full (6 rear USB-A + 1 front: keyboard and mouse, the 2 green cameras, the 2 green arms, the xArm in the front one; the Quest on USB-C), so the white arm and its cameras can only go in by unplugging the greens. Arms (white, green or xArm) could hang off a Pi, a Jetson, an unused ThinkCentre or the other desktop, with a small lab-os "robot node" running there (deployed by rsync, robots stay thin) and driven from the brain or any screen. Someone reportedly had trouble with arms on a Jetson (to check: the USB-serial driver for the arms' CH340 chips on the Jetson's kernel). The green arms only through the training launcher's rules.

### Troubleshooting suite
Was "Up next" after teleop (decision 2026-10-24); the builder chose the core first (2026-10-30). Its roll call / health checks start in the core focus; the rest waits here: microphone (level meter, noise, record + play back), cameras (live view, "is it sending images?"), robots (live joints; a test wiggle only with the builder's OK), network (reachable? delay?), accounts (API keys present and working, credits), Quest connected. Each check writes a **report file** humans and agents can read. *Why:* the roll call will find problems, and the builder, a future maintainer or an AI agent need an easy way to diagnose them.

---

## Recent ideas (2026-11-21)

### Voice: an existing framework instead of our own pipeline?
- **What:** our voice is our own pipeline (the browser's microphone and wake word → `gpt-4o-mini-transcribe` → `gpt-6-luna` → `gpt-4o-mini-tts`), and each fix finds the next small problem (lab check L, 2026-11-21). Compare maintained voice-agent frameworks and live speech-to-speech models (for example Pipecat, LiveKit Agents, OpenAI's and Google's live models) with keeping ours. A separate research session, not Claude (the builder, 2026-11-21).
- **Why:** interruptions, one steady voice and a shorter wait (now about 4 s) come built in with a live model; developing it piece by piece is cumbersome (the builder).
- **Watch out:** many screens in one room, each a browser with its own microphone and speaker; the nearest one answers (quick job 70); wake word in the browser; push-to-talk, dictation and conversation mode; the persona's voice; the AI spend count; works with the free Gemini key as a fallback; an offline mode later. A switch 10 days before the demo is a risk: decide after the research, probably after the demo.

### A wake word for the Lab Assistant
- **What:** the Lab Assistant persona uses "hey Jarvis" (`wake_word: hey_jarvis` in `config/personas/lab-assistant.yaml`), because openWakeWord has a ready model only for a few phrases. Its own name needs its own model: openWakeWord can train one from synthetic speech (about an hour on a free Colab GPU). Waits for the builder: the name to train.
- **Why:** the builder, 2026-11-21: with the Lab Assistant, the startup shouldn't say "hey Jarvis".

### Faster AI arm control (fewer, bigger model calls)
- **What:** the AI's arm moves are slow because each small move is one round trip to a frontier model. **Chosen first step (2026-11-21): quick job 81, "Code as Policies"** ([project](https://code-as-policies.github.io/)): the model writes one short program over the brain's own tools, and the brain runs it with no model call between steps. Picked from the builder's search (Gemini and ChatGPT, 2026-11-21) because it needs no training, no GPU and no new hardware.
- **Later steps, still ideas:**
  - **Prompt caching** for the hub's assistant: a shorter wait before the first word ([CSR](https://arxiv.org/abs/2605.07325)).
  - **Asynchronous action chunks with a small trained policy** (LeRobot's async inference with SmolVLA; reported on SO-100/SO-101: about 30 % faster tasks): the frontier model plans, the policy moves. Needs recorded demonstrations and training, so it goes with "Our own recording and training page" below, after the demo.
  - Not for us now: VLASH, FlashVLA, Reflex, VOTE, LiteVLA-Edge, AsyncVLA, LAGO, Chef Robotics' delay compensation (each needs a trained VLA and a fast GPU or an edge GPU); ReKep (needs a depth camera); ROSGPT and the LLM–ROS2 papers (lab-os uses no ROS).
- **Why:** smoother, faster arm control from the AI (the builder, 2026-11-21).
- **Plugs into:** the robot tools (`lab_os.tools`), the hub's assistant.

## Recent ideas (2026-11-20)

### For the builder's design review
The builder plans one design review pass. Collected for it: the card that opens when you tap a device in the Devices panel (too much text in one paragraph, and it appears with no animation, unlike the rest); the Quest's pages from the main page (the VR and AR page looks bare and unplanned; maybe a 3D model of the Quest); wording on every page. Teleop's words are quick job 66. **"Bring it back"** (lab check 11.10): it is really opening and closing a page on another device from a distance. Either move it to the page it is for and give it a better name, or let a page be open on only one device at a time (the builder: only if that is not annoying).

## Recent ideas (2026-11-19)

### Room sound and the Newline's picture at once
The classroom's Extron panel sends its Laptop and Wall Plate HDMI inputs to the ceiling speakers (tried 2026-11-19), and to the projector. To have the picture on the Newline and the sound in the ceiling: a second video output from the computer that drives the Newline, by cable to the Wall Plate or Laptop input, and Ubuntu's Sound → Output set to it. The lab desktop has only one HDMI port: a DisplayPort-to-HDMI cable (if it has DisplayPort), or a Pi, which has two HDMI outputs. The projector can stay off (Display Off), if the panel still plays sound then: to check. Not needed for the demo: the Newline's own speakers are loud enough.

### A flat picture of what the Quest sees
Quest view (quick job 36) shows the headset's own picture, which looks like a fisheye lens. Meta's casting gives a flat picture, but needs Wi-Fi with internet and a Meta account (the travel router could give the Wi-Fi). Correcting scrcpy's picture ourselves is the other way.

### The cm grid with lens correction
The stand camera's cm grid is a flat fit (worst 1.3 mm on the sheet, 2026-11-19), with no correction for the lens. Far from the sheet, the error grows. The same printed sheet, photographed at a few angles, gives the lens correction (OpenCV's ChArUco calibration).

### Point and "move there" in the headset
In the Quest, with the 3D arm lined up on the real one, point at a spot on the table and say or press "move there"; the gripper goes there. No AI. The first piece of "put that there". It was a demo preview from 2026-11-16 to 2026-11-19; the builder moved it here to make room for Tuesday's three previews (`docs/plan/current-focus.md`).

### Hand gestures for the hub
Hand signs seen by a webcam or the Kinect do hub things: move a window to another screen, open a page, go back. Later than the webcam teleop preview, and on the same hand tracking. **Watch out:** a gesture must not fire by accident while someone talks with their hands; one clear "start" sign first. The older "Kinect gestures" line under "Triggers & sign-in" below is the same idea.

### One AI budget for every brain
Each brain counts its own AI spend today (the laptop's and the lab desktop's), although both use the professor's OpenAI key, so the budget on one brain doesn't see what the other spent. One budget for the key would count both. Ways: the real cost from OpenAI (it counts every brain on the key; it needs an Admin key that only an Organization Owner can make, quick job 41, 2026-11-19: `docs/guides/hub.md` → "AI Spend"), OpenAI's own monthly limit on the key's project (set by the professor in OpenAI's dashboard), or the brains share their spend logs.

## Recent ideas (2026-11-18)

### Start the hub with a card
**The first step is built** (quick job 79, 2026-11-20): a swipe on the designed hub's start screen starts the hub, with its own animation and sound. Later steps, still ideas:
- **Greet the person by name.** It needs a way to register people (for example: ⚙ → Add a card → swipe → type the name). To think through first.
- **Authorization:** some actions only after a listed card (for example, a real arm or the settings).
- **Activating things:** a card swipe starts a mode or a device.
- **The Newline's NFC tap reader** (used for its Android profiles) as a second reader, if it can be reused.

The lab's USB card reader types the card's data like a keyboard (a student ID gives a string of numbers; a bank card gives its usual data). **Privacy:** only cards listed in config may do more than start the hub; store a hash of the number, never the number; ignore and never log anything else (bank cards above all).

### Gemini 4 Hydrogen and Google's Antigravity robotics plugin (probably not)
Google's robotics model (Nov 2026, `gemini-4-hydrogen`, replaces Gemini Robotics ER 2) and an Antigravity plugin that brings up an SO-101, simulates in MuJoCo and runs tasks from chat (demos: sorting, packing, chess in simulation). Needs a paid Google AI plan the builder doesn't have; the plugin drives the arm with its own code, outside lab-os's STOP and limits, and calibrates arms (forbidden on the green ones). Probably not: the models will have changed by the time it matters. If ever: Hydrogen as one more model behind the brain's own tools.

### A photo as a 3D scene in the headset
Turn a photo into a 3D Gaussian-splat scene to step into in the Quest (someone did this with Apple's ml-sharp: one photo → a `.ply` in under a second on a GPU). Apple's weights are for research use only. Needs a splat viewer vendored for the Quest page (offline rule).

## Recent ideas (2026-11-13)

### The hub's own chat moving the arm
- **A first version is a preview for the 2026-12-03 demo** (2026-11-19): "Jarvis, hand me the cube" (`docs/plan/current-focus.md` → "Until the demo", preview 4). **Built 2026-11-20:** a named pose, the cube's hand-over and "let go", off unless ⚙ → Robots → The Assistant May Move the Arm, never on a public venue, the brain's own computer only (`docs/guides/hub.md`). Still an idea: other moves ("pick up the cube" and put it somewhere).
- **What:** someone asks the hub's assistant (typed or by voice) to move the arm ("wave", "pick up the cube"), not only a developer's AI tool (the builder, 2026-11-13).
- **Watch out:** today the hub's chat stays in the read tier because anyone in the room can talk to it (current focus, "A public screen"). Needs: which venues allow it (never `public: true`), one controller at a time, STOP on every screen, and probably a person nearby.
- **Plugs into:** the move tools (same safety layer), voice, the persona.

## Recent ideas (2026-11-12)

### AI picking: height, sag and camera placement
- **What:** fixes suggested by the missed cube pick (`docs/dev/GOTCHAS.md`, 2026-11-12):
  1. **Check the height zero:** put the jaw tips on the table by hand (torque off), read `arm_status`, and correct the gripper-point offset or the model if z isn't ~0.
  2. **Allow for the elbow sag:** add the steady ~3° to the elbow command, or have `move_to` send a small second correction after a short stop. (Quick job 77, 2026-11-20, raised the margin for each joint to 4° instead, so poses say "arrived"; `move_to` still warns about the ~1.5 cm the sag costs, so the correction is still open.) Then `stopped_short` only fires for real misses (e.g. above 1° or 0.5 cm), so the warning means something again.
  3. **Decided 2026-11-16 as the stand camera's cm grid** (`docs/plan/current-focus.md` item 6; a printed calibration sheet instead of an AprilTag). Was: **Place the stand camera:** a printed square marker (AprilTag) at a known spot in front of the arm lets `cam-stand` turn a pixel into table cm, so the AI's first guess is close and the wrist camera only fine-tunes.
  4. **Say before moving:** move tools take a short `plan` sentence that the hub shows (and the voice says) before the arm moves, so people can follow along and the AI can't skip saying it.
- **Why:** the 2026-12-03 demo has the AI picking things up while people watch. This time it took 10 small moves to get beside the cube, then closed above it.
- **Watch out:** 1 needs the white arm's torque off and hands on the arm (ask first). Never on the green arms (their calibration is read-only).
- **Plugs into:** `tools/robot.py`, the SO-101 model, the cameras, the hub's AI view.

### Our own recording and training page (instead of LeLab)
- **What:** a lab-os page for recording demonstrations and starting training runs on the SO-101s: all cameras shown at once, episodes listed, start/stop recording, a training run's progress, through LeRobot (the `so101` extra) without its separate web app.
- **Why:** LeLab was a quick look (the builder, 2026-11-12): it seems hastily built and shows only one camera. **2026-11-13:** it doesn't pick up the cameras reliably, and its teleoperation page can't show both camera views. The builder wants that fixed, **only when the builder says so** (fix LeLab or build this page). A "Stop LeLab" button is a quick job (`docs/plan/quick-jobs.md`).
- **Watch out:** recording uses the same ports and cameras as lab-os's own control (one program per port); training uses the shared GPU; never touches the `lerobot` conda env.
- **Plugs into:** a hub module, the robot slot, the green launcher (could replace it).

### Two arms at once
- **A first version is a preview for the 2026-12-03 demo** (`docs/plan/current-focus.md` → "Until the demo"). Built 2026-11-19 (`docs/guides/quest-setup.md` → "Two arms at once"): Quest controllers only, relative and 1:1 on both arms, both 3D arms in the headset (each moved with Y and its grip), on the teleop page and the monitor; the AI tools and desktop control drive only the right arm. What's below beyond that is still an idea.
- **What:** drive two arms at the same time: in the Quest, the left controller (or hand) drives one arm and the right the other; on the desktop, perhaps one arm on the keyboard and one on the mouse, or a quick switch between them. Two-handed tasks become possible (pass a block from one arm to the other).
- **Which arms:** both SO-101 followers (`so101-white` + `so101-green`, the builder's choice 2026-11-12, once step 11 makes the greens drivable); xArms also possible.
- **Watch out:** today each hand has a job (left pinch = clutch for the right hand, right pinch = gripper), so two-arm control needs its own controls; the 3D scene shows both arms; the brain desktop's USB sockets are full (an arm on another computer: "Robots report in" above); STOP stops both.
- **Plugs into:** teleop (one session, two arms), the Quest scene, the robot slot.
- **Merged here (2026-11-13):** the earlier "one hand controls two robots" (a pitch moment: "one hand, two robots"), "two-hand control" and "two-robot handoff".

## Recent ideas (2026-11-11)

### Demo away from the lab with the brain still in the lab (Tailscale)
- **What:** the brain keeps running on a lab desktop (on the lab network), and the demo happens somewhere else with the travel router. The demo devices (screens, the Quest, a Raspbot) join the travel router, which gets its internet from a phone hotspot (or, less likely, the university Wi-Fi there). **Tailscale** (a free private network across the internet; "remote level 2" in the log) links the two places, so the demo devices open the brain as if it were in the same room. Nothing is opened on the campus network: both ends connect outward.
- **How, likely:** Tailscale on the desktop (an app; installing it needs `sudo`) and on the travel router (the Beryl 7 has it built in). The router lets its own devices through (a "subnet route"), so the Newline and the Quest don't need Tailscale themselves. To check: that the router's devices can reach the desktop this way (GL.iNet's settings mostly describe the other direction); if not, the Tailscale app on the screens that can run it (phones, laptops, Pis, Android screens).
- **The alternative:** move the brain instead: a laptop as the field brain (the portability plan), or carry the desktop along (the builder would rather not).
- **Bonus to check:** Tailscale can give the desktop a real certificate for its Tailscale name (`tailscale cert`, e.g. `https://<desktop>.<tailnet>.ts.net`), so pages would be secure (voice, Wake Lock) without the `hub.indwesailab.com` setup. Probably only on devices that run Tailscale themselves (the name is looked up through Tailscale).
- **Watch out:**
  - The arms plug into the brain by USB, so with the brain in the lab the arms stay there too: the demo shows a lab arm driven from far away (it needs a camera so people see it move), or a laptop brain comes along for the arm.
  - Delay: everything goes over the phone's internet (usually ~30–100 ms more, more when Tailscale has to relay). Fine for the hub and chat; teleop will feel it.
  - Phone data: cameras and video use a lot of it.
  - Rules: it's a tunnel out of the campus network, so **ask the professor / IT first** (like the router). Account: the builder's own for now; a separate lab-admin account can be made (the builder). The free plan's user and device limits may matter.
- **Tried (the builder, before 2026-11-11):** Tailscale already runs on the other Ubuntu desktop, some of the Windows desktops and the builder's laptop, so it works on the campus network.
- **Plugs into:** places and venues (a venue whose brain is far away), the travel router.

## Recent ideas (2026-11-10)

### A very light "wow" look for slow screens
- **What:** a version of the designed hub made for weak screens (the Newline, Pi screens, phones, the portable kit): the same colors, fonts, frame and core, but effects that cost little to draw (few moving dots, no blur, short glows, the startup as a simple line animation instead of 3000 stars), so it stays smooth where `reduced` still lags.
- **Why:** the Newline lagged even at `reduced` (2026-11-10). Measured 2026-11-13 (focus step 12): its own Chrome manages `/perf` at 44–59 fps but the startup still lags; this is the next step if a lighter startup isn't enough.
- **Watch out:** it's a design change: settle it in a design session (`DESIGN.md`, the concept, the theme together), probably as a quality level below `minimal`'s look but with its own small animations.
- **Plugs into:** quality levels (theme), "This device" settings.

### Teleop with a webcam instead of the Quest
- **A first version is a preview for the 2026-12-03 demo** (`docs/plan/current-focus.md` → "Until the demo", 2026-11-19). **Built 2026-11-19 with the webcam** (`docs/guides/webcam-teleop.md`): MediaPipe's hand landmarker in the browser (vendored), the same `xr_input` as the Quest's bare hands, relative only.
- **Left after the preview:** the wrist's turn from the hand (MediaPipe's world landmarks give the palm's direction); 1:1 (the page would need to know where the camera is relative to the arm); a one-handed clutch; per-user pinch thresholds.
- **The Kinect** (model 1414, the first Kinect for the Xbox 360): not a webcam, so Chrome can't see it. It needs libfreenect (on Ubuntu `sudo apt install freenect` and its udev rules, so `sudo`), its own power and USB adapter, and a small bridge on the brain that sends its depth to the page (or finds the hand there). Its depth would make toward/away exact. Lab check K says whether the lab has the adapter.
- **What:** drive the arm with your bare hand in front of an ordinary webcam: no headset. The page (or the brain) finds the hand's joints in each camera image and sends them through the same path as the Quest's hands: wrist = where the gripper goes, a pinch = the clutch or the gripper.
- **Why:** anyone can try it at a desk; no Quest to charge, set up or put on; a fallback when the Quest is out.
- **How (as built):** Google's MediaPipe hand landmarker (Apache-2.0) runs in the browser, offline, on the webcam, producing the same `xr_input` hand messages (`source: "webcam"`).
- **Watch out:** one webcam sees left/right/up/down well but **depth (toward/away) only roughly** (from the hand's size in the picture), so forward/back will feel worse than the Quest; a second camera from the side, or the Kinect's depth camera, could fix that. Not the arms' cameras (they look at the table, and one program per camera): use the lab's spare webcam or a laptop's. Same dead-man rule: hand out of view = freeze. The browser gives the camera only to a secure page, so the webcam page runs on the brain's own computer (`localhost`) until the secure address exists.
- **Plugs into:** inputs slot (a new input page, same clutch mapping); cameras/vision.

### Past conversations (more than "bring back the last one")
- **What:** a list of recent conversations on the hub (or per person, once the hub knows who's there), to reopen one and continue: e.g. a drafted prompt from yesterday, or picking up after lunch.
- **Built so far (2026-11-10, quick version):** the last conversation is kept for `chat_keep_minutes` and can be brought back after an accidental reset or a restart (`docs/dev/chat.md` → "Kept for a while").
- **Watch out:** a public screen; anyone can tap. Past conversations probably need a private screen (venue not `public`) or a sign-in, and a clear way to delete them.
- **Plugs into:** the conversation manager (`lab_os.ai.history`), the hub's History page.

## Recent ideas (2026-11-09)

### lab-os at home, or in someone else's place
- **What:** the builder runs lab-os at home with their own devices and screens; other people could do the same with theirs.
- **In the focus already:** rule 9 (nothing place-specific in code; another place = another config folder outside the repo, `--config`) and one brain per network (step 8).
- **Later:** a short "set up your own place" guide (copy the example config, name your devices, your own `.env` keys, an optional domain or just `localhost`); example configs for a home (one screen, a fake arm or one robot) and a lab.
- **Watch out:** the lab's hard rules (the green arm) stay in the lab's config, and the lab's domain name is updated only by the lab's brain.
- **Plugs into:** config/venues; the brain program; docs.

### Sending more than a module to another screen
- **Opening a module on another screen is in the focus** (`docs/plan/current-focus.md` step 8).
- **What stays here:** sending other things to a screen: a chat answer, a picture from a camera, the other project's poster; and later the Quest as a target.
- **Plugs into:** outputs/clients; the screens list from step 8; casting in `docs/plan/use-cases.md` (the visit, another project borrows a screen).

### Screens without browser bars ("kiosk clients")
- **What:** any lab screen (32" monitor, Pi touchscreens, the Newline) shows the hub, or any other web app, full screen, with no tabs or address bar, and starts by itself.
- **How, simplest first:**
  1. **Full screen from the page itself:** the hub's ignition press switches to full screen (in the current focus). Works in any browser, Newline's included, but Esc or a reload leaves it.
  2. **Kiosk mode:** Chrome/Chromium/Edge started with `--kiosk <address>` show only the page, start at boot, and can't be left by accident. The standard setup for Raspberry Pi screens; works on the lab desktops (Linux, Windows).
  3. **Install as an app:** the hub can declare itself an installable web app ("PWA"); Chrome/Edge/Android then offer "Install", and it opens in its own window without browser bars. Needs `localhost` or HTTPS (the certificate question again for other screens).
- **The Newline (TT-7523QCA+, a Q+ Pro: Android 15 with the Google Play Store).** Its Chrome has **no full-screen button** (builder, 2026-11-09). Options, quickest first:
  0. **The lab-os hub does this itself** (the plain hub's tap 1, the designed hub's one tap). The same trick suits other projects.
  1. **The page asks for full screen itself:** a "tap to start" layer that calls `document.documentElement.requestFullscreen()` on the first tap (Android Chrome allows it after a tap; works over plain `http` too). Needs a small change to that project's page; a reload or the Back gesture leaves full screen, so the tap layer comes back.
  2. **Install the page as an app (PWA)** with a web app manifest saying `"display": "fullscreen"`: Chrome's menu → "Install app" / "Add to home screen", then it opens from its icon with no bars. Needs HTTPS (for the lab-os hub: `hub.indwesailab.com`, deferred 2026-11-10, focus step 7; a plain `http://` LAN address won't install; workaround: `chrome://flags` → "Insecure origins treated as secure", if the Newline allows flags) and Chrome's install rules (a manifest with name + icons; older Chrome versions also want a small service worker).
  3. **A kiosk browser app from the Play Store** (e.g. Fully Kiosk Browser: full screen, starts at boot, locks to one address; check its license terms): no change to the page. Only if the Newline lets us install apps.
  4. **A small computer on its HDMI + USB touch** (spare Pi 5 or ThinkCentre) with Chromium `--kiosk` (2 above): always works, same recipe as the Pi screens; the long-term choice for the hub.
  - Test 1 and 2 today on any **Android phone** with Chrome (it behaves like the Newline's); try 3 at the Newline.
- **Newline Signage Pro** (corrected 2026-11-09): installed on the Newline but needs registering; Newline names only the Q Pro and STV+ as "fully integrated", and resellers sell a license (~$99 per display per year; a free year comes with Newline's media-player box), so maybe not free. Its listed content is images, videos, text, weather, QR codes and live feeds: **no mention of web pages or touch**. The builder checks at the lab: does registering ask for a license, can it show a URL full screen, does touch work. Good for watch-only screens if so; the interactive hub uses 1–4.
- **For other projects too:** a written "kiosk screen" recipe (any address, full screen, starts at boot) helps every lab project. Later the hub could choose what each screen shows (focus step 8; "Sending more than a module to another screen" above).
- **Plugs into:** outputs/clients; the touchscreens idea; `docs/` recipe (like `docs/guides/network-setup-checklist.md`).

## Recent ideas (2026-11-08)
"Device card", "hive" and "locked" are the hub's devices panel as defined in `docs/design/DESIGN.md`.

### GPU-busy indicator on the hub
- **What:** the hub shows when the shared GPU is in use, and by what (e.g. "GPU: training (SmolVLA) · 10.8 of 12 GB"), so nobody starts a local model during a recording or training run.
- **Why:** the lab desktop's GPU is shared with the SO-101 training (`docs/dev/chat.md` already warns about it); a visible sign beats remembering.
- **How (read-only):** `nvidia-smi` lists GPU memory use and which programs use it (Linux and Windows). Later, the model router can refuse or warn before starting a local model while the GPU is busy.
- **Plugs into:** status strip or the desktop's device card; model router (local setups).

### Teleop delay graph
- **What:** a small live graph of the Quest-to-arm delay over the last minute, in the teleop module (and the monitor page).
- **Why:** shows whether lag comes from the network, the brain or the arm; makes speed tuning measurable ("feel" is on hold: "On hold" → "Speed and feel" above).
- **Watch out:** the Quest and the brain have different clocks, so measure with a round trip (the brain echoes a timestamp back) rather than comparing clocks. "Reached the arm" can mean *command sent* (easy) or *arm got there* (needs position read-back; slower, arm-specific). Start with command sent; label which one the graph shows.
- **Plugs into:** teleop module + monitor; the troubleshooting suite (network delay).

### Battery and diagnostics in the device cards
- **What:** each device card shows what that device can actually report: battery, temperatures, voltage, servo load, signal strength, under-voltage warnings. Nothing shown that the device can't measure (no fake "100%").
- **Why:** low batteries and hot servos are the usual silent failures.
- **Source list:** "Hidden sensor data the hardware already has" (below) says what each device offers.
- **Plugs into:** each device plug-in declares its readings; the device card shows them; the troubleshooting suite logs them.

### Projects module
- **What:** an expandable list of the lab's active and past projects: name, people, devices it uses, status (active / paused / done), maybe a link to its repo or docs.
- **Why:** shows what the lab is doing; explains to visitors and the next student why a device is "locked" (e.g. the green SO-101 + training cameras while a training run uses them).
- **Idea for later:** devices get locked *by* a project entry (`config/projects.yaml`) instead of a separate flag.
- **Plugs into:** a hub module (button); the device card ("Used by: SO-101 training"). Different from the hub's "Current Project" panel, which shows lab-os's own focus.
- **Open questions:** who edits the list (a config file, or a form in the hub)? People's names are fine internally, but check before showing it to visitors.

### "Find me" button
- **What:** in a device's card (tap it in the hive), "Find me" makes the real device show itself, depending on what it can do: a Pi blinks its LED, a Raspbot beeps, a Pi with a touchscreen shows its sticker number big on screen, the Quest plays a sound.
- **Why:** with ~10 identical Pis, finding "Pi 7" on the shelf is a real chore.
- **Rules:** each device declares which "find me" actions it supports; robot **motion** (e.g. an arm wiggle) is not a find-me action (safety rules). Needs the device connected to the brain (router). Blinking a Pi's LED may need a one-time permission setup on the Pi.
- **Later, location:** GPS doesn't work indoors. Inside, a rough location could come from which Wi-Fi access point a device is near; GPS only for outdoor/cellular robots (the "cellular robots" idea).
- **Plugs into:** device plug-ins (an optional "identify" action); device card.

### AR labels in the Quest
- **What:** in the headset, look at any device and its name + status float above it.
- **Why:** visually cool (the builder: "somewhat useless but visually cool").
- **Methods, simplest first:**
  1. **Place labels by hand once:** point the controller at a device, pick its name; the Quest remembers the spot (WebXR anchors). No camera needed. Moving a device means re-placing its label.
  2. **QR codes / AprilTags** (square printed markers made for robots, readable from far): automatic, but the Quest's browser may not give web pages access to the camera images; to check (native apps can use Meta's camera access).
  3. **Recognizing devices by sight** (computer vision): hardest; identical Pis look the same anyway.
- **Not found earlier in the docs.** Related: "Quest vision Q&A" (below), and lining the 3D arm up with the real one by hand (built 2026-11-10, `docs/guides/quest-setup.md`), the same idea for one device.
- **Plugs into:** Quest client + devices (status) + cameras/vision (methods 2–3).

### Brain as an MCP server
- **Decided 2026-11-09** (`docs/plan/lab-jarvis-log.md` → "AI-assisted development"; focus steps 2, 6): the brain offers MCP tools (one definition, used by the hub chat and by any developer's Claude Code / Codex / LM Studio); a small fast chat of our own for quick questions; a **"send to harness" toggle** on the chat line + a "send everything" setting; permission tiers read / act / move / admin.
- **What's left here:** the act and move tiers; per-developer access tokens; reaching the MCP server from laptops (needs the router + remote access); LM Studio as a local harness.

### LLMs/VLMs driving the green SO-101s
- **In the focus since 2026-11-12:** the green arms become drivable in lab-os (step 11). What stays here: comparing general AI models that see and reason (LLMs/VLMs, the "look, then reach" route) with the trained VLA (SmolVLA, first round done 2026-11) on the same tasks, through the call logs.
- **Also to try:** **Physical Intelligence's API** (their π robot models; waitlist opened 2026-11, the builder heard), Gemini Robotics-ER 2, and more VLA training rounds.
- **Plugs into:** robots slot (SO-101 driver exists for so101-white); cameras/vision; AI models; the projects module (the device moves from "locked" to shared).

## Recent ideas (2026-10-30)

### Assistant pictures beyond the plain circle
- **What:** more picture styles per persona, plugged in as decorative renderers of the assistant's state (`docs/plan/lab-jarvis-log.md` → "How it fits together"):
  - **Orbs inspired by other assistants** (e.g. the feel of ChatGPT's voice-mode orb for a GPT persona, a Claude-feel one for a Claude persona). Our own designs, **no logos or brand assets**. A persona's look should match the model really behind it.
  - **A 3D character in VRM format** (open format; the `three-vrm` library runs on the three.js we already vendor): blinking, breathing, mouth moving with the voice.
- **Not Live2D** (the Neuro-sama look): its runtime isn't open source (license to check before vendoring), it needs a paid/licensed character model, and nobody here knows it. VRM gives a similar result with open tools.
- **Plugs into:** persona `picture:` field; quality levels (characters drop to the plain circle at `minimal`).

## Recent ideas (2026-10-28)

### Hidden sensor data the hardware already has
- **What:** most of our devices measure more than we use, like a Mac's lid-angle sensor. Read it in health checks, the startup status and the HUD. Candidates (**? = to verify on our exact hardware**):
  - **SO-101 servos (Feetech STS3215):** besides position, each reports **load (rough force), temperature, voltage**, speed and a "moving" flag. Uses: **grasp detection** (gripper stalls with load = it's holding something), "someone pushed me" / collision detection, rough "how heavy is it?", overheating warnings before a servo cuts out.
  - **xArm 1S:** battery voltage from the controller (?); per-servo temperature/voltage (?).
  - **Raspberry Pi:** CPU temperature, and an **under-voltage flag** (`vcgencmd get_throttled`): an indirect **low-battery warning** for the Raspbot even if its battery can't be read directly. Raspbot sensors: ultrasonic distance, line-following sensors (?).
  - **Jetson:** live power draw in watts and temperatures (`tegrastats`).
  - **Quest:** battery, **headset on/off your head** (the browser reports when the session is hidden; dead-man input already), 25 tracked joints per hand, floor height.
  - **Cameras:** auto-exposure/brightness → **room light level**, which predicts whether hand tracking will work (it needs reasonable light).
  - **Microphones:** background noise level (fans) → whether voice will work.
  - **Every networked device:** Wi-Fi signal strength and delay → connection-quality warnings before things drop.
  - **Phones (Android Chrome):** compass, motion sensors, sometimes light sensor.
- **Why:** cheap "wow" facts plus real early warnings (low battery, hot servo, too dark for hand tracking), right where the troubleshooting suite needs them.
- **Plugs into:** each device plug-in declares what extra readings it offers; the troubleshooting suite, startup status and HUD read them. Safety: reading sensors is fine; anything that powers or moves stays under the safety rules.

### Startup sequence ("systems coming online")
- **In the focus now (2026-10-30):** the startup *animation* itself (designed; built at `/design` (`docs/plan/current-focus.md` step 10), with only real brain-side checks). **What stays here:** devices lighting up as they report in (needs the roll call → router) and the power-up walk.
- **What:** after a trigger (wake word, card, button, Quest, touchscreen…), the brain wakes the screens and plays a short sequence where **each device lights up as it actually reports in**. The animation *is* the roll call, with a sound per device, and it ends with a greeting + one-line summary. Starts on the device that triggered it (Quest, touchscreen, desktop); other screens join.
- **Why:** cool to watch *and* useful: you see at a glance what's up; results feed the troubleshooting suite's report files.
- **Reality (2026-10-28):** the first person arrives to a closed, empty lab; every robot is off and needs a physical switch (SO-101s: no switch, wall power). So nothing but the brain, router, screens (and cameras) is on at startup.
- **Default (decision 2026-10-28): robots are optional.** Startup assumes no robots are on; often the builder just wants to code or ask something. Startup covers the brain, screens and anything always-on. When someone switches a robot on, its status **flickers on** in the main system (with its chime), whenever that happens.
- **Optional "power-up walk" (demo mode).** For demos: startup shows the devices for that demo dim, with what to do ("xarm1: flip the switch on the base"). As you walk around switching things on, each one lights up with its chime the moment it really answers, like a cockpit pre-flight. The manual chore becomes the show, and when you're done you know everything works. Devices you don't need today can be skipped. Fast: the brain part takes seconds; the rest goes as fast as you flip switches.
- **Battery levels:** the xArm controller's protocol reportedly has a battery-voltage command (verify in our driver). Raspbot: unknown. A Pi can't measure a battery by itself, but Yahboom's expansion board might; check its docs before giving up.
- **Sound:** cosmetic, to add life (JARVIS feel). On while someone works in the lab, off otherwise (follows the on/off triggers); volume/mute in the sound pack.
- **Rules:** "only claim what's real": nothing lights up unless it really answered. An arm "nodding awake" would be great for visitors, but it's robot motion: only under the safety rules, opt-in, workspace clear, never unattended.
- **Plugs into:** triggers slot → roll call / health checks → theme + sound packs + decorative layer.

### Smart plugs to power devices on/off (downgraded 2026-10-28)
- **What:** network-controlled power plugs for things on wall power.
- **Reality:** almost everything here is battery-powered with a physical switch, so smart plugs can't turn it on. Only useful for the SO-101 power supplies (and later Pis/Jetsons on wall power). Low priority.
- **Watch out:** cut a Pi/Jetson's power only after a proper shutdown (SD card corruption); powering an arm counts as robot motion (safety rules); needs the lab network + professor's OK; plugs must work without a cloud app (offline rule).

### Many devices at once ("who's driving?")
- **What:** several people/devices use the system at the same time (Quest, phones, touchscreens, desktop).
- **Recommendation:** **everyone can watch** (all screens show the same live state); **only one device controls a given robot at a time** (it "has control"; others ask for it or it's handed over); **STOP works from every device, always**. Voice/agent commands go through the same rule.
- **Why now:** the teleop server already accepts several input pages and mixes them (fixed for teleop 2026-10-29, closed teleop focus step 6b). This generalizes it later.
- **Plugs into:** brain core (control lock per robot) + outputs/clients + safety layer.
- **Decided (2026-10-28):** control is **handed over** (the current driver releases it), not grabbed.

---

## Recent ideas (2026-10-27)

### Touchscreens as clients (small Pi screens + the big Newline)
- **What:** the lab's 3 small Raspberry Pi touchscreens (~7–9") and the ~75" Newline touchscreen on wheels become lab-os clients. Each shows a page from the brain that is tailored to its size: control, status, or new kinds of interaction (e.g. 3D arm models you can spin with your fingers).
- **Why:** more ways to use the system without a headset; the big screen suits visitors and groups.
- **Plugs into:** outputs/clients slot (same message protocol as the Quest page). The Pis just run a browser in kiosk mode (full-screen, no address bar), so they stay thin. Related: "Multi-screen presence", "Lab health dashboard" (below).
- **Possible roles (to discuss):** a small screen next to each robot as its "face" + status + STOP; the Newline as a group/visitor screen (3D arm view, cast of the Quest view, dashboard).
- **Rules that still apply:** any robot motion from a touch goes through the same safety layer (limits, dead-man); every screen that can move a robot shows a STOP.
- **Answers (2026-10-27):** "hologram" = a 3D arm model you spin with touch (the existing three.js arm view already does this with a mouse; touch is a small step). The Newline is a standalone Android computer, so its own browser opens the brain's page (check that browser supports WebGL + WebSockets). Uses: data display, or robot control with sliders.
- **Note:** slider control is the same page as phone teleop's touch mode (below). Build **one touch-control page** that adapts to phone, small screen and the 75" screen.
- **Open questions:** which Pi models are behind the small screens? (Reaching the brain: `pi01` does over the lab Wi-Fi, and the Newline through `pi01`, 2026-11-10; the router makes it simple.)

### Voice beyond push-to-talk
- **Built (focus step 7, 2026-11-12):** push-to-talk, dictation and the wake word through the speech-to-text → chat → text-to-speech pipeline (`docs/guides/voice.md`). The routes and prices compared on 2026-11-10 (OpenAI, Gemini, local, realtime): `docs/archive/focus-2026-11-13-hub-voice-ai.md` → "Step 7, concretely".
- **What stays here:** a realtime service for demos (faster, handles interruptions); a **local** speech-to-text → model → text-to-speech pipeline (e.g. faster-whisper + Piper on the brain) as the **offline lite mode** fallback; tool calls from the voice model through our tools + safety layer; venues need internet for cloud voices.
- **Other triggers later:** a big USB button, or an IR remote (like the builder's Raspbot voice project).
- **Plugs into:** triggers slot, conversation manager, model router.

### Google Glass (Explorer Edition) as a display + camera
- **What:** custom app on the lab's Google Glass Explorer Edition: a tiny heads-up status display, and maybe its camera as a first-person view.
- **Why:** a "JARVIS glasses" moment; a hands-free status display while working at a robot.
- **Plugs into:** outputs/clients (display) + cameras/vision (first-person camera, like "Quest vision Q&A").
- **Honest caveats:** 2013 hardware, long discontinued, runs a very old Android (4.4). Apps are built with old tools, and the battery is likely worn. Camera privacy is still deferred (log). Much later.
- **Status (2026-10-27):** it boots; built-in voice commands (e.g. take a picture) work. No use picked yet ("I just want to use it for something").
- **Candidate uses (pick one later):** (1) teleop status HUD (FOLLOWING / FROZEN / gripper %) while driving the arm with a phone or leader arm; (2) "what am I looking at?": a photo from the Glass → JARVIS answers on its display; (3) alerts from the troubleshooting suite.
- **Next check (cheap, when curious):** which firmware is it on, and can a computer install apps on it over USB?

### The phone as a microphone for the hub (2026-11-11)
- **What:** open a small page on your phone, hold to talk (or dictate), and your words go to the brain; the answer plays on the phone, or on a screen you pick (e.g. ask on the phone, the Newline answers).
- **Why:** talk to the hub from anywhere without a room microphone; works in noisy places because the microphone is in your hand.
- **Watch out:** the phone's page must be secure for the microphone: Android Chrome's flag works; an iPhone needs a real `https://` address (the deferred domain, or Tailscale's certificate on a phone running Tailscale).
- **Plugs into:** voice (step 7, the same per-screen recording), "Teleop from a phone" below, screens.

### Teleop from a phone
- **What:** a phone as a teleop input. Either (a) a touch page with sliders/joystick + STOP, or (b) the phone itself as a 3D "controller" (Android Chrome supports WebXR AR, which tracks the phone's position and tilt in space; iPhones' browser doesn't).
- **Why:** anyone can try it without a headset; a fallback if the Quest is unavailable; another entry for "Ways to teach a robot".
- **Plugs into:** inputs slot (a new input plug-in, same pipeline + clutch + dead-man). Includes the earlier "visitors' phones as remotes" (interact without the headset).
- **For whom (2026-10-27):** everyone: the builder, lab members and visitors.
- **Gyro control (builder's main idea, 2026-10-27):** the phone's motion sensors (gyro + accelerometer, read by the browser's device-orientation feature) give its **tilt/rotation**, not its position in space. So pure gyro control means: tilt → wrist rotation (the glove's "tilt-for-rotation", which worked well), and/or tilt as a joystick (tilt forward = arm moves forward, at a speed set by the angle; relative, so no snapping). Real 3D **position** needs camera-based tracking (WebXR AR on Android Chrome). Both behind a clutch button on screen. iPhones ask the user for motion-sensor permission, and either way the page needs `localhost`/HTTPS.
- **Watch out:** WebXR needs `localhost` or HTTPS. Over USB that's easy with an Android phone (`adb reverse`, as with the Quest). Over Wi-Fi it needs a certificate. Phone tracking is less steady than Quest controllers.

---

## Recent ideas (2026-10-24)

### Clap to activate / deactivate
- **What:** a double clap turns the system on or off.
- **Why:** fun to show off. Usually kept **off** (loud noises could set it off), switched on occasionally.
- **Plugs into:** Triggers slot (one trigger plug-in, off by default, switchable per venue profile).

### "Jarvis, log out" (and similar phrases) to deactivate
- **What:** spoken phrases that put the system to sleep or log out.
- **Why:** a natural way to end a session, matching the wake word for starting one.
- **Plugs into:** Triggers slot (phrase triggers, fed by the voice pipeline).

### Interrupting and queueing in voice conversations
- **What:** I can cut the assistant off mid-sentence; I can give several requests in a row and have them handled in order.
- **Why:** real conversations aren't strict turn-taking; waiting for long answers is annoying.
- **Plugs into:** Conversation manager (one component owns interrupt / queue / turn-taking).

### Coding agent ("ask for a feature, it gets built")
- **Direction decided 2026-10-30** (`docs/plan/lab-jarvis-log.md` → "AI-assisted development"): an agent that works like Claude Code, paid by the lab's API account (no personal subscription); ask "add the touchscreen page from docs/plan/ideas.md" and it builds it **on its own branch** (`agent/<task>`) → tests → PR → the builder approves. Never modifies the running system. Same path for system updates. The read-only first half (project helper) is in the current focus.
- **Candidates (2026-10-30: keys are OpenAI's; Anthropic out of credits):** OpenAI's Codex (open-source coding agent, OpenAI API key; to verify), or the Claude Agent SDK (Claude Code's engine with an API key) if Anthropic credits are refilled. Reference: https://github.com/ehteshambuildagents/jarvis (runs it headless; tools default-deny); it reuses a personal subscription login, which we won't do.
- **Open questions:** cost per task vs. the budget (coding tasks cost far more than chat); which tools it gets (default-deny); how it reports progress in the hub.
- **Plugs into:** agent harness slot (slow path) + the normal git / CI / tag workflow; robot motion only through our safety layer.

---

## Earlier ideas (moved here 2026-10-24 from docs/plan/lab-jarvis-log.md and docs/plan/current-focus.md)

### Triggers & sign-in
| Idea | Why | Plugs into |
|---|---|---|
| Card-swipe ignition | Part of the walk-in moment; the lab has a card reader. | Triggers |
| Light-sensor ignition (room lights on → wake) | — | Triggers |
| Kinect gestures | — | Triggers, inputs |
| Student ID sign-in (stored hashed) | Know who's using the system. | Sign-in |
| Face recognition (opt-in only) | Hands-free sign-in / greeting. | Sign-in, cameras/vision |

### Voice, personas, agents
| Idea | Why | Plugs into |
|---|---|---|
| Program-by-voice / agent onboarding | — | Agent harness |
| Local models: beyond the `local` chat setup (`docs/dev/chat.md`) (e.g. which model fits 12 GB, local voice) | Offline lite mode; no per-use cost; privacy. | AI models (router) |

### Screens, phones, headset
| Idea | Why | Plugs into |
|---|---|---|
| Multi-screen presence (lab PCs/displays) | The system "lives" on the room's screens; lab only. | Outputs/clients |
| Quest-only mode | — | Quest client |
| Quest launch → HUD (launch animation into the HUD) | — | Quest client, theme/decorative layer |
| Quest vision Q&A ("what am I looking at?") | Ask about whatever the headset sees. | Cameras/vision, AI models |

### Teleop & robots
| Idea | Why | Plugs into |
|---|---|---|
| Fix the Hiwonder glove: (A) re-flash if its firmware source exists, or (B) glove → computer → arm with the teleop logic | Only if fun or useful (low priority). | Inputs (glove plug-in) |
| "Ways to teach a robot" demo (teleop, leader arm, glove, look-then-reach side by side) | Strong pitch / teaching story. | Teleop + demo |
| Robot testing harness (not tied to the research paper for now) | Repeatable robot tests. | Tools |
| ROS 2 bridge | — | Robots |
| Air:bit drones module (much later; drones stay out of AI/voice/visitor control) | — | Robots (bridged via micro:bit radio) |

### Uses, reach, events
| Idea | Why | Plugs into |
|---|---|---|
| Lab health dashboard | — | GUI + roll call / health checks |
| Shared lab memory | — | Tools, AI models |
| Teaching use | Use the system in classes / demos. | — |
| Recruiting demo (portable) | Visitor routes may not pass the lab. | Portable kit, teleop |
| Remote check-ins | — | Remote access |
| Full lab in a bag | — | Portability |
| Live link to the lab (from a venue) | Show lab-only devices while traveling. | Remote access, network |
| Remote GUI from home (via a private overlay network; ask IT first) | Use the system's GUI off-site. | Remote access, GUI |
| Cellular robots | Robots across campus without the lab network. | Network/connection |
| Escape room (dropped 2026-10-15, still parked) | — | — |
