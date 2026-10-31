# Ideas backlog

**The single source of truth for ideas.** New ideas land here, **not in code** and not in other docs, unless they're part of the current focus (`docs/current-focus.md`). This keeps the project finishable and nothing gets lost. When an idea becomes the focus, move it into `current-focus.md` and delete it here. When an idea is decided (but not yet scheduled), record the decision in `lab-jarvis-log.md` and keep or delete the entry here.

Each idea: what it is · why · where it plugs in (slot/module, if known; slots are in `lab-jarvis-log.md` → "Architecture sketch"). "—" = not recorded yet.

**Not here because they're already decided plans:** the teleop second act (Gemini Robotics-ER "look, then reach" → SmolVLA → bigger VLAs via rented GPU; options table in `docs/archive/focus-2026-10-teleop-demo.md`) and teleop as data collection for the training project. Also offline lite mode, the portable demo kit, and the staged remote-access plan (`lab-jarvis-log.md` → "Mobility, portability & remote access").

---

## On hold: decided, will be built (2026-10-30)
Not ideas any more: agreed features, paused when the teleop focus closed (the demo is showable, "needs polishing"; tag `demo-2026-10-30`). Pick them up from here; the teleop focus's full context is in `docs/archive/focus-2026-10-teleop-demo.md` (step numbers below refer to it).

### Teleop demo: what's left
- **Hand tracking (step 6)**, the original goal: a visitor's bare hand drives the arm (pinch = gripper, open hand = release). Same pipeline as the controllers; per-user calibration with comfortable thresholds + hysteresis (the glove lessons).
- **Speed and feel (step 7).** Builder, 2026-10-30, SO-101 + Quest at `--speed 0.2` (24 °/s per joint): "much more intuitive if it was much faster". Raise `--speed` step by step to the lab venue's 0.5 (60 °/s); then the 0.5× hand-to-gripper scale, smoothing, end-to-end delay. Above 0.5 is the builder's call (`config/venues/lab.yaml`).
- **Quest display (step 5).** Visitor hint until the first grab; the lazy-follow **HUD mini-arm** (decision 2026-10-28) whose joints turn red near their limits (= the workspace warning); the status panel lazy-follows too.
- **Visitor polish + portability test (step 8).** Script, casting to a monitor, one run from the laptop away from the lab, tag, 60-second clip. The SO-101 port check uses Linux paths (`/dev/serial/by-id/`, sysfs): a Windows/macOS field laptop needs the USB-ID lookup `xarm1` already uses.
- **`so101-white-leader`.** Build and set it up (spare board `5B41532183`; `python -m lab_os.robots.so101_setup setup-motors --arm so101-white-leader` after its port is in `config/devices.yaml`). For recording training demonstrations (second act B), not needed for the visitor demo.
- **xarm1 leftovers.** Hand-measured limits (`python -m lab_os.robots.xarm calibrate`), Keys at `--speed 0.4`, a precise delay measurement, hold-position on stop, Mouse mode tried in a browser. Its HACK stays listed in `current-focus.md`.
- **A real-Quest recording as a test fixture** (`serve --record`, commit a short clip).
- **Check:** in the XR emulator, Shift+WASD moving the arm while the clutch is *released* would be a bug.

### Troubleshooting suite
Was "Up next" after teleop (decision 2026-10-24); the builder chose the core first (2026-10-30). Its roll call / health checks start in the core focus; the rest waits here: microphone (level meter, noise, record + play back), cameras (live view, "is it sending images?"), robots (live joints; a test wiggle only with the builder's OK), network (reachable? delay?), accounts (API keys present and working, credits), Quest connected. Each check writes a **report file** humans and agents can read. *Why:* the roll call will find problems, and the builder, a future maintainer or an AI agent need an easy way to diagnose them.

---

## Recent ideas (2026-10-28)

### Hidden sensor data the hardware already has
- **What:** most of our devices measure more than we use, like a Mac's lid-angle sensor. Read it in health checks, the startup status and the HUD. Candidates (**? = to verify on our exact hardware**):
  - **SO-101 servos (Feetech STS3215):** besides position, each reports **load (rough force), temperature, voltage**, speed and a "moving" flag. Uses: **grasp detection** (gripper stalls with load = it's holding something), "someone pushed me" / collision detection, rough "how heavy is it?", overheating warnings before a servo cuts out.
  - **xArm 1S:** battery voltage from the controller (?); per-servo temperature/voltage (?).
  - **Raspberry Pi:** CPU temperature, and an **under-voltage flag** (`vcgencmd get_throttled`): an indirect **low-battery warning** for the Raspbot even if its battery can't be read directly. Raspbot sensors: ultrasonic distance, line-following sensors (?).
  - **Jetson:** live power draw in watts and temperatures (`tegrastats`).
  - **Quest:** battery, **headset on/off your head** (the browser reports when the session is hidden; dead-man input already), 25 tracked joints per hand, floor height.
  - **Cameras:** auto-exposure/brightness → **room light level**, which predicts whether hand tracking will work (it needs reasonable light).
  - **Microphones:** background noise level (fans) → whether voice will work.
  - **Every networked device:** Wi-Fi signal strength and delay → connection-quality warnings before things drop.
  - **Phones (Android Chrome):** compass, motion sensors, sometimes light sensor.
- **Why:** cheap "wow" facts plus real early warnings (low battery, hot servo, too dark for hand tracking), right where the troubleshooting suite needs them.
- **Plugs into:** each device plug-in declares what extra readings it offers; the troubleshooting suite, startup status and HUD read them. Safety: reading sensors is fine; anything that powers or moves stays under the safety rules.

### Startup sequence ("systems coming online")
- **What:** after a trigger (wake word, card, button, Quest, touchscreen…), the brain wakes the screens and plays a short sequence where **each device lights up as it actually reports in**. The animation *is* the roll call, with a sound per device, and it ends with a greeting + one-line summary. Starts on the device that triggered it (Quest, touchscreen, desktop); other screens join.
- **Why:** cool to watch *and* useful: you see at a glance what's up; results feed the troubleshooting suite's report files.
- **Reality (2026-10-28):** the first person arrives to a closed, empty lab; every robot is off and needs a physical switch (SO-101s: no switch, wall power). So nothing but the brain, router, screens (and cameras) is on at startup.
- **Default (decision 2026-10-28): robots are optional.** Startup assumes no robots are on; often the builder just wants to code or ask something. Startup covers the brain, screens and anything always-on. When someone switches a robot on, its status **flickers on** in the main system (with its chime), whenever that happens.
- **Optional "power-up walk" (demo mode).** For demos: startup shows the devices for that demo dim, with what to do ("xarm1: flip the switch on the base"). As you walk around switching things on, each one lights up with its chime the moment it really answers, like a cockpit pre-flight. The manual chore becomes the show, and when you're done you know everything works. Devices you don't need today can be skipped. Fast: the brain part takes seconds; the rest goes as fast as you flip switches.
- **Battery levels:** the xArm controller's protocol reportedly has a battery-voltage command (verify in our driver). Raspbot: unknown. A Pi can't measure a battery by itself, but Yahboom's expansion board might; check its docs before giving up.
- **Sound:** cosmetic, to add life (JARVIS feel). On while someone works in the lab, off otherwise (follows the on/off triggers); volume/mute in the sound pack.
- **Rules:** "only claim what's real": nothing lights up unless it really answered. An arm "nodding awake" would be great for visitors, but it's robot motion: only under the safety rules, opt-in, workspace clear, never unattended.
- **Plugs into:** triggers slot → roll call / health checks → theme + sound packs + decorative layer.

### Smart plugs to power devices on/off (downgraded 2026-10-28)
- **What:** network-controlled power plugs for things on wall power.
- **Reality:** almost everything here is battery-powered with a physical switch, so smart plugs can't turn it on. Only useful for the SO-101 power supplies (and later Pis/Jetsons on wall power). Low priority.
- **Watch out:** cut a Pi/Jetson's power only after a proper shutdown (SD card corruption); powering an arm counts as robot motion (safety rules); needs the lab network + professor's OK; plugs must work without a cloud app (offline rule).

### Many devices at once ("who's driving?")
- **What:** several people/devices use the system at the same time (Quest, phones, touchscreens, desktop).
- **Recommendation:** **everyone can watch** (all screens show the same live state); **only one device controls a given robot at a time** (it "has control"; others ask for it or it's handed over); **STOP works from every device, always**. Voice/agent commands go through the same rule.
- **Why now:** the teleop server already accepts several input pages and mixes them (fixed for teleop 2026-10-29, closed teleop focus step 6b). This generalizes it later.
- **Plugs into:** brain core (control lock per robot) + outputs/clients + safety layer.
- **Decided (2026-10-28):** control is **handed over** (the current driver releases it), not grabbed.

---

## Recent ideas (2026-10-27)

### Touchscreens as clients (small Pi screens + the big Newline)
- **What:** the lab's 3 small Raspberry Pi touchscreens (~7–9") and the ~75" Newline touchscreen on wheels become lab-os clients. Each shows a page from the brain that is tailored to its size: control, status, or new kinds of interaction (e.g. 3D arm models you can spin with your fingers).
- **Why:** more ways to use the system without a headset; the big screen suits visitors and groups.
- **Plugs into:** outputs/clients slot (same message protocol as the Quest page). The Pis just run a browser in kiosk mode (full-screen, no address bar), so they stay thin. Related: "Multi-screen presence", "Lab health dashboard" (below).
- **Possible roles (to discuss):** a small screen next to each robot as its "face" + status + STOP; the Newline as a group/visitor screen (3D arm view, cast of the Quest view, dashboard).
- **Rules that still apply:** any robot motion from a touch goes through the same safety layer (limits, dead-man); every screen that can move a robot shows a STOP.
- **Answers (2026-10-27):** "hologram" = a 3D arm model you spin with touch (the existing three.js arm view already does this with a mouse; touch is a small step). The Newline is a standalone Android computer, so its own browser opens the brain's page (check that browser supports WebGL + WebSockets). Uses: data display, or robot control with sliders.
- **Note:** slider control is the same page as phone teleop's touch mode (below). Build **one touch-control page** that adapts to phone, small screen and the 75" screen.
- **Open questions:** which Pi models are behind the small screens? The Pis and the Newline need the lab network (router) to reach the brain.

### Voice: build our own, use an existing realtime service, or both?
- **What:** choose between (a) an existing **speech-to-speech realtime service** (OpenAI's realtime voice models, Google's Gemini Live API), which already handles interruptions, turn-taking and tool calls in the background, and (b) our own **pipeline**: local wake word → speech-to-text → language model → text-to-speech.
- **Recommendation (not decided yet):** both, as plug-ins. The wake word / push-to-talk part is always ours and runs locally, so we don't stream the room to the cloud all day (cost + privacy). The conversation itself uses a realtime service first (best feel for the least work). Our own pipeline is the fallback for offline lite mode.
- **Fits:** Conversation manager (it gets thinner: the service does barge-in, while we keep queueing, tool routing and safety) · model router · two speeds (realtime = fast path; it can hand big jobs to the agent harness in the background). Tool calls from the voice model go through our tools + safety layer like everything else.
- **Watch out:** realtime audio is priced per minute, so check it against the ≤ $20/month budget (look up current prices, don't guess). It needs internet. Fan noise can cause false "interruptions" (push-to-talk helps).
- **Answer (2026-10-27):** used mostly for testing and **for the show** (visitors), not daily, so per-minute cost is probably fine. That favors the realtime service first; our own pipeline only when offline mode needs it.
- **Open questions:** which service ("GPT-Live" = OpenAI's realtime voice?); free-tier/data terms; venues need internet for it.

### Google Glass (Explorer Edition) as a display + camera
- **What:** custom app on the lab's Google Glass Explorer Edition: a tiny heads-up status display, and maybe its camera as a first-person view.
- **Why:** a "JARVIS glasses" moment; a hands-free status display while working at a robot.
- **Plugs into:** outputs/clients (display) + cameras/vision (first-person camera, like "Quest vision Q&A").
- **Honest caveats:** 2013 hardware, long discontinued, runs a very old Android (4.4). Apps are built with old tools, and the battery is likely worn. Camera privacy is still deferred (log). Much later.
- **Status (2026-10-27):** it boots; built-in voice commands (e.g. take a picture) work. No use picked yet ("I just want to use it for something").
- **Candidate uses (pick one later):** (1) teleop status HUD (FOLLOWING / FROZEN / gripper %) while driving the arm with a phone or leader arm; (2) "what am I looking at?": a photo from the Glass → JARVIS answers on its display; (3) alerts from the troubleshooting suite.
- **Next check (cheap, when curious):** which firmware is it on, and can a computer install apps on it over USB?

### Teleop from a phone
- **What:** a phone as a teleop input. Either (a) a touch page with sliders/joystick + STOP, or (b) the phone itself as a 3D "controller" (Android Chrome supports WebXR AR, which tracks the phone's position and tilt in space; iPhones' browser doesn't).
- **Why:** anyone can try it without a headset; a fallback if the Quest is unavailable; another entry for "Ways to teach a robot".
- **Plugs into:** inputs slot (a new input plug-in, same pipeline + clutch + dead-man). Merges with "Visitors' phones as remotes" (below).
- **For whom (2026-10-27):** everyone: the builder, lab members and visitors.
- **Gyro control (builder's main idea, 2026-10-27):** the phone's motion sensors (gyro + accelerometer, read by the browser's device-orientation feature) give its **tilt/rotation**, not its position in space. So pure gyro control means: tilt → wrist rotation (the glove's "tilt-for-rotation", which worked well), and/or tilt as a joystick (tilt forward = arm moves forward, at a speed set by the angle; relative, so no snapping). Real 3D **position** needs camera-based tracking (WebXR AR on Android Chrome). Both behind a clutch button on screen. iPhones ask the user for motion-sensor permission, and either way the page needs `localhost`/HTTPS.
- **Watch out:** WebXR needs `localhost` or HTTPS. Over USB that's easy with an Android phone (`adb reverse`, as with the Quest). Over Wi-Fi it needs a certificate. Phone tracking is less steady than Quest controllers.

---

## Recent ideas (2026-10-24)

### Clap to activate / deactivate
- **What:** a double clap turns the system on or off.
- **Why:** fun to show off. Usually kept **off** (loud noises could set it off), switched on occasionally.
- **Plugs into:** Triggers slot (one trigger plug-in, off by default, switchable per venue profile).

### "Jarvis, log out" (and similar phrases) to deactivate
- **What:** spoken phrases that put the system to sleep or log out.
- **Why:** a natural way to end a session, matching the wake word for starting one.
- **Plugs into:** Triggers slot (phrase triggers, fed by the voice pipeline).

### Interrupting and queueing in voice conversations
- **What:** I can cut the assistant off mid-sentence; I can give several requests in a row and have them handled in order.
- **Why:** real conversations aren't strict turn-taking; waiting for long answers is annoying.
- **Plugs into:** Conversation manager (one component owns interrupt / queue / turn-taking).

### Design language (JARVIS / cyberpunk feel)
- **What:** a mood board at `docs/design/references/`: depth, layers, 3D models, dynamic and mostly decorative UI elements. Later distilled into `docs/design/DESIGN.md` (colors, type, line/glow style, motion, sound, do's and don'ts), after which the reference folder can be deleted.
- **Why:** the long-term interface should feel like JARVIS / cyberpunk UIs, consistently across screen, web and headset.
- **Plugs into:** Theme file (design tokens, `config/theme.yaml`) + sound packs; decorative layer. Design phase starts after teleop works.

### Claude Code agent module
- **What:** use Claude Code, through the Claude Agent SDK, as the agent for big, slow tasks, so we get its tools and MCP connectors instead of building our own.
- **Why:** a capable agent with tools for free; our job shrinks to the harness and safety.
- **Reference:** https://github.com/ehteshambuildagents/jarvis (runs Claude Code headless via the Agent SDK; tools gated default-deny).
- **Open questions:**
  - **Auth + terms:** that project reuses a personal subscription login. Check whether that's allowed for an always-on app. The safer default is an API key paid from the lab credits.
  - **Cost:** per-task spend vs. the ≤ $20/month AI budget.
  - **Speed:** too slow for quick commands, so slow path only.
- **Plugs into:** agent harness slot (slow path). Tools default-deny; any robot motion still goes through our safety layer.

### Self-building agent
- **What:** the system's own agent can add things to the app (e.g. UI for a new robot, a new HUD status display) and handle system updates.
- **Why:** faster growth; the system helps maintain itself.
- **Rule:** **only** through the same path a human uses. Agent proposes on a branch → tests + CI → I approve → deploy from a tagged version. It never modifies the live running system directly. See `lab-jarvis-log.md` → "Agent changes to the system".
- **Plugs into:** agent harness slot + the normal git / CI / tag workflow.

---

## Earlier ideas (moved here 2026-10-24 from lab-jarvis-log.md and current-focus.md)

### Triggers & sign-in
| Idea | Why | Plugs into |
|---|---|---|
| Card-swipe ignition | Part of the walk-in moment; the lab has a card reader. | Triggers |
| Light-sensor ignition (room lights on → wake) | — | Triggers |
| Kinect gestures | — | Triggers, inputs |
| Student ID sign-in (stored hashed) | Know who's using the system. | Sign-in |
| Face recognition (opt-in only) | Hands-free sign-in / greeting. | Sign-in, cameras/vision |

### Voice, personas, agents
| Idea | Why | Plugs into |
|---|---|---|
| Multiple personas | — | Personas |
| Program-by-voice / agent onboarding | — | Agent harness |
| Local models | — | AI models (router) |

### Screens, phones, headset
| Idea | Why | Plugs into |
|---|---|---|
| Multi-screen presence (lab PCs/displays) | The system "lives" on the room's screens; lab only. | Outputs/clients |
| Screen-to-screen sending | — | Outputs/clients |
| Visitors' phones as remotes | Let visitors interact without the headset. | Inputs, clients |
| Quest-only mode | — | Quest client |
| Quest launch → HUD (launch animation into the HUD) | — | Quest client, theme/decorative layer |
| Quest vision Q&A ("what am I looking at?") | Ask about whatever the headset sees. | Cameras/vision, AI models |

### Teleop & robots
| Idea | Why | Plugs into |
|---|---|---|
| Fix the Hiwonder glove: (A) re-flash if its firmware source exists, or (B) glove → computer → arm with the teleop logic | Only if fun or useful (low priority). | Inputs (glove plug-in) |
| "Ways to teach a robot" demo (teleop, leader arm, glove, look-then-reach side by side) | Strong pitch / teaching story. | Teleop + demo |
| One hand controls two robots | Pitch moment ("one hand, two robots"). | Teleop (multi-arm output) |
| Two-hand control | — | Teleop inputs |
| Two-robot handoff | — | Robots, modules |
| Robot testing harness (not tied to the research paper for now) | Repeatable robot tests. | Tools |
| ROS 2 bridge | — | Robots |
| Air:bit drones module (much later; drones stay out of AI/voice/visitor control) | — | Robots (bridged via micro:bit radio) |

### Uses, reach, events
| Idea | Why | Plugs into |
|---|---|---|
| Lab health dashboard | — | GUI + roll call / health checks |
| Shared lab memory | — | Tools, AI models |
| Teaching use | Use the system in classes / demos. | — |
| Recruiting demo (portable) | Visitor routes may not pass the lab. | Portable kit, teleop |
| Remote check-ins | — | Remote access |
| Full lab in a bag | — | Portability |
| Live link to the lab (from a venue) | Show lab-only devices while traveling. | Remote access, network |
| Remote GUI from home (via a private overlay network; ask IT first) | Use the system's GUI off-site. | Remote access, GUI |
| Cellular robots | Robots across campus without the lab network. | Network/connection |
| Escape room (dropped 2026-10-15, still parked) | — | — |
