# Current Focus: the JARVIS hub, voice, and AI driving the SO-101 arms

**Read this at the start of every Claude Code session.** It says what to work on *now*. The long-term plan, decisions and module list live in **lab-jarvis-log.md**; this file only sets the current priority. When this focus is done, move it to `docs/archive/` and write the next one. Previous focus: the teleop demo, closed 2026-10-30 (`docs/archive/focus-2026-10-teleop-demo.md`; what's left of it is in `docs/ideas.md` → "On hold"). What already works: `FEATURES.md`.

---

## The goal right now
**A demo of every feature on Thursday 2026-11-19** (decision 2026-11-12, the builder: ambitious, everything). The hub runs full screen on the lab desktop's own screen (the Newline only once it's smooth, step 12). Someone taps it: the startup plays with sound and a spoken greeting, and lands in the hub: buttons into the system, panels of real project facts, and the assistant. They ask it something, typed or **by voice** (push-to-talk, dictation or "hey jarvis"), and it answers aloud. An AI drives the SO-101 arms (white and green) through the brain's tools, looking through the cameras. Teleop works from the Quest (relative or 1:1) and the desktop. Pages can be sent to other screens, and the hub has a VR version.

**Looks (decision 2026-11-12):** the design is no longer a surprise. The designed hub (`/design`) is the one demoed, and new or changed pages follow the design (`docs/design/DESIGN.md`, `docs/design/hub-concept.html`, `config/theme.yaml`). `/` still shows the plain hub by default (`hub.look: plain` in the theme), just in case; the plain pages stay working.

Roll call and robot connections over the network wait for the lab router (`ideas.md` → "On hold").

## Until the demo (Thursday 2026-11-19)
The builder has assignments due Wednesday 2026-11-18, so most of the coding runs in Claude Code sessions while the builder is busy; lab time is what's scarce. **Fable 5.2 access ends Monday 2026-11-16** (real-arm AI runs with it before then; after that, the same tools work with any AI).
1. **Voice** (step 7): push-to-talk with a spoken answer, the spoken greeting, dictation, the wake word. On the free Gemini key, a USB microphone on the brain desktop.
2. **Green arms in lab-os** (step 11), then **cameras for the AI** (step 3) with all four cameras usable.
3. **The AI on the real arms** (step 2): the cube task with `pose_view` and the cameras.
4. **Screens** (step 8): send a page to another screen; one tap opens the hub on any screen.
5. **The design's polish and the VR hub's buttons** (step 10).
6. **The Newline** (step 12): measure, then decide; not blocking.
7. **Before the demo:** go through `FEATURES.md` on the real hardware, fix what breaks, tag the version (`demo-2026-11-19`; demo only from a tag).

Lab checks for each step: `docs/lab-checklist.md`.

## How it fits together
- **One brain program, `lab-os serve`.** It serves the hub page and mounts the teleop pages inside it. The core grows out of the teleop code (decision 2026-10-24). `lab-os-teleop` keeps working until it's replaced.
- **The brain is an MCP server** (decision 2026-11-09): tools (read the arm, move the arm, `pose_view`, camera pictures, read the docs) in a standard format AI tools understand. Claude Code, Codex and Claude Desktop connect to it; the hub's own chat uses the read tools. Tools are grouped in permission tiers (read / act / move / admin; table under "After this focus").
- **The assistant's state is separate from its picture.** The state: `idle`, `listening`, `thinking`, `speaking`, `offline`, `error`, plus a 0–1 "loudness" while speaking. The rest of the system only sets the state; the **picture** is chosen by the persona and only reads it.
- **Personas are config files**, `config/personas/<id>.yaml` (`docs/personas.md`). The active persona: `--persona`, else the venue's `persona:` (`default` = the place's), else `persona:` in `place.yaml`; the default is `lab-assistant`, the show persona `jarvis`. Fields include `voice:` and `wake_word:` (step 7). The loader keeps unknown fields and warns. **The greeting:** "Good morning / afternoon / evening." plus one line of real news when there is some, else the persona's `greeting` line; built by the brain from real facts. The startup title is the place's name (`place.yaml`).
- **The hub's buttons come from config** (`hub.modules` in the theme). No fake "coming soon" buttons.
- **The status strip and panels show only real facts.** Where something isn't real yet, leave it out.
- **Offline vs. internet.** Offline: start screen, hub, the assistant's picture, teleop, sounds, theme, fonts. Needs internet: the AI chat and cloud voices. Without internet the assistant shows `offline` and everything else works.
- **A public screen** (the Newline, a hallway desktop): anyone can start it and talk to it, so the hub's chat stays in the read tier, the move tools only accept AI tools on the brain's own computer, a spend cap pauses the chat, the conversation clears on the reset, and the venue profile hides internal details.
- **Starting it:** the designed hub starts with one tap (full screen + start); ⏻ goes back to the start screen and leaves it waiting full screen. The plain hub keeps two taps (full screen, then start). A **Full screen** button appears on every page whenever it isn't full screen, and says why where full screen isn't available (built 2026-11-11, `docs/hub.md`).
- **Back to the start screen** after 30 minutes with nobody there (`hub.reset_after_s: 1800`, per venue; dims after 15): closes modules, clears the conversation from the screen. **Never while something is in use:** teleop has the arm, the AI tools are moving it, or a voice turn is running.
- **Drawing resolution per screen** (built 2026-11-11): ⚙ → This screen, or `?res=` (`docs/hub.md`), for slow screens.

## Rules for this focus
1. **Grow it out of the teleop code**: extract what exists; formal interfaces only when a second real user needs them.
2. **Fake first, offline first**: every step runs without hardware and (except the AI steps) without internet. Robot tools run on the fake arm before a real one.
3. **Only claim what's real**: the start screen, status strip and panels never show a check or number that didn't happen.
4. **The design for new pages** (decision 2026-11-12, above); `/` stays plain by default.
5. **The hub's built-in assistant never changes anything.** It reads and answers. The **move tools** are for a developer's AI tool on this computer only: same safety layer as teleop, **ask every time** (move tier). Writing code by AI only via branch → tests → the builder's approval.
6. **Secrets** (API keys) only in `.env`; `.env.example` lists the names.
7. **Portable**: Linux, Windows, macOS. **Plain names** in code, show names in persona files.
8. **The green arms** (decision 2026-11-12): lab-os may drive them and use the training cameras, with CLAUDE.md's four rules (no motor ID/firmware changes, calibration read-only, the `lerobot` env untouched, never a port that LeLab or a training run is using). Step 11 (built 2026-11-12) makes the code follow them.
9. **Nothing place-specific in code**: the lab's name, devices, what's off limits, venues and personas live in config; another place = another config folder (`--config`, `docs/places.md`).

## Steps (each one is a small, testable win)
The Current Project panel reads this list: each step's **bold title** is what the hub shows ("Next: Voice"), so titles are short plain words. A finished step gets `(done YYYY-MM-DD)` right after its title. Order until the demo: "Until the demo" above.

0. **Settle before coding** (done 2026-11-09). AI service: OpenAI first (the professor's key, to ask for), free Gemini keys meanwhile, local models as another setup; budget ≤ $20/month. The design approved 2026-11-09.

1. **Plain hub** (done 2026-11-12). Start screen with two taps, status strip, module buttons from `hub.modules`, a plain circle for the assistant, Current Project and Commits panels, the reset, `/perf`. Ran on the lab desktop, `pi01` and the other desktop (2026-11-10). The Newline is its own item now (step 12). How: `docs/hub.md`.

2. **Robot tools for AI.** The brain's MCP tools drive an SO-101 (`arm_status`, `list_poses`, `move_joints`, `gripper`, `move_to`, `go_to_pose`, `stop`, `pose_view`), through the same safety layer as teleop, asking before every move. Details: "Step 2, concretely".
   - **Status:** built (2026-11-09), cube task on the fake arm with Fable (2026-11-10). On the real `so101-white` (2026-11-10): the moves run, but blind the AI misses (it needed more than words). Since 2026-11-11: moves report `stopped_short` with how far off; `pose_view` (step 3). **Left:** the real arm with `pose_view` (lab day 2026-11-12), then with the cameras; STOP from another screen; the green arm once step 11 is in.

3. **Cameras for the AI.** A `camera_snapshot` tool (read tier) for the arms' cameras, so the AI looks before it reaches. Details: "Step 3, concretely". `pose_view` built 2026-11-11.

4. **Personas** (done 2026-11-10). `docs/personas.md`.

5. **Typed chat** (done 2026-11-10). OpenAI-style chat interface, setups in `config/models.yaml` (`main` OpenAI, `backup` Gemini on the free key, `local` Ollama), streaming, spend log and cap, conversation kept and brought back. `docs/chat.md`. **Left:** a real answer from OpenAI once its key is in `.env`.

6. **Project helper** (done 2026-11-10). Read tools for the docs, git and the device list on the MCP server; the hub's chat uses them and drafts prompts. **Left:** add them to the allow-list in `.claude/settings.json` (the builder).

7. **Voice.** Push-to-talk (the default), a spoken answer, the spoken greeting, dictation, and the wake word; the core follows `listening` / `speaking` + loudness. Typing never suffers; no microphone, no voice button. Details: "Step 7, concretely".
   - **Status:** push-to-talk with a spoken answer, the spoken greeting, dictation and the per-screen way in built (2026-11-12, `docs/voice.md`): on the free Gemini key, tried on a laptop in Chrome with a recorded voice. **Left:** the wake word; a person at the lab's USB microphone.

8. **Screens.** Send a page to another screen, and one tap opens the hub on any screen. Details: "Step 8, concretely".
   - **Status (2026-11-10):** done for **monitors on the brain's own computer** ("Show on another screen", Chrome's Window Management API; `docs/hub.md` → "Other monitors"). Over the lab Wi-Fi, `pi01` and the other desktop open the hub by the desktop's IP address, and `--drive-from` lets one of them drive. **Left:** named screens and "open on…" through the brain; the one-tap icons.

9. **Demo check** (done 2026-11-12). The builder ran through the hub on `/design` with nobody's help: it works, with bugs to fix later. The full every-feature check is part of "Until the demo".

10. **Design polish.** The designed hub (`/design`) is built (2026-11-10): the concept on the brain's real data, with teleop, monitor, AI Control (`/ai`) and Settings in its style (`docs/hub.md` → "The designed hub"). **Left:**
    - **The VR hub's buttons** (decision 2026-11-10): `/xr` today is watch-only (the jump, then the network and the core; the trigger replays the jump). After the jump: a few big buttons around the core that you point at with a controller or hand (Teleop, the arm view, Ask); Teleop opens the arm scene without leaving VR; the jump polished to match the main hub's.
    - Bugs from the 2026-11-12 demo check (the builder to list); alerts from real events; how a page sent to another screen looks (keep it plain if there's no time).

11. **Green arms.** lab-os drives `so101-green` and uses its two cameras, like `so101-white` (decision 2026-11-12). Details: "Step 11, concretely".
   - **Status:** built 2026-11-12, tested without hardware (`docs/ai-control.md` → "The green arm"). **Left:** on the lab desktop, with LeLab closed: the read-only `--watch`, then the green follower moving with the builder present, then the AI driving it (`docs/lab-checklist.md` → part 8); which camera is which (`so101-green-cam-a`/`-b` until then).

12. **Newline.** Find out whether the Newline can show the hub smoothly; not blocking anything (the demo is on the desktop). Details: "Step 12, concretely".

### Step 2, concretely (robot tools for AI)
- **Which AI:** any MCP client: Claude Code with **Fable 5.2** until 2026-11-16 (`/model`), then other models; Codex, Claude Desktop. Setup: `docs/ai-control.md`.
- **Safety:** every move goes through the teleop path (soft limits, the venue's `max_speed_scale`, smoothing). The brain **clips and refuses**: a maximum change per call (30° per joint or 10 cm), refusal when the venue has `motion_allowed: false`, below the 1 cm floor or out of reach. **One controller at a time:** teleop and the move tools exclude each other; STOP from any page wins. **Asks every time:** the move tools are never allow-listed. Moves return the arm's real position (`arrived` or `stopped_short` with `off_by_cm`).
- **Other screens while a real arm is connected:** view only (`--host 0.0.0.0`), STOP works everywhere; control stays with this computer, the Quest and computers named with `--drive-from`.
- **A log of every call** (`logs/ai-tools/`), so runs can be compared (e.g. with SmolVLA on the green arm).
- **Done when:** the real arm does the cube task from a Claude Code prompt, every move approved; then "pick up the red block" with no positions given in words (step 3).

### Step 3, concretely (cameras for the AI)
- **The tool:** `camera_snapshot(camera)` (read tier) opens the camera, takes one picture, closes it, and returns a small JPEG (about 640 px wide: images cost the AI tokens). OpenCV (headless) via `uv add`. A camera another program is using (LeLab, a recording) is refused with a sentence.
- **Telling the cameras apart:** all four cameras (two white, two green) are the same model (Innomaker U20CAM, Sonix chip `0c45:6366`) and report the same serial `SN0001` (GOTCHAS 2026-11-11), so `/dev/v4l/by-id/` can't tell them apart. **Use the socket:** `/dev/v4l/by-path/…` names, never `/dev/videoN` (numbers change) or by-id. Each camera gets a name in `config/devices.yaml` with its socket and what it sees (e.g. `so101-white-cam-top`, `so101-green-cam-wrist`). The model-wide block goes (step 11).
- **USB sockets are full** (2026-11-12): the brain desktop's 7 USB-A sockets hold the keyboard, mouse, the green cameras and arms, and the xArm. Until the 7-port powered hub (shopping list in the log) arrives, the white arm and its cameras go in by unplugging the green ones; their sockets then change, so record each setup's by-path names. Rewriting serials: only with a tool from Innomaker (asked? not yet; never on a camera without one).
- **`pose_view`** (built 2026-11-11, `docs/ai-control.md` → "Seeing the pose"): a picture of the 3D model in the arm's pose, side and top, with the table, a cm grid, the last target and the AI's own marks. Works without cameras.
- **Done when:** the AI looks, then reaches: "pick up the red block" with no positions given in words.

### Step 7, concretely (voice)
- **What it does (decisions 2026-11-11/12, the builder):**
  - **Push-to-talk** (hold a key or the mic button, speak, release; it answers aloud) is the **default way in**.
  - **Dictation:** tap the mic, the words appear in the ask line as you talk, it stops after a short silence or a second tap, you fix and send it like typing.
  - **The wake word** ("hey jarvis", the persona's `wake_word:`), built with voice: works from anywhere in the room. Detected locally (**openWakeWord**, free, on the brain's CPU, ships "hey jarvis"; Porcupine for custom words): nothing goes to a voice service until the phrase is heard. Listens only while the hub is awake; off by default on `public: true` venues. Its "listening for the wake word" sign is **subtle** (a small dot in the status strip) and **separate from the core's `listening`**, which only starts after the phrase or a push-to-talk press. If several screens hear it, one answers.
  - **The way in is chosen per screen** ("This screen" setting): push-to-talk by default; dictation or the wake word where that screen can do them (the wake word needs a secure page and a microphone that may stay open). Where nothing else works, push-to-talk is the only choice.
  - **A spoken greeting** after the jump when voice is on: the greeting's text, plus a short hint ("You can talk to me: tap the mic."). The start tap lets the browser play it. No voice or no internet: silent.
  - **Voice in and out happen at the screen the person is at**, with its own microphone and speakers; the brain only thinks.
- **First version (decision 2026-11-12):** the **free Gemini key** (OpenAI when the professor's key comes: a config change), a **USB microphone on the brain desktop** (any socket), the hub on the desktop's own screen (`localhost` is a secure page, so the microphone works).
- **The route:** swappable voice setups in `config/models.yaml` (service, model, key name, price per minute, `fallback`), picked by the persona's `voice:`. **The pipeline** for everyday use: speech-to-text → the same conversation manager as typing (persona, read tools, history, spend cap, states) → text-to-speech; about 2–3 s to the first spoken word. A realtime service (faster, handles interruptions) is a separate path for later.
- **Prices checked 2026-11-10** (per minute of audio; a question ≈ 10 s heard + 10 s spoken):
  | Route | Heard | Spoken | ≈ per question |
  |---|---|---|---|
  | Pipeline, OpenAI `gpt-4o-mini-transcribe` + `gpt-4o-mini-tts` | $0.003 | ~$0.015 | $0.003 (+ the chat model) |
  | Pipeline, Gemini (free key) | $0 | $0 (`gemini-3.8-flash-lite-tts`) | $0, but Google may use the audio; rate limits |
  | Pipeline, local (faster-whisper + Piper on the brain) | $0 | $0 | $0, offline, slower; the GPU is shared |
  | Realtime, OpenAI `gpt-realtime-2.1-mini` | ~$0.006 | ~$0.024 | ~$0.007 (+ the conversation re-billed each turn) |
  | Realtime, Gemini Live | $0 free key ($0.005 / $0.018 paid) | | $0 free; same caveats |
- **Who does what:** the page records and plays (microphone in the browser, audio to the brain over the WebSocket, plays the reply, reports loudness); the brain talks to the voice service, so **API keys never leave the brain**.
- **Secure pages:** browsers give the microphone only to `https://` or `http://localhost` pages. The real address (`hub.indwesailab.com` with a Let's Encrypt certificate via Route 53) is **deferred** (decision 2026-11-10). Meanwhile: the brain's own screen (`localhost`); Chrome's flag on other screens (`chrome://flags` → "Insecure origins treated as secure", or `--unsafely-treat-insecure-origin-as-secure=http://<brain>:8080` on a kiosk); `adb reverse` on Android; Tailscale's certificate (`ideas.md`). No secure page or no microphone: no mic button, typing works.
- **Microphone detection:** the mic button only when the page is secure **and** the browser lists an audio input; react to plugging and unplugging; if permission is refused, say why. Push-to-talk plus the browser's echo cancellation keeps the speakers out of the microphone.
- **Open:** the room microphone for the wake word from anywhere in the room (fans: a conference speakerphone or a microphone array, not the weak USB dongles); the Newline's microphones (`lab-checklist.md`, part 2).

### Step 8, concretely (screens)
- **What it means:** (1) on the hub, "open on…" next to a module (e.g. Monitor) lists the other screens running the hub; pick one and the page opens there, Back on that screen (or "bring it back") closes it. (2) Each screen has an icon that opens the hub full screen under its own name, without typing an address.
- **Screens have names:** each screen connects under a name in its address (`/?screen=newline`, `/?screen=desk`); the brain keeps the list of screens that are there. Only screens with the hub open show up, so a screen used for something else is never taken over.
- **Nothing starts by itself** (the builder, 2026-11-09): the brain's computer gets a "Start lab-os" shortcut; other computers a "Lab hub" icon (`google-chrome --app=<address>/?screen=desk --start-fullscreen`); the Newline a home-screen icon. Screens reconnect by themselves when the brain restarts. One controller per robot still applies; other screens stay view-only while a real arm is connected.
- **The brain's address:** the desktop's IP address for now (e.g. `http://192.168.7.72:8080`; it may change). A fixed address waits for the router or the deferred domain.
- **One brain per network** (decision 2026-11-09): at start the brain looks for another one (mDNS, `zeroconf`); if one is there it doesn't start and says where it is; never vanishes mid-move; `--second-brain` for development (another port, no real robots). Can wait until after the demo.
- **The screens must reach the brain:** `network-setup-checklist.md` → "Networks before the router".
- **Done when:** from another screen, Monitor opens on the desk monitor and comes back; after switching everything off and on, one tap or click per screen brings the hub back with its name.

### Step 11, concretely (green arms)
- **Config:** `so101-green` (follower) and `so101-green-leader` as ordinary devices in `config/devices.yaml` (no longer `off_limits`), and the two training cameras by socket (step 3); the camera-model block removed.
- **Driving:** the SO-101 driver for the green follower reads its calibration from LeRobot's cache (`~/.cache/huggingface/lerobot/calibration/`, **read only**). The motor setup tool refuses the greens (no ID, baud or firmware changes). `lab-os serve --arm so101-green` like the white arm.
- **One program per port:** before opening a green port or camera, check that no other program has it open (LeLab, a recording, a training run) and refuse with a sentence if so. The training launcher keeps its checks.
- **The guard hook and permissions** (`.claude/hooks/guard.sh`, `.claude/settings.json`): stop blocking the green ports; keep blocking writes to the calibration cache and changes to the `lerobot` env and `~/lerobot`.
- **Docs:** the code-describing docs (`docs/ai-control.md`, `docs/places.md`, `docs/protocol.md`'s example, `docs/green-launcher.md`) follow the new behavior.
- **Done when:** on the fake arm, tests prove the read-only calibration, the "port in use" refusal and the motor-setup refusal; then the real green follower moves with the builder present, and the AI can drive it.

### Step 12, concretely (the Newline)
- **Known:** the hub is laggy on the Newline in its own Chrome (through `pi01`, 2026-11-10), even at `?quality=reduced`; from a Mac laptop and a lab desktop by HDMI it looked just as laggy (GOTCHAS).
- **Measure** (`lab-checklist.md`, part 2; the builder plans it for 2026-11-12): `/perf` in its own Chrome, then the desktop on its HDMI at 1920×1080, 60 Hz, compared with the desktop's own monitor; the drawing resolution; the Newline's picture settings; whether its microphones show up over the touch cable. Its manual: `docs/device_manuals/`.
- **What the numbers decide:** HDMI smooth at 1080p → a computer behind it (a spare ThinkCentre first, then a Jetson, then a Pi 5). HDMI choppy though `/perf` says ~60 → the Newline adds the lag itself; only a lighter page helps (the very light "wow" look, `ideas.md`). Its own Chrome fast enough with a lighter page → no extra hardware.

## After this focus: AI-assisted development (direction, decisions 2026-10-30 and 2026-11-09)
The goal: anyone working on lab-os can use AI to change the system **and** the connected devices (robots, Pis), without depending on one person's subscription. Two routes, same rules:
- **Bring your own AI tool:** each developer uses their laptop with VS Code + the Claude Code extension, Codex, or Claude Desktop: clone the repo, connect the tool to the brain's MCP server (with a personal access token, once remote access exists).
- **Lab-paid harness in the hub:** a **"send to harness" toggle** on the chat line hands the request to a coding agent running on the brain with the lab's API key (Codex with the OpenAI key, or Claude Code with an Anthropic key if refilled). Monthly spend cap.

**Rules for both:** code changes only on a branch (`agent/<task>` for the lab harness) → tests → PR → the builder approves; never edit the running system. Device actions go through the brain's tools in **permission tiers**:
| Tier | Examples | Who |
|---|---|---|
| read | device status, logs, docs, arm readouts, camera snapshots | everyone, incl. the hub's built-in chat |
| act | "find me" beep, restart a service on a Pi, deploy a tagged version to a robot | developers with a token; asks first |
| move | anything that makes a robot move | developers, through the safety layer, asks every time; off in remote mode |
| admin | `sudo`, deleting, reboots | humans only, never through tools |

The hub's built-in chat stays in the read tier (anyone in the room can type into it). Realistic workflows: `docs/use-cases.md`.

## Done on the side (not focus steps)
- **Teleop on the Quest** (`docs/quest-setup.md`): bare hands work (right wrist drives, left pinch = clutch, right pinch = gripper) but are hard to steer; controllers feel better but less intuitive. A speed slider + the right thumbstick, the SO-101 kept above the table, the 3D arm movable onto the real one, `--record`.
- **Teleop 1:1 mode** (built 2026-11-11, `docs/quest-setup.md` → "1:1 mode"): once the 3D arm is lined up on the real one, the gripper goes where the hand goes (scale 1), so the clutch is only for pauses. Its own speed cap per venue (`one_to_one_max_deg_per_s`, lab 180°/s, off on visit days); servo temperature and load logged (`logs/servo-health/`), 60 °C slows it. Relative stays the default until 1:1 is tried on the real arm and the servo logs say it doesn't wear the motors. **Left:** the Quest with the real arm, and a relative vs 1:1 comparison.
- **Training launcher** (`docs/green-launcher.md`): one click starts LeLab for the green arms after a port check. Not yet tried with the greens plugged in. LeLab itself looked hastily built and shows one camera (the builder, 2026-11-12): our own recording page is an idea (`ideas.md`).
- **One flaky test**, seen once (GOTCHAS): catch its name if it fails again.

## Hacks to clean up
- `config/poses.yaml`: the SO-101 `rest` pose comes from forward kinematics only; check it on the real `so101-white` (slowly, builder present) before relying on it.
- `robots/xarm.py`: 240°/1000 units is the datasheet scale, not measured (zero = the "Run" pose, signs observed 2026-10-27). Motion tuning (`lead_s` 0.3 s, `max_deg_per_s` 120, `idle_read_after_s` 0.6, `min_read_interval_s` 0.25) is from first tests, not optimized. Default limits (until hand calibration) come from the builder's grab script.

## Up next (after this focus)
Milestone 1, "Connected lab", once the router is here: roll call, robots reporting in (arms on other computers, since the brain desktop's USB is full), the Devices panel, `xarm1` as another robot through the core (`ideas.md` → "On hold" → "Core plumbing"). Other paused work: `ideas.md` → "On hold".
