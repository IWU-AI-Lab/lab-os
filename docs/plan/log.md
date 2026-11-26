# lab-os — Running Log

A living record of decisions, facts and open questions for the AI lab's lab-os project (named "Lab JARVIS" until 2026-11-22: JARVIS is now one persona of several, quick job 92). Newest entries go at the top of each section. Ideas live only in **docs/plan/ideas.md** (the backlog). Companion docs: `docs/plan/current-focus.md` (what to work on now), `docs/plan/quick-jobs.md`, `docs/dev/project-scaffold.md` (what the repo should contain), `docs/dev/dev-setup.md`, `docs/archive/guides-2026-11-25/network-setup-checklist.md`. Early notes (the grill session, the teleop module's origin): `docs/archive/log-2026-10-early-notes.md`. Decision rows and discussion notes before 2026-11-16: `docs/archive/log-decisions-to-2026-11-15.md`.

**Current focus:** see **docs/plan/current-focus.md**.

---

## The goal (one paragraph)
Build a "JARVIS" for the university AI lab. **Primary user: the builder himself.** First priority: **connect most lab devices so Claude Code / AI agents can reach them for faster development.** On top of that: one AI brain that can see, control and eventually program the lab's robots through voice, typing and a screen GUI, with an optional Quest 3 experience (monitor only, monitor + Quest, or Quest only). Visitors are a secondary audience (a quick ~30-second headset demo with one command). **Modularity is a core requirement:** everything plugs in and out without rewriting the core. **Mobility is a goal too** (the system should travel to wherever visitors are, plus remote access from home and eventually robots across campus). Target: **~90% reliable**. Solo, unofficial project, 3–7 hours/week, no deadline. Success for the MVP = **it connects, and it inspires the builder to keep going.**

---

## Project hygiene (2026-10-23)
What the repo should contain, and what exists: `docs/dev/project-scaffold.md`. LICENSE: **ask the professor first; repo private until then.** **Always demo from a tagged known-good version.**

---

## Arm roles (2026-10-23)
| Arm | Name | Role |
|---|---|---|
| SO-101 set (leader + follower), green | `so101-green` | **The builder's own SO-101 training project** (with the two training cameras; clarified 2026-11-08: not someone else's). **Since 2026-11-12 lab-os may drive it and use its cameras** (focus step 11), keeping four rules: no motor ID/firmware changes, calibration read-only, the `lerobot` env untouched, never a port LeLab or a training run is using (CLAUDE.md). First VLA training round done (SmolVLA). |
| SO-101 set (leader + follower), white | `so101-white` (follower), `so101-white-leader` | **Polished teleop demo + second act.** Built; driven from the Quest (2026-10-30) and by AI tools (2026-11-10); its two cameras (same model as the training ones) used by the AI since 2026-11-12 (`camera_snapshot`). May also join the training project — teleop then doubles as its data-collection tool. |
| xArm 1S #1 (built, works) | `xarm1` | **Teleop prototype now** + **the JARVIS-track robot** + fallback teleop arm. |
| xArm 1S #2 (unbuilt) | `xarm2` | Spare / later. |

SO-101 over xArm for polished teleop: smoother motors/bus, LeRobot support, URDF exists. xArm: works today, keeps `so101-white` free. xArm roles: teleop prototype, JARVIS-track robot (separate hardware per track), modularity proof, glove input, visitor-safe commands.

---

## Hiwonder glove findings (2026-10-23)
Hardware: 5 finger potentiometers, MPU6050, Bluetooth, USB firmware port. Test: paired with `xarm1`; little lag; tilt-for-rotation good. Problems: extreme gestures needed; **snapping** (absolute tilt → angle) when switching motors; clumsy finger-count motor selection. Lessons → teleop requirements: per-user calibration + hysteresis, relative/clutch control, gentle ramps, whole-arm IK, keep tilt-for-rotation. Glove fix optional.

---

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
- **Beryl AX (GL-MT3000) checked against our needs (2026-10-29):** builder's pick (Amazon B0BPSGJN7T, $98.99). Fits: pocket-sized, **USB-C 5V/3A (runs from a power bank)**; internet from wall Ethernet (2.5G WAN), venue/phone Wi-Fi ("repeater") or phone USB tethering, several at once with failover ("Multi-WAN"); robots always join *its* Wi-Fi, so changing the internet source never reconfigures them; keeps working with no internet (offline lite mode); OpenWrt underneath (DHCP reservations, local names); **Tailscale built in** (remote level 2; still ask IT). Limits: only **1 LAN port** (a small switch if more wired devices); pocket-router Wi-Fi range (one room); one user report of very slow USB tethering vs. repeater, and an older report of Tailscale subnet routes breaking on tethering → **use phone hotspot over Wi-Fi (repeater) first, USB tethering as backup**. To check: joining campus/enterprise Wi-Fi (eduroam-style logins) and hotel-style login pages as repeater. Security setup: strong Wi-Fi + admin passwords, remote admin off, a **separate guest network** (client isolation) for visitors' devices, robots on the main network. Still needs: the professor's OK + who pays. **2026-11-19:** the builder buys a **GL.iNet Beryl 7 (GL-MT3600BE)** instead, about $90: Wi-Fi 7, one 2.5G WAN and one 2.5G LAN port, a USB 3.0 port, USB-C power (5 V/3 A up to 12 V/2.5 A, so a power bank works), Tailscale in GL.iNet's guide, OpenWrt underneath. **The professor approved it, on the wall port too (2026-11-20).**
- **Setup checklist:** passwords, remote admin off, DHCP reservations, auto-updates off, passwords stored safely, label, cable away from walkways.
- **The router in the lab (2026-11-23, lab check N):** the GL.iNet Beryl 7 on the wall port gives 120 Mbps (2.4 GHz) and 560 Mbps (5 GHz). The brain desktop's reserved address is 192.168.8.130, on Wi-Fi (the builder: the one LAN port stays free for the switch or to troubleshoot a device); the hub is at `http://192.168.8.130:8080`. The router's one LAN port goes to the big switch (the Jetson and 4 Pis).

---

## Robots without a Raspberry Pi (2026-10-22)
"Bridge" pattern (USB/Bluetooth/radio to a Pi 5, Jetson or the brain): TonyBot v1 (Arduino; USB serial or Bluetooth), xArm 1S (USB, Python `xarm`), Air:bit 2 ×3 (micro:bit radio; no spares; much later). Drones out of AI/voice/visitor control for now.

---

## Milestones (2026-10-23)
-1. **Repo scaffold** (docs/dev/project-scaffold.md "Day one").
0. **Fast track — teleop demo:** prototype on `xarm1`, polish on `so101-white`; portable from day one; then second act (ER "look, then reach" → SmolVLA).
1. **Milestone 1 — "Connected lab":** lab router, SSH keys + nicknames, device census, standards, one small visible win.
2. **Milestone 2 — Wake + roll call** (`xarm1`, then Raspbot); venue profiles.
3. **Milestone 3 — Voice + dev assistant.**
4. **Later:** offline lite mode; more robots; bigger VLA models (second act). Teleop demo showable 2026-10-30 (tag `demo-2026-10-30`). Current focus: the hub (`docs/plan/current-focus.md`); the troubleshooting suite and the rest of the teleop polish are on hold (`docs/plan/ideas.md` → "On hold"). Everything else: `docs/plan/ideas.md`.

---

## Dev setup
`docs/dev/dev-setup.md`: robots stay thin, the lab desktop as home base, Remote Control from home, deploys, branches and folders.

---

## Standards (to define on the ground)
To be decided once the device census shows what the robot computers look like inside: user accounts on robots, one project folder per robot, where logs go and how they're named, venue profiles. **Device names so far:** `so101-green` / `so101-green-leader` (the training set, borrowed by lab-os since 2026-11-12), `so101-white` / `so101-white-leader`, `xarm1`, `xarm2`, `pi01`, `quest-a` / `quest-b` / `quest-c` (the three Quest 3s, letters because "Quest 3" is the model; 2026-11-14); starter names: `raspbot1`, `pi5-1`, `jetson1`; bridged robots named after the robot, with the bridge noted. **Already decided:** secrets in one local `.env` per machine, never in git; calibration files travel with each arm (`calibration/<arm>/`); principles and hacks as in CLAUDE.md; demos run from tagged known-good versions.

---

## The biggest risk: on-the-ground surprises
Past examples: a VLA not using its cameras; low success rates; too little RAM; no Wi-Fi card; Wi-Fi country codes, hotspot mode, MAC registration; a humanoid's voice silently broken; VS Code Remote-SSH unstable on the Raspbot; glove needing extreme gestures and snapping.
Handling: census first · thin robots · capability checks · prove inputs · log everything · spikes · gotchas file · expect 2–3× longer · updates off, versions pinned.

---

## Is it actually useful? (still partly open)
Primary: faster development via a connected lab. In the plan: teleoperation for teaching robots (and data collection for the lab's training project); **"put anything on the table and ask it to grab it"** (ER look-then-reach). Other possible uses are in `docs/plan/ideas.md` ("Uses, reach, events"). Unofficial; no outreach. ROS 2 optional.

---

## The full vision (2026-10-19/20)
Walk in → ignition (card, the wake word, button, keyboard, Quest) → screens on + short animation + greeting → optional Quest launch → ambient standby → commands by voice/push-to-talk/typing (fast path or agent harness). Works without the Quest, with the Quest alone, and away from the lab.
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
- **Triggers slot** (generalizes "ignition"): everything that turns the system on or off is a plug-in: wake word, spoken phrases ("log out"), clap, card swipe, keyboard/button. Each can be switched on/off in config and per venue profile. *Why:* new activation methods keep coming; each should be a small add-on.
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
- **Starting, full screen, the reset, drawing resolution:** `docs/archive/guides-2026-11-25/hub.md`.

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
| move | anything that makes a robot move | developers on the brain's computer, through the safety layer; no asking per move (decision 2026-11-13, on the repo's allow list since 2026-11-14); off in remote mode |
| admin | `sudo`, deleting, reboots | humans only, never through tools |

The hub's built-in chat stays in the read tier (anyone in the room can type into it). Realistic workflows: `docs/plan/use-cases.md`. Built so far: the read and move tiers on this computer (focus steps 2, 3, 6); tokens, the act tier and the harness wait (`docs/plan/ideas.md` → "Brain as an MCP server", "Coding agent").

---

## Decisions
| Date | Decision | Why |
|---|---|---|
| 2026-11-26 | **One Monitor page for each kind of robot, at `/monitor/<kind>`** (quick jobs 146 and 147): `/monitor/so101`, `/monitor/xarm`, `/monitor/raspbot`; `/monitor` opens `/monitor/so101`. | The builder asked for the best of three address forms. A path gives each kind its own page and module, stays clean beside `?device=`, and a new kind is one more path. |
| 2026-11-26 | **The Raspbot gets mecanum driving, a live 3D model and its own Monitor before the demo** (quick jobs 142 to 146). The other board extras (the buzzer and light strip, the line tracker, the OLED, KEY1, AprilTags) wait until after the demo (`docs/plan/ideas.md`). | The builder: sideways driving has the higher priority; the extras add less. |
| 2026-11-25 | **The floor is one number for every arm; each SO-101's height is measured by hand** (quick job 121): `lab-os measure-arm <arm>` fits the shoulder offset and the table height from jaw-tip points on the table and writes them to `config/devices.yaml`. `so101-green` is measured in lab check T.3. | The green follower stopped higher than `so101-white`: it reads about 1.8 cm low, and only the white arm had its error measured (quick job 106). |
| 2026-11-25 | **Chrome on the builder's laptop waits until after the demo** (quick job 130): lab step M.6 moves to `docs/guides/lab-checklist-after-demo.md`, and the fix goes to the backlog. | The builder: not needed for the demo. Firefox on the laptop opens the hub. |
| 2026-11-25 | **The end of a question after the wake word: Pipecat's Smart Turn v3.2 on the brain** (quick job 110, `models/smart-turn/`, BSD 2-clause). After 0.3 s of quiet, it hears the last 8 s and says whether the question is finished; then the question ends at once. Not finished: the page's 2 s of quiet still ends it. Push-to-talk is unchanged (the release ends it). | The builder asked for no fixed wait. Smart Turn is maintained, runs on the CPU in about 40 ms, and uses `onnxruntime`, which lab-os already has. |
| 2026-11-25 | **How to plug in every USB device** (quick job 115, `docs/guides/plug-in.md`): the white set on its own USB hub, its cameras named by their port on that hub; the green set as the training has it (cameras in sockets 7 and 8); the card reader and the webcam on another computer of the room; the brain stays on the lab desktop. Replaces the white cameras' alias of sockets 7 and 8 (2026-11-12). | The simplest way by the demo: no new hardware, and the order of plugging no longer changes the names. Not yet tried in the lab (part P). |
| 2026-11-25 | **Three lanes at once** (lane 1: voice and the assistant; lane 2: arms, teleop, VR and the Raspbot; lane 3: the hub, its pages and the devices). Replaces the two lanes of 2026-11-20. | The builder: more jobs before 2026-12-01. |
| 2026-11-25 | **Until the demo, a change to a safety rule merges without the builder's review** (STOP, the soft limits, the floor, the speed caps, one controller at a time, the freeze). The green arms' rules and `.claude/` still wait. Replaces a part of the 2026-11-20 row. | The builder: no safety reviews while the builder works fast. |
| 2026-11-25 | **"Etc." in a job means every related thing**, not only the list (`AGENTS.md`). | The builder: sessions did only what was listed. |
| 2026-11-25 | **The designed hub becomes the only hub** (quick job 131); the plain hub goes to the archive. **Every page becomes a module of the hub** (quick job 133). **A Command Center** (quick job 134, `docs/design/command-center.md`) and **a phone remote** (quick job 124). | The builder: modular everywhere; a phone is best as a remote near the speaker. |
| 2026-11-25 | **Most guides pause until a stable version** (quick job 123): the ones the demo run does not need move to the archive, and sessions do not update them. The builder asks a session for instructions instead. | The builder: fewer output tokens. |
| 2026-11-25 | **A move to a named pose speeds up for 0.5 s and slows down for 0.5 s, and the hub's chat goes to a pose in one move** (quick job 118). The AI tools' `go_to_pose` keeps the 30° per-call limit. | The builder turned off the speed cap and the per-move limit because the moves were too slow. A minimum-jerk profile made them slower still (rest → `ready` 2.9 s → 5.4 s), and with the limit on, the arm stopped at each 30° step. Now 3.4 s, without stops. |
| 2026-11-25 | **The demo's fallback is frozen:** the branch `demo-freeze` and the tag `demo-fallback-2026-11-25` (commit `efbc5b1`, `main` after the 2026-11-24 lab day). Work goes on in `main` until Tuesday 2026-12-01. If `main` passes the practice run on 2026-12-01, it is tagged `demo-2026-12-03`; if not, the demo runs from `demo-freeze`. Nothing goes on `demo-freeze` unless the builder asks. | The builder: the 2026-11-24 version is enough for the demo, "albeit shaky". |
| 2026-11-25 | **Small jobs go to a backlog** at the end of the queue (`docs/plan/quick-jobs.md` → "Backlog"). No session starts them until the builder says. | The builder: fix only what the demo needs; the builder asks for more. |
| 2026-11-25 | **Hand control in VR Teleop only when chosen** (quick job 114): off by default, a setting turns the switch on, and Hands is a mode in the options. | Lab check T.1: the controllers put down switched to hands by themselves. |
| 2026-11-24 | **Lab day results** (the demo run, `docs/guides/lab-checklist.md`). Passed: 0.1 (863 tests), S.1 to S.6 (the wake word verifier: 10 of 12 tries, 4 of 5 answers), G.0 to G.3 (one game, about 8 min), T.1 to T.4 (T.4 after the fixes in PRs #271 and #272), R.1, R.2, L.1, A.3, A.5, M.1, M.5 to M.7. Passed with a problem: H.1 (it moved fast, quick job 118). Failed or not done: H.2, H.3, W.1, A.1 (focus), A.2 (the green arm), A.4, A.6 (fixed the same day, PRs #273 to #275), M.2, M.3, R.3 (no video); M.4 skipped. The fixes are quick jobs 109 to 122. | The record of the 2026-11-24 testing day. |
| 2026-11-24 | **The floor is 0.8 cm above the table, and `so101-white`'s shoulder_lift reading gets −4.7°** (`joint_offsets_deg` in `config/devices.yaml`). Replaces the 0.2 cm in the row below. | Quick job 106 measured the arm by hand: its height read 0.3–1.7 cm low, the more the farther out; a 4.7° shoulder offset fits every point to 0.5 cm. The jaw tips reach 0.6 cm below the gripper point, so at 0.8 cm they stop 0.2 cm above the table (the builder chose it). `pick_at` aims the fixed jaw 2 cm beside the object (the gripper point is on it). `docs/dev/GOTCHAS.md` 2026-11-24. |
| 2026-11-24 | **The floor is 0.2 cm above the table** (`min_z_cm`, both venues; was 1.1 cm since 2026-11-18). The builder asked for 0.9 cm lower, for good. Replaces the 2026-11-18 row's number. Quick job 106 measures the white arm's real position numbers. | Tic-tac-toe: at the 1.1 cm floor the jaws closed above a 3 cm piece, three times (`docs/dev/GOTCHAS.md`, 2026-11-12 entry). |
| 2026-11-23 | **The lab checklist is a short demo run until the demo** (`docs/guides/lab-checklist.md`, about 2 hours); the edge cases, errors and details move to `docs/guides/lab-checklist-after-demo.md`, for after 2026-12-03. | The builder: the full list with the reports got too long. |
| 2026-11-23 | **Each persona has a voice of its own gender:** J.A.R.V.I.S. male, the Lab Assistant female (quick job 100). The assistants never say which language they answer in. | The builder: the voice should match the persona. |
| 2026-11-23 | **Teleop on the Quest stays inside the hub in VR and AR** (the builder), as a module like the others (quick job 97). Replaces the part of the 2026-11-21 start flow (PR #204) that opened the whole Teleop page from the hub in VR. | On the Quest, leaving the hub for a full page is one step too many; the other modules stay in the hub. |
| 2026-11-21 | **Lab results and small issues become quick jobs by area** (82–88), not one job each; a polish sweep of every page in a headless browser (89) catches the look and layout ones. (Removed from the queue 2026-11-22: the builder says when.) Sound, voice timing and feel still need the lab. The brain's log goes to a file that sessions read (85). The builder adds small issues to lab reports with "Also,". | The builder: "a lot of minor issues… iron these out in one fell swoop". |
| 2026-11-21 | **Faster AI arm control: "Code as Policies" first** (quick job 81): the AI sends one short program over the brain's tools (`run_program`), run locally under the existing safety layer, instead of one model call per move. A trained policy with asynchronous action chunks (SmolVLA) comes later, with recording and training. | From the builder's search results (Gemini, ChatGPT): the only method that needs no training, GPU or new hardware; the others need a trained VLA, a GPU, a depth camera or ROS. |
| 2026-11-21 | **Full Access for the hub's assistant** (quick job 80): a Settings switch, off by default, gives it every MCP tool (arms, cameras, the green set included) and new tools for each hub button, which Claude Code and Codex get too. No new safety now; the existing layer and the green rules stay. Visitor sessions are rare (about 3 a semester), often outside the lab, and visitors mostly don't speak, so a visitor talking to the assistant is not the main concern. | The builder: "we can build safety in later, once i know what its full capabilities are." |
| 2026-11-20 | **A place's own changes go into its `local/` folder** (`config/local/` in the lab, not in git): the settings page writes only the changed value there, and the brain merges it over the defaults, value by value (sections key by key; a value or a list replaced). `hub-devices.yaml` and `table-maps/` moved there too. The files in `config/` are the defaults for every place. A small merge in lab-os, not a library (Dynaconf and others do the same, but they can't keep the comments the page keeps). | The settings page's changes showed in `git diff config/` and broke the tests, and a place's full copy of `theme.yaml` never got new fields. The usual pattern: committed defaults plus a small ignored local file. |
| 2026-11-20 | **Tic-tac-toe is played with Claude Code only**: no Codex or Gemini CLI in the lab, so lab checks G.6 and G.7 and their setup in the guide are removed. Another model through Claude Code's `/model` if one plays badly. | The builder: "i don't have codex or gemini cli, so can't test those." |
| 2026-11-20 | **A card swipe starts the hub** (quick job 79, lane 1): on the idle start screen of any device with the hub open, any card with a plain number, its own punchy animation and sound; no card data is kept. Names, authorization and activating things stay ideas. | The builder. |
| 2026-11-20 | **Two coding sessions at once, one for each lane** of the queue (lane 1: voice and the hub pages; lane 2: arms, teleop and VR); each session fixes its own conflicts. **Existing work no longer stops a session:** it uses it when it clearly fits, and writes one line in the report. Both in `AGENTS.md`. | The builder chose both, to build every job by Tuesday 2026-11-24. |
| 2026-11-20 | **Faster building:** every queue job should be built by Tuesday 2026-11-24, the testing day; Tuesday 2026-12-01 is for setting up the demo and a practice run. A coding session now works through the whole queue without stopping. Lab results of 2026-11-20 became quick jobs 74, 76, 77 and 78, and changes to 59 and 64. | The builder: the last round took 6 to 7 hours of the builder's time. |
| 2026-11-20 | **The professor approved the travel router, on the wall Ethernet port too.** The router gets its internet from the wall port from the start (lab check part N). The brain desktop keeps the campus Wi-Fi for its internet as a temporary safeguard; everything goes on the router once the wall port's internet is proven. | The builder asked the professor; the builder: "hopefully not permanent". |
| 2026-11-23 | **The devices that may drive a real arm are kept in `place.yaml`** (`drive_from:`, names or addresses, read at start, added to `--drive-from`); the Quest's reserved address on the router is on the lab's list (quick job 95). | Lab check N.8: the Quest on Wi-Fi only watched, and `--drive-from` had to be typed at every start. |
| 2026-11-20 | **The demo-day room uses every screen** (`docs/plan/current-focus.md` → item 10): the desktops, Pis, the Newline, the projector and the Quest, each with a useful page; the recommended layout is a starting point that the builder may change. Quick jobs 70 (the nearest microphone answers), 71 (a room layout), 72 (Raspbot teleop, after raspbot1 joins the router). Lab parts N (the router, assuming nothing about the wall port) and M (every screen). | The builder: "the more the better", but practical; a small microphone can't hear the whole room. |
| 2026-11-20 | **Sessions merge their own pull requests, new arm movement included**; only a critical change waits for the builder: one that weakens a safety rule, the green arms' rules, or `.claude/`. **Nothing new after Tuesday 2026-12-01** (before: 11-24); until then, as many queue jobs as possible, conversation mode and a stronger model for hard questions included (quick jobs 68, 69). | The builder: "ensure I don't need to do this unless there's something super critical"; about two weeks are left, and the builder wants to finish as much as possible. |
| 2026-11-20 | **How sessions work now:** one coding session at a time; every coding session uses the same prompt and takes the next jobs from the queue in `docs/plan/quick-jobs.md`; a session builds only what the job says; its report fits on one screen in a fixed form (`AGENTS.md`). **No STOP on the hub** (quick job 43 dropped, PR #149 closed): STOP on Monitor, open on another device. **Lab days:** Tuesdays 2026-11-24 and 2026-12-01; the demo is probably Thursday 2026-12-03. Tic-tac-toe pieces: LEGO from home. | The builder: two sessions at once kept conflicting; the reports were too long to read; what the sessions built often missed what the builder had in mind; a STOP on the hub adds clutter. |
| 2026-11-19 | **After the lab day:** the Newline's route is HDMI at 1600×900 with the USB touch cable (its own Chrome isn't smooth). The startup as a video stays off. The wake word sensitivity stays, although it changes little in the lab. **Lab checklist steps** ask at most 3 questions and fit the real room (the rules are at the top of `docs/guides/lab-checklist.md`). Quick jobs 42–55 from the day's findings. | The builder: "hdmi at 1600x900 seems like the best"; too many checks in one step got hard to report. |
| 2026-11-19 | **Tuesday's previews** (2026-11-24 lab day), shown at the demo's end as "But wait, there's more": the robot plays a game (tic-tac-toe), teleop with a webcam or the Kinect, two arms from the Quest. **Point and "move there" goes to the ideas.** **The Newline as JARVIS's screen is a priority** (lab check part 2 the same day). Quick jobs 40 (terminal colours, not urgent) and 41 (the AI Spend page says "estimated" and that it counts one brain). **The builder buys a travel router**, a GL.iNet Beryl 7 (GL-MT3600BE, about $90), hoped for by 2026-11-24; **a fourth preview, the finale:** "Jarvis, hand me the cube", the hub's assistant starts a pick and hand-over; the professor's OK before it stays on the wall port still applies. | The builder. |
| 2026-11-19 | **One rules file for every AI agent:** the rules are in `AGENTS.md`; `CLAUDE.md` only points to it (rows above that say "CLAUDE.md" now mean `AGENTS.md`). **Agents write to the builder in ASD-STE100** (Simplified Technical English): reports, questions, answers, PR descriptions, guides. | The builder: other agents (Codex, …) should read the same rules without a second copy to keep right; the guides already use STE100 (quick job 39). |
| 2026-11-18 | **Visitor mode is the AI's to start, exit and wave** (quick job 35, PR #132): no fixed phrases; the hub's chat gets tools (start, exit, wave) on the brain's own computer, and the AI words the welcome from real facts. ⚙ → Visitor mode starts and exits it without asking. "Back to normal" is now "Exit visitor mode". **Visit-day has no extra restrictions:** the lab's speed, 1:1, robots (so101-green added) and switchable limits; Settings and the AI spend stay hidden. | The builder: the AI understanding "it's demo time" is the point; 1:1 is the most intuitive headset control. |
| 2026-11-18 | **"Say hello to our visitors"**: switches to the visit-day venue, a spoken welcome, three "try this" cards, and a fixed-pose wave (quick job 35). **Tic-tac-toe** as a fourth, stretch preview, tried with several models through the MCP tools. **Gemini 4 Hydrogen / Antigravity:** an idea, probably not (no paid plan; outside our safety layer). Quick jobs 36–39: the Quest's view on another screen, the VR status box, a settings overhaul, plain-English docs with one place per fact. | The builder. |
| 2026-11-18 | **`home` hovers just above the folded rest** (quick job 30, PR #124): the builder's pose from lab check 8.16 with wrist_flex 55 instead of 75.9; shoulder_lift and elbow_flex keep the real numbers and are clipped at their soft limits (6.3° and 3.6° short), the limits not widened. | With 75.9 the model puts the gripper below the table and the floor refuses the move; letting go of the arm finishes the fold. |
| 2026-11-18 | **Heights are measured from the table** (quick job 28, PR #120, merged with the builder's OK): each arm's `table_z_cm` in `devices.yaml` (`so101-white` −1.6). The floor (`min_z_cm`) is from the table too, so it became **1.1 cm** in both venues: where the 2026-11-13 −0.5 cm (from the base) put it for `so101-white`; stricter, never looser, for an arm on the table. Replaces the 2026-11-13 row's number. | The arm stands on a plate: `pick_at` closed near the cube's top and the floor sat ~1 cm above the real table. The value is the builder's to change. |
| 2026-11-18 | **Sessions merge their own PRs** once the tests pass, except changes to arm movement, the safety layer, the green arms' rules or `.claude/`, which wait for the builder. **Sessions check open PRs first** and stay out of files another is changing; **no leftovers**: a change of behaviour or name means fixing every doc that still says the old thing, in the same PR (CLAUDE.md). **Assistant language per device:** input and output, each Any or English, Any by default (quick job 33). | The builder: waiting to merge is annoying; the docs were drifting (old context, unupdated text) and sessions overlapped (a draft left in another session's folder). |
| 2026-11-17 | **Green calibration: the training files are the source of truth.** `sheep.json` (follower) and `shepherd.json` (leader), which the cube-to-box data was recorded with from LeRobot's command line, stay untouched. lab-os drives with its own copy (`calibration/so101-green*/`) and refuses if it differs from them. LeLab gets one entry, `SO-101_Green`, using its own copy (`lelab_green.json`); its two old entries and their files move to `~/green-calibration-backup/` (`scripts/green-lelab-from-training.sh`, run by the builder). Replaces the 2026-11-16 row below. | Builder. LeLab's two entries (each the whole pair, names crossed) wrote two follower calibrations about 3° apart into the motors, and it was hard to tell which was which. Now there's one calibration everywhere, and the training files can't be overwritten by lab-os or LeLab's teleop. |
| 2026-11-16 | **Green calibration: lab-os matches the motors** (replaced 2026-11-17, above). LeLab writes one of two calibration files into the green arms at each teleop start; lab-os uses whichever file equals what the motors hold and refuses only if none does (quick job 18). **Home is the folded rest pose** with the gripper slightly open; today's home becomes `ready` (quick job 20). **Sessions say what they chose without being asked**, written so they make sense without having read the session: full sentences, everyday names, no shorthand (CLAUDE.md). | Lab check part 8 (`docs/dev/GOTCHAS.md`); the builder: reports that assume everything was read, or use the session's own shorthand, are confusing and get skipped. |
| 2026-11-16 | **Existing work: keep our teleop and AI tools, borrow parts** (`docs/dev/existing-work-teleop-ai.md`). Before the demo: teleop relative mode at scale 1.0 with a higher speed limit; the stand camera's cm grid from a printed calibration sheet (Google's robotics-pointing-sample); a `pick_at(x, y)` tool; optionally robot_MCP's pick tips. After the demo: LeRobot's Isaac Teleop as an input to the brain (a thin layer, so STOP and the limits stay). No switch to telegrip, XLeRobot, robot_MCP or phosphobot. | The comparison (code read 2026-11-16): theirs drive teleop 1:1 without our 45°/s cap; ours is the safest and only model-agnostic AI control, but lacked camera → table positions and a pick skill. Isaac is the best-engineered teleop but bypasses the brain on its own. |
| 2026-11-16 | **Three previews for the demo:** point and "move there" in the headset, "what's on the table?" (stand camera + Gemini), two arms at once. Separate from what works, cut if not running on the hardware by 2026-11-24. The lab checklist is rewritten to instructions and what to report only (the long one is archived). | The builder: people have seen parts already, so the demo also shows where it's going; three, not many, because lab time and the builder's attention are the limit. |
| 2026-11-16 | **The demo of every feature moves to Thursday 2026-12-03**, 3–4:30 pm, the AI club's meeting (tag `demo-2026-12-03`). Nothing shown before. Nothing new after Tuesday 2026-11-24, only fixes. | The builder: almost no lab time before 2026-11-19 and several features never ran on the real hardware; the lab days on 11-19 and 11-23/24 make it testable. Coursework first. |

---

## Facts about the lab
- **Status of the project (builder, 2026-11-09):** unofficial: nobody has been told yet, it may turn out useless, and it may not continue past this semester. It's about seeing what's possible. So: demo-able pieces first, cheap, nothing others come to depend on, and docs good enough for a future student to pick up.
- **Usage pattern (2026-10-28):** the lab is usually empty; startup happens when the first person arrives to a closed lab. Robots are off before that (battery-powered ones must be switched off); all need a physical switch, except the SO-101s (no switch; wall power supply).
- **Room:** desk clusters; side room with counter, SO-101 arms, beanbag; laggy big screen; projector; 32" ViewSonic monitors; noisy (fans); 3rd floor; setup movable; IWU. Visitor routes may not pass the lab.
- **Equipment check (2026-10-30):** the lab has most of the demo kit (cables, adapters, extension cords; boxes + a trolley for transport). Also a **Kinect** (version to check) and a spare webcam (the two Innomaker training cameras belong to the green set; lab-os borrows them since 2026-11-12). **To buy:** USB-C power bank (router/field use); **a powered USB hub (7 ports) for the brain desktop** (2026-11-12: all 7 USB-A sockets are taken: keyboard, mouse, the green cameras and arms, the xArm; the white arm + cameras need 4 more) (added 2026-11-11: identical cameras can only be told apart by socket, and the desktop's sockets are limited); **stronger table clamps** (the SO-101s' thin ones are only just sufficient); **a USB conference speakerphone** (one omnidirectional microphone for a room; added 2026-11-20), only if quick job 70 (the nearest microphone answers) is not enough. **Later, not urgent:** better cameras for lab-os (second act). Router: see Network plan.
- **The devices** (computers, screens, robots, cameras, microphones, wearables): `docs/guides/lab-inventory.md` (2026-11-25; before, they were listed here).
- **Network:** lab Wi-Fi with MAC registration via campus IT; wall Ethernet port works.
- **Domain:** the lab owns `indwesailab.com` (bought summer 2026 for one year: renew by summer 2027 or the certificates stop). The university didn't want it as the lab's public face, so only a subdomain is used, for lab screens. **DNS is on AWS Route 53** (checked 2026-11-09: the domain's name servers are `awsdns`); the builder has the AWS login (set up with the professor, summer 2026). The main domain still serves an old public website from S3 that was never removed; the `hub.` subdomain doesn't touch it.
- **AI access (updated 2026-10-30):** OpenAI keys (primary; the professor's account, paid by the university: believed 2026-11-09, not confirmed); free Gemini keys (free tiers may use data for training: check terms); the Anthropic key is out of credits (Gemini Robotics-ER 2 preview is on the Gemini API).
- **Earlier Raspbot work (the builder's, before lab-os):** voice control on a Raspbot: press a button on the IR remote and speak; after 3 seconds it transcribes the speech, and if it hears a known word (forward, backward, left, right) it moves a little that way. Not part of lab-os (where its code lives: to note).
- **Builder:** CS student; learns with AI; Python + web; dislikes the CLI, likes VS Code + Claude desktop/web UI; 3–7 h/week; graduating May 2027; lives ~5 min from campus.

---

## Open questions
- **Second act:** can the Kinect's depth camera help "look, then reach" (3D position directly, less camera-to-table calibration)? Which Kinect version, and does it run on our OS? ER pointing accuracy with our camera; camera-to-arm calibration method; ER preview pricing/free-tier limits and data terms; ~~SmolVLA training on 12 GB~~ (works: ~8 GB with the VLM frozen, 2026-11); cloud GPU option/cost for bigger models.
- **License/ownership:** what does the professor/university allow?
- **Portability:** which laptop is the field brain; venue internet; batteries vs. outlets; where visitor routes go.
- **Teleop spikes:** `xarm1` speed/delay; Quest WebXR data, overlays, USB forwarding (Quest developer mode / Meta account access); IK library; `so101-white` calibration; end-to-end delay.
- **Glove** firmware source; **training project** plans for `so101-white`; **IT/professor** router questions; overlay network; cellular.
- TonyBot v1 board; wake word from the doorway; waking screens; Quest camera access; Quest-only practicalities; past Quest demo contact; offline lite mode contents; use cases beyond development; mic test; agent harness; free-tier data terms; Raspbot internals; humanoid SDK. (Answered since: HTTPS → `docs/archive/guides-2026-11-25/voice.md` → "Secure pages"; model router → `config/models.yaml`; persona names → `config/personas/`; voice pipeline → `docs/archive/guides-2026-11-25/voice.md`.)

---

## Ideas
Moved to **`docs/plan/ideas.md`** (2026-10-24), the single source of truth for ideas.
