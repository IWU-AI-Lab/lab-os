# The demo: Thursday 2026-12-03, 3:30 pm

Two lists: the setup, then the run. Tick each line. Many lines are not yet tried in the lab: when one fails, use its backup [in brackets] or skip it. The reasons for the choices: `docs/plan/demo-plan-reasons.md`.

**Front** = the projector side of the room. **Back** = behind the wall: the lab desktop (the brain), monitors 1 to 3, the SO-101 table, the Quest space.

## Setup (1:00 – 2:55 pm)
- [ ] Router on. Lab desktop on.
- [ ] Plug in the arms, cameras and microphone (`docs/guides/plug-in.md`).
- [ ] `git switch --detach demo-2026-12-03` (or the fallback tag). `uv run --extra so101 lab-os serve --host 0.0.0.0 --speed 0.3`.
- [ ] Back: monitor 1 Command Center · monitor 2 the hub · monitor 3 Claude Code (connected to the brain's tools).
- [ ] Front: the laptop on the projector's HDMI (sound to the ceiling speakers). Firefox: `https://192.168.8.130:8443/?device=projector`. Allow the microphone.
- [ ] Newline: `/?device=newline`. Windows desktops: `/?device=<name>`.
- [ ] Extra monitors, each with a ThinkStation, at the front first: Cameras, System Diagram, AI Spend, Diagnostics, History, the hub.
- [ ] Pi touchscreen: raspbot1 on, `uv run lab-os raspbot deploy`, then the Raspbot page.
- [ ] Card reader: in the centre of the room, on a front computer.
- [ ] Glove xArm station on (Hiwonder's firmware).
- [ ] Quest, phone and iPad charged and on the router's Wi-Fi.
- [ ] On the brain, ⚙: persona J.A.R.V.I.S. · The Assistant May Move the Arm on · Full Access on · AI Spend well under the budget.
- [ ] Props: the blue cube, the LEGO pieces and the grid, a box for the Raspbot, the VLA success video, the practice-run clips.
- [ ] 3:25: in Claude Code, start the live agent on a small backlog job.
- [ ] Every screen on its start screen.

## Run
**Voice:** "hey Jarvis" only for the 🎤 lines. Elsewhere, push-to-talk (Space on the laptop at the front, the mic button at the back). [Type it in the ask line.]

**Front**
- [ ] 1. A key on the laptop: every screen starts; the greeting on the ceiling speakers. [Tap a screen that did not start.]
- [ ] 2. System Map on the projector; the system diagram. Say: the lab's islands (glove xArm, Raspbot voice, green training) → one brain.
- [ ] 3. 🎤 One question. Then: the next project step and a Claude Code prompt · a calculation · a status report · "open AI Spend on the Newline" · talk over an answer · History.
- [ ] 4. ⚙ → Assistant → Persona: the round table. Back to J.A.R.V.I.S.
- [ ] 5. 🎤 "Set up the room." [⚙ → Set Up the Room] · "Show the diagnostics for the Raspbot" · a question at a Windows desktop.
- [ ] 6. ⏻ → Back to the start screen; swipe a card. [Tap.]
- [ ] 7. Pass the iPad with the hub.
- [ ] 8. Projector: Level of Detail Minimal, then Maximal. Settings: search, ↺.
- [ ] 9. Raspbot: drive from the touchscreen (sideways too); Raspbot Monitor on the projector; Labels; "drive to the box". [Skip Labels and the AI drive.]

**Back**
- [ ] 10. Command Center: drag Cameras onto a screen; two screens at once. Unplug the white arm's USB → "No"; plug it in. [Open on… by hand.]
- [ ] 11. 🎤 "It's demo time" (monitor 2) → wave → "the visitors have left". [Skip the wave.]
- [ ] 12. Quest: the VR hub · 1:1 · relative · bare hands · two arms (Quest's view on monitor 3) · the Teleop page with keyboard · grey buttons on another computer · the Monitor list (say: the xArm uses the same brain) · webcam teleop. [Desktop control; one arm.]
- [ ] 13. Training page → Start: it refuses (the brain has the green arm). Hold the arms, Ctrl+C. `… serve --host 0.0.0.0 --speed 0.3 --arm so101-white`. Close every green camera picture.
- [ ] 14. LeRobot teleop with Rerun (how the data was recorded). The SmolVLA command on monitor 3, two tries. [The success video.]
- [ ] 15. Claude Code: pick up the cube (AI Control on monitor 2) · a move that is too big (refused) · one program for many moves. "Hand me the cube", once. ["Move the arm to handover".]
- [ ] 16. Tic-tac-toe with Claude Code. While it plays: the build story (the list below). [Stop after 2 moves.]

**Front**
- [ ] 17. What is practical, for show, an experiment. The future. A successor is needed.
- [ ] 18. The live agent's pull request on the projector. [One from earlier this week.]
- [ ] 19. "Shut down lab-os" → every screen off. Start it again. **Full Access off.**
- [ ] 20. Hands-on: Quest (you stay at STOP) · Raspbot touchscreen · J.A.R.V.I.S. at the Windows desktops · the glove xArm.

## Do not leave out (talking points)
- 41 days since the repository started (2026-10-23); the first demo on day 7. 388 pull requests, about 166 quick jobs, about 1,000 tests that need no hardware.
- The workflow (from the docs; add what is missing): planning sessions and coding sessions · the quick-jobs queue in 1, then 2, then 3 lanes · each session merges its own pull request when the tests pass · `AGENTS.md`, one rules file for every agent · short reports in Simplified Technical English · the fake arm first, then the lab day, then the fixes · `GOTCHAS.md` · the hook that guards the green arms · frozen fallback tags · Codex to keep the Claude usage low · Gemini for research and review · three UI/UX reviews, merged · Remote Control from home.
- Why the hub on many screens: any screen is a window into the brain, with no install · the control (STOP) is where the robot is · an AI agent can show you what it does.
- Offline: everything except the AI works with no internet. Places: it goes home with the builder in May 2027.
- The SmolVLA numbers: 50 episodes, about 2 h on the RTX 5070, about 30 % success.
