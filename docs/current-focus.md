# Current Focus: the JARVIS hub (startup, control hub, a living assistant)

**Read this at the start of every Claude Code session.** It says what to work on *now*. The long-term plan, decisions and module list live in **lab-jarvis-log.md**; this file only sets the current priority. When this focus is done, move it to `docs/archive/` and write the next one. Previous focus: the teleop demo, closed 2026-10-30 (`docs/archive/focus-2026-10-teleop-demo.md`; what's left of it is in `docs/ideas.md` → "On hold").

---

## The goal right now
You press a key at the lab desktop. A short startup animation plays, with sound, and lands in the **hub**: one full-screen page on the 32" monitor with buttons into the system (teleop today, more later), a status strip, and the **assistant**, a picture that breathes and reacts. You type a question ("what's next on the project?") and it answers, using the project's own docs. Its look and voice come from the loaded **persona**.

Roll call and robot connections wait for the lab router (`ideas.md` → "On hold").

## How it fits together (design shapes for this focus)
- **One brain program, `lab-os serve`.** It serves the hub page and mounts the teleop pages inside it. The core grows out of the teleop code (decision 2026-10-24). `lab-os-teleop` keeps working until it's replaced.
- **The assistant's state is separate from its picture.** The state is a short list: `idle`, `listening`, `thinking`, `speaking`, `offline`, `error`, plus a 0–1 "loudness" while speaking. That's the information layer. The rest of the system only sets the state. The **picture** (decorative layer) is chosen by the persona and only reads the state. New picture styles never touch the hub, chat or voice code. `minimal` quality can be a still circle that only changes color.
- **Personas are config files**, `config/personas/<id>.yaml`. The active persona is set per venue profile; the default is the plain one. Example:
  ```yaml
  version: 1                    # file format version
  id: jarvis                    # plain name (code, files)
  display_name: "J.A.R.V.I.S."  # show name (on screen)
  personality: jarvis.md        # how it talks: a short text file next to this one
  model: main                   # which AI setup (defined once in config/models.yaml)
  voice: none                   # later (step 8)
  wake_word: none               # later
  picture: { type: orb, style: calm-ring, color: primary }
  lines:                        # show names and things it says
    startup_title: "INITIATION"
    greeting: "Good evening. All local systems are up."
  sounds: default               # sound pack
  ```
  **Must stay extensible:** the loader checks the fields it knows, keeps unknown fields and **warns** about them (no crash), so new fields can be added any time. Two personas in v1: **`lab-assistant`** (default; plain name, simple circle, no character) and **`jarvis`** (the show persona). The persona changes picture, voice, lines and sounds; **the theme (colors, fonts) stays the same** for all personas.
- **The hub's buttons come from config** (the modules the venue has), so a new module adds a button without changing the hub. No fake "coming soon" buttons ("only claim what's real").
- **The status strip shows only real facts:** venue, persona, internet yes/no, AI connected yes/no.
- **Offline vs. internet.** Offline: startup, hub, the assistant's picture, teleop, sounds, theme. Needs internet: the AI chat and (later) cloud voices. Without internet the assistant shows `offline` and everything else works.
- **Looks:** colors, glow and timing come from `config/theme.yaml` (decision 2026-10-24). Quality levels full / reduced / minimal; libraries are vendored, no CDN (CLAUDE.md).
- **Sound:** browsers block all sound until the user clicks or presses a key. So the startup **starts with a key press or click** (the "ignition"), which also unlocks the sound. Sounds are generated in the browser (WebAudio) until real ones exist: offline, no license questions. Volume/mute in the sound pack.

## Rules for this focus
1. **Grow it out of the teleop code**: extract what exists; formal interfaces only when a second real user needs them.
2. **Fake first, offline first**: every step runs without hardware and (except the AI steps) without internet.
3. **Only claim what's real**: the startup and status strip never show a check that didn't happen.
4. **The assistant never changes anything in this focus.** It reads and answers. Writing code comes later, and only via branch → tests → the builder's approval (decision 2026-10-24).
5. **Secrets** (API keys) only in `.env`; `.env.example` lists the names.
6. **Portable**: Linux, Windows, macOS (decision 2026-10-27). **Plain names** in code, show names in persona files (decision 2026-10-28).

## Steps (each one is a small, testable win)
0. **Settle before coding** (planning sessions):
   - **AI service (settled 2026-10-30):** **OpenAI first** (where the keys are); free Gemini keys as a backup; the Anthropic key is out of credits. **Local models** (running on our own computer, no internet) as a second setup. Still open: are the OpenAI keys the lab's/professor's or personal (matters for "not one person's account"), and the monthly budget (≤ $20/month so far).
   - **Design session (its own Claude session, in its own folder `~/lab-os-design`, branch `design`; edits only `docs/design/` and `config/theme.yaml`):** reference pictures are in `docs/design/references/` (first batch 2026-10-30: HUD elements, cyberpunk HUDs, Iron Man HUDs, FRIDAY, startup beginning/ending). A design session distills them into a one-page `docs/design/DESIGN.md` (colors, glow, type, motion, sound, do's and don'ts) and updates `config/theme.yaml`. Can run alongside steps 1–2.
1. **Brain program + hub skeleton.** `lab-os serve` serves a full-screen hub page: status strip, module buttons from config (Teleop, Monitor), an empty spot for the assistant. Teleop works from the hub. Tests without hardware.
2. **Personas.** Loader + the two persona files + `config/models.yaml` (the AI setups, no keys). The venue profile picks the persona. The status strip shows it. Switching the persona is a config edit + reload.
3. **The assistant's picture, v1.** The breathing circle, with every state and loudness, a hidden test control to flip states (no AI yet), theme colors, persona style, all three quality levels.
4. **Startup prototypes (throwaway).** 3–4 short versions on one page, each 3–5 s, with generated sounds, so the builder can watch and pick. Candidates:
   - (a) **Type-out:** status lines type out with a soft tone each, then the circle "ignites".
   - (b) **Bloom:** a dot grows into the circle with a rising sound; the hub panels unfold from it.
   - (c) **Particles:** a stream of glowing particles converges and forms the circle (GPU-drawn).
   - (d) **HUD calibration:** rings and tick marks draw themselves like a scanner locking on, then the hub fades in.

   Push the limits, but no full 3D camera fly-through. Mark the prototype folder as throwaway; delete what isn't picked.
5. **The real startup.** The chosen prototype, finished: ignition key/click; shows only real checks ("Persona loaded", "Internet: yes", "AI: connected"); skippable with any key; ≤ ~5 s; lines from the persona (`startup_title`, `greeting`); respects quality levels and mute; lands in the hub.
6. **Typed chat.** One AI model: **OpenAI**, API key in `.env`. Talk to it through the widely copied **OpenAI-style chat interface**, so that other setups in `config/models.yaml` differ only by address, model name and key name: Gemini (it offers an OpenAI-compatible address) and **local models** (Ollama or llama.cpp's server run one on our own computer and speak the same interface). **Optional within this step:** a `local` setup proves the switch and gives a chat that works offline (offline lite mode). Careful on the lab desktop: its GPU is shared with the training project, so don't run a local model during a recording; a laptop works too. A small **conversation manager** owns the turn and sets the assistant's state (`thinking` → `speaking` → `idle`). Answers stream in. Uses the persona's personality text. Logs the cost per chat, to check against the budget. Built so voice can plug into the same conversation manager later.
7. **Project helper (read-only).** The assistant can read `docs/` (current focus, ideas, log, GOTCHAS) and git status/history, and answer "what's next?" or "what's on hold?". It **drafts the prompt to paste into a Claude Code session**. Tools are default-deny; it changes nothing.
8. **Voice (stretch: only if 1–7 are solid; typing must not suffer).** Push-to-talk first (hold a key, speak, it answers aloud); the circle follows the voice's loudness. Decide the route at this step: a realtime voice service (OpenAI's or Google's; handles interruptions; per-minute price; needs internet) or speech-to-text → our chat model → text-to-speech (the same model as typing; slower). Fan noise is why push-to-talk comes first. Wake word later.

## After this focus: the coding agent (direction, decision 2026-10-30)
The builder can ask the system for something ("add the touchscreen page from ideas.md") and it gets built: an agent that works like Claude Code, paid by the lab's API account, not one person's subscription. Candidates (the agent harness slot is swappable): **OpenAI's Codex** (its open-source coding agent; works with an OpenAI API key; to verify) since the keys are OpenAI's, or the **Claude Agent SDK** (Claude Code's engine) if the Anthropic credits are refilled. It works only on its own branch (`agent/<task>`), runs the tests, opens a PR; the builder reviews and merges; it never touches the running system. Watch the cost: one coding task can cost several dollars, more than chat. Step 7 is its read-only first half.

## Hacks to clean up
- `robots/xarm.py`: 240°/1000 units is the datasheet scale, not measured (zero = the "Run" pose, signs observed 2026-10-27). Motion tuning (`lead_s` 0.3 s, `max_deg_per_s` 120, `idle_read_after_s` 0.6, `min_read_interval_s` 0.25) is from first tests, not optimized. Default limits (until hand calibration) come from the builder's grab script.

## Up next (after this focus)
Milestone 1, "Connected lab", once the router is here: roll call, robots reporting in, `xarm1` as the second robot through the core (`ideas.md` → "On hold" → "Core plumbing"). Other paused work: `ideas.md` → "On hold".
