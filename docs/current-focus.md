# Current Focus: the JARVIS hub + AI driving a robot arm

**Read this at the start of every Claude Code session.** It says what to work on *now*. The long-term plan, decisions and module list live in **lab-jarvis-log.md**; this file only sets the current priority. When this focus is done, move it to `docs/archive/` and write the next one. Previous focus: the teleop demo, closed 2026-10-30 (`docs/archive/focus-2026-10-teleop-demo.md`; what's left of it is in `docs/ideas.md` → "On hold").

---

## The goal right now
You press a key at the lab desktop. The startup plays, with sound, and lands in the **hub**: one full-screen page on the 32" monitor with buttons into the system (teleop today, more later), panels of real project facts, and the **assistant**, a picture that breathes and reacts. You type a question ("what's next on the project?") and it answers, using the project's own docs. Its look and voice come from the loaded **persona**.

**And, this week:** an AI model (Fable 5.2 in Claude Code) drives `so101-white` through tools the brain offers (step 2), first blind, then with the arm's own cameras (step 3). The builder's Fable access ends **2026-11-16**, so steps 2–3 come right after the first hub page.

**The design is approved** (2026-11-09): `docs/design/DESIGN.md` (the why), `docs/design/hub-concept.html` (how it looks, moves and sounds: open it in a browser, add `#skip` to jump to the hub) and `config/theme.yaml` (the numbers). Steps 1, 5 and 6 **build to match the concept page**; DESIGN.md → "Building the real hub" says what to take and what to leave.

Roll call and robot connections over the network wait for the lab router (`ideas.md` → "On hold").

## How it fits together (design shapes for this focus)
- **One brain program, `lab-os serve`.** It serves the hub page and mounts the teleop pages inside it. The core grows out of the teleop code (decision 2026-10-24). `lab-os-teleop` keeps working until it's replaced.
- **The brain is an MCP server** (decision 2026-11-09): it offers tools (read the arm, move the arm, take a picture, read the docs) in a standard format that AI tools understand. Claude Code, Codex and Claude Desktop connect to it; later the hub's own chat uses the same tools. Tools are grouped in permission tiers (read / act / move / admin; table under "After this focus").
- **The assistant's state is separate from its picture.** The state is a short list: `idle`, `listening`, `thinking`, `speaking`, `offline`, `error`, plus a 0–1 "loudness" while speaking. That's the information layer. The rest of the system only sets the state. The **picture** (decorative layer) is chosen by the persona and only reads the state. New picture styles never touch the hub, chat or voice code. `minimal` quality is a still circle that only changes color.
- **Personas are config files**, `config/personas/<id>.yaml`. The active persona is set per venue profile; the default is the plain one. Example:
  ```yaml
  version: 1                    # file format version
  id: jarvis                    # plain name (code, files)
  display_name: "J.A.R.V.I.S."  # show name (on screen)
  personality: jarvis.md        # how it talks: a short text file next to this one
  model: main                   # which AI setup (defined once in config/models.yaml)
  voice: none                   # later (step 9)
  wake_word: none               # later
  picture: { type: orb, style: calm-ring, color: primary }
  lines:                        # things it says
    greeting: "All local systems are up."  # the plain line, used when there's no news
  sounds: default               # sound pack
  ```
  **The greeting** (DESIGN.md → "Startup"): the brain says "Good morning / afternoon / evening." and then **one line of real news** when there is some (an alert, a device that dropped out, the budget running low, a step finished, a busy day, the calendar); otherwise the persona's `greeting` line. The news line is built by the brain from real facts, never by the persona, so every persona tells the same truth in its own words. The chat's first message starts with the same line. **The startup title is not a persona line:** it is the lab's name, `hub.title` in the theme ("AI Comp Lab"), the same for every persona.

  **Must stay extensible:** the loader checks the fields it knows, keeps unknown fields and **warns** about them (no crash), so new fields can be added any time. Two personas in v1: **`lab-assistant`** (default; plain name, simple circle, no character) and **`jarvis`** (the show persona). The persona changes picture, voice, lines and sounds; **the theme (colors, fonts) stays the same** for all personas.
- **The hub's buttons come from config** (`hub.modules` in the theme), so a new module adds a button without changing the hub. No fake "coming soon" buttons ("only claim what's real").
- **The status strip and panels show only real facts.** Status strip: venue, persona, internet yes/no, AI connected yes/no, clock. Where something isn't real yet, leave it out instead of faking it.
- **Offline vs. internet.** Offline: startup, hub, the assistant's picture, teleop, sounds, theme, **fonts** (bundled). Needs internet: the AI chat and (later) cloud voices. Without internet the assistant shows `offline` and everything else works.
- **Looks:** every number comes from `config/theme.yaml` (served as `/theme.json`); the concept page hard-codes them, but where a token exists, the token wins. Quality levels maximal / full / reduced / minimal; libraries and fonts are vendored, no CDN (CLAUDE.md).
- **Sound:** browsers block all sound until the user clicks or presses a key. So the startup **starts with a key press, click or touch** (the "ignition"), which also unlocks the sound. Sounds are generated in the browser (WebAudio; the recipes are in the concept page's `SFX` object) until real ones exist: offline, no license questions. Volume/mute in the sound pack.

## Rules for this focus
1. **Grow it out of the teleop code**: extract what exists; formal interfaces only when a second real user needs them.
2. **Fake first, offline first**: every step runs without hardware and (except the AI steps) without internet. The robot tools run on the fake arm before the real one.
3. **Only claim what's real**: the startup, status strip and panels never show a check or number that didn't happen.
4. **The hub's built-in assistant never changes anything in this focus.** It reads and answers. The **move tools** (step 2) are for a developer's AI tool on this computer only: they go through the same safety layer as teleop and **ask every time** (move tier). Writing code by AI comes later, and only via branch → tests → the builder's approval (decision 2026-10-24).
5. **Secrets** (API keys) only in `.env`; `.env.example` lists the names.
6. **Portable**: Linux, Windows, macOS (decision 2026-10-27). **Plain names** in code, show names in persona files (decision 2026-10-28).
7. **The green arm and its training cameras stay off limits** (CLAUDE.md hard rules), including for the AI tools and camera code.

## Steps (each one is a small, testable win)
The Current Project panel reads this list: each step's **bold title** is what the hub shows ("Next: First hub page"), so titles are short plain words. A finished step gets `(done YYYY-MM-DD)` right after its title.

0. **Settle before coding** (planning sessions):
   - **AI service (settled 2026-10-30):** **OpenAI first** (where the keys are); free Gemini keys as a backup; the Anthropic key is out of credits. **Local models** (running on our own computer, no internet) as a second setup. Still open: are the OpenAI keys the lab's/professor's or personal (matters for "not one person's account"), and the monthly budget (≤ $20/month so far).
   - **Design: done (2026-11-09, approved by the builder)**, including the startup (it replaced the old "startup prototypes" step): ignition unlock, assemble or hyperspace jump, checks, greeting. Later design changes go through a design session in `~/lab-os-design` (branch `design`), which edits only `docs/design/` and the theme.

1. **First hub page** (the brain program + the hub skeleton). **Build to match the concept page.** Details: "Step 1, concretely" below.

2. **Robot tools for AI.** The brain becomes an MCP server with tools for `so101-white`, so an AI tool can drive it **blind** (no camera yet; the builder describes the scene in words: "the cube is 10 cm left of the base"). Fake arm first, then the real one. Details: "Step 2, concretely" below. **Deadline: before 2026-11-16** (end of the builder's Fable access).

3. **Cameras for the AI.** A `camera_snapshot` tool (read tier) for the white arm's **two cameras**, so the AI can look before it reaches. Details below. As soon as step 2 works.

4. **Personas.** Loader + the two persona files + `config/models.yaml` (the AI setups, no keys). The venue profile picks the persona. The status strip shows it. Switching the persona is a config edit + reload. The brain builds the greeting's news line from real facts (the cases it can know so far: a step finished, the calendar, a busy day of commits); otherwise the persona's `greeting` line.

5. **The assistant's picture.** **Build to match the concept page:** the core's rings, every state (idle, listening, thinking, speaking with loudness, offline, error), the network's pulses toward/away from the core, all four quality levels, a hidden test control to flip states (no AI yet). Colors and timings from the theme; style from the persona.

6. **The startup.** **Build to match the concept page:** the ignition screen (lists the inputs this device really has, "Safe to start. This only opens the hub; no robot moves."), the unlock with its sound, `assemble` (default) and `hyperspace` (`startup.style`), the checks, the title decoding `hub.title`, the greeting, everything flying to its place on the hub. **About 8 s including the unlock** (`startup.max_s`), and **any input skips straight to the hub**. Shows only real checks ("Persona loaded", "Internet: online", "AI: not connected"). Respects quality levels and mute. The ignition press also switches the page to **full screen** (browsers only allow that after a key press or click), so no tabs or address bar show (other screens: `ideas.md` → "Screens without browser bars").

7. **Typed chat.** One AI model: **OpenAI**, API key in `.env`. Talk to it through the widely copied **OpenAI-style chat interface**, so that other setups in `config/models.yaml` differ only by address, model name and key name: Gemini (it offers an OpenAI-compatible address) and **local models** (Ollama or llama.cpp's server run one on our own computer and speak the same interface). **Optional within this step:** a `local` setup proves the switch and gives a chat that works offline (offline lite mode). Careful on the lab desktop: its GPU is shared with the training project, so don't run a local model during a recording; a laptop works too. A small **conversation manager** owns the turn and sets the assistant's state (`thinking` → `speaking` → `idle`). The ask line under the core, the answer under the core, the conversation page, as in the concept. Answers stream in. Uses the persona's personality text. Logs the cost per chat (feeds the AI Spend panel). Built so voice can plug into the same conversation manager later.

8. **Project helper (read tools).** The MCP server from step 2 gets read tools for the project: `docs/` (current focus, ideas, log, GOTCHAS), git status/history, device list. The hub's own chat uses them to answer "what's next?" or "what's on hold?" and **drafts the prompt to paste into a Claude Code / Codex session**; a Claude Code or Codex session on any developer's laptop can use the same tools. The hub's chat gets **read tools only**; the server listens on this computer only (`localhost`).

9. **Voice (stretch: only if 1–8 are solid; typing must not suffer).** Push-to-talk first (hold a key, speak, it answers aloud); the circle follows the voice's loudness. Decide the route at this step: a realtime voice service (OpenAI's or Google's; handles interruptions; per-minute price; needs internet) or speech-to-text → our chat model → text-to-speech (the same model as typing; slower). Fan noise is why push-to-talk comes first. Wake word later.

### Step 1, concretely (the first coding task)
**Goal:** `uv run lab-os serve` opens a hub that looks like `hub-concept.html#skip` for the parts listed under "In", runs offline, and opens the existing teleop pages from its buttons.

**In:**
- **The program:** a new `lab-os` command with `serve` (one aiohttp app: the hub at `/`, the teleop and monitor pages and `/ws` moved under the hub, still working from the Quest; the Quest's bookmarked address may change, then update `docs/quest-setup.md`). `lab-os-teleop serve` keeps working.
- **Shared web files:** move what both the hub and teleop use (`vendor/`, `theme.js`, base styles) to one shared web folder, e.g. `src/lab_os/web/`; update the vendor README and the path in CLAUDE.md.
- **Fonts, bundled** (instead of the concept's Google Fonts link): `woff2` files for the families in `font.bundled`, only the weights the concept uses (Chakra Petch 400/500/600, Orbitron 500/700, Inter 300/400, JetBrains Mono 400, Oxanium 500/700, Rajdhani 500/600, Doto 600, Share Tech Mono 400; DSEG7 and DSEG14 Classic), Latin subset is enough. Sources: the Google Fonts GitHub repository (`google/fonts`) and the DSEG project (`keshikan/DSEG`); all SIL Open Font License. Put them in `vendor/fonts/` with each license file, and list name + version + license in the vendor README. One `fonts.css` with `@font-face` rules; the pages pick fonts only through the theme's `font.*` roles.
- **Theme:** every color, size and timing read from `/theme.json` (CSS variables set from it), not copied from the concept's constants. Mark each token the hub now reads as "Used by: hub" in `config/theme.yaml` (drop its "(planned)").
- **From the concept page:** the screen frame; the background network (drift, links, push away from mouse/finger; the random pulses; no thinking/speaking pulses yet); the title (`hub.title`) top-left; the status strip with **venue, internet, AI, clock** (`clock` 24h/12h); the **core drawn in its idle look** (rings turning, breathing; states come in step 5); **module buttons from `hub.modules`**, alternating left/right, with the traces to the core, corner brackets and hover; **opening a module** (unfolds from its button, the hub shrinks back and blurs, the core flies to the bottom-right corner, Back/Esc closes) with the existing teleop / monitor pages inside; the **button and module sounds** from `SFX`; sizes scale with the screen (`scale_with_screen`); quality levels for what step 1 draws (the computer's "reduce motion" setting means minimal).
- **Two real fact panels**, as callouts with their details pages:
  - **Current Project:** read from this file's "Steps" list (project name = this file's title, the step bar, "Step N of M", "Next ›› <bold title of the first step not marked done>"). Details page: every step with its title, done or not, and the goal paragraph.
  - **Commits:** commits per day from `git log` for `7d 14d 30d` (`hub.commits_days`); details page: 30 days of bars, totals, the latest commit messages. The typed log at the bottom of the hub shows the latest commits too.
- **Brain side:** small JSON endpoints (e.g. `/api/status`: venue, internet yes/no; `/api/project`; `/api/commits?days=14`). Internet is checked by the brain in the background (a short request, every ~30 s); with no internet everything still loads.
- **Tests (no hardware, no internet):** the pages and endpoints answer; the Steps parser on a sample file (done markers, next step); commit counting on a temporary git repo; **no `http://` or `https://` loads in any web file** (only the vendored copies), which keeps the offline rule enforced.
- **Done when:** the hub and `hub-concept.html#skip` side by side match for everything above; with the network cable out the hub still loads with all its fonts; teleop with the fake arm works when opened from the hub; `ruff` and `pytest` pass.

**Waits (later steps or later focuses):** the startup (step 6; step 1 opens straight into the hub, use F11 for full screen until then); the core's states, ask line, reply, chat and conversation page (steps 5, 7); the persona in the status strip (step 4); the **AI Spend** panel (step 7, when costs are logged); the **Devices** panel, device cards and table (Milestone 1, roll call); alerts, toast, error message, room mood; the `panels` layout; the portrait layout; sleep; maximal's extras and the Bible verses; the arm joints panel (it belongs with the arm module).

### Step 2, concretely (robot tools for AI)
**Goal:** in a Claude Code session on the lab desktop, the builder types "pick up the cube that's 15 cm in front of the base and put it 10 cm to the left", and the AI does it on `so101-white` through the brain's tools, asking before every move.

- **Which AI:** Claude Code with **Fable 5.2** (pick it with `/model`; the builder's subscription covers it, so no API key; to verify it shows in the list). Nothing is tied to Fable: any MCP client works (Codex, Claude Desktop), and the hub's chat can use the read tools later.
- **The connection:** the brain offers its tools over MCP on `localhost` only (the official `mcp` Python package; a separate port is fine). Connect with something like `claude mcp add --transport http lab-os http://127.0.0.1:<port>/mcp`; write the exact command in a new `docs/ai-control.md`.
- **Tools** (shared joint names, degrees; the arm chosen by its lab-os name):
  - read: `arm_status` (connected?, joint angles, gripper, limits, who has control, held or not), `list_poses`.
  - move: `move_joints` (absolute or relative angles for some joints), `gripper` (0–100 % open), `move_to` (x, y, z in cm from the arm's base, with the existing `kinematics.py` IK; says "can't reach" instead of guessing), `go_to_pose` (named poses such as `home`, `rest`, from config).
  - `stop`: always allowed, from any tier.
- **Safety:** every move goes through the same path as teleop (the driver's soft limits, the venue's `max_speed_scale`, smoothing). The brain **clips and refuses**, never trusts the model's numbers: a maximum change per call (a setting, e.g. 30° per joint or 10 cm), and refusal when the venue has `motion_allowed: false`. **One controller at a time:** while teleop has the arm the move tools refuse ("teleop has control"), and the other way round; STOP from any page wins. **Asks every time:** never allow-list the move tools in Claude Code, so each move shows a permission prompt (the read tools may be allow-listed). The move tools return the arm's real position afterwards, so the AI sees what actually happened.
- **Fake arm first** (watch it on the monitor page), then the real `so101-white`, with the builder present (CLAUDE.md: ask before anything that makes a real robot move).
- **A log of every call** (time, tool, arguments, clipped or refused, the result) per session, so runs can be compared later (e.g. with SmolVLA's ~30% on the green arm).
- **Protocol:** list the tools in `docs/protocol.md`.
- **Done when:** the fake arm does the cube task from a Claude Code prompt; then the real arm does it, with every move approved; a test proves clipping, refusal while teleop has control, and `stop`.

### Step 3, concretely (cameras for the AI)
- **The cameras:** the white arm's two cameras are the **same model as the green arm's training cameras** (Innomaker U20CAM). Both training cameras report the **same serial number `SN0001`** (GOTCHAS 2026-10-28), and the white ones very likely do too (check: `ls -l /dev/v4l/by-id/ /dev/v4l/by-path/` lists the names without opening any camera). So they can only be told apart by the **USB socket** they're plugged into: use `/dev/v4l/by-path/…` names, **never** `/dev/videoN` (numbers change) and never the by-id names (they collide).
- At the lab: plug the white cameras into fixed sockets, label sockets and cables, record their by-path names in `config/devices.yaml` with what each one sees (e.g. `so101-white-cam-top`, `so101-white-cam-wrist`). The training cameras' sockets (1-7 and 1-8) are marked `off_limits`, and the camera code refuses any camera that isn't listed.
- **The tool:** `camera_snapshot(camera)` (read tier) opens the camera, takes one picture, closes it, and returns a small JPEG (about 640 px wide: images cost the AI tokens). Camera library added to this project with `uv add` (e.g. OpenCV, headless).
- **Done when:** the AI looks, then reaches: "pick up the red block" with no positions given in words.

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
