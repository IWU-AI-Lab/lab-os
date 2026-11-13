# Lab JARVIS — Running Log

A living record of decisions, facts and open questions for the AI-lab "JARVIS" project. Newest entries go at the top of each section. Ideas live only in **docs/plan/ideas.md** (the backlog). Companion docs: **docs/plan/current-focus.md** (what to work on now), **docs/dev/project-scaffold.md** (what the repo should contain), **docs/dev/dev-setup.md**, **docs/guides/network-setup-checklist.md**.

**Current focus:** see **docs/plan/current-focus.md**.

---

## The goal (one paragraph)
Build a "JARVIS" for the university AI lab. **Primary user: the builder himself.** First priority: **connect most lab devices so Claude Code / AI agents can reach them for faster development.** On top of that: one AI brain that can see, control and eventually program the lab's robots through voice, typing and a screen GUI, with an optional Quest 3 experience (monitor only, monitor + Quest, or Quest only). Visitors are a secondary audience (a quick ~30-second headset demo with one command). **Modularity is a core requirement:** everything plugs in and out without rewriting the core. **Mobility is a goal too** (the system should travel to wherever visitors are, plus remote access from home and eventually robots across campus). Target: **~90% reliable**. Solo, unofficial project, 3–7 hours/week, no deadline. Success for the MVP = **it connects, and it inspires the builder to keep going.**

---

## Project hygiene (2026-10-23) — details in docs/dev/project-scaffold.md
Day one: README, CLAUDE.md (points to current focus + log; rules), docs/, SAFETY.md, .gitignore, .env.example (secrets never committed), config/ (personas, model router, devices, venue profiles), calibration/<robot>/, dependency lock, install script, tests with fake robots, formatter/linter, LICENSE (**ask the professor first; repo private until then**). Soon: docs/dev/GOTCHAS.md, DEMO.md runbook, decision records, CI on GitHub, **tagged known-good demo versions (always demo from a tag)**, CHANGELOG, task board. Later: CONTRIBUTING.md, HANDOFF.md, ARCHITECTURE.md, demo video.

---

## Arm roles (2026-10-23)
| Arm | Name | Role |
|---|---|---|
| SO-101 set (leader + follower), green | `so101-green` | **The builder's own SO-101 training project** (with the two training cameras; clarified 2026-11-08: not someone else's). **Since 2026-11-12 lab-os may drive it and use its cameras** (focus step 11), keeping four rules: no motor ID/firmware changes, calibration read-only, the `lerobot` env untouched, never a port LeLab or a training run is using (CLAUDE.md). First VLA training round done (SmolVLA). |
| SO-101 set (leader + follower), white | `so101-white` (follower), `so101-white-leader` | **Polished teleop demo + second act.** Built; driven from the Quest (2026-10-30) and by AI tools (2026-11-10); its two cameras (same model as the training ones) not in lab-os yet (focus step 3). May also join the training project — teleop then doubles as its data-collection tool. |
| xArm 1S #1 (built, works) | `xarm1` | **Teleop prototype now** + **the JARVIS-track robot** + fallback teleop arm. |
| xArm 1S #2 (unbuilt) | `xarm2` | Spare / later. |

SO-101 over xArm for polished teleop: smoother motors/bus, LeRobot support, URDF exists. xArm: works today, keeps `so101-white` free. xArm roles: teleop prototype, JARVIS-track robot (separate hardware per track), modularity proof, glove input, visitor-safe commands.

---

## Quest teleop input & display (2026-10-23) — details in archive/focus-2026-10-teleop-demo.md
Inputs: **controllers first** (grip = clutch, analog trigger = gripper, button = stop), **then hand tracking** (wow); keep both. Display: passthrough + minimal overlay (status, stop, workspace box, visitor hint); later ghost arm + camera feed; cast to a monitor.

---

## Hiwonder glove findings (2026-10-23)
Hardware: 5 finger potentiometers, MPU6050, Bluetooth, USB firmware port. Test: paired with `xarm1`; little lag; tilt-for-rotation good. Problems: extreme gestures needed; **snapping** (absolute tilt → angle) when switching motors; clumsy finger-count motor selection. Lessons → teleop requirements: per-user calibration + hysteresis, relative/clutch control, gentle ramps, whole-arm IK, keep tilt-for-rotation. Glove fix optional.

---

## Teleoperation module: "your hand becomes the robot's hand" (2026-10-23)
**Origin:** first-principles "what would impress most?" check, inspired by Tesla's Oct 15, 2026 Roadster demo (staged at a private site; double-take reactions; skepticism about unproven claims). **Lessons:** break an expectation; seconds to understand; narrow, controlled demo; filmable; never overclaim; fewest moving parts.
**The module:** Quest input → arm copies it live. Practical and true (teleop is how robots get taught). Needs only Quest + computer + arm (USB). Fast-tracked; rest of the plan stays.

## Second act & generalization (2026-10-23)
**Concern (user):** a trained arm that can't generalize (new places, lighting, objects) doesn't feel magical.
**Findings:** generalist robot models and APIs do exist, with limits:
- **Gemini Robotics-ER 2** (Google) — robotics reasoning model available as a **preview via the Gemini API** (spatial reasoning, function calling, etc.). Use it to **look and point**: camera photo + "where is X?" → location → our inverse kinematics grabs it. **Generalizes to new objects/places with no training.** Needs camera-to-arm calibration. User already has Gemini keys.
- **SmolVLA** (Hugging Face, LeRobot) — open pretrained robot model with a documented SO-101 fine-tuning route (~50 varied demonstrations to start). Better than training from scratch; language instructions. Training may fit the RTX 5070 (12 GB) — verify.
- **NVIDIA GR00T N1.6, Physical Intelligence π0/π0.5** — bigger open models; training needs ~22–70 GB GPU memory (rented cloud GPU); GR00T has an SO-101 route.
- **Gemini Robotics** (full action model) — partner-only; not available.
- **ACT from scratch** — weakest generalization; fine as a learning exercise.
**Result so far (2026-11, training project):** SmolVLA fine-tuned on **50 episodes** on `so101-green`: **~30% success**, better when objects are near the positions seen in training (limited generalization, as expected; more varied demonstrations should help). Training took **~2 h on the RTX 5070 (12 GB), using ~8 GB**, with tweaks (e.g. the VLM part frozen). First real evidence for route B on our hardware.
**Plan:** (A) "look, then reach" with Gemini Robotics-ER 2 first (most magic per hour: "put anything on the table and ask it to grab it"); (B) then SmolVLA fine-tuned on our own teleop recordings with varied conditions. Recording tip: vary positions, lighting, backgrounds, distractors; record in the demo venue too.

---

## Mobility, portability & remote access (2026-10-23)
**Principle: the brain is software, not a place.** Lab desktop by default; laptop/Jetson ("field brain") when traveling. Robots find the brain **by name**. **The travel router travels** → robots reconnect anywhere with no reconfiguration.

| Part | On the road? | Notes |
|---|---|---|
| Brain | ✅ laptop/Jetson | One install script. |
| Network | ✅ travel router | Venue Ethernet, venue Wi-Fi (repeater), or phone hotspot for internet. |
| Cloud AI | ✅ with internet | Otherwise **offline lite mode**. |
| GUI | ✅ any browser / Quest-only | |
| Voice | ⚠️ noisy places | Push-to-talk / Quest mic / phone mic. |
| Teleop demo | ✅ fully | USB. |
| Robots | ✅ those you bring | Arms/Jetsons/Pis need outlets. |
| Multi-screen presence, lab PCs/displays, local GPU models | ❌ lab only | |
| Trained policies | ⚠️ | New lighting/backgrounds; "look, then reach" (ER) generalizes better. |

**Rules:** venue profiles; no hardcoded lab addresses/machines; offline lite mode; ≤10-minute setup checklist; optional "live link to the lab" later.
**Remote levels:** (1) Claude Code via **Remote Control** — confirmed working; (2) GUI from home via a private overlay network (Tailscale; ask IT first; also for demos away from the lab with the brain left in the lab: `docs/plan/ideas.md`, 2026-11-11); (3) lab in a bag; (4) cellular robots (much later). **Safety:** remote mode = no motion by default; dead-man stop.

---

## Network plan (2026-10-22)
- Campus IT must register MAC addresses (lab Wi-Fi); no self-registration. **Slow in practice:** the Raspbots were emailed in ~2026-10-26 and still weren't on as of 2026-11-09 (IT tried; unclear why it failed). So no new device (Newline, Quest, Pis not yet registered) should depend on joining the lab Wi-Fi.
- Lab wall Ethernet port works (which network unknown); classmate in IT says IT doesn't watch for devices — still get the professor's OK.
- **Direction:** lab's own travel router uplinked by Ethernet to the wall port; brain on the router's side. Fallback: isolated router.
- **Router shortlist:** GL.iNet Opal ($39.99) vs Beryl AX ($98.99); pending (portability slightly favors Beryl AX).
- **Beryl AX (GL-MT3000) checked against our needs (2026-10-29):** builder's pick (Amazon B0BPSGJN7T, $98.99). Fits: pocket-sized, **USB-C 5V/3A (runs from a power bank)**; internet from wall Ethernet (2.5G WAN), venue/phone Wi-Fi ("repeater") or phone USB tethering, several at once with failover ("Multi-WAN"); robots always join *its* Wi-Fi, so changing the internet source never reconfigures them; keeps working with no internet (offline lite mode); OpenWrt underneath (DHCP reservations, local names); **Tailscale built in** (remote level 2; still ask IT). Limits: only **1 LAN port** (a small switch if more wired devices); pocket-router Wi-Fi range (one room); one user report of very slow USB tethering vs. repeater, and an older report of Tailscale subnet routes breaking on tethering → **use phone hotspot over Wi-Fi (repeater) first, USB tethering as backup**. To check: joining campus/enterprise Wi-Fi (eduroam-style logins) and hotel-style login pages as repeater. Security setup: strong Wi-Fi + admin passwords, remote admin off, a **separate guest network** (client isolation) for visitors' devices, robots on the main network. Still needs: the professor's OK + who pays.
- **Setup checklist:** passwords, remote admin off, DHCP reservations, auto-updates off, passwords stored safely, label, cable away from walkways.

---

## Robots without a Raspberry Pi (2026-10-22)
"Bridge" pattern (USB/Bluetooth/radio to a Pi 5, Jetson or the brain): TonyBot v1 (Arduino; USB serial or Bluetooth), xArm 1S (USB, Python `xarm`), Air:bit 2 ×3 (micro:bit radio; no spares; much later). Drones out of AI/voice/visitor control for now.

---

## Grill session answers (2026-10-20)
1. One thing this semester: most lab devices connected, AI agents able to access them. 2. For: primarily the builder. 3. MVP done: it connects and inspires continuing. 4. 3–7 h/week. 5. After May 2027: handoff docs; builder lives ~5 min from campus. 6. Professor: "connect devices for faster development." 7. Willing to learn Unity if needed. 8. Visitors: ~30 s in the headset. 9. Camera privacy deferred. 10. Worst failures → offline lite mode. 11. Auto-restart + AI diagnosis. 12. AI budget ≤ $20/month. 13. Modularity via AI; hardcode when needed. 14. Safety in the harness.
- **2026-10-23:** also **impress** → teleop fast track; visitor routes may not pass the lab → **must travel**; trained arm should **generalize** → "look, then reach" + pretrained models.

### The walk-in moment (2026-10-20)
Open the door → one trigger → screens on → greeting → use. Animation ≤ several seconds.

---

## Milestones (2026-10-23)
-1. **Repo scaffold** (docs/dev/project-scaffold.md "Day one").
0. **Fast track — teleop demo:** prototype on `xarm1`, polish on `so101-white`; portable from day one; then second act (ER "look, then reach" → SmolVLA).
1. **Milestone 1 — "Connected lab":** lab router, SSH keys + nicknames, device census, standards, one small visible win.
2. **Milestone 2 — Wake + roll call** (`xarm1`, then Raspbot); venue profiles.
3. **Milestone 3 — Voice + dev assistant.**
4. **Later:** offline lite mode; more robots; bigger VLA models (second act). Teleop demo showable 2026-10-30 (tag `demo-2026-10-30`). Current focus: the JARVIS hub (`docs/plan/current-focus.md`); the troubleshooting suite and the rest of the teleop polish are on hold (`docs/plan/ideas.md` → "On hold"). Everything else: `docs/plan/ideas.md`.

---

## Dev setup — details in docs/dev/dev-setup.md
Robots stay thin · Linux lab desktop with VS Code + Claude Code extension · Remote Control from home (confirmed) · cloud sessions only for pure-software work · ssh + rsync deploys · auto-restarting services · permission rules (ask before sudo, deletes, reboots, robot motion) · git as undo · fake robots at home, real hardware in the lab · private GitHub repo · one install script for desktop *and* laptop · CLAUDE.md points to docs/plan/current-focus.md and this log.

---

## Standards (to define on the ground)
To be decided on the ground, once the device census shows what the robot computers look like inside: user accounts on robots, one project folder per robot, where logs go and how they're named, venue profiles. **Device names so far:** `so101-green` / `so101-green-leader` (the training set, borrowed by lab-os since 2026-11-12), `so101-white` / `so101-white-leader`, `xarm1`, `xarm2`, `pi01`; starter names: `raspbot1`, `pi5-1`, `jetson1`, `quest1`; bridged robots named after the robot, with the bridge noted. **Already decided:** secrets in one local `.env` per machine, never in git; calibration files travel with each arm (`calibration/<arm>/`); principles and hacks as in CLAUDE.md; demos run from tagged known-good versions.

---

## The biggest risk: on-the-ground surprises
Past examples: a VLA not using its cameras; low success rates; too little RAM; no Wi-Fi card; Wi-Fi country codes, hotspot mode, MAC registration; a humanoid's voice silently broken; VS Code Remote-SSH unstable on the Raspbot; glove needing extreme gestures and snapping.
Handling: census first · thin robots · capability checks · prove inputs · log everything · spikes · gotchas file · expect 2–3× longer · updates off, versions pinned.

---

## Is it actually useful? (still partly open)
Primary: faster development via a connected lab. In the plan: teleoperation for teaching robots (and data collection for the lab's training project); **"put anything on the table and ask it to grab it"** (ER look-then-reach). Other possible uses are in `docs/plan/ideas.md` ("Uses, reach, events"). Unofficial; no outreach. ROS 2 optional.

---

## The full vision (2026-10-19/20)
Walk in → ignition (card, "hey Jarvis," button, keyboard, Quest) → screens on + short animation + greeting → optional Quest launch → ambient standby → commands by voice/push-to-talk/typing (fast path or agent harness). Works without the Quest, with the Quest alone, and away from the lab.
Modules in the plan: teleoperation; look-then-reach; phones/laptops as mics; offline lite mode; remote access (staged); portable kit. Further optional modules: `docs/plan/ideas.md`.

---

## Architecture sketch (2026-10-23)
- **Brain** = portable software. Robots find it by name.
- One standard message protocol for all clients.
- Modular core with slots: ignition · sign-in · inputs/mics (Quest controllers, hand tracking, leader arm, glove) · outputs/clients · cameras/vision · AI models (router; incl. robotics models like Gemini Robotics-ER and VLAs) · robots (incl. ROS 2, bridged, fake) · tools · personas · network/connection.
- **Venue profiles** decide which plug-ins are present/active.
- Modules connect slots (teleop = input → arm; look-then-reach = camera + robotics model → IK → arm), sharing control logic (calibration, clutch, smoothing, ramps, safety).
- Model router with fallbacks; two speeds (fast path vs. agent harness).
- Reliability: auto-restart; start on boot; offline lite mode.
- Safety: speed/workspace limits, always-working stop, approved visitor commands, remote mode = no motion by default, dead-man stop; drones excluded for now.

### Shapes to design toward (2026-10-24), not things to build now
- **Triggers slot** (generalizes "ignition"): everything that turns the system on or off is a plug-in: wake word, spoken phrases ("Jarvis, log out"), clap, card swipe, keyboard/button. Each can be switched on/off in config and per venue profile. *Why:* new activation methods keep coming; each should be a small add-on.
- **Conversation manager:** one component owns voice-conversation behavior (interrupting, queueing, turn-taking), so it isn't scattered across the code.
- **Theme file ("design tokens") + sound packs:** all visual style (colors, fonts, sizes, glow, animation speed, decorative intensity) lives in one config file (`config/theme.yaml`); nothing hardcodes a style. Sounds are a swappable **sound pack** with volume and mute. Later, a settings panel edits both. *Why:* full, easy control of look and sound from one user-friendly place. Sound sources: my brother (sound design), stock (check licenses), or AI-generated.
- **Decorative layer separate from the information layer:** decorative effects (3D, animated elements) have an intensity setting; useful information always stays readable on top.
- **Visual quality levels: full / reduced / minimal.** Can drop automatically when the frame rate falls. The Quest gets its own stricter performance budget (low frame rates in a headset cause motion sickness). Not the same as **offline lite mode** (no internet); keep the names distinct.
- **The brain doesn't need to be lightweight** (it runs on the desktop or a laptop); robot-side code stays thin, as already decided.
- **Agent changes to the system:** agent proposes on a branch → tests + CI → I approve → deploy from a tagged version. The agent never modifies the live running system directly. Same for system updates.
- **Agent harness is a swappable slot** (slow path). A Claude Code / Claude Agent SDK harness is one candidate (`docs/plan/ideas.md`): tools default-deny; any robot motion still goes through our safety layer.

---

## How it fits together (as built, 2026-11)
- **One brain program, `lab-os serve`.** It serves the hub and mounts the teleop pages inside it; the core grows out of the teleop code (decision 2026-10-24). `lab-os-teleop` keeps working until it's replaced.
- **The brain is an MCP server** (decision 2026-11-09): tools (read the arm, move it, `pose_view`, camera pictures, read the docs) in the standard format AI tools understand. Claude Code, Codex and Claude Desktop connect to it; the hub's own chat gets only the read tools. Tiers: "AI-assisted development" below.
- **The assistant's state is separate from its picture.** The state: `idle`, `listening`, `thinking`, `speaking`, `offline`, `error`, plus a 0–1 loudness while speaking. The rest of the system only sets the state; the picture is chosen by the persona and only reads it (`docs/dev/personas.md`).
- **The hub's buttons come from config** (`hub.modules` in the theme). No fake "coming soon" buttons. **The status strip and panels show only real facts.**
- **Offline vs. internet.** Offline: start screen, hub, the assistant's picture, teleop, sounds, theme, fonts. Needs internet: the AI chat and cloud voices. Without internet the assistant shows `offline` and everything else works.
- **A public screen** (the Newline, a hallway desktop): anyone can start it and talk to it, so the hub's chat stays in the read tier, the move tools only accept AI tools on the brain's own computer, a spend cap pauses the chat, the conversation clears on the reset, and a `public: true` venue hides internal details.
- **Starting, full screen, the reset, drawing resolution:** `docs/guides/hub.md`.

---

## AI-assisted development (direction, decisions 2026-10-30 and 2026-11-09)
Anyone working on lab-os can use AI to change the system **and** the connected devices (robots, Pis), without depending on one person's subscription. Two routes, same rules:
- **Bring your own AI tool:** a laptop with VS Code + the Claude Code extension, Codex, or Claude Desktop: clone the repo, connect the tool to the brain's MCP server (with a personal access token, once remote access exists).
- **Lab-paid harness in the hub:** a **"send to harness" toggle** on the chat line hands the request to a coding agent running on the brain with the lab's API key (Codex with the OpenAI key, or Claude Code with an Anthropic key if refilled). Monthly spend cap.

**Rules for both:** code changes only on a branch (`agent/<task>` for the lab harness) → tests → PR → the builder approves; never edit the running system. Device actions go through the brain's tools in **permission tiers**:
| Tier | Examples | Who |
|---|---|---|
| read | device status, logs, docs, arm readouts, camera snapshots | everyone, incl. the hub's built-in chat |
| act | "find me" beep, restart a service on a Pi, deploy a tagged version to a robot | developers with a token; asks first |
| move | anything that makes a robot move | developers on the brain's computer, through the safety layer; no asking per move since the 2026-11-13 decision (`docs/plan/quick-jobs.md` job 1); off in remote mode |
| admin | `sudo`, deleting, reboots | humans only, never through tools |

The hub's built-in chat stays in the read tier (anyone in the room can type into it). Realistic workflows: `docs/plan/use-cases.md`. Built so far: the read and move tiers on this computer (focus steps 2, 3, 6); tokens, the act tier and the harness wait (`docs/plan/ideas.md` → "Brain as an MCP server", "Coding agent").

---

## Decisions
| Date | Decision | Why |
|---|---|---|
| 2026-11-13 | **The AI's arm moves no longer ask.** The four move tools go on the repo's allow list (`.claude/settings.json`), for everyone. The per-move limit, the speed cap and the floor can each be turned off (the venue file and the Settings page; on by default; not on public or visit-day venues). Always kept: STOP on every screen, the soft joint limits, one controller at a time. The hub's own chat may move the arm one day (`docs/plan/ideas.md`). Built by `docs/plan/quick-jobs.md` jobs 1–2. | The builder, after the first real cube pick: asking before every move was in the way, and STOP is enough when it does something it shouldn't. |
| 2026-11-13 | **The floor is −0.5 cm** (was 1 cm), for the AI's moves and teleop. | The SO-101 stands on the overhead camera's base now, so the table is below its zero; 1 cm made some things impossible to grab. |
| 2026-11-13 | **"Screens" are "devices"** (step 8): each device has a name and its own settings (the way in to voice, drawing resolution), with its monitors inside (a desktop with two monitors is one device; "open on desk" picks a monitor). Address: `/?device=desk`. | "Screen" sounds like a monitor; the settings belong to the device. |
| 2026-11-13 | **The spoken greeting is a saved recording per voice** (fixed text: time of day + the hint, no news line), made once, then played without a voice request. | Fewer requests on the free key (only ~10 speech requests a day per model). |
| 2026-11-13 | **The docs go into folders by who reads them** (`docs/plan/`, `docs/guides/`, `docs/dev/`, plus `design/`, `device_manuals/`, `archive/`), and **`docs/plan/quick-jobs.md`** lists small decided jobs a Claude session can build any time. | The builder: easier to find things; quick sessions now and then. |
| 2026-11-12 | **Step 11 as built: "borrowed" devices.** The green arms and cameras are `borrowed: true` in `devices.yaml` (not `off_limits`): drivable, but `so101_setup` refuses them (by name and board serial), never a command-line default, carried to every place like off-limits ones. Calibration `calibration: lerobot`: LeRobot's file copied into a temporary folder, LeRobot only sees the copy. Every SO-101 port and camera is checked for other programs (`/proc`, `lsof`) before opening, white ones too. Cameras by `socket:` (`usb-0:7`), named `so101-green-cam-a`/`-b` until it's known which sees what. | The four rules enforced in code, not only in docs; the copy makes "read only" structural; one check for every port keeps it simple. |
| 2026-11-12 | **The green rules are loosened:** lab-os may drive the green arms and use the training cameras (the camera-model block goes). Kept: no motor ID/firmware changes, calibration read-only, the `lerobot` env untouched, never a port that LeLab or a training run is using. Code, config and hook change in focus step 11. | The builder: too strict; the green set is the builder's own, the first VLA round is done, and LLMs/VLMs (and Physical Intelligence's API) are worth trying on it. |
| 2026-11-12 | **Demo of every feature on Thursday 2026-11-19** (the builder has assignments due Wednesday; ambitious: everything). Step 9 done with `/design`; step 1 done, the Newline its own item (step 12); the design is no longer a surprise, but `/` stays plain by default. | The builder. |
| 2026-11-12 | **Voice fast-tracked:** the first version on the free Gemini key (OpenAI when the professor's key comes; a config change) and a USB microphone on the brain desktop. **Demos happen on the desktop's own screen** until the Newline shows the hub smoothly. | The builder: easy to start; the Newline's refresh rate is unresolved. |
| 2026-11-11 | **Teleop 1:1 keeps up with the hand:** in 1:1 the Speed slider and the venue's `max_speed_scale` don't apply; each joint is capped at the venue's `one_to_one_max_deg_per_s` instead: **180°/s in the lab** (about 2/3 of the STS3215's rated no-load speed, ~270°/s at 12 V, ~310°/s at 7.4 V), adjustable down or to `none` (the servos' own top speed) in ⚙; **off** on visit days and at new places. Servo temperature, load and voltage are logged every 5 s (`logs/servo-health/`); a servo at 60 °C slows 1:1 to relative speed. **Relative stays the default** until the logs and the feel say 1:1 is fine for the motors. | The builder: waving should make the arm wave, as fast as the hand, within a known-safe limit. No published "safe for wear" speed exists; LeRobot's own leader-follower teleop runs these servos with no software cap at all. Heat and shock loads are what wear them, so measure. |
| 2026-11-11 | **Voice's way in is chosen per screen** (push-to-talk by default; dictation or the wake word where the screen can), and **voice in and out happen at the screen the person is at**, with its own microphone and speakers. **A USB hub for the white cameras** (shopping list); camera serials only if Innomaker has a tool. | The builder: nobody should walk to the desktop to talk; identical cameras need fixed sockets and sockets are scarce. |
| 2026-11-11 | **Push-to-talk is voice's default; dictation can be a screen's default instead. The wake word is built with voice** (works from anywhere in the room, local detection, a subtle sign separate from the core's `listening` state). | The builder: browsers are wary of always-on microphones; the wake word belongs with voice. |
| 2026-11-11 | **Voice adds a spoken greeting** after the jump when voice is on, and **dictation** is wanted (tap the mic, the words appear in the ask line as you talk, it stops on silence or a second tap, then you send it). Both in focus step 7. | The builder: so people know it can speak; dictation like Claude Code's microphone. |
| 2026-11-10 | **The designed hub keeps one tap** (full screen + start in one); to leave it waiting full screen, press ⏻. The plain hub keeps its two taps. | The builder: "that might be fine, since i can just use the power button to reset it to idle". |
| 2026-11-10 | **This week's order (until Fable ends 2026-11-16):** the honest "arrived", `pose_view`, the full-screen button, a drawing resolution per screen and teleop's 1:1 mode (no lab), then a lab day (Fable on the real arm, the camera sockets, the training launcher, `/perf` on the Newline), then cameras (step 3), then voice (step 7). **A full-screen button** on the hub and every page, shown while not full screen. | Real-arm AI runs while Fable lasts. Something can always leave full screen (a swipe, a pop-up), and the designed hub doesn't go back to tap 1. |
| 2026-11-10 | **The Newline: measure, then lighten,** keeping the look where possible (lower drawing resolution, cheaper effects); the desktop + a 32" monitor is the close second; maybe a very light but still "wow" look for the Newline and portable screens. No extra computer on its HDMI for now. | Laggy even at `reduced`, from the laptop and the desktop too (the builder), so the screen itself is the suspect. |
| 2026-11-10 | **Teleop gets a 1:1 mode:** after lining up the 3D arm on the real one, the gripper follows the hand at the same distance; the relative mode stays as a choice. | With hands and controllers the arm drifts away from the hand (0.5× scale, slips at the table and the limits), so the builder keeps re-clutching. |
| 2026-11-10 | **The hub in VR gets buttons:** after the jump, a few big buttons around the core you point at; Teleop opens the arm scene without leaving VR; the jump polished to match the main hub. | `/xr` was watch-only and the trigger replayed the jump: no way into the system from the headset. |
| 2026-11-10 | **One click starts the SO-101 training setup on the lab desktop** (`lab-os green`: a desktop icon and the hub's Training page): a port check (both green arms, nothing else on a serial port, LeLab's saved ports = the green ones, not swapped since the last start), then LeLab. lab-os itself still never opens the green ports. | Builder: "a one-click way to open the VLA training (greens) environment and boot it … warn the user and don't proceed" if the ports aren't right. LeLab saves raw `ttyACM` names, which the white arm can take. |
| 2026-11-10 | **Other computers can be allowed to drive a real arm** (`lab-os serve --drive-from pi01.iwu.ai.lab`); without it they stay view-only. | Builder: "i'm in control of them too, so it should be safe". |
| 2026-11-10 | **The concept's "Arm" view became AI Control (`/ai`):** the arm from its side (real geometry from the kinematics), where the last move aimed, every robot-tool call live, STOP. | Builder asked what the Arm module was for: it was a second, simpler monitor. Watching what an AI does with the arm (and stopping it) is what the lab needs while Fable drives it. |
| 2026-11-10 | **A settings page** (the hub's ⚙, `/settings`): `src/lab_os/settings.py` lists the settings (a module adds its own section); changes are written into the config files with their comments kept, only from the brain's computer; "This screen" (level of detail, sound, full screen) is per browser. | Builder: "a configuration interface for all the configs … that grows with more modules". Files stay the source of truth, so a change is an ordinary, reviewable config edit. |
| 2026-11-10 | **Teleop and monitor redesigned in the hub's style;** the plain pages kept at `/classic/teleop`, `/classic/monitor`. Same element ids and scripts, so the logic is shared. | Builder: better layout, and a fallback if the new ones break. |
| 2026-11-10 | **The secure address (`hub.indwesailab.com`) is deferred:** voice and the rest are built as a complete proof of concept on plain `http://` (the brain's own screen on `localhost`; Chrome's insecure-origins flag on other screens); the domain + certificate become an extension later. | Builder: getting the subdomain means the professor working in AWS and the builder setting up DNS and the certificate, more than it's worth before the system is shown. Full screen works on `http://` anyway (it only needs a press). |
| 2026-11-10 | **The design is built now, as a preview at `/design`;** `/` stays plain until `hub.look: design` in the theme. | Builder: wants to show the vision (startup, graphics, features) this week; "it doesn't need to 100% work". A separate address keeps the surprise in the builder's hands. |
| 2026-11-10 | **A real arm can be served to the network, with other screens view-only:** input pages from other computers are watchers (their STOP works); only the brain's computer (and the Quest over `adb reverse`) drives. | So the Newline can show the hub while Fable drives `so101-white` (step 2's "Other screens while a real arm is connected", already decided). |
| 2026-11-10 | **The venue's persona is back, as the venue's default:** order `--persona` → `$LAB_OS_PERSONA` → the venue's `persona:` → the place's `persona:` → `lab-assistant`. Every venue starts at `persona: default` (= the place's) until someone changes it. | Builder: a venue may want its own persona, but nothing should be forced by the venue. |
| 2026-11-10 | **Voice route (prepared, not built):** swappable voice setups in `config/models.yaml` like the chat's; the speech-to-text → chat → text-to-speech pipeline for everyday use (OpenAI's mini models once the key is there), a realtime service for demos or when speed matters (the builder: "you pay for speed"; thinking out loud, not a hard rule). Open: which key pays, the professor's OK for `hub.indwesailab.com`, the microphone. | Reuses the chat's persona, tools, history and spend cap; about $0.003 per question; realtime only where its speed is worth the price. |
| 2026-11-10 | **The persona isn't tied to a venue:** `persona:` moved from the venue profiles to `place.yaml`, with `--persona` and `$LAB_OS_PERSONA` to override it. | Builder: who the assistant is and how cautious a place is are separate choices. |
| 2026-11-09 | **Robot tools for AI, details (focus step 2):** MCP on `127.0.0.1:8081/mcp` only, in the brain's process. Moves run as a "motion" in the teleop loop (AI has control only while its move runs). Per call: at most 30° per joint (the gripper exempt) or 10 cm, bigger requests go part of the way and say so; nothing below 1 cm above the table; `move_to` follows a straight line. Limits per venue (`ai_tools`), named poses per arm model (`config/poses.yaml`). In Claude Code: read tools and `stop` allowed without asking, move tools are "ask" rules in the project settings. | Small, checkable steps with a human approving each; stopping must never wait for a click. |
| 2026-11-09 | **Plain hub built (focus step 1):** modules open in an `iframe` inside the hub page (the hub hears their keys and taps for Esc and the reset); under `lab-os serve` the teleop page moves to `/teleop` (`lab-os-teleop` keeps `/`); `lab-os serve` listens on this computer only, and `--host` for other screens is allowed **only with a fake arm** (changed 2026-11-10: a real arm too, other screens view-only). Theme ids without a page (`arm`) get no button. | No page load keeps full screen; existing pages work unchanged inside it; nobody on the network can drive a real arm through the hub. |
| 2026-11-09 | **The brain is an MCP server; the hub keeps a small fast chat; a "send to harness" toggle (+ a send-everything setting) hands requests to a coding agent.** Tools are defined once and grouped in **permission tiers**: read (everyone, incl. the built-in chat), act and move (developers with a token; move through the safety layer, asks every time), admin (humans only). | One set of tools for every AI; quick questions stay fast and cheap; anyone at the screen can't change things. |
| 2026-11-09 | **Two routes for AI-assisted development, same branch → tests → PR → approval rule:** (1) bring your own tool (laptop + VS Code with Claude Code / Codex / Claude Desktop + repo + the brain's MCP tools); (2) a lab-paid harness on the brain with the lab's API key (Codex with the OpenAI key, to verify), with a spend cap. | Most students have no subscription; the system shouldn't depend on one person's account. |
| 2026-11-09 | **AI driving a robot arm moves into the current focus** (steps 2–3, right after the plain hub): the brain's MCP server with move tools for `so101-white`, driven by Fable 5.2 in Claude Code (the builder's access ends 2026-11-16), blind first, then the white arm's two cameras. Move tools: localhost only, same safety layer as teleop, clip and refuse, one controller at a time, ask every time. The green arm stays off limits. | Use the Fable access while it lasts; it starts the "LLMs/VLMs driving the arms" goal on an arm that's ours. |
| 2026-11-09 | **The hub design is approved** (`docs/design/`: DESIGN.md, hub-concept.html, theme). The startup is designed (old prototype step dropped); it takes **about 8 s including the unlock**, skippable with any input. The greeting = time of day + one line of real news built by the brain, else the persona's plain line; the startup title is the lab's name (`hub.title`), not a persona line. Fonts are bundled (offline). | The concept page is the spec; real facts only. |
| 2026-11-09 | **Plain first, the design as a surprise reveal.** Phase 1 (focus steps 1–8, now 1–9): everything works on deliberately plain pages that copy the concept's structure but not its looks, until teleop, the AI driving the arm and voice can be demoed. Phase 2 (step 9, now 10): the full design in one 1–2 hour sitting, then the hub is left at its start screen on the Newline or a desktop for someone curious to start. **Voice moves from stretch to required.** | The builder wants the design to be a surprise (people see the screens while work happens); demo-able features first. |
| 2026-11-09 | **Two taps on the start screen:** tap 1 = full screen (the idle screen itself; skipped when already full screen), tap 2 = start. **After ~3 min with nobody (30 min since 2026-11-10), back to the start screen** (modules closed, conversation cleared; never while teleop, an AI move or a voice turn runs). **Hyperspace is the default startup**; `assemble` and per-venue are the other settings. | The hub is left full screen on a public screen for someone curious; the next visitor should get the startup, not the last visitor's chat. |
| 2026-11-09 | **Voice on any screen; the brain gets a real HTTPS address** (the address deferred 2026-11-10, see above): a subdomain of the lab's `indwesailab.com` (e.g. `hub.indwesailab.com`) pointing to the brain on the lab network, with a free Let's Encrypt certificate via a DNS check; the router answers the name locally for offline use. Fallbacks, easiest first: localhost on the brain's screen, Chrome's insecure-origin flag, `adb reverse`, our own certificate authority; with no secure page or no microphone, voice is hidden. The page records and plays; the brain talks to the voice service (keys stay on the brain). | Browsers give the microphone (and Wake Lock, app install, WebXR) only to secure pages; one certificate makes every screen work with no setup per device. |
| 2026-11-09 | **Opening a module on another screen comes before the reveal** (focus step 8, the reveal is now step 10), with **one tap or click to open the hub on any screen, nothing starting by itself** (screens, the Newline above all, are used for other things; lab-os uses nothing where it isn't open): a shortcut per screen with its name in the address (`/?screen=newline`), and the brain updating `hub.indwesailab.com` in Route 53 to its current address until the router gives it a fixed one (deferred with the secure address, 2026-11-10). | The devices are switched off every night, so nothing may depend on someone typing an address, and nothing may take over a screen; the builder wants screen-to-screen in the demo. |
| 2026-11-09 | **One brain per network:** the brain runs on any computer, but if one is already on the network a new one doesn't start, and when two meet later the later one closes (safely: never mid-move). A `--second-brain` development option. **Nothing place-specific in code:** lab name, domain, devices, off-limits list, venues and personas in config; another place (the builder's home, other people) = another config folder. Only the lab's brain updates `hub.indwesailab.com`. | Builder: start the brain on any computer without two fighting; reuse lab-os at home and elsewhere. |
| 2026-11-09 | **Places, as built:** place files (`place.yaml`, `devices.yaml`, `venues/`) come only from the place's own config folder; shared files (theme, poses, later models and personas) fall back to the repo's `config/`; the repo's `config/` is the lab. **The repo's off-limits devices are added at every place.** The hub title is `name` in `place.yaml`. | A home brain must never claim to be the lab or drive the lab's devices; and switching folders on the lab desktop must never unblock so101-green. |
| 2026-11-09 | **Typed chat, as built:** plain aiohttp against the OpenAI-style chat interface (no vendor library); `main` = OpenAI `gpt-6-luna` (cheapest current OpenAI model, $0.10/$0.50 per 1M), `backup` = Gemini `gemini-3.5-flash-lite` on the free key (3.8 Flash was overloaded on the free tier), `local` = Ollama. A missing key falls back to `backup`; an error never switches silently. Monthly budget per place (`ai_budget_usd_month`, $20 at the lab); spend logged per place. | Same code for every service; the budget stays ≤ $20/month; a home brain's spend never counts against the lab's. |
| 2026-11-09 | **Personas, as built:** re-read on every request (switching = edit + reload, no restart); a broken or unknown persona falls back to `lab-assistant`. Greeting news so far: step finished (today/yesterday) → `calendar` in `place.yaml` (two weeks ahead) → busy day (≥ 10 commits); the greeting is also the conversation's first message. visit-day uses `jarvis`. | Plan step 4; the news comes from real facts only. |
| 2026-11-09 | **Project helper, as built:** one MCP server in the brain; its read-only tools (project docs, git, devices, `arm_status`) also go to the hub's chat in-process, filtered by the read-only annotation plus a never-list (move tools, `stop`). **`docs/design/` is not served** by the project tools until the reveal. Read tools may be allow-listed in Claude Code; move tools never. | Anyone at a hub screen can ask the chat: it must not reveal the surprise design or move anything. |
| 2026-11-09 | **Time box: the reveal by ~2026-12-04** (semester ends 2026-12-15, finals the week before). Build order 1 → 2 → 5 → 7 → (3, 4, 6, 8) → 9 → 10; all steps stay in. | The project may end with the semester; lab testing, not coding, takes the calendar time. |
| 2026-10-30 | **AI provider: OpenAI first; free Gemini as backup; local models as a second setup.** The chat speaks the OpenAI-style interface so OpenAI, Gemini and local servers (Ollama / llama.cpp) differ only by config. The Anthropic key is out of credits; coding-agent candidate changes accordingly (OpenAI Codex, or Claude Agent SDK if refilled). | Where the keys are; one interface keeps the model router simple and makes offline chat possible. |
| 2026-10-30 | **Focus = the JARVIS hub first** (supersedes the core-plumbing order of the earlier 2026-10-30 entry): `lab-os serve` → hub page → personas → the assistant's picture → startup prototypes → real startup → typed chat → read-only project helper → voice (stretch). Roll call, plug-in descriptions and robots reporting in wait for the router (`docs/plan/ideas.md` → "On hold"). | The builder wants the system itself first; most core plumbing is easier with the router at hand. |
| 2026-10-30 | **The assistant's state is separate from its picture.** States: idle / listening / thinking / speaking / offline / error (+ loudness). Pictures are per-persona decorative renderers (plain circle first; inspired orbs and VRM characters later; no brand assets; Live2D dropped). | New looks never touch the conversation code; quality levels come for free. |
| 2026-10-30 | **Personas are files in `config/personas/`** (versioned; unknown fields kept with a warning, so the format can grow). Fields: id, display name, personality text, model setup, voice, wake word, picture, lines (show names), sound pack. **Default persona: a plain "lab assistant"**; `jarvis` is the show persona, chosen per venue (changed 2026-11-10: per place or per run, not per venue). The theme stays the same across personas. | Extensible without code changes; "JARVIS" needs no explanation if it isn't the default. |
| 2026-10-30 | **Hub = one full-screen browser page served by `lab-os serve`, on a 32" monitor first.** Module buttons come from config; the status strip shows only real facts; startup begins with a key press/click (unlocks browser sound), shows only real checks, is skippable. Typing first; voice when typing is solid. | Same tech as teleop; offline; honest. |
| 2026-10-30 | **Coding agent direction:** works like Claude Code but paid by the lab's API account (Claude Agent SDK if the credits are Anthropic's); works only on `agent/<task>` branches → tests → PR → builder's approval. This focus: read-only helper that answers and drafts Claude Code prompts. | AI-assisted development that doesn't depend on one student's subscription; keeps the agent-changes rule. |
| 2026-10-30 | **Teleop demo focus closed: showable as is, "needs polishing"** (`so101-white` driven from the Quest controllers through IK at `--speed 0.2`; tag `demo-2026-10-30`). Unfinished steps (hand tracking, speed, Quest display, visitor polish), the leader arm and the xArm leftovers are **on hold** in `docs/plan/ideas.md`. **Next focus: the JARVIS core** (brain + plug-in interfaces, roll call), ahead of the troubleshooting suite; network parts wait for the lab router. The old focus is in `docs/archive/`. | Builder's call: good enough to show; the core is what they want next, and most of it needs no router. |
| 2026-10-28 | **Naming: plain names in code and docs; show names live in persona/theme config.** A **plain name** says what a thing does and is used in code, file names, docs, logs and commit messages (e.g. `startup_sequence`, "roll call", "troubleshooting suite"). A **show name** is the in-character name JARVIS *displays or says* to people (e.g. the startup screen's title "INITIATION", the spoken line "Initiating systems…", a mode called "Overwatch"). Show names are text in the persona/theme config (`config/`), so they can change, or differ per persona, without touching code. Code never depends on a show name. Things get a show name only after they exist and run. | Plain names stay searchable and obvious to the next student; the JARVIS flavor stays fully customizable. |
| 2026-10-28 | **Robots are optional at startup:** by default the system assumes no robots are on; a robot that gets switched on appears in the system when it reports in. A "power-up walk" (expected devices shown dim with instructions) is an optional demo mode. | Often the builder only wants to code or ask something; robots are for projects, learning and demos. |
| 2026-10-28 | **One device controls a robot at a time; control is handed over** (the current driver releases), not grabbed; everyone can watch; STOP works from every device. Teleop gets this first (teleop focus step 6b, done 2026-10-29). | Two inputs interleaved on a real arm is unsafe; handing over is the safer choice. |
| 2026-10-28 | **No ghost arm lined up on the real arm** (changed 2026-11-10: the Quest's 3D arm can be moved onto the real one by hand, left grip). The Quest shows a lazy-follow **HUD mini-arm** (what was commanded; joints turn red near limits) instead; the status panel also lazy-follows instead of being fixed in the room. | Lining up needs calibration and adds little: the real arm is visible; a fixed-in-room panel is awkward. |
| 2026-10-28 | **"AI lab admin" is the lab's one Meta account** for all current and future Meta devices/platforms (owns the 3 Quests; joins a Meta developer organization for developer mode). Verified with **the professor's phone number** (his OK, 2026-10-28). Handoff docs record the account and whose number is on it; the password lives in the lab's password store, never in git. | Developer mode needs the owner account to be a verified developer; any future Meta product hits the same issue; a lab-owned identity survives the builder's graduation. |
| 2026-10-27 | **xArm driver = our own ~100-line protocol layer over the `hid` package** (not the `xarm` PyPI wrapper); read-only by default, motion needs `allow_motion=True` + the builder's OK. `devices.yaml` entries may carry `usb:` (vendor/product ID, product, serial); `find_usb_device()` resolves them; so101-green is also blocked by USB serial (any OS path containing it is refused). | Cross-platform lookup by USB ID + serial; the wrapper is unmaintained; see GOTCHAS for the hidapi-vs-hid trade-off. |
| 2026-10-27 | **The brain is cross-platform: Linux (primary), Windows and macOS.** USB devices are identified by USB ID + serial number (resolved to the OS's own path at run time), not only `/dev/serial/by-id/`; the so101-green block works by its serial numbers on every OS. Robot-side code stays Linux. Needs: a non-bash install path, CI on all three, the safety hook made OS-aware. | The field laptop could be anyone's (Linux, Mac, mostly Windows); both Ubuntu desktops are busy with other projects. |
| 2026-10-24 | **Ideas live only in `docs/plan/ideas.md`** (single source of truth); new ideas go there, not into code, unless they're the current focus. Earlier idea lists moved there. | Keep the project finishable without losing ideas. |
| 2026-10-24 | **Triggers slot:** every on/off method (wake word, phrases, clap, card, button) is a plug-in, switchable in config and per venue. | New activation methods keep coming; each should be a small add-on. |
| 2026-10-24 | **Conversation manager** owns interrupting, queueing and turn-taking. | Keep voice-conversation behavior in one place. |
| 2026-10-24 | **One theme file (design tokens, `config/theme.yaml`) + swappable sound packs** (volume, mute); nothing hardcodes a style; a settings panel later. | Full, easy control of look and sound from one place. |
| 2026-10-24 | **Decorative layer separate from the information layer**, with an intensity setting; information always readable on top. | Rich JARVIS / cyberpunk visuals without hurting usability. |
| 2026-10-24 | **Visual quality levels full / reduced / minimal**, auto-drop on low frame rate; stricter Quest budget. Distinct from offline lite mode. | Headset frame drops cause motion sickness; slower machines still work. |
| 2026-10-24 | **The brain need not be lightweight**; robot-side code stays thin. | It runs on a desktop or laptop. |
| 2026-10-24 | **Agent changes (incl. system updates) only via branch → tests + CI → my approval → tagged deploy**; never the live system directly. | Same safety net as human changes. |
| 2026-10-24 | **Agent harness (slow path) is a swappable slot**; Claude Code / Agent SDK is one candidate (tools default-deny; motion via our safety layer). | Reuse a capable agent without giving up control. |
| 2026-10-24 | **Next focus after teleop: troubleshooting suite** (superseded 2026-10-30: the core, then the hub) (mic, cameras, robots, network, accounts, Quest; each check writes a report). | Health checks will find problems; diagnosis must be easy for me, a maintainer or an agent. |
| 2026-10-24 | **3D arm view with three.js + urdf-loader, vendored in the repo (no CDN); SO-101 drawn from its real URDF, xArm from primitives. All arms share joint names (`shoulder_pan` … `gripper`, degrees); each driver maps them to its servos.** The view draws per-command driver input (`arm_command` messages), not a sampled state. Model code is page-independent so it becomes the Quest ghost arm. No physics yet. | Offline/venue-proof; exact testing at home; one model reused on desktop and in the headset. |
| 2026-10-24 | **Teleop input = plain HTML/JS WebXR page served by the Python program (aiohttp), WebSocket JSON messages (`docs/dev/protocol.md`); Quest reaches it over USB via `adb reverse` + `http://localhost:8080`.** No Node.js yet. First mapping is joint-space with clutch control; after any freeze the grip must be released and pressed again. JARVIS core grows out of this code rather than being designed up front. | Fewest moving parts; works at home via emulator + record/replay; localhost is a secure context for WebXR. |
| 2026-10-24 | **lab-os gets its own uv environment** (Python 3.12, uv-managed only); LeRobot for `so101-white` is added to lab-os, never to the shared `lerobot` conda env. **Serial devices are referenced only by `/dev/serial/by-id/`.** `so101-green`'s ports are off limits in code (`config/devices.yaml` + `lab_os.devices`) and via a Claude Code hook. Repo commits authored as JoshuaCYin; pushes use the lab `gh` login. | The conda env and green arm belong to the training project; `ttyACM` numbers swap between boots. |
| 2026-10-23 | **Second act = "look, then reach" with Gemini Robotics-ER 2 (API preview) first, then SmolVLA fine-tuned on our teleop data; bigger VLAs (GR00T, π0.5) only via rented GPU later; ACT only as a learning exercise.** | User wants generalization; ER generalizes without training; SmolVLA is the best-documented SO-101 route. |
| 2026-10-23 | **Repo scaffold per docs/dev/project-scaffold.md before feature work** (short, solo-sized); LICENSE after asking the professor (private until then); always demo from tagged known-good versions. | User wants Claude Code to include what a good project needs. |
| 2026-10-23 | **The full system must be portable** (laptop brain, travel router, venue profiles, no lab-only assumptions, offline lite mode, ≤10-minute setup). | Visitor routes may not pass the lab. |
| 2026-10-23 | **Quest teleop inputs: controllers first, then hand tracking; keep both.** Display = passthrough + minimal overlay. | Steadiness + clutch vs. wow. |
| 2026-10-23 | **Prototype teleop on `xarm1`; polish + second act on `so101-white`; teleop doubles as data collection for the training project.** | Smoother/LeRobot-native vs. available today. |
| 2026-10-23 | **Teleop requirements from the glove test; glove fix optional.** | Glove findings. |
| 2026-10-23 | **Arm names by color; `xarm1` = JARVIS-track robot + teleop prototype; `xarm2` spare.** | Clarity; separate hardware per track. |
| 2026-10-23 | **Remote Control from home confirmed; develop at home against fake robots; private GitHub repo.** | User verified; most of the system is software. |
| 2026-10-23 | **Teleop module added and fast-tracked; priority in docs/plan/current-focus.md; built on the seams with labeled hacks.** | Impress with fewest moving parts. |
| 2026-10-22 | Brain is portable software; remote access in stages; remote mode = no motion + dead-man stop; professor's OK before leaving a router on the wall port; wired uplink with brain on the router's network; router shortlist (pending); ask professor/IT and plan to pay; lab router replaces per-device registration; non-Pi robots via bridges; drones out of AI control. | 2026-10-22 discussion. |
| 2026-10-20 | Dev setup; standards on the ground; primary user = builder; Milestone 1 = connected lab; short animation; one client protocol; 30-s visitor demo; offline lite mode; updates off; auto-restart + AI diagnosis; ≤ $20/month; handoff docs; camera privacy deferred; professor handles IT; Quest-only + Quest vision modules. | Grill session and follow-ups. |
| 2026-10-19 | Census + capability checks; ROS 2 optional; no outreach; paper kept separate; Claude Code only on the brain desktop; SSH + deploy + one repo; phones/laptops as mics; ignition options; Quest optional; typing + push-to-talk; modularity core; model router; trained wake word; agent harness + fast path; face recognition opt-in; ~90% target; Raspbot first; config files; cloud first; keys never in git; thin-client station; reuse old spec principles. | Earlier discussion. |
| 2026-10-15 | One Linux brain + backup; 32" ViewSonic display; ~~no new router~~ (reversed 2026-10-22); few extra things; drop retro gear/camera-on-arm/live training/escape room. | Earlier discussion. |

---

## Facts about the lab
- **Status of the project (builder, 2026-11-09):** unofficial: nobody has been told yet, it may turn out useless, and it may not continue past this semester. It's about seeing what's possible. So: demo-able pieces first, cheap, nothing others come to depend on, and docs good enough for a future student to pick up.
- **Usage pattern (2026-10-28):** the lab is usually empty; startup happens when the first person arrives to a closed lab. Robots are off before that (battery-powered ones must be switched off); all need a physical switch, except the SO-101s (no switch; wall power supply).
- **Room:** desk clusters; side room with counter, SO-101 arms, beanbag; laggy big screen; projector; 32" ViewSonic monitors; noisy (fans); 3rd floor; setup movable; IWU. Visitor routes may not pass the lab.
- **Equipment check (2026-10-30):** the lab has most of the demo kit (cables, adapters, extension cords; boxes + a trolley for transport). Also a **Kinect** (version to check) and a spare webcam (the two Innomaker cameras belong to the training project). **To buy:** USB-C power bank (router/field use); **a powered USB hub (7 ports) for the brain desktop** (2026-11-12: all 7 USB-A sockets are taken: keyboard, mouse, the green cameras and arms, the xArm; the white arm + cameras need 4 more) (added 2026-11-11: identical cameras can only be told apart by socket, and the desktop's sockets are limited); **stronger table clamps** (the SO-101s' thin ones are only just sufficient). **Later, not urgent:** better cameras for lab-os (second act). Router: see Network plan.
- **Displays/wearables (2026-10-27):** 3 small (~7–9") Raspberry Pi touchscreens; a ~75" Newline touchscreen on wheels (standalone, runs Android); Google Glass Explorer Edition (boots, voice commands work).
- **Computers:** 6 RTX 5070 desktops (12 GB GPU memory, to confirm; 2 Ubuntu → brain + backup, 4 Windows 11); 5 Jetson Orin Nano; several Pi 5s; 7 ThinkCentres (no Wi-Fi; 4 at the front on two desks, 3 at the back; all unused, 2026-11-11). Remote Control from home works.
- **Network:** lab Wi-Fi with MAC registration via campus IT; wall Ethernet port works.
- **Domain:** the lab owns `indwesailab.com` (bought summer 2026 for one year: renew by summer 2027 or the certificates stop). The university didn't want it as the lab's public face, so only a subdomain is used, for lab screens. **DNS is on AWS Route 53** (checked 2026-11-09: the domain's name servers are `awsdns`); the builder has the AWS login (set up with the professor, summer 2026). The main domain still serves an old public website from S3 that was never removed; the `hub.` subdomain doesn't touch it.
- **AI access (updated 2026-10-30):** OpenAI keys (primary; the professor's account, paid by the university: believed 2026-11-09, not confirmed); free Gemini keys (free tiers may use data for training: check terms); the Anthropic key is out of credits (Gemini Robotics-ER 2 preview is on the Gemini API).
- **Mics:** 4 weak USB dongle mics; phones/laptops; old Nokias/Pixel C; Quest mic + speakers.
- **Robots:** Raspbot v2 ×2; SO-101 green set (the training project's); SO-101 white set (lab-os's, built); xArm 1S ×2 (`xarm1` works); Hiwonder glove ×2; TonyBot v1; PiCar Pro ×3 (unbuilt); Air:bit 2 ×3; Quest 3 ×3; card reader. No wheels+arm robot.
- **Earlier Raspbot work (the builder's, before lab-os):** voice control on a Raspbot: press a button on the IR remote and speak; after 3 seconds it transcribes the speech, and if it hears a known word (forward, backward, left, right) it moves a little that way. Not part of lab-os (where its code lives: to note).
- **Builder:** CS student; learns with AI; Python + web; dislikes the CLI, likes VS Code + Claude desktop/web UI; 3–7 h/week; graduating May 2027; lives ~5 min from campus.

---

## Open questions
- **Second act:** can the Kinect's depth camera help "look, then reach" (3D position directly, less camera-to-table calibration)? Which Kinect version, and does it run on our OS? ER pointing accuracy with our camera; camera-to-arm calibration method; ER preview pricing/free-tier limits and data terms; ~~SmolVLA training on 12 GB~~ (works: ~8 GB with the VLM frozen, 2026-11); cloud GPU option/cost for bigger models.
- **License/ownership:** what does the professor/university allow?
- **Portability:** which laptop is the field brain; venue internet; batteries vs. outlets; where visitor routes go.
- **Teleop spikes:** `xarm1` speed/delay; Quest WebXR data, overlays, USB forwarding (Quest developer mode / Meta account access); IK library; `so101-white` calibration; end-to-end delay.
- **Glove** firmware source; **training project** plans for `so101-white`; **IT/professor** router questions; overlay network; cellular.
- TonyBot v1 board; wake word from the doorway; waking screens; Quest camera access; Quest-only practicalities; past Quest demo contact; offline lite mode contents; use cases beyond development; mic test; agent harness; free-tier data terms; Raspbot internals; humanoid SDK. (Answered since: HTTPS → current-focus step 7; model router → `config/models.yaml`; persona names → `config/personas/`; voice pipeline → step 7's route.)

---

## Discussion notes & considerations
- **Generalization reality:** no robot model is magic yet; "look, then reach" generalizes for simple pick-and-place; learned skills generalize better with varied training data and pretrained models.
- **Portability rule of thumb:** anything tied to a specific room, computer or address won't travel; anything defined by a name, profile or plug-in will.
- **Absolute vs. relative control:** teleop should be relative (no snapping).
- **Impressiveness from first principles:** break an expectation; seconds to understand; narrow, controlled demo; filmable; don't overclaim; fewest moving parts.
- **Separate hardware per track** avoids blocking.
- **Training project + lab-os at the same time (2026-10-28):** the builder also works on the so101-green training project (now: preparing to record data). Keep them apart: separate folders, separate VS Code windows / Claude Code sessions (lab-os's hook would block legitimate training commands), separate environments (conda `lerobot` vs lab-os uv). Shared-desktop conflicts: a serial port or camera can be opened by only one program at a time; don't run lab-os hardware tests while a recording runs. The two USB cameras on the lab desktop belong to the training setup (confirmed 2026-10-28); off limits in lab-os until 2026-11-12, usable since (focus step 11).
- **Remote Control vs. cloud sessions:** Remote Control runs on the lab computer; cloud sessions can't reach lab devices.
- **Router policy:** a quick professor OK costs little. **One-way walls:** outside devices can't reach in.
- **Bridged robots** add a failure point. **AI makes modular code cheap to write, not free to design.**
- **Robot safety:** arms pinch; snapping arms lose balance; robots drive off tables; drones biggest risk; remote/venues add risk.
- **Cost:** Claude Code dev usage separate from system AI budget; realtime voice, robotics API calls, cloud GPUs and cellular data cost extra.
- **Silent failures** are the worst papercut. **Mic noise fixes:** close mic → wake word trained with lab noise → noise removal → echo cancellation → push-to-talk/typing → directional mic.
- **Two-speed design** is the main path to ~90% reliability. **Face recognition** opt-in only; **student ID** stored hashed.
- **Pitch:** "undergrads built this." 60-second clip; "ways to teach a robot"; "one hand, two robots"; "put anything on the table and ask it to grab it."

---

## Ideas
Moved to **`docs/plan/ideas.md`** (2026-10-24), the single source of truth for ideas.
