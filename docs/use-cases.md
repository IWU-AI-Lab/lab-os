# Use cases: realistic workflows

Concrete situations lab-os should handle, used to decide which features matter. Each one: who, what happens step by step, and which features it needs. **Draft (2026-11-09): correct anything that isn't how the lab really works.** Feature status at the bottom: focus (`current-focus.md`), on hold / idea (`ideas.md`).

---

### 1. First one in (the everyday case)
**Who:** the builder, alone, lab closed, robots off.
1. Presses a key at the desktop: startup plays, hub opens full screen.
2. Sees: current project step, AI spend, "GPU: training (SmolVLA)" because a training run is going.
3. Types "what's next?" → the assistant answers from `current-focus.md` and drafts a prompt for a Claude Code session.
4. Switches on `xarm1` to test something; its hexagon lights up as it connects.

**Needs:** startup, hub, status strip, project helper (MCP read tools), GPU-busy indicator, devices panel, roll call (router).

### 2. Getting ready for a visit
**Who:** the builder, an hour before visitors.
1. Picks the `visit-day` venue: persona switches to `jarvis`, only that venue's devices are expected.
2. Asks "is everything ready?" → list: Quest battery 40% (charge it), `so101-white` connected, limits set, internet: no (fine, offline mode).
3. Runs the teleop once with STOP tested.

**Needs:** venue profiles, personas per venue, battery/diagnostics in device cards, a readiness check (roll call + venue checklist), teleop.

### 3. The visit
**Who:** 3–10 visitors, the builder running it.
1. A visitor puts on the Quest and drives the arm; the Newline shows the arm's 3D view and the Quest's view for everyone else.
2. Another visitor asks the hub out loud "what can this robot do?" (voice, `jarvis` persona).
3. A visitor's phone could drive the arm next (control handed over, not grabbed).

**Needs:** teleop, kiosk screens (Newline), casting, voice, control handover, phone teleop (idea), STOP on every device.

### 4. A student adds a robot from home (bring your own AI)
**Who:** a student with their own laptop and Claude Code (or Codex), at home.
1. Clones the repo; asks their AI tool to write a Raspbot driver against a fake Raspbot.
2. Their tool connects to the brain's MCP server (personal token, remote access) to read the real Raspbot's status and logs.
3. Opens a PR; the builder reviews; after merge, "deploy to raspbot1" runs through the brain (act tier, asks first).

**Needs:** MCP server with tiers + tokens, remote access (overlay network, ask IT), fake devices, deploy tool, PR workflow, docs a newcomer can follow.

### 5. A student without an AI subscription
**Who:** a student at the hub, no Claude/Codex account.
1. Turns on "send to harness" and types "add the xArm's battery voltage to its device card".
2. The lab-paid agent works on `agent/xarm-battery`, runs the tests, opens a PR; the hub shows "PR ready for review" and the cost ($0.40).
3. The builder approves (or not).

**Needs:** harness toggle, lab-paid harness (Codex + OpenAI key), spend cap + cost display, agent branches, PR status in the hub.

### 6. Something's broken
**Who:** anyone; "Pi 7 isn't showing up".
1. Taps Pi 7 in the hive: off since 10:42, last report "under-voltage".
2. Presses "Find me": Pi 7 blinks on the shelf.
3. Asks the assistant "why did Pi 7 drop?" → it reads the troubleshooting report and suggests a power supply swap.

**Needs:** device cards with history, diagnostics, find me, troubleshooting reports, assistant reads reports (MCP read tools).

### 7. Training and lab-os on the same machine
**Who:** the builder recording SmolVLA demonstrations on `so101-green`.
1. Hub shows the green arm and training cameras as locked to "SO-101 training"; GPU busy.
2. Someone tries a local model in the hub: warned that the GPU is busy.
3. Later: the green arm joins lab-os to compare VLA vs. LLM/VLM control (future idea).

**Needs:** projects module (locks), GPU-busy indicator, model router check, off-limits rules.

### 8. Checking in from home
**Who:** the builder on a phone, evening.
1. Opens the hub remotely: which devices are on, did today's training finish, any errors.
2. Can't move anything (remote mode = no motion).

**Needs:** remote access (level 2), read-only remote mode, phone layout.

### 9. Another project borrows a screen
**Who:** another lab project needing the Newline for a poster session.
1. Uses the kiosk recipe: their web page full screen, no browser bars, starts at boot.
2. Later, from the hub: "show the poster on the Newline".

**Needs:** kiosk screen recipe, screen-to-screen sending (idea).

---

## Features by how many workflows need them
| Feature | Workflows | Status |
|---|---|---|
| Hub + status strip + devices panel | 1, 2, 6, 7, 8 | focus (devices: roll call waits for the router) |
| MCP tools, read tier (assistant reads docs, devices, reports) | 1, 4, 6 | focus step 7 |
| Roll call / device diagnostics / battery | 1, 2, 6 | on hold (router) / idea |
| Teleop + control handover + STOP everywhere | 2, 3 | done (polish on hold) |
| Personas per venue | 2, 3 | focus step 2 |
| Kiosk screens | 3, 9 | idea (full screen on ignition: focus step 5) |
| Remote access + tokens + tiers | 4, 8 | after focus / idea (needs router + IT) |
| Harness toggle + lab-paid agent + cost display | 5 | after focus |
| GPU-busy indicator | 1, 7 | idea |
| Find me | 6 | idea |
| Projects module (locks) | 7 | idea |
| Voice | 3 | focus step 8 (stretch) |
