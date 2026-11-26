# Lab checklist: after the demo

The full checks: edge cases, errors and the details of each feature. Do them after the demo on 2026-12-03. Before the demo, use only `docs/guides/lab-checklist.md` (the demo run). The tags are the same as before (2026-11-23), so older reports still match. Part 0 (update) and the step rules are in `docs/guides/lab-checklist.md`.

Rules:
- A real arm moves without asking. Keep one hand at **STOP** (on any lab-os page) while an arm has power.
- Ctrl+C in the brain's terminal makes an SO-101 go limp. If the arm is lifted, hold it first.
- The green arms have their own rules (`AGENTS.md` → "Hard rules"). Never start lab-os on them while LeLab runs.
- The voice is OpenAI's (the professor's key, in `.env`). After you change `.env`, restart the brain. Without that key, the free Gemini key speaks (about 15 to 20 answers a day).

**(wake word)** in a step means the active persona's wake word: "hey Jarvis" for J.A.R.V.I.S., "OK computer" for the Lab Assistant (⚙ → Assistant).

You need no ruler. Measure with these:
- a sheet of letter paper (short edge 21.6 cm, long edge 27.9 cm);
- a bank card (8.6 cm long, 5.4 cm wide);
- the cube (3 cm);
- your phone, flat on the table (about 1 cm thick).

---

## V. The wake word and the greeting (15 min)
**Done (2026-11-23):** V.1, V.2, V.3, V.15, V.16, V.17, V.19, V.20 and 0.2 to 0.5 passed. The wake words answered too rarely (V.21 to V.23), and the end of a question came too early (V.25, V.18): quick jobs 98 and 99. The settings value box moved (0.3): quick job 101. The brain logs only the wake words it heard, so the misses of V.5 are not in the log (quick job 99 adds them).
**These steps need a microphone on the Newline's screen.** The Pi that drives the Newline (HDMI and the touch cable) has no microphone: the Newline's own microphone belongs to its Android, not to the Pi. Connect a USB microphone to that Pi first, or skip them.
- **V.4** Open the hub on the Newline too (Open on…), with its sound on. Ask the desktop a question by voice. When the answer ends, say the wake word again. → did the desktop answer at once? (yes / no) If no, write the time.
- **V.8** Quick job 58. Open the hub on the Newline too. Ask the Newline a question by voice. Look at the desktop's core while the Newline answers. → did the desktop's core stay still (not listening, thinking or speaking)? (yes / no)
- **V.12** Quick job 70. Open the hub on the Newline and on the desktop, both with Wake Word. Stand next to the Newline. Say "(wake word), what time is it?". → did only the Newline answer? (yes / no) Write the time.

---

## T. Two arms from the Quest (45 min)
Preview 3: the right controller drives `so101-white`, and the left controller drives `so101-green`. How it works: `docs/guides/quest-setup.md` → "Two arms at once".

Before you start:
- Stop LeLab and any training or recording run. The brain refuses the green arm while another program has its port open.
- Do not move the green arm's stand or its cameras (the training setup). If the two arms face different directions, leave them so, and write it in T.5.

Cables to plug in, on the lab desktop:
- `so101-white` (the follower): its USB cable and its power supply.
- `so101-green` (the follower): its USB cable and its power supply.
- The Quest: its USB-C data cable.
- The arms need no cameras for this part. If no USB socket is free, unplug the green set's two cameras (sockets 7 and 8).
- The green leader arm can stay plugged in. lab-os does not open it.

Then run:
```bash
ls /dev/serial/by-id/
uv run --extra so101 lab-os serve --arm so101-white --left-arm so101-green --speed 0.3
```
Connect the Quest by USB. The brain runs `adb reverse` by itself.

- **T.1** Read the `ls` output. → does it show both `…5B41532410-if00` (white) and `…5B41533501-if00` (green)? (yes / no)
- **T.2** Read the brain's terminal. → does it say `two arms: the right controller drives so101-white, the left one so101-green`? (yes / no; if no, copy the last line)
- **T.3** On the desktop, open http://localhost:8080/teleop. → does it show **Right arm** and **Left arm**, both "holding"? Does the 3D view show two arms, with the joints of each in the column next to it? (yes / no each) Keep this page open, with the mouse near **STOP**, for all steps.
- **T.4** On the desktop, open http://localhost:8080/monitor/so101 in a second window, next to the teleop page. → does it show two arms in the 3D view, and a joints card for each arm? (yes / no) Keep it in view during T.8 to T.11. → do both 3D arms move with the real arms? (yes / no)
- **T.5** In the Quest's browser, open `http://localhost:8080/teleop` and select **Enter AR**. Look at the status panel. → does it show two labels, "Left holding" on the left and "Right holding" on the right? (yes / no) Do you see two see-through arms? (yes / no) Do the real arms face the same direction? (yes / no; if no, which way does each face?)
- **T.6** Hold **Y**, then hold the right grip. Move and turn the right 3D arm onto `so101-white`, then release the grip. Do the same with the left grip for the left 3D arm and `so101-green`. Release Y. → did the real arms stay still the whole time? (yes / no) Did the panel say "Y held: a grip moves its 3D arm"? (yes / no) Is each 3D arm on its real arm? (yes / no)
- **T.7** Tap Y once, quickly. → did both 3D arms go back? (yes / no) Put them on the real arms again, as in T.6.
- **T.8** Hold the right grip. Move the right controller slowly 10 cm to the right, then back. → did only `so101-white` move, to the right and back? (yes / no)
- **T.9** Hold the left grip. Move the left controller slowly 10 cm to the left, then back. → did only `so101-green` move, to the left and back? (yes / no)
- **T.10** Hold both grips. Move both hands slowly forward 10 cm, then up 10 cm. → did both arms move the same way as your hands? (yes / no) Was one arm slower or shakier than the other? (which one?)
- **T.11** Hold both grips. Pull the right trigger, then the left trigger. → did each trigger close only its own arm's gripper? (yes / no)
- **T.12** Release both grips. On the desktop's teleop page, set **Hand → arm** to **1:1**. → does the headset show a green ball at each 3D gripper? (yes / no) Put your left hand in the left ball and hold the left grip. Move the hand slowly 5 cm up, then 5 cm forward. → does `so101-green`'s gripper stay with your hand? (yes / no; about how many cm off?)
- **T.13** Do the same with the right hand and `so101-white`. → does its gripper stay with your hand? (yes / no; about how many cm off?) Then use both hands at once. → does it work? (yes / no) Set **Hand → arm** back to **Relative**.
- **T.14** Hold both grips and move. Press **X** (left controller). → did both arms stop? Does the panel say "Left stopped: let go" and "Right stopped: let go"? (yes / no each) Release both grips and hold them again. → do both arms move again? (yes / no)
- **T.15** Hold both grips and move. Press **STOP** on the desktop page. → did both arms stop? (yes / no)
- **T.16** Put the cube in front of `so101-white`. Pick it up with the right arm, then give it to the left arm. → did it work? (yes / no; how many tries? What was difficult?)
- **T.17** Hold both arms. Press Ctrl+C in the brain's terminal. → did both arms go limp? (yes / no)
- **T.18** Run `ls -l --time-style=full-iso ~/.cache/huggingface/lerobot/calibration/robots/so_follower/sheep.json`. → is the date before today? (yes / no; it must be: lab-os only reads this file)
- **T.19** Run `uv run --extra so101 lab-os serve --speed 0.3`, with no arm names. → does the terminal say `two arms: the right controller drives so101-white, the left one so101-green`? (yes / no) Press Ctrl+C. Hold the arms first if they are lifted.
- **T.20** Run `uv run lab-os green` and wait for LeLab. In a second terminal, run the command from T.19 again. → does the terminal say why it does not use the green arm, and drive `so101-white` only? (yes / no) Press Ctrl+C in both terminals.

## D. STOP from another device (10 min)
Setup: `so101-white` connected, the brain running (part T's command without `--left-arm`). A second device (a phone or a laptop) on the brain's network, or the Quest's browser.
- **D.1** On the second device, open `http://<address>:8080/monitor/so101`. → does SO-101 Monitor show the arm and a STOP button? (yes / no)
- **D.2** On the desktop's hub, say `(wake word), it's demo time`, then tap **Ask me to wave**. During the wave, press STOP on the second device. → did the arm stop at once? (yes / no)
- **D.3** Say `(wake word), the visitors have left`. → nothing to report.

## W. Teleop with a webcam (25 min)
Preview 2: your bare hand in front of the Logitech C615 drives the arm. How it works: `docs/archive/guides-2026-11-25/webcam-teleop.md`. W.3 to W.8 passed on the laptop (2026-11-21); W.3 to W.6 are new checks for the fixes. Do W.1 to W.6 and W.9 with no arm (the fake arm), then W.10 to W.15 with `so101-white`.

Cables to plug in, on the lab desktop:
- The C615: a free USB socket. If no socket is free, unplug the green set's two cameras (sockets 7 and 8). This part does not use them.
- Put the C615 on top of the desktop's monitor, facing the chair.

Then run:
```bash
uv run lab-os serve
```

- **W.1** Run `ls /dev/v4l/by-path/`. Unplug the C615, run it again, and plug the C615 back in. → which name went away? (copy it)
- **W.2** On the desktop, open http://localhost:8080/webcam. Click **Start webcam control** and allow the camera. → does **Camera** show the C615? (yes / no) What does **Frames a second** show?
- **W.3** Quick job 88. Show both hands. → is your right hand cyan? (yes / no) Is the **Swap left and right hands** box clear? (yes / no)
- **W.4** Hold Space. Keep your right hand still for 5 seconds. → does the 3D arm stay still? (yes / a little shake / it shakes a lot)
- **W.5** Hold Space. Tilt your right hand: fingers toward the camera. Then turn it like the hand of a clock. → did the 3D arm's gripper tilt, then turn? (yes / no each)
- **W.6** Hold Space. Move your right hand down. If the hand reaches the bottom of the picture, let go of Space, raise the hand, and hold Space again. → can the 3D arm's gripper reach the table? (yes / no) Did a hand that was not there show at any time? (no / yes: how long?)
- **W.9** Ask another person to stand behind you in the picture. Pinch with your left hand, and move your right hand slowly 20 cm to the right. → did the page follow your hand only? (yes / no; if no, what happened?) Close the webcam page. Press Ctrl+C in the brain's terminal.

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
Preview 1: Claude Code plays tic-tac-toe with `so101-white` against you. How it works: `docs/archive/guides-2026-11-25/tic-tac-toe.md`. You need the stand camera's table map (made on 2026-11-19), the cube, and 5 red and 5 blue pieces (LEGO, about 3 cm tall).

Before the lab day, print `models/games/tic-tac-toe-sheet-letter.pdf` at 100 % ("Actual size"). Plug in `so101-white` (its USB cable and its power supply) and its two cameras, on its USB hub (`docs/guides/plug-in.md`). Then run:
```bash
uv run --extra so101 lab-os serve --speed 0.3
```
- **G.1** Put the cube on the printed sheet. → is one cell as wide as two cubes? (yes / no)
- **G.2** Set up the table as in the guide, section 1 (the sheet 12 cm in front of the base, the red pieces beside the arm). In Claude Code, type the prompt in section 4 of the guide. → are the magenta squares on the printed lines? (yes / after I moved the paper / no) Are the green rings on the red pieces? (yes / after I moved them / no)
- **G.3** Type the prompt in section 5 of the guide. Put a blue piece in B2 and say "your turn". → did the arm take a red piece? (yes / no) Did it put it fully inside the cell it named? (yes / partly / no) Did the arm or a jaw touch any other piece? (no / yes: which)
- **G.4** Play to the end of the game. → did the AI read the board right each time? (yes / no: which turn) Did it say the right result? (yes / no) About how many minutes did the game take?
- **G.5** During the game, did the arm go low over the board at a time when it did not put a piece down? (no / yes: when) Clear the board. Tell the AI to go home. Press Ctrl+C in the brain's terminal. Hold the arm first if it is lifted.

## H. "Hand me the cube" (25 min)
Preview 4: the hub's assistant moves the arm to a named pose, and hands you the blue cube. How it works: `docs/archive/guides-2026-11-25/hub.md` → "The assistant moves the arm". You need the blue cube and the stand camera's table map. Stand in front of the arm, across the table, with a hand near STOP on a second device (Monitor).

Plug in `so101-white` (its USB cable and its power supply) and its two cameras, on its USB hub (`docs/guides/plug-in.md`). Then run:
```bash
uv run --extra so101 lab-os serve --speed 0.3 --open desk
```
- **H.1** The switch is off by default. On the hub, ask "move the arm to home" (typed). → did the arm stay still? (yes / no)
- **H.2** Select ⚙ → Robots → **The Assistant May Move the Arm**. Ask "(wake word), move the arm to ready" by voice. → did the arm go to `ready`, slowly? (yes / no) Did AI Control show the moves? (yes / no)
- **H.3** Ask "move the arm to the hand-over pose". → is the gripper held out toward you, at a height you can reach easily? (yes / too low / too high / not toward me)
- **H.4** Put the cube about 20 cm straight in front of the arm. Ask "Hand me the cube". → did the assistant say that it found the cube? (yes / no: what did it say) Did the arm pick it up? (yes / no / it missed)
- **H.5** → did the arm hold the cube out to you at the hand-over pose? (yes / no) Was it easy to take? (yes / no) Say "let go". → did the gripper open? (yes / no)
- **H.6** Put the cube about 35 cm in front of the arm. Ask for the cube again. → did the assistant say that it can't reach it, with nothing moved? (yes / no) Move the cube to a place the camera can't see. Ask again. → did it say that it can't see the cube? (yes / no)
- **H.7** Put the cube back 20 cm in front. Ask for the cube, and press STOP on Monitor while the arm moves. → did the arm stop at once, and stay still? (yes / no) Ask "move the arm to home". Press Ctrl+C in the brain's terminal. Hold the arm first if it is lifted.
- **H.8** Quick job 77. Start the brain again with the command above. Open AI Control (`/ai`) on the desktop. Ask "move the arm to ready", then "move the arm to the hand-over pose". → does AI Control show each move as arrived, not "short"? (yes / no: copy the line that says short)
- **H.9** Quick job 80. Keep a hand at STOP. Put the cube about 20 cm straight in front of the arm. Set ⚙ → Assistant → **Full Access** off, and ⚙ → Robots → **The Assistant May Move the Arm** off. Ask the hub's assistant: "Pick up the cube." → did the arm stay still? (yes / no)
- **H.10** Set **Full Access** on. Ask again, in one sentence: "Pick up the cube." → did the arm pick it up? (yes / no) About how many seconds did it take? Write the time. Set **Full Access** off again.
- **H.11** Quick job 81. Put the cube about 20 cm straight in front of the arm. In Claude Code, ask: "Pick up the cube with one run_program call, then hold it at the handover pose." → did the arm do it in one call? (yes / no) How many seconds did it take? Earlier, single moves took about a minute or more.

## I. The icon, one hub window and full screen (30 min)
Quick job 59. The hub window is now a browser of its own. Setup: the lab desktop, no brain running, every hub window closed.
- **I.1** Tap **Start lab-os**. If the browser asks for the microphone, allow it. → did one hub window open? (yes / no)
- **I.2** Click the brain's terminal, so that it covers the hub. Tap **Start lab-os** again. → did the hub come to the front? (yes / no) Did a second hub window open? (yes / no)
- **I.3** Minimize the hub window. Tap **Start lab-os** again. → did the hub window come back? (yes / no)
- **I.4** Close the hub window with its X. The brain keeps running. Tap **Start lab-os** again. → did one hub window open? (yes / no)
- **I.5** Quick job 64. Open the hub on the Newline too (Open on…). Press ⏻ → **Shut down lab-os** on the desktop. → did the desktop's hub window close? (yes / no) What does the Newline show? (closed / "lab-os is off" / other)
- **I.6** Tap **Start lab-os**. Open Quest view (the Quest on its USB cable). Press Ctrl+C in the brain's terminal. → did the hub window and the Quest view window close? (yes / no each) Did the Newline say "lab-os is off"? (yes / no)
- **I.7** Quick job 74. Tap **Start lab-os**. Press F11 two times, so that the hub is a window. → is there a full screen button in the hub's strip? (yes / no) Press it. → is the hub full screen? (yes / no)
- **I.8** In the hub, open Monitor. Press **Open on…** → **Another monitor of this computer**. → is Monitor full screen on the other monitor, with no click? (yes / no) Is the hub still full screen? (yes / no)
- **I.9** On the other monitor, press **Window** in Monitor's bar. → is Monitor a window now? (yes / no) Close it. Open it on the other monitor again, as in I.8. → does it open as a window? (yes / no)
- **I.10** Quick job 65. On the Newline (touch), press and hold the core for 2 seconds. Then press and hold a module button. → did a browser menu open? (yes / no) Press and hold a word in the ask line. → can you select it and paste? (yes / no)
- **I.11** Quick job 79. Plug the USB card reader into the lab desktop. Press ⏻ → **Back to the start screen**. Swipe your student ID. → did the hub start with "Card read" and its own sound? (yes / no) Go back to the start screen. Swipe a bank card. → did anything happen? (yes / no)
- **I.15** Quick job 54. Connect the Newline by HDMI and its USB touch cable, and the other monitor too. Follow `docs/archive/guides-2026-11-25/hub.md` → "The Newline's touch with a second monitor". → what did `echo $XDG_SESSION_TYPE` say? (x11 / wayland) Did each touch in the four corners land under your finger? (yes / no)
- **I.16** Quick job 138. Use a computer with two monitors that is not the brain's computer. In Chrome, open `https://192.168.8.130:8443/?device=<its name>`. If Chrome shows a certificate warning, select Advanced → Proceed. Open **Monitor**. Press **Open on…** → **Another monitor of this computer**. If Chrome asks to manage windows, select Allow, then press it again. → did Monitor open on the other monitor by itself? (yes / no) If not, did the message say to drag it? (yes / no) Write the computer's system (Windows / Ubuntu / macOS).

## Q. Leave VR, and "lab-os is off" in the Quest (20 min)
Quick job 78. Setup: the brain running on the fake arm (`uv run lab-os serve --arm fake`), the Quest on its USB cable, and `http://localhost:8080/xr` open in the Quest's browser.
- **Q.1** Press **Enter AR**. Pull the trigger to start, and wait for the hub. Point at **EXIT** under the hub. Pull the trigger. → are you back on the browser page? (yes / no)
- **Q.2** Press **Enter VR**. Start, and open **Teleop**. Point at **EXIT**. Pull the trigger. → are you back on the browser page? (yes / no)
- **Q.3** Press **Enter VR**. Stay on the start screen. On the desktop, shut down lab-os (⏻). → does the "lab-os is off" card show in the Quest? (yes / no) Pull the trigger. → does the startup start? (yes / no: it must not)
- **Q.4** Point at **EXIT** under the card. Pull the trigger. → are you back on the browser page? (yes / no) Start lab-os with its icon. → does the page come back by itself? (yes / no)
- **Q.5** Start lab-os with its icon. On the Quest, press **Enter VR**. Stay on the start screen. Unplug the Quest's USB cable. Wait 5 seconds. → does a card say "lab-os is not reachable"? (yes / no) Pull the trigger. → does the startup start? (yes / no: it must not)
- **Q.6** Plug the Quest's USB cable in again. Do not run `adb reverse`. → does the page come back by itself? (yes / no)

## U. Unplug and plug in again (50 min)
Quick job 73. Start lab-os with its icon, with no arm, no xArm and no USB microphone plugged in. Keep the brain's terminal in view.
- **U.1** Plug in `so101-white` (its USB cable and its power supply). Wait 10 seconds. → does the hub's Arm line say `so101-white`? (yes / no) Did the terminal say "so101-white was plugged in"? (yes / no)
- **U.2** Open Teleop on the desktop. Drive the arm a little with the keys. → does the real arm move? (yes / no)
- **U.3** Plug in the xArm. Run `uv run lab-os serve --arm xarm1 --port 8090 --mcp-port 0` in a second terminal, and open `http://localhost:8090/monitor/xarm`. Unplug the xArm's USB. → does Monitor say "disconnected"? (yes / no) Plug it in again. Wait 5 seconds. → does Monitor show the arm again? (yes / no) Stop that brain with Ctrl+C.
- **U.4** Plug in the USB microphone. → does the mic button show next to "Ask anything" within 5 seconds? (yes / no) Unplug it. → does the button go? (yes / no) Plug it in again. Wait 5 seconds. → is the button back? (yes / no)
- **U.5** Unplug the Quest's USB cable, then plug it in again. Do not run `adb reverse`. In the Quest's browser, open `http://localhost:8080/xr`. → does the page load? (yes / no)
- **U.6** Quick job 76. Open Teleop on the desktop's hub and on the Newline (Open on…). On the desktop, select **Desktop control** and move the arm with a key. → on the Newline, are the Teleop buttons grey, with a line that says the page on desk has control? (yes / no) On the desktop, press the \` key to leave desktop control. → can you press the Newline's buttons again? (yes / no)
- **U.8** In the Quest, open the hub in VR, then **Teleop**. Hold the grip, then press **A**. → does the panel say "Stopped", with "Let go of the grip, then grab again" under it? (yes / no) Let go of the grip. → does the panel change to "Holding" at once, without a new grab? (yes / no)
- **U.9** Quick job 60. Open the hub in VR (the Quest on its USB cable). → is the hub easy to read, and does all of it still fit when you turn your head a little? (yes / no) Point at ⚙ (beside ⏻) and pull the trigger. → does Settings open, with This Device first? (yes / no)
- **U.10** In Settings → This Device, switch **Sound** off, then on again. → does the line at the bottom say "Saved"? (yes / no) Press **B**. → does Settings close? (yes / no)
- **U.11** Quick job 63. Plug in `so101-white` and its two cameras, on its USB hub (`docs/guides/plug-in.md`). Open Teleop on the desktop. → under the joint angles, do you see the stand and the wrist picture, moving? (yes / no) Plug in the green set's two cameras (sockets 7 and 8). Start LeLab's camera view of the green set. Open the Cameras page. → do the two green pictures say that the camera is in use? (yes / no)
- **U.12** Quick job 49. Connect the Quest by USB. On the desktop's hub, press the Quest view button. Close the window with its own X. → does the button go dark within a second or two? (yes / no) Press it once. → does the window open again? (yes / no)
- **U.13** Quick job 50. Keep a hand at STOP. With `so101-white` and AI Control open, ask the hub's assistant "move the arm to home" (⚙ → Robots → The Assistant May Move the Arm on). → does AI Control show the move without "clipped"? (yes / no) → is the arm folded where it was before? (yes / no)
- **U.14** Quick job 51. Keep a hand at STOP. Put the cube about 20 cm straight in front of `so101-white`. Ask the hub's assistant "Hand me the cube". → when the jaws closed, did they hold the cube with most of their length, not only the tips? (yes / no) Did the gripper touch the table? (yes / no)
- **U.15** Quick job 52. Keep a hand at STOP. Clear the space to the right of `so101-white` and above it. On the desktop's hub, say `(wake word), it's demo time`, then tap **Ask me to wave**. → does it look like a wave from where the visitors stand? (yes / no) Did the arm touch anything? (yes / no) Say `(wake word), the visitors have left`.
- **U.16** In the hub in VR, point at ⏻ (top right) and pull the trigger. → does a menu open with "Back to the start screen" and "Exit"? (yes / no) Open **Teleop**, then press ⏻ beside ← on its tab, then **Exit**. → are you back on the browser page? (yes / no)
- **U.17** In the Quest's browser, open the hub's address. → do you see three choices in the middle (Enter VR, Enter AR, the hub in the browser)? (yes / no) Press **Use the hub in the browser instead**, then **Teleop**. → does the Teleop page open, with Desktop control grey? (yes / no)
- **U.18** On the Teleop page, select 1:1, then **Enter AR**. Drive the fake arm. → does it work? (yes / no) Leave AR. In the browser's menu, is there an Install choice? (yes / no)
- **U.19** Quick job 94. Connect the USB cable of `so101-white`, but not its power supply. Start lab-os with its icon. → does the terminal say "so101-white: the motors do not answer. Is the arm's power on?", with no traceback? (yes / no) Does the hub's Arm line say the fake arm? (yes / no) Connect the power supply. Wait 10 seconds. → does the Arm line say `so101-white`? (yes / no)
- **U.20** Quick job 97. Keep a hand at STOP. With `so101-white`, open the hub in VR, then **Teleop**. → does the arm's room open, without leaving VR? (yes / no) Hold the right grip and move your hand. → does the arm follow, and does the status box say "Following"? (yes / no)
- **U.21** Let go of the grip. Press **A**. → does the box say "Stopped"? (yes / no) Press **B**. → is the hub back, and does the arm hold still? (yes / no) Open Teleop again, press ⏻ beside ←, then **Exit**. → are you back on the browser page? (yes / no)
- **U.22** On the desktop, open Teleop and press **Desktop control**. In VR, open Teleop. → does the status box say "desk has control" (or the desktop's name)? (yes / no) On the desktop, press the \` key to leave Desktop control. Leave VR, press **Enter AR**, then open Teleop and hold the right grip. → does the arm follow your hand? (yes / no)

## B. The Teleop page's buttons (5 min)
Quick job 87. Use the lab desktop's Chrome with the **Immersive Web Emulator** extension switched on.
- **B.1** Open Teleop. → are the buttons in this order: **Desktop control**, **Enter AR**, **Enter VR**? (yes / no) Can you click **Desktop control**? (yes / no)
- **B.2** Look under the buttons. → is there a **Controls** box with the speed, Hand → arm and the desktop keys? (yes / no)
- **B.3** In the Quest's browser, open Teleop. → is **Desktop control** grey? (yes / no)

## E. LeRobot teleop with Rerun (15 min)
Quick job 91. The green leader drives the green follower through LeRobot's own command. Run `uv sync --extra so101` once before. Stop LeLab. Plug in both green arms and their two cameras. Run `uv run --extra so101 lab-os serve --arm fake`.
- **E.1** On the lab desktop, open the hub's **Training** page. → are all lines in the "LeRobot teleop with Rerun" card fine? (yes / no; if no, copy the lines with a warning)
- **E.2** Put the leader and the follower in the same pose. Press **Start**. Wait 20 seconds. → does Rerun open in its own window, with the two camera pictures and the joints? (yes / no) Move the leader. → does the follower follow? (yes / no)
- **E.3** Hold the follower. Press **Stop**, then OK. → did the follower go limp? (yes / no) Does the card say "LeRobot's teleop stopped"? (yes / no)

## C. The Cameras page (15 min)
Quick job 93. Plug in the white arm's two cameras. Run `uv run lab-os serve`. Open the hub on the lab desktop as `/?device=desk`, and on the Newline as `/?device=newline`.
- **C.1** On the desktop's hub, open **All Pages** → **Cameras** → **Open**. → does each camera show a live picture? (yes / no) Do the digits next to each camera's name stay under 1.0? (yes / no)
- **C.2** Press the name of the wrist camera above the pictures. → did the wrist picture go away? (yes / no) Did the stand picture stay? (yes / no)
- **C.3** On the desktop's hub, open Cameras inside the hub, press **Open on…**, then select the Newline. On the Newline, hide the stand camera. On the desktop, show the stand camera and hide the wrist camera. → does the Newline show only the wrist camera? (yes / no) Does the desktop show only the stand camera? (yes / no)

## R. The Raspbot page (25 min)
Quick job 72. raspbot1 on the router's Wi-Fi, with its battery charged. Put it on a box with the wheels off the floor. Steps: `docs/guides/raspbot.md`.
- **R.1** Run `ssh raspbot1 sh /home/pi/project_demo/raspbot/killprocess.sh`. Run `uv run lab-os raspbot deploy`. → does the last line say "lab-os's program runs on raspbot1"? (yes / no: copy the last lines)
- **R.2** Run `uv run lab-os serve`. On the desktop, open **All Pages** → **Raspbot** → **Open**. → does **Connection** show **Connected**? (yes / no: copy the message below the controls) Does the camera show a picture? (yes / no)
- **R.3** Keep a hand at **STOP**. Hold **↑** for 2 seconds, then let go. → did all four wheels turn the same way, forward? (yes / no: which wheel did not?) Did they stop when you let go? (yes / no)
- **R.4** Hold **←** for 2 seconds. → did the left wheels turn back and the right wheels forward? (yes / no) Hold **↓**, and press **STOP** while you hold it. → did the wheels stop at once? (yes / no) Did they stay stopped while you still held **↓**? (yes / no)
- **R.5** Hold **↑**. While the wheels turn, turn off the desktop's Wi-Fi. → did the wheels stop within 1 second? (yes / no) Turn the Wi-Fi on again.
- **R.7** Run `ssh -t raspbot1 sudo sh lab-os/install-wifi.sh` (type raspbot1's password). Run `ssh raspbot1 sudo reboot`. Wait 1 minute. Run `ssh raspbot1 systemctl status lab-os-wifi`. → does the last line say "joined GL-B7-5G" or "on GL-B7-5G"? (yes / no: copy the last line)
- **R.8** Turn off the router's Wi-Fi in its admin page, or take raspbot1 out of the router's range. Restart raspbot1 with its switch. Wait 2 minutes. → does a phone see the "Raspbot" Wi-Fi? (yes / no) Turn the router's Wi-Fi on again. Restart raspbot1. → does `ssh raspbot1 hostname` answer after 2 minutes? (yes / no)
- **R.9** When raspbot1 stops by itself again (black screen, keyboard and mouse off), switch it off and on. Run `ssh raspbot1 tail -n 20 lab-os/health.log`. → copy the lines. What did raspbot1 do just before (nothing / driving / the camera page open / other)?
- **R.6** Put raspbot1 on the floor with space around it. Drive it forward, back and in a circle. Move **Speed** from 0 % to 100 %. → which speed is good for the demo? (a percentage) Is the camera picture behind by less than about 1 second? (yes / no)

## P. After the demo: one program or single moves, 5 against 5 (60 min)
Quick job 81. Do this part only after the demo. It compares how often the pick works, and how long it takes. Use Claude Code, `so101-white`, and the cube about 20 cm straight in front of the arm. Keep a hand at **STOP**. Before each try, put the cube back in the same place, and send the arm to `ready`.
- **P.1** Ask Claude Code 5 times, each time in a new conversation: "Pick up the cube step by step, with single moves and no run_program, then hold it at the handover pose." → how many times did it hold the cube at `handover`? (0 to 5)
- **P.2** For each try of P.1, write the seconds from your request to the arm at `handover`. → the 5 times, in seconds.
- **P.3** Ask Claude Code 5 times, each time in a new conversation: "Pick up the cube with one run_program call, then hold it at the handover pose." → how many times did it hold the cube at `handover`? (0 to 5)
- **P.4** For each try of P.3, write the seconds. → the 5 times, in seconds. For each try that did not work, write what went wrong (missed the cube, dropped it, stopped, other).

## V2. After the demo: the wake word with other people near (30 min)
There are no other people in the lab before the demo.
- **V.24** With each word that answered 4 or 5 times: talk with another person near the microphone for 10 minutes, without the wake word. → did it wake by itself? (no / yes: write the times)
- **V.14** Say "(wake word), start a conversation". → did the sign show? (yes / no) Let two people talk near the microphone for 20 seconds. → what did it do? (answered them / nothing / other)

## M4. After the demo: "set up the room" (10 min)
Skipped on 2026-11-24. Open the hub on each computer first (`/?device=<its name>`).
- **M.4** Quick job 71. Name the devices as in `config/room.yaml` (newline, win-1, pi-1 …), or edit that file to match. On the desktop, say "(wake word), set up the room". → did each device show its page? (yes / no) Did the answer name the devices that were not on? (yes / no)

## M7. After the demo: a second lab desktop as the brain (30 min)
Quick job 150. Use a lab desktop that does not have lab-os.
- **M.13** On that desktop, open a terminal. Type `git clone https://github.com/IWU-AI-Lab/lab-os.git && cd lab-os && ./scripts/install.sh`. Paste the commands that it prints at the end, and do its other steps. Then type `uv run lab-os setup`. → how many minutes did it take? Which lines said TO DO at the end? (none / the lines) Did a step surprise you? (no / yes: what)
- **M.14** On that desktop, type `uv run lab-os serve --open desk`. → did the hub open? (yes / no) Did it show the SO-101 that you plugged in? (yes / no / no arm plugged in)

## M6. After the demo: the hub in Chrome on a laptop (10 min)
Moved from the demo run on 2026-11-25 (the builder). Before the demo, use Firefox on the laptop.
- **M.6** Quick job 130. On the builder's laptop, open Chrome. Type `http://192.168.8.130:8080/?device=laptop`. If Chrome shows "This site can't be reached", do the steps in `docs/guides/plug-in.md` → "Open the hub on another computer". → which error code was under Chrome's message? (the code, or "none") Did the hub open? (yes / no: after which step)

## PT. After the demo: the persona round table (10 min)
Quick job 151, a first version. Use the desktop with sound on.
- **PT.1** Open ⚙ → **This Device**. Set **Level of Detail** to **Full**. Open ⚙ → **Assistant**. Click the name of the persona that does not show **Active**. → did the table turn that persona to face you? (yes / no) Did you hear its greeting in its own voice? (yes / no: copy the line under the buttons)
- **PT.2** Click **Choose** (the button under the greeting). Open the hub. → does the hub show the persona that you chose? (yes / no) Set **Level of Detail** to **Minimal**. → does ⚙ → **Assistant** → **Persona** show the plain buttons and no table? (yes / no)
- **PT.3** Look at the table on the slowest screen (the Pi or a laptop) with **Full**. → does the turn look smooth? (yes / no) What do you want to change on the table? (a sentence)

## M8. After the demo: System Map (5 min)

- **M8.1** Open **System Map** from the hub on the slowest lab screen. Drag the map to rotate it. Select an SO-101 and the Raspbot. Open the hub on a second screen. Close that hub. → Do both robots show their models? Does the second screen change to **Connected** and then **Disconnected**? Does the map rotate smoothly? (yes / no for each)
- **M8.2** Drag the map until you can see below the bases. Open **Cameras** on a second screen. → Do the names stay upright? Do the connected devices float above their bases? Does the preview show **Cameras**? (yes / no for each)
- **M8.3** Open **System Map** on the lab desktop and do not touch it for 10 s. Right-drag the map. Scroll the mouse wheel over a device. Double-click a device on the map. Double-click a device in the list. Click **Reset view**. Then do the same steps on a Pi touchscreen, with two fingers instead of the right-drag and the wheel. → Does the map turn slowly by itself, and stop when you touch it? Do the robots turn on their bases? Does a screen at the back hide behind the devices in front of it? Do the devices of each kind make a 3D group, above and below the brain? Is the text on a screen's picture sharp when you go to it? Does the map move with the right-drag and the two fingers? Does the view fly to the device and back? (yes / no for each)

## X1. After the demo: the shared parts of the UX review (15 min)
Quick job 153. Use the 4K screen, a Pi touchscreen and the lab desktop.
- **X1.1** Open `docs/plan/ux-review.md`, part 1. Check each line on the pages. Tick the lines that are right. → Which lines are not right? (the line's first words and a sentence)

## X2. After the demo: the robot pages of the UX review (20 min)
Quick job 155. Use the 4K screen, a Pi touchscreen, a phone, the Quest and the lab desktop.
- **X2.1** Open `docs/plan/ux-review.md`, part 3. Check each line on the pages. Tick the lines that are right. → Which lines are not right? (the line's first words and a sentence)
