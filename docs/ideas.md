# Ideas backlog

**The single source of truth for ideas.** New ideas land here, **not in code** and not in other docs, unless they're part of the current focus (`docs/current-focus.md`). This keeps the project finishable and nothing gets lost. When an idea becomes the focus, move it into `current-focus.md` and delete it here. When an idea is decided (but not yet scheduled), record the decision in `lab-jarvis-log.md` and keep or delete the entry here.

Each idea: what it is · why · where it plugs in (slot/module, if known; slots are in `lab-jarvis-log.md` → "Architecture sketch"). "—" = not recorded yet.

**Not here because they're already decided plans:** the teleop second act (Gemini Robotics-ER "look, then reach" → SmolVLA → bigger VLAs via rented GPU) and teleop as data collection for the training project (`current-focus.md`). Also offline lite mode, the portable demo kit, and the staged remote-access plan (`lab-jarvis-log.md` → "Mobility, portability & remote access").

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

### HUD mini-arm in the headset
- **What:** a small floating copy of the arm as part of the heads-up display (lazy-follow panel or on the wrist), instead of a see-through ghost lined up exactly with the real arm.
- **Why:** aligning a ghost with the real arm is hard and unnecessary when the real arm is visible. A HUD copy shows *what was commanded* (frozen, at a soft limit, later lag behind the real arm) without clutter.
- **Plugs into:** Quest display (teleop step 5); reuses `web/arm/arm-model.js` + `ArmFeed`.

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

### Troubleshooting suite
- **What / why / checks:** planned as the next focus after teleop. See `current-focus.md` → "Up next".
- **Plugs into:** health checks / roll call; every check writes a report file that humans and agents can read.

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
