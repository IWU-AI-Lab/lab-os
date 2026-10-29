# Quest input: at home (no headset) and on the real Quest (USB)

The teleop program serves a WebXR page and receives the controller data over a WebSocket. Everything currently drives the **fake arm**. Real arms come later and always need the builder's OK before motion.

```bash
uv run lab-os-teleop serve                         # XR page + live fake arm
uv run lab-os-teleop serve --record recordings/try1.jsonl
uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl   # no browser needed
```
Then open **http://localhost:8080/monitor** to watch the fake arm. In VS Code, the Run and Debug panel has buttons for each of these (`.vscode/launch.json`).

**3D view** (on both pages): draws exactly the joint angles the arm driver receives, per command, unclamped. Pick the model in its dropdown: SO-101 (real URDF meshes), SO-101 stick figure, or xArm 1S boxes. Drag to orbit, scroll to zoom. The table under it flags joints the driver clamped and commands outside the model's limits; the arm turns dark red while frozen. Works offline (three.js and the model are in the repo). Note: control is relative, so `replay --loop` adds the same motion every loop until joints reach their soft limits (3° inside the real ones). There the clutch slips: the arm stops, and moving the hand back moves it back right away.

Controls: **grip** held = clutch (arm follows, relative to where it is) · **trigger** = gripper (released = open, fully pressed = closed; applied while the clutch is held) · **A/X** = stop. The arm freezes when the grip is released, tracking is lost, the connection drops, or the session ends. After a freeze, release and re-press the grip.

---

## 1. At home: replay (zero setup)
`uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl --loop` plays a synthetic 7-second session (grab, move, squeeze, release, move back without the arm following, grab again). Open the monitor page to watch it. Add `--speed 0.5` to slow it down.

## 2. At home: desktop control (recommended for a trackpad/mouse)
`uv run lab-os-teleop serve`, open **http://localhost:8080/**, click **Desktop control (keyboard + trackpad)**. The page captures the pointer (Esc gives it back) and drives a virtual right-hand controller that sends the same messages as the Quest:

| Input | Does |
|---|---|
| **Space** (hold) | clutch: the arm follows while held |
| Trackpad / mouse | hand left/right, up/down |
| Two-finger scroll | hand forward/back ("Invert scroll" if it feels backwards) |
| **W A S D**, **R F** | steady move: forward/left/back/right, up/down |
| **← →**, **↑ ↓** | wrist roll, wrist tilt |
| **C** | gripper close/open (toggle, ramped) |
| **X** (hold) | stop (= A/X) |
| **H** | re-center the virtual hand (only while released, so the arm stays put) |
| **Esc** | leave desktop control (the arm freezes) |

**Software xArm (IK, no hardware):** `uv run lab-os-teleop --arm fake-xarm1 serve`. With the xArm (real or software) the mapping is **IK**: W/S, A/D, R/F and the trackpad move the *gripper* forward/back, left/right, up/down, and ↑/↓ tilt it; several joints move at once.

**Real arm (xarm1):** `uv run lab-os-teleop --arm xarm1 --speed 0.2 serve` (speed is capped by the venue). Before starting: arm clamped, area clear, power plug in reach, and if the servos are limp press the board's **Run** button (the arm stands up by itself). Stand **behind the arm, opposite the controller board** (the board side is the arm's "front", docs/GOTCHAS.md), so your hand and the arm move the same way. The arm only moves while Space is held; release or Esc freezes it (a move already sent still finishes, ≤ ~0.1 s).

Work in short clutch strokes, like lifting a mouse: hold Space, move, release, re-center with H, repeat. The "Trackpad speed" slider sets how far the hand moves per swipe. The 3D view starts behind the arm, so left/right on screen = left/right of your hand.

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

## 4. The real Quest over USB (Monday)
The trick: the Quest's browser opens `http://localhost:8080`, and **`adb reverse`** forwards the headset's port 8080 through the USB cable to the desktop. To the browser it's still `localhost` (secure, WebXR allowed), and nothing goes over the lab network.

One-time:
1. **Developer mode** on the Quest. The headset must belong to a Meta account that's in a (free) developer organization. Turn it on in the Meta Horizon phone app → Devices → the headset → Developer mode. *Needs whoever controls the lab's Meta account.*
2. Install adb on the desktop (in a normal terminal): `sudo apt install adb`
3. Plug the Quest into the desktop with a USB-C data cable. In the headset, accept **"Allow USB debugging"** (tick "always allow from this computer").
4. Check: `adb devices` should list the headset as `device` (not `unauthorized`).

Each session:
```bash
uv run lab-os-teleop serve --record recordings/quest-$(date +%F).jsonl
adb reverse tcp:8080 tcp:8080          # re-run after every re-plug
```
In the headset: open **Quest Browser** → `http://localhost:8080` → **Enter AR (passthrough)**. Hold the grip and move the controller; the desktop terminal and `http://localhost:8080/monitor` (on the desktop) should follow.

Troubleshooting:
- Page doesn't load → `adb reverse --list` should show `tcp:8080 tcp:8080`; re-run it after re-plugging.
- `unauthorized` in `adb devices` → put the headset on and accept the USB debugging prompt.
- "WebXR not available" → the URL must be exactly `http://localhost:8080`, not the desktop's IP address (that's not a secure context).
- Arm shows "frozen: release grip" → release the grip fully, then press again.

Later (not needed for the demo): Wi-Fi instead of USB needs HTTPS with a certificate the Quest trusts, or `adb` over Wi-Fi. USB is simpler and portable (see current-focus.md, "Fewest moving parts").
