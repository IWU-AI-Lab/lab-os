# Quest input: at home (no headset) and on the real Quest (USB)

The teleop program serves a WebXR page and receives the controller data over a WebSocket. By default it drives the **fake arm**; real arms (`--arm xarm1`, `--arm so101-white`) always need the builder's OK before motion.

```bash
uv run lab-os-teleop serve                         # XR page + live fake arm
uv run lab-os-teleop serve --record recordings/try1.jsonl
uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl   # no browser needed
```
Then open **http://localhost:8080/monitor** to watch the fake arm. **Under `uv run lab-os serve`** (the brain with the hub, `docs/hub.md`) the same page is at **http://localhost:8080/teleop**; `/`, `/ws` and `/monitor` work the same otherwise, so use `/teleop` wherever this page says `http://localhost:8080/`. In VS Code, the Run and Debug panel has buttons for each of these (`.vscode/launch.json`).

**3D view** (on both pages): draws exactly the joint angles the arm driver receives, per command, unclamped. Pick the model in its dropdown: SO-101 (real URDF meshes), SO-101 stick figure, or xArm 1S boxes. Drag to orbit, scroll to zoom. The table under it flags joints the driver clamped and commands outside the model's limits; the arm turns dark red while frozen. Works offline (three.js and the model are in the repo). Note: control is relative, so `replay --loop` adds the same motion every loop until joints reach their soft limits (3° inside the real ones). There the clutch slips: the arm stops, and moving the hand back moves it back right away.

Controls: **grip** held = clutch (arm follows, relative to where it is) · **trigger** = gripper (released = open, fully pressed = closed; applied while the clutch is held) · **A/X** = stop · right **thumbstick** up/down = speed (5 % steps, up to the venue's cap; also the Speed slider on the page) · **left grip** held = move and turn the 3D arm, **Y** = put it back. The arm freezes when the grip is released, tracking is lost, the connection drops, or the session ends. After a freeze, release and re-press the grip.

**Bare hands** (put the controllers down; the Quest switches to hand tracking by itself): the **right wrist** moves the arm like the controller, hold a **left pinch** (thumb on index finger) = clutch, **right pinch** = gripper (fingers apart = open, touching = closed). Let go of the left pinch and the arm holds still. Each hand's ball grows as you pinch; the left one turns green once the pinch holds the clutch, the right one while the arm follows. Without finger tracking (the Quest then offers hands as simple controllers) the page uses the Quest's own pinch instead. No stop gesture: let go, or STOP on a screen. Palm up + pinch is the Quest's own menu gesture, so pinch with the palm down or sideways.

**Lining the 3D arm up with the real one:** hold the left grip and move: the ghost follows the controller (and turns with it); let go to leave it there. It's kept in the Quest's browser for next time. Once it sits on the real arm, hand moves are sent in *its* direction: push your hand toward the arm's front and the gripper goes forward, from whichever side you stand.

---

## 1. At home: replay (zero setup)
`uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl --loop` plays a synthetic 7-second session (grab, move, squeeze, release, move back without the arm following, grab again). Open the monitor page to watch it. Add `--speed 0.5` to slow it down.

## 2. At a computer: desktop control
`uv run lab-os-teleop serve` (fake SO-101), `--arm fake-xarm1` (software xArm) or `--arm xarm1 --speed 0.2` (the real one). Open **http://localhost:8080/**, pick a **mode** under "Desktop control: mode and keys", then click **Desktop control**. The page captures the pointer; **Esc** leaves (the arm freezes and another page may take over). **X** = STOP in every mode. The key table on the page is built from the connected arm's joints.

| Mode | How | Goes through |
|---|---|---|
| **Keys** (default) | one key pair per motor, hold to turn: D/A base, W/S shoulder, R/F elbow, T/G wrist tilt, Q/E wrist roll, V/C gripper open/close. Shift = slow. | joint jogging (`joint_input`), never IK |
| **Mouse** | hold 1–5 (base, shoulder, elbow, wrist tilt, wrist roll) and move the mouse; left/right button = gripper open/close. Shift = slow. | joint jogging |
| **Virtual hand** (prototype) | a pretend Quest controller: Space = clutch, trackpad/WASD/RF move it, arrows tilt/roll, C gripper. Unintuitive on a desk; kept because it costs nothing and tests the Quest path. | pose (`xr_input`): IK on the xArm, joint space on the SO-101 |

**Real arm (xarm1):** before starting: arm clamped, area clear, power plug in reach, and if the servos are limp press the board's **Run** button (the arm stands up by itself). Stand **behind the arm, opposite the controller board** (the board side is the arm's "front", docs/GOTCHAS.md), so "forward" and "right" match. Motors move only while a key/button is held; a move already sent still finishes (≤ ~0.1 s).

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

Each session, with the brain (the hub runs too):
```bash
uv run lab-os serve                    # fake arm
adb reverse tcp:8080 tcp:8080          # re-run after every re-plug
```
In the headset: open **Quest Browser** → `http://localhost:8080/teleop` → **Enter AR (passthrough)**. Hold the grip and move the controller; `http://localhost:8080/monitor` on the desktop should follow. If the redesigned page misbehaves in the Quest's browser, `http://localhost:8080/classic/teleop` is the old one.

Teleop on its own (no hub; it can record): `uv run lab-os-teleop serve --record recordings/quest-$(date +%F).jsonl`, and the page is `http://localhost:8080` (no `/teleop`).

**Real SO-101:** `uv run --extra so101 lab-os serve --arm so101-white --speed 0.2` (or `uv run --extra so101 lab-os-teleop --arm so101-white --speed 0.2 serve`), then the same `adb reverse` and page. Without `--speed` it runs at the venue's maximum (`max_speed_scale`, 0.5 in the lab). The SO-101 is driven by IK (hand forward/left/up → gripper forward/left/up, controller tilt/roll → wrist). Close any desktop-control tab first (one page has control at a time). Ctrl+C turns torque off and the arm goes limp: hold it or park it low first.

### Tuning: when it doesn't follow well
Record a session, then replay it without the Quest (and without the real arm):
```bash
uv run lab-os serve --arm so101-white --speed 0.2 --record recordings/quest-$(date +%F).jsonl
uv run lab-os-teleop replay recordings/quest-2026-11-10.jsonl      # the fake arm; watch /monitor
```
A recording is what Claude needs to find where it goes wrong ("at 0:40 the elbow straightens"). The knobs are in `MappingConfig` (`src/lab_os/teleop/mapping.py`):
- `tip_m_per_hand_m` (0.5): 10 cm of hand → 5 cm of gripper. Lower = finer and more "it doesn't follow"; higher = jumpier.
- `floor_m` (0.01): the gripper and wrist stay this far above the base's bottom. Raise it if the real arm still touches the table (it sags under its own weight when stretched out).
- The speed (slider, thumbstick, `--speed`): at 0.2 the arm lags far behind a quick hand.

Troubleshooting:
- Page doesn't load → `adb reverse --list` should show `tcp:8080 tcp:8080`; re-run it after re-plugging.
- `unauthorized` in `adb devices` → put the headset on and accept the USB debugging prompt.
- "WebXR not available" → the URL must be exactly `http://localhost:8080`, not the desktop's IP address (that's not a secure context).
- Arm shows "frozen: release grip" → release the grip fully, then press again.

Later (not needed for the demo): Wi-Fi instead of USB needs HTTPS with a certificate the Quest trusts, or `adb` over Wi-Fi. USB is simpler and portable (see docs/archive/focus-2026-10-teleop-demo.md, "Fewest moving parts").
