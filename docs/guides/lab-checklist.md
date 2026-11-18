# Lab checklist

Every step has a tag (like **9.4**). What to report is on the same line after **→**. Report as `9.4: yes` or `9.4: 6 s`. Run commands in a terminal on the lab desktop, in `~/lab-os`. Each part works alone.

Only what's still to do; finished steps are removed (their results are in `docs/dev/GOTCHAS.md` and `docs/plan/quick-jobs.md`). **Thursday 2026-11-19, top to bottom:** 0, F (only the steps whose quick job is done: `docs/plan/quick-jobs.md` → Done), 9 if the room is quiet, 3b, 11, 2.

Rules:
- A real arm moves without asking. Keep one hand at **STOP** (on any lab-os page) while an arm is powered.
- Ctrl+C in the brain's terminal makes the arm go limp. Hold the arm first if it is lifted.
- Green arms: never change motor IDs or firmware, never recalibrate, never touch the `lerobot` conda env, never start lab-os on them while LeLab is running.
- The voice is OpenAI's (the professor's key, in `.env` since 2026-11-18; restart the brain after any `.env` change). Only without it does the free Gemini key take over (about 15–20 spoken answers a day).

No ruler needed. Measure with: a sheet of letter paper (short edge 21.6 cm, long edge 27.9 cm), a bank card (8.6 cm long, 5.4 cm wide), the cube (3 cm), your phone lying flat (about 1 cm thick).

---

## 0. Update (5 min)
```bash
cd ~/lab-os
git switch main && git pull && git switch green-training-calibration && git merge main
uv sync --extra so101
uv run pytest -q
```
- **0.1** Read the last line `pytest` printed. → copy the line.

## F. This week's fixes on the real arm (25 min)
Setup: `so101-white` and its two cameras plugged in, green arms unplugged.
```bash
uv run --extra so101 lab-os serve --arm so101-white --speed 0.3 --host 0.0.0.0
```
In a **new** Claude Code session in `~/lab-os`: `/mcp` → `lab-os` → reconnect.
- **F.1** (quick job 29) Prompt: `Use the lab-os tools. Take a picture with so101-white-cam-wrist.` → does it show the view along the jaws? (yes / no)
- **F.2** (quick job 28) Open http://localhost:8080/teleop → Desktop control. Jog the gripper down, slowly, until the jaw tips just touch the table. Read the gripper's z on http://localhost:8080/ai. → z ___ cm (it should be about 0 now that quick job 28 is in; if not, add it to `table_z_cm` of `so101-white` in `config/devices.yaml`, e.g. z 0.3 → −1.3). The floor (1.1 cm above the table) may stop the jog before the tips touch: then note the lowest z and how far the tips are from the table.
- **F.3** (quick job 30) Hand on STOP. Prompt: `Go to the home pose.` (it takes three or four calls) → did it fold into nearly the position you always leave it in, the gripper hovering a little above where it rests, without hitting anything? (yes / no; how high are the jaw tips above the table? ___ cm)
- **F.4** (quick job 27) Open http://localhost:8080/design → Teleop. Unplug the arm's USB cable. → within a few seconds, does the hub show the arm as disconnected? (yes / no)
- **F.5** Plug it back in. Wait 10 seconds (the terminal should say `so101-white reconnected`). Desktop control → jog a joint (let go of the keys first, then press again). → did the arm move? (yes / no; copy any line the terminal keeps repeating)
- **F.6** (the Quest's wake word) The Quest on USB, `adb reverse tcp:8080 tcp:8080`. In the Quest's browser, `http://localhost:8080/design?device=quest-a` → ⚙ → This device → Wake word sensitivity → 7. Open `http://localhost:8080/xr` → Enter VR. Say "Hey Jarvis" 10 times with pauses. → number of misses.
- **F.7** (quick job 32) While doing the rest, leave the designed hub open on the desktop and glance at the brain's terminal now and then. → did the strip ever say "AI not connected"? (yes / no; copy any line starting `AI:` or `internet:`)
- **F.8** (quick job 34) On the desktop's hub (`/design?device=desk`): press ⏻ and start 3 times, watching the core. Then ⚙ → This device → **Startup as a video** on → Back, and press ⏻ and start 3 times again. → which looked smoother: drawn / video / the same? Any jump when the video hands over? Then the same with ⚙ → This device → Level of detail → **maximal** (its own recording): drawn vs video. Then switch both back.
- Hold the arm. Ctrl+C in the brain's terminal.

## 9. Voice (20 min)
Setup: USB microphone plugged in and picked in Ubuntu Settings → Sound → Input. Speakers on.
```bash
uv run lab-os serve --persona jarvis
```
Open http://localhost:8080/design in Chrome. Press start. Keep the terminal visible.
- **9.1** Listen to the greeting. → was it spoken? (yes / no)
- **9.2** Press ⏻, wait 10 seconds, press start again. → did the greeting start at once? (yes / no)
- **9.3** Hold the mic button, say "What's the next step?", let go. Count the seconds until the first spoken word. → seconds.
- **9.4** ⚙ → This device → Talking to it → **wake word** → Back. Say "Hey Jarvis, what's the next step" in one breath. → was the start of your question cut off on the screen? (yes / no)
- **9.5** Do 9.4 two more times. → copy the three `voice timing` lines from the terminal.
- **9.6** Walk backwards, one step at a time, saying "Hey Jarvis" at each step, until it stops working. → number of steps from the microphone.
- **9.7** From that spot: ⚙ → This device → Wake word sensitivity → 7. Try. Then 8. Try. → the lowest of 5, 7, 8 that works there.
- **9.8** At that sensitivity, talk normally near the microphone for one minute. Say "Jarvis" inside a sentence once. → number of times it woke by mistake.
- **9.9** Say "Hey Jarvis, pull up the teleop page." → did Teleop open? (yes / no)
- **9.10** Say "Hey Jarvis, show me the AI spend." → did the AI Spend page open? (yes / no)
- **9.11** Say "Hey Jarvis, go back to the hub." → did everything close? (yes / no)
- **9.12** Type in the ask line: `show me the commits`. → did the Commits page open? (yes / no)
- **9.13** (quick job 33) ⚙ → This device → Assistant language → Input: English, Output: English → Back. Say "Hey Jarvis, what's the next step?" twice. → answered in English both times? (yes / no)
- **9.14** Type in the ask line: `¿Cuál es el siguiente paso?` → answered in English? (yes / no). Then set Output back to Any.

---

## 3b. The stand camera's cm grid (15 min)
Setup: `so101-white` and its stand camera plugged in. Print `models/charuco/calibration-sheet-letter.pdf` with the printer set to **100 % / "Actual size"** (not "Fit to page").
```bash
uv run --extra so101 lab-os serve --arm so101-white --speed 0.3
```
- **3b.1** Lay the sheet flat in front of the arm, long edge pointing straight away from it, roughly centred. On `http://localhost:8080/teleop`, drive the gripper (keyboard) until the jaw tips touch the sheet's **"Board origin"** corner (top left as you look from the arm). Read the gripper's x and y on the AI Control page (`/ai`). → x ___ cm, y ___ cm
- **3b.2** Drive the arm up and to the side so it covers none of the sheet. In a second terminal: `uv run --extra so101 lab-os table-map so101-white-cam-stand --origin <x> <y>` (the numbers from 3b.1). → corners seen ___ of 24, worst ___ mm (or the error it printed)
- **3b.3** Open the preview it names (`logs/table-maps/…jpg`). → is the red dot on the arm's base? (yes / no / not in the picture) Do the grid lines run along the sheet's squares? (yes / no)
- **3b.4** Take the sheet away. Put the cube anywhere in front of the arm. New Claude Code session (`/mcp` → `lab-os` → reconnect). Prompt: `Use the lab-os tools. Take a picture with so101-white-cam-stand and tell me where the cube is, in cm. Then move the gripper to 3 cm above that spot, pointing straight down.` → what it said ___; is the gripper over the cube? (yes / off by about ___ cube-widths, which way ___)
- **3b.5** Same session. Prompt: `Pick it up with pick_at, then tell me whether you're holding it.` Watch `/ai`. → is the cube in the jaws? (yes / no) What did it say: holding or missed? Did `/ai` show each step before it moved? (yes / no)

## 11. Devices (30 min)
Setup: the desktop and the Newline (or a laptop in place of the Newline). No arm.
- **11.1** Stop any running brain (Ctrl+C). Run `uv run lab-os icon --device desk`. Ubuntu's app list → click **Start lab-os**. → did a terminal and a full-screen hub open? (yes / no)
- **11.2** Look at the hub's address. → does it contain `?device=desk`? (yes / no)
- **11.3** Click **Start lab-os** a second time. → did a second brain start? (yes / no)
- **11.4** On the desktop run `hostname -I` and take the first address. On the Newline's Chrome open `http://<address>:8080/?device=newline`. → did the page load? (yes / no)
- **11.5** On the Newline: ⚙ → This device → Drawing resolution → 0.5. On the desktop run `cat ~/lab-os/config/hub-devices.yaml`. → does it show `newline:` with `res: '0.5'`? (yes / no)
- **11.6** On the Newline: Chrome menu → Add to Home screen. Close Chrome. Tap the new icon. Open ⚙. → does it say "This device: newline"? (yes / no)
- **11.7** On the Newline: open Monitor → **Open on…** → **desk**. → did Monitor open on the desk? (yes / no)
- **11.8** Look at the Newline. → does it show "Monitor is on desk"? (yes / no)
- **11.9** On the desk press **Back**. → did Monitor close on the desk and the line disappear on the Newline? (yes / no)
- **11.10** On the Newline: Monitor → Open on… → desk. Then on the Newline press **Bring it back**. → did Monitor come back to the Newline? (yes / no)
- **11.11** On the desk: open Teleop → Open on… → **newline**. → did Teleop open on the Newline? (yes / no)
- **11.12** Send Monitor to the desk again. Ctrl+C in the brain's terminal. Wait 10 seconds. Click **Start lab-os**. → did both hubs come back without reloading? (yes / no) After how many seconds?
- **11.13** Shut down the desktop and switch the Newline off. Switch both on. Click **Start lab-os**, then tap the Newline's icon. → are both back under their names, the Newline's resolution still 0.5? (yes / no)

## 2. The Newline (20 min)
Setup for 2.1–2.4: an Ethernet cable from the desktop to the Newline. Brain: `uv run lab-os serve --host 0.0.0.0`. The desktop's address: `hostname -I`, the first one.
- **2.1** On the Newline's Chrome: `chrome://flags` → search "Insecure origins treated as secure" → type `http://<address>:8080` → Enabled → Relaunch. Open `http://<address>:8080/design?device=newline`. Press start. → is there a mic button next to "Ask anything"? (yes / no)
- **2.2** Hold the mic button and ask a question. → did it hear and answer? (yes / no)
- **2.3** ⚙ → This device → Drawing resolution → 1. Press ⏻, then start. → is the startup smooth? (yes / no)
- **2.4** Same with Drawing resolution 0.5. → is the startup smooth? (yes / no) Does it look too blurry? (yes / no)
- **2.5** Plug the desktop into the Newline's HDMI. Ubuntu Settings → Displays → the Newline → 1920×1080. → the refresh rate shown, in Hz.
- **2.6** In the Newline's own picture menu, look for a "PC" or "Game" mode and switch it on. → the mode's name, or "none found".
- **2.7** Open http://localhost:8080/design on the Newline's screen. Press start. → is the startup smooth at 1920×1080? (yes / no)

## Optional: raspbot1 on a phone hotspot (10 min)
Setup: the Raspbot reached by cable. Phone hotspot security set to **WPA2-Personal**.
- **R.1** On the Raspbot: `sudo nmcli dev wifi connect "<hotspot name>" password "<password>"`. → did it join? (yes / no; if no, copy the error line)
- **R.2** `sudo nmcli con up Raspbot`. → nothing to report.
