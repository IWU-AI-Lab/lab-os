# The demo plan: the reasons (for later)

The short list to run is `docs/plan/demo-plan.md`. This page keeps the reasons for its choices. **Corrections (the builder, 2026-11-28), stronger than the text below:** the other Ubuntu desktop is at the back too (its port reaches the projector's HDMI); the front computer for the projector is now the builder's laptop (the VS Code browser or Chrome; Firefox works badly), so no cable crosses a walkway. The sound plays only on the laptop (S in the Command Center). No interaction with the audience during the show. There is no wireless keyboard: push-to-talk at the front is Space on the laptop. Only one Pi touchscreen is installed, for the Raspbot page. Each extra monitor gets a ThinkStation. The other hubs may not hear the voice reliably, so each voice moment has a typed backup. Codex was used to keep the Claude usage low, not because it ran out. Many moments are not yet tried in the lab: some will fail, and that is accepted.

**Status (planning session, 2026-11-27).** Each "Recommended" choice gives its reasons. The open questions are at the end. When the builder decides, the choice goes into the log (`docs/plan/log.md`) and this page changes to match. The practice run on Tuesday 2026-12-01 follows this page (`docs/guides/lab-checklist.md`).

## The facts that this plan uses
- **The audience:** students and faculty of the AI club. One or two people come at about 3:00 pm, and the rest come at about 3:30 pm. The professor may come.
- **The time:** at most 2 hours, from 3:00 to 5:00 pm. The builder can set up in the lab from 1:00 pm. The lab is usually empty from 1:00 to 3:00 pm.
- **The room:** the lab, which is also a classroom. It has two zones (the builder, 2026-11-27):
  - **The front:** the whiteboard, with the projector on it. The other Ubuntu desktop drives the projector. Its HDMI also goes to the room's ceiling speakers.
  - **The back, behind a wall:** the lab desktop (the brain) with monitor 1 (27"), monitor 2 (32") and monitor 3 (higher up, a little farther away), and the SO-101 table in the space beside them. The projector's HDMI cable does not reach the lab desktop. Wireless projection is not reliable. So the audience walks to the back for the brain's own pages and the arms.
  - **The Newline is at the front. The Quest space is at the back.** The Raspbot can be anywhere: it goes to the front (part 3, act 4a).
- **The audience size:** fewer than 10 people. Everyone fits at the back at once.
- **The setup:** the screens and stations do not stay set up from Tuesday. Everything is set up again on Thursday from 1:00 pm.
- **The people:** the builder runs the demo alone. The audience tries things only in the hands-on part at the end: Quest teleop, the Raspbot, and talking to J.A.R.V.I.S.
- **The persona:** J.A.R.V.I.S. ("hey Jarvis").
- **Live:** the SmolVLA run on the green arms. Lower priority: LeRobot teleop with Rerun. **One sentence only:** the xArm.
- **"Hand me the cube"** works about 1 time in 10 (the builder). It is not the finale.

### Numbers for the talk (from GitHub and the repository, 2026-11-27)
| What | Number |
|---|---|
| The repository was made | 2026-10-23: **41 days** before the demo |
| The first demo (Quest → arm) | 2026-10-30: day 7 (tag `demo-2026-10-30`) |
| Pull requests | 388 (385 merged) |
| Quick jobs | about 166 |
| Code (not counting vendored libraries) | about 23,000 lines of Python and 21,000 lines of web pages |
| Tests | about 18,000 lines, about 1,000 tests (863 passed on 2026-11-24), no hardware needed |
| The SmolVLA training (the training project) | 50 episodes, about 2 h on the RTX 5070, about 30 % success |

**The timeline** (for one minute of the talk): 10-23 the repository and the glove xArm → 10-30 the Quest drives the arm → 11-09 the hub's design approved after ten rounds → 11-10 personas and chat → 11-12 an AI tool drives the real arm; voice → 11-14 devices → 11-17 the AI picks up the cube → 11-19 the AI finds the cube in the camera's picture → 11-20 the previews (game, webcam, two arms, hand-over) → 11-22 the router → 11-24 the testing day → 11-25 the fallback freeze → 11-26 the UI/UX review and the Command Center → 12-03 the demo.

---

## 1. The format

| Format | For | Against |
|---|---|---|
| A demo video, then a walkthrough | Polished. A safe start. | The audience sees each thing twice. The video spoils the live moments. It costs the builder hours (coursework first). |
| Slides, then a walkthrough | Clear story. | Slides compete with 10+ live screens. Nobody looks at a slide while a robot moves. The walkthrough becomes a long list at the end. |
| Slides, with a walkthrough of each part | Clear story with proof. | Many changes between the slides and the live system. Each change costs time and attention. |
| Only talking and a walkthrough | Simple. No preparation. | With about 90 features it becomes a list. Attention drops after about 10 minutes with no change. |
| A flashy pitch with the walkthrough woven in | Strong start. Each claim gets proof at once. | Drama for 70 minutes is tiring, and it promises more than the tests show. |
| A flashy pitch, then the walkthroughs | Strong start. | The claims and the proof are far apart. The faculty want the proof. |
| A tiered reveal (small things first, then bigger) | A good arc: each part is bigger than the last part. | A slow start. The people who come at 3:30 see the weakest part first. |

**Chosen (the builder, 2026-11-27): "hook, then build up", with no slide deck.** The parts:
1. **A cold open** (the first 2 minutes): the most visual and most reliable moment first. One tap on the Newline starts every screen in the room at once, with the hyperspace jump and the spoken greeting.
2. **Then a tiered reveal:** step down to the plain, practical things (talking to it, the screens), then build up to the robots, then the AI driving the robots, then how one person built it in 41 days.
3. **The pitch is woven in:** each act starts with one sentence of "why", then the proof live.
4. **The room is the slide deck.** The projector shows real lab-os pages (the System Map, the hub); at the back, monitors 1 to 3 show the brain's pages (the Command Center, AI Control, Claude Code, the Quest's view). For the numbers and the workflow, it shows the real things: the GitHub list of pull requests, `docs/plan/quick-jobs.md`, `AGENTS.md`.
5. **No video at the start.** The practice run on 2026-12-01 is recorded (screen recording and a phone video). The recordings are the **backups**: when a live moment fails, its clip plays.

**The reasons:**
- Attention is highest in the first minutes. A cold open uses that time for the moment that is most visual and most reliable.
- The people who come at 3:30 must see the cold open. So the show starts at 3:30, and 3:00 to 3:30 is "doors open" (see part 2).
- A slide deck needs a laptop at the projector, and every slide is time away from the robots. The real files are better proof than slides of them, for an AI club and for faculty.
- A tiered reveal after the hook keeps each act bigger than the last one. The end of the show then has the robots and the AI, which people remember.
- The practice-run recordings cost almost no extra time, and each one is a backup for a risky moment.

**The minimal → maximal reveal (the builder's idea):** keep it, as a 1-minute moment in act 4b, not as the shape of the whole show. Set the projector to **Minimal** ("this is how it looks on a Pi"), then to **Maximal** (the denser network, more rings, the Bible verses). The reason: it shows that Level of Detail is a practical feature (slow screens), and the contrast makes Maximal stronger. A whole show in Minimal first would waste the cold open.

### Against boredom
- **Change the mode every 5 to 8 minutes:** talk, voice, a walk to another station, a robot moving, a question to the audience.
- **Move the audience:** the show has three parts in two zones: **the front** (acts 1 to 4b: talking and the screens), **the back** (acts 4c to 8: the brain's pages and the robots), and **the front again** (acts 9 and 10: the future and the close). Two walks of about 1 minute each. The walk to the back is a reset of attention, at about minute 25, when attention starts to drop. Do not walk more often: each walk costs time.
- **A robot moves during the talking parts:** tic-tac-toe plays during "How it was built".
- **Short questions to the audience:** "Who has used Claude Code?", "Which cell?" (in tic-tac-toe, if the builder agrees: question 9).
- **Name the time:** "Ten minutes on the robots, then the AI drives them." People stay when they know what comes next.
- **Cut, don't rush:** each moment has a "cut first" mark. When time is short, cut a whole moment.

---

## 2. The day
| Time | What |
|---|---|
| Tuesday 2026-12-01 | Set up every screen and station. The practice run, in the order below, with a recording. Tag `demo-2026-12-03`, or choose a fallback (`docs/plan/log.md`, 2026-11-27). |
| 1:00 – 2:30 pm (12-03) | Set up every screen and station again, from the list made on Tuesday (part 8). Start the brain from the tag. Run part 0 of the lab checklist. |
| 2:30 – 2:50 pm | A dry run of each risky moment, once. Reset the cube, the LEGO pieces and the Raspbot. Charge the Quest, the phone and the iPad. Check the AI Spend (the $20 budget pauses the chat). |
| 2:50 – 3:00 pm | Put every screen on its start screen. |
| **3:00 – 3:30 pm: doors open** | Every screen waits at its start screen. The early people try Quest teleop on `so101-white` (one arm, speed 0.3). The reason: the early people get something, and it is a last test of the arm and the Quest with a real person. At 3:25, put the Quest down and reset. |
| **3:30 – about 4:40 pm: the show** | Acts 1 to 9 below (about 70 minutes). |
| **About 4:40 – 5:00 pm: hands-on** | Quest teleop, the Raspbot, talking to J.A.R.V.I.S. |

---

## 3. The order of moments
**The tags:** 🛠 practical (the lab uses it now), ✨ for show, 🧪 an experiment or a preview. **Risk:** low, medium or high, from the lab results (`docs/plan/log.md`, 2026-11-24). The feature numbers in the brackets are in part 4.

**How to ask (recommended, question 3):** "hey Jarvis" for **three** moments only (marked 🎤). Every other question uses **push-to-talk**. Typing is the backup for every voice moment. **The reason:** with the wake word at about 9 in 10, 20 voice moments all work only about 1 time in 8 (0.9²⁰ ≈ 0.12), and the audience sees about 2 misses. With push-to-talk, no wake word can miss. Three wake-word moments still show the feature. After a wake-word miss, say: "That is why there is a button."

**Where the voice comes from (recommended, 2026-11-27):**
- **At the front: the projector's computer, through the ceiling speakers.** Put a USB microphone on that computer, on a USB extension cable, where you stand. Hold Space on a wireless keyboard for push-to-talk (Space works as the mic button). The answer plays on the projector's computer, so the ceiling speakers play it to the whole room.
- **At the back: the lab desktop's own USB microphone,** and monitor 2's hub speaks. The audience stands near it, so its speaker is loud enough.
- **The phone is only a backup:** its remote is not yet tried as a microphone, and it plays the answer on its own speaker.

**The reasons:** the ceiling speakers reach every person, and the voice seems to come from the room itself. That fits J.A.R.V.I.S. better than any speaker on a table. A Bluetooth speaker on the phone works too, but it is one more device to charge and pair, and the phone remote is not tested yet. A USB microphone and the ceiling speakers use only things that the lab has. **Showing that every device can speak** (the builder's option 3): keep it to one moment. In act 4, ask a question at a Windows desktop: its own speaker answers. Say: "Each screen can talk; the room's speakers are only the loudest one." So the Bluetooth speaker never looks necessary.

**The startup sound on many screens:** with sound on for each screen, 10 screens play the startup at once. Check on 2026-12-01 whether it sounds big or messy (an agent is changing this now: the builder, 2026-11-27). If it is messy, keep the sound on only for the projector's computer, so the ceiling speakers play it.

### Brain setup A (acts 1 to 5): both arms
`uv run --extra so101 lab-os serve --host 0.0.0.0 --speed 0.3`, from the tag. The brain drives `so101-white` and `so101-green` (the left arm).

| # | Moment (min) | What the audience sees | Shows | Risk | Backup |
|---|---|---|---|---|---|
| **1** | **Cold open** (2) | **At the front.** The room is dark and quiet. Press a key on the projector's computer. Every screen in the room starts at once: the hyperspace jump, the sounds. Only the projector's computer speaks the greeting, with real news, through the ceiling speakers. The reason for the projector, not the Newline: everyone sees it, and only its sound reaches the whole room. ✨ | H1, H26, T15, T19, H7 | Medium: one start for every screen is not yet tried in the lab (C.5) | A screen that does not start: say nothing, tap it later. The projector's computer fails: tap the Newline. |
| **2** | **What and why** (4) | The projector: the System Map turns slowly. "The lab has many robots and computers. Each project is an island: the glove xArm, the Raspbot's voice, the green arms' training. lab-os is one brain that connects them, and that an AI can use." Then the system diagram. 🛠 | H12, H11, the lab projects not connected | Low | — |
| **3** | **Talk to it** (10) | 🎤 "Hey Jarvis, what is lab-os?" Point at the network: the pulses run into the core while it thinks, and out of it while it speaks. Then TALK on the phone: "What is the next step of the project?" and "Write a prompt for Claude Code for it" (the Copy button). "What is 17 % of 3,400?" (it computes with Python and says the steps). "Give me a status report." "Open the AI Spend on the Newline." Barge-in: talk over an answer, and it stops. Open the History page. One sentence each: dictation, Ollama and Gemini as fallbacks, the voice per persona, the conversation kept for 30 min, "teach it your voice". 🛠 | T1–T4, T7–T10, T12–T14, T16, T20, H1, H7 | Medium: the wake word; the answer takes several seconds | A wake-word miss: TALK on the phone. No internet: "the AI part needs the internet; the rest works offline" (P3), then go to act 4. |
| **3b** | **The round table** (2, cut first) | ⚙ → Assistant → Persona: the personas around a 3D round table. Select the Lab Assistant: it turns, types its greeting and says it in its own voice. Select J.A.R.V.I.S. again. ✨ | T17, T18 | Medium: not yet tried in the lab (PT.1) | The plain persona buttons, or cut. |
| **4** | **The room** (8) | **At the front.** Here the builder answers "what is the use?" (part 5). 🎤 "Hey Jarvis, set up the room": every screen changes to its page. "Open the Cameras on the Newline." "Show the diagnostics for the Raspbot." Ask a question at a Windows desktop: its own speaker answers. ⏻ → Back to the start screen on the projector, then swipe a student ID (question 12: where the card reader is). One sentence each: the screen names, All Pages, the "Lab hub" icon on each computer, the full-screen button, back to the start screen after 30 min, watch-only on other computers. Hand the iPad around: the hub fits a phone and a Pi. 🛠✨ | H17, H18, H20–H32, H34 | Medium to high: "set up the room" (M.4) is not yet tried in the lab | "Set up the room": ⚙ → Set Up the Room. The card: a tap. |
| **4b** | **The look** (2) | On the projector, ⚙ → This Device → Level of Detail: **Minimal** ("for a Pi"), then **Maximal** (the Bible verses in the far layer). Open a module: the hub behind it blurs (depth). ⚙ Settings: type "speed" in the search; the preview at the right; ↺ resets one setting. One sentence: the startup as a video, the colours in one file, a test checks the capital letters. ✨🛠 | H2, H5, H6, H8, H15, H23, H24 | Low | — |
| **4a** | **The Raspbot** (5) | **At the front**, on the floor in front of the whiteboard. Drive raspbot1 sideways and on the diagonal from the iPad's Raspbot page. The projector shows Raspbot Monitor: the live camera and the 3D Raspbot follow the car. Labels on the camera picture: "CUP 82%" and the distance (cut first). With Full Access on: "Look through the Raspbot's camera and drive to the box" (cut first). The reason for the front: the front acts are mostly talking, and a robot that moves there breaks the talking before the walk to the back. 🛠🧪 | R10, R12, R13, Q14, A12 | Medium (driving), high (the labels and the AI driving are not yet tried in the lab) | The labels and the AI: their clips, or cut. The car does not connect: say one sentence and go on. |
| **4c** | **Behind the wall: the brain** (5) | **Walk to the back** ("Now the brain and the robots"). Monitor 1 (27"): the Command Center: every device and screen in the room, with a preview of each screen. Drag **Cameras** onto monitor 2; then select two screens and open the System Map on both. Monitor 2 (32"): the hub, with the Devices panel: unplug the white arm's USB cable → "No" within 5 s, the arm frozen; plug it in → it connects by itself. Open on… → Monitor on another monitor of this computer. 🛠✨ | H10, H19, H33, R4, R5, R7–R9 | Medium to high: the Command Center (part C) is not yet tried in the lab; the unplug failed on 2026-11-24 (fixed since) | Command Center: Open on… by hand. The unplug: cut. |
| **5** | **Visitors are here** (2) | 🎤 "Hey Jarvis, it's demo time." The AI welcomes the room in its own words, and the "try this" cards come. "Ask me to wave": `so101-white` waves. This is the first time an arm moves. "Hey Jarvis, the visitors have left." 🛠 | H13, P2 | Medium to high: the wave needs work (backlog) | Cut the wave; the welcome is enough. |
| **6** | **Robots by hand** (14) | Put on the Quest. Monitor 3 shows what the Quest sees (the brain opens that window). Enter VR: the hub around you. Teleop: 1:1, then relative; the arm stops at the floor; let go and it freezes. Bare hands for 10 seconds ("difficult to steer"). Then **two arms**: the left hand drives the green arm, the right hand the white arm. Monitor shows both arms. Take the Quest off. The Teleop page on the desktop: desktop control (keyboard), the camera pictures; on a Windows desktop the buttons are grey ("only one controller at a time"). SO-101 Monitor on the Pi touchscreen beside the arms, with STOP. The Monitor list: "No xArm is connected", and one sentence on the xArm. Webcam teleop: one minute (cut first). 🛠✨🧪 | Q1–Q13, Q15–Q21, H9, R1, R2, R6 | Low (one arm), medium (two arms, the Quest's view), high (webcam) | The Quest fails: desktop control. Two arms fail: one arm. The Quest's view fails: the audience watches the arm. Webcam: its clip, or cut. |

### The change: the green arm goes back to the training (2)
"The green arms belong to the training project. lab-os has rules for them." On the Training page, press Start for LeRobot teleop: it refuses with a sentence, because the brain drives the green arm (R2, G1). Stop the brain (Ctrl+C; hold the arms first). Every screen says "lab-os is off". Start **brain setup B**: `uv run --extra so101 lab-os serve --host 0.0.0.0 --speed 0.3 --arm so101-white`. Every screen comes back by itself. **The reason for this order:** two-arm teleop needs the green arm in the brain, and the training tools need it out of the brain. One restart is necessary, and this way it shows a rule and a feature (the pages come back by themselves). **Before the VLA run:** no page may show a green camera (Cameras page switches off), because the VLA run opens them.

### Brain setup B (acts 7 to 9): only `so101-white`
| # | Moment (min) | What the audience sees | Shows | Risk | Backup |
|---|---|---|---|---|---|
| **7** | **Two ways an AI drives an arm** (15) | **(a) A trained policy.** On the Training page, LeRobot teleop with Rerun: "This is how we recorded 50 demonstrations." (cut first.) Then the SmolVLA run on the green arm: the training project's command in a terminal on monitor 3. "50 episodes, 2 hours of training, about 3 in 10." Two tries, then the success video if both miss. **(b) A general AI with tools.** Monitor 2 shows AI Control; monitor 3 shows Claude Code. Claude Code on the brain: "Pick up the cube." It takes a camera picture, finds the cube on the table's cm grid, and calls `pick_at`; each step shows on AI Control before it moves. Ask it for a move that is too big: the tool refuses ("at most 10 cm"). One program instead of many moves (`run_program`). Then push-to-talk at the brain: "Hand me the cube", **once, as a preview**: "it works about 1 time in 10." 🧪🛠 | G1, G2, A1–A11, A13, T5, T6, H14, R3, R11 | High (VLA, hand-over), low to medium (Claude Code and `pick_at`, which worked on 2026-11-19 and 11-24) | VLA: the clip of a success. Hand-over: "move the arm to handover" (a named pose). |
| **8** | **How it was built** (8, while tic-tac-toe plays) | Claude Code plays tic-tac-toe with LEGO pieces against the builder, on the printed grid; monitor 2 shows the board on the stand camera's picture. Between the moves, the builder tells the story: 41 days, part-time, coursework first; the numbers; the workflow (part 6). On monitor 3, beside Claude Code: the GitHub pull requests, `AGENTS.md`, the quick-jobs file, a one-screen report. One sentence each: the fake arm, CI on each push, the tests without hardware, `install.sh`, places (it goes home with the builder), `lab-os logs`, `lab-os usb`, `measure-arm`, record and replay. 🛠 | A10, R11, P1–P6, H28, Q6, Q11 | Medium: one game passed on 2026-11-24, but it takes about 8 min | Stop the game after 2 robot moves; or say the moves. |
| **9** | **What is real, what is next** (5) | **Walk to the front.** The honest scorecard (part 5): 🛠 / ✨ / 🧪. The future: refine the features and the UI; then projects, workspaces and the development workflow (the AI opens a browser, and more). **The successor:** "lab-os needs a student to keep it after I leave in May 2027." | — | — | — |
| **10** | **The close** (3) | **Chosen:** "But wait, there's more" is the **live agent** (part 7): show its pull request on the projector (GitHub in its browser). Then the **bookend**: hold push-to-talk and say "Shut down lab-os." Every screen in the room says "lab-os is off" at once, as the opening started every screen at once. Then one tap brings it back for the hands-on. **Before you walk to the front** (end of act 8), select ⚙ → Assistant → Full Access on the brain: Settings changes only from the brain's own computer, and the shutdown by voice needs Full Access. **Switch Full Access off before the hands-on**, because with it any screen can move the arms. ✨ | H16, T6 | Low (the shutdown); medium (the agent; the shutdown by voice is not yet tried) | The agent fails: show a pull request that an agent made this week. The voice shutdown fails: type it in the ask line; or ⏻ on the brain (behind the wall). |

**Hands-on (about 4:40 – 5:00 pm):** Quest teleop at the back (one arm, speed 0.3, the builder at STOP); the Raspbot at the front on the iPad's Raspbot page (low speed; it stops when the finger lets go); J.A.R.V.I.S. at the Windows desktops and from people's own phones (no arm moves from them). The builder stays at the Quest and the arm, because only the arm can hurt someone.

---

## 4. Every feature has a moment
The list follows `FEATURES.md`. A number in the "Moment" column is a row of part 3. "Said" means one sentence, with no live moment.

| Feature (`FEATURES.md`) | Moment |
|---|---|
| **The hub:** H1 the hub, the hyperspace, the network, the sounds · H2 the shared look · H3 robot pages fit every screen · H4 small screens · H5 the UX fixes · H6 depth · H7 the 3D core | 1, 3, 4, 4b, 6 |
| H8 the startup as a video · H9 the hub in VR · H10 live devices · H11 the system diagram · H12 the System Map · H13 visitor mode · H14 the assistant moves the arm | 4b (said), 6, 4, 2, 2, 5, 7 |
| H15 Settings · H16 shut down · H17 named devices · H18 display names · H19 the Command Center · H20 Diagnostics · H21 Open on… | 4b, 10, 4, 4, 4, 4, 4 |
| H22 one tap for each device · H23 drawing resolution and Level of Detail · H24 full screen · H25 the card swipe · H26 one start for every screen · H27 every view on any device · H28 the brain's log | 4 (said), 4b, 4b (said), 4, 1, 4, 8 (said) |
| H29 the room's layout · H30 All Pages · H31 no long-press menu · H32 back to the start screen after 30 min · H33 another monitor of the brain · H34 watch-only computers | 4, 4, 4 (said), 4 (said), 4, 4 and 6 |
| **Talking:** T1 typed chat and History · T2 AI setups · T3 the spend log and budget · T4 the AI Spend panel · T5 `run_program` · T6 Full Access · T7 the chat knows the project | 3, 3 (said), 3, 3, 7, 7 (said), 3 |
| T8 push-to-talk · T9 dictation · T10 the wake word and the rest of its row · T11 the language for each device · T12 the status report · T13 it opens pages · T14 the phone as a remote | 3, 3 (said), 3 and 1–5, 3 (said), 3, 3, 3 |
| T15 the spoken greeting · T16 voice setups · T17 personas · T18 the round table · T19 the greeting's news · T20 the conversation kept | 1, 3 (said), 3b, 3b, 1, 3 (said) |
| **Teleop:** Q1 controllers · Q2 bare hands · Q3 relative · Q4 1:1 · Q5 speed and floor · Q6 `measure-arm` · Q7 the 3D arm and the AR ghost | 6, 6, 6, 6, 6, 8 (said), 6 |
| Q8 the headset's status panel · Q9 the Quest's view on another screen · Q10 desktop control · Q11 record and replay · Q12 the teleop and monitor pages · Q13 a Monitor for each kind · Q14 Raspbot Monitor | 6, 6, 6, 8 (said), 6, 6, 6 |
| Q15 the Teleop page's buttons · Q16 camera pictures on Teleop · Q17 the Cameras page · Q18 grey buttons when another device drives · Q19 the freeze and STOP · Q20 webcam teleop · Q21 two arms | 6, 6, 4 and 7, 6, 6, 6, 6 |
| **AI tools:** A1 the robot tools · A2 their safety · A3 named poses · A4 heights from the table · A5 limits that switch off · A6 `pose_view` · A7 `pick_at` | 7 |
| A8 the table map · A9 `camera_snapshot` · A10 tic-tac-toe · A11 AI Control · A12 AI driving for raspbot1 · A13 the project tools | 7, 7, 8, 7, 7, 3 and 8 |
| **Robots:** R1 `so101-white` · R2 `so101-green` · R3 the green cameras · R4 the white cameras by hub port · R5 `lab-os usb` · R6 `xarm1` · R7 the brain finds the arm | 6, 6 and the change, 7, 4 (said), 8 (said), 6 (said), 4 (said) |
| R8 unplugged and plugged in again · R9 plugged in later · R10 the Raspbot page · R11 the fake arm · R12 labels · R13 the 3D models | 4c, 4c (said), 4a, 8 (said), 4a, 4a and 6 |
| **Anywhere:** P1 places · P2 venues · P3 offline · P4 `install.sh` · P5 CI · P6 terminal colours | 8 (said), 5, 3 and 8 (said), 8 (said), 8, 8 (said) |
| **Training:** G1 LeRobot teleop with Rerun · G2 `lab-os green` and LeLab | 7, the change and 7 (said) |
| **Not connected:** the glove xArm · the Raspbot's voice control · the xArm camera demos | 2 (said); the glove at the hands-on if question 7 says so |

---

## 5. What is practical, and what is for show
**The honest scorecard (act 9).** Say it plainly: the faculty will trust the rest more.
- 🛠 **Practical now:** the robot tools for AI coding agents (they made development faster: the agents test on the real arm), the safety layer (STOP, the limits, the floor, one controller at a time), the fake arm (development with no hardware), the device list and Diagnostics, `lab-os usb`, the Cameras page, the AI Spend budget, the green arms' rules in the code, the phone as a remote, the room's layout for a class, places (it goes home with the builder).
- ✨ **For show:** the hyperspace startup, the 3D core, Maximal (the Bible verses), the round table, the card swipe, the Command Center's drag, the number of screens.
- 🧪 **Experiments:** "Hand me the cube", tic-tac-toe, webcam teleop, the Raspbot's labels and its AI driving, two arms, the VLA compared with a general AI, visitor mode.

**"What is the use of the hub on other devices?"** Recommended answer, in three parts:
1. **Any screen is a window into the brain.** A Pi and an old monitor become a lab-os screen with no install: the brain does the work, the screen only shows a page. That is cheap and easy to keep.
2. **The control is where the robot is.** The Pi touchscreen beside the arms shows Monitor with STOP. The person at the robot has the STOP, not only the person at the desk.
3. **The AI can show you what it does.** Open on… is also a tool for AI agents (Full Access). An agent can put its camera picture or its plan on the screen beside you. That is the start of the future direction (workspaces, the AI opens a browser).

And say it honestly: "The Command Center is for show today. The idea under it is the practical part." For a class: "set up the room" puts each page on its screen in one sentence, before the class starts.

---

## 6. The workflow (for act 8)
From the docs (the builder adds what is missing: question 10):
- **Planning sessions and coding sessions.** A planning session (Claude Code by Remote Control on the lab desktop) edits only `docs/plan/` and the lab checklists. Coding sessions take the quick jobs.
- **The quick-jobs queue and lanes:** one session at a time, then two lanes (2026-11-20), then three lanes (2026-11-25), each lane its own `git worktree`. A session merges its own pull request when the tests pass on GitHub.
- **One rules file for every agent** (`AGENTS.md`): Claude Code, Codex and the others read the same rules. The reports fit on one screen, in Simplified Technical English (ASD-STE100).
- **Other AI tools:** Gemini for research and review; GPT (Codex) for quick jobs, to keep the Claude usage low; three separate UI/UX reviews, merged into one (`docs/plan/ux-review.md`).
- **The loop with the lab:** build on the fake arm → the lab day → the results become quick jobs → build again. `docs/dev/GOTCHAS.md` keeps every surprise.
- **The guard rails for agents:** a hook stops Claude Code from writing to the training calibration and the `lerobot` env. The fallback versions are frozen (tags).
- **The point to say:** "I wrote rules and checked results more than I wrote code."

---

## 7. "But wait, there's more"
No single feature is bigger than the rest, so a feature as "one more thing" can make the end weaker. Three options (question 8):
1. **The live agent (recommended).** At the start of the show, give a coding agent a small job from the backlog. At the end, show its pull request with the tests passed: "While I talked, an AI built this." Do not merge it live. The reasons: for an AI club, the way it was built is the real news; it leads to the future direction and to the successor. The risk: the agent fails or the usage runs out. Then show a pull request from earlier in the week; a failure is also a lesson.
2. **The bookend only:** the shutdown of every screen at once. Reliable and visual, but not a surprise.
3. **No "more":** end with the future and the successor.

**Chosen (the builder, 2026-11-27): 1, then 2 as the last 30 seconds.**

---

## 8. The screens
**Recommended** (the builder decides; questions 2 and 6):
| Screen | Page | Why |
|---|---|---|
| The projector (the other Ubuntu desktop, front) | The hub: the cold open, the System Map, the voice, Level of Detail; GitHub at the close | The one screen that everyone sees, and the ceiling speakers. |
| The Newline (Pi, HDMI 1600×900; where it stands: question 11) | The hub's core | A second place to talk, and a target for "open … on the Newline". |
| Monitor 1, 27" (the brain, back) | The Command Center | The brain's own page: it opens only there. |
| Monitor 2, 32" (the brain, back) | The hub; AI Control; the tic-tac-toe board | The audience stands here for the robots. |
| Monitor 3 (the brain, back, higher up) | Claude Code; the Quest's view; GitHub and the docs in act 8 | High up, so people at the back of the group see it. |
| The Windows desktops | The hub's core | Voice stations at the other side of the room; the hands-on "Talk to J.A.R.V.I.S.". |
| The Pi touchscreens (2) | SO-101 Monitor (with STOP) beside the arms; Raspbot Monitor beside the Raspbot | The control is where the robot is. |
| The 32" monitors (the screens wall) | Cameras, the System Diagram, AI Spend, Diagnostics, History, Raspbot Monitor, the hub | They make the cold open big, and each shows a real page. |
| The iPad | The hub in the hand (passed around in act 4); the Raspbot page (act 4a and the hands-on) | It shows that the hub fits a tablet, and it is the Raspbot's controller at the front. |
| The phone | The remote (TALK) | The presenter's microphone. |
| The Quest | The VR hub and teleop | Act 6 and the hands-on. |

**How many screens:** each extra screen costs about 5 minutes (power, cable, network, the address, full screen). Everything is set up again on Thursday, so about **6 to 8 extra screens** fit in 1:00 to 2:30 pm. **Put the extra screens at the front.** The reason: at the cold open the audience is at the front, so a screen at the back adds nothing to it. On Tuesday, write the list: each screen, its computer, its cable and its address (`/?device=<name>`), and put the "Lab hub" icon on each computer, so that Thursday is one tap for each screen. **Recommended:** the 32" monitors on the ThinkStations (by Ethernet), because a ThinkStation draws Full quality and a Pi draws only Minimal or Reduced. The 8 Pis and the Jetsons only where a monitor has no ThinkStation. The reason: the cold open looks best when every screen does the full hyperspace jump; a slow screen that jumps late looks broken.

---

## 9. The xArm and the microphone
**The xArm (recommended: one sentence, and don't build the second xArm now).** The reasons: the xArm driver works, but it shows nothing that the SO-101 does not show; the lab desktop has no free USB socket; and the builder has 6 days and coursework. On the screen, the Monitor list's "No xArm is connected" card is the one sentence: "the xArm uses the same brain and safety layer; it waits for a free USB port." The glove xArm (Hiwonder's own firmware, no lab-os) can stand at the hands-on as "a lab project that lab-os connects next", if it is safe to leave alone (question 7).

**The microphone (recommended: keep the desktop's USB microphone, and add one on the projector's computer).** The front acts use a USB microphone on the projector's computer, with the ceiling speakers (part 3). The back acts use the lab desktop's microphone, because the audience stands near it. The phone is a backup only: it is not yet tried as a microphone. A free USB socket on the lab desktop helps only for the xArm, and the xArm gets one sentence. So the phone does not need to replace the desktop's microphone.

---

## 10. The risks for the whole show
- **The OpenAI key or the internet fails:** Gemini's free key answers (about 15 to 20 answers a day). Use it only for acts 3 and 5.
- **The AI budget ($20 a month) pauses the chat:** check AI Spend at 2:30 pm. Raise the budget in Settings before the show if it is near the limit.
- **A screen goes back to its start screen after 30 minutes untouched:** the screens wall shows pages that nobody touches. Check on 2026-12-01 whether a page that is only shown counts as "in use".
- **Visitor mode hides Settings** (the visit-day venue): do Settings (4b) before visitor mode (5).
- **A coding session merges to `main` on the day:** the demo runs from the tag. No coding sessions on 2026-12-03.
- **The green cameras during the VLA run:** no page may show them (the change, above).
- **`main` fails the practice run:** the demo runs from `demo-fallback-2026-11-25` or `checkpoint-2026-11-26` (the log, 2026-11-27).

---

## 11. Open questions for the builder
1. **The format:** "hook, then build up", with no slide deck and recorded clips as backups? (Or a few slides only for act 8?)
2. ~~The brain's own pages~~: answered 2026-11-27 (monitors 1 to 3 at the back; the audience walks there).
3. **The voice:** a USB microphone on the projector's computer, Space on a wireless keyboard for push-to-talk, and the ceiling speakers? Is there a wireless keyboard, and a USB extension cable?
4. ~~The size of the audience~~: answered 2026-11-27 (fewer than 10).
5. ~~The VLA run~~: answered 2026-11-27 (the command on monitor 3; a success video is the backup).
6. ~~The room on 2026-12-03~~: answered 2026-11-27 (set up again on Thursday).
7. **The glove xArm at the hands-on:** yes, as a station that runs alone, or no?
8. **The close:** the live agent, then the shutdown of every screen? Which agent (Codex, Claude Code)?
9. **The audience in tic-tac-toe:** may people call out the cells (you place the pieces)?
10. **The workflow:** what is missing from part 6?
11. ~~The Newline, the Raspbot and the Quest~~: answered 2026-11-27 (the Newline and the Raspbot at the front, the Quest at the back).
12. **The card reader:** on the lab desktop (back) or on a front computer? (A swipe at the front fits act 4.)
