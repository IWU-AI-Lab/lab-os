# Lab checklist

Every step has a tag (like **9.4**). What to report is on the same line after **→**. Report as `9.4: yes` or `9.4: 6 s`. Run commands in a terminal on the lab desktop, in `~/lab-os`. Each part works alone.

**About one hour, shortest first: parts 0, 6, 1, 5, 9.** Then, on later lab days: 3, 3b, 8, 11, 7, 10, 2.

Rules:
- A real arm moves without asking. Keep one hand at **STOP** (on any lab-os page) while an arm is powered.
- Ctrl+C in the brain's terminal makes the arm go limp. Hold the arm first if it is lifted.
- Green arms: never change motor IDs or firmware, never recalibrate, never touch the `lerobot` conda env, never start lab-os on them while LeLab is running.
- The free voice key speaks about 15–20 answers a day. Silent answers with "sending too much voice" = used up until midnight Pacific.

No ruler needed. Measure with: a sheet of letter paper (short edge 21.6 cm, long edge 27.9 cm), a bank card (8.6 cm long, 5.4 cm wide), the cube (about 2.5 cm), your phone lying flat (about 1 cm thick).

The older, longer version with explanations: `docs/archive/lab-checklist-long-2026-11-16.md`.

---

## 0. Update (5 min)
```bash
cd ~/lab-os
git switch main && git pull
uv sync --extra so101
uv run pytest -q
```
- **0.1** Read the last line `pytest` printed. → copy the line.

## 6. Quick checks, fake arm (10 min)
```bash
uv run lab-os serve
```
- **6.1** Open http://localhost:8080/teleop → Desktop control. Hold two jog keys at once, then one, then two others. → did the 3D model change size? (yes / no)
- **6.2** Same page. → do all six joint rows stay in place? (yes / no)
- **6.3** Open http://localhost:8080/settings → The assistant → Monthly AI budget → set 0. Ask the hub a question. → did it say the budget is used up? (yes / no)
- **6.4** Set the budget back to 20. Ask again. → did it answer? (yes / no)
- **6.5** Settings → Safety limits in this venue → switch **Floor** off. Ctrl+C in the terminal. Run `uv run lab-os serve` again. → did the terminal print `LIMITS OFF in venue lab: floor`? (yes / no)
- **6.6** Switch Floor back on. Ctrl+C. Run `git checkout config/venues/lab.yaml`. → nothing to report.
- **6.7** In Chrome, open http://localhost:8080/teleop on its own (not in the hub) → **Full screen** → **Desktop control** → hold a jog key → tap **Esc** once. → did the arm stop? (yes / no) Is the page still full screen? (yes / no)

## 1. The hub on the desktop (5 min)
```bash
uv run lab-os serve --host 0.0.0.0
```
Open http://localhost:8080/design. Press start.
- **1.1** Open and close Teleop, Monitor and AI Control. → did all three open and close? (yes / no; name the one that didn't)
- **1.2** Press Esc. Press the ⛶ button in the strip. → did full screen come back? (yes / no)
- **1.3** Look at the whole startup and hub. → anything that stuttered or looked wrong (one line each, or "nothing").

## 5. Training launcher (10 min)
Setup: `so101-white` unplugged, both green arms plugged in.
- **5.1** Double-click the desktop icon "SO-101 Training (LeLab)". → did every check line pass? (yes / no; if no, copy the failing line)
- **5.2** On LeLab's page (http://127.0.0.1:8000) press teleop. Move the leader. → did the follower follow? (yes / no)
- **5.3** Close LeLab (Ctrl+C in its terminal). → nothing to report.

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

---

## 3. AI drives so101-white (30 min)
Setup: `so101-white` plugged in, green arms unplugged. A sheet of letter paper, the cube, your phone.
```bash
ls -l /dev/serial/by-id/
uv run --extra so101 lab-os serve --arm so101-white --speed 0.3 --host 0.0.0.0
```
In a **new** Claude Code session in `~/lab-os`: type `/mcp`, pick `lab-os`, reconnect. Give the prompts one at a time.
- **3.1** Prompt: `Use the lab-os tools. Read the arm's status, then go to the home pose.` → did Claude Code ask permission before moving? (yes / no)
- **3.2** Prompt: `Move to x 20, y 0, z 2, pointing straight down.` Stand the cube next to the jaw tips. → are the tips above, level with, or below the cube's top?
- **3.3** Prompt: `Move to z 0.5.` Try to slide your phone, lying flat, under the jaw tips. → does the phone fit under? (yes / no) Do the tips touch the table? (yes / no)
- **3.4** Only if the tips did **not** touch the table in 3.3. Prompt: `Move to z -0.5.` → do the tips touch the table? (yes / no; or "skipped")
- **3.5** Lay the paper flat with one short edge touching the middle of the arm's base, the paper pointing straight away from the arm. Put the cube at the middle of the far short edge. Take the paper away. Prompt: `There's a cube 28 cm in front of the base and 0 cm to the left, about 2.5 cm wide. Pick it up and put it down 10 cm to the left. Look with both cameras and pose_view before you close the gripper. Say one line before each move.` → was the cube picked up? (yes / no)
- **3.6** Same run. → was it put down about 10 cm to the left? (yes / no)
- **3.7** Same run, only if 3.5 was no. → where did the gripper close: in front of, behind, left of, right of or above the cube, and by about how many cube-widths?
- **3.8** Same run. → did it say one line before each move? (yes / no)

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

## 8. Green arms in lab-os (40 min)
Setup: green follower, green leader and both training cameras plugged in as for training. `so101-white` unplugged. LeLab closed.
- **8.1** Run `cat logs/green-last-start.json`. → the `follower` value. **If it is `5B41531599`, stop part 8 here.**
- **8.2** Run `ls -l ~/.cache/huggingface/lerobot/calibration/robots/*/`. → the `.json` file names.
- **8.3** Run `sha256sum ~/.cache/huggingface/lerobot/calibration/robots/*/*.json > /tmp/green-cal-before.txt`. → nothing to report.
- **8.4** Double-click the icon "SO-101 Training (LeLab)". On LeLab's page press teleop. Leave it running. Then run `uv run --extra so101 python -m lab_os.robots.so101 so101-green`. → copy the line it printed.
- **8.5** Stop LeLab's teleop. Ctrl+C in LeLab's terminal. → nothing to report.
- **8.6** Run `uv run --extra so101 python -m lab_os.robots.so101_setup check --arm so101-green`. → copy the line it printed.
- **8.7** Run `uv run --extra so101 python -m lab_os.robots.so101_setup calibrate --arm so101-green-leader`. → copy the line it printed.
- **8.8** Run `uv run --extra so101 python -m lab_os.robots.so101 so101-green --watch`. Move each joint of the follower by hand. Then Ctrl+C. → did the numbers follow every joint? (yes / no; name the joints that didn't; copy any error)
- **8.9** Run `uv run --extra so101 lab-os serve --arm so101-green --speed 0.3`. Open http://localhost:8080/teleop → Desktop control. → does the 3D arm match the real arm's pose? (yes / no)
- **8.10** Jog one joint a little. Press STOP. → did the real arm move and then stop? (yes / no)
- **8.11** In Claude Code (`/mcp` → `lab-os` → reconnect), prompt: `Use the lab-os tools. Read so101-green's status, then go to the home pose.` → did it reach the home pose without hitting anything? (yes / no)
- **8.12** With the brain still running, double-click the "SO-101 Training (LeLab)" icon. → did LeLab start? (yes / no) Copy the line that mentions the green arm. Then press Enter to close that window.
- **8.13** Hold the arm. Ctrl+C in the brain's terminal. Run `sha256sum -c /tmp/green-cal-before.txt`. → does every line say `OK`? (yes / no)
- **8.14** Start LeLab with the icon, press teleop, move the leader. Close LeLab. → did the follower follow? (yes / no)
- **8.15** Run `ls -l /dev/v4l/by-path/`. Unplug the wrist camera's cable. Run it again. Plug the cable back in. → which disappeared: `usb-0:7` or `usb-0:8`?

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

## 7. Teleop 1:1 on the real arm (20 min)
Setup: `so101-white` plugged in, green arms unplugged, the Quest on USB. Lay a sheet of letter paper on the table beside the arm, long edge pointing away from the arm.
```bash
uv run --extra so101 lab-os serve --arm so101-white --speed 0.2 --record recordings/quest-1to1-real-$(date +%F).jsonl
adb reverse tcp:8080 tcp:8080
```
In the Quest's browser: `http://localhost:8080/teleop` → **Hand → arm → 1:1** → **Enter AR**.
- **7.1** Hold the left Grip. Move the see-through arm onto the real arm. Let go. → does it sit on the real arm? (yes / no)
- **7.2** Put the right controller in the ball at the gripper. Hold the right Grip. Move your hand forward by the paper's long edge (28 cm), from the near edge to the far edge. → did the real gripper travel the same edge, less, or more? (same / short by about ___ card-lengths / long by ___)
- **7.3** Move your hand left by the paper's short edge (22 cm). → same, less or more? Did the gripper also drift forward or back? (no / forward / back)
- **7.4** Wave your hand slowly side to side. → did the arm keep up? (yes / late by about ___ s)
- **7.5** After about 5 minutes of 1:1, in a second terminal: `tail -n 1 logs/servo-health/*so101-white.jsonl`. → the highest `temp_c` in the line.
- **7.6** Switch to relative on the page and drive for a minute. → which is easier to steer? (1:1 / relative / same)
- **7.7** Still in relative, push the right thumbstick up until the speed stops rising. Grab, move your hand forward by the paper's long edge, at a normal pace. → did the gripper travel the same edge? (same / short / long) Did it keep up? (yes / late by about ___ s) Did it shake or jerk? (no / a little / a lot)

## 10. The hub in VR (20 min)
Setup: the Quest on USB. No arm.
```bash
uv run lab-os serve
adb reverse tcp:8080 tcp:8080
```
In the Quest's browser: open `http://localhost:8080/design?device=quest-a` once (the name of the Quest in your hands: its serial in `config/devices.yaml`), then `http://localhost:8080/xr`. Allow the microphone. **Enter VR**.
- **10.1** Pull the trigger to start; let the startup play (don't skip it). After the jump, look around. → is there a tight cluster of linked dots far away? (yes / no) If yes: where (straight ahead / left / right / behind / up / down), does it stay or slowly drift into place, about how many dots? Then ⏻ (top right), start again and **skip** the startup with a second pull. → cluster then? (yes / no)
- **10.2** Point at a callout and pull the trigger. Press **B**. → did the page open and close? (yes / no)
- **10.3** Point at "Ask anything", hold the trigger, ask three long questions in a row. → does the newest chat text stay visible? (yes / no)
- **10.4** Say "Hey Jarvis" 10 times, with a pause between. → number of times nothing happened. For each miss, copy the newest line in the desktop's terminal.
- **10.5** Point at Teleop (left of the core), pull the trigger. Grip and move. → did the fake arm follow? (yes / no)
- **10.6** Press **B**. → are you back in the hub? (yes / no)
- **10.7** Say "Hey Jarvis, open teleop." → did Teleop open? (yes / no)
- **10.8** Say "Hey Jarvis, back to the hub." → did it go back? (yes / no)

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
