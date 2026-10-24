# Current Focus — Fast track to the "hand → robot hand" demo

**Read this at the start of every Claude Code session.** It says what to work on *now*. The long-term plan, decisions and module list live in **lab-jarvis-log.md** — this file only sets the current priority. When this focus is done, replace this file with the next one. Repository setup: see **project-scaffold.md**.

---

## The goal right now
A visitor puts on a Quest 3, and a robot arm copies their **bare hand** live (hand tracking, no glove): reach, rotate, pinch to grab. Within ~30 seconds they pick up a block with the robot.

**Second act (after the first works):** the arm does tasks on its own — ideally ones that **generalize** (new objects, new spots), not just one memorized task. See "Second act options" below. The teleop setup is also the **data-collection tool** for training (incl. the lab's training project if `so101-white` joins it).

## Monday lab checklist (2026-10-26)
In-lab tasks only; everything else can be done from home. Tick them off here and note surprises in `docs/GOTCHAS.md`. `so101-green` may be plugged in: leave it alone.

- [ ] **Raspbots:** read raspbot #2's Wi-Fi MAC (`ip link` → the `wlan0` entry's `link/ether`), add it to the device table in `network-setup-checklist.md` step 1. Rename both: `sudo hostnamectl set-hostname raspbot1` / `raspbot2` (step 4; change the default passwords while you're in there).
- [ ] **xarm1, identify:** plug it into the lab desktop; Claude identifies it from `lsusb` / `/dev/serial/by-id/` (or its HID device) **without opening anything else**, and adds it to `config/devices.yaml`.
- [ ] **xarm1, driver:** an `Arm` plug-in (same interface as `FakeArm`), read-only first: read servo positions, measure reads/second.
- [ ] **xarm1, motion test (ask first):** only after the builder's OK, with the arm clamped, the area clear and the power plug in reach (`SAFETY.md`). Small, slow single-servo moves; measure commands/second and command→motion delay. Record the numbers in `docs/GOTCHAS.md` (or a decision note) and step 1 below.
- [ ] **Quest access:** check whether developer mode is on (or can be turned on) for the lab's Quest 3s, and find out **who controls the lab's Meta account** (developer mode needs that account in a developer organization).
- [ ] **If developer mode works:** run the real Quest data test from `docs/quest-setup.md` section 3 (`adb reverse` + `http://localhost:8080`), drive the fake arm, and save a recording (`serve --record recordings/quest-2026-10-26.jsonl`). Commit a short clip as a test fixture.

## Which arm
- **`so101-green`** — built SO-101 set, **in use for another training project. Don't touch/recalibrate.**
- **`so101-white`** — second SO-101 set (leader + follower); parts printed except camera mounts. **Polished demo + second act.** Smoother motors, LeRobot support, existing URDF.
- **`xarm1`** — built xArm 1S, works over USB. **Prototype teleop on it now**; measure its update rate and delay.

## Which Quest input: both, as two input plug-ins
Controllers first (grip = clutch, analog trigger = gripper, button = stop; steadier; best for recording training demonstrations), then hand tracking (best wow for visitors). Same pipeline; keep both.

## What the Quest shows
Mixed reality (passthrough): the real arm + a minimal overlay — status panel (connected / clutch / gripper % / speed), clear STOP, workspace boundary box (red near the edge), a one-line visitor hint until their first grab. Later: "ghost arm," arm camera feed window, short launch animation. Cast to a monitor for onlookers. Hand tracking needs reasonable light.

## Portable demo kit
No lab network needed (USB). Kit: Quest + controllers (charged) · laptop with the teleop software · arm + power supply · USB cables · table clamp · block + target mat · extension cord · optional monitor/casting. Calibration files travel with the arm. Arrive-early checklist: clamp, power, calibration/limit check, test stop + clutch, set workspace for the new table. Padded transport box. Quest ~2 h battery.

## Design requirements learned from the Hiwonder glove
1. **No extreme gestures** — calibrate per user; comfortable thresholds with hysteresis.
2. **No snapping** — relative ("clutch") or speed control; start from the arm's current position; gentle ramps.
3. **No one-motor-at-a-time mode switching** — whole-arm control via inverse kinematics.
4. **Keep what worked** — tilt-for-rotation; low lag; stable connection.

## Rules for the fast track
1. **Everything else waits.** No other modules until the demo works.
2. **Fast, but on the seams.** Teleop module = *input* (Quest controllers, hand tracking; glove/leader arm later) → *robot* (xArm or SO-101).
3. **Hacks are allowed but labeled.** `# HACK:` + a line in "Hacks to clean up."
4. **Fewest moving parts.** Quest + Linux desktop or laptop + arm; Quest by **USB cable** (port forwarding; `localhost` counts as secure).
5. **Safety from the first motion:** speed limits, limited workspace, **dead-man rule** (clutch released / tracking lost / headset off / connection drops → arm freezes).
6. **Only claim what's real.**
7. **Fake arm first**, then the real arm.
8. **Portable from day one:** nothing that only works on the lab desktop or lab network.

## Steps (each one is a small, testable win)
-1. ~~**Scaffold the repo** per project-scaffold.md "Day one" (README, CLAUDE.md, docs/, SAFETY.md, .gitignore, .env.example, config/, calibration/, lock file, install script, tests + fake robot, formatter). Keep it quick — an hour, not a week.~~ **Done 2026-10-24.** Still open from Day one: LICENSE (ask the professor).
0. **In parallel:** build + calibrate `so101-white`.
1. **Arm works from a computer.** `xarm1` over USB (Python `xarm`): move each servo, read positions, measure commands/second and delay. Later `so101-white` with LeRobot.
2. **Controller data reaches the computer.** WebXR page in the Quest browser → controller pose + buttons → WebSocket over USB → printed live. *Software done 2026-10-24 and tested with replay + emulator (`lab-os-teleop`, docs/quest-setup.md); real-Quest test pending (Monday checklist).*
3. **Cheap first mapping with clutch control.** First visible win. *Done on the fake arm 2026-10-24 (joint-space, `teleop/mapping.py`); real arm pending step 1.*
4. **Proper mapping.** Inverse kinematics (SO-101 URDF; xArm needs one).
5. **Quest display basics.** Passthrough + status panel + stop + workspace box. *Partly done 2026-10-24 (`web/xr-scene.js`): ghost arm (see-through in AR) driven by the driver's commands, status panel, controller markers + clutch line, A/X stop. Still to do: workspace boundary box, visitor hint, placing the ghost arm on the real arm (calibration).*
6. **Hand-tracking input.** Same pipeline; per-user calibration.
7. **Make it feel good.** Smoothing, latency, limits, dead-man freeze.
8. **Visitor polish + portability test.** Script, hint, casting, run once from the laptop away from the lab; tag a known-good version; 60-second clip.
9. **Second act** — see options below.

## Second act options
A small model trained from scratch on one task (e.g. ACT) tends to break with new lighting, positions or objects. Better-generalizing options:

| Option | What it is | Generalizes? | Cost / effort | Notes |
|---|---|---|---|---|
| **A. "Look, then reach"** with **Gemini Robotics-ER 2** (Google's robotics reasoning model, available as a *preview* through the Gemini API) | A camera photo + "where is the red marker?" → the model points to it → our inverse kinematics moves the arm there and grabs | **Yes, to new objects and places — no training** | API calls (user has Gemini keys); needs camera-to-arm calibration (mapping picture positions to table positions) | Best "magic per hour." Works for simple pick-and-place, not delicate skills. Preview = may change. |
| **B. Fine-tune a pretrained robot model (VLA)** — **SmolVLA** (Hugging Face, made for LeRobot/SO-101) | A model already trained on lots of community robot data, then adapted with our own demonstrations (~50 to start, with **varied** conditions) | Better than training from scratch; still limited | Training may fit the RTX 5070 (12 GB) — to verify; reported ~hours on a big GPU | Understands language instructions ("pick up the cube"); best-documented SO-101 route. |
| **C. Bigger open models** — NVIDIA **GR00T N1.6**, Physical Intelligence **π0 / π0.5** | Larger pretrained robot models | Potentially more | Training needs ~22–70 GB GPU memory → **rented cloud GPU**; running may fit locally (GR00T inference on RTX 3080+) | Later, if B isn't enough. |
| **D. Classic ACT** | Small model, one task | Weak | Cheapest | Fine as a first learning exercise only. |

**Plan:** A first (fastest generalizing wow — "put anything on the table and ask it to grab it"), then B (learned skills from our own teleop data, with varied lighting/positions/distractors during recording). **Gemini Robotics** (the full action model) is partner-only — not available.

**Recording tips (for B/C/D):** vary object positions, lighting, backgrounds and distractor objects during demonstrations; record in the demo venue too if possible.

## Early risks to test first (spikes)
- `xarm1` commands/second and delay over USB.
- Quest WebXR: controller pose + hand tracking; passthrough overlays; USB port forwarding (needs Quest developer mode).
- IK library for the SO-101 URDF (and an xArm 1S URDF?).
- `so101-white` calibration with LeRobot; LeRobot on the laptop's OS.
- End-to-end delay.
- (Second act) Gemini Robotics-ER 2 pointing accuracy on our camera + camera-to-arm calibration; SmolVLA training on 12 GB.

## Side task (optional, low priority): fix the glove
Options: (A) re-flash if Hiwonder's glove firmware source exists; (B) glove → computer → arm with the teleop module's logic. Only if fun or useful.

## Hacks to clean up
*(empty — add entries as they happen)*
