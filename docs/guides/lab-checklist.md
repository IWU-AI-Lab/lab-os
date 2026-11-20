# Lab checklist

Every step has a tag (for example **11.4**). The line after **→** says what to report. Report as `11.4: yes` or `T.10: right arm`. Run the commands in a terminal on the lab desktop, in `~/lab-os`. Each part works alone.

This list has only what is still to do. When a step is done, it is removed (its result goes to `docs/dev/GOTCHAS.md` or `docs/plan/quick-jobs.md`).

**Order for the next lab days.** Friday 2026-11-20 (about 1 hour, no sound): 0, A, S, 11, then W if time is left (hub sounds off: the speakers off, or the volume at 0). Tuesday 2026-11-24: 0, then N and M (if the router is here), then V, then T and D, then W, G and H, then 11 if it is not done, then the parts that the sessions add for the new quick jobs.

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

## A. The brain finds the arm (10 min)
Setup: `so101-white` with its power supply and USB cable. No brain runs. The "Start lab-os" icon is the one that you have now: it needs no change.
- **A.1** (quick job 61) Click **Start lab-os**. → does the brain's terminal say "Plugged in: so101-white. Driving so101-white"? (yes / no: copy the line) Does the hub show so101-white, not the fake arm? (yes / no)
- **A.2** (quick job 61) Hold the arm. Press Ctrl+C in the brain's terminal. Disconnect the arm's USB cable. Click **Start lab-os**. → does the terminal say "No arm plugged in: the fake arm"? (yes / no) Press Ctrl+C. Connect the USB cable again.

## S. Safety fixes on the real arm (25 min)
Setup: `so101-white` with its power supply and USB cable. Claude Code on the desktop, connected to the brain's robot tools (`docs/guides/ai-control.md`). Keep one hand at STOP.
- **S.1** (quick job 44) Click **Start lab-os**. On the desktop's hub, press ⏻ → **Shut down lab-os**. → does the first line say that so101-white goes limp? (yes / no) Does the **Shut down** button say it too? (yes / no) Press **Cancel**.
- **S.2** (quick job 44) Connect the Quest with USB. Run `adb reverse tcp:8080 tcp:8080`. In the Quest's browser, open `http://localhost:8080/xr` and press **Enter AR (your room)**. Pull the trigger until the hub is around you. Put the headset on the table. → did the hub open in AR? (yes / no)
- **S.3** (quick job 44) In Claude Code, prompt: `Go to the home pose.` Wait until the arm is at home. Hold the arm. Prompt: `Go to the ready pose.` While the arm moves, press ⏻ → **Shut down lab-os** → **Shut down**. → did the arm stop at once and make no more moves? (yes / no) Did it go limp in your hand within about 2 seconds? (yes / no) Did the terminal close within about 2 seconds, after `lab-os was shut down from the hub; so101-white was let go.`? (yes / no)
- **S.4** (quick job 44) Look at the desktop's pages. Put on the Quest. → did every page on the desktop say "lab-os is off"? (yes / no) Did the Quest show a "lab-os is off" card in front of you? (yes / no)
- **S.5** (quick job 44) Click **Start lab-os**. → did the desktop's pages come back by themselves? (yes / no)

## V. The wake word and the greeting (20 min)
Quick job 42. The cause of the stops was not found on the Mac. The brain's terminal now says when it ignores "hey Jarvis", and why. Setup: the desktop's hub with ⚙ → This Device → Talking to It → **Wake Word**, the USB microphone in its front port, and no roof fan if possible. Keep the brain's terminal in view.
- **V.1** Press ⏻ → **Back to the start screen**. Tap to start. → did the greeting start at once, before the jump ended? (yes / no)
- **V.2** Say "Hey Jarvis, what time is it?". Wait for the answer. Say it again. → did it answer both times? (yes / no)
- **V.3** Open ⚙. Move **Wake Word Sensitivity** from 5 to 7. Close ⚙. Say "Hey Jarvis, what's next?". → did it answer? (yes / no) If no, copy the terminal's last lines that start with `voice:`.
- **V.4** Open the hub on the Newline too (Open on…), with its sound on. Ask the desktop a question by voice. When the answer ends, say "Hey Jarvis" again. → did the desktop answer at once? (yes / no) If no, copy the `ignored:` line from the terminal.
- **V.5** Each time during the day that the wake word does not answer: copy the terminal's `voice:` lines from that minute into the report. → how many times did it stop today? (a number)

---

## N. The travel router (45 min)
The GL.iNet Beryl 7 (`docs/plan/current-focus.md` → "Waiting on others"). The professor approved the router and its use of the wall Ethernet port (2026-11-20). The router gets its internet from the wall port from the start. For now, the brain desktop keeps its own internet on the campus Wi-Fi, and reaches the router's devices by a cable. This is a temporary safeguard until the wall port's internet is proven; then everything goes on the router. Background: `docs/guides/network-setup-checklist.md`. To undo all of it: switch the router off and remove the desktop's cable.
- **N.1** Read the label under the router. → write the router's admin address (for example `192.168.8.1`) and its Wi-Fi names. Do not write the Wi-Fi password in the report.
- **N.2** Connect the wall Ethernet port to the router's **WAN** port. Connect the router's power adapter (from the box) to a wall socket. Wait 2 minutes. → is its light on and steady? (yes / no)
- **N.3** Connect an Ethernet cable from the lab desktop's Ethernet port to the router's **LAN** port (not WAN). In Ubuntu Settings → Network → the wired connection → ⚙ → IPv4, select **Use this connection only for resources on its network**, then Apply. Turn the wired connection off and on. → does a web page still open on the desktop? (yes / no) Copy the first line that `ip -4 addr | grep 192.168.8` shows.
- **N.4** On the desktop, open the admin address from N.1. Set an admin password, and keep it in your password manager, not in the repo. → did the router's page open? (yes / no)
- **N.5** In the router's page, open the Wi-Fi settings. Give both bands one name of your choice, a new password, and the security **WPA2-PSK** or **WPA2/WPA3**, not WPA3 alone (older Pis and the Raspbot need WPA2). Save. → which security options did it offer? (copy them)
- **N.6** In the router's page, find the list of clients. Reserve the lab desktop's address, so that it does not change. → the desktop's reserved address: ___ (it starts with 192.168.8)
- **N.7** On the desktop, run `uv run lab-os serve --host 0.0.0.0`. On your phone, join the router's Wi-Fi. Open `http://<the reserved address>:8080/design?device=phone`. → did the hub load? (yes / no)
- **N.8** On the Quest, join the router's Wi-Fi. Without the USB cable, open `http://<the reserved address>:8080/design?device=quest-a` in its browser. → did the hub load? (yes / no) Open `chrome://flags` in the Quest's browser. → does a flags page open? (yes / no)
- **N.9** On a Pi with a screen, run `sudo nmcli dev wifi connect "<the router's Wi-Fi name>" password "<password>"`. → did it join? (yes / no; if no, copy the error) Run `ping -c 3 <the reserved address>`. → replies? (yes / no)
- **N.10** On the Newline, open its Wi-Fi settings and join the router. In its Chrome, open `http://<the reserved address>:8080/?device=newline`. → did it join? (yes / no) Did the hub load? (yes / no)
- **N.11** Connect to raspbot1 by its cable (`docs/guides/network-setup-checklist.md` → Step 2). Run `sudo nmcli dev wifi connect "<the router's Wi-Fi name>" password "<password>"`. → did it join? (yes / no; if no, copy the error line)
- **N.12** On your phone, on the router's Wi-Fi, open a web page. → does it open? (yes / no) If no: in the router's page → Internet, copy what it says about the WAN port. Then connect your phone's hotspot (security WPA2) in the router's page → Internet → Repeater. → does a web page open now? (yes / no)
- **N.13** On your phone, on the router's Wi-Fi, open fast.com. → the speed in Mbps.

## M. Every screen in the room (30 min)
After part N, or on the campus network for the computers that are already on it (the desktops and the Pis). The plan for the demo: `docs/plan/current-focus.md` → item 10. Use the brain's address on the same network as the device: `192.168.8…` on the router, or the campus address that `hostname -I` shows first.
- **M.1** On each computer that can show a screen (the 2 Windows desktops, the other Ubuntu desktop, each Pi with a screen, the Newline), open Chrome at `http://<the brain's address>:8080/design?device=<a short name>`. Use names like `win-1`, `win-2`, `ubuntu-2`, `pi-1`, `newline`. → for each: the name, and did the hub load? (yes / no)
- **M.2** On each computer with a USB microphone (the 2 Windows desktops) and on the Newline: open `chrome://flags`, search for "Insecure origins treated as secure", type `http://<the brain's address>:8080`, select Enabled, then Relaunch. → for each: is there a mic button next to "Ask anything"? (yes / no)
- **M.3** On the desktop's hub, open the Devices panel. → how many devices does it list? (a number) Are all names from M.1 there? (yes / no: which are missing?)

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

## D. STOP from another device (10 min)
Setup: `so101-white` connected, the brain running (part T's command without `--left-arm`). A second device (a phone or a laptop) on the brain's network, or the Quest's browser.
- **D.1** On the second device, open `http://<address>:8080/monitor`. → does Monitor show the arm and a STOP button? (yes / no)
- **D.2** On the desktop's hub, say `Hey Jarvis, it's demo time`, then tap **Ask me to wave**. During the wave, press STOP on the second device. → did the arm stop at once? (yes / no)
- **D.3** Say `Hey Jarvis, the visitors have left`. → nothing to report.

## W. Teleop with a webcam (40 min)
Preview 2: your bare hand in front of the Logitech C615 drives the arm. How it works: `docs/guides/webcam-teleop.md`. Do W.1 to W.9 with no arm (the fake arm), then W.10 to W.15 with `so101-white`.

Cables to plug in, on the lab desktop:
- The C615: a free USB socket. If no socket is free, unplug the two cameras in sockets 7 and 8. This part does not use them.
- Put the C615 on top of the desktop's monitor, facing the chair.

Then run:
```bash
uv run lab-os serve
```

- **W.1** Run `ls /dev/v4l/by-path/`. Unplug the C615, run it again, and plug the C615 back in. → which name went away? (copy it)
- **W.2** On the desktop, open http://localhost:8080/webcam. Click **Start webcam control** and allow the camera. → does the picture show you, like a mirror? (yes / no) Does **Camera** show the C615? (yes / no) What does **Frames a second** show?
- **W.3** Sit in the chair. Hold up both hands, palms to the camera. → is your right hand drawn in cyan and your left hand in amber? (yes / no; if no, select **Swap left and right hands** and write it down)
- **W.4** Hold your left hand open and relaxed, not pinching. → what does **Clutch** show? (a number) Now pinch with your left hand. → what does **Clutch** show? Does the state say "Following your right hand"? (yes / no)
- **W.5** Keep the left pinch. Move your right hand slowly 20 cm to the right, then up, then down. Watch the 3D view. → did the 3D arm move to the right, up and down with your hand? (yes / no each)
- **W.6** Keep the left pinch. Move your right hand slowly 20 cm toward the camera, then back. → did the 3D arm move forward and back? (yes / no) Did it shake when your hand was still? (no / a little / a lot)
- **W.7** Release the left pinch. Hold **Space** instead and move your right hand. → does the 3D arm follow? (yes / no) Pinch and open your right hand. → does the 3D gripper close and open? (yes / no)
- **W.8** Keep Space held. Move your right hand out of the picture, then back in. → did the 3D arm stop, and the state say "Frozen"? (yes / no) Does it stay still when your hand comes back? (yes / no) Release Space and press it again. → does it follow again? (yes / no)
- **W.9** Ask another person to stand behind you in the picture. Do W.5 again. → did the page follow your hand only? (yes / no; if no, what happened?) Close the webcam page. Press Ctrl+C in the brain's terminal.

Now the real arm. Keep one hand near the keyboard: **X** is STOP on the webcam page. Plug in `so101-white` (its USB cable and its power supply), then run:
```bash
uv run --extra so101 lab-os serve --speed 0.3
```
- **W.10** Open http://localhost:8080/webcam and click **Start webcam control**. → do the chips show "Control: this page" and "Arm: holding" (or "frozen")? (yes / no)
- **W.11** Hold Space. Move your right hand slowly 10 cm to the right, then back. → did `so101-white` move to the right and back? (yes / no) About how long after your hand did it move? (at once / a short time / about 1 s or more)
- **W.12** Hold Space. Move your right hand slowly up 10 cm, then 10 cm toward the camera. → did the arm move up, then forward? (yes / no each) Did it shake? (no / a little / a lot)
- **W.13** Hold Space and move. Move your right hand out of the picture. → did the arm stop at once? (yes / no) Press **X**. → did the page's state and the Arm chip say "frozen"? (yes / no)
- **W.14** Put the cube in front of the arm. Pick it up with the webcam: Space to move, a right pinch to close the gripper. → did it work? (yes / no; how many tries? What was difficult?)
- **W.15** Was it easy to use? (easy / possible / too hard) Would you show it at the demo? (yes / no) Press Ctrl+C in the brain's terminal. Hold the arm first if it is lifted.

## G. Tic-tac-toe (45 min)
Preview 1: Claude Code plays tic-tac-toe with `so101-white` against you. How it works: `docs/guides/tic-tac-toe.md`. You need the stand camera's table map (made on 2026-11-19), the cube, and 5 red and 5 blue pieces (LEGO, about 3 cm tall).

Before the lab day, print `models/games/tic-tac-toe-sheet-letter.pdf` at 100 % ("Actual size"). Plug in `so101-white` (its USB cable and its power supply) and its stand camera (socket 8). Then run:
```bash
uv run --extra so101 lab-os serve --speed 0.3
```
- **G.1** Put the cube on the printed sheet. → is one cell as wide as two cubes? (yes / no)
- **G.2** Set up the table as in the guide, section 1 (the sheet 12 cm in front of the base, the red pieces beside the arm). In Claude Code, type the prompt in section 4 of the guide. → are the magenta squares on the printed lines? (yes / after I moved the paper / no) Are the green rings on the red pieces? (yes / after I moved them / no)
- **G.3** Type the prompt in section 5 of the guide. Put a blue piece in B2 and say "your turn". → did the arm take a red piece? (yes / no) Did it put it fully inside the cell it named? (yes / partly / no) Did the arm or a jaw touch any other piece? (no / yes: which)
- **G.4** Play to the end of the game. → did the AI read the board right each time? (yes / no: which turn) Did it say the right result? (yes / no) About how many minutes did the game take?
- **G.5** During the game, did the arm go low over the board at a time when it did not put a piece down? (no / yes: when) Clear the board. Tell the AI to go home. Press Ctrl+C in the brain's terminal. Hold the arm first if it is lifted.

## H. "Jarvis, hand me the cube" (25 min)
Preview 4: the hub's assistant moves the arm to a named pose, and hands you the blue cube. How it works: `docs/guides/hub.md` → "The assistant moves the arm". You need the blue cube and the stand camera's table map. Stand in front of the arm, across the table, with a hand near STOP on a second device (Monitor).

Plug in `so101-white` (its USB cable and its power supply) and its stand camera (socket 8). Then run:
```bash
uv run --extra so101 lab-os serve --speed 0.3 --open desk
```
- **H.1** The switch is off by default. On the hub, ask "move the arm to home" (typed). → did the arm stay still? (yes / no)
- **H.2** Select ⚙ → Robots → **The Assistant May Move the Arm**. Ask "Hey Jarvis, move the arm to ready" by voice. → did the arm go to `ready`, slowly? (yes / no) Did AI Control show the moves? (yes / no)
- **H.3** Ask "move the arm to the hand-over pose". → is the gripper held out toward you, at a height you can reach easily? (yes / too low / too high / not toward me)
- **H.4** Put the cube about 20 cm straight in front of the arm. Ask "Jarvis, hand me the cube". → did the assistant say that it found the cube? (yes / no: what did it say) Did the arm pick it up? (yes / no / it missed)
- **H.5** → did the arm hold the cube out to you at the hand-over pose? (yes / no) Was it easy to take? (yes / no) Say "let go". → did the gripper open? (yes / no)
- **H.6** Put the cube about 35 cm in front of the arm. Ask for the cube again. → did the assistant say that it can't reach it, with nothing moved? (yes / no) Move the cube to a place the camera can't see. Ask again. → did it say that it can't see the cube? (yes / no)
- **H.7** Put the cube back 20 cm in front. Ask for the cube, and press STOP on Monitor while the arm moves. → did the arm stop at once, and stay still? (yes / no) Ask "move the arm to home". Press Ctrl+C in the brain's terminal. Hold the arm first if it is lifted.

## Optional: the Kinect, without drivers (5 min)
The lab's Kinect is model 1414 (the first Kinect, for the Xbox 360). lab-os does not use it yet: it needs drivers that need `sudo` (`docs/guides/webcam-teleop.md` → "Limits of the preview"). These steps install nothing.
- **K.1** Find the Kinect's cable. → does it end in a normal USB plug, or in an orange-tipped Xbox plug? Does the lab have the Kinect's power and USB adapter? (yes / no)
- **K.2** If it has a USB plug (or the adapter), connect it and its power. Run `lsusb | grep -i 045e`. → copy the lines (none is an answer).

## Optional: raspbot1 on a phone hotspot (10 min)
Setup: connect to the Raspbot with a cable. Set the phone hotspot's security to **WPA2-Personal**.
- **R.1** On the Raspbot, run `sudo nmcli dev wifi connect "<hotspot name>" password "<password>"`. → did it connect? (yes / no; if no, copy the error line)
- **R.2** Run `sudo nmcli con up Raspbot`. → nothing to report.
