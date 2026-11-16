# Lab checklist

Do the parts in this order: **0, 3, 8, 11, 7, 9, 10, 2, 6, 5, 1**. Each part works alone. Run every command in a terminal on the lab desktop, in `~/lab-os`. Send the "Report" answers to the planning session.

Rules:
- A real arm moves without asking. Keep one hand at **STOP** (any lab-os page) while an arm is powered.
- Ctrl+C in the brain's terminal makes the arm go limp. Hold the arm first if it is lifted.
- Green arms: never change motor IDs or firmware, never recalibrate, never touch the `lerobot` conda env, never start lab-os on them while LeLab is running.
- The free voice key speaks about 15–20 answers a day. Silent answers with "sending too much voice" = used up until midnight Pacific.

The longer version with explanations: `docs/archive/lab-checklist-long-2026-11-16.md`.

## 0. Update
```bash
cd ~/lab-os
git switch main && git pull
uv sync --extra so101
uv run pytest -q
```
Report:
- The last line of `pytest` (copy it).

## 3. AI drives so101-white
Setup: `so101-white` plugged in, green arms unplugged, a ruler, a cube.
```bash
ls -l /dev/serial/by-id/
uv run --extra so101 lab-os serve --arm so101-white --speed 0.3 --host 0.0.0.0
```
In a **new** Claude Code session in `~/lab-os`: type `/mcp`, pick `lab-os`, reconnect. Then give these prompts one at a time:
1. `Use the lab-os tools. Read the arm's status, then go to the home pose.`
2. `Move to x 20, y 0, z 2, pointing straight down.` Measure the jaw tips' height above the table with the ruler.
3. `Move to z 0.5.` Measure again. If the tips touch the table, press STOP and skip step 4.
4. Only if the tips were clearly above the table in step 3: `Move to z -0.5.` Measure again.
5. Put the cube on the table. Measure its middle: cm in front of the middle of the arm's base, cm to the left. Then: `There's a cube X cm in front of the base and Y cm to the left, about 3 cm wide. Pick it up and put it down 10 cm to the left. Look with both cameras and pose_view before you close the gripper. Say one line before each move.`

Report:
- Step 1: did Claude Code ask for permission before moving? (yes / no)
- Steps 2–4: the measured tip height in cm at z 2, z 0.5 and z −0.5.
- Step 5: was the cube picked up? (yes / no) Was it put down? (yes / no) If no: where did the gripper close relative to the cube (cm, and which direction)?
- Step 5: did it say one line before each move? (yes / no)

## 8. Green arms in lab-os
Setup: green follower, green leader and both training cameras plugged in as for training. `so101-white` unplugged. LeLab closed.

**a. Which arm is the follower**
```bash
cat logs/green-last-start.json
ls -l /dev/serial/by-id/
```
If the file says the follower is `5B41531599`: **stop part 8** and report it.

**b. Calibration files**
```bash
ls -l ~/.cache/huggingface/lerobot/calibration/robots/*/
sha256sum ~/.cache/huggingface/lerobot/calibration/robots/*/*.json > /tmp/green-cal-before.txt
```

**c. lab-os refuses while LeLab runs**
1. Double-click the desktop icon "SO-101 Training (LeLab)". On LeLab's page, press teleop. Leave it running.
2. Run:
```bash
uv run --extra so101 python -m lab_os.robots.so101 so101-green
```
3. Stop LeLab's teleop. Press Ctrl+C in LeLab's terminal.

**d. The setup tool refuses the greens**
```bash
uv run --extra so101 python -m lab_os.robots.so101_setup check --arm so101-green
uv run --extra so101 python -m lab_os.robots.so101_setup calibrate --arm so101-green-leader
```

**e. Read only** (LeLab closed)
```bash
uv run --extra so101 python -m lab_os.robots.so101 so101-green --watch
```
Move each joint of the follower by hand. Then Ctrl+C.

**f. Moving**
```bash
uv run --extra so101 lab-os serve --arm so101-green --speed 0.3
```
1. Open http://localhost:8080/teleop. Choose Desktop control. Jog one joint a little. Press STOP.
2. In Claude Code (`/mcp` → `lab-os` → reconnect): `Use the lab-os tools. Read so101-green's status, then go to the home pose.`
3. With the brain still running, double-click the "SO-101 Training (LeLab)" icon. Press Enter to close its window.
4. Hold the arm. Ctrl+C in the brain's terminal.

**g. Calibration untouched**
```bash
sha256sum -c /tmp/green-cal-before.txt
```
Then start LeLab with the icon, press teleop, move the leader. Close LeLab.

**h. Which camera is which**
```bash
ls -l /dev/v4l/by-path/
```
Unplug the wrist camera's cable. Run the command again. Plug it back in.

Report:
- a: the `follower` value in the file.
- b: how many `.json` files, and their names.
- c: the line the command printed (copy it).
- d: the line each command printed (copy both).
- e: did the numbers follow each joint? (yes / no per joint) Any error message (copy it).
- f1: did the 3D arm match the real arm? (yes / no) Did STOP stop it? (yes / no)
- f2: did the arm reach the home pose without hitting anything? (yes / no)
- f3: did LeLab start? (yes / no) The line it printed (copy it).
- g: does every line say `OK`? (yes / no) Does the follower still follow the leader in LeLab? (yes / no)
- h: which socket (`usb-0:7` or `usb-0:8`) disappeared when the wrist camera was unplugged.

## 11. Devices
Setup: the desktop and the Newline (or a laptop in place of the Newline). No arm needed.

**a. The icon**
```bash
uv run lab-os icon --device desk
```
1. Stop any running brain (Ctrl+C).
2. Ubuntu's app list → click **Start lab-os**.
3. Click **Start lab-os** a second time.

**b. The Newline**
1. On the desktop: `hostname -I`. Use the first address.
2. On the Newline's Chrome, open `http://<address>:8080/?device=newline`.
3. On the Newline: ⚙ → This device → Drawing resolution → 0.5.
4. On the desktop: `cat ~/lab-os/config/hub-devices.yaml`
5. On the Newline: Chrome menu → Add to Home screen. Close Chrome. Tap the new icon.

**c. Open on…**
1. On the Newline: open Monitor → **Open on…** → **desk**.
2. On the desk: press **Back**.
3. On the Newline: Monitor → Open on… → desk again. Then on the Newline press **Bring it back**.
4. On the desk: open Teleop → Open on… → **newline**.

**d. Restart**
1. With Monitor sent to the desk: Ctrl+C in the brain's terminal. Wait 10 seconds. Click **Start lab-os**.
2. Shut down the desktop and switch the Newline off. Switch both on. Click **Start lab-os**, then tap the Newline's icon.

Report:
- a2: did a terminal and a full-screen hub open? (yes / no) Does the address contain `?device=desk`? (yes / no)
- a3: did a second brain start? (yes / no)
- b2: did the page load? (yes / no)
- b4: does the file show `newline:` with `res: '0.5'`? (yes / no)
- b5: does ⚙ say "This device: newline" after opening from the icon? (yes / no)
- c1: did Monitor open on the desk? (yes / no) Did the Newline show "Monitor is on desk"? (yes / no)
- c2: did Monitor close on the desk and the line disappear on the Newline? (yes / no)
- c3: did Monitor come back to the Newline? (yes / no)
- c4: did Teleop open on the Newline? (yes / no)
- d1: did both hubs come back without reloading? (yes / no) How many seconds?
- d2: did both come back under their names with the Newline's resolution still 0.5? (yes / no)

## 7. Teleop 1:1 on the real arm
Setup: `so101-white` plugged in, green arms unplugged, the Quest on USB, a ruler taped to the table pointing away from the arm.
```bash
uv run --extra so101 lab-os serve --arm so101-white --speed 0.2 --record recordings/quest-1to1-real-$(date +%F).jsonl
adb reverse tcp:8080 tcp:8080
```
In the Quest's browser: `http://localhost:8080/teleop` → **Hand → arm → 1:1** → **Enter AR**.
1. Hold the left Grip. Move the see-through arm onto the real arm. Let go.
2. Put the right controller in the ball at the gripper. Hold the right Grip.
3. Move your hand 10 cm forward along the ruler. Read how far the real gripper moved.
4. Move your hand 10 cm to the left. Read how far the real gripper moved.
5. Wave your hand slowly side to side.
6. Run this in a second terminal after 5 minutes of 1:1: `tail -n 1 logs/servo-health/*so101-white.jsonl`

Report:
- Step 3: gripper travel in cm for 10 cm of hand, forward.
- Step 4: gripper travel in cm for 10 cm of hand, left. Did it also move forward or back? (cm)
- Step 5: did the arm keep up with the wave? (yes / late by about ___ s)
- Step 6: the highest `temp_c` in the line.
- Is it easier to steer than relative mode? (yes / no / same)

## 9. Voice
Setup: USB microphone plugged in and selected in Ubuntu Settings → Sound → Input. Speakers on.
```bash
uv run lab-os serve --persona jarvis
```
Open http://localhost:8080/design in Chrome. Press start. Keep the terminal visible.
1. Listen to the greeting. Press ⏻, wait 10 seconds, press start again.
2. Hold the mic button, say "What's the next step?", let go. Time from letting go to the first spoken word.
3. ⚙ → This device → Talking to it → **wake word** → Back.
4. From the desk, say "Hey Jarvis, what's the next step" in one breath. Do it three times. After each, copy the `voice timing` line from the terminal.
5. Walk back until "Hey Jarvis" stops working. Measure the distance.
6. From that spot: ⚙ → This device → Wake word sensitivity → 7. Try again. Then 8.
7. Talk normally near the microphone for one minute. Say "Jarvis" inside a sentence once.
8. "Hey Jarvis, pull up the teleop page." Then "Hey Jarvis, show me the AI spend." Then "Hey Jarvis, go back to the hub."
9. Type in the ask line: `show me the commits`.

Report:
- Step 1: was the greeting spoken both times? (yes / no) Did the second one start at once? (yes / no)
- Step 2: seconds to the first spoken word.
- Step 4: the three `voice timing` lines. Was the start of the question cut off? (yes / no)
- Step 5: the distance in meters at sensitivity 5.
- Step 6: the lowest sensitivity that works from that spot.
- Step 7: number of false wakes.
- Step 8: did each page open? (yes / no for each of the three)
- Step 9: did the Commits page open? (yes / no)

## 10. The hub in VR
Setup: the Quest on USB. No arm needed.
```bash
uv run lab-os serve
adb reverse tcp:8080 tcp:8080
```
In the Quest's browser: open `http://localhost:8080/design?device=quest` once, then `http://localhost:8080/xr`. Allow the microphone. **Enter VR**.
1. Pull the trigger to start. Watch the jump.
2. Look around for a tight cluster of linked dots far away.
3. Point at a callout and pull the trigger. Press **B**.
4. Point at "Ask anything", hold the trigger, ask three long questions in a row.
5. Say "Hey Jarvis" 10 times, with a pause between. Count the times nothing happens. For each miss, copy the newest line in the desktop's terminal.
6. Point at Teleop (left of the core), pull the trigger. Grip and move. Press **B**.
7. Say "Hey Jarvis, open teleop." Then "Hey Jarvis, back to the hub."

Report:
- Step 2: is the cluster there? (yes / no)
- Step 3: did the page open and close? (yes / no)
- Step 4: does the newest chat text stay visible? (yes / no)
- Step 5: misses out of 10, and the terminal line for each miss.
- Step 6: did the fake arm follow? (yes / no) Did B return to the hub? (yes / no)
- Step 7: did both commands work? (yes / no each)

## 2. The Newline
**a. Its own Chrome** (Ethernet cable from the desktop, brain started with `uv run lab-os serve --host 0.0.0.0`)
1. On the Newline's Chrome: `chrome://flags` → search "Insecure origins treated as secure" → enter `http://<desktop address>:8080` → Enabled → Relaunch.
2. Open `http://<desktop address>:8080/design?device=newline`. Press start.
3. ⚙ → This device → Drawing resolution → 1. Press ⏻, press start. Then the same with 0.5.

**b. HDMI from the desktop**
1. Plug the desktop into the Newline's HDMI. Ubuntu Settings → Displays → the Newline → 1920×1080. Read the refresh rate shown.
2. In the Newline's own picture menu, look for a "PC" or "Game" mode and switch it on.
3. Open http://localhost:8080/design on the Newline's screen. Press start.

Report:
- a2: is there a mic button next to "Ask anything"? (yes / no) Does hold-to-talk work? (yes / no)
- a3: is the startup smooth at 1? At 0.5? (yes / no each)
- b1: the refresh rate in Hz at 1920×1080.
- b2: the name of the mode you switched on, or "none found".
- b3: is the startup smooth at 1920×1080? (yes / no)

## 6. Quick checks (fake arm)
```bash
uv run lab-os serve
```
1. http://localhost:8080/teleop → Desktop control → hold two jog keys at once, then one, then two others.
2. http://localhost:8080/settings → The assistant → Monthly AI budget → 0. Ask the hub a question. Set it back to 20. Ask again.
3. http://localhost:8080/settings → Safety limits in this venue → switch **Floor** off. Ctrl+C. Start the brain again. Read the terminal. Switch Floor back on. Then: `git checkout config/venues/lab.yaml`
4. raspbot1, reached by cable: set your phone's hotspot security to **WPA2-Personal**, then on the Raspbot: `sudo nmcli dev wifi connect "<hotspot name>" password "<password>"`. Afterwards: `sudo nmcli con up Raspbot`

Report:
- Step 1: did the 3D model change size? (yes / no) Do all six joint rows stay in place? (yes / no)
- Step 2: at 0, did it say the budget is used up? (yes / no) At 20, did it answer? (yes / no)
- Step 3: did the terminal print `LIMITS OFF in venue lab: floor`? (yes / no)
- Step 4: did the Raspbot join? (yes / no) If no, the error line (copy it).

## 5. Training launcher
Setup: `so101-white` unplugged, both green arms plugged in.
1. Double-click the desktop icon "SO-101 Training (LeLab)".
2. On LeLab's page (http://127.0.0.1:8000) press teleop. Move the leader.

Report:
- Step 1: did every check line pass? (yes / no) If no, the failing line (copy it).
- Step 2: did the follower follow the leader? (yes / no)

## 1. The hub on the desktop
```bash
uv run lab-os serve --host 0.0.0.0
```
Open http://localhost:8080/design. Press start.
1. Open and close Teleop, Monitor and AI Control.
2. Press Esc. Press the ⛶ button in the strip.

Report:
- Step 1: did all three open and close? (yes / no)
- Step 2: did ⛶ bring full screen back? (yes / no)
- Anything that stuttered or looked wrong (one line each).
