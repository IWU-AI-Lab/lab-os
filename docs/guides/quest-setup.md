# Quest input: at home (no headset) and on the real Quest (USB)

The teleop program serves a WebXR page and receives the controller data over a WebSocket. By default it drives the **fake arm**; real arms (`--arm xarm1`, `--arm so101-white`) always need the builder's OK before motion.

```bash
uv run lab-os-teleop serve                         # XR page + live fake arm
uv run lab-os-teleop serve --record recordings/try1.jsonl
uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl   # no browser needed
```
Then open **http://localhost:8080/monitor** to watch the fake arm. **Under `uv run lab-os serve`** (the brain with the hub, `docs/guides/hub.md`) the same page is at **http://localhost:8080/teleop**; `/`, `/ws` and `/monitor` work the same otherwise, so use `/teleop` wherever this page says `http://localhost:8080/`. In VS Code, the Run and Debug panel has buttons for each of these (`.vscode/launch.json`).

**3D view** (on both pages): draws exactly the joint angles the arm driver receives, per command, unclamped. Pick the model in its dropdown: SO-101 (real URDF meshes), SO-101 stick figure, or xArm 1S boxes. Drag to orbit, scroll to zoom. Beside it (under it on a narrow screen) the joint readout: one row per joint, always all of them, each a fixed height, so the 3D view never changes size; a row's note (in accent color, cut with … — hover for all of it) flags a joint the driver clamped, or a joint the driver holds outside the arm's limits in force (the driver's own, from its status: the URDF narrowed by the calibration; since 2026-11-17, quick job 24; the 3D model's limits only until the driver's arrive); the arm turns dark red while frozen. Works offline (three.js and the model are in the repo). Note: control is relative, so `replay --loop` adds the same motion every loop until joints reach their soft limits (3° inside the real ones). There the clutch slips: the arm stops, and moving the hand back moves it back right away.

Controls: **grip** held = clutch (arm follows, relative to where it is) · **trigger** = gripper (released = open, fully pressed = closed; applied while the clutch is held) · **A/X** = stop · right **thumbstick** up/down = speed (5 % steps, up to the venue's cap; also the Speed slider on the page) · **left grip** held = move and turn the 3D arm, **Y** = put it back. The arm freezes when the grip is released, tracking is lost, the connection drops, or the session ends. After a freeze, release and re-press the grip.

**Bare hands** (put the controllers down; the Quest switches to hand tracking by itself): the **right wrist** moves the arm like the controller, hold a **left pinch** (thumb on index finger) = clutch, **right pinch** = gripper (fingers apart = open, touching = closed). Let go of the left pinch and the arm holds still. Each hand's ball grows as you pinch; the left one turns green once the pinch holds the clutch, the right one while the arm follows. Without finger tracking (the Quest then offers hands as simple controllers) the page uses the Quest's own pinch instead. No stop gesture: let go, or STOP on a screen. Palm up + pinch is the Quest's own menu gesture, so pinch with the palm down or sideways.

**Lining the 3D arm up with the real one:** hold the left grip and move: the ghost follows the controller (and turns with it); let go to leave it there. It's kept in the Quest's browser for next time. Once it sits on the real arm, hand moves are sent in *its* direction: push your hand toward the arm's front and the gripper goes forward, from whichever side you stand.

---

## 1. At home: replay (zero setup)
`uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl --loop` plays a synthetic 7-second session (grab, move, squeeze, release, move back without the arm following, grab again). Open the monitor page to watch it. Add `--speed 0.5` to slow it down.

## 2. At a computer: desktop control
`uv run lab-os-teleop serve` (fake SO-101), `--arm fake-xarm1` (software xArm) or `--arm xarm1 --speed 0.2` (the real one). Open **http://localhost:8080/**, pick a **mode** under "Desktop control: mode and keys", then click **Desktop control**. The page captures the pointer; **Esc** leaves (the arm freezes and another page may take over). In full screen in Chrome or Edge, Esc does only that and the page stays full screen (Keyboard Lock; hold Esc to leave full screen; since 2026-11-16). **X** = STOP in every mode. The key table on the page is built from the connected arm's joints.

| Mode | How | Goes through |
|---|---|---|
| **Keys** (default) | one key pair per motor, hold to turn: D/A base, W/S shoulder, R/F elbow, T/G wrist tilt, Q/E wrist roll, V/C gripper open/close. Shift = slow. | joint jogging (`joint_input`), never IK |
| **Mouse** | hold 1–5 (base, shoulder, elbow, wrist tilt, wrist roll) and move the mouse; left/right button = gripper open/close. Shift = slow. | joint jogging |
| **Virtual hand** (prototype) | a pretend Quest controller: Space = clutch, trackpad/WASD/RF move it, arrows tilt/roll, C gripper. Unintuitive on a desk; kept because it costs nothing and tests the Quest path. | pose (`xr_input`): IK on the xArm, joint space on the SO-101 |

**Real arm (xarm1):** before starting: arm clamped, area clear, power plug in reach, and if the servos are limp press the board's **Run** button (the arm stands up by itself). Stand **behind the arm, opposite the controller board** (the board side is the arm's "front", docs/dev/GOTCHAS.md), so "forward" and "right" match. Motors move only while a key/button is held; a move already sent still finishes (≤ ~0.1 s).

## 3. At home: browser WebXR emulator
1. In Chrome or Brave (both work on the lab desktop), install Meta's **Immersive Web Emulator** extension from the Chrome Web Store.
2. `uv run lab-os-teleop serve --record recordings/emulator.jsonl`
3. Open **http://localhost:8080/**, then open DevTools (F12) → the **WebXR** tab. Pick a Quest 3 device.
4. Click **Enter AR** / **Enter VR** on the page.
5. In the WebXR tab, drag the right controller's gizmo to move it; use the grip and trigger sliders and the button toggles. Watch the page's readout, the terminal line, and the monitor tab.
6. Stop with `Ctrl+C`. The recording can be replayed (section 1) or turned into a test.

The trigger is the gripper: use the right controller's trigger control in the emulator's panel. For everyday testing, desktop control (section 2) is easier to steer than the emulator's gizmos.

`localhost` counts as a secure context, so WebXR works over plain `http://`. No certificates needed.

**What you see inside the session** (emulator or headset): the arm standing on a table in front of you, facing away (you operate it from behind), moving with exactly what the driver receives. Also a marker on each controller (the right one turns green while the clutch is held), a dashed line from where you grabbed, and a floating status panel (FOLLOWING / HOLDING / FROZEN, gripper, speed). In VR there's a dim room and a table. In AR (passthrough on the Quest) the arm is a see-through ghost and the real room shows. Add `?xrarm=stick` to the page URL for the lighter stick-figure arm.

## 4. The real Quest over USB
The trick: the Quest's browser opens `http://localhost:8080`, and **`adb reverse`** forwards the headset's port 8080 through the USB cable to the desktop. To the browser it's still `localhost` (secure, WebXR allowed), and nothing goes over the lab network.

One-time:
1. **Developer mode** on the Quest. The headset must belong to a Meta account that's in a (free) developer organization. Turn it on in the Meta Horizon phone app → Devices → the headset → Developer mode. *Needs whoever controls the lab's Meta account.*
2. Install adb on the desktop (in a normal terminal): `sudo apt install adb`
3. Plug the Quest into the desktop with a USB-C data cable. In the headset, accept **"Allow USB debugging"** (tick "always allow from this computer").
4. Check: `adb devices` should list the headset as `device` (not `unauthorized`).

Each session, with the brain (the hub runs too):
```bash
uv run lab-os serve                    # fake arm
adb reverse tcp:8080 tcp:8080          # re-run after every re-plug
```
In the headset: open **Quest Browser** → `http://localhost:8080/teleop` → **Enter AR (passthrough)**. Hold the grip and move the controller; `http://localhost:8080/monitor` on the desktop should follow. If the redesigned page misbehaves in the Quest's browser, `http://localhost:8080/classic/teleop` is the old one.

Teleop on its own (no hub; it can record): `uv run lab-os-teleop serve --record recordings/quest-$(date +%F).jsonl`, and the page is `http://localhost:8080` (no `/teleop`).

**Real SO-101:** `uv run --extra so101 lab-os serve --arm so101-white --speed 0.2` (or `uv run --extra so101 lab-os-teleop --arm so101-white --speed 0.2 serve`), then the same `adb reverse` and page. Without `--speed` it runs at the venue's maximum (`max_speed_scale`, 0.5 in the lab). The SO-101 is driven by IK (hand forward/left/up → gripper forward/left/up, controller tilt/roll → wrist). Close any desktop-control tab first (one page has control at a time). Ctrl+C turns torque off and the arm goes limp: hold it or park it low first.

**Relative mode (the default) since 2026-11-16:** 10 cm of hand = **10 cm** of gripper (it was 5 cm), and the arm follows at the 1:1 follow speed scaled by the Speed slider: the slider at its top (the venue's `max_speed_scale`) = `one_to_one_max_deg_per_s` (180°/s in the lab), half way = half. It was at most 45°/s, so the arm fell far behind the hand (`docs/dev/existing-work-teleop-ai.md`: LeRobot's Isaac Teleop and telegrip both drive at scale 1). Where 1:1 is off (visit days) relative keeps the old, slower speed. Hot servos (60 °C) slow it down like 1:1. With `--speed 0.2` in the lab that's 72°/s: push the right thumbstick up for more.

### 1:1 mode: the gripper stays with your hand
On the teleop page, **Hand → arm → 1:1** (the brain keeps the choice until it restarts; relative is the default). Then in the headset:
1. **Line up** the 3D arm on the real one: hold the left **Grip**, move and turn it until the see-through arm sits on the real one, let go (kept in the Quest's browser; **Y** puts it back).
2. Put your right hand in the **green ball** at the 3D gripper (the panel says "REACH THE GRIPPER · 14 cm" until you're within 8 cm) and hold **Grip**. Nothing jumps: the small distance between hand and gripper at that moment is kept.
3. Move: the gripper goes where your hand goes, the same distance (not half). Out of reach or below the table, the arm waits as close as it gets and follows again when your hand comes back, so hand and arm never drift apart. Let go to pause; grab again at the gripper.

**Scale (checked 2026-11-16, quick job 13):** nothing in the chain scales the hand: metres from the Quest, the 3D arm at real size (the URDF), the real arm's link lengths, LeRobot's gripper point. If 1:1 feels off on the real arm, it's the arm (sag, the height offset) or the lag; lab checks 7.2–7.4 measure it. One fix: on a headset without a floor-level space the hand was measured from the wrong base (`docs/dev/GOTCHAS.md`).

**Speed (2026-11-11):** 1:1 isn't slowed by the Speed slider or the venue's top speed: each joint turns as fast as the hand needs, up to the venue's `one_to_one_max_deg_per_s` (**180°/s in the lab**; off on visit days and at new places). Change it in ⚙ Settings → Robots → **Teleop 1:1: top joint speed** (off / 90 / 120 / 180 / 240 / none; `none` = no software cap, the servos' own top speed of roughly 270–310°/s), then restart the brain. For scale: a quick wave (1.5 Hz, 10 cm side to side) needs ~120°/s at the base; the old lab speed (~45°/s) kept only ~60 % of it. The panel and the page say "1:1 up to 180°/s".

**The servos' health:** with a real SO-101 the brain reads each servo's temperature, load and voltage every 5 s and logs them to `logs/servo-health/<date>_<arm>.jsonl` (with the mode, so relative and 1:1 sessions can be compared). A servo at **60 °C** slows 1:1 down to relative speed (the panel says "SERVOS WARM, SLOWED"); the servos switch themselves off at 70 °C. Whether 1:1 wears the motors more: compare the temperatures of a relative and a 1:1 session of the same length.

Tilt and roll stay relative (degree for degree from the grab). Bare hands work too: the right wrist in the ball, left pinch = clutch. Desktop control and old recordings have no arm position, so they stay relative. Replay a new recording in 1:1: `uv run lab-os-teleop replay recordings/<file>.jsonl --mode one_to_one` (a recording made in 1:1 switches by itself).

Why: in the relative mode (then 10 cm of hand = 5 cm of gripper) the hand drifted away from the arm and needed re-grabbing again and again (decision 2026-11-10).

### Tuning: when it doesn't follow well
Record a session, then replay it without the Quest (and without the real arm):
```bash
uv run lab-os serve --arm so101-white --speed 0.2 --record recordings/quest-$(date +%F).jsonl
uv run lab-os-teleop replay recordings/quest-2026-11-10.jsonl      # the fake arm; watch /monitor
```
A recording is what Claude needs to find where it goes wrong ("at 0:40 the elbow straightens"). The knobs are in `MappingConfig` (`src/lab_os/teleop/mapping.py`):
- `tip_m_per_hand_m` (1.0 since 2026-11-16, 0.5 before): relative mode, 10 cm of hand → 10 cm of gripper. Lower = finer and more "it doesn't follow"; higher = jumpier. (1:1 is always 1.)
- Relative speed: `TeleopLoop.relative_cap()` (the 1:1 follow speed × the Speed slider's share of its top); `MappingConfig.max_deg_per_s` (90 × speed) only where 1:1 is off.
- `capture_m` (0.08): 1:1, how close the hand must be to the gripper to grab it.
- the floor: since 2026-11-14 the venue's `ai_tools.min_z_cm` sets it (−0.5 cm in both venues, since the arm stands on the stand camera's base; `MappingConfig.floor_m` is only the default), and the AI tools use the same number. The gripper and wrist stay above it. Raise it if the real arm still touches the table (it sags under its own weight when stretched out). Settings → Safety limits can switch it off (not on visit days).
- The speed (slider, thumbstick, `--speed`): at 0.2 the arm lags far behind a quick hand.

**The hub in VR:** `http://localhost:8080/xr` in the Quest's browser → **Enter VR** (or AR). The startup plays around you as on the designed hub's screen: pull the trigger (or pinch) to start, again to skip it. Then the hub is around you: point at a callout with a controller (or your hand) and pull the trigger (or pinch) to open its details; 7d/14d/30d, List all and a device's card work too. **B** or **Y** closes a page. The trigger no longer replays the jump: ⏻ (top right) goes back to the start screen.
- **Teleop** (left of the core) opens the arm scene without leaving VR: everything above works the same (grip = clutch, trigger = gripper, A/X = stop, left grip moves the 3D arm, Y puts it back). Back: **B**, or point the right controller at ← on the TELEOP tab (top left) and pull the trigger. The left hand's pinch and Y stay teleop's.
- **Asking:** point at the ask line under the core ("Ask anything"), **hold** the trigger (or a pinch), talk, let go: the answer types out under the core and is spoken. Where the brain has the wake word, "hey Jarvis" works too while the hub is up (a small dot in the strip; nothing open). Before entering VR, press **Allow the microphone** on the page once (the browser remembers; a question about the microphone inside VR is easy to miss). A question asked on the desktop (its own microphone) shows in VR too; the desktop speaks that answer.
- **Monitor** and **AI Control** show the arm as a hologram (watch-only), with each joint's angle, who has control, STOP; AI Control adds the robot-tool calls as they happen. Back: B or Y, or ←.

**Testing without a headset:** the Immersive Web Emulator (section 3) works for `/xr` too: Enter VR, then move the right controller's gizmo and use its trigger and buttons. For a scripted check, Meta's emulator engine (`npm i iwer`, with `playwright-core` and Chrome) can run the page headless: install `IWER.XRDevice(IWER.metaQuest3)` before the page loads, click Enter VR, set `controllers.right.quaternion` to aim and `updateButtonValue("trigger", 1)` to press, and take screenshots. `/xr?slow=10` plays everything ten times slower and silent, so each moment of the startup can be looked at. Limits: headless Chrome draws the scene in software at ~7 frames a second, so teleop's dead-man stop freezes the arm right after the clutch engages (GOTCHAS 2026-10-24): the arm following needs the headset. Chrome's fake microphone (`--use-file-for-fake-audio-capture`, GOTCHAS 2026-11-12) gives the ask line a spoken question.

Troubleshooting:
- Page doesn't load → `adb reverse --list` should show `tcp:8080 tcp:8080`; re-run it after re-plugging.
- `unauthorized` in `adb devices` → put the headset on and accept the USB debugging prompt.
- "WebXR not available" → the URL must be exactly `http://localhost:8080`, not the desktop's IP address (that's not a secure context).
- Arm shows "frozen: release grip" → release the grip fully, then press again.

Later (not needed for the demo): Wi-Fi instead of USB needs HTTPS with a certificate the Quest trusts, or `adb` over Wi-Fi. USB is simpler and portable (see docs/archive/focus-2026-10-teleop-demo.md, "Fewest moving parts").
