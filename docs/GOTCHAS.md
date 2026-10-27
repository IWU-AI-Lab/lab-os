# Gotchas

Every on-the-ground surprise and its fix. Newest first. (Network/device-setup gotchas also live at the bottom of `network-setup-checklist.md`.)

---

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
**Fix:** see `lab-jarvis-log.md` → Open questions (Quest ownership).

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
