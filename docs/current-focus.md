# Current Focus: the JARVIS hub + AI driving a robot arm

**Read this at the start of every Claude Code session.** It says what to work on *now*. The long-term plan, decisions and module list live in **lab-jarvis-log.md**; this file only sets the current priority. When this focus is done, move it to `docs/archive/` and write the next one. Previous focus: the teleop demo, closed 2026-10-30 (`docs/archive/focus-2026-10-teleop-demo.md`; what's left of it is in `docs/ideas.md` → "On hold").

---

## The goal right now
The hub is left running **full screen** on the Newline or a lab desktop, waiting at its start screen. Someone curious taps it: the startup plays, with sound, and lands in the **hub**: buttons into the system (teleop today, more later), panels of real project facts, and the **assistant**, a picture that breathes and reacts. They ask it something, typed or **by voice**, and it answers. In the lab, the builder can also have an AI drive `so101-white` (Fable 5.2 in Claude Code, through the brain's tools).

**Two phases (decision 2026-11-09):**
- **Phase 1, make it work (steps 1–8): plain looks on purpose.** Everything works, but the pages stay simple: dark background, system fonts, no animation, a plain circle for the assistant. **Don't apply the approved design yet**, not even partly: it's a surprise, and people in the lab see the screens while the builder works.
- **Phase 2, the reveal (step 9): the full design in one sitting** (about 1–2 hours, uninterrupted), once at least one or two things plus voice can be demoed. Then it's left on a screen for someone to find.

**The design is approved** (2026-11-09): `docs/design/DESIGN.md` (the why), `docs/design/hub-concept.html` (how it looks, moves and sounds; open it with `#skip` to jump to the hub) and `config/theme.yaml` (the numbers). Phase 1 doesn't copy its looks, but **does copy its structure** (see "Ready for the reveal" below), so the reveal is mostly a new skin.

Roll call and robot connections over the network wait for the lab router (`ideas.md` → "On hold").

## How it fits together (design shapes for this focus)
- **One brain program, `lab-os serve`.** It serves the hub page and mounts the teleop pages inside it. The core grows out of the teleop code (decision 2026-10-24). `lab-os-teleop` keeps working until it's replaced.
- **The brain is an MCP server** (decision 2026-11-09): it offers tools (read the arm, move the arm, take a picture, read the docs) in a standard format that AI tools understand. Claude Code, Codex and Claude Desktop connect to it; the hub's own chat uses the read tools. Tools are grouped in permission tiers (read / act / move / admin; table under "After this focus").
- **The assistant's state is separate from its picture.** The state is a short list: `idle`, `listening`, `thinking`, `speaking`, `offline`, `error`, plus a 0–1 "loudness" while speaking. That's the information layer. The rest of the system only sets the state. The **picture** (decorative layer) is chosen by the persona and only reads the state. In phase 1 the picture is a plain circle that changes color (like `minimal` quality); the reveal swaps in the real one without touching the hub, chat or voice code.
- **Personas are config files**, `config/personas/<id>.yaml`. The active persona is set per venue profile; the default is the plain one. Example:
  ```yaml
  version: 1                    # file format version
  id: jarvis                    # plain name (code, files)
  display_name: "J.A.R.V.I.S."  # show name (on screen)
  personality: jarvis.md        # how it talks: a short text file next to this one
  model: main                   # which AI setup (defined once in config/models.yaml)
  voice: none                   # step 7
  wake_word: none               # later
  picture: { type: orb, style: calm-ring, color: primary }
  lines:                        # things it says
    greeting: "All local systems are up."  # the plain line, used when there's no news
  sounds: default               # sound pack
  ```
  **The greeting** (DESIGN.md → "Startup"): the brain says "Good morning / afternoon / evening." and then **one line of real news** when there is some (an alert, a device that dropped out, the budget running low, a step finished, a busy day, the calendar); otherwise the persona's `greeting` line. The news line is built by the brain from real facts, never by the persona. The chat's first message starts with the same line. **The startup title is not a persona line:** it is the lab's name, `hub.title` in the theme ("AI Comp Lab"), the same for every persona.

  **Must stay extensible:** the loader checks the fields it knows, keeps unknown fields and **warns** about them (no crash), so new fields can be added any time. Two personas in v1: **`lab-assistant`** (default; plain name, simple circle, no character) and **`jarvis`** (the show persona). The persona changes picture, voice, lines and sounds; **the theme (colors, fonts) stays the same** for all personas.
- **The hub's buttons come from config** (`hub.modules` in the theme), so a new module adds a button without changing the hub. No fake "coming soon" buttons ("only claim what's real").
- **The status strip and panels show only real facts.** Status strip: venue, persona, internet yes/no, AI connected yes/no, clock. Where something isn't real yet, leave it out instead of faking it.
- **Offline vs. internet.** Offline: start screen, hub, the assistant's picture, teleop, sounds, theme, fonts. Needs internet: the AI chat and cloud voices. Without internet the assistant shows `offline` and everything else works.
- **A public screen** (the Newline, a hallway desktop): anyone can start it and talk to it, so: the start screen says "Safe to start. This only opens the hub; no robot moves."; the hub's chat stays in the read tier; the move tools only accept AI tools on the brain's own computer; a **spend cap** pauses the chat when it's reached; the conversation clears on the reset; the venue profile hides internal details (IP addresses, spend).
- **Two taps (decision 2026-11-09).** Browsers allow full screen and sound only after a press, so:
  1. **Tap 1 = full screen.** The idle start screen goes full screen (and sound is unlocked). This is the builder's tap when leaving the hub on a screen; skipped when the page is already full screen (kiosk mode, F11, an installed app) or the browser can't do it.
  2. **Tap 2 = start.** The visitor's tap: the unlock and the startup (hyperspace by default), then the hub.
  - If full screen is lost (a swipe, Esc, a reload), the start screen asks for tap 1 again.
- **Back to the start screen when nobody's there (decision 2026-11-09):** after ~3 minutes with no input (a setting, e.g. `hub.reset_after_s: 180`, a venue can change it), the hub closes any open module, clears the conversation from the screen (the next visitor shouldn't see the last one's questions) and returns to the start screen, still full screen, so the next person only needs tap 2. **Never while something is in use:** teleop has the arm, the AI tools are moving it, or a voice turn is running.
- **Sound** is generated in the browser (WebAudio) until real ones exist.

## Rules for this focus
1. **Grow it out of the teleop code**: extract what exists; formal interfaces only when a second real user needs them.
2. **Fake first, offline first**: every step runs without hardware and (except the AI steps) without internet. The robot tools run on the fake arm before the real one.
3. **Only claim what's real**: the start screen, status strip and panels never show a check or number that didn't happen.
4. **Plain until the reveal**: phase 1 pages use no fonts, colors, animations or sounds from the design beyond a dark background and readable text. Visible design work waits for step 9.
5. **The hub's built-in assistant never changes anything in this focus.** It reads and answers. The **move tools** (step 2) are for a developer's AI tool on this computer only: same safety layer as teleop, **ask every time** (move tier). Writing code by AI comes later, and only via branch → tests → the builder's approval (decision 2026-10-24).
6. **Secrets** (API keys) only in `.env`; `.env.example` lists the names.
7. **Portable**: Linux, Windows, macOS (decision 2026-10-27). **Plain names** in code, show names in persona files (decision 2026-10-28).
8. **The green arm and its training cameras stay off limits** (CLAUDE.md hard rules), including for the AI tools and camera code.

## Steps (each one is a small, testable win)
The Current Project panel reads this list: each step's **bold title** is what the hub shows ("Next: Plain hub"), so titles are short plain words. A finished step gets `(done YYYY-MM-DD)` right after its title.

0. **Settle before coding** (done 2026-11-09) (planning sessions):
   - **AI service (settled 2026-10-30):** **OpenAI first**; free Gemini keys as a backup; the Anthropic key is out of credits. **Local models** as a second setup. **Keys (2026-11-09, believed, not confirmed):** the OpenAI account is the professor's, paid by the university. Budget ≤ $20/month so far.
   - **Design: done (2026-11-09, approved by the builder)**, including the startup. Used in step 9 only. Later design changes go through a design session in `~/lab-os-design` (branch `design`).

### Phase 1: make it work (plain looks)
1. **Plain hub.** `uv run lab-os serve` serves a plain hub page:
   - a **start screen with the two taps**: tap 1 "Tap for full screen" (skipped when already full screen), tap 2 "Tap, click or press any key to start" + "Safe to start. This only opens the hub; no robot moves." (this also answers "full screen on the Newline's Chrome", which has no full-screen button). Modules open **inside** the hub page (no page loads), because loading a new page leaves full screen. In Chrome/Edge, use the Keyboard Lock API in full screen so Esc can mean "Back" without leaving full screen;
   - the **reset to the start screen** after ~3 minutes with nobody there (see "How it fits together");
   - the **status strip** (venue, internet yes/no, AI: not connected, clock);
   - **module buttons from `hub.modules`** that open the existing teleop and monitor pages (inside the hub, with Back/Esc);
   - a **plain circle** for the assistant (one color per state);
   - **Current Project** (read from this file's Steps list: "Step N of M", "Next: <bold title of the first step not done>") and **Commits** (per day from `git log`, 7/14/30 days) as plain text or a simple bar list.
   - Brain side: small JSON endpoints (`/api/status`, `/api/project`, `/api/commits?days=14`); internet checked in the background (~every 30 s). Move the shared web files (`vendor/`, `theme.js`) to one folder both use, e.g. `src/lab_os/web/`; update the vendor README and the path in CLAUDE.md. The teleop pages and `/ws` keep working from the Quest (update `docs/quest-setup.md` if its address changes).
   - Tests (no hardware, no internet): pages and endpoints answer; the Steps parser on a sample file; commit counting on a temporary git repo; **no `http://` or `https://` loads in any web file**.
   - **Done when:** it runs offline, teleop with the fake arm works when opened from the hub, `ruff` + `pytest` pass, and **the two taps work on the Newline** (full screen, start, a module, Back, reset).
   - **Also in step 1, a performance test page** (`/perf`): only drifting dots, links and star streaks on a black page (no frame, no core, no hub: nothing that gives the design away), at the screen's full size, showing frames per second. Run it on the Newline (a 4K panel on a phone-class chip) and the Pi screens, so step 9 knows which quality level each screen can carry.
   - **Status (2026-11-09):** built and checked on a laptop (headless Chrome: the two taps, a module, Back/Esc, the reset and "not while teleop has the arm", teleop driving the fake arm from inside the hub). **Left before it's done:** the two taps on the Newline, and `/perf` numbers from the Newline and the Pi screens. How to run it: `docs/hub.md`.

2. **Robot tools for AI.** The brain becomes an MCP server with tools for `so101-white`, so an AI tool can drive it **blind** (no camera yet; the builder describes the scene in words). Fake arm first, then the real one. Details: "Step 2, concretely". **Before 2026-11-16** if possible (end of the builder's Fable access); after that the same tools work with any AI tool, so nothing is lost by waiting except trying Fable.

3. **Cameras for the AI.** A `camera_snapshot` tool (read tier) for the white arm's **two cameras**, so the AI can look before it reaches. Details: "Step 3, concretely". As soon as step 2 works.

4. **Personas.** Loader + the two persona files + `config/models.yaml` (the AI setups, no keys). The venue profile picks the persona; the status strip shows it; switching is a config edit + reload. The brain builds the greeting's news line from real facts (so far: a step finished, the calendar, a busy day of commits); otherwise the persona's `greeting` line, shown as plain text after the start press.

5. **Typed chat.** One AI model: **OpenAI**, API key in `.env`. Through the widely copied **OpenAI-style chat interface**, so other setups in `config/models.yaml` differ only by address, model name and key name: Gemini (OpenAI-compatible address) and **local models** (Ollama or llama.cpp's server). Optional: a `local` setup that proves the switch and works offline. Careful on the lab desktop: its GPU is shared with the training project. A small **conversation manager** owns the turn and sets the assistant's state (`thinking` → `speaking` → `idle`). Plain ask line under the circle ("Ask anything"; typing anywhere lands there), the answer under it, a plain conversation history. Answers stream in. Uses the persona's personality text. Logs the cost per chat and has a **spend cap** (a setting) that pauses the chat with a full-sentence message.

6. **Project helper (read tools).** The MCP server from step 2 gets read tools for the project: `docs/` (current focus, ideas, log, GOTCHAS), git status/history, device list. The hub's chat uses them to answer "what's next?" or "what's on hold?" and **drafts the prompt to paste into a Claude Code / Codex session**; a developer's Claude Code or Codex can use the same tools. The hub's chat gets **read tools only**; the server listens on this computer only.

7. **Voice** (part of the demo now, not a stretch; typing must not suffer). Push-to-talk first (hold a key, or hold a button on a touch screen, speak, it answers aloud); the circle follows the voice's loudness (state `listening`, `speaking` + loudness). Decide the route here: a realtime voice service (OpenAI's or Google's; handles interruptions; per-minute price; needs internet) or speech-to-text → our chat model → text-to-speech (same model as typing; slower). Fan noise is why push-to-talk comes first. **Voice works on whatever screen the hub is on**, which needs the secure address: see "Step 7, concretely". **No microphone, no voice button:** typing always works. Wake word later.

8. **Demo check (plain).** On the plain hub, with nobody's help: start it from the start screen, teleop the fake arm, ask a typed and a spoken question, have the AI move the arm (step 2). Fix what breaks. Tag the version. Phase 1 is done.

### Phase 2: the reveal (one sitting)
9. **The design.** **Build to match the concept page** (DESIGN.md → "Building the real hub": what to take, what to leave): fonts bundled (instead of the concept's Google Fonts link; files in `vendor/fonts/` with their licenses), every number from `/theme.json`, the frame and network, the core with every state, the module buttons and traces, the panels as callouts with their details pages, the ask line and reply under the core, the startup (unlock; **`hyperspace` by default**, with `assemble` and "per venue" as the other choices of `startup.style`, decision 2026-11-09; update the theme then; real checks, the title decoding `hub.title`, the greeting; **about 8 s including the unlock**, any input skips), sounds from the concept's `SFX`, quality levels. Then leave it at the start screen on the Newline or a desktop.

   **Making it fit 1–2 hours** (the concept is ~2,500 lines; a full port in one sitting is tight):
   - Phase 1 already has every part with the same structure and real data (see "Ready for the reveal"), so step 9 is mostly lifting the concept's CSS, SVG and JavaScript onto parts that work.
   - Prep that shows nothing on screen can happen earlier: download and license the font files, list which concept functions go where.
   - If time runs short, this order: the look of the hub + the core and its states → the startup → the panels' details pages → the rest. Whatever isn't done stays plain and gets finished in a second sitting.
   - Alternative that removes the time limit: do step 9 away from the lab on a laptop (it runs with the fake arm, offline), on a branch, and only bring it to the lab's screens when it's done.

### Ready for the reveal (phase 1 rules that make step 9 quick)
- The plain pages have **the same parts as the concept** (status strip, module buttons, core, ask line, reply, panels, start screen) in separate, clearly named elements, so step 9 restyles them instead of rebuilding.
- **All data comes from the brain's endpoints** (status, project, commits, assistant state, chat), never from the page, so the designed page reads the same endpoints.
- The **assistant's state and loudness** are already sent to the page (step 5, 7); the picture only reads them.
- The pages already read `/theme.json` for the few values they use (e.g. `hub.title`, `hub.modules`, `clock`), so the design's numbers slot in.

### Step 2, concretely (robot tools for AI)
**Goal:** in a Claude Code session on the lab desktop, the builder types "pick up the cube that's 15 cm in front of the base and put it 10 cm to the left", and the AI does it on `so101-white` through the brain's tools, asking before every move.

- **Which AI:** Claude Code with **Fable 5.2** (pick it with `/model`; the builder's subscription covers it, so no API key; to verify it shows in the list). Nothing is tied to Fable: any MCP client works (Codex, Claude Desktop).
- **The connection:** the brain offers its tools over MCP on `localhost` only (the official `mcp` Python package; a separate port is fine). Connect with something like `claude mcp add --transport http lab-os http://127.0.0.1:<port>/mcp`; write the exact command in a new `docs/ai-control.md`.
- **Tools** (shared joint names, degrees; the arm chosen by its lab-os name):
  - read: `arm_status` (connected?, joint angles, gripper, limits, who has control, held or not), `list_poses`.
  - move: `move_joints` (absolute or relative angles for some joints), `gripper` (0–100 % open), `move_to` (x, y, z in cm from the arm's base, with the existing `kinematics.py` IK; says "can't reach" instead of guessing), `go_to_pose` (named poses such as `home`, `rest`, from config).
  - `stop`: always allowed, from any tier.
- **Safety:** every move goes through the same path as teleop (the driver's soft limits, the venue's `max_speed_scale`, smoothing). The brain **clips and refuses**, never trusts the model's numbers: a maximum change per call (a setting, e.g. 30° per joint or 10 cm), and refusal when the venue has `motion_allowed: false`. **One controller at a time:** while teleop has the arm the move tools refuse ("teleop has control"), and the other way round; STOP from any page wins. **Asks every time:** never allow-list the move tools in Claude Code, so each move shows a permission prompt (the read tools may be allow-listed). The move tools return the arm's real position afterwards, so the AI sees what actually happened.
- **Other screens while a real arm is connected** (today `lab-os serve --host 0.0.0.0` refuses real arms, which would stop the Newline showing the hub during the demo): allow them, but **view only**: the hub, the monitor/arm view and the chat, no teleop control and no moving. **STOP works from every screen** (decision 2026-10-28). Control stays with this computer and the Quest (`adb reverse`), and later with signed-in devices.
- **Fake arm first** (watch it on the monitor page), then the real `so101-white`, with the builder present (CLAUDE.md: ask before anything that makes a real robot move).
- **A log of every call** (time, tool, arguments, clipped or refused, the result) per session, so runs can be compared later (e.g. with SmolVLA's ~30% on the green arm).
- **Protocol:** list the tools in `docs/protocol.md`.
- **Done when:** the fake arm does the cube task from a Claude Code prompt; then the real arm does it, with every move approved; a test proves clipping, refusal while teleop has control, and `stop`.

### Step 3, concretely (cameras for the AI)
- **The cameras:** the white arm's two cameras are the **same model as the green arm's training cameras** (Innomaker U20CAM). Both training cameras report the **same serial number `SN0001`** (GOTCHAS 2026-10-28), and the white ones very likely do too (check: `ls -l /dev/v4l/by-id/ /dev/v4l/by-path/` lists the names without opening any camera). So they can only be told apart by the **USB socket** they're plugged into: use `/dev/v4l/by-path/…` names, **never** `/dev/videoN` (numbers change) and never the by-id names (they collide).
- At the lab: plug the white cameras into fixed sockets, label sockets and cables, record their by-path names in `config/devices.yaml` with what each one sees (e.g. `so101-white-cam-top`, `so101-white-cam-wrist`). The training cameras' sockets (1-7 and 1-8) are marked `off_limits`, and the camera code refuses any camera that isn't listed.
- **The tool:** `camera_snapshot(camera)` (read tier) opens the camera, takes one picture, closes it, and returns a small JPEG (about 640 px wide: images cost the AI tokens). Camera library added to this project with `uv add` (e.g. OpenCV, headless).
- **Done when:** the AI looks, then reaches: "pick up the red block" with no positions given in words.

### Step 7, concretely (voice on any screen)
- **Who does what:** the page only records and plays. It captures the microphone in the browser, streams the audio to the brain over the WebSocket, plays the reply, and reports the loudness to the assistant's picture. The brain talks to the voice service, so **API keys never leave the brain** and every screen works the same way.
- **The microphone needs a "secure" page**: browsers give it only to pages on `https://` or `http://localhost`. Same rule for keeping the screen awake (Wake Lock), installing the hub as an app, and WebXR on the Quest. So the brain gets **a real address with a real certificate (decision 2026-11-09):**
  - The lab owns **`indwesailab.com`** (bought summer 2026 for a year, unused). Use a subdomain only, e.g. **`hub.indwesailab.com`**, pointing to the brain's address on the lab network. No public website; the main domain stays unused. **Check with the professor that this is fine.**
  - A free **Let's Encrypt** certificate through a DNS check (the brain proves it owns the name by adding a DNS record, so it never has to be reachable from the internet). Renewed automatically; needs internet once every ~2 months (certificates last 90 days today, 64 from Feb 2027, 45 from Feb 2028). The DNS is on **AWS Route 53** (certbot's `dns-route53` plugin or `lego` handle it). Give the brain its **own limited AWS key** that may only change records in this one zone (an IAM user/policy), stored in `.env`; never the main AWS login. The main domain's old S3 website stays as it is.
  - Offline: the certificate keeps working until it expires, but the name must still resolve: the lab router answers `hub.indwesailab.com` itself (a local DNS entry; `network-setup-checklist.md`).
  - Bonus: the same address lets the Quest run teleop **over Wi-Fi** (no USB cable or `adb reverse`), keeps screens awake, and lets the Newline or iPad install the hub as a full-screen app.
- **Fallbacks, easiest first** (when the real certificate isn't there yet, or a screen can't use it):
  1. **The brain's own screen:** a browser on the brain's computer opens `http://localhost:…`: always secure, no certificate, works offline.
  2. **Chrome's flag** on Android and desktop Chrome: `chrome://flags` → "Insecure origins treated as secure" → add the brain's address. Per device; not on the iPad; may reset after Chrome updates.
  3. **USB like the Quest:** `adb reverse` lets an Android device open the brain as `http://localhost` over a USB cable (the Newline only if it allows USB debugging).
  4. **Our own certificate authority** (e.g. `mkcert`): install its certificate on each device. Works offline forever; installing may be locked on the Newline.
  5. **No secure page, or no microphone:** voice is off on that screen and its button is hidden; typing works.
- **Microphone detection:** show push-to-talk only when the page is secure **and** the browser lists an audio input (`navigator.mediaDevices.enumerateDevices()`); react to plugging and unplugging (`devicechange`); if permission is refused, hide it with a short sentence why. The first use on each device asks "Allow microphone?" once (someone must tap Allow; on HTTPS Chrome remembers it). The Newline Q+ series has a built-in 8-microphone array (to confirm on our Q+ Pro). Push-to-talk plus the browser's echo cancellation keeps the speakers out of the microphone.

## After this focus: AI-assisted development (direction, decisions 2026-10-30 and 2026-11-09)
The goal: anyone working on lab-os can use AI to change the system **and** the connected devices (robots, Pis), without depending on one person's subscription. Two routes, same rules:
- **Bring your own AI tool:** each developer uses their laptop with VS Code + the Claude Code extension, Codex, or Claude Desktop: clone the repo, connect the tool to the brain's MCP server (with a personal access token, once remote access exists). Works with whatever the person has.
- **Lab-paid harness in the hub:** a **"send to harness" toggle** on the chat line (plus a setting to send everything) hands the request to a coding agent running on the brain with the lab's API key: Codex with the OpenAI key (to verify: it accepts an API key instead of a subscription), or Claude Code with an Anthropic key if refilled. Monthly spend cap.

**Rules for both:** code changes only on a branch (`agent/<task>` for the lab harness) → tests → PR → the builder approves; never edit the running system. Device actions go through the brain's tools in **permission tiers**:
| Tier | Examples | Who |
|---|---|---|
| read | device status, logs, docs, arm readouts, camera snapshots | everyone, incl. the hub's built-in chat |
| act | "find me" beep, restart a service on a Pi, deploy a tagged version to a robot | developers with a token; asks first |
| move | anything that makes a robot move | developers, through the safety layer, asks every time; off in remote mode |
| admin | `sudo`, deleting, reboots, off-limits devices | humans only, never through tools |

The hub's built-in chat stays in the read tier (anyone in the room can type into it); a later sign-in could raise that. Realistic workflows behind these choices: `docs/use-cases.md`.

## Also this week (not a lab-os step)
- **The Newline, full screen, for another project** (due Wed/Thu 2026-11-11/12): options and a test plan in `ideas.md` → "Screens without browser bars". The builder also checks whether Newline Signage Pro can show a web page.

## Hacks to clean up
- `robots/xarm.py`: 240°/1000 units is the datasheet scale, not measured (zero = the "Run" pose, signs observed 2026-10-27). Motion tuning (`lead_s` 0.3 s, `max_deg_per_s` 120, `idle_read_after_s` 0.6, `min_read_interval_s` 0.25) is from first tests, not optimized. Default limits (until hand calibration) come from the builder's grab script.

## Up next (after this focus)
Milestone 1, "Connected lab", once the router is here: roll call, robots reporting in, the Devices panel, `xarm1` as the second robot through the core (`ideas.md` → "On hold" → "Core plumbing"). Other paused work: `ideas.md` → "On hold".
