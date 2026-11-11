# In the lab: what to test, in order

A walk-in list for the lab desktop (`ai-comp-lab-ubuntu-76358`). Each part works without the next. Note what you find in `docs/current-focus.md` (the step's status) and surprises in `docs/GOTCHAS.md`.

**Never:** the green arm's ports (`…5B41531599`, `…5B41533501`), its calibration, the `lerobot` conda env, the training cameras. The brain refuses them; leave them unplugged or alone either way.

## 0. Get the latest (2 min)
```bash
cd ~/lab-os
git pull
uv sync --extra so101          # LeRobot for so101-white; plain `uv sync` would remove it
uv run pytest -q               # should end "passed"
```

## 1. The designed hub on the desktop's own screen (5 min)
```bash
uv run lab-os serve --host 0.0.0.0
```
Open **http://localhost:8080/design** in Chrome. Check:
- [ ] One click: full screen, the unlock sound, the jump, the title, the greeting, the hub.
- [ ] The strip says the venue, the persona and `AI: …` (the key in `~/lab-os/.env`).
- [ ] Ask something ("What's next?"). Gemini's free key takes 6–15 s.
- [ ] Teleop, Monitor and Arm open and close (Back or Esc).
- [ ] Smooth? If it stutters: `/design?quality=reduced`, or check `/perf` (`docs/hub.md` → "Performance test").
- [ ] Sound comes out of the speakers you want.

Full screen without the click, as an app window (close it with Alt+F4):
```bash
google-chrome --app=http://localhost:8080/design --start-fullscreen
```

## 2. The Newline (10–15 min)
Find the desktop's address: `hostname -I` (the first one). With the brain from part 1 still running, on the Newline's Chrome open `http://<that address>:8080/design`.
- [ ] **It loads.** If it doesn't, the network keeps devices apart: `network-setup-checklist.md` → "Networks before the router" (the HDMI + USB-touch cable to the desktop is the quickest fix, and `localhost` then even allows voice later).
- [ ] **One tap = full screen + start.** Swipe from the edge: can you leave it? Does the Newline's own bar stay away?
- [ ] Chrome menu → **Add to Home screen**: does the icon open the hub? (On `http://` it opens as a tab; tap once for full screen.)
- [ ] Touch: the panels' details pages, the commit range buttons, the devices list.
- [ ] Leave it alone for 30 minutes: it goes back to the start screen (`hub.reset_after_s`; it dims to sleep after 15 minutes). To check it quickly, set a shorter reset in ⚙ → The hub, then set it back.
- [ ] The plain hub's two taps too (`http://<address>:8080/plain`): this checks off focus step 1 (then mark it `(done …)` in `current-focus.md`).

## 3. Fable drives the real arm (20–30 min, you at the arm)
The full walkthrough: `docs/ai-control.md` → "5. On the real arm". Short version:
```bash
ls -l /dev/serial/by-id/       # so101-white = …5B41532410-if00
uv run --extra so101 lab-os serve --arm so101-white --speed 0.3 --host 0.0.0.0
```
(`--host 0.0.0.0` lets the Newline keep showing the hub; it's view-only there, and its STOP works.)
- In Claude Code: `/mcp` → `lab-os` → reconnect; `/model` → Fable 5.2.
- [ ] "Read the arm's status": the joints match the arm.
- [ ] "Go to the home pose" (approve it, watch it).
- [ ] "Move the gripper 3 cm lower, pointing straight down."
- [ ] The cube: measure it (cm in front of the base's middle, cm to the left), then the step-2 prompt.
- [ ] STOP from the Newline stops a move.
- [ ] Watch it on **AI Control** (`/ai`, or the hub's AI Control button): each call shows up as it happens; on a second monitor of the desktop: open AI Control in the hub → **Show on another screen**.
- Approve every move after reading it; never "always allow". Ctrl+C stops the brain (the arm goes limp: hold it if lifted).
- Afterwards: `logs/ai-tools/` has the calls. Write in `current-focus.md` step 2 what worked.

## 4. If there's time
- **Settings** (the ⚙ top right in `/design`): try Level of detail → maximal under "This screen", and `hub.look` → design (then `git diff config/` shows the change; `git checkout config/theme.yaml` undoes it).
- The new **Teleop** page on the Quest's browser; if anything misbehaves there, `/classic/teleop` is the old page.
- `/design?quality=maximal` on the Newline (adds the far-layer verses): still smooth?
- The Quest: teleop through the hub (`adb reverse tcp:8080 tcp:8080`, then `http://localhost:8080/teleop` on the Quest; `docs/quest-setup.md`).
- Show someone: `/design`, press start, ask it something, open Arm while Fable moves the arm.
