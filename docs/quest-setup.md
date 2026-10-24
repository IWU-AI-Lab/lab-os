# Quest input: at home (no headset) and on the real Quest (USB)

The teleop program serves a WebXR page and receives the controller data over a WebSocket. Everything currently drives the **fake arm**. Real arms come later and always need the builder's OK before motion.

```bash
uv run lab-os-teleop serve                         # XR page + live fake arm
uv run lab-os-teleop serve --record recordings/try1.jsonl
uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl   # no browser needed
```
Then open **http://localhost:8080/monitor** to watch the fake arm. In VS Code, the Run and Debug panel has buttons for each of these (`.vscode/launch.json`).

**3D view** (on both pages): draws exactly the joint angles the arm driver receives, per command, unclamped. Pick the model in its dropdown: SO-101 (real URDF meshes), SO-101 stick figure, or xArm 1S boxes. Drag to orbit, scroll to zoom. The table under it flags joints the driver clamped and commands outside the model's limits; the arm turns dark red while frozen. Works offline (three.js and the model are in the repo). Note: control is relative, so `replay --loop` adds the same motion every loop and eventually runs into the joint limits. That's expected, and a handy way to see the clamp flags.

Controls: **grip** held = clutch (arm follows, relative to where it is) · **trigger** = gripper · **A/X** = stop. The arm freezes when the grip is released, tracking is lost, the connection drops, or the session ends. After a freeze, release and re-press the grip.

---

## 1. At home: replay (zero setup)
`uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl --loop` plays a synthetic 7-second session (grab, move, squeeze, release, move back without the arm following, grab again). Open the monitor page to watch it. Add `--speed 0.5` to slow it down.

## 2. At home: browser WebXR emulator
1. In Chrome or Brave (both work on the lab desktop), install Meta's **Immersive Web Emulator** extension from the Chrome Web Store.
2. `uv run lab-os-teleop serve --record recordings/emulator.jsonl`
3. Open **http://localhost:8080/**, then open DevTools (F12) → the **WebXR** tab. Pick a Quest 3 device.
4. Click **Enter AR** / **Enter VR** on the page.
5. In the WebXR tab, drag the right controller's gizmo to move it; use the grip and trigger sliders and the button toggles. Watch the page's readout, the terminal line, and the monitor tab.
6. Stop with `Ctrl+C`. The recording can be replayed (section 1) or turned into a test.

`localhost` counts as a secure context, so WebXR works over plain `http://`. No certificates needed.

## 3. The real Quest over USB (Monday)
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
