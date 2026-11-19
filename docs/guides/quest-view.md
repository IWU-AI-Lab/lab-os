# What the Quest sees, on another screen

So people in the room can watch what the person in the headset sees. Since 2026-11-18 (quick job 36).

## What it uses
**scrcpy** ([github.com/Genymobile/scrcpy](https://github.com/Genymobile/scrcpy), Apache 2.0, widely used). It mirrors an Android device over adb, and the Quest is one. It uses the same USB cable and `adb` link as teleop (`docs/guides/quest-setup.md`). Nothing is installed on the headset for good: scrcpy copies a small server to the Quest each time and removes it afterwards.

Meta's own casting (the headset's Camera → Cast, or oculus.com/casting in Chrome) needs the internet, a Meta account and the headset and the computer on the same Wi-Fi. The lab has no such network yet, so lab-os uses scrcpy. Casting stays a fallback if it's ever needed.

Older scrcpy versions showed a black or flickering picture on Quest system versions 74 and later. scrcpy v4.0 (May 2026) fixed it, so lab-os uses v5.0.1.

## Install it once (no sudo)
On the brain's computer, in the lab-os folder:
```bash
uv run lab-os quest-view --install
```
It downloads scrcpy v5.0.1 for this computer (Linux x86_64, macOS or Windows) from GitHub into `downloads/scrcpy/` in the lab-os folder, and checks it against the release's SHA-256. Nothing outside that folder changes. `uv run lab-os quest-view` says what's installed and which headsets adb sees.

**To remove it:** `uv run lab-os quest-view --remove` (or delete the `downloads/scrcpy/` folder). The hub's button then disappears.

## Use it
1. The Quest on the brain's computer's USB cable, with USB debugging allowed (as for teleop: `adb devices` lists it as `device`).
2. On the brain's own screen, press the Quest view button in the hub's strip: the screen-with-goggles icon on the designed hub, **Quest view** on the plain hub. The button shows only on the brain's computer, and only once scrcpy is installed. Its tooltip says why it can't start (no headset connected, for example).
3. A window titled "Quest view (quest-a)" opens on the brain's computer. Drag it to the other monitor, or press **Alt+F** in it for full screen there. Press the button again (it's lit while the window is open), or close the window, to stop.

The window only watches: clicks and keys in it never reach the headset (`--no-control`), and the headset keeps its own sound (`--no-audio`). It runs at 30 frames per second to leave the Quest's graphics for VR. Stopping the brain closes it.

**Both eyes or one:** by default the window shows the Quest's whole screen: both eyes side by side. To show one eye, or to open the window in a set place, add scrcpy options to the headset in `config/devices.yaml`:
```yaml
  quest-a:
    kind: quest
    serial: 2G97C5ZHB300FG
    mirror: ["--crop=2064:2208:0:0", "--fullscreen"]   # left eye only, full screen
```
`--crop=width:height:x:y` is in the headset's own pixels. The exact numbers for the Quest 3 are found in the lab (lab-checklist F.12). Other options: scrcpy's own docs (`doc/video.md`, `doc/window.md`).

**adb:** the download brings its own adb, but lab-os gives scrcpy the system's adb when there is one (`ADB=…`). Two different adb versions stop each other's server, which would cut teleop's `adb reverse` (`docs/dev/GOTCHAS.md` 2026-11-18).

## Where the code is
`src/lab_os/quest_view.py` (the download, finding scrcpy and adb, starting and stopping), the endpoints `/api/quest-view` in `src/lab_os/hub/server.py` (`docs/dev/protocol.md`), the button in `hub/web/design.html` and `hub/web/hub.js`. Tests: `tests/test_quest_view.py`.
