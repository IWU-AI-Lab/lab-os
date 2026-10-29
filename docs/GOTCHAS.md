# Gotchas

Every on-the-ground surprise and its fix. Newest first. (Network/device-setup gotchas also live at the bottom of `network-setup-checklist.md`.)

---

### 2026-10-29 — xArm servos report negative positions when pushed past 0 by hand
**What:** The first hand calibration saved shoulder_pan and elbow_flex lows of −15600°. Pushed past the end of their range, the servos report a slightly negative position (e.g. −36), which the driver read as unsigned (65500). The loader then clamped −15600 to −120°, so those two joints had **no real limit** on that side.
**Fix:** positions are parsed as signed 16-bit; the calibration ignores impossible readings; the loader replaces any side that's far outside the servo range with the safe default (and logs it). Re-run the calibration to measure those two sides properly.

### 2026-10-29 — xArm jogging was choppy, needed re-pressing, and servos went limp
**What (builder):** keys moved the wrist in steps; sometimes a key had to be released and pressed again; sometimes motors went limp. **Causes:** (1) each command aimed only ~0.25° ahead with a 100 ms move, so the servo sat inside its deadband (it ignores errors of a few units) and moved in jerks; (2) every 0.25 s a real position read blocked the teleop loop for 10-100 ms (and reads compete with moves on this board), so input looked stale → dead-man freeze → "release first"; (3) limits were the servo's full ±120°, beyond where joints hit something, so a held key drove servos into hard stops → stall protection → limp. Found afterwards: base at +116.6°, wrist roll at −116.4°.
**Fix:** `XArm` now runs its USB I/O in a worker thread (never blocks the loop), doesn't read while moving (tracks where the servo should be instead), and aims `lead_s` = 0.3 s ahead while a joint moves, so servos run continuously; release/STOP sends "hold here" at once. Measured after: 18° jogs land within 0.1-0.3° (before: 1-3° short). Limits: safe defaults from the builder's grab script until `calibration/xarm1/limits.yaml` is measured by hand (`uv run python -m lab_os.robots.xarm calibrate`, servos limp, no motion).

### 2026-10-29 — A joint outside its limits jumped into range on the first key press
**What:** With the new, tighter xArm limits, the arm was found outside them (base +116°, limit 72°). The shared soft-limit helper widened the range to include the current position, then clamped it back to the limits, so the first jog pulled base 62° and wrist roll 44° toward the range (speed-capped at ~24°/s, but not what was asked). Caught in Claude's real-arm test.
**Fix:** a joint may always stay where it is and move back toward its range, never further out (`soft_bounds`, the xArm driver and the fake arm all follow this rule; `test_jogging_from_outside_the_limits_never_jumps`).

### 2026-10-29 — xArm position replies sometimes take >100 ms or skip a servo
**What:** With a 100 ms timeout only ~13/20 reads answered; with 150 ms, 18/20, and two replies lacked the shoulder servo (5). Reads now happen only in the worker thread, so a longer timeout costs nothing.
**Fix:** `read_timeout_s = 0.15`; incomplete replies still count as failed reads.

### 2026-10-29 — Headless test browsers outlived their tests for days
**What:** Headless Brave instances from Claude's 2026-10-24 tests were still running 5 days later; their pages kept auto-reconnecting to `localhost:8090`, and one took **control** of a fresh test server, so the real-arm test's input was (correctly) ignored. A plain `terminate()` of the browser leaves its renderer processes alive.
**Fix:** test scripts start the browser in its own process group and kill the group. Before a real-arm test, check who is connected: `ss -tnp | grep :8080` (or the test port), and the page's "Control" field.

### 2026-10-29 — A display bug stopped the teleop loop
**What:** The terminal status line assumed every input is a controller frame; the first `joint_input` raised inside `on_tick`, which ran outside the loop's error guard, so the loop task died silently (page "holding", arm never moving).
**Fix:** the printer handles joint input, and `on_tick` errors are logged without stopping the loop. Rule: nothing cosmetic runs unguarded in the arm loop.

### 2026-10-29 — Claude's headless browser tests connected to the builder's own server
**What:** Claude's test pages used port 8080 while the builder had `lab-os-teleop serve` running there (software arm, so harmless), and a test page took control from the builder's tab for a moment.
**Fix:** Claude's tests use another port (`--port 8090`). Check `ss -ltnp | grep 8080` before assuming a server is your own.

### 2026-10-29 — xArm IK: small reach, and tilt is the first thing given up
**What:** The xArm reaches only ~0.34 m from its shoulder (links 101 + 95 mm + 145 mm to the gripper). Near full stretch, a hand move can't keep both the gripper's position and its tilt, so the IK keeps the position and lets the tilt change; past full stretch the clutch slips (no wind-up). Tilting the gripper *about its grip point* takes big joint moves (20° of tilt ≈ elbow +34°, wrist −52°), because the wrist swings around that point. Also: upright (all zero) everything is on the base axis, so sideways hand motion can't turn the base until the arm bends forward a bit.
**Fix:** none needed; start teleop from a bent pose. If tilt-about-the-grip feels too wild on the real arm, pivot about the wrist instead (smaller `tool` length in `XArmKinematics`).

### 2026-10-29 — Brave's cache served old pages to Claude's headless checks too
**What:** A reused headless-Brave profile showed an old `index.html` (no STOP button) even after the server sent `no-cache`: files cached before the header existed stay "fresh" by the browser's own guess. Confirms the stale-cache explanation for the Firefox problem below.
**Fix:** after updating the server once, reload with Ctrl+Shift+R (or clear the site's cache) one time; from then on `no-cache` makes the browser re-check every file.

### 2026-10-29 — Teleop page broken in Firefox, fine in Brave/VS Code (cause not yet confirmed)
**What:** With `--arm xarm1`, Firefox showed "—" values, no 3D model and no clutch; the same server works in headless Brave (status, model and joints all fine). **Likely cause (?):** the server sent the page's scripts without `Cache-Control`, so Firefox kept using old cached copies (from before the xArm work) for hours. Also found: an exception in the teleop loop (e.g. the arm not answering) silently ended the loop task, so pages stayed "connected" but nothing moved.
**Fix:** every page/script/model response now has `Cache-Control: no-cache` (re-check, cheap 304); the loop freezes the arm and keeps running on errors; a failing status read is logged, not fatal. If Firefox still misbehaves: Ctrl+Shift+R, then F12 → Console for the error. Firefox can't be tested headless from Claude's sandbox (snap).

### 2026-10-28 — Two Claude sessions in one folder switch branches under each other
**What:** A coding session and a planning session both worked in `lab-os/`. The coding session switched the folder to `xarm-driver`, so the planning session's doc commits landed there instead of on its own branch (nothing lost, but confusing).
**Fix:** One folder per session, via **git worktrees** (several folders on the same repo, each on its own branch). Coding: `lab-os/`. Planning: `lab-os-planning/` on branch `planning`. See `dev-setup.md` → "Branches and folders".

### 2026-10-28 — The two training cameras have the same serial number
**What:** Both USB cameras (Innomaker U20CAM-1080p, USB ID `0c45:6366`, `lsusb` calls them "Microdia Webcam Vitade AF") belong to the so101-green training setup. Both report serial `SN0001`, so a serial number can't tell them apart. On the lab desktop they sit in USB sockets `1-7` and `1-8` (each shows up as two `/dev/video*` entries).
**Rule:** lab-os never opens them (a camera can only be used by one program at a time; opening it can break a training recording). Mark them off limits either by USB socket path or by blocking that camera model in lab-os entirely (simpler; revisit if lab-os ever gets the same model). Identified from `/sys` only, without opening them.

### 2026-10-27 — xArm driver: the `hidapi` wheel can't open the arm on Linux; use `hid`
**What:** PyPI's `hidapi` ships wheels for Linux/Windows/macOS, but its Linux build uses the *libusb* backend: it needs access to `/dev/bus/usb/…` (root-only), so `enumerate()` returns empty serial/product strings and `open()` fails ("open failed"). Our udev rule only covers `/dev/hidraw*`. The `xarm` PyPI package is an unmaintained 5-file wrapper (imports `hid` without declaring it), so we don't use it.
**Fix:** use the `hid` package (ctypes over the system hidapi, MIT, "OS Independent"). On Linux it uses the hidraw backend, which the existing udev rule + `libhidapi-hidraw0` already cover; `enumerate()` then shows manufacturer/product/serial. **Open for Windows/macOS:** `hid` needs the hidapi library installed there (`hidapi.dll` on PATH / `brew install hidapi`); not yet tested. Alternative: the `hidapi` wheel (bundles the library everywhere) plus a second udev line for `SUBSYSTEM=="usb"` on Linux.

### 2026-10-27 — xArm read speed: ~29 reads/s, with periodic lost replies
**What:** One request for all six servos takes a steady ~30 ms (median 29.9, worst 32 ms), i.e. ~29–33 reads/s, so a 30 Hz limit is plausible (probably the HID polling interval). Also ~8 requests per 5 s get no reply within 100 ms (same count on three runs); the next read works. Raw positions + battery (8.07 V) read fine. Commands/s and command→motion delay are still unmeasured (motion test).
**Fix:** the driver raises `TimeoutError`; callers must tolerate it (retry). Cause of the lost replies unknown: ideas are the stale-report drain racing a late reply, or the device skipping a poll.

### 2026-10-27 — xArm ignores move commands while it's being polled fast
**What:** The first motion tests "didn't move": the board accepted every move command (no error) but no servo moved, because the test polled positions every ~0.01–0.09 s. With polls every 0.25 s (or none), every move worked: gripper, `wrist_flex` and `wrist_roll`. The command bytes are identical to the `xarm` library's (which worked on the builder's Mac), padded or not, so it wasn't the OS or library. Also: while servos move, many position replies are missing or leave out the moving servo.
**Fix:** with motion on, `XArm` paces bus reads (`min_read_interval_s = 0.25`; faster calls get the last reading) and treats incomplete replies as timeouts. The exact limit between 0.09 and 0.25 s is unmeasured.

### 2026-10-27 — xArm servos are limp after power-on; the board's "Run" button poses the arm
**What:** After switching on, all servos were limp (position reads still worked). The board's "Run" button plays its stored action and stands the arm upright (all joints ~500), which also powers the servos. Not yet checked: whether a USB move alone wakes limp servos (the tests before "Run" were also polling too fast to tell). Note "Run" **moves the arm by itself**.

### 2026-10-27 — xArm motion numbers (first test, arm upright)
- **Delay:** first visible motion 0.25–0.8 s after a 1 s move command (polling at 0.25 s, so coarse). Slow for teleop; measure it properly (e.g. camera) later.
- **Stops short:** gripper ~12–15 units of a 40-unit move (repeated cycles crept it closed 593 → 645); `wrist_flex`/`wrist_roll` 3–6 units; base/shoulder/elbow 1–5 units. Probably servo deadband/load.
- **Base, shoulder, elbow** (+40 units over 1 s and back, arm upright): all three move smoothly and track the 1 s duration, already moving at the first poll (0.26 s).
- **Streaming:** 40-unit ramps over 2 s sent as 100 ms moves at **20 and 50 commands/s** were followed and ended within ~5 units. Sending is cheap (~490 writes/s possible); the limit is the servos, not USB.

### 2026-10-27 — xArm joint directions: base and elbow are reversed vs. the SO-101 convention
**What:** Watched by the builder, +40 raw units from upright: base turns counter-clockwise from above; shoulder, `wrist_flex` tilt toward the **controller-board side**; elbow tilts away from it; `wrist_roll` turns counter-clockwise from above; gripper closes (builder's script: 302 open, 750 closed). The arm has no obvious front, so **"front" = the board side** (stand there when calibrating teleop).
**Fix:** `SIGNS` in `robots/xarm.py`: pan −1, lift +1, elbow −1, wrist_flex +1, wrist_roll +1 (shared convention: +pan to the arm's right, +lift/elbow/wrist_flex forward, +roll counter-clockwise from above). Gripper mapped 750 → 0° (closed), 302 → 90° (open).

### 2026-10-27 — Hook blocks shell commands that merely contain green's serial numbers
**What:** `guard.sh` denies any Bash command containing so101-green's serials, even when only writing them into the block list. Editing `config/devices.yaml` and the tests with the editor tools (not shell heredocs) works.

### 2026-10-27 — The xArm 1S is a HID device, and `lsusb` calls it an "LED badge"
**What:** The xArm doesn't appear under `/dev/serial/by-id/`. It's a USB HID device (like a keyboard), `/dev/hidraw*`. `lsusb` names its ID `0483:5750` "STMicroelectronics LED badge", because that's a generic chip-maker ID that other gadgets share. Its own strings say manufacturer "Hiwonder", product "xArm", serial `720710C0D60063300023D4D4`. By default only root can open `/dev/hidraw*`.
**Fix:** Identify it by USB ID **plus** product/serial, not the ID alone. One-time setup on each Linux brain (normal terminal, not Claude's):
```bash
sudo apt install libhidapi-hidraw0 libhidapi-libusb0
echo 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5750", MODE="0666"' | sudo tee /etc/udev/rules.d/99-xarm.rules
sudo udevadm control --reload-rules && sudo udevadm trigger --subsystem-match=hidraw
```
Then unplug and re-plug the xArm's USB.

### 2026-10-27 — The lab Quests' Meta account is tied to classmates' phones
**What:** All 3 Quest 3s are owned by one informal "AI lab admin" Meta account; its sign-in/verification goes through classmates' phones; there's no lab phone. Developer mode can only be turned on by the account that owns the headset, and Meta asks for a phone number (or card) to verify a developer account.
**Fix:** "AI lab admin" becomes the lab's one Meta account, verified with the professor's phone number (decision 2026-10-28 in `lab-jarvis-log.md`).

### 2026-10-24 — Joint directions differ per arm: check them with forward kinematics
**What:** The first joint-space mapping had its signs picked by hand. On the SO-101, "hand up" lowered the arm (in its URDF, +shoulder_lift lowers it, +elbow_flex folds it down, +shoulder_pan swings it to its right).
**Fix:** `MappingConfig.signs`, set from forward kinematics on the URDF; `tests/test_so101_directions.py` checks up/down/right/forward with the real model. A new arm needs the same check (the xArm 3D model uses the SO-101 conventions).

### 2026-10-24 — Headless browser tests: software rendering is slow, and that trips the dead-man
**What:** In headless Brave (software WebGL), the SO-101 meshes render at ~3–5 frames/s. Input tied to frames then goes stale (> 250 ms) and the arm freezes. That's correct behavior, but it looks like a bug.
**Fix:** Desktop control sends on a 60 Hz timer (not animation frames); the 3D view renders only on change; use the stick model (`?xrarm=stick`) for headless XR tests. Meta's `iwer` runtime (the engine of the Immersive Web Emulator, npm `iwer`) can emulate a Quest 3 in a headless page for testing the real XR path.

### 2026-10-24 — `astral-sh/setup-uv` has no `@v10`-style tag
**What:** CI failed with "unable to find version `v10`". That action doesn't publish moving major-version tags.
**Fix:** Pin exact versions in `.github/workflows/ci.yml` (e.g. `@v10.3.2`). Same for `actions/checkout` for consistency.

### 2026-10-24 — WebXR needs a secure context: use `localhost`, not an IP
**What:** Browsers only allow WebXR on `https://` or `http://localhost`. Opening the page via the desktop's IP address shows "WebXR not available".
**Fix:** On the Quest, use `adb reverse tcp:8080 tcp:8080` over USB and open `http://localhost:8080` (docs/quest-setup.md). Re-run `adb reverse` after every re-plug.

### 2026-10-24 — Never open so101-green's serial ports
**What:** The lab desktop has so101-green's leader + follower plugged in. Both show up as CH343 adapters (`1a86:55d3`, "USB Single Serial"), exactly what so101-white will look like.
**Why it matters:** so101-green is another project's training arm. Opening its port (even to read) can disturb their session.
**Rule:** Never open these:
- `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41531599-if00`
- `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41533501-if00`

They're `off_limits` in `config/devices.yaml`; `lab_os.devices` refuses them, and a Claude Code hook blocks commands that name them. The arm may be unplugged at times; that doesn't change the rule.

### 2026-10-24 — ttyACM0/ttyACM1 swap
**What:** `/dev/ttyACM0` and `/dev/ttyACM1` are numbered in plug-in order, so they can swap after a reboot or re-plug.
**Fix:** Refer to arms only by `/dev/serial/by-id/…` (stable, includes the adapter's serial number). Find them with `ls -l /dev/serial/by-id/`. `lab_os.devices` rejects raw `ttyACM`/`ttyUSB` paths.

### 2026-10-24 — The `lerobot` conda env is shared
**What:** `~/miniforge3/envs/lerobot` (+ the editable `~/lerobot` checkout) is so101-green's training setup.
**Fix:** lab-os uses its own uv environment (`.venv/`). LeRobot for so101-white gets added to lab-os with `uv add`, never installed into the conda env. `pyproject.toml` sets uv to use only uv-managed Pythons so conda's interpreter is never picked up.

### 2026-10-24 — Sudo doesn't work inside Claude Code sessions
**What:** Claude's shell runs with the "no new privileges" flag, so `sudo` fails.
**Fix:** Run `sudo` commands yourself in a normal terminal; Claude gives the exact command.
