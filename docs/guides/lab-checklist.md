# In the lab: what to test, in order

A walk-in list for the lab desktop (`ai-comp-lab-ubuntu-76358`). Each part works without the next. Results go in the focus step's status (`docs/plan/current-focus.md`), surprises in `docs/dev/GOTCHAS.md`. The plans and results of earlier visits: `docs/archive/lab-checklist-plans-2026-11-10-to-12.md`.

**The next visits, in this order** (Fable 5.2 ends Monday 2026-11-16, so the real-arm AI first; the demo is Thursday 2026-11-19):
1. Part 0.
2. Part 3, the AI on `so101-white`: the height checked with a ruler first, then the cube pick (after quick jobs 1–3 if they're merged).
3. Part 8, the green arms in lab-os (plugged in as for training, their cameras back in sockets 7 and 8).
4. Part 11, devices (step 8): the "Start lab-os" icon, Monitor from the Newline to the desk and back, everything off and on again.
5. Part 7 on the real arm: 1:1 (after quick job 13, a ruler for the scale), relative vs 1:1.
6. Part 5, the training launcher, if it hasn't run from the icon yet.
7. Part 10 again once quick jobs 10–11 are merged.
8. Part 2's leftovers: the refresh rate at 1920×1080, the Newline's picture mode, Chrome's flag for its microphone.
9. Part 6, raspbot1 on a WPA2 hotspot.
10. Before the demo: `FEATURES.md` row by row on the real hardware.

**Gemini's free key speaks only ~15–20 answers a day** (10 requests per TTS model per day, GOTCHAS): if answers come silent with "…sending too much voice", that's it for the day (it resets at midnight Pacific). Keep some for the demo.

**Never:** change the green arms' motor IDs or firmware, write their calibration, touch the `lerobot` conda env, or open a green port while LeLab is using it (CLAUDE.md, loosened 2026-11-12). Since step 11 the brain follows these rules itself (part 8 checks it does).

## 0. Get the latest (2 min)
```bash
cd ~/lab-os
git pull
uv sync --extra so101          # LeRobot for the SO-101s; plain `uv sync` would remove it
uv run pytest -q               # should end "passed"
```
Since quick job 1 (2026-11-14) Claude Code no longer asks before any lab-os tool, moves included: keep a hand near STOP.
- [ ] **No prompts, fake arm first (quick job 1):** `uv run lab-os serve` (fake arm), then a **new** Claude Code session in `~/lab-os`: `/mcp` → `lab-os` connected, then "Use the lab-os tools: go to the home pose, then open the gripper to 50." Both moves run with no permission question, and the hub's AI Control (`http://localhost:8080/ai`) lists them. If it still asks: `.claude/settings.local.json` may hold an old `"ask"` rule for `mcp__lab-os__…` (ask beats allow): delete that line.

## 1. The designed hub on the desktop's own screen (5 min)
```bash
uv run lab-os serve --host 0.0.0.0
```
Open **http://localhost:8080/design** in Chrome. Check:
- [x] One click: full screen, the unlock sound, the jump, the title, the greeting, the hub. (2026-11-10)
- [ ] The strip says the venue, the persona and `AI: …` (the key in `~/lab-os/.env`).
- [x] Ask something ("What's next?"). Gemini's free key takes 6–15 s. (2026-11-10: it answered)
- [ ] Teleop, Monitor and Arm open and close (Back or Esc).
- [ ] Smooth? If it stutters: `/design?quality=reduced` or `/design?res=1`, or check `/perf` (`docs/guides/hub.md` → "Performance test").
- [ ] **Full screen button:** press Esc to leave full screen: a ⛶ appears in the strip next to ⏻ and ⚙; it brings full screen back. The VR headset icon should **not** be in the strip on the desktop (it used to show everywhere).
- [ ] Sound comes out of the speakers you want.

Full screen without the click, as an app window (close it with Alt+F4):
```bash
google-chrome --app=http://localhost:8080/design --start-fullscreen
```

## 2. The Newline (10–15 min)
Find the desktop's address: `hostname -I` (the first one). With the brain from part 1 still running, on the Newline's Chrome open `http://<that address>:8080/design`.
- [ ] **It loads.** If it doesn't, the network keeps devices apart: `docs/guides/network-setup-checklist.md` → "Networks before the router" (the HDMI + USB-touch cable to the desktop is the quickest fix, and `localhost` then even allows voice later).
- [ ] **One tap = full screen + start.** Swipe from the edge: can you leave it? Does the Newline's own bar stay away?
- [ ] Chrome menu → **Add to Home screen**: does the icon open the hub? (On `http://` it opens as a tab; tap once for full screen.)
- [ ] Touch: the panels' details pages, the commit range buttons, the devices list.
- [ ] Leave it alone for 30 minutes: it goes back to the start screen (`hub.reset_after_s`; it dims to sleep after 15 minutes). To check it quickly, set a shorter reset in ⚙ → The hub, then set it back.
- [x] **`/perf`** full screen for a minute (2026-11-13, its own Chrome: 44 fps with 3000 stars, 59 with 1000): note the average frames per second (then again with `/perf?res=1` and `/perf?res=0.5`: fewer pixels drawn, scaled up by the screen; `docs/guides/hub.md` → "Performance test").
- [ ] **The drawing resolution on the hub:** open `http://<address>:8080/design?device=newline&res=1`, then `…&res=0.5`. Is the jump and the network smoother? Does it look too soft? Keep the best one for the Newline: ⚙ → **This device → Drawing resolution** (the brain keeps it under the name `newline`; no `?res=` needed after that). Note the numbers in `docs/plan/current-focus.md` step 12.
- [ ] If a page doesn't go full screen on the Newline, press its **Full screen** button: it says why (note the sentence in `docs/dev/GOTCHAS.md`).
- [x] **Desktop on the Newline's HDMI** (2026-11-13: choppy at 1920×1080 though `/perf` said 60, smooth at 1600×900; left: the refresh rate Ubuntu picks at 1080p and the picture mode): run `/perf` on the desktop's own monitor, then on the Newline. Same number on both but the Newline looks worse → the Newline adds the lag. Things to try on the way: Ubuntu Settings → Displays → the Newline at 1920×1080, 60 Hz; the Newline's picture menu (a "PC" or "Game" mode, motion smoothing / noise reduction off, HDMI 2.0 if it has the setting); another of its HDMI ports. In Chrome, `chrome://gpu` should say "Hardware accelerated" for most lines.
- [ ] **The Newline's microphones** (for voice later): with the desktop's USB touch cable plugged into the Newline, does a microphone appear? Ubuntu Settings → Sound → Input, or `arecord -l` (lists them, records nothing). Note its name in `docs/plan/current-focus.md` step 7. (2026-11-13: the Newline's own Chrome hears well, but the hub over `http://<ip>` shows no mic button: Chrome's flag, `docs/guides/voice.md` → "Secure pages".)
- [ ] The plain hub's two taps too (`http://<address>:8080/plain`).

## 3. Fable drives the real arm (20–30 min, you at the arm)
The full walkthrough: `docs/guides/ai-control.md` → "5. On the real arm". Short version:
```bash
ls -l /dev/serial/by-id/       # so101-white = …5B41532410-if00
uv run --extra so101 lab-os serve --arm so101-white --speed 0.3 --host 0.0.0.0
```
(`--host 0.0.0.0` lets the Newline keep showing the hub; it's view-only there, and its STOP works.)
- In Claude Code: `/mcp` → `lab-os` → reconnect; `/model` → Fable 5.2.
- [ ] "Read the arm's status": the joints match the arm.
- [ ] "Go to the home pose" (it moves without asking: watch it).
- [ ] "Move the gripper 3 cm lower, pointing straight down."
- [ ] The cube: measure it (cm in front of the base's middle, cm to the left), then the step-2 prompt.
- [x] STOP from the Newline (or any other screen) stops a move. (2026-11-13, the Newline over Ethernet.)
- [ ] **Height first** (the reading looked 1–2 cm low on 2026-11-12): "go to x 20, y 0, z 1, pointing straight down" (z −0.5 once quick job 3 is in), then hold a ruler by the jaw tips. How high are they really? Note it in step 2.
- [x] **Honest "arrived"** (2026-11-12: the elbow ~3° short on nearly every move, GOTCHAS): after each move the result says `arrived` or `stopped_short` with `off_by_cm` and which joints fell short. Hold a ruler to one `stopped_short`: is it about that far off? Near the base, a low `move_to` like "x 11, y 0, z 2.1" is where it fell 1.6 cm short on 2026-11-10: is it still short (load / the arm folded) or does it arrive now (the half-second hold)?
- [x] **`pose_view`** (2026-11-12, used in the cube pick): ask Fable "Look at the arm with pose_view, with a mark where the cube is (… cm in front, … cm left, 1.5 cm up, size 3 cm), before you close the gripper." Does the picture match the real arm? To see the same picture yourself: open **http://localhost:8080/api/pose-view.png** (reload for a new one).
- [ ] The cube task again, this time with `pose_view` before every grip: does Fable catch its own misses?
- [ ] Watch it on **AI Control** (`/ai`, or the hub's AI Control button): each call shows up as it happens; on a second monitor of the desktop: open AI Control in the hub → **Open on…** → **Another monitor of this computer**.
- Claude Code doesn't ask before moves (quick job 1): STOP is the brake. Ctrl+C stops the brain (the arm goes limp: hold it if lifted).
- Afterwards: `logs/ai-tools/` has the calls. Write in `docs/plan/current-focus.md` step 2 what worked.

## 4. The white arm's cameras (5 min, for step 3)
- [x] 2026-11-12: both white cameras in sockets 7 and 8 (the training cameras' sockets, a temporary alias: `docs/plan/current-focus.md` → "Hacks to clean up"); `so101-white-cam-a` looks from above, `-b` is the wrist camera.
- [ ] When the powered USB hub arrives: plug both white cameras into its sockets for good. Label the sockets and cables.
- [ ] `ls -l /dev/v4l/by-path/ /dev/v4l/by-id/`: this only lists names, it opens no camera. Tell Claude the new socket names, with which camera is which (top, wrist), for `config/devices.yaml`.

## 5. The training launcher, first try (10 min)
- [ ] Unplug `so101-white`'s USB (the launcher refuses while any other serial device is plugged in). Plug in both green arms.
- [ ] The desktop icon "SO-101 Training (LeLab)": every line of the check fine? If one isn't, it says what to change and starts nothing.
- [ ] LeLab opens at http://127.0.0.1:8000: check once that the follower moves when you move the leader. Note in `FEATURES.md` (Training launcher) how it went.

## 6. Quick checks (5 min each)
- [ ] **raspbot1 on a phone hotspot** (does the lab router fix its Wi-Fi? `docs/guides/network-setup-checklist.md`, Step 5): reach it by cable (Step 2 there), set the phone's hotspot to WPA2 (iPhone: "Maximize Compatibility"; Android: security "WPA2-Personal"), then on the Raspbot: `sudo nmcli dev wifi connect "<hotspot name>" password "<password>"`. Note in `docs/dev/GOTCHAS.md` (raspbot1 Wi-Fi) whether it joined. While it's connected, its own "Raspbot" hotspot is off; `sudo nmcli con up Raspbot` brings it back.
- [ ] **The Pi's full screen:** on `pi01`, open `http://192.168.7.72:8080/teleop` (the desktop's address). There's now always a **Full screen** button in the bar while it isn't full screen: press it (or hover over it). If full screen isn't possible, it says why. Note the sentence in `docs/dev/GOTCHAS.md` ("`/teleop` on the Pi"). Same on `/design` (the ⛶ in the strip) to compare.

## 7. Teleop's 1:1 mode on the Quest (15–20 min; fake arm first)
Fake arm, recording the session (so a problem can be replayed at home):
```bash
uv run lab-os serve --record recordings/quest-1to1-$(date +%F).jsonl
adb reverse tcp:8080 tcp:8080
```
In the Quest's browser: `http://localhost:8080/teleop` → **Hand → arm → 1:1** → **Enter AR**. (`docs/guides/quest-setup.md` → "1:1 mode".)
- [ ] The panel says "REACH THE GRIPPER · N cm" and a see-through ball sits at the 3D gripper; it turns green with your hand inside.
- [ ] Hold Grip in the ball: nothing jumps. Move: the 3D gripper stays at your hand (same distance, not half).
- [ ] Reach far out (past the arm's reach) and come back: the gripper meets your hand again, no re-grabbing.
- [ ] Bare hands (controllers down): the right wrist in the ball, left pinch = move.
- [ ] Relative still works (switch back on the page; grip again after switching).

Then the **real arm**, with you at it, slowly (you at the arm, hand near STOP). If part 5 left the green arms plugged in, unplug them and plug `so101-white` back in first:
```bash
ls -l /dev/serial/by-id/       # so101-white = …5B41532410-if00
uv run --extra so101 lab-os serve --arm so101-white --speed 0.2 --record recordings/quest-1to1-real-$(date +%F).jsonl
adb reverse tcp:8080 tcp:8080
```
- [ ] Line up the 3D arm on the real one (left Grip, move and turn until it sits on it, let go), then 1:1 as above. Does the real gripper stay at your hand?
- [ ] **Ruler:** with the arm in 1:1, move the hand 10 cm forward along a ruler: does the gripper move 10 cm? (It felt slightly off on 2026-11-13; quick job 13.)
- [ ] **Speed:** the page says "1:1 follows as fast as 180°/s". Move the hand 10 cm left quickly: does the real gripper arrive about when your hand does? **Wave** (small and slow first): does the arm wave with you? If 180 feels too slow: ⚙ Settings → Robots → **Teleop 1:1: top joint speed** → 240 or `none`, then restart the brain (Ctrl+C, the same command again).
- [ ] **Motor wear, measured:** do about 5 minutes in **relative**, let the arm rest 10 minutes, then about 5 minutes of the same kind of moves in **1:1**. Then compare the servos' temperatures:
  ```bash
  tail -n 3 logs/servo-health/*so101-white.jsonl     # the latest readings: temp_c per servo
  grep -h '"mode": "one_to_one"' logs/servo-health/*so101-white.jsonl | tail -n 1
  grep -h '"mode": "relative"' logs/servo-health/*so101-white.jsonl | tail -n 1
  ```
  Much warmer in 1:1 (well over 50 °C) → keep relative as the default; about the same → 1:1 can become the default (the builder's call). If the panel says "SERVOS WARM, SLOWED", stop and let them cool.
- [ ] Note in `docs/plan/current-focus.md` (step 10) how it felt, and whether 1:1 should become the default (`FEATURES.md` too). At home: `uv run lab-os-teleop replay recordings/quest-1to1-<date>.jsonl` replays it on the fake arm (watch `/monitor`).

## 8. The green arms in lab-os (step 11; 30–40 min, you at the arm)
Green follower, green leader and both training cameras plugged in as for training; `so101-white` unplugged. Part 0 first (`git pull`, `uv sync --extra so101`, `uv run pytest -q`).

**a. Which green is the follower?** `config/devices.yaml` says the follower is `…3501` and the leader `…1599` (from `CLAUDE.md`). The training launcher remembered which one LeLab uses as the follower (only if part 5 started it once):
```bash
cd ~/lab-os
cat logs/green-last-start.json        # {"follower": "5B41533501", ...} = devices.yaml is right
ls -l /dev/serial/by-id/              # both greens there: …3501 and …1599
```
- [ ] If the file names `…1599` as the follower, **stop here** and tell Claude: the two green entries in `config/devices.yaml` swap their ports and serials.

**b. The calibration file** (only listed, nothing opened or changed):
```bash
ls -l ~/.cache/huggingface/lerobot/calibration/robots/*/
sha256sum ~/.cache/huggingface/lerobot/calibration/robots/*/*.json > /tmp/green-cal-before.txt
```
- [ ] Exactly one `.json` in there? Then nothing to do. Several: note which is the green follower's (LeLab's robot name) and tell Claude, which adds `calibration_id: <that name without .json>` to `so101-green` in `config/devices.yaml`.

**c. Refusals, with LeLab running** (start it with the desktop icon "SO-101 Training (LeLab)", open its page, press **teleop** so it opens the ports, leave it running):
```bash
uv run --extra so101 python -m lab_os.robots.so101 so101-green
```
- [ ] It says `Not opening anything: so101-green is in use by … (pid …): one program per port …` and nothing else happens. (If it reads joints instead, LeLab hadn't opened the port yet: say so, that's worth knowing.)
- [ ] Stop LeLab's teleop, Ctrl+C in LeLab's terminal (LeLab closed).

**d. The motor setup tool refuses the greens** (opens nothing, by name and by board):
```bash
uv run --extra so101 python -m lab_os.robots.so101_setup check --arm so101-green
uv run --extra so101 python -m lab_os.robots.so101_setup calibrate --arm so101-green-leader
```
- [ ] Both say `Not opening anything: … is borrowed from another project …`.

**e. Read only, LeLab closed:**
```bash
uv run --extra so101 python -m lab_os.robots.so101 so101-green --watch
```
- [ ] It connects (no "different calibration" message). Move each joint **by hand** (the arm is limp): the numbers follow, about 0 at the middle pose, and the same directions as the white arm (`docs/dev/GOTCHAS.md` → joint directions). Ctrl+C.

**f. Moving, slowly** (you at the arm, hand near STOP):
```bash
uv run --extra so101 lab-os serve --arm so101-green --speed 0.3
```
- [ ] Open http://localhost:8080/teleop on the desktop: the 3D arm matches the real one. Small jog moves with the desktop controls; STOP works.
- [ ] In Claude Code (`/mcp` → `lab-os` → reconnect): "Use the lab-os tools. Read so101-green's status, then go to the home pose." (It moves without asking: watch it.) Is `home` a safe pose for the green arm too? (It comes from the white arm's kinematics.)
- [ ] **The launcher refuses while the brain has the port:** with the brain still running, the desktop icon "SO-101 Training (LeLab)". One line says `green arm …3501 is open in …: stop it first`, and LeLab doesn't start. Press Enter to close it.
- [ ] Ctrl+C in the brain's terminal (the arm goes limp: hold it if it's lifted).

**g. The calibration is untouched, and LeLab still works:**
```bash
sha256sum -c /tmp/green-cal-before.txt     # every line should say OK
```
- [ ] Every line `OK`. Then start LeLab with the icon and check teleop there once (the follower follows the leader), as before.

**h. Which training camera is which** (only lists names; nothing opens a camera):
```bash
ls -l /dev/v4l/by-path/
```
- [ ] Entries with `usb-0:7` and `usb-0:8` (`so101-green-cam-a` and `-b`). Unplug the **wrist** camera's cable for a moment and run the `ls` again: the socket whose lines vanish is the wrist camera. Plug it back in. Tell Claude which socket is the wrist and which the top camera, so the names can change to `so101-green-cam-wrist` / `-top`. If the sockets aren't 7 and 8 any more, paste the `ls` output.
- [ ] Note in `docs/plan/current-focus.md` step 11 what worked.

## 9. Voice (step 7; 20–30 min, the USB microphone and the speakers)
Needs `GEMINI_API_KEY` in `~/lab-os/.env` (it's there) and the hub on **this desktop's own screen** (`localhost`: other screens by IP get no microphone).

**2026-11-13:** push-to-talk and the wake word work at the desk with the USB microphone (sometimes only spoken louder). Not noted yet: the distance, false wakes, the time to the first spoken word.

**a. The microphone** (before starting anything):
- [ ] Plug in the USB microphone (any socket). Ubuntu: Settings → Sound → **Input**: pick it; the level bar moves when you talk. Output: the speakers you want, at a normal volume.

**b. Start** (a fresh brain reads `.env` and the persona):
```bash
cd ~/lab-os
uv run lab-os serve --persona jarvis
```
Open **http://localhost:8080/design** in Chrome and press start.
- [ ] After the jump, the greeting is **spoken** while it's typed, ending "You can talk to me: hold the mic." (No sound at all? ⚙ → This device → Sound must be on.)
- [ ] A **mic button** sits next to "Ask anything". If there's none, check what the brain says:
  ```bash
  curl -s http://localhost:8080/api/status | python3 -m json.tool | grep -A12 '"voice"'
  ```
  (`"available": false` + `"why"` says why; `true` but still no button = the browser sees no microphone: check part a, then reload.)

**c. Push-to-talk:**
- [ ] **Hold** the mic (or Space) and ask "What's the next step?", then let go. Chrome asks for the microphone the first time: **Allow**. Your words appear above the core while you talk; the core says listening → thinking → speaking and moves with the voice; the answer is spoken (the free key: 3–15 s to the first word).
- [ ] Ask again while it's speaking (hold the mic): it stops talking and listens. Esc while it speaks: it stops.
- [ ] Loud speakers: does it hear itself? (It shouldn't: echo cancellation, and it only listens while held.)
- [ ] Note the time from letting go to the first spoken word: ________

**d. Dictation:** ⚙ (top right) → This device → **Talking to it → dictation**, then Back.
- [ ] Tap the mic once, say a sentence, stop talking: the words appear in the ask line and it stops by itself after ~1.5 s. Fix a word, press Enter: it's asked (the answer is text only, like typing).

**e. The wake word:** ⚙ → This device → Talking to it → **wake word**, then Back.
- [ ] A small **dot** appears in the status strip (and Chrome's recording sign in the tab). The core stays idle.
- [ ] From the desk: "Hey Jarvis" … "what time is it?": the core listens after the phrase, the question ends after a short silence, the answer is spoken.
- [ ] From across the room, and with the fans/AC running: how far does it still work? ________ m. (A weak USB dongle may only work up close: then a conference speakerphone or microphone array is the fix, `docs/guides/voice.md`.)
- [ ] False wakes: talk normally near it for a minute (say "Jarvis" in a sentence too). Any wake it shouldn't have? ________
- [ ] While its own answer plays, saying "hey Jarvis" doesn't wake it (expected: it doesn't listen for the phrase while speaking).
- [ ] When done, set Talking to it back to **push-to-talk** (or keep the wake word for the demo).

**f.** Note the results in `docs/plan/current-focus.md` step 7 (status) and surprises in `docs/dev/GOTCHAS.md`.

## 10. The hub in VR (step 10; 20–30 min, the Quest on USB)
Tried in the headset 2026-11-13: it works; a cluster of linked dots far away and a chat that doesn't scroll (quick jobs 10–11). Fake arm first:
```bash
uv run lab-os serve
adb reverse tcp:8080 tcp:8080          # re-run after every re-plug
```
In the Quest's browser: `http://localhost:8080/xr`. If **Allow the microphone** shows, press it and allow (once). Then **Enter VR**. (`docs/guides/quest-setup.md` → "The hub in VR".)
- [ ] **Start:** the small core with "Pull the trigger or pinch to start" floats ahead. Pull the trigger: the bolts pull back, the ring opens, then the jump. Do the lines grow out of the stars you were looking at? Cyan with whiter heads (not black and white)? Comfortable, or too fast / too bright (note it)?
- [ ] **Arrival:** the flash, the network streaking in, the core's rings locking on, the checks, the place's name, the greeting (spoken if voice works). Then everything flies to its place and the callouts unfold.
- [ ] **Reading:** can you read the callouts, the strip and the log without leaning in? Is anything too far to the side (you shouldn't need to turn your head much)? Note sizes that feel off.
- [ ] **Pointing:** each controller has a thin beam and a ring where it lands. Point at a callout and pull the trigger: its page unfolds, the core docks in its corner; **B** closes it. Try 7d/14d/30d on Commits, **List all** and a device on Devices. Then bare hands: point and pinch.
- [ ] **The trigger on empty space does nothing**; **⏻** (top right) goes back to the start screen; the trigger there starts the jump again.
- [ ] **Teleop** (left of the core): the arm room opens, the TELEOP tab top left. Grip and move: does the fake arm follow (watch `/monitor` on the desktop)? A/X stops; left grip moves the 3D arm; Y puts it back. **B** (or the right controller on ← and the trigger) goes back to the hub; the desktop's `/teleop` can take control again.
- [ ] **Monitor / AI Control:** the arm hologram with joint angles; move the arm from the desktop's `/teleop` and watch the hologram follow; **STOP** stops it. AI Control lists tool calls if Claude Code drives the arm meanwhile.
- [ ] **Asking:** point at "Ask anything", hold the trigger, ask "what's next?", let go: the answer types out under the core and is spoken. Then say "hey Jarvis, what's next?" without pressing anything (the dot in the strip should be on). Then ask on the desktop (its mic): does the question and answer show in VR?
- [ ] Note what felt wrong in `docs/plan/current-focus.md` step 10 and surprises in `docs/dev/GOTCHAS.md`. With time: the real `so101-white` through Teleop in VR (you at the arm, `--speed 0.2`, part 7's setup).

## 11. Devices (step 8; 20–30 min, the desktop and the Newline, or a laptop instead of the Newline)
Built 2026-11-14 and tried with headless browser pages only (`docs/guides/hub.md` → "Devices"). Fake arm is enough. Part 0 first.

**a. The "Start lab-os" icon on the desktop** (once):
```bash
cd ~/lab-os
uv run lab-os icon --device desk
```
- [ ] It says where it wrote the icon. Ubuntu's app list → **Start lab-os** → right-click → **Add to Favorites**.
- [ ] Close any running brain (Ctrl+C in its terminal). Click the icon: a terminal with the brain's log opens, then Chrome full screen on the hub with `?device=desk` in the address. One tap starts it. (No Chrome? It opens the default browser instead: note which.)
- [ ] Click the icon again while it runs: only a second hub window opens, no second brain ("lab-os already runs here" in a terminal that closes).
- [ ] If the hub isn't the designed one: ⚙ → The hub → Look → design (the icon opens whatever `hub.look` says).

**b. The Newline as a device.** Find the desktop's address: `hostname -I` (the first one). On the Newline's Chrome open `http://<that address>:8080/?device=newline` (the brain from **a** listens for other devices).
- [ ] It loads with `?device=newline` still in the address. ⚙ → **This device: newline** (the heading says the name).
- [ ] ⚙ → This device → Drawing resolution → 0.5. Then on the desktop: `cat ~/lab-os/config/hub-devices.yaml` shows `newline:` with `res: '0.5'`. The desk's own settings didn't change.
- [ ] Chrome menu → **Add to Home screen**: the icon opens the hub as `newline` (check the ⚙ heading).

**c. Open on… (the "done when" of step 8).**
- [ ] On the **Newline**: open **Monitor** → **Open on…** (next to Back): the list shows **desk** ("the hub"). Pick it: Monitor opens on the desk's screen, inside its hub, with "Opened from newline" under the title; the Newline goes back to its hub and shows "Monitor is on desk · **Bring it back**" at the top.
- [ ] On the **desk**: press **Back**: Monitor closes there, and the Newline's line disappears.
- [ ] Again from the Newline, then **Bring it back** on the Newline: Monitor closes on the desk and opens on the Newline.
- [ ] From the **desk** to the Newline (Teleop or AI Control): same, the other way. Does the menu ever cover STOP? (It shouldn't: it opens on the left.)
- [ ] The desk's **second monitor**: open a second hub there (`google-chrome --new-window --app=http://localhost:8080/design?device=desk --window-position=1920,0 --start-fullscreen`, the 1920 = the first monitor's width). From the Newline, Open on… → desk: it asks **which monitor** ("left monitor" / "right monitor"); pick one. With one of them showing a page, it picks the free one without asking.
- [ ] Leave the Newline at its **start screen** (⏻), then send Monitor to it from the desk: does it open there without a tap?
- [ ] On the Newline, switch to another app (the Newline used for something else): the desk's Open on… should no longer list it once its hub tab is closed. (Only devices with the hub open are listed.)

**d. Everything off, then one tap each (the other half of "done when").**
- [ ] With Monitor sent to the desk: stop the brain (Ctrl+C in its terminal), wait 10 s, click **Start lab-os** again. Within ~5 s both hubs are back by themselves (no reload): the Newline's "Monitor is on desk" line comes back too.
- [ ] Switch everything off (the desktop shut down, the Newline off). Switch on: click **Start lab-os** on the desktop, then the home-screen icon on the Newline. Both come back under their names (⚙ headings), with their own settings (the Newline's drawing resolution still 0.5).
- [ ] The Newline's icon tapped *before* the brain runs: Chrome says it can't reach the page. Tap again once the brain runs (expected; note if it's a nuisance).
- [ ] Note the results in `docs/plan/current-focus.md` step 8 and surprises in `docs/dev/GOTCHAS.md`.

## 12. If there's time
- **Settings** (the ⚙ top right in `/design`): try Level of detail → maximal under "This device", and `hub.look` → design (then `git diff config/` shows the change; `git checkout config/theme.yaml` undoes it).
- The new **Teleop** page on the Quest's browser; if anything misbehaves there, `/classic/teleop` is the old page.
- `/design?quality=maximal` on the Newline (adds the far-layer verses): still smooth?
- The Quest: teleop through the hub (`adb reverse tcp:8080 tcp:8080`, then `http://localhost:8080/teleop` on the Quest; `docs/guides/quest-setup.md`).
- Show someone: `/design`, press start, ask it something, open Arm while Fable moves the arm.
