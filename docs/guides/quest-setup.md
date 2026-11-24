# Teleop with the Quest: at home (no headset) and on the real Quest (USB)

The teleop program shows a WebXR page and gets the controller data over a WebSocket. `lab-os-teleop` drives the **fake arm** unless you name a real arm (`--arm xarm1`, `--arm so101-white`). `lab-os serve` drives the SO-101 that is plugged in, else the fake arm (`docs/guides/hub.md` → "Start it"). In a coding session, ask the builder before a real arm moves (`AGENTS.md`).

```bash
uv run lab-os-teleop serve                         # the headset page and the fake arm
uv run lab-os-teleop serve --record recordings/try1.jsonl
uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl   # no browser needed
```
Then open **http://localhost:8080/monitor** to watch the fake arm.

**With the brain** (`uv run lab-os serve`, `docs/guides/hub.md`), the teleop page is at **http://localhost:8080/teleop**. `/ws` and `/monitor` are the same. Where this guide says `http://localhost:8080/`, use `/teleop` with the brain.

In VS Code, the Run and Debug panel has a button for each of these commands (`.vscode/launch.json`).

## What the page shows
**The 3D view** (on the teleop and monitor pages) shows the joint angles that the arm's driver gets, for each command, without limits. Select the model in its list: SO-101 (the real meshes), SO-101 stick figure, or xArm 1S boxes. Drag to turn the view. Scroll to zoom. The view works offline (three.js and the model are in the repository).

**The joint readout** is next to the 3D view (under it on a narrow screen). It has one row for each joint, always all joints, each row the same height, so the 3D view never changes size. A note on a row (accent color) shows a joint that the driver clamped, or a joint that the driver holds outside the arm's limits. Hover over a short note to see all of it. While the arm is frozen, it is dark red.

**Replay and the limits:** control is relative, so `replay --loop` adds the same motion in each loop until the joints get to their soft limits (3° inside the real limits). There the clutch slips: the arm stops, and when the hand moves back, the arm moves back immediately.

## The controls
With the controllers:
- **Grip** (hold): the clutch. The arm follows, relative to where it is.
- **Trigger:** the gripper. Released = open. Fully pressed = closed. It applies while you hold the clutch.
- **A or X:** stop.
- **Right thumbstick** up or down: the speed, in 5 % steps, up to the venue's top speed. The Speed slider on the page does the same.
- **Left grip** (hold): move and turn the 3D arm. **Y** puts it back. With two arms, the left grip drives the second arm (section 6).

The arm freezes when you release the grip, when tracking stops, when the connection drops, or when the session ends. After a freeze, release the grip and press it again.

**Bare hands:** put the controllers down. The Quest changes to hand tracking by itself.
- The **right wrist** moves the arm, like the controller.
- Hold a **left pinch** (thumb on index finger): the clutch.
- **Right pinch:** the gripper. Fingers apart = open. Fingers together = closed.
- Release the left pinch: the arm stops and holds.

The ball on each hand grows as you pinch. The left ball turns green when the pinch holds the clutch. The right ball turns green while the arm follows. Without finger tracking, the page uses the Quest's own pinch. There is no stop gesture: release the pinch, or press STOP on a screen. A pinch with the palm up opens the Quest's own menu, so pinch with the palm down or to the side.

**Put the 3D arm on the real arm:** hold the left grip and move. The see-through arm follows the controller and turns with it. Release the grip to leave it there. The Quest's browser keeps the position for next time. After that, the brain sends hand moves in the direction of the 3D arm: move your hand toward the front of the arm, and the gripper goes forward, from any side.

**The status panel** (to the right of the arm, in the hub's design) shows:
- the state, as a colored label: cyan Holding, green Following, amber No controller, rust Frozen (with a pause sign), gray Connecting;
- the gripper's opening and the speed;
- how to drive.

The panel is easy to read over the room in AR. In VR there is a dark room with a table. In AR (passthrough on the Quest), the arm is a see-through ghost over the real room. For a lighter arm, add `?xrarm=stick` to the page's address.

---

## 1. At home: replay (no setup)
Run `uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl --loop`. It plays a 7-second recorded session: grab, move, squeeze, release, move back without the arm, grab again. Open the monitor page to watch it. To make it slower, add `--speed 0.5`.

## 2. At a computer: desktop control
1. Start teleop: `uv run lab-os-teleop serve` (the fake SO-101). Or use `--arm fake-xarm1` (the fake xArm), or `--arm xarm1 --speed 0.2` (the real xArm).
2. Open **http://localhost:8080/**.
3. In the **Controls** box, under "Desktop control", select a **mode**.
4. Click **Desktop control**. The page takes the pointer.

To leave, press **`** (backtick, above Tab) or **Esc**. The pointer is free again, the arm freezes, and another page can take control. In full screen in Chrome or Edge, Esc does only that, and the page stays full screen. To leave full screen, hold Esc.

**X** is STOP in every mode. While desktop control is on, "X = STOP" shows next to the STOP button. The key table on the page comes from the connected arm's joints.

| Mode | How | What it sends |
|---|---|---|
| **Keys** (default) | One key pair for each motor. Hold a key to turn: D/A base, W/S shoulder, R/F elbow, T/G wrist tilt, Q/E wrist roll, V/C gripper open/close. Shift = slow. | joint movement (`joint_input`), never IK |
| **Mouse** | Hold 1 to 5 (base, shoulder, elbow, wrist tilt, wrist roll) and move the mouse. Left and right button: gripper open and close. Shift = slow. | joint movement |
| **Virtual hand** (prototype) | A simulated Quest controller: Space = clutch, trackpad or WASD/RF move it, the arrows tilt and roll, C = gripper. It is difficult to use on a desk, but it tests the Quest's path. | a pose (`xr_input`): IK on the xArm, joint space on the SO-101 |

**The real xarm1:** before you start, clamp the arm, clear the area, and keep the power plug near you. If the servos are limp, press the board's **Run** button (the arm stands up by itself). Stand **behind the arm, opposite the controller board** (the board's side is the arm's "front", `docs/dev/GOTCHAS.md`). Then "forward" and "right" agree. The motors move only while you hold a key or a button. A move that was already sent still finishes (in 0.1 s or less).

## 3. At home: the WebXR emulator in the browser
1. In Chrome or Brave, install Meta's **Immersive Web Emulator** extension from the Chrome Web Store.
2. Run `uv run lab-os-teleop serve --record recordings/emulator.jsonl`.
3. Open **http://localhost:8080/**. Open DevTools (F12), then the **WebXR** tab. Select a Quest 3 device.
4. Click **Enter AR** or **Enter VR** on the page. **Desktop control** stays available: the page tells a headset by its browser, not by the emulator.
5. In the WebXR tab, drag the right controller's gizmo to move it. Use the grip and trigger sliders and the buttons. Look at the page's readout, the terminal line and the monitor tab.
6. Press Ctrl+C to stop. You can replay the recording (section 1) or make a test from it.

The trigger is the gripper: use the right controller's trigger in the emulator's panel. For everyday tests, desktop control (section 2) is easier than the emulator's gizmos.

`localhost` is a secure address, so WebXR works over `http://` without certificates.

## 4. The real Quest over USB
The Quest's browser opens `http://localhost:8080`. **`adb reverse`** sends the headset's port 8080 through the USB cable to the desktop. The browser sees `localhost` (secure, so WebXR is allowed), and nothing goes over the lab network.

Do this one time:
1. Switch on **Developer mode** on the Quest. The headset must belong to a Meta account in a (free) developer organization. In the Meta Horizon phone app, select Devices → the headset → Developer mode. *The person who controls the lab's Meta account must do this.*
2. Install adb on the desktop (in a normal terminal): `sudo apt install adb`.
3. Connect the Quest to the desktop with a USB-C data cable. In the headset, accept **"Allow USB debugging"** and select "always allow from this computer".
4. Run `adb devices`. It must show the headset as `device` (not `unauthorized`).

Do this in each session:
```bash
uv run lab-os serve                    # the brain, with the fake arm
```
The brain runs `adb reverse tcp:8080 tcp:8080` by itself each time the Quest connects by USB (it looks every 3 seconds). `lab-os-teleop serve` does not: with it, run that command yourself, again after each new connection of the cable.
In the headset, open **Quest Browser** → `http://localhost:8080/teleop` → **Enter AR (passthrough)**. Hold the grip and move the controller. On the desktop, `http://localhost:8080/monitor` must follow.

Teleop without the hub (it can record): run `uv run lab-os-teleop serve --record recordings/quest-$(date +%F).jsonl`. Then the page is `http://localhost:8080` (no `/teleop`).

**The real SO-101:** plug it in, then run `uv run --extra so101 lab-os serve --speed 0.2`, then open the same page. Without `--speed`, it uses the venue's top speed (`max_speed_scale`: 0.5 in the lab and in visitor mode). The brain drives the SO-101 with IK: hand forward, left or up moves the gripper forward, left or up; the controller's tilt and roll turn the wrist. Close all desktop-control tabs first (one page has control at a time). Ctrl+C switches the torque off and the arm goes limp: hold it, or put it down low first.

### The relative mode (the default)
10 cm of hand moves the gripper 10 cm (since 2026-11-16; before, 5 cm). The arm follows at the 1:1 follow speed, scaled by the Speed slider: at the top of the slider (the venue's `max_speed_scale`), it follows at `one_to_one_max_deg_per_s` (180°/s); at half, at half that speed. Before 2026-11-16 it was 45°/s at most, and the arm was far behind the hand (`docs/dev/existing-work-teleop-ai.md`). Where 1:1 is off, the relative mode uses the old, slower speed. Hot servos (60 °C) also slow it down. With `--speed 0.2` in the lab, it is 72°/s: push the right thumbstick up for more.

### The 1:1 mode: the gripper stays with your hand
On the teleop page, select **Hand → arm → 1:1**. The brain keeps the choice until it restarts. The relative mode is the default. Then, in the headset:
1. **Put the 3D arm on the real arm:** hold the left **Grip**, move and turn the see-through arm until it is on the real arm, then release. **Y** puts it back.
2. Put your right hand in the **green ball** at the 3D gripper and hold **Grip**. The panel says "Reach the gripper: 14 cm" until you are within 8 cm. Nothing jumps: the small distance between the hand and the gripper stays the same.
3. Move. The gripper goes where your hand goes, the same distance. If the hand is out of reach or below the table, the arm waits as close as it can and follows again when the hand comes back. Release to pause. Grab again at the gripper.

**Scale (checked 2026-11-16, quick job 13):** nothing in the chain scales the hand. The Quest gives meters, the 3D arm has the real size (the URDF), and the real arm has the same link lengths and gripper point. If 1:1 feels wrong on the real arm, the cause is the arm (sag, the height offset) or the delay. Lab checks 7.2 to 7.4 measure it.

**Speed:** the Speed slider and the venue's top speed do not slow 1:1. Each joint turns as fast as the hand needs, up to the venue's `one_to_one_max_deg_per_s`: **180°/s in the lab and in visitor mode**, off at a new place. To change it, select ⚙ → Robots → **Teleop 1:1 Top Joint Speed** (Off, 90, 120, 180, 240, None), then restart the brain. None means no software limit: the servos' own top speed (about 270 to 310°/s). For comparison, a quick wave (1.5 times a second, 10 cm from side to side) needs about 120°/s at the base. The panel and the page say "Speed 1:1: 180 °/s top".

**The servos' health:** with a real SO-101, the brain reads each servo's temperature, load and voltage every 5 s. It writes them to `logs/servo-health/<date>_<arm>.jsonl`, with the mode, so that you can compare relative and 1:1 sessions. A servo at **60 °C** slows 1:1 down to the relative speed (the panel says "1:1 slowed: servos warm"). The servos switch themselves off at 70 °C. To learn if 1:1 wears the motors more, compare the temperatures of a relative session and a 1:1 session of the same length.

Tilt and roll stay relative (degree for degree from the grab). Bare hands also work: the right wrist in the ball, a left pinch for the clutch. Desktop control and old recordings have no hand position, so they stay relative. To replay a new recording in 1:1, run `uv run lab-os-teleop replay recordings/<file>.jsonl --mode one_to_one` (a recording made in 1:1 changes mode by itself).

Why 1:1: in the relative mode (then 10 cm of hand = 5 cm of gripper), the hand moved away from the arm and the user had to grab again and again (decision 2026-11-10).

### Tuning: when the arm does not follow well
Record a session. Then replay it without the Quest and without the real arm:
```bash
uv run lab-os serve --arm so101-white --speed 0.2 --record recordings/quest-$(date +%F).jsonl
uv run lab-os-teleop replay recordings/quest-2026-11-10.jsonl      # the fake arm; watch /monitor
```
Give the recording to Claude to find where the problem is ("at 0:40 the elbow straightens"). The settings are in `MappingConfig` (`src/lab_os/teleop/mapping.py`):
- `tip_m_per_hand_m` (1.0 since 2026-11-16, 0.5 before): the relative mode, 10 cm of hand → 10 cm of gripper. Lower is finer but follows less. Higher is less smooth. (1:1 is always 1.)
- The relative speed: `TeleopLoop.relative_cap()` (the 1:1 follow speed × the Speed slider's share of its top). `MappingConfig.max_deg_per_s` (90 × speed) applies only where 1:1 is off.
- `capture_m` (0.08): in 1:1, how near the hand must be to the gripper to grab it.
- The floor: the gripper and the wrist stay above the venue's floor, the same as for the AI tools. What sets it and how to change it: `docs/guides/ai-control.md` → "Limits".
- The speed (the slider, the thumbstick, `--speed`): at 0.2, the arm is far behind a quick hand.

## 5. The hub in VR
In the Quest's browser, open the hub's address (`http://localhost:8080` over USB, or `http://<the brain's address>:8080` over Wi-Fi). A Quest gets a start page with three choices: **Enter VR**, **Enter AR**, and **Use the hub in the browser instead**.
- To open it without typing: save the address as a bookmark, or install the hub as an app (the browser's menu → Install, if it offers it). The app gets its own icon in the app library.
- Over Wi-Fi, VR and AR need a secure address. In the Quest's browser, open `chrome://flags`, find "Insecure origins treated as secure", add `http://<the brain's address>:8080`, select Enabled, then Relaunch.
- **Teleop** in the hub in the browser opens the Teleop page. There, select **Hand → arm** (relative or 1:1), the speed and the 3D arm's look, then press **Enter VR** or **Enter AR**. Desktop control is not available in the headset. In the hub in VR or AR, Teleop opens as a module (below).

After Enter VR (or Enter AR): The startup plays around you, as on the designed hub. Pull the trigger (or pinch) to start; do it again to skip the startup. Then the hub is around you:
- Point at a panel with a controller (or your hand) and pull the trigger (or pinch) to open its details. 7d, 14d, 30d, List all and a device's card also work.
- **B** or **Y** closes a page. **⏻** (top right; on a module, beside ← on its tab) opens a small menu: **Back to the start screen** or **Exit** (leaves VR or AR). B closes the menu.
- **⚙** (beside ⏻) opens Settings, with the same groups as ⚙ on the screens. **This Device** is the Quest. Point at a switch, a choice or − / + and pull the trigger: it saves at once, and the line at the bottom says "Saved" or why not. Change names, colours and lists on a screen (VR has no keyboard). The brain's settings change only when the Quest is connected by USB (it then counts as the brain's computer).
- **Asking:** point at the ask line under the core and hold the trigger (or a pinch) while you talk. The wake word and the microphone permission: `docs/guides/voice.md` → "In VR".
- **Monitor** and **AI Control** show the arm as a hologram, with each joint's angle, who has control, and STOP. They only show; they do not drive. AI Control also shows each robot-tool call. To go back, press B or Y, or point at ←.
- **Teleop** opens around you, without leaving VR or AR, like Monitor and AI Control (since 2026-11-23). The arm follows your controllers or hands, as on the Teleop page: hold the right grip to move, the trigger is the gripper, **A** or **X** stops. The status box beside the arm says what the arm does, and who has control when another page or the AI tools have it. The left grip moves the 3D arm; **Y** puts it back. The arm holds still when you go back, when you leave VR, or when input stops.
  - Under the status box are four buttons: **STOP**, **OPTIONS**, **BACK** (back to the hub) and **EXIT** (leaves VR or AR). Point at one with the right controller or the right hand. Then pull the trigger or pinch. The beam shows while it is on a button. **B** also goes back.
  - **OPTIONS** opens the Teleop page's options above the status box: the speed (− and +), **Hand → Arm** (relative or 1:1), the **3D Arm**'s look (full model or light) and **Put the 3D Arm Back**. They change at once. The Teleop page shows the same choices.
- **EXIT** (under the hub, on every page; in Teleop, under the status box) leaves VR or AR and shows the browser page again. The "lab-os is off" card has it too.

**Tests without a headset:** the Immersive Web Emulator (section 3) also works for `/xr`: select Enter VR, then move the right controller's gizmo and use its trigger and buttons.
- For a scripted test, Meta's emulator engine (`npm i iwer`, with `playwright-core` and Chrome) can run the page headless. Install `IWER.XRDevice(IWER.metaQuest3)` with `installRuntime({ forceInstall: true })` before the page loads (GOTCHAS 2026-11-23), click Enter VR, set `controllers.right.quaternion` to aim, call `updateButtonValue("trigger", 1)` to press, and take screenshots. On the Mac, launch Chrome with `--use-angle=swiftshader --enable-unsafe-swiftshader`, or WebGL fails (GOTCHAS 2026-11-20).
- `/xr?slow=10` plays everything ten times slower and without sound, so that you can look at each moment of the startup.
- `/xr?preview&passthrough` draws the preview the AR way (see-through) over the page. Put a light background behind it to find anything that would cover the room in AR (GOTCHAS 2026-11-18).
- Limits: headless Chrome draws the scene in software at about 7 frames a second. Then teleop's dead-man stop freezes the arm right after the clutch engages (GOTCHAS 2026-10-24), so the arm only follows with the headset. Chrome's fake microphone (`--use-file-for-fake-audio-capture`, GOTCHAS 2026-11-12) can ask a spoken question on the ask line.

## 6. Two arms at once (preview)
A preview for the demo (`docs/plan/current-focus.md`, item 7). The right controller drives one arm. The left controller drives a second arm at the same time. One Quest page drives both.

```bash
uv run lab-os serve --left-arm fake        # two software arms: fake-arm (right hand), fake-left (left hand)
uv run --extra so101 lab-os serve --arm so101-white --left-arm so101-green --speed 0.3   # the lab's arms
```
Then do `adb reverse` and open the teleop page, as in section 4. `lab-os-teleop serve` also takes `--left-arm`.

The controls (with the controllers):
- **Right grip** (hold): the clutch of the `--arm` arm. **Left grip** (hold): the clutch of the `--left-arm` arm. Each arm follows its own hand, relative to where it is.
- **Each trigger:** the gripper of that hand's arm.
- **A or X:** stops both arms. STOP on any page also stops both arms.
- **Right thumbstick** and the Speed slider: the speed of both arms.
- **Y** (hold) **and a grip:** move and turn that hand's 3D arm. While you hold Y, the real arms hold still. After you release Y, release the grip and hold it again to drive.
- **Y** (a short tap, no grip): put both 3D arms back to where they start.

**The 3D arms:** the headset shows one 3D arm for each real arm. The left 3D arm starts 40 cm to the left of the right one. Put each 3D arm on its real arm (Y and the grip). The Quest's browser keeps both positions. Each hand's moves are measured from its own 3D arm: move your hand toward the front of a 3D arm, and that gripper goes forward, from any side.

What is different from one arm:
- The left grip does not move a 3D arm by itself. Hold Y with it.
- **Hand → arm** on the teleop page sets the mode of both arms. In 1:1, each 3D arm has its own green ball: put that hand in it and hold the grip. Put both 3D arms on their real arms first (Y and the grip).
- Bare hands drive only the right arm (a left pinch is its clutch), as with one arm.
- Desktop control and the AI tools drive only the right arm. While an AI tool moves the right arm, the left arm holds.
- The status panel in the headset has two labels: the left arm on the left ("Left following"), the right arm on the right. While you hold Y, it says "Y held: a grip moves its 3D arm".
- The teleop page and the monitor show "Right arm" and "Left arm", and both arms in the 3D view (the left one 40 cm to the left; these pages do not know where the real arms stand). The monitor shows the joints of each arm.
- If one arm's USB cable is disconnected, the other arm continues.
- Ctrl+C makes both SO-101s go limp. Hold both arms first.

**Where to put the arms:** next to each other, both facing away from you, with the `--arm` arm on the right, is the easiest. Stand behind them. If an arm faces another way, turn its 3D arm the same way (Y and the grip). Then that hand moves its gripper in the room's directions too.

**The green arm:** `--left-arm so101-green` has the same checks as `--arm so101-green` (`docs/guides/ai-control.md` → "The green arm"). It must be in the venue's `active_devices`. The brain refuses it while LeLab or a training run has its port open. The brain drives it with its copy of the training calibration and never changes the arm.

## Troubleshooting
- The page does not load → `adb reverse --list` must show `tcp:8080 tcp:8080`. The brain runs it by itself when the Quest connects. If it fails, the brain's terminal says why. With `lab-os-teleop serve`, run `adb reverse tcp:8080 tcp:8080` yourself.
- `adb devices` shows `unauthorized` → put on the headset and accept the USB debugging question.
- "WebXR not available" → the address must be `http://localhost:8080`, not the desktop's IP address (an IP address is not a secure address).
- The headset's panel says "Stopped" and "Let go of the grip, then grab again" → release the grip fully, then press it again.

To show what the headset sees on the desktop's screen, for the room: `docs/guides/quest-view.md`.

Later (not needed for the demo): Wi-Fi instead of USB needs HTTPS with a certificate that the Quest trusts, or adb over Wi-Fi. USB is simpler and portable (`docs/archive/focus-2026-10-teleop-demo.md`, "Fewest moving parts").
