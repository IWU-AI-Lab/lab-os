# Gotchas made out of date (moved 2026-11-25)

These entries left `docs/dev/GOTCHAS.md` on 2026-11-25 (quick job 108), because a later fix or a later entry made them out of date. They stay as written. Newest first.

---

### 2026-11-20 — The tests failed after a change on the settings page, or with an arm plugged in
**What:** In the lab, the settings page saves into the repo's `config/` (persona, chat keep time, the hub's look and buttons, the limits). The tests read that folder and expected the committed values, so 6 tests failed after the builder changed settings. One more test failed because so101-white was plugged in: the visitors' welcome names the robots whose `/dev/serial/by-id/…` port exists.
**Fix:** `tests/conftest.py` gives each test run a copy of `config/` as last committed (`git archive HEAD config`) and uses it as the repo's config. Changes on the settings page do not change the tests now. A committed change can still make a test fail: then update that test. The visitor test's brain treats every port as unplugged.
**Since 2026-11-20 (later the same day):** replaced. The settings page writes into `config/local/` (not in git), so `config/` holds only the defaults, and the tests read it as it is, with an empty `local/` (`docs/dev/places.md` → "The place's own changes").

### 2026-11-19 — The teleop pages say "frozen: release grip" while the grip is already released
**What:** after any freeze (also the brain's first input), `status.needs_release` stays true until the arm moves again, even with the clutch let go: it is the mapper's flag *or* the jog's (`loop.py` `status()`), and the jog's flag clears only with keyboard jogging. So with a Quest or the webcam, the Arm chip says "frozen: release grip" (the webcam page: "frozen: let go of the clutch") until the next grab, though the release already happened. Nothing moves wrongly; only the words are off.
**Fix:** not changed (it is in the teleop loop, which the builder reviews). The webcam page's own state shows the page's freeze, which is correct. (2026-11-20, quick job 66: fixed. `status.needs_release` is now the flag of the input that drives: the keys' flag for keys, the hand mapper's for a Quest, hands or the webcam.)

### 2026-11-19 — Lab day: the wake word stops after a settings change
**What:** on the desktop, the wake word stopped after a change to Wake Word Sensitivity and came back only after a restart (lab check 9.7). During visitor mode it stopped too, and came back much later (F.11). On the Quest it did not answer until the builder changed Level of Detail (F.6). When it works, it is reliable.
**Fix:** quick job 42 (2026-11-20, the entry "The wake word: not reproduced…" above).

### 2026-11-19 — Lab day: voice timing and languages
**What:** push-to-talk took about 9 s to the first spoken word (9.3). After a wake word question, the answer started 4.2 s and 5.3 s after the question ended (the words were final after 0.5 to 0.9 s, the first text came 1.8 to 2.9 s later). After ⏻ and start, the greeting did not start at once (9.2). With Answers: English, a typed Spanish question got a Spanish answer and no voice; a typed "你好" got English (9.14). Listens: English still let other languages through ("ni hao"), and a few times "test" came out in Cyrillic. The voice sometimes changed to another person between answers. The microphone button disappeared when the microphone was unplugged and did not come back when it was plugged in again. With the lab-assistant persona, spoken questions came back as words in German, Turkish or Portuguese, with Listens on English and on Any; JARVIS was fine (2.9).
**Fix:** quick jobs 42 (the greeting), 46, 47, 48 and 55.

### 2026-11-19 — Lab day: the arm kept moving after "Shut down lab-os"
**What:** F.9. The arm went limp, but the AI tool's move went on and the arm moved to its goal. The terminal stayed about 30 s after `shutting down: asked from…`. The page in AR did not show "lab-os is off". The checklist also asked for the "Start lab-os" icon before step 11.1 had made it, so the icon opened as a text file.
**Fix:** quick job 44. The checklist's rules now say: a step comes after the steps that it needs.

### 2026-11-19 — Lab day: STOP was not on the hub during the visitor wave
**What:** F.11. To stop the wave, the builder had to open Monitor quickly: the designed hub had no STOP button in view. The wave itself works but does not look much like a wave.
**Fix:** quick jobs 43 (STOP) and 52 (the wave).

### 2026-11-19 — Lab day: Top Speed gave "500 Internal Server Error", then Settings was empty
**What:** F.14. A change to Top Speed showed `500 Internal Server Error` under the field, no "✓ Saved", and the amber bar only at the top of the page. Restart Now did nothing. After ⚙ was closed and opened again, the page showed nothing. After the brain was stopped and started again, all of it worked (Saved, Restart Now, the arm connected again). Changing a number and changing it back still asked for a restart. The order arrows of Buttons Around the Core do not line up and look like lines.
**Fix:** quick job 45.

### 2026-11-19 — The pages' 3D arm takes every `arm_command`, whatever its `device`
**What:** two arms at once (preview 3). Every `arm_command`, `arm_stop` and `arm_resume` has a `device` field, but `ArmFeed` (`teleop/web/arm/arm-feed.js`) never reads it. A second arm's commands on `/ws` would make the 3D arm jump between the two arms, and its `arm_stop` would show the right arm as frozen.
**Fix:** the second loop sends no `arm_*` messages. Its state goes in `status.left_arm`. A 3D view of two arms must first make `ArmFeed` filter by `device`.
**Replaced the same day:** `ArmFeed` now follows one arm (right or left) and takes only messages whose `device` is that arm, so both arms send `arm_*` messages again.

### 2026-11-17 — Unplugging a real arm while the brain runs: the hub doesn't notice, and after replugging it's stuck
**What:** lab check 10.5. With `so101-white` driven by the brain, its USB cable was unplugged: the hub still showed it connected. Plugged back in, teleop showed "following" but the arm didn't move, and the brain repeated `so101-white: read failed (Failed to sync read 'Present_Position' … [TxRxResult] Port is in use!); using the last reading`. Likely (not checked): the brain keeps the old port open after the cable goes, and never opens the new one.
**Fix:** quick job 27 (notice the unplug, say so on every page, reconnect when it's back). Until then: after replugging an arm, stop the brain (Ctrl+C) and start it again.
**2026-11-18:** built (quick job 27): the brain checks the arm's `/dev/serial/by-id/` name every half second, lets go of the port when it's gone and opens it again when it's back. Not yet tried on the real arm (lab check F.4–F.5).

### 2026-11-17 — The VR hub's far-away dot cluster only shows in AR
**What:** lab check 10.1: the cluster is visible only in AR (passthrough), straight ahead, behind the idle circle, not moving. In VR it's probably there too but black on black. When the hub's network bursts into place, its dots seem to fly out of that cluster.
**Fix:** quick job 10 (2026-11-18): found, see the entry below.

### 2026-11-17 — so101-white's two cameras answer to each other's names
**What:** during an AI pick, `camera_snapshot so101-white-cam-wrist` showed the table from above (the arm, the Quest, a box), and `so101-white-cam-stand` showed the view along the jaws (the cube between them). The names in `config/devices.yaml` point at the wrong video ports.
**Fix:** lab check 3.9 (2026-11-17): unplugging the wrist camera removed `usb-0:7`, so the wrist camera is socket 7 and the stand camera socket 8, as on the green set. Swap them in `config/devices.yaml`: quick job 29.
**2026-11-18:** swapped (quick job 29): `so101-white-cam-wrist` is `usb-0:7`, `so101-white-cam-stand` `usb-0:8`. Lab check F.1.

### 2026-11-16 — Green arms: LeLab writes a calibration into the motors at every teleop start, and it has two setups
**What:** lab check part 8. `--watch` on `so101-green` worked with `calibration_file` set to `sheep.json`, then later refused: "motors hold a different calibration than its file". Cause, read from LeLab's code and saved setups (nothing written): LeLab's teleop writes the chosen setup's two calibration files into both arms' motors every time it starts. LeLab has **two saved setups for the same green pair**, and their names are crossed:

| LeLab setup | follower file (written to the follower) | leader file |
|---|---|---|
| `SO-101_Green_Follower` | `sheep.json` | `SO-101_Green_Follower.json` |
| `SO-101_Green_Leader` | `SO-101_Green_Leader.json` | `shepherd.json` |

`sheep` and `shepherd` are the builder's own calibrations from LeRobot's command line (the ones used for training, as far as the builder remembers); the two `SO-101_Green_…` files came from LeLab's calibration page. The two follower files differ by up to 43 motor steps (about 3°). So the motors hold whichever setup LeLab ran last, and a lab-os pinned to one file refuses after the other. Each setup also saves only one camera (one `wrist_cam`, the other `overhead_camera`, both camera number 2); adding cameras in LeLab is finicky (they don't always show up or save).
**Fix:** decided 2026-11-16: lab-os matches the motors. It uses whichever file in LeLab's follower folder equals what the motors hold, says which, and refuses only if none does (quick job 18, built 2026-11-17: it reads the motors' homing offsets and ranges, compares them as LeRobot does, and looks in the arm's own role folder first, then the other; the leader the same way; `calibration_file` is gone from `devices.yaml`). Still read-only. Lab check: part 8b. For training, the builder keeps to one LeLab setup, so recordings and the policy use the same calibration.

### 2026-11-13 — The Newline by HDMI is choppy at 1920×1080 though the desktop draws 60 fps (open)
**What:** the lab desktop on the Newline's HDMI (+ the touch cable), the Newline as its screen. `/perf` showed the desktop's numbers, a steady 60 fps, but the picture on the Newline was still very choppy. After lowering the desktop's resolution to **1600×900** (Ubuntu Settings → Displays) it was smooth. So the drawing isn't the problem; the lag is between the HDMI output and the Newline's panel at 1080p. Push-to-talk showed up (whose microphone, the desktop's USB one or the Newline's over the touch cable, isn't clear) and its transcription was poor. The wake word wasn't tried.
**Fix:** open. Workaround: 1600×900. To check next: the refresh rate Ubuntu picks at 1920×1080 (Displays: 60 Hz, or 30/50?), and the Newline's picture mode (a "game" or low-latency mode in its menu; manual in `docs/device_manuals/`).

### 2026-11-13 — The Quest's wake word sometimes doesn't fire
**What:** in the headset, "hey jarvis" usually works but sometimes nothing happens; push-to-talk always works. On the lab desktop with a USB microphone both work, though sometimes only when spoken louder (the microphone isn't great).
**Fix:** open. Cause unknown (the Quest browser pausing the microphone, the level, or the detector's threshold).

### 2026-11-12 — Which white-arm camera sees what
**What:** the `camera_snapshot` tool told the AI this wasn't written down. From the pick run: **`so101-white-cam-a`** is fixed above the table, behind the arm, looking forward over it (the arm comes in at the bottom right; the box and pliers are top right). **`so101-white-cam-b`** is on the wrist, looking along the jaws (both jaw tips at the bottom of the picture). The exposure settles slowly: cam-a gave three very dark pictures in a row while the arm moved under it, and cam-b one washed-out yellow-white picture, both fine again on the next snapshot.
**Fix:** written into the cameras' notes in `config/devices.yaml` and the tool's description, which also says to take another picture when one is too dark or too bright.

### 2026-11-10 — The Newline doesn't look like 60 Hz from a laptop (open)
**What:** the laptop says the Newline runs at 60 Hz, but motion looks no smoother. Several ways tried by the builder; not solved yet. Likely suspects, cheapest first: the browser's energy saver (Chrome/Edge/Brave cap pages at 30 frames a second on battery: plug in, or turn it off under Settings → Performance / System); a 4K signal (60 Hz at 4K needs HDMI 2.0 at both ends and a "Premium High Speed" cable, and 4× the pixels for a laptop's graphics to draw: set the laptop to 1920×1080 at 60 Hz and let the Newline scale it); the Newline's HDMI/EDID version setting (1.4 vs 2.0) on its input menu, where the model has one; its USB-C input instead of HDMI, if both ends carry video over USB-C. Measure with `/perf` (frames the browser actually draws) on the Newline.
**Later the same day:** still stuck at a low rate from the laptop, though it says 60 Hz. And the hub in the Newline's own Chrome (through `pi01`) is laggy too, even at `?quality=reduced`: probably its browser on its phone-class chip. The builder now questions the Newline as the hub's screen; `/perf` numbers on it would settle how much it can carry. The builder also connected a lab desktop by HDMI (maybe DisplayPort): just as laggy as the laptop (a Mac). So it's the Newline itself (its input or how it scales the picture), not the computer behind it, and another computer on its HDMI isn't expected to help.

### 2026-11-09 — New devices can't join the lab Wi-Fi quickly
**What:** only campus IT can add a device (by MAC address) to the lab Wi-Fi. The Raspbots were sent in about two weeks ago and still aren't on (IT tried; it didn't work, cause unknown). Planning had assumed the Newline could just join it.
**Fix:** plan around it: only devices already on it (the desktops, the Pis) use it; the Newline reaches the brain by cable, through a Pi, or by a phone hotspot until the lab router exists (`docs/guides/network-setup-checklist.md` → "Networks before the router").

### 2026-10-27 — Hook blocks shell commands that merely contain green's serial numbers
**(Gone since step 11, 2026-11-12: the hook doesn't look for the green serials any more.)**
**What:** `guard.sh` denies any Bash command containing so101-green's serials, even when only writing them into the block list. Editing `config/devices.yaml` and the tests with the editor tools (not shell heredocs) works.

### 2026-10-24 — Never open so101-green's serial ports
**What:** The lab desktop has so101-green's leader + follower plugged in. Both show up as CH343 adapters (`1a86:55d3`, "USB Single Serial"), exactly what so101-white will look like.
**Why it matters:** so101-green is the training project's arm (the builder's own, separate from lab-os). Opening its port (even to read) can disturb their session.
**Rule:** Never open these:
- `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41531599-if00`
- `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41533501-if00`

They're `off_limits` in `config/devices.yaml`; `lab_os.devices` refuses them, and a Claude Code hook blocks commands that name them. The arm may be unplugged at times; that doesn't change the rule.
**Since 2026-11-12 (step 11):** loosened by the builder. lab-os may open them, but never while another program (LeLab, a run) has them open; they're `borrowed`, not `off_limits` (CLAUDE.md, "Hard rules").
