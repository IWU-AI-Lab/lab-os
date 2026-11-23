# Lab checklist

Every step has a tag (for example **11.4**). The line after **→** says what to report. Report as `11.4: yes` or `T.10: right arm`. Run the commands in a terminal on the lab desktop, in `~/lab-os`. Each part works alone.

This list has only what is still to do. When a step is done, it is removed (its result goes to `docs/dev/GOTCHAS.md` or `docs/plan/quick-jobs.md`).

**Order.** Monday 2026-11-23 (about 1 hour): 0, then N (its home steps done before). If you have more time: M, then W. Tuesday 2026-11-24 (the testing day): 0, V, T, D, G, H, I, Q, U, then the parts that the sessions add for the new quick jobs. This is about 5 hours. If you have time on Monday, do I and Q then (they need no arm). Tuesday 2026-12-01: setting up for the demo, and a practice run.

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
  - The lab has many Ethernet cables. Do not ask to bring one.
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

## V. The wake word and the greeting (25 min)
Quick job 42. The cause of the stops was not found on the Mac. The brain's terminal now says when it ignores "hey Jarvis", and why. Setup: the desktop's hub with ⚙ → This Device → Talking to It → **Wake Word**, the USB microphone in its front port, and no roof fan if possible. Keep the brain's terminal in view.
- **V.1** Press ⏻ → **Back to the start screen**. Tap to start. → did the greeting start at once, before the jump ended? (yes / no)
- **V.2** Say "Hey Jarvis, what time is it?". Wait for the answer. Say it again. → did it answer both times? (yes / no)
- **V.3** Open ⚙. Move **Wake Word Sensitivity** from 5 to 7. Close ⚙. Say "Hey Jarvis, what's next?". → did it answer? (yes / no) If no, copy the terminal's last lines that start with `voice:`.
- **V.4** Open the hub on the Newline too (Open on…), with its sound on. Ask the desktop a question by voice. When the answer ends, say "Hey Jarvis" again. → did the desktop answer at once? (yes / no) If no, copy the `ignored:` line from the terminal.
- **V.5** Each time during the day that the wake word does not answer: copy the terminal's `voice:` lines from that minute into the report. → how many times did it stop today? (a number)
- **V.8** Quick job 58. Open the hub on the Newline too. Ask the Newline a question by voice. Look at the desktop's core while the Newline answers. → did the desktop's core stay still (not listening, thinking or speaking)? (yes / no)
- **V.12** Quick job 70. Open the hub on the Newline and on the desktop, both with Wake Word. Stand next to the Newline. Say "Hey Jarvis, what time is it?". → did only the Newline answer? (yes / no) Copy the terminal's line that ends with `answers`.
- **V.14** Say "Hey Jarvis, start a conversation". → did the sign show? (yes / no) Let two people talk near the microphone for 20 seconds. → what did it do? (answered them / nothing / other)
- **V.15** Quick job 83. Ask a question that has a long answer. While the answer plays, say "Hey Jarvis". → did the answer stop, and did it listen? (yes / no)
- **V.16** Say "Hey Jarvis, start a conversation". Ask one question. Then say "That's all". → did the core go back to rest (not thinking)? (yes / no)
- **V.17** Press and hold the mic for 1 second. Say nothing. → did it answer something? (yes / no) Write the time.
- **V.18** Say "Hey Jarvis, calculate 37 times 48," then wait a moment, then say "then add 199". → did it hear the whole question? (yes / no)
- **V.19** Set ⚙ → Answers to **Any**. Say "Hey Jarvis, hi". → which language was the answer? Ask three more questions. → did the voice sound like the same person each time? (yes / no)

---

## N. The travel router (15 min at home, 45 min in the lab)
The GL.iNet Beryl 7 (`docs/plan/current-focus.md` → "Waiting on others"). The professor approved the router and its use of the wall Ethernet port (2026-11-20). The router gets its internet from the wall port from the start. For now, the brain desktop keeps its own internet on the campus Wi-Fi, and reaches the router's devices by a cable. This is a temporary safeguard until the wall port's internet is proven; then everything goes on the router. Background: `docs/guides/network-setup-checklist.md`. To undo all of it: switch the router off and remove the desktop's cable.
**At home, before the lab day (15 min).** Connect the router's power adapter. Setting it up at home changes nothing for the lab: the router keeps its settings. Do not change its own address (`192.168.8.1`); the steps below expect it.
- **N.1** Read the label under the router. → write the router's admin address (for example `192.168.8.1`) and its Wi-Fi names. Do not write the Wi-Fi password in the report.
- **N.4** Connect the laptop to the router (its Wi-Fi from the label, or a cable to a **LAN** port). Open the admin address from N.1. Set an admin password, and keep it in your password manager, not in the repo. → did the router's page open? (yes / no)
- **N.5** In the router's page, open the Wi-Fi settings. Give both bands one name of your choice, a new password, and the security **WPA2-PSK** or **WPA2/WPA3**, not WPA3 alone (older Pis and the Raspbot need WPA2). Save. → which security options did it offer? (copy them)
- **N.14** If you can, connect the router's **WAN** port to your home router by a cable. In the router's page, update the firmware. → which firmware version does it show now?

**In the lab.** Do the steps in this order; stop when your time ends. The first ones answer the main question: does the wall port give internet?
- **N.2** Connect the wall Ethernet port to the router's **WAN** port. Connect the router's power adapter (from the box) to a wall socket. Wait 2 minutes. → is its light on and steady? (yes / no)
- **N.12** On your phone, on the router's Wi-Fi, open a web page. → does it open? (yes / no) If no: in the router's page → Internet, copy what it says about the WAN port. Then connect your phone's hotspot (security WPA2) in the router's page → Internet → Repeater. → does a web page open now? (yes / no)
- **N.13** On your phone, on the router's Wi-Fi, open fast.com. → the speed in Mbps.
- **N.3** Connect an Ethernet cable from the lab desktop's Ethernet port to the router's **LAN** port (not WAN). In Ubuntu Settings → Network → the wired connection → ⚙ → IPv4, select **Use this connection only for resources on its network**, then Apply. Turn the wired connection off and on. → does a web page still open on the desktop? (yes / no) Copy the first line that `ip -4 addr | grep 192.168.8` shows.
- **N.6** In the router's page, find the list of clients. Reserve the lab desktop's address, so that it does not change. → the desktop's reserved address: ___ (it starts with 192.168.8)
- **N.15** The big switch (the Jetson and 4 Pis). Do not unplug anything yet. → where does the switch's other cable go now? (a wall port / another device / nothing) Is the switch's power light on? (yes / no)
- **N.16** Connect a free port of the switch to the router's **LAN** port. If the router has only one LAN port and the desktop uses it, connect the desktop's cable to the switch instead. Wait 1 minute. In the router's list of clients → how many new devices? Do their names look like the Pis and the Jetson? (yes / no: copy the names)
- **N.17** On the Pi with the touchscreen, open Chrome at `http://<the reserved address>:8080/design?device=pi-switch`. → did the hub load? (yes / no; if no, run `hostname -I` on that Pi and copy the line) If the Pis do not work on the router: connect the switch back as it was in N.15. They were on the campus network before; the hub is then at the desktop's campus address (`hostname -I` on the desktop, the first one).
- **N.7** On the desktop, run `uv run lab-os serve --host 0.0.0.0`. On your phone, join the router's Wi-Fi. Open `http://<the reserved address>:8080/design?device=phone`. → did the hub load? (yes / no)
- **N.8** On the Quest, join the router's Wi-Fi. Without the USB cable, open `http://<the reserved address>:8080/design?device=quest-a` in its browser. → did the hub load? (yes / no) Open `chrome://flags` in the Quest's browser. → does a flags page open? (yes / no)
- **N.10** On the Newline, open its Wi-Fi settings and join the router. In its Chrome, open `http://<the reserved address>:8080/?device=newline`. → did it join? (yes / no) Did the hub load? (yes / no)
- **N.9** On a Pi with a screen, run `sudo nmcli dev wifi connect "<the router's Wi-Fi name>" password "<password>"`. → did it join? (yes / no; if no, copy the error) Run `ping -c 3 <the reserved address>`. → replies? (yes / no)
- **N.11** Connect to raspbot1 by its cable (`docs/guides/network-setup-checklist.md` → Step 2). Run `sudo nmcli dev wifi connect "<the router's Wi-Fi name>" password "<password>"`. → did it join? (yes / no; if no, copy the error line)

## M. Every screen in the room (30 min)
After part N, or on the campus network for the computers that are already on it (the desktops and the Pis). The plan for the demo: `docs/plan/current-focus.md` → item 10. Use the brain's address on the same network as the device: `192.168.8…` on the router, or the campus address that `hostname -I` shows first.
- **M.1** On each computer that can show a screen (the 2 Windows desktops, the other Ubuntu desktop, each Pi with a screen, the Newline), open Chrome at `http://<the brain's address>:8080/design?device=<a short name>`. Use names like `win-1`, `win-2`, `ubuntu-2`, `pi-1`, `newline`. → for each: the name, and did the hub load? (yes / no)
- **M.2** On each computer with a USB microphone (the 2 Windows desktops) and on the Newline: open `chrome://flags`, search for "Insecure origins treated as secure", type `http://<the brain's address>:8080`, select Enabled, then Relaunch. → for each: is there a mic button next to "Ask anything"? (yes / no)
- **M.3** On the desktop's hub, open the Devices panel. → how many devices does it list? (a number) Are all names from M.1 there? (yes / no: which are missing?)
- **M.4** Quick job 71. Name the devices as in `config/room.yaml` (newline, win-1, pi-1 …), or edit that file to match. On the desktop, say "Hey Jarvis, set up the room". → did each device show its page? (yes / no) Did the answer name the devices that were not on? (yes / no)
- **M.5** On the desktop's hub, open the AI Spend panel's details. Press **Open on…** → the Newline. → did AI Spend open on the Newline? (yes / no) Do the same with the system diagram (the network icon in Devices). → did it open there? (yes / no)

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
Connect the Quest by USB. The brain runs `adb reverse` by itself.

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
- **T.14** Hold both grips and move. Press **X** (left controller). → did both arms stop? Does the panel say "Left stopped: let go" and "Right stopped: let go"? (yes / no each) Release both grips and hold them again. → do both arms move again? (yes / no)
- **T.15** Hold both grips and move. Press **STOP** on the desktop page. → did both arms stop? (yes / no)
- **T.16** Put the cube in front of `so101-white`. Pick it up with the right arm, then give it to the left arm. → did it work? (yes / no; how many tries? What was difficult?)
- **T.17** Hold both arms. Press Ctrl+C in the brain's terminal. → did both arms go limp? (yes / no)
- **T.18** Run `ls -l --time-style=full-iso ~/.cache/huggingface/lerobot/calibration/robots/so_follower/sheep.json`. → is the date before today? (yes / no; it must be: lab-os only reads this file)
- **T.19** Run `uv run --extra so101 lab-os serve --speed 0.3`, with no arm names. → does the terminal say `two arms: the right controller drives so101-white, the left one so101-green`? (yes / no) Press Ctrl+C. Hold the arms first if they are lifted.
- **T.20** Run `uv run lab-os green` and wait for LeLab. In a second terminal, run the command from T.19 again. → does the terminal say why it does not use the green arm, and drive `so101-white` only? (yes / no) Press Ctrl+C in both terminals.

## D. STOP from another device (10 min)
Setup: `so101-white` connected, the brain running (part T's command without `--left-arm`). A second device (a phone or a laptop) on the brain's network, or the Quest's browser.
- **D.1** On the second device, open `http://<address>:8080/monitor`. → does Monitor show the arm and a STOP button? (yes / no)
- **D.2** On the desktop's hub, say `Hey Jarvis, it's demo time`, then tap **Ask me to wave**. During the wave, press STOP on the second device. → did the arm stop at once? (yes / no)
- **D.3** Say `Hey Jarvis, the visitors have left`. → nothing to report.

## W. Teleop with a webcam (25 min)
Preview 2: your bare hand in front of the Logitech C615 drives the arm. How it works: `docs/guides/webcam-teleop.md`. W.3 to W.8 passed on the laptop (2026-11-21). Do W.1, W.2 and W.9 with no arm (the fake arm), then W.10 to W.15 with `so101-white`.

Cables to plug in, on the lab desktop:
- The C615: a free USB socket. If no socket is free, unplug the two cameras in sockets 7 and 8. This part does not use them.
- Put the C615 on top of the desktop's monitor, facing the chair.

Then run:
```bash
uv run lab-os serve
```

- **W.1** Run `ls /dev/v4l/by-path/`. Unplug the C615, run it again, and plug the C615 back in. → which name went away? (copy it)
- **W.2** On the desktop, open http://localhost:8080/webcam. Click **Start webcam control** and allow the camera. → does **Camera** show the C615? (yes / no) What does **Frames a second** show?
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
- **H.8** Quick job 77. Start the brain again with the command above. Open AI Control (`/ai`) on the desktop. Ask "move the arm to ready", then "move the arm to the hand-over pose". → does AI Control show each move as arrived, not "short"? (yes / no: copy the line that says short)

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
- **I.15** Quick job 54. Connect the Newline by HDMI and its USB touch cable, and the other monitor too. Follow `docs/guides/hub.md` → "The Newline's touch with a second monitor". → what did `echo $XDG_SESSION_TYPE` say? (x11 / wayland) Did each touch in the four corners land under your finger? (yes / no)

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
- **U.3** Plug in the xArm. Run `uv run lab-os serve --arm xarm1 --port 8090 --mcp-port 0` in a second terminal, and open `http://localhost:8090/monitor`. Unplug the xArm's USB. → does Monitor say "disconnected"? (yes / no) Plug it in again. Wait 5 seconds. → does Monitor show the arm again? (yes / no) Stop that brain with Ctrl+C.
- **U.4** Plug in the USB microphone. → does the mic button show next to "Ask anything" within 5 seconds? (yes / no) Unplug it. → does the button go? (yes / no) Plug it in again. Wait 5 seconds. → is the button back? (yes / no)
- **U.5** Unplug the Quest's USB cable, then plug it in again. Do not run `adb reverse`. In the Quest's browser, open `http://localhost:8080/xr`. → does the page load? (yes / no)
- **U.6** Quick job 76. Open Teleop on the desktop's hub and on the Newline (Open on…). On the desktop, select **Desktop control** and move the arm with a key. → on the Newline, are the Teleop buttons grey, with a line that says the page on desk has control? (yes / no) On the desktop, press the \` key to leave desktop control. → can you press the Newline's buttons again? (yes / no)
- **U.8** In the Quest, open the hub in VR, then **Teleop**. Hold the grip, then press **A**. → does the panel say "Stopped", with "Let go of the grip, then grab again" under it? (yes / no) Let go of the grip. → does the panel change to "Holding" at once, without a new grab? (yes / no)
- **U.9** Quick job 60. Open the hub in VR (the Quest on its USB cable). → is the hub easy to read, and does all of it still fit when you turn your head a little? (yes / no) Point at ⚙ (beside ⏻) and pull the trigger. → does Settings open, with This Device first? (yes / no)
- **U.10** In Settings → This Device, switch **Sound** off, then on again. → does the line at the bottom say "Saved"? (yes / no) Press **B**. → does Settings close? (yes / no)
- **U.11** Quick job 63. Plug in `so101-white` and its two cameras (sockets 7 and 8). Open Teleop on the desktop. → under the joint angles, do you see the stand and the wrist picture, moving? (yes / no) Close Teleop and wait 10 seconds. Start LeLab's camera view of the green set (it uses the same sockets). Open Teleop again. → does each picture say that the camera is in use? (yes / no)
- **U.12** Quick job 49. Connect the Quest by USB. On the desktop's hub, press the Quest view button. Close the window with its own X. → does the button go dark within a second or two? (yes / no) Press it once. → does the window open again? (yes / no)
- **U.13** Quick job 50. Keep a hand at STOP. With `so101-white` and AI Control open, ask the hub's assistant "move the arm to home" (⚙ → Robots → The Assistant May Move the Arm on). → does AI Control show the move without "clipped"? (yes / no) → is the arm folded where it was before? (yes / no)
- **U.14** Quick job 51. Keep a hand at STOP. Put the cube about 20 cm straight in front of `so101-white`. Ask the hub's assistant "Jarvis, hand me the cube". → when the jaws closed, did they hold the cube with most of their length, not only the tips? (yes / no) Did the gripper touch the table? (yes / no)
- **U.15** Quick job 52. Keep a hand at STOP. Clear the space to the right of `so101-white` and above it. On the desktop's hub, say `Hey Jarvis, it's demo time`, then tap **Ask me to wave**. → does it look like a wave from where the visitors stand? (yes / no) Did the arm touch anything? (yes / no) Say `Hey Jarvis, the visitors have left`.
- **U.16** In the hub in VR, point at ⏻ (top right) and pull the trigger. → does a menu open with "Back to the start screen" and "Exit"? (yes / no) Open **Teleop**, then press ⏻ beside ← on its tab, then **Exit**. → are you back on the browser page? (yes / no)
- **U.17** In the Quest's browser, open the hub's address. → do you see three choices in the middle (Enter VR, Enter AR, the hub in the browser)? (yes / no) Press **Enter AR**, start, then **Teleop**. → does the Teleop page open, with Desktop control grey? (yes / no)
- **U.18** On the Teleop page, select 1:1, then **Enter AR**. Drive the fake arm. → does it work? (yes / no) Leave AR, then press **Back to the hub in AR**. → are you back at the hub in AR? (yes / no) In the browser's menu, is there an Install choice? (yes / no)

## K. The Teleop page's buttons (5 min)
Quick job 87. Use the lab desktop's Chrome with the **Immersive Web Emulator** extension switched on.
- **K.1** Open Teleop. → are the buttons in this order: **Desktop control**, **Enter AR**, **Enter VR**? (yes / no) Can you click **Desktop control**? (yes / no)
- **K.2** Look under the buttons. → is there a **Controls** box with the speed, Hand → arm and the desktop keys? (yes / no)
- **K.3** In the Quest's browser, open Teleop. → is **Desktop control** grey? (yes / no)

## Optional: raspbot1 on a phone hotspot (10 min)
Setup: connect to the Raspbot with a cable. Set the phone hotspot's security to **WPA2-Personal**.
- **R.1** On the Raspbot, run `sudo nmcli dev wifi connect "<hotspot name>" password "<password>"`. → did it connect? (yes / no; if no, copy the error line)
- **R.2** Run `sudo nmcli con up Raspbot`. → nothing to report.
