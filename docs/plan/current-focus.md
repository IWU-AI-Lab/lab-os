# Current Focus: the JARVIS hub, voice, and AI driving the SO-101 arms

**Read this at the start of every Claude Code session.** It says what's left before the demo on **Thursday 2026-12-03**, and nothing else. What already works: `FEATURES.md`. Small decided jobs: `docs/plan/quick-jobs.md`. Plan, decisions, devices and how the pieces fit together: `docs/plan/lab-jarvis-log.md`. Ideas: `docs/plan/ideas.md`. Rewritten 2026-11-13; the long version, with each step's history and details: `docs/archive/focus-2026-11-13-hub-voice-ai.md`. When this focus closes, move it to `docs/archive/` and write the next one.

## The goal
A demo of every feature on Thursday 2026-12-03 (decision 2026-11-12; date moved 2026-11-16). The designed hub (`/design`) full screen on the lab desktop's own screen: one tap, the startup with sound and a spoken greeting, the hub. Someone asks it something, typed or by voice (push-to-talk, dictation or "hey jarvis"), and it answers aloud. An AI drives the SO-101 arms (white and green) through the brain's tools, looking through the cameras. Teleop from the Quest (relative or 1:1) and the desktop. A page sent to another device. The hub in VR. The Newline only if it's smooth.

**Time (decision 2026-11-16):** the demo moved from 2026-11-19 to **Thursday 2026-12-03, 3–4:30 pm (the AI club's meeting)**; nothing is shown before then. Lab days for trying things on the real hardware: Thursday 2026-11-19, Monday and Tuesday 2026-11-23/24. **Nothing new after Tuesday 2026-11-24:** from then on, sessions only fix what the lab days found, and whatever doesn't work on the hardware by then is left out of the demo. The builder's coursework (a research paper above all) comes first; Claude Code sessions do most of the coding.

## Until the demo, in order
1. **The AI on the real arms** (steps 2, 3, 11), before Monday: quick jobs 1–3 are done (moves without asking, switchable limits, the floor at −0.5 cm); the height checked with a ruler and the elbow sag (`docs/plan/ideas.md` → "AI picking"); the cube actually picked on `so101-white`; then the green arm (`docs/guides/lab-checklist.md` part 8).
2. **Devices** (step 8): built 2026-11-14; left: the lab check (`docs/guides/lab-checklist.md` part 11).
3. **Voice and the assistant** (step 7): the snappier wake word with adjustable sensitivity is built (2026-11-14; its lab check: `docs/guides/lab-checklist.md` part 9e, the Quest in part 10); the assistant opens pages when asked is built (2026-11-14, typed and spoken, all three hubs; lab check: part 9g); the Newline's microphone (the greeting from a recording is done).
4. **VR and teleop fixes** (step 10): quick jobs 10, 11 and 13 (1:1 scale), then the Quest with the real arm in 1:1.
5. **More quick jobs** from the top of `docs/plan/quick-jobs.md` whenever a session has time.
6. **Borrowed from existing work** (decision 2026-11-16; the comparison: `docs/dev/existing-work-teleop-ai.md`), before the 2026-11-19 lab day where possible: **teleop relative mode at scale 1.0 with a higher speed limit** (built 2026-11-16; lab: checklist 7.7); **the stand camera's cm grid** (Google's printed calibration sheet → pixels to table cm, drawn on `cam-stand`'s picture); **`pick_at(x, y)`**, a one-call pick (after the height and sag fix in item 1); optionally robot_MCP's pick tips in the AI instructions. Isaac Teleop as an input to the brain comes after the demo (`docs/plan/ideas.md` → "On hold").
7. **Three previews** (decision 2026-11-16), shown at the end of the demo as "what's next". Started only after devices, the quick jobs and the voice polish are merged; each on its own page or behind a switch that's off by default, so it can't break what works; cut if it hasn't run on the real hardware by 2026-11-24:
   - **Point and "move there"** in the headset: in the Quest with the 3D arm lined up, point at a spot on the table, say or press "move there", and the gripper goes there. No AI. The first piece of "put that there".
   - **"What's on the table?"**: the stand camera's picture goes to Gemini, which names the objects; the hub shows the picture with labels and the assistant says them.
   - **Two arms at once:** in the Quest, the left hand drives one SO-101 and the right hand the other (`docs/plan/ideas.md` → "Two arms at once").
8. **The Newline** (step 12): pick the route if it's used; not blocking.
9. **Before the demo:** go through `FEATURES.md` on the real hardware, fix what breaks, tag `demo-2026-12-03` (demo only from a tag).

Lab checks for each step: `docs/guides/lab-checklist.md`.

## Rules for this focus
1. **Grow it out of the teleop code:** extract what exists; formal interfaces only when a second real user needs them.
2. **Fake first, offline first:** every step runs without hardware and (except the AI steps) without internet. Robot tools run on the fake arm before a real one.
3. **Only claim what's real:** the start screen, status strip and panels never show a check or number that didn't happen; what isn't real yet is left out.
4. **The design for new and changed pages** (`docs/design/DESIGN.md`, `config/theme.yaml`); `/` stays plain by default (`hub.look: plain`) and the plain pages keep working.
5. **The hub's built-in assistant reads, answers and opens pages** on the device it's talking at (anyone in the room can talk to it; moving the arm from it is an idea; more abilities may come, so it's not a hard rule that it never changes anything, the builder 2026-11-14). The move tools are for a developer's AI tool on the brain's computer, through the same safety layer as teleop. Since 2026-11-13 they don't ask before each move (quick job 1, built 2026-11-14); STOP on every screen, the soft joint limits and one controller at a time always stay. Code written by AI only via branch → tests → the builder's approval.
6. **Secrets** (API keys) only in `.env`; `.env.example` lists the names.
7. **Portable:** Linux, Windows, macOS. **Plain names** in code, show names in persona files.
8. **The green arms:** CLAUDE.md's four rules (the code follows them since step 11).
9. **Nothing place-specific in code:** the lab's name, devices, venues and personas live in config (`docs/dev/places.md`).

## Steps (each one is a small, testable win)
The Current Project panel reads this list: each step's **bold title** is what the hub shows ("Next: Voice"), so titles are short plain words. A finished step gets `(done YYYY-MM-DD)` right after its title and keeps one line.

0. **Settle before coding** (done 2026-11-09).

1. **Plain hub** (done 2026-11-12). `docs/guides/hub.md`.

2. **Robot tools for AI.** The brain's MCP tools drive an SO-101 through teleop's safety layer (`docs/guides/ai-control.md`). On the real `so101-white` with `pose_view` and both cameras (2026-11-12) the gripper came down beside the cube and closed just past it (`docs/dev/GOTCHAS.md`).
   - **Left:** the height reads 1–2 cm low and the elbow sags ~3° (`docs/plan/ideas.md` → "AI picking"); the cube actually picked; the green arm (step 11).
   - **Done when:** the real arm does the cube task from a Claude Code prompt.

3. **Cameras for the AI.** `pose_view` (2026-11-11) and `camera_snapshot` (2026-11-12) are built and were used in the cube pick.
   - **Left:** placing things from the stand camera's picture (the AI doesn't know where that camera is: a printed marker, `docs/plan/ideas.md` → "AI picking"); a camera for each arm by name (hack below).
   - **Done when:** "pick up the red block" works with no positions given in words.

4. **Personas** (done 2026-11-10). `docs/dev/personas.md`.

5. **Typed chat** (done 2026-11-10). `docs/dev/chat.md`.

6. **Project helper** (done 2026-11-10). `docs/dev/chat.md` → "What it knows".

7. **Voice.** Push-to-talk, the spoken greeting, dictation and the wake word, built 2026-11-12 (`docs/guides/voice.md`); the greeting from a recording 2026-11-14; a snappier wake word with a sensitivity slider per device, its timing logged, and the Quest's paused microphone woken by itself 2026-11-14 (not yet in the lab). In the lab (2026-11-13) push-to-talk and the wake word work on the desktop with a USB microphone (sometimes only spoken louder) and on the Quest (the wake word sometimes misses there).
   - **Left:** the Newline's microphone (Chrome's flag, `docs/guides/voice.md` → "Secure pages"). After the demo: a better room microphone, the Quest's misses.
   - The free Gemini key speaks only ~15–20 answers a day (`docs/dev/GOTCHAS.md`): keep them for the demo.

8. **Devices.** Built 2026-11-14 (`docs/guides/hub.md` → "Devices"), tried with headless browser pages as devices: each hub page connects under a name (`/?device=desk`), the brain lists the devices with the hub open (each monitor a window) and keeps "This device" settings under the name (`hub-devices.yaml`); "Open on…" next to Back in a module (the free monitor, or it asks), Back there or "Bring it back" closes it; pages reconnect by themselves after a restart; `lab-os icon` ("Start lab-os", `lab-os serve --open desk`) and a "Lab hub" icon from ⚙ → This device. Before: a page on another monitor of the brain's computer (now Open on… → "Another monitor of this computer"); other computers view-only while a real arm is connected (`--drive-from` lets one drive).
   - **Left:** the lab check (`docs/guides/lab-checklist.md` part 11). The brain's address is the desktop's IP address for now (it may change: then the icons again). The Quest's VR hub (`/xr`) isn't a device (its browser at `/design?device=quest` is).
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
- `config/devices.yaml`: `so101-white-cam-stand` / `-cam-wrist` (2026-11-12; `-cam-a` / `-b` until quick job 15, 2026-11-16) are a temporary alias of sockets 7 and 8, which are also the green set's cameras, because the white arm's two cameras sit in those sockets today. Give each setup its own names (a looks from above, b is the wrist camera) when the powered USB hub arrives. `camera_snapshot` (step 3) is built for the test; its tidy-up (a camera for the arm by name, not by hand) is left.
- `config/poses.yaml`: the SO-101 `rest` pose comes from forward kinematics only; check it on the real `so101-white` (slowly, builder present) before relying on it.
- `robots/xarm.py`: 240°/1000 units is the datasheet scale, not measured (zero = the "Run" pose, signs observed 2026-10-27). Motion tuning (`lead_s` 0.3 s, `max_deg_per_s` 120, `idle_read_after_s` 0.6, `min_read_interval_s` 0.25) is from first tests, not optimized. Default limits (until hand calibration) come from the builder's grab script.

## Up next (after this focus)
Milestone 1, "Connected lab", once the router is here: roll call, robots reporting in (arms on other computers, since the brain desktop's USB is full), the Devices panel, `xarm1` as another robot through the core (`docs/plan/ideas.md` → "On hold" → "Core plumbing"). Isaac Teleop as an input to the brain (`docs/plan/ideas.md` → "On hold"). Then AI-assisted development (`docs/plan/lab-jarvis-log.md` → "AI-assisted development"). Other paused work: `docs/plan/ideas.md` → "On hold".
