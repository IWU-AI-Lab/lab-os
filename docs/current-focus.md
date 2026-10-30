# Current Focus — Fast track to the "hand → robot hand" demo

**Read this at the start of every Claude Code session.** It says what to work on *now*. The long-term plan, decisions and module list live in **lab-jarvis-log.md** — this file only sets the current priority. When this focus is done, replace this file with the next one. Repository setup: see **project-scaffold.md**.

---

## The goal right now
A visitor puts on a Quest 3, and a robot arm copies their **bare hand** live (hand tracking, no glove): reach, rotate, pinch to grab. Within ~30 seconds they pick up a block with the robot.

**Second act (after the first works):** the arm does tasks on its own — ideally ones that **generalize** (new objects, new spots), not just one memorized task. See "Second act options" below. The teleop setup is also the **data-collection tool** for training (incl. the lab's training project if `so101-white` joins it).

## Monday lab checklist (2026-10-26)
In-lab tasks only; everything else can be done from home. Tick them off here and note surprises in `docs/GOTCHAS.md`. `so101-green` may be plugged in: leave it alone.

- [x] **Raspbots** *(done 2026-10-27; MACs in the table)*: read raspbot #2's Wi-Fi MAC (`ip link` → the `wlan0` entry's `link/ether`), add it to the device table in `network-setup-checklist.md` step 1. Rename both: `sudo hostnamectl set-hostname raspbot1` / `raspbot2` (step 4; change the default passwords while you're in there).
- [x] **xarm1, identify** *(2026-10-27)*: it's a **HID device, not serial**: USB ID `0483:5750`, manufacturer "Hiwonder", product "xArm", USB serial `720710C0D60063300023D4D4` (showed up as `/dev/hidraw4`, root-only). Still to do in a coding session: add it to `config/devices.yaml` by that USB ID + serial. Before the driver works the builder runs (once, normal terminal): hidapi install + a udev access rule (see `GOTCHAS.md`). **Config part done 2026-10-27:** `config/devices.yaml` has `xarm1` by USB ID + product + serial; `lab_os.devices.find_usb_device()` resolves it on any OS.
- [x] **xarm1, driver** *(read-only part done 2026-10-27)*: `lab_os.robots.xarm.XArm` (same interface as `FakeArm`; library `hid`, see GOTCHAS). Reads all 6 servos + battery (8.07 V); **~29 reads/s** (median 30 ms/read, ~8 timeouts per 5 s). Motion is blocked in code (`allow_motion=False`) until the motion test. Check yourself: `uv run python -m lab_os.robots.xarm`.
- [x] **xarm1, motion test** *(first pass 2026-10-27, builder OK, arm clamped)*: all six servos move in small slow steps (±40 units, 1 s). **Polling faster than ~0.1 s makes the board drop moves** (driver now paces reads at 0.25 s). Delay 0.25–0.8 s to first motion (coarse); stops 3–15 units short; streamed 100 ms moves at 20 and 50/s are followed. Servos are limp after power-on until the board's "Run" button. Details in `GOTCHAS.md`. Joint directions set from the builder's observations ("front" = board side). Still open:, a precise delay measurement, hold-position on stop. Re-run: `uv run python -m lab_os.robots.xarm_motion_test`.
- [ ] **xarm1, desktop teleop test (Quest on hold for account access):** `uv run lab-os-teleop --arm xarm1 --speed 0.2 serve` → desktop control (keyboard + trackpad), docs/quest-setup.md section 2. *Code ready 2026-10-27; started without input (no motion), not yet driven.* Check: directions feel right from behind the arm, smoothness, freeze on release/Esc.
- [x] **Quest access** *(2026-10-29: developer mode on for the Quest 3 with serial `2G97C5ZHB300FG`. The builder signed the lab account into the Meta Horizon app on their own phone and added **their phone number** (temporary: remove it later or move it to the lab's own number, see Open questions → Quest ownership). `adb devices` shows `device`. The Quest uses the builder's **phone hotspot** for internet (account, updates) until the travel router arrives; teleop itself goes over the USB cable (`adb reverse`). **First real-Quest teleop worked 2026-10-29** (software xArm, IK): "sort of scuffed, but it does"; wrist roll was mirrored → fixed. Before that: blocked, see GOTCHAS 2026-10-29.)*: check whether developer mode is on (or can be turned on) for the lab's Quest 3s, and find out **who controls the lab's Meta account** (developer mode needs that account in a developer organization).
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
8. **Portable from day one:** nothing that only works on the lab desktop or lab network. **The brain runs on Linux, Windows and macOS** (decision 2026-10-27): identify USB devices by USB ID + serial number, not OS paths. Do this as part of the xArm driver work, since the xArm has no `/dev/serial/by-id/` name anyway.

## Steps (each one is a small, testable win)
-1. ~~**Scaffold the repo** per project-scaffold.md "Day one" (README, CLAUDE.md, docs/, SAFETY.md, .gitignore, .env.example, config/, calibration/, lock file, install script, tests + fake robot, formatter). Keep it quick — an hour, not a week.~~ **Done 2026-10-24.** Still open from Day one: LICENSE (ask the professor).
0. ~~**In parallel:** build + calibrate `so101-white`.~~ **Follower done 2026-10-30** (leader arm not built yet). *2026-10-29: LeRobot 0.6.1 is in lab-os as the optional extra `so101`; guarded motor setup / check / calibration command ready, not yet run on the motors (`uv run --extra so101 python -m lab_os.robots.so101_setup setup-motors`; calibration files go to `calibration/so101-white/`). The builder is at the motor-setup stage. Driver `lab_os.robots.so101.SO101Arm` (LeRobot's bus, read-only unless `allow_motion`; tested against a fake bus only). Builder's order: `setup-motors` → assemble → `check` → `calibrate` → read-only check `uv run --extra so101 python -m lab_os.robots.so101` → check joint signs → `lab-os-teleop --arm so101-white --speed 0.2 serve` (ask first).* *2026-10-30: done up to the joint signs. Motors set up, arm assembled, board swapped to `…2410` (devices.yaml), calibrated (`calibration/so101-white/`), read-only check OK (939 reads/s, 0 failed), all six directions match the URDF (`--watch`). First powered teleop at `--speed 0.2` (desktop control, builder's OK): went well. Then the real Quest (IK) at `--speed 0.2`: "went great".*
1. **Arm works from a computer.** `xarm1` over USB HID (`lab_os.robots.xarm`): move each servo, read positions, measure commands/second and delay. `so101-white` with LeRobot (`lab_os.robots.so101`): *works on the real arm 2026-10-30.*
2. **Controller data reaches the computer.** WebXR page in the Quest browser → controller pose + buttons → WebSocket over USB → printed live. *Software done 2026-10-24 and tested with replay + emulator (`lab-os-teleop`, docs/quest-setup.md); real-Quest test pending (Monday checklist).*
3. **Cheap first mapping with clutch control.** First visible win. *Done on the fake arm 2026-10-24 (joint-space, `teleop/mapping.py`); real arm pending step 1.*
4. **Proper mapping.** Inverse kinematics (SO-101 URDF; xArm needs one). *xArm done 2026-10-29 in software (`lab_os/kinematics.py`, mapper IK mode, `--arm fake-xarm1` to try it at home): hand forward/left/up → gripper forward/left/up at 0.5×, controller pitch = gripper tilt, roll = wrist_roll. Not yet driven on the real arm (ask first). **SO-101 done 2026-10-29 in software:** `so101_kinematics()` reads `models/so101` (URDF chain), same IK and tests as the xArm; the default fake arm (`serve` with no `--arm`) now uses it, from a new home pose above the table. Per-arm `roll_sign` (the arms roll opposite ways, GOTCHAS 2026-10-29). **Real SO-101 driven from the real Quest 2026-10-30** at `--speed 0.2`: "went great".*
5. **Quest display basics.** Passthrough + status panel + stop + workspace box. *Partly done 2026-10-24 (`web/xr-scene.js`): ghost arm (see-through in AR) driven by the driver's commands, status panel, controller markers + clutch line, A/X stop. Still to do: visitor hint; the **HUD mini-arm** (below); the workspace warning shown on the HUD mini-arm + status panel.*
   - **No ghost arm lined up on the real arm** (decision 2026-10-28): lining it up needs calibration and the real arm is visible anyway. Instead a **HUD mini-arm**: a small floating copy of the arm that lazily follows your view (drifts back into view when you turn, rather than being glued to your face, which causes discomfort; or sits on the wrist). It shows *what was commanded*: frozen, at a soft limit (joint turns red near its limit = the "workspace boundary"). Reuses `web/arm/arm-model.js` + `ArmFeed`. The status panel follows the same lazy-follow rule instead of being fixed in the room.
6. **Hand-tracking input.** Same pipeline; per-user calibration.
6b. ~~**One driver at a time + training cameras off limits**~~ **Done 2026-10-29** (`teleop/server.py` control handover, STOP button on every page incl. the monitor; `training-cameras` in `config/devices.yaml`, blocked by model `0c45:6366` via `devices.check_usb_allowed()`). *(found 2026-10-28, do before the Quest test)*: the teleop server merges input from **every** connected input page into one stream (e.g. a desktop-control tab + the Quest → two hands interleaved on the real arm), and one page's `session_end` freezes input for all. Fix: one input page "has control"; others can watch; STOP works from every page. Control is **handed over** (the current driver releases it), not grabbed (decision 2026-10-28). Also mark the two training cameras off limits in `config/devices.yaml` (see GOTCHAS 2026-10-28: identical serials, so by USB socket or by model).
7. **Make it feel good.** Smoothing, latency, limits, dead-man freeze. *Builder, 2026-10-30 (SO-101 + Quest at `--speed 0.2`, 24 °/s per joint): "much more intuitive if it was much faster". Raise the speed step by step (the venue allows up to 0.5) and find what limits it.*
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

## Known teleop issues (builder's testing, 2026-10-28)
Seen while testing desktop control on the real xArm and the browser XR emulator. Guesses at causes are marked "?".

**Fix now (cheap, or a safety issue on the real arm):**
- ~~**Wrist roll spins all the way around**~~ *fixed 2026-10-29: angles are unwrapped, the soft limit holds the joint (`test_rolling_past_180_never_spins_the_wrist_around`).* When it reaches one end ("rebounds"). ? An angle wrap-around bug (an angle jumping from +180° to −180°). On the real arm a sudden full turn is exactly the "snapping" the glove taught us to avoid, so treat it as a safety bug: clamp, never wrap.
- ~~**Wrist flex also moves another joint.**~~ *fixed 2026-10-29: rotation is now measured in room axes; with a tilted controller, pitch leaked ~17° into roll.* ? Rotation math mixing axes in the joint-space mapping.
- ~~**Rotation too sensitive** in desktop control.~~ *Arrow keys 90 → 30 °/s.*
- ~~**The monitor page shows the SO-101 while the xArm is driven.**~~ *Already picked from `status.arm.model`; most likely a stale cached script (checked: a fresh browser picks "xArm 1S"). Fixed by `Cache-Control: no-cache` (GOTCHAS 2026-10-29).* The page should pick the 3D model from the connected arm (`Arm` already declares `model`).

**Desktop control rethought (builder, 2026-10-29):** the virtual hand stays unintuitive, so desktop control now has three swappable modes: **Keys** (key pair per motor), **Mouse** (hold a motor key + move the mouse, buttons = gripper) and the **virtual hand** (prototype, kept). Keys/Mouse send `joint_input` and never use IK; **IK is only for pose devices** (Quest, glove; the virtual hand counts as one). *Done 2026-10-29; Keys tested in headless Brave on the software xArm; Mouse not yet tried in a browser.* **Real xArm, 2026-10-29 (builder's OK):** Keys-mode messages through the server at `--speed 0.2` (12 °/s): wrist roll +18°, gripper +12°, base +18° and back each moved only that joint, stopping 1–3° short (servo deadband); leaving froze the arm and freed control. Builder then found it slow/choppy with occasional limp motors → driver reworked (worker thread, lead targets, safe limits; GOTCHAS 2026-10-29); re-test: 18° jogs land within 0.3°. **Next for the builder:** measure the limits by hand once (`uv run python -m lab_os.robots.xarm calibrate`, servos limp: switch on without pressing Run), then try Keys at `--speed 0.4`.

**Fix with IK (step 4), not by patching the joint-space mapping** (it gets replaced): *IK is in for the xArm (2026-10-29); re-check both items with `--arm fake-xarm1` / the real arm.*
- In the XR emulator, only up/down really controls the arm; nothing else does.
- Desktop control moves single joints (WASD/RF/arrows). With IK, the same keys move the **hand** in space (forward/left/up…) and the arm works out its joints. That's the right desktop mode. Note: with IK, moving your hand *will* move several joints at once; that's intended.

**Check, may be correct:**
- **Shift+WASD in the emulator moves the arm.** That moves the emulated *player*, and the controllers move with you. If the clutch is held, the arm should follow (your hand really moved in the room). If it moves with the clutch released, that's a bug.

**XR UI is fixed in the room, not following you:** handled by the lazy-follow HUD (step 5).

**Emulator vs. real Quest:** don't polish the emulator experience by hand; it's for automated tests. The real Quest is the judge once developer mode works. Desktop control stays as the everyday tool at a computer.

**End goal (unchanged):** on well-equipped inputs (Quest hand tracking, controllers, glove), no buttons besides the clutch (and a pinch/trigger for the gripper): the arm just follows your hand.

**Order:** 6b → the "fix now" list → IK (step 4) → step 5 → Quest test when developer mode is on.

## Early risks to test first (spikes)
- `xarm1` commands/second and delay over USB.
- Quest WebXR: controller pose + hand tracking; passthrough overlays; USB port forwarding (needs Quest developer mode).
- IK library for the SO-101 URDF (and an xArm 1S URDF?).
- `so101-white` calibration with LeRobot; LeRobot on the laptop's OS.
- End-to-end delay.
- (Second act) Gemini Robotics-ER 2 pointing accuracy on our camera + camera-to-arm calibration; SmolVLA training on 12 GB.

## Hacks to clean up
- `robots/xarm.py`: 240°/1000 units is the datasheet scale, not measured (zero = the "Run" pose, signs observed 2026-10-27). Motion tuning (`lead_s` 0.3 s, `max_deg_per_s` 120, `idle_read_after_s` 0.6, `min_read_interval_s` 0.25) is from first tests, not optimized. Default limits (until hand calibration) come from the builder's grab script.

## Up next (after the teleop demo works)
**Troubleshooting suite.** *Why:* the health checks / roll call will discover problems, and then I, a future maintainer, or an AI agent need an easy way to diagnose them. It's also the most concretely useful feature so far, and it targets the on-the-ground papercuts I keep hitting.

Checks:
- **Microphone:** level meter, background-noise measurement, record and play back.
- **Cameras:** live view; "is it actually sending images?"
- **Robots:** live joint readings; a small test wiggle (**only with my OK**).
- **Network:** can each device be reached, and how much delay.
- **Accounts:** are API keys present and working; credits available.
- **Quest:** connected or not.

Each check writes a **report file** that humans and agents can read.

(Ideas that aren't the current focus or this next step live in `docs/ideas.md`.)
