# Lab checklist: the demo run

Before the demo on 2026-12-03, check only what the demo shows, once, in the order of the demo. Everything else (edge cases, errors, the details of each feature) is in `docs/guides/lab-checklist-after-demo.md`, for after the demo.

Every step has a tag (for example **H.2**). The line after **→** says what to report. Report as `H.2: yes`. Run the commands in a terminal on the lab desktop, in `~/lab-os`. The hub is at `http://192.168.8.130:8080` on the router's Wi-Fi. Each part works alone.

**Report problems in one line each, after "Also,".** A problem that does not stop the demo becomes a job for after the demo. When a step passes, it is removed.

**Order.** Tuesday 2026-12-01: 0, then the parts below, then a practice run of the whole demo. The steps that passed on 2026-11-24 are removed (`docs/plan/log.md`, 2026-11-25). The quick jobs since then add their steps here.

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

## How to write a step (for the sessions that add steps)
- Before the demo, add a step here only when a job changes a moment of the demo run. Put every other step (edge cases, errors, details) in `docs/guides/lab-checklist-after-demo.md`.
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

## 0. Update (10 min)
```bash
cd ~/lab-os
git switch main && git pull
uv sync --extra so101
uv run pytest -q
```
- **0.1** Read the last line that `pytest` shows. → copy the line.

## P. Plug in every USB device (15 min)
Quick job 115. Do this part before every other part. Setup: no brain running. Follow `docs/guides/plug-in.md` → "The plan" and steps 1 and 2 of "The order". Put the card reader and the webcam on the Windows desktop.
- **P.1** Run `uv run lab-os usb`. → copy the output.
- **P.2** Unplug the white wrist camera. Run `uv run lab-os usb` again. Plug the camera in again. → which name went from the list? Is there a line that starts with `!`? (yes / no)
- **P.3** Run `uv run --extra so101 lab-os serve --host 0.0.0.0`. → copy the line that starts with "Plugged in". Open the Cameras page. Is each picture under the correct name (the wrist camera looks along the jaws)? (yes / no, for each camera)
- **P.4** Sit in the chair. Say "(wake word), what time is it?" 3 times, in a normal voice. → how many times did it answer? (0 to 3)
- **P.5** Stop the brain (Ctrl+C). Unplug the USB cables of the two green arms. Start the brain as in P.3. → does the line that starts with "Plugged in" name only `so101-white`? (yes / no)

## S. The start and the voice (10 min)
Setup: no brain running, every hub window closed, the USB microphone in the desktop's front port. Quick jobs 110 and 111 add their steps here.

- **S.1** Quick job 110. Start the brain: `uv run lab-os serve`. Open `http://localhost:8080` and tap the start screen. Set ⚙ → This device → **Talking to It** to **wake word**. Say "(wake word), what time is it?" in a normal voice. → did the hub start to think less than 1 s after your last word? (yes / no: about how long)
- **S.2** Say "(wake word), calculate 37 times 48". Stop for about 1 s. Then say "then add 199". → did it wait for "then add 199"? (yes / no) Did it say 1975? (yes / no)
- **S.3** Quick job 111. Say "(wake word), tell me three short facts about robot arms". Listen to the full answer. → was the speed normal, not too fast? (yes / no) Did you hear the start and the end of each word? (yes / no: which word was cut) Was there a short pause between the sentences? (yes / no)

## H. The AI moves the arm: "Hand me the cube" (15 min)
How it works: `docs/archive/guides-2026-11-25/hub.md` → "The assistant moves the arm". Plug in `so101-white` (its USB cable and its power supply) and its two cameras, on its USB hub (`docs/guides/plug-in.md`). Open Monitor on your phone (`http://192.168.8.130:8080/monitor`) for its STOP. Keep a hand on it while the arm has power.
- **H.1** Quick job 118. Select ⚙ → Robots → **The Assistant May Move the Arm**. Say "(wake word), move the arm to ready". → did the arm go to `ready`? (yes / no) Did it start slowly and slow down at the end? (yes / no: what was wrong)
- **H.2** Quick job 117. Put the blue cube about 20 cm straight in front of the arm. Say "(wake word), hand me the cube". → did the arm pick it up and hold it out to you? (yes / no / it missed) Say "let go". → did the gripper open? (yes / no) Do it again with the cube to the side of the arm. → did it pick it up? (yes / no: what it said)
- **H.3** Ask for the cube again. While the arm moves, press STOP on the phone. → did the arm stop at once? (yes / no) Say "(wake word), move the arm to home". → did it go home? (yes / no)

## W. Teleop with a webcam (10 min)
Put the Logitech C615 on top of the desktop's monitor, in a free USB socket. Plug in `so101-white`. Run `uv run --extra so101 lab-os serve --speed 0.3`. **X** is STOP on the webcam page.
- **W.1** Quick job 120. Open `http://localhost:8080/webcam`. Click **Start webcam control**. Hold Space and move your right hand slowly. → did the arm follow your hand? (yes / no) Can you close the gripper and keep it closed while you move? (yes / no) Is it good enough to show? (yes / no: what is wrong)

## T. The Quest: one arm, then two (10 min)
Stop LeLab and any training run first. Plug in `so101-white` and `so101-green` (each its USB cable and power supply). Run `uv run --extra so101 lab-os serve --host 0.0.0.0 --speed 0.3`. The Quest is on the router's Wi-Fi. Quick jobs 119 and 121 add their steps here.
- **T.1** Quick job 114. On the Quest, open the hub, **Enter VR**, then **Teleop**. Hold the right grip and move the arm a little. Put both controllers down on the table and hold your hands up in view. → did the arm stay still? (yes / no) Pick up the controllers. Select **Options**, then **Hand → Arm** → **Hands**. Hold a left pinch and move the right hand. → did the arm follow? (yes / no) Select **Relative**. Set **Switch to Hands by Itself** to **On**, and put the controllers down. → did the hands drive without a choice? (yes / no) Set it back to **Off**.

## R. The Raspbot (10 min)
raspbot1 on the router's Wi-Fi, charged, on the floor with space around it. Steps: `docs/guides/raspbot.md`. Run `uv run lab-os raspbot deploy`, then `uv run lab-os serve`.
- **R.3** Quick job 122. On the Quest, open the hub, **Enter VR**, then **Raspbot**. Press **PICTURE**, then **RECORD**. Wait 5 s, then press **END REC**. → did the status line give two file names? (yes / no) On the desktop, open the recording. → does it play 5 s of video? (yes / no)

## L. The Newline (10 min)
The Newline is a screen of the Pi that drives it (HDMI and the USB touch cable). On 2026-11-24, `arecord -l` on the Pi listed the Newline's microphone ("Newline Q Pro Elite", card 2), through the touch cable.
- **L.2** On the Pi, open `chrome://flags`, search for "Insecure origins treated as secure", type `http://192.168.8.130:8080`, select Enabled, then Relaunch. Open `http://192.168.8.130:8080/design?device=newline`. In Chrome's site settings for the hub, select the Newline microphone. Stand 2 m in front of the Newline and say "(wake word), what time is it?". → did it answer? (yes / no) Did you need a raised voice? (yes / no)

## A. More to show (20 min)
Each step checks one more moment of the demo, once. Plug in `so101-white` (its USB cable and its power supply) and its two cameras, on its USB hub (`docs/guides/plug-in.md`). Run `uv run --extra so101 lab-os serve --host 0.0.0.0 --speed 0.3`. Keep a hand at STOP on your phone (Monitor).
- **A.1** Quick job 113. Plug the USB card reader into the lab desktop. Press ⏻ → **Back to the start screen**. Click on another window, so that the hub does not have the focus. Swipe your student ID. → did the hub start, with "Card read" and its own sound? (yes / no)
- **A.2** Quick job 115. Do this once with `so101-white`, then once with only `so101-green` plugged in. Say "(wake word), it's demo time". Tap **Ask me to wave**. → did the arm wave? (yes / no, for each arm) Say "(wake word), the visitors have left".
- **A.4** Quick job 109. Open **All Pages** → **Cameras**. Plug in the webcam. → did it show within a few seconds? (yes / no) → does each camera show under the right arm's name? (yes / no: which is wrong)
- **A.7** Quick job 109. Plug in the card reader. → is it in the Devices panel within 5 s, as "Unknown" with its maker's name? (yes / no) Press **Remove** on its card. Ask "(wake word), which devices are connected?". → did the answer name only the devices that are plugged in? (yes / no: what was wrong)
- **A.6** LeRobot teleop with Rerun (fixed on 2026-11-24, PRs #273 to #275). Press Ctrl+C in the brain's terminal (hold the arm first). Stop LeLab. Plug in both green arms and their two cameras. Run `uv run --extra so101 lab-os serve --arm fake`. Open **Training**. Put the leader and the follower in the same pose, and press **Start** in "LeRobot teleop with Rerun". → did Rerun open in its own window, with the camera pictures and the joints? (yes / no) Does the follower follow the leader? (yes / no) Hold the follower, then press **Stop**.

## M. Every screen in the room (15 min)
The plan for the demo: `docs/plan/current-focus.md` → item 10. Each computer must be on the router: its Wi-Fi, or a cable to the big switch. A computer on the campus network cannot reach the hub at `192.168.8.130`. Open the hub on each computer as on 2026-11-24 (`/design?device=<its name>`).
- **M.2** Quick job 112. On each Windows desktop, say "(wake word), what time is it?". → did it answer the question? (yes / no: what it said)
- **M.3** Quick job 109. On the desktop's hub, open the Devices panel's details. Unplug the white arm's USB cable. → did "Connected" change to "No" within 5 s? (yes / no) Plug it in again. → did it change to "Yes", with the motor power "On"? (yes / no) Close the hub on one computer. → did that screen change to "No"? (yes / no)
