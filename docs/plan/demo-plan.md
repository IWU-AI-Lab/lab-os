# The demo: Thursday 2026-12-03

This page has the setup, the run and the points to say. Many steps are not yet tried in the lab. When a step fails, do the step in **If it fails**, or skip it. The reasons for the choices are in `docs/plan/demo-plan-reasons.md`.

**The room** (north is at the top of the plan; the entrance door is in the south wall):
- **The back:** the north strip, behind the central wall. It has the two Ubuntu desktops, the SO-101 table, the xArm, the routers and the screens on the east wall.
- **The front:** the room south of the central wall. It has the projector on the central wall, the Newline, the four Windows desktops, the four ThinkStations and the seats.

The hub's address is `http://192.168.8.130:8080/?device=<name>`. For a microphone on a computer that is not the brain, use `https://192.168.8.130:8443/?device=<name>`.

## Names and pages
| Device (`?device=`) | Where | Page after "set up the room" |
|---|---|---|
| The lab desktop (the brain): monitor 1 | Back | Command Center |
| The lab desktop: monitor 2 (`desk`) | Back | The hub |
| The lab desktop: monitor 3 | Back | Claude Code, then the Quest's view |
| The other Ubuntu desktop (`ubuntu-2`) | Back | Cameras |
| The screens on the east wall (`east-1` to `east-3`), if they have computers | Back | System Map, Diagnostics, Raspbot Monitor |
| The laptop on the projector (`projector`) | Front | The hub (you control it) |
| The Newline, through its Pi (`newline`) | Front | The hub |
| The Windows desktops (`win-1` to `win-4`) | Front | The hub |
| The ThinkStations (`ts-1` to `ts-4`) | Front | Commits, Current Project, AI Spend, Devices |
| The Pi touchscreen (`pi-touch`) | Beside raspbot1 | Raspbot Control |
| The Quest (`quest`) | Back | The VR hub |
| Your phone | With you | SO-101 Monitor (for its STOP) |

## Tuesday 2026-12-01: prepare
1. Write the layout above into `config/local/room.yaml` on the lab desktop:
   ```yaml
   layout:
     ubuntu-2: cameras
     east-1: system-map
     east-2: diagnostics
     east-3: monitor-raspbot
     newline: core
     win-1: core
     win-2: core
     win-3: core
     win-4: core
     ts-1: commits
     ts-2: project
     ts-3: spend
     ts-4: devices
     pi-touch: raspbot
   ```
2. Find a browser on the laptop that opens the hub with the microphone: the VS Code browser first, then Chrome.
3. Do the whole run below once. Record it with a screen recording and a phone video. Keep the clips as the backups.
4. Record a SmolVLA success on the green arm, if you do not have a video yet.
5. Tag `demo-2026-12-03`, or choose a fallback tag (`docs/plan/log.md`, 2026-11-27).

## Thursday: set up (1:00 – 2:55 pm)
Do not open pages now. Each screen shows only its start screen until the show starts.

**Turn on each device:**
1. Turn on the GL.iNet router.
2. Turn on the lab desktop and its monitors 1, 2 and 3.
3. Turn on the other Ubuntu desktop and its screen.
4. Turn on the computers of the east-wall screens, and the screens.
5. Turn on the laptop. Connect it to the projector's HDMI. Turn on the projector.
6. Turn on the Newline and its Pi.
7. Turn on the four Windows desktops and their screens.
8. Turn on the four ThinkStations and their screens.
9. Turn on the Pi touchscreen. Put it beside the place where raspbot1 drives.
10. Turn on raspbot1.
11. Turn on the Quest. Connect it to the router's Wi-Fi.
12. Turn on the glove xArm station.
13. Plug in the arms, the cameras and the microphone (`docs/guides/plug-in.md`). Turn on the arms' power supplies.
14. Plug the card reader into `win-1` (the room's centre).

**Start the brain** (the lab desktop):
1. Run `git switch --detach demo-2026-12-03` in `~/lab-os`.
2. Run `uv run --extra so101 lab-os serve --host 0.0.0.0 --speed 0.3`.
3. Run `uv run lab-os raspbot deploy`.
4. Open Claude Code on monitor 3. Check that it has the brain's tools (`arm_status`).

**Open the start screen on each screen** (enter the address, then full screen):
1. Open `?device=desk` on monitor 2. Open `/command-center` on monitor 1.
2. Open `?device=ubuntu-2` on the other Ubuntu desktop.
3. Open `?device=east-1`, `east-2` and `east-3` on the east-wall screens.
4. Open `?device=projector` on the laptop (on port 8443, for the microphone).
5. Open `?device=newline` on the Newline's Pi.
6. Open `?device=win-1` to `win-4` on the Windows desktops.
7. Open `?device=ts-1` to `ts-4` on the ThinkStations.
8. Open `?device=pi-touch` on the Pi touchscreen.
9. Open `?device=quest` in the Quest's browser.
10. Open `/monitor/so101` on your phone.

**Set the settings:**
1. On monitor 1, in the Command Center, press **S** on the `projector` card. Only the laptop plays sound (the ceiling speakers).
2. On the brain, select ⚙ → Assistant → Persona → J.A.R.V.I.S.
3. On the brain, select ⚙ → Robots → The Assistant May Move the Arm.
4. On the brain, select ⚙ → Assistant → Full Access.
5. On the brain, check that AI Spend is well under the budget.

**Prepare the props:**
1. Put the blue cube on the SO-101 table.
2. Put the tic-tac-toe grid and the LEGO pieces beside the white arm.
3. Put a box about 1 m in front of raspbot1.
4. Open the SmolVLA success video and the practice clips on the laptop.
5. At 3:25, give Claude Code a small job from the backlog (the live agent).
6. Check that every screen shows its start screen.

## The run (3:30 pm)
**How to ask:** 🎤 = say "hey Jarvis" and the question. ⌨ = type it in the ask line. 🔘 = hold Space on the laptop (push-to-talk). Ask most questions by typing. That is faster, and it does not need a quiet room.

### Part 1: the start (front, 2 min)
1. Press a key on the laptop. Every screen starts. The greeting plays on the ceiling speakers.
   - If it fails: tap each screen that did not start.
2. Say:
   - My name, the AI club, the lab.
   - lab-os: one brain that connects the lab's robots and computers.
   - J.A.R.V.I.S. is its assistant.
   - Every screen in this room started from one key.

### Part 2: why (front, 3 min)
1. Open **System Map** on the projector. Drag to turn it.
2. Open the **System Diagram** (the network icon in the Devices panel).
3. Say:
   - The lab had islands: the glove xArm, the Raspbot's voice control, the green arms' training.
   - Each worked alone. None could talk to another.
   - lab-os: one brain. The robots, the screens, the cameras and the AI connect to it.
   - An AI agent (Claude Code, Codex) can use the brain's tools: read the robots, move them, see through the cameras.
   - Built in 41 days, part-time, mostly by AI agents. More at the end.

### Part 3: talking to it (front, 7 min)
1. 🎤 Ask "what can you do?".
   - If it fails: ask it with 🔘.
2. While it thinks, point at the network: pulses run into the core. While it speaks, they run out.
3. ⌨ Ask "what is the next step of the project?".
4. ⌨ Ask "write a prompt for Claude Code for it". Show the **Copy** button.
5. ⌨ Ask "what is 17 % of 3,400?".
6. 🔘 Ask "give me a status report".
7. 🔘 Ask a long question. Stop the answer with Space.
8. ⌨ Ask "open AI Spend on the Newline".
9. Open **History**.
10. Open ⚙ → Assistant → Persona. Select the Lab Assistant on the round table. Then select J.A.R.V.I.S.
    - If it fails: use the plain persona buttons.
11. Say:
    - It knows the project: it reads the docs, the git history and the device list.
    - It computes with Python. It does not guess numbers.
    - Hard questions go to a stronger model ("Let me think about that").
    - Three ways to talk: push-to-talk, dictation, the wake word.
    - The wake word runs on the brain's own processor. It sends nothing until it hears the word.
    - "Teach it your voice": the Wake Word page learns how you say the word.
    - Conversation mode: it keeps listening until "that's all".
    - Each persona has its own voice and wake word.
    - OpenAI first. Gemini or a local Ollama if OpenAI fails.
    - A monthly budget pauses the chat. The AI Spend page shows the estimated cost.
    - It keeps the conversation for 30 minutes.
    - A phone can be the remote: TALK, or the ask line.

### Part 4: the screens (front, 6 min)
1. 🎤 Say "set up the room". Each screen opens its page.
   - If it fails: on the brain, select ⚙ → The Lab → Set Up the Room.
2. Point at the ThinkStations: Commits, Current Project, AI Spend, Devices.
3. ⌨ Ask "show the diagnostics for the Raspbot" on the projector.
4. ⌨ Ask a question on `win-2`. The laptop plays the answer.
5. Open ⏻ → Back to the start screen on the projector. Swipe your student ID on the reader at `win-1`.
   - If it fails: press a key.
6. On the projector, select ⚙ → This Device → Level of Detail → **Minimal**. Then select **Maximal**.
7. Open a module on the projector. The hub behind it blurs.
8. Open ⚙ Settings on the projector. Type "speed" in the search. Point at the preview and ↺.
9. Say:
   - Any screen is a window into the brain: a browser, no install.
   - Each screen has a name. The brain keeps its settings.
   - Each page can open on any screen: Open on…, the Command Center, or by voice.
   - "Set up the room": one sentence prepares a class.
   - The Newline runs from its Pi. It can run alone in its own Chrome, but that is slower and looks worse.
   - Minimal is for slow screens, such as a Pi. Maximal is for show.
   - The hub fits a phone and the Pi touchscreen.
   - After 30 minutes with nobody there, a screen goes back to its start screen.
   - Other computers watch. Only the brain's computer drives an arm, unless allowed.
   - Everything except the AI works with no internet.

### Part 5: the Raspbot (front, 5 min)
1. Drive raspbot1 from the Pi touchscreen: forward, sideways, on the diagonal, a turn.
2. Turn its camera with Pan and Tilt.
3. Open **Raspbot Monitor** on the projector.
4. Press **Labels off** on Raspbot Monitor. Point at a label and its distance.
   - If it fails: skip it.
5. Press **Picture** on the Raspbot page.
6. ⌨ Ask "look through the Raspbot's camera and drive to the box".
   - If it fails: skip it.
7. Say:
   - The page was made for this touchscreen.
   - Mecanum wheels: it drives sideways.
   - The 3D model follows the real car.
   - The labels: a detector on the brain, offline, about 6 pictures a second.
   - STOP on every page. The car stops when input stops.

### Part 6: the brain (back, 5 min)
1. Walk to the back with the audience.
2. Point at the Command Center on monitor 1: each device, each screen, a preview of each page.
3. Drag **Cameras** onto monitor 2. Drag **The Hub** back.
4. Select two screens. Open **System Map** on both.
5. Point at **M**, **S** and **C** on a card.
6. Unplug the white arm's USB cable. Point at Devices: "No". Plug it in again.
   - If it fails: skip it.
7. Say:
   - The Command Center opens only on the brain's computer.
   - The brain sees each device plugged in, within seconds.
   - An unplugged arm freezes. It connects again by itself.
   - `lab-os usb` shows each USB device. The white cameras keep their names in any socket.
   - Today it is mostly for show. The idea under it is practical: the AI can show you what it does, on any screen.

### Part 7: the arms by hand (back, 12 min)
1. 🎤 Ask "it's demo time" at monitor 2. Point at the welcome and the "try this" cards.
2. Press **Ask me to wave**.
   - If it fails: skip the wave.
3. 🎤 Say "the visitors have left".
4. Press the Quest's view button in the hub's strip on monitor 2. Move its window to monitor 3.
5. Put on the Quest.
6. Select **Enter VR** on the Quest. Show the hub around you.
7. Open **Arm Control** in VR. Drive the white arm 1:1. Then select **Relative**.
8. Move the arm down to the table. It stops above the table.
9. Let go of the grip. The arm freezes.
10. Select **Hands**. Drive with bare hands for 10 seconds.
11. Drive both arms: the left hand drives the green arm, the right hand drives the white arm.
    - If it fails: drive one arm.
12. Open **Monitor** in VR. Show both arms.
13. Open **Raspbot** in VR. Drive raspbot1 with the left stick. Turn the camera with your head. Press **LABELS**.
    - If it fails: skip it.
14. Select **Enter AR**. Show the 3D arm as a ghost over the real arm.
15. Take off the Quest.
16. Open **Arm Control** on monitor 2. Press **Desktop control**. Drive with the keyboard. Press **X** (STOP).
17. Point at the camera pictures under the joint angles.
18. Open **Monitor** on monitor 2. Point at the SO-101 card and the xArm card ("No xArm is connected").
19. Open **Webcam Control** on monitor 2. Drive with your hand.
    - If it fails: skip it.
20. Say:
    - The first feature: Quest → arm on day 7.
    - 1:1: the gripper goes where your hand is. Relative: 10 cm of hand = 10 cm of gripper.
    - Safety: STOP on every page, soft joint limits, a floor above the table, a speed cap, one controller at a time, a freeze when input stops.
    - The xArm uses the same brain and safety layer. It waits for a free USB socket.
    - The webcam: no headset, a bare hand. A preview.

### Part 8: the green arm goes back (back, 2 min)
1. Open **Training** on monitor 2. Press **Start** in LeRobot Control with Rerun. It refuses.
2. Hold the arms. Press Ctrl+C in the brain's terminal. Every screen says "lab-os is off".
3. Run `uv run --extra so101 lab-os serve --host 0.0.0.0 --speed 0.3 --arm so101-white`. Every screen comes back.
4. Close every page that shows a green camera.
5. Say:
   - The green arms belong to the training project.
   - lab-os keeps four rules for them: no motor changes, its calibration is read-only, no change to its software, one program per port.
   - The brain refuses a port that another program uses.

### Part 9: two ways an AI drives an arm (back, 15 min)
1. Press **Start** in LeRobot Control with Rerun. Move the leader arm. Press **Stop**.
   - If it fails: skip it.
2. Run the SmolVLA command on monitor 3. Try it two times.
   - If it fails: play the success video.
3. Open **AI Control** on monitor 2.
4. Tell Claude Code: "Pick up the cube."
   - If it fails: tell it "move to the cube" in steps.
5. Point at each tool call on AI Control.
6. Tell Claude Code to move 50 cm in one call. The tool refuses.
7. Tell Claude Code to do it with one program (`run_program`).
8. 🔘 Ask "hand me the cube" at monitor 2.
   - If it fails: ask "move the arm to handover".
9. Say "let go".
10. Say:
    - Trained policy (SmolVLA): 50 demonstrations, about 2 h on the RTX 5070, about 3 successes in 10. It works near the places it saw.
    - General AI with tools: no training. It reads the camera, the table's cm grid and the tools.
    - The tools: `camera_snapshot`, `pose_view`, `pick_at`, `move_to`, named poses, `stop`.
    - Each call goes through the same safety layer as the Quest.
    - "Hand me the cube" works about 1 time in 10: a preview.

### Part 10: how it was built (back, 8 min, while tic-tac-toe plays)
1. Tell Claude Code: "Play tic-tac-toe with me." Play your moves.
   - If it is slow: stop after 2 robot moves.
2. Open GitHub's pull requests, `AGENTS.md` and `docs/plan/quick-jobs.md` on monitor 3.
3. Say:
    - 41 days: the repository on 2026-10-23, the first demo on day 7.
    - 388 pull requests, about 166 quick jobs, about 1,000 tests. The tests need no hardware.
    - I wrote rules and checked results more than I wrote code.
    - Planning sessions: Claude Code by Remote Control on the lab desktop. They edit the plan only.
    - Coding sessions: one quick job each, from a queue. One lane, then two, then three at once.
    - Each session tests, opens a pull request and merges it when the tests pass.
    - `AGENTS.md`: one rules file for every agent.
    - Short reports in Simplified Technical English, so that I read them fast.
    - Codex for quick jobs, to keep the Claude usage low. Gemini for research and review.
    - Three UI/UX reviews by separate agents, merged into one list.
    - The fake arm first, then a lab day, then the fixes as quick jobs.
    - `GOTCHAS.md`: every surprise, so no agent finds it twice.
    - A hook stops Claude Code from changing the green arms' training files.
    - Frozen fallback versions for the demo.
    - One command sets up a new brain computer (`install.sh`).
    - It goes home with me in May 2027: a "place" is one config folder.
4. Before you walk: on the brain, check that ⚙ → Assistant → Full Access is on.

### Part 11: the end (front, 5 min)
1. Walk to the front with the audience.
2. Say:
    - **Practical now:**
      - The robot tools for AI agents. The agents test their code on the real arm.
      - The safety layer.
      - The fake arm: development with no hardware.
      - The device list, Diagnostics and `lab-os usb`.
      - The Cameras page.
      - The AI budget.
      - The green arms' rules in the code.
      - The room's layout for a class.
    - **For show:**
      - The startup, the 3D core, Maximal.
      - The round table.
      - The card swipe.
      - The Command Center's drag.
      - The number of screens.
    - **Experiments:**
      - "Hand me the cube".
      - Tic-tac-toe.
      - Webcam control.
      - The Raspbot's labels and its AI driving.
      - Two arms.
      - SmolVLA compared with a general AI.
    - **Next:**
      - Make the features and the pages better.
      - Projects and workspaces.
      - The development workflow in lab-os: the AI opens a browser, and more.
    - **A successor:**
      - I graduate in May 2027.
      - The lab needs a student to keep lab-os.
      - The docs, the rules and the tests are ready for that student.
3. Open the live agent's pull request on the projector. Say "an AI built this while I talked".
   - If it fails: open a pull request from this week.
4. 🔘 Say "shut down lab-os". Every screen says "lab-os is off".
   - If it fails: type it. Or press ⏻ on the brain.
5. Say "questions?".

## After the show
1. Run `uv run --extra so101 lab-os serve --host 0.0.0.0 --speed 0.3` on the brain.
2. On the brain, turn off ⚙ → Assistant → Full Access.
3. Offer the Quest (one arm, you at STOP), the Raspbot touchscreen, J.A.R.V.I.S. at the Windows desktops and the glove xArm to people who ask.
