# Lab checklist: the demo run

Before the demo on 2026-12-03, check only what the demo shows, once, in the order of the demo. Everything else (edge cases, errors, the details of each feature) is in `docs/guides/lab-checklist-after-demo.md`, for after the demo.

Every step has a tag (for example **H.2**). The line after **→** says what to report. Report as `H.2: yes`. Run the commands in a terminal on the lab desktop, in `~/lab-os`. The hub is at `http://192.168.8.130:8080` on the router's Wi-Fi. Each part works alone.

**Report problems in one line each, after "Also,".** A problem that does not stop the demo becomes a job for after the demo. When a step passes, it is removed.

**Order.** Tuesday 2026-11-24: 0, S, H, G, W, T, R, L, M. Tuesday 2026-12-01: 0, then a practice run of the whole demo.

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

## S. The start and the voice (25 min)
Setup: no brain running, every hub window closed, the USB microphone in the desktop's front port.
- **S.1** On the lab desktop, click the **Start lab-os** icon. When the start screen shows, click it. → did the hub open full screen, with the startup's sound and a spoken greeting? (yes / no)
- **S.2** Say "(wake word), what time is it?". → did it answer aloud? (yes / no) Type a question in the ask line. → did it answer? (yes / no)
- **S.3** Quick job 98. Say fast, in one breath: "(wake word), how many minutes does a 1200 km flight take at 850 km per hour?" → did it hear the whole question? (yes / no) Say "(wake word), calculate 37 times 48," stop for one breath, then say "then add 199". → did it say 1975? (yes / no) → did the answer start about 2 s after you stopped? (yes / slower: how many seconds?)
- **S.4** Quick job 99. On the desktop, open All Pages → **Wake Word**. Select the active word. Record 8 tries in the tones the page shows, and 20 s of talk. Press **Train**. → copy the result line. Say "(wake word), what time is it?" 5 times, with a new tone each time (once like a question). → how many times did it answer? (0 to 5)
- **S.5** Quick job 100. Say "(wake word), hi". → was the voice male for J.A.R.V.I.S. or female for the Lab Assistant? (yes / no) → did J.A.R.V.I.S. have a British accent? (yes / no) → did the answer talk about the language, such as "I'll answer in English"? (no / yes: the words) In ⚙ → Assistant, change the persona. Say "(wake word), hi" again. → was the greeting and the answer in the other persona's voice? (yes / no)
- **S.6** Quick job 104. Open ⚙ on the hub. Type "wake" in the search bar at the top. → did only the wake word settings show? (yes / no) Empty the bar. → did all the settings show again? (yes / no)

## H. The AI moves the arm: "Hand me the cube" (15 min)
How it works: `docs/guides/hub.md` → "The assistant moves the arm". Plug in `so101-white` (its USB cable and its power supply) and its stand camera (socket 8). Open Monitor on your phone (`http://192.168.8.130:8080/monitor`) for its STOP. Keep a hand on it while the arm has power.
- **H.1** Select ⚙ → Robots → **The Assistant May Move the Arm**. Say "(wake word), move the arm to ready". → did the arm go to `ready`? (yes / no)
- **H.2** Put the blue cube about 20 cm straight in front of the arm. Say "(wake word), hand me the cube". → did the arm pick it up and hold it out to you? (yes / no / it missed) Say "let go". → did the gripper open? (yes / no)
- **H.3** Ask for the cube again. While the arm moves, press STOP on the phone. → did the arm stop at once? (yes / no) Say "(wake word), move the arm to home". → did it go home? (yes / no)

## G. Tic-tac-toe (30 min)
Claude Code plays against you with `so101-white`. Set up as in `docs/guides/tic-tac-toe.md` (the printed sheet, the pieces, the stand camera). Run `uv run --extra so101 lab-os serve --speed 0.3`.
- **G.0** Quick job 106. Do this first. Make the stand camera's map again: follow `docs/guides/ai-control.md` → "Table map", steps 1 to 5 (the printed sheet). → did it find 20 or more corners, with the worst 5 mm or less? (yes / no) Put the paper board back where the Board drawing (G.1) shows it.
- **G.1** Open the Cameras page. Press **Board** on the stand camera's picture. → do the magenta squares sit on the printed lines? (yes / no) Put the 5 red pieces in the green rings while you watch. → was each place easy to find? (yes / no: which ring)
- **G.2** In Claude Code, type the prompts in sections 4 and 5 of the guide. Play one game to the end. → did the AI read the board right each time? (yes / no: which turn) Did each red piece go inside its cell? (yes / no) About how many minutes did the game take?
- **G.3** Quick job 106. Put a red piece in ring 3. In Claude Code, type "pick up the piece at start spot 3 with pick_at, then lift it". → did the jaws close around the middle of the piece? (yes / no: above it, beside it) Did the jaw tips touch the table? (yes / no)

## W. Teleop with a webcam (10 min)
Put the Logitech C615 on top of the desktop's monitor, in a free USB socket. Plug in `so101-white`. Run `uv run --extra so101 lab-os serve --speed 0.3`. **X** is STOP on the webcam page.
- **W.1** Open `http://localhost:8080/webcam`. Click **Start webcam control**. Hold Space and move your right hand slowly. → did the arm follow your hand? (yes / no) Is it good enough to show? (yes / no: what is wrong)

## T. The Quest: one arm, then two (20 min)
Stop LeLab and any training run first. Plug in `so101-white` and `so101-green` (each its USB cable and power supply). Run `uv run --extra so101 lab-os serve --speed 0.3`. The Quest is on the router's Wi-Fi.
- **T.1** On the Quest, open the hub, then **Enter VR**, then **Teleop**. Hold the right grip and move your hand. → did `so101-white` follow? (yes / no) Hold the left grip and move your hand. → did `so101-green` follow? (yes / no)
- **T.2** Hold both grips and move both hands slowly. → did both arms follow, each with its own hand? (yes / no) Is it good enough to show? (yes / no: what is wrong)
- **T.3** Quick job 102. In the hub in VR, open **Teleop**. Point the right controller at **OPTIONS** under the status box, then pull the trigger. Press **+** for the speed and select **1:1**, then **Relative**. → did each change at once? (yes / no) Point at **BACK** and pull the trigger. → are you back on the hub? (yes / no) Open Teleop again in AR, put the controllers down, then point your right hand at **EXIT** and pinch. → did it leave AR? (yes / no)
- **T.4** Quick job 103. Connect the Quest by USB. On the brain's computer, run `uv run lab-os quest-view --wifi`. → did it say "ready on Wi-Fi"? (yes / no: what did it say?) Unplug the cable, then press the Quest view button in the hub's strip. → did the window show what the Quest sees? (yes / no) Is it smooth enough to show? (yes / no)

## R. The Raspbot (10 min)
raspbot1 on the router's Wi-Fi, charged, on the floor with space around it. Steps: `docs/guides/raspbot.md`.
- **R.1** Run `uv run lab-os raspbot deploy`, then `uv run lab-os serve`. Open **All Pages** → **Raspbot**. Drive it forward, back and in a circle. → did it drive? (yes / no) Did STOP stop it at once? (yes / no) Which speed is good for the demo? (a percentage)

## L. The Newline (10 min)
The Newline is a screen of the Pi that drives it (HDMI and the USB touch cable).
- **L.1** On that Pi, open `http://192.168.8.130:8080/design?device=newline`. Tap to start. → is the startup smooth enough to show? (yes / no) Does a touch land under your finger? (yes / no) Do you hear the greeting from the Newline? (yes / no)
- **L.2** The Newline's microphones through the Pi. Many touch screens give their microphones to the computer on the touch cable. On the Pi, run `arecord -l`. → copy the lines. In the Newline's own settings, look for a choice that shares its microphone or camera with the HDMI or USB source. → is there one? (yes: its name and where / no)

## M. Every screen in the room (30 min)
The plan for the demo: `docs/plan/current-focus.md` → item 10. Each computer must be on the router: its Wi-Fi, or a cable to the big switch. A computer on the campus network cannot reach the hub at `192.168.8.130`.
- **M.1** On each computer that can show a screen (the 2 Windows desktops, the other Ubuntu desktop, each Pi with a screen, the Pi that drives the Newline), open Chrome at `http://192.168.8.130:8080/design?device=<a short name>`. Use names like `win-1`, `win-2`, `ubuntu-2`, `pi-1`, `newline`. → for each: the name, and did the hub load? (yes / no)
- **M.2** On each computer with a USB microphone (the 2 Windows desktops, and a Pi with a USB microphone): open `chrome://flags`, search for "Insecure origins treated as secure", type `http://192.168.8.130:8080`, select Enabled, then Relaunch. → for each: is there a mic button next to "Ask anything"? (yes / no)
- **M.3** On the desktop's hub, open the Devices panel. → how many devices does it list? (a number) Are all names from M.1 there? (yes / no: which are missing?)
- **M.4** Quick job 71. Name the devices as in `config/room.yaml` (newline, win-1, pi-1 …), or edit that file to match. On the desktop, say "(wake word), set up the room". → did each device show its page? (yes / no) Did the answer name the devices that were not on? (yes / no)
- **M.5** On the desktop's hub, open the AI Spend panel's details. Press **Open on…** → the Newline. → did AI Spend open on the Newline? (yes / no) Do the same with the system diagram (the network icon in Devices). → did it open there? (yes / no)
- **M.6** Quick job 96. Open `http://192.168.8.130:8080/design?device=phone` on a phone, held upright. Open the hub on the Pi's touchscreen too. On each, open Teleop, then the Devices details, then Settings. → Did each page fit with no sideways scroll? (yes / no: which page?) Could you press every button with a finger? (yes / no: which button?) Was any text cut off? (no / yes: where?)
- **M.7** Quick job 101. On a Pi, open the hub with no name (`http://192.168.8.130:8080/design?device=`). On the desktop's hub, open AI Spend's details and press **Open on…**. → is the Pi in the list, by its address? (yes / no) Select it. → did AI Spend open on the Pi? (yes / no) On the desktop, press **Open on…** → **Another monitor of this computer**. → did AI Spend open on the other monitor? (yes / no / no other monitor)
