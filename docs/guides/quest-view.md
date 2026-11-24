# What the Quest sees, on another screen

Use it so that the people in the room can see what the person in the headset sees. Since 2026-11-18 (quick job 36).

## What it uses
lab-os uses **scrcpy** ([github.com/Genymobile/scrcpy](https://github.com/Genymobile/scrcpy), Apache 2.0, widely used). scrcpy shows the screen of an Android device over adb, and the Quest is an Android device. It uses the same USB cable and adb connection as teleop (`docs/guides/quest-setup.md`), or adb on the router's Wi-Fi (since 2026-11-23, below). scrcpy installs nothing on the headset permanently: it copies a small server to the Quest each time and removes it after.

Meta's own casting (the headset's Camera → Cast, or oculus.com/casting in Chrome) needs the internet and a Meta account. lab-os uses scrcpy, which needs neither. Casting stays available as a fallback.

Older scrcpy versions showed a black or flickering picture on Quest system versions 74 and later. scrcpy v4.0 (May 2026) fixed this. lab-os uses v5.0.1.

## Install it once (no sudo)
On the brain's computer, in the lab-os folder, run:
```bash
uv run lab-os quest-view --install
```
The command downloads scrcpy v5.0.1 for this computer (Linux x86_64, macOS or Windows) from GitHub into `downloads/scrcpy/` in the lab-os folder. It compares the download with the release's SHA-256. Nothing outside that folder changes. To see what is installed and which headsets adb sees, run `uv run lab-os quest-view`.

**To remove it,** run `uv run lab-os quest-view --remove`, or delete the `downloads/scrcpy/` folder. The hub's button then disappears.

## Use it
1. Connect the Quest to the brain's computer with the USB cable, and allow USB debugging (as for teleop: `adb devices` shows it as `device`).
2. On the brain's own screen, press the Quest view button in the hub's strip. On the designed hub it is the screen-with-goggles icon. On the plain hub it is **Quest view**. The button shows only on the brain's computer, and only after you install scrcpy. If the view cannot start, the button's tooltip says why (for example, no headset is connected).
3. A window "Quest view (quest-a)" opens on the brain's computer. Drag it to the other monitor. For full screen, press **Alt+F** in the window.
4. To stop, press the button again (it is lit while the window is open), or close the window.

The window only shows the picture. Clicks and keys in it never reach the headset (`--no-control`). The headset keeps its own sound (`--no-audio`). The window shows 30 frames per second, so that the Quest has enough graphics power for VR. When the brain stops, the window closes.

## Without the USB cable (the router's Wi-Fi)
Since 2026-11-23 (quick job 103), Quest view also works when the Quest is on the router's Wi-Fi and not plugged in. scrcpy then gets the picture over adb on Wi-Fi, as scrcpy's own docs and Meta's describe (`adb tcpip 5555`, then `adb connect`). The Quest's own wireless debugging screen is not used: on Quest system version 83 it does not open (Meta's forum).

USB stays the first choice. If the Quest is plugged in, the view comes over the cable.

The headset's address is `host` in `config/devices.yaml` (`quest-a`: `192.168.8.180`, reserved in the router). adb on Wi-Fi stays on until the Quest restarts. So, after each restart of the Quest, do this once:
1. Connect the Quest by USB, and allow USB debugging.
2. Run:
   ```bash
   uv run lab-os quest-view --wifi
   ```
   It says "quest-a: ready on Wi-Fi at 192.168.8.180:5555. You can unplug the USB cable."
3. Unplug the cable. Press the Quest view button. The press connects to the Quest on Wi-Fi first.

If the Quest does not answer on Wi-Fi, the button's message says so and what to do. Over Wi-Fi the window uses 4 Mbit/s (8 over USB), so that the router has room for the hub and teleop. Another Quest gets its own `host` line when its address is reserved in the router.

**Both eyes or one eye:** the window shows the Quest's full screen, both eyes side by side. To show one eye, or to open the window in a fixed place, add scrcpy options to the headset in `config/devices.yaml`:
```yaml
  quest-a:
    kind: quest
    serial: 2G97C5ZHB300FG
    mirror: ["--crop=2064:2208:0:0", "--fullscreen"]   # left eye only, full screen
```
`--crop=width:height:x:y` uses the headset's own pixels. In the lab (2026-11-19), `--crop=2064:2208:0:0` showed one eye. The picture looks like a fisheye lens: scrcpy shows the headset's own picture, before the lenses. For other options, read scrcpy's docs (`doc/video.md`, `doc/window.md`).

**adb:** the download includes its own adb. But if the computer has an adb, lab-os gives scrcpy that one (`ADB=…`). Two different adb versions stop each other's server, and that would cut teleop's `adb reverse` (`docs/dev/GOTCHAS.md` 2026-11-18).

## Where the code is
- `src/lab_os/quest_view.py`: the download, finding scrcpy and adb, USB or Wi-Fi, starting and stopping.
- `/api/quest-view` in `src/lab_os/hub/server.py` (`docs/dev/protocol.md`).
- The button: `hub/web/design.html` and `hub/web/hub.js`.
- The tests: `tests/test_quest_view.py`.
