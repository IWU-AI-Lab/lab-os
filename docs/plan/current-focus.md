# Current Focus: the JARVIS hub, voice, and AI driving the SO-101 arms

**Read this at the start of every Claude Code session.** It says what's left before the demo on **Thursday 2026-11-19**, and nothing else. What already works: `FEATURES.md`. Small decided jobs: `docs/plan/quick-jobs.md`. Plan, decisions, devices and how the pieces fit together: `docs/plan/lab-jarvis-log.md`. Ideas: `docs/plan/ideas.md`. Rewritten 2026-11-13; the long version, with each step's history and details: `docs/archive/focus-2026-11-13-hub-voice-ai.md`. When this focus closes, move it to `docs/archive/` and write the next one.

## The goal
A demo of every feature on Thursday 2026-11-19 (decision 2026-11-12). The designed hub (`/design`) full screen on the lab desktop's own screen: one tap, the startup with sound and a spoken greeting, the hub. Someone asks it something, typed or by voice (push-to-talk, dictation or "hey jarvis"), and it answers aloud. An AI drives the SO-101 arms (white and green) through the brain's tools, looking through the cameras. Teleop from the Quest (relative or 1:1) and the desktop. A page sent to another device. The hub in VR. The Newline only if it's smooth.

**Time:** the builder has assignments due Wednesday 2026-11-18, so Claude Code sessions do most of the coding; lab time is scarce. **Fable 5.2 access ends Monday 2026-11-16**: real-arm AI runs come first (afterwards the same tools work with any model).

## Until the demo, in order
1. **The AI on the real arms** (steps 2, 3, 11), before Monday: quick jobs 2–3 (limits that can be switched off, the floor at −0.5 cm; moves without asking is done); the height checked with a ruler and the elbow sag (`docs/plan/ideas.md` → "AI picking"); the cube actually picked on `so101-white`; then the green arm (`docs/guides/lab-checklist.md` part 8).
2. **Devices** (step 8): named devices, "open on…", one-tap icons.
3. **Voice and the assistant** (step 7): a snappier wake word with adjustable sensitivity; the assistant opens pages when asked ("pull up the teleop page", decision 2026-11-14); the greeting from a recording (quick job 4); the Newline's microphone.
4. **VR and teleop fixes** (step 10): quick jobs 10, 11 and 13 (1:1 scale), then the Quest with the real arm in 1:1.
5. **More quick jobs** from the top of `docs/plan/quick-jobs.md` whenever a session has time.
6. **Existing work instead of ours, if there's time** (decision 2026-11-14, a preference): compare our Quest teleop and our AI arm control with existing projects (`docs/plan/ideas.md` → "Teleop: compare…" and "AI arm control: compare…"), and switch where theirs is better.
7. **The Newline** (step 12): pick the route if it's used; not blocking.
8. **Before the demo:** go through `FEATURES.md` on the real hardware, fix what breaks, tag `demo-2026-11-19` (demo only from a tag).

Lab checks for each step: `docs/guides/lab-checklist.md`.

## Rules for this focus
1. **Grow it out of the teleop code:** extract what exists; formal interfaces only when a second real user needs them.
2. **Fake first, offline first:** every step runs without hardware and (except the AI steps) without internet. Robot tools run on the fake arm before a real one.
3. **Only claim what's real:** the start screen, status strip and panels never show a check or number that didn't happen; what isn't real yet is left out.
4. **The design for new and changed pages** (`docs/design/DESIGN.md`, `config/theme.yaml`); `/` stays plain by default (`hub.look: plain`) and the plain pages keep working.
5. **The hub's built-in assistant only reads, answers and opens pages** on the device it's talking at (anyone in the room can talk to it; moving the arm from it is an idea). The move tools are for a developer's AI tool on the brain's computer, through the same safety layer as teleop. Since 2026-11-13 they don't ask before each move (quick job 1, built 2026-11-14); STOP on every screen, the soft joint limits and one controller at a time always stay. Code written by AI only via branch → tests → the builder's approval.
6. **Secrets** (API keys) only in `.env`; `.env.example` lists the names.
7. **Portable:** Linux, Windows, macOS. **Plain names** in code, show names in persona files.
8. **The green arms:** CLAUDE.md's four rules (the code follows them since step 11).
9. **Nothing place-specific in code:** the lab's name, devices, venues and personas live in config (`docs/dev/places.md`).

## Steps (each one is a small, testable win)
The Current Project panel reads this list: each step's **bold title** is what the hub shows ("Next: Voice"), so titles are short plain words. A finished step gets `(done YYYY-MM-DD)` right after its title and keeps one line.

0. **Settle before coding** (done 2026-11-09).

1. **Plain hub** (done 2026-11-12). `docs/guides/hub.md`.

2. **Robot tools for AI.** The brain's MCP tools drive an SO-101 through teleop's safety layer (`docs/guides/ai-control.md`). On the real `so101-white` with `pose_view` and both cameras (2026-11-12) the gripper came down beside the cube and closed just past it (`docs/dev/GOTCHAS.md`).
   - **Left:** quick jobs 2–3; the height reads 1–2 cm low and the elbow sags ~3° (`docs/plan/ideas.md` → "AI picking"); the cube actually picked; the green arm (step 11).
   - **Done when:** the real arm does the cube task from a Claude Code prompt.

3. **Cameras for the AI.** `pose_view` (2026-11-11) and `camera_snapshot` (2026-11-12) are built and were used in the cube pick.
   - **Left:** placing things from the overhead picture (the AI doesn't know where that camera is: a printed marker, `docs/plan/ideas.md` → "AI picking"); a camera for each arm by name (hack below).
   - **Done when:** "pick up the red block" works with no positions given in words.

4. **Personas** (done 2026-11-10). `docs/dev/personas.md`.

5. **Typed chat** (done 2026-11-10). `docs/dev/chat.md`.

6. **Project helper** (done 2026-11-10). `docs/dev/chat.md` → "What it knows".

7. **Voice.** Push-to-talk, the spoken greeting, dictation and the wake word, built 2026-11-12 (`docs/guides/voice.md`). In the lab (2026-11-13) push-to-talk and the wake word work on the desktop with a USB microphone (sometimes only spoken louder) and on the Quest (the wake word sometimes misses there).
   - **Left:** the greeting from a recording (quick job 4); the Newline's microphone (Chrome's flag, `docs/guides/voice.md` → "Secure pages"). After the demo: a better room microphone, the Quest's misses.
   - The free Gemini key speaks only ~15–20 answers a day (`docs/dev/GOTCHAS.md`): keep them for the demo.

8. **Devices.** Built: a page on another monitor of the brain's computer ("Show on another screen", `docs/guides/hub.md`); other computers open the hub by the desktop's IP address, view-only while a real arm is connected (`--drive-from` lets one drive).
   - **Left, as decided (2026-11-09, renamed from "screens" 2026-11-13):** each device connects under a name in its address (`/?device=desk`, `/?device=newline`, `/?device=quest`), and the brain lists the devices that have the hub open. The "This screen" settings become "This device" and belong to the name (the way in to voice, drawing resolution). A device's monitors are part of it: "open on desk" picks the free monitor, or asks.
   - On the hub, "open on…" next to a module lists the other devices; the page opens there; Back there (or "bring it back") closes it. Only devices with the hub open are listed, so a device used for something else is never taken over.
   - Nothing starts by itself: a "Start lab-os" shortcut on the brain's computer, a "Lab hub" icon on the others (`google-chrome --app=<address>/?device=desk --start-fullscreen`), a home-screen icon on the Newline. Pages reconnect when the brain restarts. The brain's address is the desktop's IP address for now (it may change).
   - **Done when:** from another device, Monitor opens on the desk monitor and comes back; after everything was switched off, one tap per device brings the hub back under its name.
   - After the demo: one brain per network (mDNS, `--second-brain`).

9. **Demo check** (done 2026-11-12).

10. **Design polish.** The designed hub (`/design`) and the hub in VR (`/xr`) are built; the VR hub worked in the headset on 2026-11-13.
    - **Left:** quick jobs 10–11 (a far-away cluster of dots, the chat that doesn't scroll); the bugs from the 2026-11-12 demo check (the builder to list them); alerts from real events; how a page sent to another device looks (plain is fine if time is short).

11. **Green arms.** Built 2026-11-12, tested without hardware (`docs/guides/ai-control.md` → "The green arm").
    - **Left:** in the lab with LeLab closed (`docs/guides/lab-checklist.md` part 8): `--watch`, then moving with the builder present, then the AI; which camera is which (`so101-green-cam-a`/`-b` until then).

12. **Newline.** Not blocking: the demo is on the desktop's own screen. Measured 2026-11-13 (`docs/dev/GOTCHAS.md`): by HDMI from the desktop, choppy at 1920×1080 though the desktop draws 60 fps, smooth at 1600×900; in its own Chrome `/perf` gives 44–59 fps but the startup lags and there's no mic button.
    - **Next, if it's used:** HDMI at 1600×900 is the simplest route (first check the refresh rate Ubuntu picks at 1920×1080 and the Newline's picture mode). Its own Chrome needs a lighter startup on slow devices (fewer stars, `?res=`) and Chrome's flag for the microphone. No extra hardware so far.

## Waiting on others
- **The professor's OpenAI key** in `.env`: then `main` answers and speaks (a config change; steps 5 and 7).
- **The 7-port powered USB hub** (shopping list in the log): the white arm and its cameras without unplugging the green ones.
- **The lab router** (the professor's OK): "Up next" below.

## Hacks to clean up
- `config/devices.yaml`: `so101-white-cam-a` / `-b` (2026-11-12; to be renamed `-cam-stand` / `-cam-wrist`, quick job 15) are a temporary alias of sockets 7 and 8, which are also the green set's cameras, because the white arm's two cameras sit in those sockets today. Give each setup its own names (a looks from above, b is the wrist camera) when the powered USB hub arrives. `camera_snapshot` (step 3) is built for the test; its tidy-up (a camera for the arm by name, not by hand) is left.
- `config/poses.yaml`: the SO-101 `rest` pose comes from forward kinematics only; check it on the real `so101-white` (slowly, builder present) before relying on it.
- `robots/xarm.py`: 240°/1000 units is the datasheet scale, not measured (zero = the "Run" pose, signs observed 2026-10-27). Motion tuning (`lead_s` 0.3 s, `max_deg_per_s` 120, `idle_read_after_s` 0.6, `min_read_interval_s` 0.25) is from first tests, not optimized. Default limits (until hand calibration) come from the builder's grab script.

## Up next (after this focus)
Milestone 1, "Connected lab", once the router is here: roll call, robots reporting in (arms on other computers, since the brain desktop's USB is full), the Devices panel, `xarm1` as another robot through the core (`docs/plan/ideas.md` → "On hold" → "Core plumbing"). Then AI-assisted development (`docs/plan/lab-jarvis-log.md` → "AI-assisted development"). Other paused work: `docs/plan/ideas.md` → "On hold".
