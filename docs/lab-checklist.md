# In the lab: what to test, in order

A walk-in list for the lab desktop (`ai-comp-lab-ubuntu-76358`). Each part works without the next. Note what you find in `docs/current-focus.md` (the step's status) and surprises in `docs/GOTCHAS.md`.

**Done on Tuesday 2026-11-10** (the builder, ~6–7 h): part 1 (the designed hub on the desktop, Gemini answered; `/perf` not run), the hub on `pi01` and the other desktop as well, all full screen except `/teleop` on the Pi (GOTCHAS); the Newline through `pi01` (laggy, part 2); Fable on the real arm (part 3; STOP from other screens not tried). Still open: `/perf` everywhere, STOP from another screen, parts 4–6.

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
- [x] One click: full screen, the unlock sound, the jump, the title, the greeting, the hub. (2026-11-10)
- [ ] The strip says the venue, the persona and `AI: …` (the key in `~/lab-os/.env`).
- [x] Ask something ("What's next?"). Gemini's free key takes 6–15 s. (2026-11-10: it answered)
- [ ] Teleop, Monitor and Arm open and close (Back or Esc).
- [ ] Smooth? If it stutters: `/design?quality=reduced`, or check `/perf` (not run yet) (`docs/hub.md` → "Performance test").
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
- [ ] **`/perf`** full screen for a minute: note the average frames per second (then again with `/perf?res=1` and `/perf?res=0.5`: fewer pixels drawn, scaled up by the screen; `docs/hub.md` → "Performance test"). Once the drawing resolution per screen exists, try it on `/design` too.
- [ ] **Desktop on the Newline's HDMI** (tried 2026-11-10: as laggy as the Mac): run `/perf` on the desktop's own monitor, then on the Newline. Same number on both but the Newline looks worse → the Newline adds the lag. Things to try on the way: Ubuntu Settings → Displays → the Newline at 1920×1080, 60 Hz; the Newline's picture menu (a "PC" or "Game" mode, motion smoothing / noise reduction off, HDMI 2.0 if it has the setting); another of its HDMI ports. In Chrome, `chrome://gpu` should say "Hardware accelerated" for most lines.
- [ ] **The Newline's microphones** (for voice later): with the desktop's USB touch cable plugged into the Newline, does a microphone appear? Ubuntu Settings → Sound → Input, or `arecord -l` (lists them, records nothing). Note its name in `current-focus.md` step 7 (the microphone question).
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
- [ ] STOP from the Newline (or any other screen) stops a move. (Not tried yet.)
- [ ] Watch it on **AI Control** (`/ai`, or the hub's AI Control button): each call shows up as it happens; on a second monitor of the desktop: open AI Control in the hub → **Show on another screen**.
- Approve every move after reading it; never "always allow". Ctrl+C stops the brain (the arm goes limp: hold it if lifted).
- Afterwards: `logs/ai-tools/` has the calls. Write in `current-focus.md` step 2 what worked.
- 2026-11-10: Fable drove the real arm; it clearly needed more to go on than words (cameras, or at least `pose_view`). See `current-focus.md` step 2.

## 4. The white arm's cameras (5 min, for step 3)
- [ ] (If the builder picks the USB hub: `current-focus.md` → "Step 3, concretely".) Plug both white cameras into USB sockets you'll keep them in (**not** 1-7 and 1-8, the training cameras' sockets). Label the sockets and cables.
- [ ] `ls -l /dev/v4l/by-path/ /dev/v4l/by-id/`: this only lists names, it opens no camera. Paste the output into `current-focus.md` step 3, with which camera is which (top, wrist).

## 5. The training launcher, first try (10 min)
- [ ] Unplug `so101-white`'s USB (the launcher refuses while any other serial device is plugged in). Plug in both green arms.
- [ ] The desktop icon "SO-101 Training (LeLab)": every line of the check fine? If one isn't, it says what to change and starts nothing.
- [ ] LeLab opens at http://127.0.0.1:8000: check once that the follower moves when you move the leader. Note in `current-focus.md` ("Done on the side") how it went.

## 6. Quick checks (5 min each)
- [ ] **raspbot1 on a phone hotspot** (does the lab router fix its Wi-Fi? `network-setup-checklist.md`, Step 5): reach it by cable (Step 2 there), set the phone's hotspot to WPA2 (iPhone: "Maximize Compatibility"; Android: security "WPA2-Personal"), then on the Raspbot: `sudo nmcli dev wifi connect "<hotspot name>" password "<password>"`. Note in `GOTCHAS.md` (raspbot1 Wi-Fi) whether it joined. While it's connected, its own "Raspbot" hotspot is off; `sudo nmcli con up Raspbot` brings it back.
- [ ] **The Pi's full screen:** on `pi01`, open `/teleop` and then `/design`, press Ctrl+Shift+J (the console), type `document.fullscreenEnabled` and Enter. Note true/false for each in `GOTCHAS.md` ("`/teleop` on the Pi").

## 7. If there's time
- **Settings** (the ⚙ top right in `/design`): try Level of detail → maximal under "This screen", and `hub.look` → design (then `git diff config/` shows the change; `git checkout config/theme.yaml` undoes it).
- The new **Teleop** page on the Quest's browser; if anything misbehaves there, `/classic/teleop` is the old page.
- `/design?quality=maximal` on the Newline (adds the far-layer verses): still smooth?
- The Quest: teleop through the hub (`adb reverse tcp:8080 tcp:8080`, then `http://localhost:8080/teleop` on the Quest; `docs/quest-setup.md`).
- Show someone: `/design`, press start, ask it something, open Arm while Fable moves the arm.
