# Lab JARVIS — Running Log

A living record of decisions, facts and open questions for the AI-lab "JARVIS" project. Newest entries go at the top of each section. Ideas live only in **ideas.md** (the backlog). Companion docs: **current-focus.md** (what to work on now), **project-scaffold.md** (what the repo should contain), **dev-setup.md**, **network-setup-checklist.md**.

**Current focus:** see **current-focus.md**.

---

## The goal (one paragraph)
Build a "JARVIS" for the university AI lab. **Primary user: the builder himself.** First priority: **connect most lab devices so Claude Code / AI agents can reach them for faster development.** On top of that: one AI brain that can see, control and eventually program the lab's robots through voice, typing and a screen GUI, with an optional Quest 3 experience (monitor only, monitor + Quest, or Quest only). Visitors are a secondary audience (a quick ~30-second headset demo with one command). **Modularity is a core requirement:** everything plugs in and out without rewriting the core. **Mobility is a goal too** (the system should travel to wherever visitors are, plus remote access from home and eventually robots across campus). Target: **~90% reliable**. Solo, unofficial project, 3–7 hours/week, no deadline. Success for the MVP = **it connects, and it inspires the builder to keep going.**

---

## Project hygiene (2026-10-23) — details in project-scaffold.md
Day one: README, CLAUDE.md (points to current focus + log; rules), docs/, SAFETY.md, .gitignore, .env.example (secrets never committed), config/ (personas, model router, devices, venue profiles), calibration/<robot>/, dependency lock, install script, tests with fake robots, formatter/linter, LICENSE (**ask the professor first; repo private until then**). Soon: GOTCHAS.md, DEMO.md runbook, decision records, CI on GitHub, **tagged known-good demo versions (always demo from a tag)**, CHANGELOG, task board. Later: CONTRIBUTING.md, HANDOFF.md, ARCHITECTURE.md, demo video.

---

## Arm roles (2026-10-23)
| Arm | Name | Role |
|---|---|---|
| SO-101 set (leader + follower), green | `so101-green` | **The builder's own SO-101 training project** (with the two training cameras; clarified 2026-11-08: not someone else's). Not part of lab-os *yet*: the hard rules (never open its ports, never recalibrate) stay until its integration is planned (`ideas.md` → "LLMs/VLMs driving the green SO-101s"). |
| SO-101 set (leader + follower), white | `so101-white` (follower), `so101-white-leader` | **Polished teleop demo + second act.** Parts printed; camera mounts printing; to be built. May also join the training project — teleop then doubles as its data-collection tool. |
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
**Remote levels:** (1) Claude Code via **Remote Control** — confirmed working; (2) GUI from home via a private overlay network (ask IT first); (3) lab in a bag; (4) cellular robots (much later). **Safety:** remote mode = no motion by default; dead-man stop.

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
-1. **Repo scaffold** (project-scaffold.md "Day one").
0. **Fast track — teleop demo:** prototype on `xarm1`, polish on `so101-white`; portable from day one; then second act (ER "look, then reach" → SmolVLA).
1. **Milestone 1 — "Connected lab":** lab router, SSH keys + nicknames, device census, standards, one small visible win.
2. **Milestone 2 — Wake + roll call** (`xarm1`, then Raspbot); venue profiles.
3. **Milestone 3 — Voice + dev assistant.**
4. **Later:** offline lite mode; more robots; bigger VLA models (second act). Teleop demo showable 2026-10-30 (tag `demo-2026-10-30`). Current focus: the JARVIS hub (`current-focus.md`); the troubleshooting suite and the rest of the teleop polish are on hold (`ideas.md` → "On hold"). Everything else: `ideas.md`.

---

## Dev setup — details in dev-setup.md
Robots stay thin · Linux lab desktop with VS Code + Claude Code extension · Remote Control from home (confirmed) · cloud sessions only for pure-software work · ssh + rsync deploys · auto-restarting services · permission rules (ask before sudo, deletes, reboots, robot motion) · git as undo · fake robots at home, real hardware in the lab · private GitHub repo · one install script for desktop *and* laptop · CLAUDE.md points to current-focus.md and this log.

---

## Standards (to define on the ground)
Device names, accounts, folders on robots, repo layout, logs, secrets, principles, venue profiles. **Names so far:** `so101-green` (not ours), `so101-white` / `so101-white-leader`, `xarm1`, `xarm2`; starter names: `raspbot1`, `pi5-1`, `jetson1`, `quest1`; bridged robots named after the robot with bridge noted. Calibration files travel with each arm. Hacks: `# HACK:` + entry in current-focus.md. Demos run from tagged known-good versions.

---

## The biggest risk: on-the-ground surprises
Past examples: a VLA not using its cameras; low success rates; too little RAM; no Wi-Fi card; Wi-Fi country codes, hotspot mode, MAC registration; a humanoid's voice silently broken; VS Code Remote-SSH unstable on the Raspbot; glove needing extreme gestures and snapping.
Handling: census first · thin robots · capability checks · prove inputs · log everything · spikes · gotchas file · expect 2–3× longer · updates off, versions pinned.

---

## Is it actually useful? (still partly open)
Primary: faster development via a connected lab. In the plan: teleoperation for teaching robots (and data collection for the lab's training project); **"put anything on the table and ask it to grab it"** (ER look-then-reach). Other possible uses are in `ideas.md` ("Uses, reach, events"). Unofficial; no outreach. ROS 2 optional.

---

## The full vision (2026-10-19/20)
Walk in → ignition (card, "hey Jarvis," button, keyboard, Quest) → screens on + short animation + greeting → optional Quest launch → ambient standby → commands by voice/push-to-talk/typing (fast path or agent harness). Works without the Quest, with the Quest alone, and away from the lab.
Modules in the plan: teleoperation; look-then-reach; phones/laptops as mics; offline lite mode; remote access (staged); portable kit. Further optional modules: `ideas.md`.

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
- **Agent harness is a swappable slot** (slow path). A Claude Code / Claude Agent SDK harness is one candidate (`ideas.md`): tools default-deny; any robot motion still goes through our safety layer.

---

## Decisions
| Date | Decision | Why |
|---|---|---|
| 2026-11-09 | **Robot tools for AI, details (focus step 2):** MCP on `127.0.0.1:8081/mcp` only, in the brain's process. Moves run as a "motion" in the teleop loop (AI has control only while its move runs). Per call: at most 30° per joint (the gripper exempt) or 10 cm, bigger requests go part of the way and say so; nothing below 1 cm above the table; `move_to` follows a straight line. Limits per venue (`ai_tools`), named poses per arm model (`config/poses.yaml`). In Claude Code: read tools and `stop` allowed without asking, move tools are "ask" rules in the project settings. | Small, checkable steps with a human approving each; stopping must never wait for a click. |
| 2026-11-09 | **Plain hub built (focus step 1):** modules open in an `iframe` inside the hub page (the hub hears their keys and taps for Esc and the reset); under `lab-os serve` the teleop page moves to `/teleop` (`lab-os-teleop` keeps `/`); `lab-os serve` listens on this computer only, and `--host` for other screens is allowed **only with a fake arm**. Theme ids without a page (`arm`) get no button. | No page load keeps full screen; existing pages work unchanged inside it; nobody on the network can drive a real arm through the hub. |
| 2026-11-09 | **The brain is an MCP server; the hub keeps a small fast chat; a "send to harness" toggle (+ a send-everything setting) hands requests to a coding agent.** Tools are defined once and grouped in **permission tiers**: read (everyone, incl. the built-in chat), act and move (developers with a token; move through the safety layer, asks every time), admin (humans only). | One set of tools for every AI; quick questions stay fast and cheap; anyone at the screen can't change things. |
| 2026-11-09 | **Two routes for AI-assisted development, same branch → tests → PR → approval rule:** (1) bring your own tool (laptop + VS Code with Claude Code / Codex / Claude Desktop + repo + the brain's MCP tools); (2) a lab-paid harness on the brain with the lab's API key (Codex with the OpenAI key, to verify), with a spend cap. | Most students have no subscription; the system shouldn't depend on one person's account. |
| 2026-11-09 | **AI driving a robot arm moves into the current focus** (steps 2–3, right after the plain hub): the brain's MCP server with move tools for `so101-white`, driven by Fable 5.2 in Claude Code (the builder's access ends 2026-11-16), blind first, then the white arm's two cameras. Move tools: localhost only, same safety layer as teleop, clip and refuse, one controller at a time, ask every time. The green arm stays off limits. | Use the Fable access while it lasts; it starts the "LLMs/VLMs driving the arms" goal on an arm that's ours. |
| 2026-11-09 | **The hub design is approved** (`docs/design/`: DESIGN.md, hub-concept.html, theme). The startup is designed (old prototype step dropped); it takes **about 8 s including the unlock**, skippable with any input. The greeting = time of day + one line of real news built by the brain, else the persona's plain line; the startup title is the lab's name (`hub.title`), not a persona line. Fonts are bundled (offline). | The concept page is the spec; real facts only. |
| 2026-11-09 | **Plain first, the design as a surprise reveal.** Phase 1 (focus steps 1–8): everything works on deliberately plain pages that copy the concept's structure but not its looks, until teleop, the AI driving the arm and voice can be demoed. Phase 2 (step 9): the full design in one 1–2 hour sitting, then the hub is left at its start screen on the Newline or a desktop for someone curious to start. **Voice moves from stretch to required.** | The builder wants the design to be a surprise (people see the screens while work happens); demo-able features first. |
| 2026-11-09 | **Two taps on the start screen:** tap 1 = full screen (the idle screen itself; skipped when already full screen), tap 2 = start. **After ~3 min with nobody, back to the start screen** (modules closed, conversation cleared; never while teleop, an AI move or a voice turn runs). **Hyperspace is the default startup**; `assemble` and per-venue are the other settings. | The hub is left full screen on a public screen for someone curious; the next visitor should get the startup, not the last visitor's chat. |
| 2026-11-09 | **Voice on any screen; the brain gets a real HTTPS address:** a subdomain of the lab's `indwesailab.com` (e.g. `hub.indwesailab.com`) pointing to the brain on the lab network, with a free Let's Encrypt certificate via a DNS check; the router answers the name locally for offline use. Fallbacks, easiest first: localhost on the brain's screen, Chrome's insecure-origin flag, `adb reverse`, our own certificate authority; with no secure page or no microphone, voice is hidden. The page records and plays; the brain talks to the voice service (keys stay on the brain). | Browsers give the microphone (and Wake Lock, app install, WebXR) only to secure pages; one certificate makes every screen work with no setup per device. |
| 2026-11-09 | **Opening a module on another screen comes before the reveal** (focus step 8, the reveal is now step 10), with **one tap or click to open the hub on any screen, nothing starting by itself** (screens, the Newline above all, are used for other things; lab-os uses nothing where it isn't open): a shortcut per screen with its name in the address (`/?screen=newline`), and the brain updating `hub.indwesailab.com` in Route 53 to its current address until the router gives it a fixed one. | The devices are switched off every night, so nothing may depend on someone typing an address, and nothing may take over a screen; the builder wants screen-to-screen in the demo. |
| 2026-11-09 | **One brain per network:** the brain runs on any computer, but if one is already on the network a new one doesn't start, and when two meet later the later one closes (safely: never mid-move). A `--second-brain` development option. **Nothing place-specific in code:** lab name, domain, devices, off-limits list, venues and personas in config; another place (the builder's home, other people) = another config folder. Only the lab's brain updates `hub.indwesailab.com`. | Builder: start the brain on any computer without two fighting; reuse lab-os at home and elsewhere. |
| 2026-11-09 | **Places, as built:** place files (`place.yaml`, `devices.yaml`, `venues/`) come only from the place's own config folder; shared files (theme, poses, later models and personas) fall back to the repo's `config/`; the repo's `config/` is the lab. **The repo's off-limits devices are added at every place.** The hub title is `name` in `place.yaml`. | A home brain must never claim to be the lab or drive the lab's devices; and switching folders on the lab desktop must never unblock so101-green. |
| 2026-11-09 | **Time box: the reveal by ~2026-12-04** (semester ends 2026-12-15, finals the week before). Build order 1 → 2 → 5 → 7 → (3, 4, 6, 8) → 9 → 10; all steps stay in. | The project may end with the semester; lab testing, not coding, takes the calendar time. |
| 2026-10-30 | **AI provider: OpenAI first; free Gemini as backup; local models as a second setup.** The chat speaks the OpenAI-style interface so OpenAI, Gemini and local servers (Ollama / llama.cpp) differ only by config. The Anthropic key is out of credits; coding-agent candidate changes accordingly (OpenAI Codex, or Claude Agent SDK if refilled). | Where the keys are; one interface keeps the model router simple and makes offline chat possible. |
| 2026-10-30 | **Focus = the JARVIS hub first** (supersedes the core-plumbing order of the earlier 2026-10-30 entry): `lab-os serve` → hub page → personas → the assistant's picture → startup prototypes → real startup → typed chat → read-only project helper → voice (stretch). Roll call, plug-in descriptions and robots reporting in wait for the router (`ideas.md` → "On hold"). | The builder wants the system itself first; most core plumbing is easier with the router at hand. |
| 2026-10-30 | **The assistant's state is separate from its picture.** States: idle / listening / thinking / speaking / offline / error (+ loudness). Pictures are per-persona decorative renderers (plain circle first; inspired orbs and VRM characters later; no brand assets; Live2D dropped). | New looks never touch the conversation code; quality levels come for free. |
| 2026-10-30 | **Personas are files in `config/personas/`** (versioned; unknown fields kept with a warning, so the format can grow). Fields: id, display name, personality text, model setup, voice, wake word, picture, lines (show names), sound pack. **Default persona: a plain "lab assistant"**; `jarvis` is the show persona, chosen per venue. The theme stays the same across personas. | Extensible without code changes; "JARVIS" needs no explanation if it isn't the default. |
| 2026-10-30 | **Hub = one full-screen browser page served by `lab-os serve`, on a 32" monitor first.** Module buttons come from config; the status strip shows only real facts; startup begins with a key press/click (unlocks browser sound), shows only real checks, is skippable. Typing first; voice when typing is solid. | Same tech as teleop; offline; honest. |
| 2026-10-30 | **Coding agent direction:** works like Claude Code but paid by the lab's API account (Claude Agent SDK if the credits are Anthropic's); works only on `agent/<task>` branches → tests → PR → builder's approval. This focus: read-only helper that answers and drafts Claude Code prompts. | AI-assisted development that doesn't depend on one student's subscription; keeps the agent-changes rule. |
| 2026-10-30 | **Teleop demo focus closed: showable as is, "needs polishing"** (`so101-white` driven from the Quest controllers through IK at `--speed 0.2`; tag `demo-2026-10-30`). Unfinished steps (hand tracking, speed, Quest display, visitor polish), the leader arm and the xArm leftovers are **on hold** in `ideas.md`. **Next focus: the JARVIS core** (brain + plug-in interfaces, roll call), ahead of the troubleshooting suite; network parts wait for the lab router. The old focus is in `docs/archive/`. | Builder's call: good enough to show; the core is what they want next, and most of it needs no router. |
| 2026-10-28 | **Naming: plain names in code and docs; show names live in persona/theme config.** A **plain name** says what a thing does and is used in code, file names, docs, logs and commit messages (e.g. `startup_sequence`, "roll call", "troubleshooting suite"). A **show name** is the in-character name JARVIS *displays or says* to people (e.g. the startup screen's title "INITIATION", the spoken line "Initiating systems…", a mode called "Overwatch"). Show names are text in the persona/theme config (`config/`), so they can change, or differ per persona, without touching code. Code never depends on a show name. Things get a show name only after they exist and run. | Plain names stay searchable and obvious to the next student; the JARVIS flavor stays fully customizable. |
| 2026-10-28 | **Robots are optional at startup:** by default the system assumes no robots are on; a robot that gets switched on appears in the system when it reports in. A "power-up walk" (expected devices shown dim with instructions) is an optional demo mode. | Often the builder only wants to code or ask something; robots are for projects, learning and demos. |
| 2026-10-28 | **One device controls a robot at a time; control is handed over** (the current driver releases), not grabbed; everyone can watch; STOP works from every device. Teleop gets this first (teleop focus step 6b, done 2026-10-29). | Two inputs interleaved on a real arm is unsafe; handing over is the safer choice. |
| 2026-10-28 | **No ghost arm lined up on the real arm.** The Quest shows a lazy-follow **HUD mini-arm** (what was commanded; joints turn red near limits) instead; the status panel also lazy-follows instead of being fixed in the room. | Lining up needs calibration and adds little: the real arm is visible; a fixed-in-room panel is awkward. |
| 2026-10-28 | **"AI lab admin" is the lab's one Meta account** for all current and future Meta devices/platforms (owns the 3 Quests; joins a Meta developer organization for developer mode). Verified with **the professor's phone number** (his OK, 2026-10-28). Handoff docs record the account and whose number is on it; the password lives in the lab's password store, never in git. | Developer mode needs the owner account to be a verified developer; any future Meta product hits the same issue; a lab-owned identity survives the builder's graduation. |
| 2026-10-27 | **xArm driver = our own ~100-line protocol layer over the `hid` package** (not the `xarm` PyPI wrapper); read-only by default, motion needs `allow_motion=True` + the builder's OK. `devices.yaml` entries may carry `usb:` (vendor/product ID, product, serial); `find_usb_device()` resolves them; so101-green is also blocked by USB serial (any OS path containing it is refused). | Cross-platform lookup by USB ID + serial; the wrapper is unmaintained; see GOTCHAS for the hidapi-vs-hid trade-off. |
| 2026-10-27 | **The brain is cross-platform: Linux (primary), Windows and macOS.** USB devices are identified by USB ID + serial number (resolved to the OS's own path at run time), not only `/dev/serial/by-id/`; the so101-green block works by its serial numbers on every OS. Robot-side code stays Linux. Needs: a non-bash install path, CI on all three, the safety hook made OS-aware. | The field laptop could be anyone's (Linux, Mac, mostly Windows); both Ubuntu desktops are busy with other projects. |
| 2026-10-24 | **Ideas live only in `ideas.md`** (single source of truth); new ideas go there, not into code, unless they're the current focus. Earlier idea lists moved there. | Keep the project finishable without losing ideas. |
| 2026-10-24 | **Triggers slot:** every on/off method (wake word, phrases, clap, card, button) is a plug-in, switchable in config and per venue. | New activation methods keep coming; each should be a small add-on. |
| 2026-10-24 | **Conversation manager** owns interrupting, queueing and turn-taking. | Keep voice-conversation behavior in one place. |
| 2026-10-24 | **One theme file (design tokens, `config/theme.yaml`) + swappable sound packs** (volume, mute); nothing hardcodes a style; a settings panel later. | Full, easy control of look and sound from one place. |
| 2026-10-24 | **Decorative layer separate from the information layer**, with an intensity setting; information always readable on top. | Rich JARVIS / cyberpunk visuals without hurting usability. |
| 2026-10-24 | **Visual quality levels full / reduced / minimal**, auto-drop on low frame rate; stricter Quest budget. Distinct from offline lite mode. | Headset frame drops cause motion sickness; slower machines still work. |
| 2026-10-24 | **The brain need not be lightweight**; robot-side code stays thin. | It runs on a desktop or laptop. |
| 2026-10-24 | **Agent changes (incl. system updates) only via branch → tests + CI → my approval → tagged deploy**; never the live system directly. | Same safety net as human changes. |
| 2026-10-24 | **Agent harness (slow path) is a swappable slot**; Claude Code / Agent SDK is one candidate (tools default-deny; motion via our safety layer). | Reuse a capable agent without giving up control. |
| 2026-10-24 | **Next focus after teleop: troubleshooting suite** (mic, cameras, robots, network, accounts, Quest; each check writes a report). | Health checks will find problems; diagnosis must be easy for me, a maintainer or an agent. |
| 2026-10-24 | **3D arm view with three.js + urdf-loader, vendored in the repo (no CDN); SO-101 drawn from its real URDF, xArm from primitives. All arms share joint names (`shoulder_pan` … `gripper`, degrees); each driver maps them to its servos.** The view draws per-command driver input (`arm_command` messages), not a sampled state. Model code is page-independent so it becomes the Quest ghost arm. No physics yet. | Offline/venue-proof; exact testing at home; one model reused on desktop and in the headset. |
| 2026-10-24 | **Teleop input = plain HTML/JS WebXR page served by the Python program (aiohttp), WebSocket JSON messages (`docs/protocol.md`); Quest reaches it over USB via `adb reverse` + `http://localhost:8080`.** No Node.js yet. First mapping is joint-space with clutch control; after any freeze the grip must be released and pressed again. JARVIS core grows out of this code rather than being designed up front. | Fewest moving parts; works at home via emulator + record/replay; localhost is a secure context for WebXR. |
| 2026-10-24 | **lab-os gets its own uv environment** (Python 3.12, uv-managed only); LeRobot for `so101-white` is added to lab-os, never to the shared `lerobot` conda env. **Serial devices are referenced only by `/dev/serial/by-id/`.** `so101-green`'s ports are off limits in code (`config/devices.yaml` + `lab_os.devices`) and via a Claude Code hook. Repo commits authored as JoshuaCYin; pushes use the lab `gh` login. | The conda env and green arm belong to the training project; `ttyACM` numbers swap between boots. |
| 2026-10-23 | **Second act = "look, then reach" with Gemini Robotics-ER 2 (API preview) first, then SmolVLA fine-tuned on our teleop data; bigger VLAs (GR00T, π0.5) only via rented GPU later; ACT only as a learning exercise.** | User wants generalization; ER generalizes without training; SmolVLA is the best-documented SO-101 route. |
| 2026-10-23 | **Repo scaffold per project-scaffold.md before feature work** (short, solo-sized); LICENSE after asking the professor (private until then); always demo from tagged known-good versions. | User wants Claude Code to include what a good project needs. |
| 2026-10-23 | **The full system must be portable** (laptop brain, travel router, venue profiles, no lab-only assumptions, offline lite mode, ≤10-minute setup). | Visitor routes may not pass the lab. |
| 2026-10-23 | **Quest teleop inputs: controllers first, then hand tracking; keep both.** Display = passthrough + minimal overlay. | Steadiness + clutch vs. wow. |
| 2026-10-23 | **Prototype teleop on `xarm1`; polish + second act on `so101-white`; teleop doubles as data collection for the training project.** | Smoother/LeRobot-native vs. available today. |
| 2026-10-23 | **Teleop requirements from the glove test; glove fix optional.** | Glove findings. |
| 2026-10-23 | **Arm names by color; `xarm1` = JARVIS-track robot + teleop prototype; `xarm2` spare.** | Clarity; separate hardware per track. |
| 2026-10-23 | **Remote Control from home confirmed; develop at home against fake robots; private GitHub repo.** | User verified; most of the system is software. |
| 2026-10-23 | **Teleop module added and fast-tracked; priority in current-focus.md; built on the seams with labeled hacks.** | Impress with fewest moving parts. |
| 2026-10-22 | Brain is portable software; remote access in stages; remote mode = no motion + dead-man stop; professor's OK before leaving a router on the wall port; wired uplink with brain on the router's network; router shortlist (pending); ask professor/IT and plan to pay; lab router replaces per-device registration; non-Pi robots via bridges; drones out of AI control. | 2026-10-22 discussion. |
| 2026-10-20 | Dev setup; standards on the ground; primary user = builder; Milestone 1 = connected lab; short animation; one client protocol; 30-s visitor demo; offline lite mode; updates off; auto-restart + AI diagnosis; ≤ $20/month; handoff docs; camera privacy deferred; professor handles IT; Quest-only + Quest vision modules. | Grill session and follow-ups. |
| 2026-10-19 | Census + capability checks; ROS 2 optional; no outreach; paper kept separate; Claude Code only on the brain desktop; SSH + deploy + one repo; phones/laptops as mics; ignition options; Quest optional; typing + push-to-talk; modularity core; model router; trained wake word; agent harness + fast path; face recognition opt-in; ~90% target; Raspbot first; config files; cloud first; keys never in git; thin-client station; reuse old spec principles. | Earlier discussion. |
| 2026-10-15 | One Linux brain + backup; 32" ViewSonic display; ~~no new router~~ (reversed 2026-10-22); few extra things; drop retro gear/camera-on-arm/live training/escape room. | Earlier discussion. |

---

## Facts about the lab
- **Status of the project (builder, 2026-11-09):** unofficial: nobody has been told yet, it may turn out useless, and it may not continue past this semester. It's about seeing what's possible. So: demo-able pieces first, cheap, nothing others come to depend on, and docs good enough for a future student to pick up.
- **Usage pattern (2026-10-28):** the lab is usually empty; startup happens when the first person arrives to a closed lab. Robots are off before that (battery-powered ones must be switched off); all need a physical switch, except the SO-101s (no switch; wall power supply).
- **Room:** desk clusters; side room with counter, SO-101 arms, beanbag; laggy big screen; projector; 32" ViewSonic monitors; noisy (fans); 3rd floor; setup movable; IWU. Visitor routes may not pass the lab.
- **Equipment check (2026-10-30):** the lab has most of the demo kit (cables, adapters, extension cords; boxes + a trolley for transport). Also a **Kinect** (version to check) and a spare webcam (the two Innomaker cameras belong to the training project). **To buy:** USB-C power bank (router/field use); **stronger table clamps** (the SO-101s' thin ones are only just sufficient). **Later, not urgent:** better cameras for lab-os (second act). Router: see Network plan.
- **Displays/wearables (2026-10-27):** 3 small (~7–9") Raspberry Pi touchscreens; a ~75" Newline touchscreen on wheels (standalone, runs Android); Google Glass Explorer Edition (boots, voice commands work).
- **Computers:** 6 RTX 5070 desktops (12 GB GPU memory, to confirm; 2 Ubuntu → brain + backup, 4 Windows 11); 5 Jetson Orin Nano; several Pi 5s. Remote Control from home works.
- **Network:** lab Wi-Fi with MAC registration via campus IT; wall Ethernet port works.
- **Domain:** the lab owns `indwesailab.com` (bought summer 2026 for one year: renew by summer 2027 or the certificates stop). The university didn't want it as the lab's public face, so only a subdomain is used, for lab screens. **DNS is on AWS Route 53** (checked 2026-11-09: the domain's name servers are `awsdns`); the builder has the AWS login (set up with the professor, summer 2026). The main domain still serves an old public website from S3 that was never removed; the `hub.` subdomain doesn't touch it.
- **AI access (updated 2026-10-30):** OpenAI keys (primary; the professor's account, paid by the university: believed 2026-11-09, not confirmed); free Gemini keys (free tiers may use data for training: check terms); the Anthropic key is out of credits (Gemini Robotics-ER 2 preview is on the Gemini API).
- **Mics:** 4 weak USB dongle mics; phones/laptops; old Nokias/Pixel C; Quest mic + speakers.
- **Robots:** Raspbot v2 ×2; SO-101 green set (in use elsewhere); SO-101 white set (to build — this project); xArm 1S ×2 (`xarm1` works); Hiwonder glove ×2; TonyBot v1; PiCar Pro ×3 (unbuilt); Air:bit 2 ×3; Quest 3 ×3; card reader. No wheels+arm robot.
- **Builder:** CS student; learns with AI; Python + web; dislikes the CLI, likes VS Code + Claude desktop/web UI; 3–7 h/week; graduating May 2027; lives ~5 min from campus.

---

## Open questions
- **Second act:** can the Kinect's depth camera help "look, then reach" (3D position directly, less camera-to-table calibration)? Which Kinect version, and does it run on our OS? ER pointing accuracy with our camera; camera-to-arm calibration method; ER preview pricing/free-tier limits and data terms; ~~SmolVLA training on 12 GB~~ (works: ~8 GB with the VLM frozen, 2026-11); cloud GPU option/cost for bigger models.
- **License/ownership:** what does the professor/university allow?
- **Portability:** which laptop is the field brain; venue internet; batteries vs. outlets; where visitor routes go.
- **Teleop spikes:** `xarm1` speed/delay; Quest WebXR data, overlays, USB forwarding (Quest developer mode / Meta account access); IK library; `so101-white` calibration; end-to-end delay.
- **Glove** firmware source; **training project** plans for `so101-white`; **IT/professor** router questions; overlay network; cellular.
- TonyBot v1 board; wake word from the doorway; waking screens; Quest camera access; Quest-only practicalities; past Quest demo contact; offline lite mode contents; use cases beyond development; HTTPS for browser mic/WebXR; mic test; model router; agent harness; free-tier data terms; persona name; voice pipeline; Raspbot internals; humanoid SDK.

---

## Discussion notes & considerations
- **Generalization reality:** no robot model is magic yet; "look, then reach" generalizes for simple pick-and-place; learned skills generalize better with varied training data and pretrained models.
- **Portability rule of thumb:** anything tied to a specific room, computer or address won't travel; anything defined by a name, profile or plug-in will.
- **Absolute vs. relative control:** teleop should be relative (no snapping).
- **Impressiveness from first principles:** break an expectation; seconds to understand; narrow, controlled demo; filmable; don't overclaim; fewest moving parts.
- **Separate hardware per track** avoids blocking.
- **Training project + lab-os at the same time (2026-10-28):** the builder also works on the so101-green training project (now: preparing to record data). Keep them apart: separate folders, separate VS Code windows / Claude Code sessions (lab-os's hook would block legitimate training commands), separate environments (conda `lerobot` vs lab-os uv). Shared-desktop conflicts: a serial port or camera can be opened by only one program at a time; don't run lab-os hardware tests while a recording runs. The two USB cameras on the lab desktop belong to the training setup (confirmed 2026-10-28) → off limits in lab-os (GOTCHAS 2026-10-28).
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
Moved to **`ideas.md`** (2026-10-24), the single source of truth for ideas.
