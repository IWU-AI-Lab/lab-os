# Lab checklist

Every step has a tag (for example **9.4**). The line after **→** says what to report. Report as `9.4: yes` or `9.4: 6 s`. Run the commands in a terminal on the lab desktop, in `~/lab-os`. Each part works alone.

This list has only what is still to do. When a step is done, it is removed (its result goes to `docs/dev/GOTCHAS.md` or `docs/plan/quick-jobs.md`).

**Order for Thursday 2026-11-19.** The AI club starts between 2:50 and 3:00 pm. Before that time, do the parts that need sound or a quiet room: 0, 9, 2, S, then F.11 and F.6 (about 90 min). After that time, do the rest of F, then 3b and 11.

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

---

## 0. Update (5 min)
```bash
cd ~/lab-os
git switch main && git pull
uv sync --extra so101
uv run pytest -q
```
- **0.1** Read the last line that `pytest` shows. → copy the line.

## Before the AI club: sound and voice

## 9. Voice on the desktop (20 min)
Setup: plug in the USB microphone and select it in Ubuntu Settings → Sound → Input. Switch the speakers on. Then run:
```bash
uv run lab-os serve --persona jarvis --host 0.0.0.0
```
Open http://localhost:8080/design in Chrome. Press start. Keep the terminal in view. Keep this brain running for parts 2 and S.
- **9.1** Listen to the greeting. → did it speak? (yes / no)
- **9.2** Press ⏻. Wait 10 seconds. Press start again. → did the greeting start immediately? (yes / no)
- **9.3** Hold the mic button. Say "What's the next step?". Release the button. Count the seconds until the first spoken word. → seconds.
- **9.4** Select ⚙ → This Device → Talking to It → **Wake Word**, then Back. Say "Hey Jarvis, what's the next step" in one breath. → was the start of your question missing on the screen? (yes / no)
- **9.5** Do 9.4 two more times. → copy the three `voice timing` lines from the terminal.
- **9.6** Walk backwards one step at a time. At each step, say "Hey Jarvis". Stop when it does not hear you. → the number of steps from the microphone.
- **9.7** At that position, select ⚙ → This Device → Wake Word Sensitivity → 7 and try. Then try 8. → the lowest of 5, 7 and 8 that works there.
- **9.8** At that sensitivity, talk normally near the microphone for one minute. Say "Jarvis" once inside a sentence. → how many times did it wake by mistake?
- **9.9** Say "Hey Jarvis, pull up the teleop page." → did Teleop open? (yes / no)
- **9.10** Say "Hey Jarvis, show me the AI spend." → did the AI Spend page open? (yes / no)
- **9.11** Say "Hey Jarvis, go back to the hub." → did everything close? (yes / no)
- **9.12** Type in the ask line: `show me the commits`. → did the Commits page open? (yes / no)
- **9.13** (quick job 33) Select ⚙ → This Device → Assistant Language → Listens: English, Answers: English, then Back. Say "Hey Jarvis, what's the next step?" two times. → did it answer in English both times? (yes / no)
- **9.14** Type in the ask line: `¿Cuál es el siguiente paso?` → did it answer in English? (yes / no) Then set Answers back to Any.

## 2. The Newline as JARVIS's screen (35 min)
Setup for 2.1 to 2.4: connect the desktop to the Newline with an Ethernet cable. Use the brain from part 9. The desktop's address is the first one that `hostname -I` shows.
- **2.1** In the Newline's Chrome, open `chrome://flags` and search for "Insecure origins treated as secure". Type `http://<address>:8080`, select Enabled, then Relaunch. Open `http://<address>:8080/design?device=newline` and press start. → is there a mic button next to "Ask anything"? (yes / no)
- **2.2** Hold the mic button and ask a question. → did it hear you and answer? (yes / no)
- **2.3** Select ⚙ → This Device → Drawing Resolution → 1. Press ⏻, then start. → is the startup smooth? (yes / no)
- **2.4** Do the same with Drawing Resolution 0.5. → is the startup smooth? (yes / no) Is it too blurry? (yes / no)
- **2.5** Connect the desktop to the Newline's HDMI. In Ubuntu Settings → Displays, select the Newline and 1920×1080. → the refresh rate that it shows, in Hz.
- **2.6** In the Newline's own picture menu, find a "PC" or "Game" mode and switch it on. → the name of the mode, or "none found".
- **2.7** Open http://localhost:8080/design on the Newline's screen and press start. → is the startup smooth at 1920×1080? (yes / no)
- **2.8** In Ubuntu Settings → Displays, select 1600×900 for the Newline. Press ⏻, then start. → is the startup smooth? (yes / no) Stand 3 m from the Newline. → can you read the hub's text? (yes / no)
- **2.9** In Ubuntu Settings → Sound → Output, select the Newline (HDMI). Hold the mic button and ask a question. → did the answer come from the Newline's speakers? (yes / no) Is it loud enough for the room? (yes / no) Then select the desktop's speakers again.
- **2.10** Find the Newline's USB "Touch" socket, next to its HDMI sockets. If you find it, connect it to the desktop with a USB cable. If no socket on the desktop is free, disconnect the xArm's cable (never a green arm's cable while LeLab runs). Tap the hub on the Newline. → does touch work on the desktop's hub? (yes / no / no touch socket) Then connect the xArm again.
- **2.11** Compare the two ways: the Newline's own Chrome (2.1 to 2.4) and HDMI from the desktop (2.5 to 2.10). → which is better as JARVIS's screen, and why? (a few words)

## S. The room's ceiling speakers (15 min)
Setup: your laptop with its charger, and the brain from part 9. Do not change settings on the classroom's computer. Change only the input on the audio panel, and set it back when you finish.
- **S.1** Find the classroom computer station (the teaching computer that connects to the projector). Find its audio controls: a wall panel or a box with input buttons (for example "PC", "Laptop", "HDMI" or "Aux") and a volume knob. → what do the buttons say? (a photo is good)
- **S.2** Find a cable for a guest laptop at the station: HDMI, or a 3.5 mm audio plug. Look also at the walls and the floor boxes for an audio plate. → what did you find, and where?
- **S.3** Set your laptop's volume low. Connect the laptop to the guest cable from S.2. Select that input on the panel. Play a sound on the laptop. → does the sound come from the ceiling speakers? (yes / no)
- **S.4** If yes: on the desktop, run `hostname -I` and use the first address. On the laptop's Chrome, open `http://<address>:8080/design?device=laptop`. Press start. → did the page load? (yes / no) Does the startup sound come from the ceiling? (yes / no) Can you hear the greeting clearly everywhere in the room? (yes / no)
- **S.5** Set the panel back to its first input. Disconnect the laptop. → nothing to report.

## F. This week's fixes on the real arm (55 min)
Setup: plug in `so101-white` and its two cameras. Unplug the green arms. Then run:
```bash
uv run --extra so101 lab-os serve --arm so101-white --speed 0.3 --host 0.0.0.0
```
Open a **new** Claude Code session in `~/lab-os`. Type `/mcp`, select `lab-os`, then "reconnect".

Do F.11 and F.6 first, before the club starts: they need sound. Do the other steps after the club starts.

- **F.11** (quick job 35) Keep a hand at STOP. Put the arm at `ready` or `home`. On the desktop's hub (`/design?device=desk`), say `Hey Jarvis, it's demo time`. → five answers: does the strip show the venue `visit-day`? Does it speak a welcome that names the white SO-101 arm? Are the cards above the core? Is AI Spend gone? Does ⚙ show only Visitor Mode? (yes / no each) Tap **Ask me to wave**. → did the arm go to `ready` and wave (the shoulder a little, the wrist nodding) without touching anything? (yes / no) Say `Hey Jarvis, wave at everyone` and press STOP during the wave. → did it stop? (yes / no) Use teleop 1:1 from the Quest in visitor mode. → does it work as in the lab? (yes / no) Say `Hey Jarvis, the visitors have left`. → is the venue `lab` again, and is AI Spend back? (yes / no) Select ⚙ → Start Visitor Mode, then ⚙ → Exit Visitor Mode. → did both work? (yes / no)
- **F.6** (the Quest's wake word) Connect the Quest with USB and run `adb reverse tcp:8080 tcp:8080`. In the Quest's browser, open `http://localhost:8080/design?device=quest-a`. Select ⚙ → This Device → Wake Word Sensitivity → 7. Open `http://localhost:8080/xr` and select Enter VR. Say "Hey Jarvis" 10 times, with pauses. → the number of misses.
- **F.1** (quick job 29) Prompt: `Use the lab-os tools. Take a picture with so101-white-cam-wrist.` → does the picture show the view along the jaws? (yes / no)
- **F.2** (quick job 28) Open http://localhost:8080/teleop and select Desktop control. Move the gripper down slowly until the jaw tips touch the table. Read the gripper's z on http://localhost:8080/ai. → z ___ cm. It should be about 0. If it is not, change `table_z_cm` of `so101-white` in `config/devices.yaml` by that amount (for example, z 0.3 → −1.3). The floor (1.1 cm above the table) can stop the gripper before the tips touch. Then write the lowest z, and how far the tips are from the table.
- **F.3** (quick job 30) Keep a hand at STOP. Prompt: `Go to the home pose.` (it takes three or four moves). → did the arm fold to almost the position where you usually leave it, with the gripper a little above its rest, without hitting anything? (yes / no; how high are the jaw tips above the table? ___ cm)
- **F.4** (quick job 27) Open http://localhost:8080/design and select Teleop. Unplug the arm's USB cable. → after a few seconds, does the hub show the arm as disconnected? (yes / no)
- **F.5** Plug the cable in again. Wait 10 seconds. The terminal should say `so101-white reconnected`. In Desktop control, release the keys, then move a joint. → did the arm move? (yes / no; copy any line that the terminal shows again and again)
- **F.7** (quick job 32) During the other steps, keep the designed hub open on the desktop. Look at the brain's terminal now and then. → did the strip show "AI not connected" at any time? (yes / no; copy any line that starts with `AI:` or `internet:`)
- **F.8** (quick job 34) On the desktop's hub (`/design?device=desk`), press ⏻ and start 3 times. Look at the core. Then select ⚙ → This Device → **Startup as a Video** → on, and press Back. Press ⏻ and start 3 times again. → which was smoother: drawn, video, or the same? Did the picture jump when the video changed to the live hub? Then do the same with ⚙ → This Device → Level of Detail → **Maximal** (it has its own recording): drawn or video? Then set both back.
- **F.9** (quick job 6) Hold the arm. Prompt: `Go to the ready pose.` On the desktop's hub (`/design?device=desk`), press ⏻ → **Shut down lab-os**. → does the confirmation say that so101-white goes limp? (yes / no) Hold the arm and press **Shut down**. → three answers: did the arm go limp in your hand? Did the terminal say `lab-os was shut down from the hub; so101-white was let go.`? Did every open page (also the Quest's, if open) say "lab-os is off"? (yes / no each) Start lab-os again with the "Start lab-os" icon. → did the pages come back by themselves? (yes / no)
- **F.10** (quick job 10) Connect the Quest with USB and run `adb reverse tcp:8080 tcp:8080`. In its browser, open `http://localhost:8080/xr` and select **Enter AR**. On the start screen, look straight ahead, past the circle. → do you still see a dark cluster of lines? (yes / no) Start it. → do the stars and the network look like light over the room, with no dark spots or lines? (yes / no) Press ⏻ once and look again. → cluster? (yes / no)
- **F.12** (quick job 36) Once, in a terminal in `~/lab-os`, run `uv run lab-os quest-view --install`. Reload the brain's hub page. Connect the Quest with USB (`adb devices` shows it as `device`) and open the teleop page or the VR hub in it. On the desktop's hub, press the Quest view button in the strip (the screen-with-goggles icon). → does a window open with what the headset sees, without flicker? (yes / no) → is teleop still smooth while the window is open, and does `adb reverse --list` still show `tcp:8080 tcp:8080`? (yes / no) → does the window show both eyes side by side, or one? For one eye, add `mirror: ["--crop=2064:2208:0:0"]` under `quest-a` in `config/devices.yaml`, and press the button two times. Write the crop that looks correct: ___. Press the button again. → did the window close? (yes / no)
- **F.13** (quick job 37) Connect the Quest with USB and run `adb reverse tcp:8080 tcp:8080`. In its browser, open `http://localhost:8080/xr`, select Enter VR, then Teleop. Look at the status panel to the right of the arm. → is it in the hub's style (cut corners, cyan, the numbers in the clock's digits), and easy to read quickly? (yes / no) Hold the grip. → does it show green "Following"? Release the grip. → "Holding"? Put a controller down. → amber "No controller"? (yes / no) Leave VR, select **Enter AR**, then Teleop. → is it still easy to read over the room? (yes / no)
- **F.14** (quick job 38) Hold the arm (it goes limp for a moment). On the desktop's hub, open ⚙. → is each group easy to find (sidebar, folding), and is every value lined up on the right? (yes / no) In Robots → Top Speed, change the number by 0.05, then change it back. → do you see "✓ Saved" each time, and the amber bar with Restart Now? (yes / no) Press Restart Now, then Restart. → does every screen say "lab-os is restarting" and come back by itself in about 15 s, with the arm connected again? (yes / no)
- To finish: hold the arm, then press Ctrl+C in the brain's terminal.

---

## After the club starts: no sound needed

## 3b. The stand camera's cm grid (15 min)
Setup: plug in `so101-white` and its stand camera. Print `models/charuco/calibration-sheet-letter.pdf` with the printer at **100 % ("Actual size")**, not "Fit to page". Then run:
```bash
uv run --extra so101 lab-os serve --arm so101-white --speed 0.3
```
- **3b.1** Put the sheet flat in front of the arm, with the long edge pointing straight away from the arm, approximately in the center. On `http://localhost:8080/teleop`, move the gripper with the keyboard until the jaw tips touch the sheet's **"Board origin"** corner (top left, seen from the arm). Read the gripper's x and y on the AI Control page (`/ai`). → x ___ cm, y ___ cm
- **3b.2** Move the arm up and to the side, so that it covers no part of the sheet. In a second terminal, run `uv run --extra so101 lab-os table-map so101-white-cam-stand --origin <x> <y>` (with the numbers from 3b.1). → corners seen: ___ of 24; worst: ___ mm (or the error that it shows)
- **3b.3** Open the picture that it names (`logs/table-maps/…jpg`). → is the red dot on the arm's base? (yes / no / not in the picture) Do the grid lines follow the sheet's squares? (yes / no)
- **3b.4** Remove the sheet. Put the cube anywhere in front of the arm. Start a new Claude Code session (`/mcp` → `lab-os` → reconnect). Prompt: `Use the lab-os tools. Take a picture with so101-white-cam-stand and tell me where the cube is, in cm. Then move the gripper to 3 cm above that spot, pointing straight down.` → what did it say? ___ Is the gripper above the cube? (yes / no: about ___ cube-widths off, in which direction ___)
- **3b.5** In the same session, prompt: `Pick it up with pick_at, then tell me whether you're holding it.` Look at `/ai`. → is the cube in the jaws? (yes / no) Did it say "holding" or "missed"? Did `/ai` show each step before the arm moved? (yes / no)

## 11. Devices (30 min)
Setup: the desktop and the Newline (or a laptop instead of the Newline). No arm.
- **11.1** Stop any brain that runs (Ctrl+C). Run `uv run lab-os icon --device desk`. In Ubuntu's app list, click **Start lab-os**. → did a terminal and a full-screen hub open? (yes / no)
- **11.2** Look at the hub's address. → does it have `?device=desk` in it? (yes / no)
- **11.3** Click **Start lab-os** again. → did a second brain start? (yes / no)
- **11.4** On the desktop, run `hostname -I` and use the first address. In the Newline's Chrome, open `http://<address>:8080/?device=newline`. → did the page load? (yes / no)
- **11.5** On the Newline, select ⚙ → This Device → Drawing Resolution → 0.5. On the desktop, run `cat ~/lab-os/config/hub-devices.yaml`. → does it show `newline:` with `res: '0.5'`? (yes / no)
- **11.6** On the Newline, select Chrome's menu → Add to Home screen. Close Chrome. Tap the new icon. Open ⚙. → does it say "This Device: newline"? (yes / no)
- **11.7** On the Newline, open Monitor → **Open on…** → **desk**. → did Monitor open on the desk? (yes / no)
- **11.8** Look at the Newline. → does it say "Monitor is on desk"? (yes / no)
- **11.9** On the desk, press **Back**. → did Monitor close on the desk, and did the line go away on the Newline? (yes / no)
- **11.10** On the Newline, select Monitor → Open on… → desk. Then, on the Newline, press **Bring it back**. → did Monitor come back to the Newline? (yes / no)
- **11.11** On the desk, open Teleop → Open on… → **newline**. → did Teleop open on the Newline? (yes / no)
- **11.12** Send Monitor to the desk again. Press Ctrl+C in the brain's terminal. Wait 10 seconds. Click **Start lab-os**. → did both hubs come back without a reload? (yes / no) After how many seconds?
- **11.13** Shut down the desktop and switch off the Newline. Switch both on. Click **Start lab-os**, then tap the Newline's icon. → are both back under their names, with the Newline's resolution still 0.5? (yes / no)

## Optional: raspbot1 on a phone hotspot (10 min)
Setup: connect to the Raspbot with a cable. Set the phone hotspot's security to **WPA2-Personal**.
- **R.1** On the Raspbot, run `sudo nmcli dev wifi connect "<hotspot name>" password "<password>"`. → did it connect? (yes / no; if no, copy the error line)
- **R.2** Run `sudo nmcli con up Raspbot`. → nothing to report.
