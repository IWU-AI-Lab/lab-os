# Existing work vs. ours: Quest teleop and AI arm control (2026-11-16)

The comparison asked for in `docs/plan/ideas.md` ("Teleop: compare…", "AI arm control: compare…") and in focus item 6. I read the code, not only the READMEs (shallow clones of each project on 2026-11-16; nothing was installed or run). **Decided 2026-11-16 (the builder): all recommendations below, and Isaac Teleop after the demo as an input to the brain (`docs/plan/ideas.md` → "Isaac Teleop as an input to the brain").** **Dates:** the demo is now **2026-12-03**. Thursday **2026-11-19** is the first lab day, and nothing new goes in after **2026-11-24**. The costs below are counted against those dates.

## Projects looked at
| Project | Stars / last change / license | What it is |
|---|---|---|
| LeRobot `examples/isaac_teleop_to_so101` (HF + NVIDIA) | official, changed 2026-11 | Quest via NVIDIA CloudXR → SO-101, Placo IK, records LeRobot datasets |
| telegrip (DipFlip) | ★145, 2026-03, MIT | WebXR page → one or two SO-100/101 arms, PyBullet IK |
| XLeRobot (Vector-Wangel) | ★5.8k, active, Apache-2.0 | Two-arm home robot. Its VR page "XLeVR" is a fork of telegrip's page with a different mapping |
| google-gemini/robotics-pointing-sample | official, 2026-02, Apache-2.0 | SO-101 + one camera + Gemini: points at a named object |
| robot_MCP (IliaLarchenko) | ★88, 2025-08, Apache-2.0 | MCP server + small agent for SO-100/101 (Claude, Gemini, GPT); older LeRobot API |
| phosphobot | ★394, 2026-09, MIT | A whole robot platform with its own Quest app. Its MCP server only replays recorded pickups of 3 fixed objects |
| Found by searching, all 0–9★ | 2026 | SO-101-VR-Control (a telegrip fork), vr-teleop-kit, xrtact, VELMA (MCP + wrist-camera triangulation, mostly in simulation, no license), so101-mcp, so101-pick |

None of the newer finds clears the "maintained and actually used" bar. I only took ideas from them, and VELMA has no license, so its code can't be copied.

## 1. Quest teleop: how the hand becomes arm motion
| | **Ours** (`teleop/mapping.py`) | Isaac Teleop (LeRobot) | telegrip | XLeRobot VR |
|---|---|---|---|---|
| Path | Quest browser (WebXR) → USB `adb reverse` → brain | CloudXR stream (needs Linux + NVIDIA GPU); no web page | Quest browser over Wi-Fi, self-signed HTTPS | same page as telegrip |
| Clutch | grip held, with hysteresis (0.6 on, 0.4 off); re-press after a freeze | squeeze above a threshold | grip held | grip held |
| Scale | relative **0.5** (10 cm of hand → 5 cm of gripper); 1:1 mode at 1.0 | **1.0** (relative) | **1.0** (relative) | per-frame deltas ×0.015–3 (feels like a velocity) |
| IK | own damped least squares: x, y, z + gripper tilt, 4 joints, table floor | Placo: position + **full orientation, weighted softly** (0.01) | PyBullet, **position only, 3 joints** | 2-link analytic in the arm's plane; pan driven directly |
| Wrist | pitch → gripper tilt held by the IK (the tilt in the room stays put); roll → wrist_roll; yaw ignored | the whole hand rotation, tracked as far as 5 joints can | pitch → wrist_flex **directly**, so the tilt changes as the arm moves | wrist_flex keeps the tilt + pitch offset |
| Gripper | trigger, analog | trigger, analog | trigger **on/off** | trigger on/off |
| Smoothing | none on the input; a speed ramp, all joints arrive together | none; at most 0.1 m per frame (glitch guard) | none | exponential smoothing, α 0.1 (strong) |
| Speed / delay | page sends every XR frame, 50 Hz loop; **relative tops out at 90°/s × speed 0.5 = 45°/s** (the lab venue caps the speed at 0.5); 1:1 180°/s | 30 Hz, no joint speed cap (the servos' own) | 20 Hz, no cap | P-control |
| Safety | STOP everywhere, dead-man 0.25 s, soft limits, table floor, one controller at a time | stops when you release the squeeze; floor at z ≥ 0 only | joint limits | joint limits |
| Records training data | input JSONL for replay (not LeRobot format) | **LeRobot datasets** (`record.py`) | no | yes (an example script) |

**What this says about "hard to pilot":** both well-used projects drive at **scale 1.0 with no joint speed cap**. Ours drives at **0.5 scale and a 45°/s ceiling** in relative mode, so a normal hand motion outruns the arm and the two drift apart. That matches "doesn't follow" better than anything in the IK. Our wrist handling (the tilt held in the room) is already better than telegrip's and XLeRobot's. Isaac's soft full-orientation IK is the one real improvement on it.

**Recommendation: keep ours, borrow three small parts.**
1. **Relative mode at scale 1.0 and a higher speed ceiling** (from telegrip and Isaac): change `tip_m_per_hand_m` 0.5 → 1.0, and let relative mode use the 1:1 joint speed (or raise `max_deg_per_s` and the venue's `max_speed_scale` in the lab only). Settings only, then the replay check. *Cost: about 1 hour in a session before 11-19; try it on the 11-19 lab day. Low risk: it can be switched back.*
2. **Grab from the measured pose** (Isaac's `Clutch.engage`), probably not needed. Today a grab starts from the SO-101's last command (`read_joints` while driving), which never jumps. Isaac uses the measured pose so that an arm pushed while held doesn't snap back to the old command. That only matters if people push the arm during teleop. *Cost: 1 hour with a test, only if the lab shows it.*
3. **A light filter on the hand pose** (vr-teleop-kit uses α 0.8), only if the arm looks shaky once it's faster. *Cost: 1 hour. Optional.*

**Not before the demo:**
- **Switching to telegrip.** It's no better at the mapping, and we would lose the hub, STOP, the floor, 1:1, the 3D arm, the Quest hub and one controller at a time.
- **Switching to Isaac Teleop.** It's the best-engineered of the four and the right candidate for **recording training data after the demo**, but:
  - It needs CloudXR (a runtime, an EULA, streaming over the network).
  - It bypasses the brain completely.
  - It needs a newer LeRobot than our pinned 0.6.1 (the example lives only in the LeRobot repository), plus `isaacteleop` and Placo in our `so101` extra.
  - **It writes into LeRobot's cache** (it downloads the URDF to `HF_LEROBOT_HOME/robot-urdfs`, and saves reset poses there). It must run with `HF_LEROBOT_HOME` pointed at a lab-os folder (`docs/dev/GOTCHAS.md`).

  *Cost: roughly 1–2 sessions plus a lab day. After the demo.*

## 2. AI arm control
| | **Ours** (MCP, `tools/robot.py`) | Google pointing sample | robot_MCP | VELMA (small, ideas only) |
|---|---|---|---|---|
| Tools | `arm_status`, `move_to` (absolute cm, straight line), `move_joints`, `gripper`, `go_to_pose`, `camera_snapshot`, `pose_view`, `stop`; "stopped short" reports | none: a script runs the loop | `move_robot`: **relative to the gripper** ("up 10 mm, forward 5 mm, turn left 15°"), `control_gripper`, `get_robot_state`; **every move returns pictures from all cameras** | `find_object`, `triangulate`, **`grasp`, `place`** (skills) + low-level moves |
| Camera picture → position | **none**: the AI guesses from the picture (8 cm off on 2026-11-12) | **printed ChArUco board → homography** (pixel → table cm, one-time, saved to a file) | none: look, move, look again | side camera ~1 cm, then the wrist camera from 5 views ~1 mm |
| How a grab is done | the AI composes it, one small move at a time | (it points, doesn't grab) script: hover 10 cm above → down to 2 cm | the AI composes it; prompt rules ("approach from above, tilted 10–15°", "close fully", "check the wrist camera") | a `grasp(x, y, z)` skill |
| Steps the AI needs | ~10 moves to get beside the cube, ~17 calls in all (2026-11-12) | 1 question, then 3 scripted moves | many (look after each small move) | ~4–5 calls |
| Any frontier model? | **yes**: any MCP client (Claude Code, Codex, …). The hub's own chat is text only (no pictures) | Gemini only (0–1000 point format) | Claude, Gemini, GPT (the author: Claude best, GPT worst) | any MCP client or OpenAI-compatible model |

**What this says:** our tools are already the safest and most model-agnostic of the lot. What we lack is what made the 2026-11-12 pick slow and wrong: **no mapping from the camera to the table**, and **no grab skill**, so the AI spends 10+ calls getting close.

**Recommendation: keep ours, borrow two parts (and one optional).**
1. **Camera → table cm with a printed board** (Google's method, ~60 lines of OpenCV, Apache-2.0). Print their calibration PDF and lay it at a measured spot in front of `so101-white`. A one-time `lab-os` step saves the homography per camera. `camera_snapshot` of `cam-a` then draws a **cm grid of the table** on the picture (and/or a `locate(camera, x_px, y_px)` tool returns table cm). A grid works with every model, not only Gemini, because no model has to name exact pixels. OpenCV 4.13 is already in our `so101` extra, so nothing new gets installed. It's only right on the table plane: a 2.5 cm cube's centre is ~1 cm off, and the wrist camera fine-tunes. *Cost: one session (fake picture, tests) before 11-19; 15 min in the lab on 11-19 (print, place, measure, calibrate).*
2. **A `grasp` skill** (Google's hover-then-descend, VELMA's `grasp`): one move tool, `pick_at(x, y)`. Open, go 8 cm above, look straight down, descend, close, lift 5 cm. It's built from our existing `move_to` steps, through the same safety path and STOP, and says each stage (this also covers "say before moving", ideas → "AI picking" 4). The AI's ~17 calls become ~3: look, `pick_at`, check. *Cost: one session before 11-19. It depends on the height zero and the sag being fixed first (focus item 1), or it closes above the cube like on 11-12.*
3. *(Optional)* **robot_MCP's prompt rules** in our MCP instructions. A `look` option on move tools that returns a picture with the result (saves calls, costs tokens). *Cost: ~30 min.*

**Not before the demo:** switching to any of them (robot_MCP uses an old LeRobot API and has no safety layer; Google's sample is Gemini-only and points only). A Gemini Robotics-ER `find_object` tool fits the "What's on the table?" preview. It's model-agnostic for the AI driving the arm, because the tool hides the Gemini call, but the free key's limits are unknown.

## Summary of costs
| Area | Do | Before 11-19 (code) | In the lab |
|---|---|---|---|
| Teleop | scale 1.0 + higher relative speed | ~1 h | try on 11-19 |
| Teleop | pose filter; grab from the measured pose | ~1 h each, only if the lab shows a need | 11-19 / 11-23 |
| AI | printed board → cm grid on `cam-a` | 1 session | 15 min on 11-19 |
| AI | `pick_at` skill | 1 session (after the height/sag fix) | 11-19 or 11-23 |
| Later | Isaac Teleop for recording training data | — | after the demo |
