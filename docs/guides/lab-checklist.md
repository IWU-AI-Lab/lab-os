# Lab checklist

Every step has a tag (for example **11.4**). The line after **→** says what to report. Report as `11.4: yes` or `T.10: right arm`. Run the commands in a terminal on the lab desktop, in `~/lab-os`. Each part works alone.

This list has only what is still to do. When a step is done, it is removed (its result goes to `docs/dev/GOTCHAS.md` or `docs/plan/quick-jobs.md`).

**Order for the next lab days.** Friday 2026-11-20, if you go: 0, then 11. Tuesday 2026-11-24: 0, then T, then the parts that the sessions add for the other previews and the new quick jobs.

Rules:
- A real arm moves without asking. Keep one hand at **STOP** (on any lab-os page) while an arm has power.
- Ctrl+C in the brain's terminal makes an SO-101 go limp. If the arm is lifted, hold it first.
- The green arms have their own rules (`AGENTS.md` → "Hard rules"). Never start lab-os on them while LeLab runs.
- The voice is OpenAI's (the professor's key, in `.env`). After you change `.env`, restart the brain. Without that key, the free Gemini key speaks (about 15 to 20 answers a day).

You need no ruler. Measure with these:
- a sheet of letter paper (short edge 21.6 cm, long edge 27.9 cm);
- a bank card (8.6 cm long, 5.4 cm wide);
- the cube (3 cm);
- your phone, flat on the table (about 1 cm thick).

## How to write a step (for the sessions that add steps)
- Ask at most 3 questions in one step. Split a longer step into two steps.
- Put a step after the steps that it needs. (For example, the "Start lab-os" icon exists only after step 11.1.)
- Fit the step to the real room:
  - The lab desktop faces the wall. Its back ports face the room, for the robots. The USB microphone is in its front port, about 60 cm from the chair.
  - A dividing wall stands between the desk and the door. Do not ask for tests from the doorway.
  - A loud fan on the roof makes noise above the desk at times.
  - The Newline is used by HDMI at 1600×900, with its USB touch cable.
  - Ask for what a person can tell: heard or not, a normal or a raised voice, near or far. Do not ask for counts that are not exact, such as steps walked.

---

## 0. Update (5 min)
```bash
cd ~/lab-os
git switch main && git pull
uv sync --extra so101
uv run pytest -q
```
- **0.1** Read the last line that `pytest` shows. → copy the line.

## 11. Devices (25 min)
Setup: the desktop, and the Newline's own Chrome (or a laptop instead of the Newline). Connect the Newline to the desktop with the Ethernet cable. No arm. Step 11.1 (the icon) is done.
- **11.3** In Ubuntu's app list, click **Start lab-os**. Wait until the hub opens. Click **Start lab-os** again. → how many brain terminals are open now? (1 / 2) Copy the last line of the newest terminal.
- **11.4** On the desktop, run `hostname -I` and use the first address. In the Newline's Chrome, open `http://<address>:8080/?device=newline`. → did the page load? (yes / no)
- **11.6** On the Newline, select Chrome's menu → Add to Home screen. Close Chrome. Tap the new icon. Open ⚙. → does it say "This Device: newline"? (yes / no)
- **11.7** On the Newline, open Monitor → **Open on…** → **desk**. → did Monitor open on the desk? (yes / no)
- **11.8** Look at the Newline. → does it say "Monitor is on desk"? (yes / no)
- **11.9** On the desk, press **Back**. → did Monitor close on the desk? (yes / no) Did the line go away on the Newline? (yes / no)
- **11.10** On the Newline, select Monitor → Open on… → desk. Then, on the Newline, press **Bring it back**. → did Monitor come back to the Newline? (yes / no)
- **11.11** On the desk, open Teleop → Open on… → **newline**. → did Teleop open on the Newline? (yes / no)
- **11.12** Send Monitor to the desk again. Press Ctrl+C in the brain's terminal. Wait 10 seconds. Click **Start lab-os**. → did both hubs come back without a reload? (yes / no) After how many seconds?
- **11.13** Shut down the desktop and switch off the Newline. Switch both on. Click **Start lab-os**, then tap the Newline's icon. → are both back under their names? (yes / no) Is the Newline's Drawing Resolution still 0.5? (yes / no)

---

## For Tuesday 2026-11-24: the previews

## T. Two arms from the Quest (45 min)
Preview 3: the right controller drives `so101-white`, and the left controller drives `so101-green`. How it works: `docs/guides/quest-setup.md` → "Two arms at once".

Before you start:
- Stop LeLab and any training or recording run. The brain refuses the green arm while another program has its port open.
- Do not move the green arm's stand or its cameras (the training setup). If the two arms face different directions, leave them so, and write it in T.5.

Cables to plug in, on the lab desktop:
- `so101-white` (the follower): its USB cable and its power supply.
- `so101-green` (the follower): its USB cable and its power supply.
- The Quest: its USB-C data cable.
- The arms need no cameras for this part. If no USB socket is free, unplug the two cameras in sockets 7 and 8.
- The green leader arm can stay plugged in. lab-os does not open it.

Then run:
```bash
ls /dev/serial/by-id/
uv run --extra so101 lab-os serve --arm so101-white --left-arm so101-green --speed 0.3
```
In a second terminal, run `adb reverse tcp:8080 tcp:8080`.

- **T.1** Read the `ls` output. → does it show both `…5B41532410-if00` (white) and `…5B41533501-if00` (green)? (yes / no)
- **T.2** Read the brain's terminal. → does it say `two arms: the right controller drives so101-white, the left one so101-green`? (yes / no; if no, copy the last line)
- **T.3** On the desktop, open http://localhost:8080/teleop. → does it show **Right arm** and **Left arm**, both "holding"? Does the 3D view show two arms, with the joints of each in the column next to it? (yes / no each) Keep this page open, with the mouse near **STOP**, for all steps.
- **T.4** On the desktop, open http://localhost:8080/monitor in a second window, next to the teleop page. → does it show two arms in the 3D view, and a joints card for each arm? (yes / no) Keep it in view during T.8 to T.11. → do both 3D arms move with the real arms? (yes / no)
- **T.5** In the Quest's browser, open `http://localhost:8080/teleop` and select **Enter AR**. Look at the status panel. → does it show two labels, "Left holding" on the left and "Right holding" on the right? (yes / no) Do you see two see-through arms? (yes / no) Do the real arms face the same direction? (yes / no; if no, which way does each face?)
- **T.6** Hold **Y**, then hold the right grip. Move and turn the right 3D arm onto `so101-white`, then release the grip. Do the same with the left grip for the left 3D arm and `so101-green`. Release Y. → did the real arms stay still the whole time? (yes / no) Did the panel say "Y held: a grip moves its 3D arm"? (yes / no) Is each 3D arm on its real arm? (yes / no)
- **T.7** Tap Y once, quickly. → did both 3D arms go back? (yes / no) Put them on the real arms again, as in T.6.
- **T.8** Hold the right grip. Move the right controller slowly 10 cm to the right, then back. → did only `so101-white` move, to the right and back? (yes / no)
- **T.9** Hold the left grip. Move the left controller slowly 10 cm to the left, then back. → did only `so101-green` move, to the left and back? (yes / no)
- **T.10** Hold both grips. Move both hands slowly forward 10 cm, then up 10 cm. → did both arms move the same way as your hands? (yes / no) Was one arm slower or shakier than the other? (which one?)
- **T.11** Hold both grips. Pull the right trigger, then the left trigger. → did each trigger close only its own arm's gripper? (yes / no)
- **T.12** Release both grips. On the desktop's teleop page, set **Hand → arm** to **1:1**. → does the headset show a green ball at each 3D gripper? (yes / no) Put your left hand in the left ball and hold the left grip. Move the hand slowly 5 cm up, then 5 cm forward. → does `so101-green`'s gripper stay with your hand? (yes / no; about how many cm off?)
- **T.13** Do the same with the right hand and `so101-white`. → does its gripper stay with your hand? (yes / no; about how many cm off?) Then use both hands at once. → does it work? (yes / no) Set **Hand → arm** back to **Relative**.
- **T.14** Hold both grips and move. Press **X** (left controller). → did both arms stop? Does the panel say "Left frozen: let go" and "Right frozen: let go"? (yes / no each) Release both grips and hold them again. → do both arms move again? (yes / no)
- **T.15** Hold both grips and move. Press **STOP** on the desktop page. → did both arms stop? (yes / no)
- **T.16** Put the cube in front of `so101-white`. Pick it up with the right arm, then give it to the left arm. → did it work? (yes / no; how many tries? What was difficult?)
- **T.17** Hold both arms. Press Ctrl+C in the brain's terminal. → did both arms go limp? (yes / no)
- **T.18** Run `ls -l --time-style=full-iso ~/.cache/huggingface/lerobot/calibration/robots/so_follower/sheep.json`. → is the date before today? (yes / no; it must be: lab-os only reads this file)

## Optional: raspbot1 on a phone hotspot (10 min)
Setup: connect to the Raspbot with a cable. Set the phone hotspot's security to **WPA2-Personal**.
- **R.1** On the Raspbot, run `sudo nmcli dev wifi connect "<hotspot name>" password "<password>"`. → did it connect? (yes / no; if no, copy the error line)
- **R.2** Run `sudo nmcli con up Raspbot`. → nothing to report.
