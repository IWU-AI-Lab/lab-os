# Gotchas

Every on-the-ground surprise and its fix. Newest first. (Network/device-setup gotchas also live at the bottom of `docs/guides/network-setup-checklist.md`.)

---

### 2026-11-23 — OpenAI's `onyx` is not a British voice (quick job 100)
**What:** Quick job 100 gave J.A.R.V.I.S. `onyx` for a male voice. The builder wanted the British voice of the films. `onyx` is a deep American voice; of OpenAI's voices only `fable` sounds British. `tts-1-hd` takes no accent instruction (`style:` needs gpt-4o-mini-tts, which drifted: the entry of 2026-11-20).
**Fix:** J.A.R.V.I.S. uses `fable` again (`config/personas/jarvis.yaml`). Gemini's `Charon` has no British accent; Gemini gets no accent instruction now.

### 2026-11-23 — A hub with no device name was never in Open on…, and kit.css's [hidden] beat a Settings rule (quick job 101)
**What:** (1) Lab check V.4: the Pi that drives the Newline had the hub open, but the log said only "device (no name) connected (192.168.8.167)". The brain listed only windows with a device name, so Open on… had nothing to offer. (2) Only pages with an address of their own had "Another monitor of this computer"; the details pages (AI Spend, Commits) have none, and the plain hub had the choice nowhere. (3) Lab check 0.3: the note "Applies when the brain restarts" was to keep its place while hidden (`.row.may-restart .rs[hidden] { display: block; visibility: hidden }`), but `kit.css` has `[hidden] { display: none !important; }`, which wins. When the Restart bar showed, the row grew 21 px, and the value box (centered in the row) moved down 10.6 px under the pointer (measured in headless Chrome at 1600 × 900).
**Fix:** (1) A window with no name is listed by its address (`addr-192-168-8-167`, shown "192.168.8.167 (no device name)"). (2) A details page opens on another monitor as `/design?view=<id>`; the plain hub has the choice too (`device.js` → `openOnMonitor`). (3) The note is shown with a class, not `hidden`. Measured again: the box does not move. Note: a browser keeps the last device name it had, so a page with no name in the address can still be a named device.

### 2026-11-23 — A long, fast question ended while the person still talked (quick job 98)
**What:** lab checks V.25 and V.18 (the OpenAI voice: only the page's silence watch ends a question after the wake word). The watch counts a 50 ms piece as speech when it is 3 times the room's level. While the person talked, it moved the room's level toward each loud piece (a time constant of about 5 s), and toward each softer piece even faster. A fast voice with the browser's gain control has few quiet pieces, so after a few seconds the room's level was near the voice, the voice counted as quiet, and 1.6 s later the question ended. The same rise made a short pause in "37 times 48, … then add 199" count as a longer quiet.
**Fix:** the watch (`web/silence.js`, tested with node) keeps the room's level while the person talks. Only a noise that stays in one range (the loudest piece less than 2 times the quietest) for 4 s becomes the room's level. Between words the level goes down fast and up slowly. The end is 2 s of quiet (was 1.6 s). With the Gemini voice, a pause in the middle of a sentence waits 1.6 s (was 1.2 s).

### 2026-11-24 — raspbot1 checked: the software is as expected; the camera picture is dark
**What:** on raspbot1: Debian 12, Python 3.11, `Raspbot_Lib` 0.0.2 in `/usr/local/lib/python3.11/dist-packages`, OpenCV 4.10, user `pi` in the `i2c` group, the USB camera at `/dev/video0` (auto exposure on). Yahboom's `raspbot.pyc` ran and held port 6001. `Raspbot_Lib` only prints its I2C errors. Under systemd, Python holds printed lines back, so the log did not show them. The camera's pictures came (9 a second) but were black: the lens probably saw only the box. raspbot1 logs in by itself, so user services run without `loginctl enable-linger`. At start, NetworkManager turns on the "Raspbot" hotspot (priority 2) before it tries GL-B7-5G (priority 0). A hotspot is always "available", so it never changes to the router by itself.
**Fix:** the service runs `python3 -u`. No linger step. For the Wi-Fi, lab-os has a service that joins the router at start, and starts the hotspot only when the router is not found (`docs/guides/raspbot.md` → "The Raspbot's Wi-Fi at start"). Installing it needs sudo on raspbot1 once. raspbot1 stops at times: the screen goes black, the keyboard and mouse go off, and it must be switched off and on (the builder, 2026-11-24). It runs on wall power. Its log stops with no shutdown and no warning (05:55:38, with no driving, and 06:09:54, 10 s after a drive test). The supply looks good: 5.2 V, a 5 A USB-C supply, no USB over-current, `throttled=0x0`, 48 °C. The cause is not known. The Wi-Fi driver logged channel errors at 06:11, and the disk is 94 % full. Fix, 2026-11-24: lab-os-wifi installed ("joined GL-B7-5G" 15 s after the start). A health log on raspbot1 (`lab-os/health.log`, a line every 10 s, forced to disk) keeps the last minute before the next stop (`docs/guides/raspbot.md`).

### 2026-11-23 — iwer 2.8 does not replace Chrome's own WebXR unless it is told to
**What:** quick job 102. For the scripted check of the hub's VR Teleop, `new IWER.XRDevice(IWER.metaQuest3).installRuntime()` printed "a native WebXR runtime is already available on navigator.xr; skipping installRuntime". The page then said "No VR here" and Enter VR stayed grey.
**Fix:** call `installRuntime({ forceInstall: true })`. `docs/guides/quest-setup.md` → "Tests without a headset" says so.

### 2026-11-23 — The other wake words answer much less than "hey Jarvis" (lab checks V.21 to V.23)
- The desk at sensitivity 9, the builder in the chair, 5 tries each: OK computer 0, TARS 1, Hey Friday 2, Hey Jarvis 4. The heard ones scored 0.89 to 1.00 (`lab-os logs`). The misses are not in the log: the brain logs only a heard phrase. The builder thinks the tone matters (said like a question, it may not wake). Quick job 99.
- **Later (2026-11-23, quick job 99):** the brain logs each second that did not wake it, with its best score (`missed "…"? best 0.12 in this second`). It logged a score only from 0.25 up, so at sensitivity 9 (threshold 0.25) no miss showed. The Wake Word page trains openWakeWord's "custom verifier" idea on the builder's own tries (numpy, no scikit-learn): a score from 0.1 up to the threshold wakes it when the verifier agrees. A try that scores under 0.1 can't be helped by it: the log shows those. No better trained models were found for the three community words.
- The Pi that drives the Newline (HDMI and the touch cable) has no microphone. The Newline's own microphone works only in its Android Chrome (2026-11-13), not through the Pi.

### 2026-11-23 — The Raspbot v2: Yahboom's app program holds the car, and the board has no watchdog (quick job 72)
**What:** found in Yahboom's software (github.com/YahboomTechnology/Raspbot-V2, and a copy of the factory `project_demo`), not yet on raspbot1. (1) At login, `~/.config/autostart/start_raspbot.desktop` starts Yahboom's phone-app program (`raspbot.pyc`, ports 6000 and 6001). It drives the motors and holds the camera, so a second program fights it. (2) The motor board (I2C bus 1, address 0x2B) keeps the last speed until the next command: it has no stop of its own. (3) Yahboom's PDF names the motors 1 to 4, but its code uses 0 to 3 (0 front left, 1 back left, 2 front right, 3 back right). (4) The wheels are mecanum wheels: the car can also move sideways (not used yet). (5) `ssh raspbot1` (192.168.8.175) gave "No route to host" on 2026-11-23 at 16:30: raspbot1 was off or not on the Wi-Fi.
**Fix:** stop Yahboom's program first (`killprocess.sh`, `docs/guides/raspbot.md`). lab-os's program stops the motors after 0.5 s without a command, when the brain's connection drops, and when it ends. Check the motor numbers with the wheels off the floor (lab check R.3).

### 2026-11-23 — The hub on a phone and on the Pi's touchscreen (quick job 96)
**What:** checked in headless Chrome at 390 × 844, 800 × 480 and 1024 × 600. (1) On the Pi's 800 × 480 screen, the Teleop and Monitor 3D view shrank to a thin line: the page had a fixed height, and the joint list took the room. (2) On a phone, the ask line lay over the module buttons, because it hangs under the core and the buttons came right after the core. (3) At 800 × 480 the fact panels were too narrow: words were cut, and "List all" went past the edge. (4) The docked core covered buttons on an open page. (5) Many buttons were 20 to 30 px high, because the sizes follow the screen and a small screen makes them small.
**Fix:** small-screen rules in the hub, the shared page style, Settings and the Teleop style: a minimum height for the 3D view (the page scrolls), room under the core for the ask line, a tighter grid on 800 × 480, one column of panels on a narrow phone, the docked core in its own corner, and controls of at least about 40 px. Large screens keep their layout. `docs/design/DESIGN.md` → "Screens and places".

### 2026-11-23 — raspbot1 sees only the router's 5 GHz Wi-Fi (lab check N.11)
- The router has one Wi-Fi name for each band. On raspbot1, `nmcli dev wifi list` did not show the 2.4 GHz name, so a profile for it failed ("the Wi-Fi network could not be found"). `sudo nmcli dev wifi connect "<the 5 GHz name>" password …` worked. The first try (2.4 GHz) gave "Secrets were required, but not provided". The cause of the missing 2.4 GHz name is not known. Use the 5 GHz name for the Raspbots.

### 2026-11-23 — An arm with USB but no motor power stops the brain with a traceback (lab check N.17)
**What:** `uv run lab-os serve --host 0.0.0.0` stopped twice. The white arm's USB board was connected, so the brain chose so101-white. In the first try no motor answered (`FeetechMotorsBus motor check failed … Missing motor IDs: 1–6`, found `{}`): the board gets its power from USB, the motors only from the 12 V plug. In the second try motor 2 did not answer (`ConnectionError: Failed to write 'Torque_Enable' on id_=2 … There is no status packet!`): the power was coming on, or a cable between motors was loose. A few minutes later the same command started. `_open_arm` (`teleop/cli.py`) falls back to the fake arm only for `PortNotAllowed` and `LookupError`, so LeRobot's `RuntimeError` and `ConnectionError` stopped the brain.
**Fix:** for now, connect the arm's motor power before you start the brain, or disconnect its USB cable. A clear sentence and the fake arm: quick job 94 in `docs/plan/quick-jobs.md`.
**Later (2026-11-23, quick job 94):** the driver says "so101-white: the motors do not answer. Is the arm's power on?" and closes the port (LeRobot leaves it open after a failed motor check). Found plugged in: the fake arm. Named with `--arm`: it stops with that sentence. LeRobot's own words are in the brain's log.

### 2026-11-22 — Full Access: pictures can't go in a tool's answer, and in-process MCP calls raise (quick job 80)
**What:** (1) OpenAI-style chat takes only text in a `tool` message, so a camera picture can't be the tool's answer. (2) The MCP library's in-process `call_tool` raises `ToolError` for a refusal; over HTTP the same refusal comes back as a result with `is_error`. Its picture field is `mime_type` (not `mimeType`, as in the protocol's JSON). (3) A conversation made outside `create_brain_app` (the tests) had no MCP tools at all, so the hub's chat in those tests never saw the read tools.
**Fix:** after a round of tool calls, the pictures follow as one `user` message with `image_url` parts (`lab_os.ai.tools.ChatTools.take_images`). `create_brain_app` gives a conversation without tools the brain's tools.

### 2026-11-22 — LeRobot's teleop with Rerun: four surprises (quick job 91)
**What:** (1) Rerun is not in `lerobot[feetech]`: it is LeRobot's `viz` extra, so `--display_data=true` failed without it. (2) Rerun 0.33 collects anonymous usage data by default (its viewer prints "Welcome to Rerun"). Its only switches are `rerun analytics disable` (the user's own setting) or a `CI` variable. (3) LeRobot's robots and teleoperators take `calibration_dir`, so LeRobot can read the training files from a copy and never touch its cache. (4) Rerun's own web viewer page links Google's fonts; offline it uses its own font.
**Fix:** the `so101` extra is `lerobot[feetech,viz]`; `CI=1` for the two programs only (a `# HACK:`, current-focus.md); `--robot.calibration_dir` and `--teleop.calibration_dir` point at a temporary copy under the ids `sheep` and `shepherd`. Rerun's page is its own, in a frame, so lab-os's pages still load nothing from the internet.

### 2026-11-22 — The community wake words: 200 KB each, and TARS scores low (quick job 90)
**What:** the three models from the community collection are about 200 KB each (the job said 1 MB). They take the same input as openWakeWord's own (16 embeddings × 96). On macOS's `say` voice, OK computer and hey Friday scored 0.88 and TARS only 0.42, under the default threshold of 0.5. A clip shorter than about 1 s scored near 0 in a test: the detector's first 5 chunks (0.4 s) are its warm-up, so the test pads the clip with quiet.
**Fix:** none in code. The lab check (V.21–V.24) decides whether TARS stays.

### 2026-11-22 — Webcam teleop: the arm can't reach down, and MediaPipe's label is right on a webcam (quick job 88)
**What:** lab check W on the laptop. (1) MediaPipe's left and right labels were right for the webcam's plain picture, though its documents say they assume a mirrored one; the 2026-11-19 choice came from a sample photo. (2) "Can't reach down": the brain's mapping reaches the table in a test with the fake arm's numbers, so the limit is the picture. At 60 cm from a 78° camera the picture is about 48 cm high, and MediaPipe loses the hand before the wrist reaches the edge. (3) MediaPipe's default confidences (0.5) let a hand that wasn't there show for seconds.
**Fix:** the label as it is; hand moves count 1.5 times and the page says to grab again to go further; confidences 0.7 and 5 frames in a row before a hand counts; the hand's turn is sent, so tilting the hand can also point the gripper down. Smoothing chosen with simulated noise (`OneEuro` 0.3 Hz, β 5; 0.2 Hz, β 3 for toward/away): not yet checked on a real hand.

### 2026-11-22 — A transcriber can return its own hint for silence (quick job 83)
**What:** lab check L.11: a push-to-talk press of 0.5 s with nothing said came back from `gpt-4o-mini-transcribe` as the `prompt` we sent ("The speaker talks English to a lab assistant called Jarvis."), and the AI answered it. Whisper-style transcribers are known to do this when the audio has no speech. The other finds of part L had plain causes in the code: the page stopped sending its microphone for the wake word while an answer played; "That's all" sent a final `heard` but no answer, so the page waited on the thinking core; the page ended a wake-word question after 1 s of quiet.
**Fix:** the brain sends no recording without speech (`speech.has_speech`: the loudest 0.1 s must be loud and 3 times the quietest), drops a transcript that repeats the hint, and the hint names the active persona. The rest: quick job 83 in `docs/plan/quick-jobs.md`.

### 2026-11-22 — The WebXR emulator gives the page a Quest's browser name (quick job 87)
**What:** lab check L.5: with Meta's Immersive Web Emulator in the desktop's Chrome, Teleop's **Desktop control** was grey. The page already told a headset by its browser (`OculusBrowser` in `navigator.userAgent`), not by WebXR support. But the emulator also changes `navigator.userAgent` to a Quest's, so the page took the desktop for a headset. The brain's own check (`hub/server.py`, the HTTP `User-Agent`) and the VR hub's (`xr-hub.js`) use the same name.
**Fix:** `teleop/web/headset.js`: a Quest's browser name is a headset only when `navigator.xr` is the browser's own code (the emulator puts a JavaScript copy in its place) and `userAgentData` doesn't name a desktop system. The other two checks are unchanged.

### 2026-11-21 — Laptop checks (lab checklist part L, on the Mac)
**What:** passed: the tests (814 passed, 5 skipped), the settings bar and arrows, All Pages, Teleop's Controls, the answer language, conversation mode, the strong model's line in AI Spend, the full-screen exit on shut down (Cmd+W line, no Close button), webcam teleop W.3–W.8 on the laptop's camera. Found (quick jobs 82–88): "Hey Jarvis" stops a thinking answer but not a playing one; the core stuck on thinking after "That's all"; a push-to-talk press with silence sent the transcriber's own hint ("The speaker talks English to a lab assistant called Jarvis.") as a question, and the AI answered; the question cut at a short pause; "Hi" answered in other languages; the voice changed now and then while the log named one model (`gpt-4o-mini-tts`, `fable`); one false wake while the builder talked to someone; the greeting over the jump after Restart; the WebXR emulator extension made Teleop take the desktop for a headset; webcam hands swapped, a small shake, no reach down, no clear wrist. AI Spend named the Mac "Mac.indy.rr.com": `socket.gethostname()` on a home network can return the internet provider's long name.
**Log of the silence case** (18:14–18:15): conversation mode on; two questions answered (`gpt-4o-mini-transcribe` → `main/gpt-6-luna` → `gpt-4o-mini-tts` `fable`, about 4 s from the end of the question to the first word); "That's all." ended conversation mode; then a push-to-talk "question" 0.5 s long was transcribed and answered.

### 2026-11-21 — Shut down didn't close the hub on the Mac (`uv run lab-os serve`)
**What:** the builder opened the hub in a normal browser tab on the Mac and shut down: the window stayed, full screen, with "lab-os is off". A browser lets a page close only a window that a script opened (Chrome also a tab with one page in its history, as a tab that a command line opened). lab-os can close its own app window ("Start lab-os"), but no tab that a person opened, on any device.
**Fix:** every page now leaves full screen at once (a page may do that without a press) and tries to close; a page that is still open shows only a small card with a big Close button, which says Cmd+W / Ctrl+W when the browser keeps the tab. Checked in headless Chrome: a script-opened window and a one-page tab closed; a tab with history showed the card.

### 2026-11-20 — A fresh copy of lab-os couldn't save a device's settings
**What:** quick job 60 (in a new `git worktree`): the first "This Device" setting failed with "No such file or directory: …/config/local/hub-devices.tmp". `config/local/` is not in git, and the brain wrote the file without making the folder. The lab desktop has the folder, so nobody saw it there.
**Fix:** `hub_devices.DeviceSettings` makes the folder on the first save.

### 2026-11-20 — A settings file broken by hand gave "500 Internal Server Error" and an empty ⚙ (quick job 45)
**What:** lab check F.14: a change to Top Speed showed `500 Internal Server Error`, no "Saved", and Restart Now did nothing; after ⚙ was opened again, the page was empty until the brain restarted. Probably a config file made invalid by hand: the settings page's writer (ruamel) raised its own error, which nothing caught, and the reader had no way to say which file.
**Fix:** a file that can't be read gives one sentence with the file and the line (`config.broken_yaml`), at the top of ⚙ and for a change; nothing on the settings endpoints answers with a bare error number. A restart that doesn't come back in 45 s says to look at the terminal.

### 2026-11-20 — The voice changed to another person between answers (quick job 47)
**What:** the lab heard the assistant's voice change between answers. Both personas use one voice setup (`main`, OpenAI `fable`), so the persona is not the cause. Two paths can change the sound: (1) with the free Gemini key, a TTS model over its limit hands over to the next model, and another model sounds like another person with the same voice name; the greeting's recording could also come from such a model and then play at every start. (2) With OpenAI, each sentence is its own `gpt-4o-mini-tts` request, and the model renders the style text again each time, so the accent can drift. Not confirmed which one the lab heard.
**Fix:** an answer keeps the model that spoke its first part when it can; a greeting from a fallback model is not saved (older recordings are made again once, "v2" in the name); the terminal names the voice and model of each answer and greeting. If the log shows one model and the sound still changes, it is (2): then try `tts-1-hd` with `fable` (no style text) in `config/models.yaml`. **2026-11-22 (quick job 83):** the log showed one model, so `main` now uses `tts-1-hd`.

### 2026-11-20 — The mic button didn't come back after the USB microphone was plugged in again
**What:** quick job 48 (lab day 2026-11-19). The button hides on "devicechange" when the microphone goes, but it stayed hidden after the microphone came back. The page counted the microphones once per "devicechange". On Linux, the browser can send that event when the USB device appears, before the sound system (PipeWire or PulseAudio) lists its microphone; then the one count finds none, and no second event comes. Likely, not proven on the lab desktop: in headless Chrome, a faked microphone listed 1 s after the event gave exactly this.
**Fix:** quick job 73: `web/voice.js` counts again 0.5, 2 and 5 s after each change, and every 5 s while it sees none.

### 2026-11-20 — The hub in VR could miss "lab-os is off" and start anyway
**What:** In lab check S.4, the Quest sat on the hub's start screen in VR when the desktop shut lab-os down. It never showed the off card: a press still started the startup, and the hub came up with no modules and no callouts (the brain wasn't there to give them). The hub in VR turned off only on the one "brain_off" message; why the Quest missed it is not known (its connection was perhaps reconnecting).
**Fix:** Quick job 78: the hub in VR also turns off when the brain doesn't answer (on entering, at a press after a quiet time, after two failed status reads). Its status reads have a 6 s limit: a busy page's first reads took ~2.3 s in headless Chrome, so a short limit gave a false "not reachable". A brain that's gone fails at once ("connection refused").

### 2026-11-20 — Headless Chrome on the Mac: WebGL needs ANGLE's SwiftShader
**What:** `--use-gl=swiftshader` gives "Could not create a WebGL context" on macOS, and the VR hub's preview stops at "Couldn't start". The test looks like it ran, but no scene ever drew.
**Fix:** Launch Chrome with `--use-angle=swiftshader --enable-unsafe-swiftshader`.

### 2026-11-20 — An app window counts as "standalone", so the Full screen button hid
**What:** quick job 74. The Full screen button hid in the window that "Start lab-os" opens (Chrome's `--app`). The pages counted `display-mode: standalone` as full screen, and an `--app` window matches it, with its title bar (checked in headless Chrome). Also, a browser takes a page out of full screen when that page opens a new window ("Open on…" → another monitor), and a page may go full screen again only from a press.
**Fix:** "standalone" no longer counts as full screen (`src/lab_os/web/fullscreen.js`). In lab-os's own browser, the brain puts a window in full screen through the DevTools port (`POST /api/window-state`, `Browser.setWindowBounds`). This is the browser's full screen, as F11: Esc does not leave it, and F11 does.

### 2026-11-20 — A web page can't bring its own window to the front
**What:** quick job 59 (one hub window). A page can't raise or close a window that it didn't open itself, and the browser's `--app` flag opens one more window on each call. The window manager tools (`wmctrl`, `xdotool`) are not installed on Ubuntu and do nothing on Wayland.
**Fix:** lab-os starts the hub in a browser of its own: its own profile folder (`~/.cache/lab-os/hub-browser`) and the browser's DevTools port on 127.0.0.1 only (`--remote-debugging-port=0`, the port is in the profile's `DevToolsActivePort`). A second tap asks that port for the hub page and activates it (`/json/activate/<id>`). Side effects: it is a separate browser, so the microphone permission and the browser's own settings start empty once. Any program on the brain's computer can control that one browser through the port. Shut down and Ctrl+C close its pages through the same port (`/json/close/<id>`, quick job 64).

### 2026-11-20 — Lab day: shut down, devices, the icon and the Kinect
**What:**
- Shut down (part S): the arm stopped at once and went limp, the terminal closed, and every page on the desktop said "lab-os is off". In the Quest, the "lab-os is off" card showed, but some ways of moving around in VR still showed the broken hub behind it (what it was: the entry above, quick job 78). There is no clear way to leave full screen in the Quest and get back to the browser.
- After the arm's USB was unplugged and plugged in again during S.3, the arm was not found again (quick job 73).
- Each click on "Start lab-os" opens one more hub window (three clicks, three windows, one brain). The builder wants one window, and shut down closes it, like a normal program.
- Open on… → Another monitor of this computer: the page that opened it leaves full screen, and the new page opens as a window. After that, and after F11, neither has a full screen button.
- Devices (part 11): Open on…, Back and Bring it back worked between the desk and the Newline's own Chrome. Monitor could also open on the Newline while it was open on the desk. After Ctrl+C, both hubs came back in about 3 s; meanwhile the core was grey, with no "lab-os is off". After both were switched off and on, both came back under their names, and the Newline kept its resolution.
- The Newline's own Chrome has "Install" and "Create shortcut", not "Add to Home screen". "Create shortcut" works. Its Chrome is too slow to use: the teleop page keeps redrawing.
- AI tools (mostly Sonnet 5.5) often say that the arm did not quite reach a pose, although it looks right (quick job 77).
- The Kinect (model 1414) has an adapter with a normal USB plug and a power plug. `lsusb` showed only `045e:02b0 Xbox NUI Motor`. Its power was plugged in. The Kinect is usable: the lab has shown its picture on a display before. Why `lsusb` listed only the motor is not known; a session that uses the Kinect checks it.
**Fix:** quick jobs 59, 64, 73, 74, 76, 77 and 78.

### 2026-11-20 — "Start lab-os" opened the hub with a title bar, and the start press did not go full screen
**What:** Brave on the lab desktop (GNOME, X11, two monitors) with `--app=… --start-fullscreen`: Brave showed "To exit full screen, press F11" at once, but the window kept its title bar. The hub's start press then did nothing, because Brave believed it was full screen already. Tested with a new profile: with the flag, the press gave no full screen; without it, the press gave full screen (2560×1440). F11 worked.
**Fix:** on Linux, `lab-os icon` and `--open` start the browser with `--app` only. The start press makes it full screen.

### 2026-11-20 — `lab-os serve` now takes the real arm by itself
**What:** Since quick job 61, `lab-os serve` with no `--arm` opens the SO-101 that is plugged in, and switches its torque on (it holds where it is, it does not move). A coding session that starts the brain to look at a page would take the white arm too. A brain that already has the arm keeps it: the second one says the port is in use and drives the fake arm.
**Fix:** In a coding session, start the brain with `--arm fake`. The tests never see a port (`tests/conftest.py`, `_no_arm_plugged_in`).

### 2026-11-20 — The tests failed after a change on the settings page, or with an arm plugged in
**What:** In the lab, the settings page saves into the repo's `config/` (persona, chat keep time, the hub's look and buttons, the limits). The tests read that folder and expected the committed values, so 6 tests failed after the builder changed settings. One more test failed because so101-white was plugged in: the visitors' welcome names the robots whose `/dev/serial/by-id/…` port exists.
**Fix:** `tests/conftest.py` gives each test run a copy of `config/` as last committed (`git archive HEAD config`) and uses it as the repo's config. Changes on the settings page do not change the tests now. A committed change can still make a test fail: then update that test. The visitor test's brain treats every port as unplugged.
**Since 2026-11-20 (later the same day):** replaced. The settings page writes into `config/local/` (not in git), so `config/` holds only the defaults, and the tests read it as it is, with an empty `local/` (`docs/dev/places.md` → "The place's own changes").

### 2026-11-20 — The wake word: not reproduced, but one screen could make every screen deaf for 2 minutes
**What:** (quick job 42, for the lab-day entry below.) Tried on the Mac with the designed hub in headless Chrome, a fake microphone that says "hey Jarvis" every 7 s, and a stand-in for OpenAI (full spoken answers): the wake word kept working after a sensitivity change sent to the brain, after one made in ⚙ in the hub, after full answers, and the venue switch changes nothing for it (both personas have `hey_jarvis`; neither venue is public). Found in the code instead:
- The brain ignores the phrase on **every** screen while **any** screen is busy: the chat answering, a question being heard, or a screen still playing an answer.
- "Still playing" lasted until the page said it had played the answer, or for **120 s** after each spoken piece. A page that never says so (a second window, a tab that the browser paused, a held greeting that never played) kept every screen deaf for 2 minutes after each answer it got. A "still playing" message also added 120 s. Nothing was logged.
This fits "came back much later" (visitor mode) and maybe the others; not proven.
- The greeting delay after ⏻ and start (lab check 9.2): by design, the designed hub plays the greeting while it is typed under the title, about 6.5 s after the tap, on every start (measured 3 times).
**Fix:** "still playing" now lasts the audio's own length plus 10 s (a held greeting waits for the startup), and a "still playing" message adds 3 s. When the brain ignores a heard phrase, its terminal says why, every 10 s at most ("voice: desk heard the wake word, ignored: newline hasn't said it finished playing (8 s more)"). After Back to the start screen, the next start speaks the greeting at once (0.15 s). **2026-11-22 (quick job 84):** the builder wants it to wait for the jump again, as after the first start. If the wake word stops again, the terminal's lines say which one it was: lab check part V.

### 2026-11-20 — Tic-tac-toe: straight down reaches a thin ring, and `home` and `ready` sit over the board
**What:** (preview 1, found on the fake arm's 3D model.)
- Pointing straight down (tool angle 180), the SO-101 reaches only a ring about 17 to 22 cm from its base (from `ready`: a band about 14 to 19 cm to each side). A 3×3 grid of 6 cm cells doesn't fit in it. Tilted 15° (165), it reaches up to about 30 cm.
- The IK solves from the arm's pose now. From `home` (folded), no start spot was reachable straight down, though the same spots work from `ready`.
- `home` puts the gripper point 19 cm in front of the base and 1.6 cm high; `ready` 26 cm out and 5 cm high. Both are over a board 15 to 33 cm out, so either pose knocks pieces over.
- 12 cm above the table, straight down is out of reach at 18 cm out (the wrist would need to be about 22 cm up).
**Fix:** the board's cells are put down at 165°; the robot's pieces wait in the straight-down band beside the base, where `pick_at` works. During a game the arm waits at a park point beside its base and travels 9 cm high through one point above the board's near edge; `ready` only at the start (board empty), `home` only at the end. All in `config/games/tic-tac-toe.yaml`, tested to every cell (`tests/test_tic_tac_toe.py`).

### 2026-11-20 — A closed page could leave a Gemini Live connection open; one test waited 31 s for it
**What:** (quick job 56, faster tests.) `test_two_screens_hear_it_one_answers` spent 31 s in its teardown. When a page's `/ws/voice` connection ends, aiohttp cancels the handler, and the cancel also stopped the handler's own cleanup in `finally` (closing the page's hearing). The hearing's Live websocket to the voice service then stayed open. Closing the client session doesn't close it: aiohttp detaches a websocket's connection from the session's pool. The fake service waited for it until its shutdown timeout. In the lab the same thing could keep a Gemini session open after a tab closed. Also: pytest tore down `aiohttp_server` (the fake services) before `aiohttp_client` (the brain), so a hearing that connected just as a test ended waited the full 3 s for a goodbye from a service that had stopped answering.
**Fix:** the page's voice cleanup runs in its own task that the cancel can't stop, and the brain's shutdown waits for it (`voice_ws`). `tests/conftest.py` overrides `aiohttp_client` to set up after `aiohttp_server`, so the brain closes first. The tests also skip the robot tools' 0.5 s hold and 0.2 s settle (the fake arm arrives at once). The tests went from 136 s to about 44 s in one process.

### 2026-11-19 — Webcam teleop: MediaPipe's left and right, and an open hand that reads as a pinch
**What:** (preview 2, the webcam page, tried with MediaPipe's own sample photo of two hands as Chrome's camera.)
- MediaPipe's handedness label assumes a mirrored (selfie) picture. For a camera's plain picture it names the other hand. The labels do follow crossed arms: "the hand on the picture's left is the right hand" chose wrong on the photo, the labels chose right.
- With the Quest's pinch scale (tips 6–7 cm apart = 0), the photo's relaxed open hands read 72–87 % pinch: enough to hold the clutch (over 60 %). A hand with its thumb along the index finger still reads about 60 % at 5 cm.
**Fix:** the page uses the opposite label, and the position in the picture only when both hands carry the same label; a **Swap left and right hands** box for the lab. Pinch is now 5 cm apart = 0, 2 cm = 1 (`webcam-hands.js`). Lab check W.3 and W.4 say if that is right for a real hand. (2026-11-22, quick job 88: on a real webcam the opposite label swapped the hands, lab check W on the laptop. The page now uses MediaPipe's label as it is.)

### 2026-11-19 — The teleop pages say "frozen: release grip" while the grip is already released
**What:** after any freeze (also the brain's first input), `status.needs_release` stays true until the arm moves again, even with the clutch let go: it is the mapper's flag *or* the jog's (`loop.py` `status()`), and the jog's flag clears only with keyboard jogging. So with a Quest or the webcam, the Arm chip says "frozen: release grip" (the webcam page: "frozen: let go of the clutch") until the next grab, though the release already happened. Nothing moves wrongly; only the words are off.
**Fix:** not changed (it is in the teleop loop, which the builder reviews). The webcam page's own state shows the page's freeze, which is correct. (2026-11-20, quick job 66: fixed. `status.needs_release` is now the flag of the input that drives: the keys' flag for keys, the hand mapper's for a Quest, hands or the webcam.)

### 2026-11-19 — A teleop test that holds the grip from its first frame fails when the loop ticks first
**What:** quick job 44's pull request. `test_stop_works_from_a_monitor` failed on GitHub, and locally only after `test_shutdown.py`. If the loop's first tick comes before the page's first frame, it freezes (no input) and then wants the grip released before it engages. The test held the grip from its first frame, so it never engaged. The race was there before; a small change in timing showed it.
**Fix:** the test (and the two-arms test like it) sends a released frame first, as a real controller does.

### 2026-11-19 — A stopping aiohttp server waits up to 60 s for open pages; the AI tools keep working meanwhile
**What:** quick job 44. `AppRunner.cleanup()` waits for every running handler (`shutdown_timeout`, 60 s by default). An open WebSocket is a running handler, and aiohttp doesn't close WebSockets by itself, so with pages open the brain stayed up about 30 s after "Shut down" (31.4 s measured). The teleop loop and the MCP server ran the whole time, so an AI tool's next small move started and the arm moved to its goal. uvicorn (the MCP server) waits the same way for an AI tool's open stream, and cutting it prints an error trace.
**Fix:** `TeleopLoop.shut_down()` refuses every move from the start of a shutdown. `on_shutdown` closes every page's WebSocket (`close_sockets`), `shutdown_timeout` is 1 s, and the MCP server ends each session before it stops (a `# HACK:`, current-focus.md). A new long-lived connection (a stream, a socket) must be closed there too.

### 2026-11-19 — Lab day: the wake word stops after a settings change
**What:** on the desktop, the wake word stopped after a change to Wake Word Sensitivity and came back only after a restart (lab check 9.7). During visitor mode it stopped too, and came back much later (F.11). On the Quest it did not answer until the builder changed Level of Detail (F.6). When it works, it is reliable.
**Fix:** quick job 42 (2026-11-20, the entry "The wake word: not reproduced…" above).

### 2026-11-19 — Lab day: the room decides what the microphone hears, not the sensitivity
**What:** the desktop faces the wall, and the USB microphone is in its front port, about 60 cm from the chair. A dividing wall stands between the desk and the door. A loud fan on the roof makes noise above the desk at times. Without the fan, the wake word works about 9 times in 10 near the microphone, and from the front of the room with a raised voice. With the fan and more than a few feet away, it is unreliable. Sensitivities 5, 7 and 9 made little difference. Without "hey", "Jarvis" inside a sentence woke it 0 times in one minute.
**Fix:** none in code. The builder keeps the sensitivity setting. A USB extension cable can put the microphone on the table, facing the room.

### 2026-11-19 — Lab day: voice timing and languages
**What:** push-to-talk took about 9 s to the first spoken word (9.3). After a wake word question, the answer started 4.2 s and 5.3 s after the question ended (the words were final after 0.5 to 0.9 s, the first text came 1.8 to 2.9 s later). After ⏻ and start, the greeting did not start at once (9.2). With Answers: English, a typed Spanish question got a Spanish answer and no voice; a typed "你好" got English (9.14). Listens: English still let other languages through ("ni hao"), and a few times "test" came out in Cyrillic. The voice sometimes changed to another person between answers. The microphone button disappeared when the microphone was unplugged and did not come back when it was plugged in again. With the lab-assistant persona, spoken questions came back as words in German, Turkish or Portuguese, with Listens on English and on Any; JARVIS was fine (2.9).
**Fix:** quick jobs 42 (the greeting), 46, 47, 48 and 55.

### 2026-11-19 — Lab day: the Newline is smooth only by HDMI at 1600×900
**What:** in the Newline's own Chrome, the startup was not smooth at Drawing Resolution 1 or 0.5 (0.5 is also blurry). By HDMI from the desktop, Ubuntu shows 60 Hz at 1920×1080, but everything on the Newline looks like a low frame rate (the desktop's other monitors are normal). At 1600×900 it is smooth and readable from 3 m. The Newline has no "PC" or "Game" picture mode. Ubuntu and the Pi show it as "Hitevision group 32". Its USB touch cable works (the desktop's xArm cable was out from then on), but with a second monitor connected, touch did not land correctly. Its speakers play the hub's voice by HDMI. A Pi by HDMI and USB touch works the same way: smoother at 1600×900 than at 1920×1080, but less smooth than the desktop or a laptop.
**Fix:** the route is HDMI at 1600×900 with the USB touch cable (`docs/plan/log.md`, 2026-11-19). Touch with a second monitor: quick job 54.

### 2026-11-19 — Lab day: the classroom's Extron panel feeds the ceiling speakers
**What:** the teaching station has an Extron panel: Display On and Off, inputs PC, Laptop, Wireless and Wall Plate, and a volume knob. There is an HDMI cable at the station (labelled "Laptop") and an HDMI socket in a wall plate. An XLR socket labelled "mic" is at the front of the room. A laptop on the station's HDMI plays through the ceiling speakers, and a hub page on it (the desktop's address) played the startup and the greeting clearly everywhere in the room. The same input also goes to the projector.
**Fix:** none needed. Sound in the ceiling with the picture on the Newline: `docs/plan/ideas.md` → "Room sound and the Newline's picture at once".

### 2026-11-19 — Lab day: the white arm's camera cables were in each other's sockets
**What:** `so101-white-cam-wrist` showed the stand camera's view (F.1). The config was right (wrist = socket 7, stand = socket 8); the two USB cables were the wrong way round. The builder swapped them, and the names were correct. The stand camera's picture was blurry.
**Fix:** the cables, not the config. The names follow the socket until the powered USB hub arrives (`docs/plan/current-focus.md` → "Hacks to clean up"). The blur: turn the stand camera's focus ring, if it has one.

### 2026-11-19 — Lab day: the arm kept moving after "Shut down lab-os"
**What:** F.9. The arm went limp, but the AI tool's move went on and the arm moved to its goal. The terminal stayed about 30 s after `shutting down: asked from…`. The page in AR did not show "lab-os is off". The checklist also asked for the "Start lab-os" icon before step 11.1 had made it, so the icon opened as a text file.
**Fix:** quick job 44. The checklist's rules now say: a step comes after the steps that it needs.

### 2026-11-19 — Lab day: STOP was not on the hub during the visitor wave
**What:** F.11. To stop the wave, the builder had to open Monitor quickly: the designed hub had no STOP button in view. The wave itself works but does not look much like a wave.
**Fix:** quick jobs 43 (STOP) and 52 (the wave).

### 2026-11-19 — Lab day: Top Speed gave "500 Internal Server Error", then Settings was empty
**What:** F.14. A change to Top Speed showed `500 Internal Server Error` under the field, no "✓ Saved", and the amber bar only at the top of the page. Restart Now did nothing. After ⚙ was closed and opened again, the page showed nothing. After the brain was stopped and started again, all of it worked (Saved, Restart Now, the arm connected again). Changing a number and changing it back still asked for a restart. The order arrows of Buttons Around the Core do not line up and look like lines.
**Fix:** quick job 45.

### 2026-11-19 — Lab day: smaller findings
**What:**
- Every move to `home` says "clipped" on AI Control, because two of home's numbers are past the soft limits (quick job 30). The arm still arrives where it should (F.3; quick job 50). (2026-11-20, quick job 50: home is now at the soft limits, so it no longer says "clipped".)
- The table height is right: the jaw tips touched the table at z 0.0 (F.2). Farther out (x 24.5 cm) they touched the sheet at z −0.4 (3b.1): the arm sags a little at reach.
- The cm grid saw 24 of 24 corners, worst 1.3 mm. The AI found the cube from the stand camera's picture (to about 1 cm), went above it, and picked it with `pick_at`. The jaws held the cube with their tips only (3b.5; quick job 51). The grid is a flat fit with no lens correction, so it is less exact far from the sheet (`docs/plan/ideas.md`).
- Quest view: closing the window with its own X leaves the button lit (F.12; quick job 49). (2026-11-20: the hubs asked only every 5 s, and a press acted on that old state; now they ask on focus, every second while it's open, and before a press.) The view looks like a fisheye lens. The one-eye crop showed one eye.
- In the headset, when you put the controllers down, the Quest changes to hand tracking, so the status panel never shows "No controller" (F.13).
- The startup as a video is a little smoother, but its resolution is lower (even at Maximal) and the stars do not match when it changes to the live hub (F.8). It stays off.
- Restarting `lab-os serve` by hand brings the hub back, but not full screen. A browser goes full screen only after a tap.
- When the Newline's hub speaks, the desktop's core shows the speaking animation too.
- A lot of content text is all lowercase ("clipped", "arrived", status words; quick job 53).
- People who see the hub look at "JARVIS" first, although it is in two small places.

### 2026-11-19 — The pages' 3D arm takes every `arm_command`, whatever its `device`
**What:** two arms at once (preview 3). Every `arm_command`, `arm_stop` and `arm_resume` has a `device` field, but `ArmFeed` (`teleop/web/arm/arm-feed.js`) never reads it. A second arm's commands on `/ws` would make the 3D arm jump between the two arms, and its `arm_stop` would show the right arm as frozen.
**Fix:** the second loop sends no `arm_*` messages. Its state goes in `status.left_arm`. A 3D view of two arms must first make `ArmFeed` filter by `device`.
**Replaced the same day:** `ArmFeed` now follows one arm (right or left) and takes only messages whose `device` is that arm, so both arms send `arm_*` messages again.

### 2026-11-19 — Two 3D arms loaded at the same time: the second one never moved
**What:** with two arms, the teleop page loaded both SO-101 models at once. The second model stood still in its rest pose, without the frozen colour, although it got every joint angle. Most likely, three.js shares a file request that is already running, so the second loader's manager said "done" before its meshes were in, and the model was made without them.
**Fix:** `loadArmModel` loads one model at a time (a queue). The headset scene benefits too.

### 2026-11-19 — The Claude Code hook refuses a command that only names LeRobot's calibration folder
**What:** a Bash command that wrote a lab checklist step (in a heredoc) was refused, because the step's text had the path of the green arm's training calibration in it. The hook (`.claude/hooks/guard.sh`) reads the command's text, not what it does.
**Fix:** write such doc text with the editor tool instead of a shell command. Leave the hook as it is: it guards the green arms' rules.

### 2026-11-19 — colorlog treats an empty `NO_COLOR` as set, and checks a pipe only when it gets the stream
**What:** quick job 40. no-color.org says that `NO_COLOR` counts only when it is not empty, but `colorlog` checks only that the name exists. `colorlog` also colours a pipe unless you give it `stream=`.
**Fix:** `lab_os.term.use_colour` decides once (`FORCE_COLOR`, then a non-empty `NO_COLOR`, then `isatty()`) and gives `colorlog` the answer as `force_color` / `no_color`.

### 2026-11-19 — OpenAI's real cost needs an Admin key, not the key lab-os has
**What:** quick job 41. OpenAI's usage and costs endpoints (`/v1/organization/usage/…`, `/v1/organization/costs`) refuse a normal project key (a missing `api.usage.read` scope). They need an Admin key (`sk-admin-…`), and only an Organization Owner can make one. So lab-os can't read the bill with the professor's key.
**Fix:** none built. The AI Spend panel says "Estimated · this computer's brain only". `docs/guides/hub.md` → "AI Spend" says what the professor would have to create.

### 2026-11-19 — The settings page didn't come back after "Restart Now"
**What:** quick job 38. The hub pages and teleop pages reload once the brain is back because their live connections (`/ws/hub-device`, `/ws`) notice it. The settings page has no live connection of its own, so after a restart it kept saying "lab-os is restarting".
**Fix:** after asking for a restart or shutdown, the settings page asks `/api/status` every 2 s and reloads once it has seen the brain go and come back. A new page without a live connection needs the same.

### 2026-11-18 — A pop-up inside a hub panel is cut off, even with `position: fixed`
**What:** the ⏻ menu (quick job 6), put next to its button inside the designed hub's status strip, didn't show at all. Every `.panel` has a `clip-path` (the unfolding, the cut corners), and a clip-path clips its descendants, `position: fixed` ones included.
**Fix:** pop-ups go straight under `<body>` (the ⏻ menu is appended there by its script, like the full-screen notice), never inside a `.panel`.
### 2026-11-18 — scrcpy brings its own adb, and two adb versions stop each other
**What:** quick job 36. scrcpy's release (v5.0.1) includes adb 37.0.0. When a different adb version runs a command, it finds the other version's server on port 5037, stops it ("adb server version doesn't match this client; killing...") and starts its own, which drops every `adb reverse`: teleop's page on the Quest loses the brain. Also: Quest system versions 74 and later gave scrcpy a black or flickering picture (scrcpy issue #5913) until scrcpy v4.0 (2026-05) worked around it.
**Fix:** lab-os starts scrcpy with `ADB=` the system's adb when there is one (the one `adb reverse` was run with), the bundled one only when there's none. Pinned to scrcpy v5.0.1.

### 2026-11-18 — The system diagram got smaller each time it was opened
**What:** closing a page in the designed hub removes only `.detail` elements from the module slot; the system diagram's box (`.sysbox`) isn't one, so it stayed, and the next opening added another beside it. The two shared the width, and the redraw went to the old one: half size, on the left (a third on the third opening).
**Fix:** closing removes `.sysbox` too. Anything new put in `#mod-slot` must be removed in `closeModule` as well.

### 2026-11-18 — Recording the startup: slowing Chrome's animations also slows its frame times, and the jump's streaks depend on the frame step
**What:** quick job 34. To record the startup smoothly, the page runs 8× slower (its clock and timers patched, CSS animations slowed with the DevTools `Animation.setPlaybackRate`) while frames are captured. Two surprises: (1) `setPlaybackRate` also slows the timestamps `requestAnimationFrame` hands out, so slowing them again in the page made the drawing clock run 64× slow and the white flash never ended; (2) the jump's streaks are as long as a star moved since the last frame, so with 8× more frames each streak was 8× shorter and the jump came out black. Also checked: the concept and the real hub run the same startup code and the core follows the same curve (big at the flash, a long brake to 1.3×, a 1.6 s hold, then into place), with no frame over 40 ms on the Mac even with the CPU slowed 4×; the concept alone drops frames while loading its web fonts. So no hitch in the designed motion itself; the two-step shrink of the core is by design.
**Fix:** the recorder (`scripts/record_startup.py`) gives the page one drawn frame per 8 of the browser's, stamped with the page's slowed clock, so each drawn frame is a normal 1/60 s step.

### 2026-11-18 — The AI status blinks off while idle: one failed check showed as "not connected"
**What:** lab check 6.4: now and then, with nobody using it, the strip said the AI was disconnected and the core greyed, then it came back; no pattern. **Cause, from the code:** three things could flip it, and none logged anything. (1) The brain's AI check (every 60 s, listing the service's models, 10 s timeout) counted any single failure as "not connected", then waited 20 s to try again: one slow name lookup for `api.openai.com` or one hiccup on the campus network greys the hub for ~20 s. It fits best: the internet check uses bare IP addresses, so it stays "online" while only the AI goes off, as seen. (2) The internet check (every 30 s, 3 s timeout) counted one miss as offline for 30 s, and the AI then counts as not connected without being asked. (3) Each hub page counted one failed status poll (every 3 s) as "brain not reachable, AI not connected". **Not reproduced here:** on the builder's Mac, 82 checks over 14 minutes all answered (slowest 1.0 s), a pooled connection reused after 4–14 s idle never failed, and a headless `/design` watched for 15 minutes never blinked. So it's the lab's network, not a timer in the code.
**Fix:** quick job 32. A failed AI check while connected is asked again twice, 3 s apart, before the hub shows it; the internet check tries once more after a miss; the pages need two missed polls in a row. Every change is logged with its reason (`AI: main not reachable (HTTP 503): shown as not connected`, `AI: main answers again`, `internet: offline`), so if it still happens, the brain's terminal says why.

### 2026-11-18 — The real folded pose is past two joint limits and, in the 3D model, below the table
**What:** quick job 30. The green follower as the builder leaves it (lab check 8.16) reads shoulder_lift −103.3 and elbow_flex 97.4: 6.3° and 3.6° past the soft limits (−97.0 / 93.8), and past the URDF's own limits (−100 / 96.8) by 3.3° and 0.6°. The arm folds further than the model allows. With the other numbers (wrist_flex 75.9), the model puts the gripper point 1.3 cm below the table (0.9 cm once the two joints are clipped), so the floor refused `go_to_pose home`: the height reads 1–2 cm low near the table (2026-11-12) and the jaws really rest on it.
**Fix:** the builder's choice: `home` hovers just above the rest. The real numbers, the two joints clipped at their soft limits (the move says so; the limits aren't widened), and wrist_flex 55 instead of 75.9: the lowest point ~1.8 cm above the table (~3.4 cm on so101-white's plate). Let go of the arm and it settles into the real rest. Lab check F.3.

### 2026-11-18 — A failing STOP inside the teleop loop's error handler would end the loop
**What:** quick job 27. When a step failed (e.g. the arm stopped answering), the loop froze the arm, and that freeze wrote to the arm again (`stop()` holds where the motors are). With the USB gone that write fails too, inside the error handler, so the loop task would end: every page "connected", nothing moving, no message (as in the 2026-10-29 entry; a second way in). That may be part of what lab check 10.5 saw ("following" but nothing moved after replugging); the repeated "read failed" lines come from the status broadcast, which kept running. Not confirmed on the real arm.
**Fix:** a freeze never lets a failing `stop()` out (it's logged), and a failed step checks the USB at once, so an unplug is reported as one line, not a traceback per tick.

### 2026-11-17 — Unplugging a real arm while the brain runs: the hub doesn't notice, and after replugging it's stuck
**What:** lab check 10.5. With `so101-white` driven by the brain, its USB cable was unplugged: the hub still showed it connected. Plugged back in, teleop showed "following" but the arm didn't move, and the brain repeated `so101-white: read failed (Failed to sync read 'Present_Position' … [TxRxResult] Port is in use!); using the last reading`. Likely (not checked): the brain keeps the old port open after the cable goes, and never opens the new one.
**Fix:** quick job 27 (notice the unplug, say so on every page, reconnect when it's back). Until then: after replugging an arm, stop the brain (Ctrl+C) and start it again.
**2026-11-18:** built (quick job 27): the brain checks the arm's `/dev/serial/by-id/` name every half second, lets go of the port when it's gone and opens it again when it's back. Not yet tried on the real arm (lab check F.4–F.5).

### 2026-11-17 — The Quest's wake word misses just under the line
**What:** lab check 10.4: of 10 "Hey Jarvis" on the Quest, the misses printed `a screen heard something like "hey Jarvis" (0.40; it takes 0.50 at sensitivity 5)` and `(0.47; …)`. It heard the words; the score was just short.
**Fix:** raise the Quest's sensitivity (⚙ → This device → Wake word sensitivity, 6 or 7). Lab check F.6.

### 2026-11-17 — The voice assistant heard English as another language
**What:** lab check 10.4: twice, a spoken English request was taken as another language and answered in it. Mandarin, said on purpose, worked (it opened and closed Monitor).
**Fix:** quick job 33: an input and an output language per device, each "Any" or "English". Built 2026-11-18: Output English is an instruction to the AI and works with any voice; Input English only reaches OpenAI's transcription. Gemini's live transcriber (the lab's voice at the time; OpenAI's since its key went into `.env` the same day) has no language setting; a test with English said by macOS's French, Chinese and German voices was heard right with and without an instruction, so the misheard English wasn't reproduced (`docs/guides/voice.md`).

### 2026-11-17 — The VR hub's far-away dot cluster only shows in AR
**What:** lab check 10.1: the cluster is visible only in AR (passthrough), straight ahead, behind the idle circle, not moving. In VR it's probably there too but black on black. When the hub's network bursts into place, its dots seem to fly out of that cluster.
**Fix:** quick job 10 (2026-11-18): found, see the entry below.

### 2026-11-18 — In AR, additive blending covers the room: a black glow is a dark shape
**What:** the VR hub's cluster of dots (above) was the network's links, drawn black while the dots wait in a tight clump far ahead for the jump. Three's `AdditiveBlending` adds colour but also writes opacity, and in AR the headset shows the room only where the picture is see-through, so black lines with opacity covered it as a dark clump (in VR: black on black, invisible). The faint stars of the start screen were dark specks the same way. Seen without a headset: `/xr?preview&passthrough` draws the AR way (transparent), over a light page.
**Fix:** every glow in the VR hub uses `GLOW` (`xr/draw.js`): it adds light like before but leaves the opacity alone (`blendSrcAlpha` zero, `blendDstAlpha` one), so a glow can only brighten the room. A test fails if `AdditiveBlending` comes back. On the Quest itself: lab-checklist F.10.

### 2026-11-17 — Hiwonder glove: all five LEDs must be lit to drive the xArm
**What:** with the glove paired to `xarm1`, only the base followed the hand; the other five servos bent to one end and clacked. Both gloves had been switched to a robot-hand mode (each finger drives its own servo, tilt drives servo 6 = the xArm's base). The arm and lab-os were fine.
**Fix:** press **K3** on the glove until **all five LEDs (D1–D5)** are lit ("robotic arm, bus servo" mode; one LED is the right-hand robot-hand mode). After every glove restart: right hand, palm down, fist; switch on; when the LEDs go off, open the hand. To re-pair, press **DEL** with the arm on. Manuals: `docs/device_manuals/Hiwonder_Wireless_Glove_*.pdf`.

### 2026-11-17 — so101-white's two cameras answer to each other's names
**What:** during an AI pick, `camera_snapshot so101-white-cam-wrist` showed the table from above (the arm, the Quest, a box), and `so101-white-cam-stand` showed the view along the jaws (the cube between them). The names in `config/devices.yaml` point at the wrong video ports.
**Fix:** lab check 3.9 (2026-11-17): unplugging the wrist camera removed `usb-0:7`, so the wrist camera is socket 7 and the stand camera socket 8, as on the green set. Swap them in `config/devices.yaml`: quick job 29.
**2026-11-18:** swapped (quick job 29): `so101-white-cam-wrist` is `usb-0:7`, `so101-white-cam-stand` `usb-0:8`. Lab check F.1.

### 2026-11-17 — so101-white stands on a ~1.6 cm plate, so its "z = 0" is above the table
**What:** the arm sits on the stand camera's base plate. Its z = 0 is the bottom of the arm's own base, so the real table is about z −1.6 cm (the builder measured the jaw tips 3 cm off the table at a reading of 1.4 cm). `pick_at` goes down to half the object's height *in the arm's numbers*, so it would close near the top of a 3 cm cube; the 0.5 cm floor also stops the tips ~1 cm above the real table. Done by hand instead (open, `move_to` z 0 ≈ the cube's middle, close, lift): picked and placed fine. The elbow also sags ~3° on most moves (the gripper ends ~1 cm low/short): harmless at this size.
**Fix:** quick job 28 (a table height per arm). Lab check 3.2 agrees: told z 2, the tips stopped about 0.5 cm above the top of the 3 cm cube, so about 1.5 cm higher than asked.
**2026-11-18:** built (quick job 28): `table_z_cm: -1.6` for `so101-white` in `config/devices.yaml`; every height the AI tools and teleop use is from the table. The venues' floor became 1.1 cm (from the table), the place −0.5 cm from the base put it. Lab check F.2.

### 2026-11-17 — so101-white jumped far past a go_to_pose step (cause not found yet)
**What:** before the move, `arm_status` put the gripper point at z = −3.9 cm (below the table, impossible unless it was pressing on it). `go_to_pose ready` was capped to 34 % of the way (shoulder_lift 45.3° → about 23°), but the arm **jumped** and read shoulder_lift −28.7°, elbow 24°: about 52° and 22° *past* the command, beyond the ready pose itself. The builder saw the upper arm about 60° from the table, which matches the −28.7° reading (0 = straight up), so the reading *after* the move was right. The software path looked right (the cap clipped the target; the motion starts from the read position and ramps). Suspect the reading *before* the move (gripper below the table): if the start was misread, the ramp starts from the wrong place and the arm lurches. Also: the result said "short of the command … by 51.9°" though the arm *overshot*; the message ignores direction.
After that, readings were steady, a 5° shoulder test moved 5.1° smoothly, and two more `go_to_pose ready` steps arrived exactly. So the motors and calibration look fine now. But the "below the table" start may not have been a bad reading: so101-white stands on a ~1 cm plate (the stand camera's), so the real table is at z ≈ −1 cm in the arm's frame (z = 0 is the bottom of the arm's base), and the model's gripper point isn't checked against the real arm near the table. The driver already sets goals to the current position before torque goes on, so a stale goal is unlikely too. Cause still unknown.
**Fix:** none yet. If it happens again, note what ran on the arm just before (teleop, a restart, the arm being moved by hand).

### 2026-11-17 — A backtick in the button's text broke all of desktop control
**What:** the desktop-control button's text is a JavaScript template string (between backticks), so writing "` to leave" in it ended the string early: the whole `desktop-input.js` failed to load and the Desktop control button did nothing. A test that only reads the text passed anyway.
**Fix:** write it as \` inside the template. The test now runs `node --check` on the script where node is installed, and the page was tried in a headless browser.

### 2026-11-17 — The teleop readout said "outside model limits" for a joint held at its limit
**What:** lab check 8.9 on `so101-green`: `elbow_flex` read "97.4 clamped by driver → 96.8; outside model limit". The row shows the *command* (97.4°), and the "outside" note compared that command with the 3D model's URDF limit (±96.8°), so every command the driver cut to its limit was also called "outside", though the arm itself sat at the limit, inside it. The driver's own limits (the URDF narrowed by the calibration, sent in `status.limits`) weren't used at all.
**Fix:** quick job 24: the note compares the angle the driver holds with the driver's limits in force (`teleop/web/arm/joint-flags.js`, tested with node); the model's limits only until the driver's status has arrived. Lab check 8.20.

### 2026-11-17 — Startup: the core's arrival did two big jobs at once, and the jump made megabytes of garbage a frame
**What:** quick job 23 (the core stutters as it loads in, about one start in three or four, lab check 1.3). On the builder's Mac, at full speed, 6 starts at 1920×1080 in headless Chrome: every frame 16.7 ms, nothing over 50 ms, **no stutter reproduced**. With Chrome's CPU slowdown at 4× (a stand-in for a slower computer) and full traces of 3 starts: as the core arrives, the code after the jump's pause runs as one task of 15–18 ms right before a 15–22 ms frame, so at least one frame is missed every start. About half of that task was the arrival sound making 2.6 s of fresh white noise (130,000 random numbers; ~1 ms at full speed, 10 ms the first time). Separately, every jump frame built 48 new arrays of line pieces (~144,000 numbers) plus 15,000 for the impact frame and threw them away: the heap swung between 2 and 20–30 MB and ~57 garbage collections ran between the jump and a second after the arrival, a major one (7–12 ms) at a different moment each start, sometimes right on the arrival (55 ms after it in one trace). That randomness fits "one start in three or four". Other long frames found, left alone: the start press itself (~85 ms at 4×, before anything moves), removing the start screen 2.05 s in (mid-jump, ~40 ms at 4×), the end of the title decode (~33 ms at 4×).
**Fix:** the noise is made once when the page loads and every whoosh plays a random place in it (looped); the jump keeps its line batches (typed arrays) from frame to frame. After, at 4× (4 clean traces): the arrival task 8–13 ms, ~25 small collections, the heap 2–5 MB; full speed unchanged. Not checked on the lab desktop yet (lab check 1.3). Headless Chrome's own frame times are useless for this: requestAnimationFrame ticks at 16.7 ms whatever happens, so measure with CPU slowdown and a trace.

### 2026-11-17 — Settings: CSS columns in a box of fixed height spill sideways, out of reach
**What:** quick job 21 ("the AI budget isn't in the hub's ⚙"). The settings page laid its cards out with `columns:` inside a box of fixed height. A tall "This device" card filled the visible columns and every later section went into extra columns off to the right, which nothing scrolls to: 4612 px of page in a 1526 px box at 1600×900, on `/settings` too. Seen only when "This device" grew (voice, wake word, monitors, the icon rows).
**Fix:** a grid that scrolls down. With the kit's `.card { min-height: 0 }` the grid's rows shrank and cards overlapped: `grid-auto-rows: max-content`.

### 2026-11-17 — Two Claude Code sessions in one checkout: the other one switched the branch
**What:** this session created a branch in `~/Code/lab-os`; another session working in the same folder switched it back to `main` before the commit, so the commit landed on local `main` (and `git push` of the branch said "up to date").
**Fix:** moved the commit to its branch and reset local `main` (nothing pushed). Two sessions at once each work in their own `git worktree`.

### 2026-11-17 — Green arms: LeLab's two "robots" were each the whole pair, and training never used LeLab
**What:** untangling the entry below. A LeLab robot entry (`~/.cache/huggingface/lerobot/robots/<name>.json`) holds both arms: both ports, a leader file, a follower file, one camera. Its two entries, `SO-101_Green_Follower` and `SO-101_Green_Leader`, were the same pair. LeLab names a calibration file after the name on its calibration page (by default the entry's), so `SO-101_Green_Leader.json` was the *follower's* calibration and `SO-101_Green_Follower.json` the *leader's*; the numbers showed each in the right arm's folder. The follower folder also held a `shepherd.json` with the leader's numbers, from `lerobot-calibrate --robot.type=so101_follower --robot.id=shepherd` (unused). The training (cube-to-box, 2026-11-05) was recorded from the command line with `--robot.id=sheep --teleop.id=shepherd` (shell history), not LeLab. On the command line, when the motors hold another calibration, LeRobot asks: ENTER writes the file back into the motors, `c` recalibrates and **overwrites** it.
**Fix:** the training files are the source of truth (`docs/plan/log.md`, 2026-11-17): lab-os drives with its copy in `calibration/` and refuses if it differs; LeLab gets one entry with its own copy (`scripts/green-lelab-from-training.sh`, which backs up and moves the old entries and files to `~/green-calibration-backup/`). At the command line's calibration question, press ENTER, never `c`.

### 2026-11-16 — Green arms: LeLab writes a calibration into the motors at every teleop start, and it has two setups
**What:** lab check part 8. `--watch` on `so101-green` worked with `calibration_file` set to `sheep.json`, then later refused: "motors hold a different calibration than its file". Cause, read from LeLab's code and saved setups (nothing written): LeLab's teleop writes the chosen setup's two calibration files into both arms' motors every time it starts. LeLab has **two saved setups for the same green pair**, and their names are crossed:

| LeLab setup | follower file (written to the follower) | leader file |
|---|---|---|
| `SO-101_Green_Follower` | `sheep.json` | `SO-101_Green_Follower.json` |
| `SO-101_Green_Leader` | `SO-101_Green_Leader.json` | `shepherd.json` |

`sheep` and `shepherd` are the builder's own calibrations from LeRobot's command line (the ones used for training, as far as the builder remembers); the two `SO-101_Green_…` files came from LeLab's calibration page. The two follower files differ by up to 43 motor steps (about 3°). So the motors hold whichever setup LeLab ran last, and a lab-os pinned to one file refuses after the other. Each setup also saves only one camera (one `wrist_cam`, the other `overhead_camera`, both camera number 2); adding cameras in LeLab is finicky (they don't always show up or save).
**Fix:** decided 2026-11-16: lab-os matches the motors. It uses whichever file in LeLab's follower folder equals what the motors hold, says which, and refuses only if none does (quick job 18, built 2026-11-17: it reads the motors' homing offsets and ranges, compares them as LeRobot does, and looks in the arm's own role folder first, then the other; the leader the same way; `calibration_file` is gone from `devices.yaml`). Still read-only. Lab check: part 8b. For training, the builder keeps to one LeLab setup, so recordings and the policy use the same calibration.

### 2026-11-16 — The training launcher started LeLab while the brain was driving the green arm
**What:** lab check 8.12: with `lab-os serve --arm so101-green` running, the "SO-101 Training (LeLab)" icon started LeLab instead of refusing. The brain then logged `so101-green: read failed (… Incorrect status packet!); using the last reading`: two programs on one port, which rule 4 forbids. The launcher skips its "is the port open elsewhere" check when LeLab's page already answers ("then it's LeLab's"), `green.check`.
**Fix (2026-11-17, quick job 17):** the launcher refuses whenever a program that isn't LeLab has a green port open, whether or not LeLab is running. LeLab is told apart by its command line (a part of it is a `lelab` folder or script: `~/.local/bin/lelab`, or LeLab's own Python in `~/.local/share/uv/tools/lelab/`), not by its page answering. Lab check: part 8b.

### 2026-11-16 — Brave: Esc still leaves full screen; in desktop control STOP can't be clicked
**What:** lab check 6.7 in Brave: Esc stopped the arm but also left full screen. Keeping Esc needs the browser's Keyboard Lock, which Chrome and Edge have and Brave doesn't. And in desktop control the pointer is captured, so the STOP button can't be clicked (8.10).
**Fix:** **X is STOP in every desktop-control mode** (already built) and leaves full screen alone. Quick job 19 shows that on the page. Use Chrome for the hub.

### 2026-11-16 — Green follower stayed stiff during `--watch`
**What:** lab check 8.8: the joints could only be moved a little by hand. `--watch` never switches the motors on or off, and LeLab had left them holding.
**Fix:** none in lab-os (it doesn't write to a borrowed arm in watch mode). Unplug and replug the arm's power to make it limp.

### 2026-11-16 — The closet router (Linksys WRK54G) is too old to be the lab router
**What:** a 2.4 GHz 802.11g router from about 2005: measured 1.46 Mbps down, 13.5 Mbps up, 7 ms. Its Wi-Fi tops out near 20 Mbps real, wired ports 100 Mbps, and it gets no security updates.
**Fix:** not for cameras, the Quest or the internet. It could carry small messages (a Raspbot reporting in) on its own, with nothing in its Internet port, as a stand-in until the real router.
**2026-11-17:** with a new cable to the wall, from the other desktop: 8.14 Mbps down, 10.9 Mbps up, 7 ms. Better, but a speed test only measures the internet through campus. For the lab network the limit is the router's own Wi-Fi: about 20 Mbps in real use, shared by every device. Enough for hub pages, chat, teleop messages from the Quest, the Raspbots and an occasional camera picture; not enough for several live camera videos at once. If it's used: a WPA2 password (if it only offers WEP, don't use it), and it's still a router on the wall port, the same question to IT. Plugging it into the wall is the same question to IT as any router.

### 2026-11-16 — An exited process still shows in `ps` on Linux until its parent collects it
**What:** Stop LeLab (quick job 7) checks that the LeLab it stops is gone by asking `ps` for its pid. In CI (Linux) the test's stand-in LeLab had exited but `ps` still listed it, `[lelab] <defunct>` with the same start time, because the test (its parent) hadn't collected it yet: a zombie. On the Mac the same test passed. Real LeLab's parent is its terminal, which collects it at once.
**Fix:** a process whose `ps` state has `Z` counts as stopped (`green.started_lelab`).

### 2026-11-16 — 1:1 teleop: the hand was measured from the wrong base on a headset without a floor
**What:** checking the 1:1 scale without the lab (quick job 13). The Quest page sends each hand's position minus the 3D arm's base. The hands are drawn under the scene's `root` exactly as WebXR gives them, but `armBase()` returned the base's *world* position. With a "local" reference space (no floor level) `root` is shifted down 1.4 m, so the brain would see the hand 1.4 m from the gripper and 1:1 could never be grabbed. With `local-floor` (the Quest's usual) the shift is 0, so it never showed. Not a scale error.
**Fix:** `armBase()` gives the base in `root`'s space, like the hands (`teleop/web/xr-scene.js`). The rest checked out, none of it a scale error: the SO-101 model's links are the real arm's (11.60 and 13.50 cm, as XLeRobot and robot_MCP measured), the gripper point is LeRobot's (`gripper_frame_link`), WebXR and the brain both use metres with no factor anywhere, the 3D arm is the URDF at real size, and a test moves the hand 6 cm and gets 6 cm. So a real 1:1 that feels off is the real arm (the elbow sag, the height offset) or the lag: lab checks 7.2–7.4.

### 2026-11-16 — LeRobot's Isaac Teleop example writes into LeRobot's cache
**What:** reading `examples/isaac_teleop_to_so101` (for `docs/dev/existing-work-teleop-ai.md`): on its first run it downloads the SO-101 URDF to `HF_LEROBOT_HOME/robot-urdfs/so101/`, and `override_reset_pose.py` saves poses to `HF_LEROBOT_HOME/reset_poses/`. By default that's `~/.cache/huggingface/lerobot/`, the folder holding the green arms' calibration (read-only for lab-os, CLAUDE.md). The leader-arm path reads the calibration from there too.
**Fix:** not used yet. If it's ever tried, run it with `HF_LEROBOT_HOME` set to a lab-os folder, and only on `so101-white`.

### 2026-11-16 — The guard hook also blocks cloning LeRobot from GitHub
**What:** `git clone https://github.com/huggingface/lerobot.git` in the same command as `mkdir` (or a `>` redirect) was denied: "The green arms' calibration in LeRobot's cache is read only". The hook matches the text `huggingface/lerobot`, which is in the GitHub URL as well as in the cache path.
**Fix:** none needed. Clone it in a command of its own, with no `mkdir` and no redirect (the clone itself is allowed).

### 2026-11-14 — The designed hub's question and answer can't simply be pinned over an open page
**What:** for the docked core on an open page (its reply beside it), the reply (`#reply`) lives inside `#hub`, which is scaled, faded to 12 % and blurred while a page is open (`body.folded #hub`). A `position: fixed` child of a transformed, filtered parent is placed and blurred with it, so it can't just be repositioned with CSS.
**Fix:** like the core itself, the element moves: into `#dock-say` (beside `#orb-dock`, outside `#hub`) when a page opens, back to its old place when it closes (both looks). It sits bottom right, left of the core: never over the page's bar with STOP (the "Open on…" rule above). It covers a corner of the page for the 14 s the answer shows.

### 2026-11-14 — openWakeWord's voice-activity filter makes a noisy room worse
**What:** for the sensitivity setting, openWakeWord 0.6's own options were tried on the recordings (its package, on the Mac). Its Silero VAD filter (`vad_threshold` 0.3 or 0.5) left a clear "hey Jarvis" alone, but with the voice at 30 % under loud noise it turned a 0.98 score into **0.00**: the filter looks at the audio 0.3–0.6 s back and decides there's no speech. Its Speex noise suppression needs `speexdsp_ns` (a Linux C package). Also measured: a quiet voice alone scores the same as a loud one (the recording at 1 % loudness: 0.999); what lowers the score is noise relative to the voice.
**Fix:** neither is used. The sensitivity slider sets openWakeWord's threshold and patience (`ai/wake.py` → `SENSITIVITY`); the browser's own noise suppression already runs on the microphone. `docs/guides/voice.md` → "Sensitivity".

### 2026-11-14 — The Quest's missed wake word: the page's sound can stop without telling anyone (likely cause, not yet seen in the lab)
**What:** looking for why the Quest sometimes misses "hey Jarvis" while push-to-talk always works (entry 2026-11-13): the page sends the microphone through its WebAudio recorder. If the browser suspends the page's sound (the headset sleeps when taken off, or the browser loses audio focus) or mutes the microphone track, the recorder stops and nothing reaches the brain; the microphone counted as "open", so nothing tried again. A push-to-talk press resumes the sound (`unlock()`), which is why push-to-talk always worked and the wake word worked again after it. Not reproduced on a real Quest (no headset here): that's the code's only path where the wake word goes deaf while push-to-talk works.
**Fix (2026-11-14):** while the wake word is on, the page checks every second: no audio for 1.5 s or the sound not running → resume it, else open the microphone again; while it can't, the dot turns orange and the brain logs `voice: quest's microphone: …`; the brain also logs gaps in the audio and near misses (a score over 0.25 but under the threshold). If the Quest still misses with audio flowing and no near misses logged, it's something else (lab checklist part 10). Other things found on the way: the old wake turns waited 0.25 s for other screens even with one, and a noisy room could keep the page's silence watch from ever ending the question (20 s), both fixed.

### 2026-11-14 — A hearing's WebSocket close could hang until the server went away
**What:** writing the warm-hearing tests, one test's teardown took 2 minutes: `GeminiHearing.close()` cancelled its reader task and closed the socket right away, and the close waited on the still-cancelling reader until the (fake) service shut down. A test on `main` already took 31 s in teardown for a similar reason (not chased further).
**Fix:** `close()` waits for its cancelled tasks first, then closes with a 3 s limit (`ai/speech.py`).

### 2026-11-14 — The AI budget wasn't read live, though the docs said so
**What:** `docs/dev/chat.md` said raising `ai_budget_usd_month` un-pauses the chat with no restart, and the Settings page said "applies when the brain restarts". The second was true: the brain read the number once at start (`SpendLog(budget_usd=…)`).
**Fix:** quick job 5: `SpendLog(budget_from=config.ai_budget)` re-reads `place.yaml` each time it checks (a broken file keeps the last good number); the Settings field says "applies from the next question". (`load_place()` wasn't used for it: it logs a warning per unknown field on every call, and `/api/spend` is polled.)

### 2026-11-14 — The "Open on…" menu covered the module page's STOP
**What:** the first version of "Open on…" (step 8) opened under its button at the top right, which is exactly where every module page (teleop, monitor, AI Control) keeps STOP. The page is an iframe, so nothing in the hub can sit under it: while the menu was open, the first tap on STOP landed on the menu. Seen in a headless screenshot, not in the lab.
**Fix:** the menu opens on the left (under Back / the title) in both looks, and a tap on the page closes it. Rule for anything the hub draws over an open module: never over the page's bar on the right.

### 2026-11-14 — Headless Chrome: background tabs slow their timers, and `/json/new` drops `#skip`
**What:** testing several hub pages as devices in one headless Chrome. (1) Pages opened as tabs (`/json/new`) are background tabs except the last; their `setTimeout`s run late, so the designed hub's 0.7 s module-close animation hadn't finished when the next step clicked, and the module looked stuck open. Real devices are each the front window of their own browser. (2) `PUT /json/new?http://…/design#skip`: the HTTP client treats `#skip` as the request's own fragment and never sends it, so the page started at its start screen.
**Fix:** open each page in a window of its own (the browser's DevTools socket, `Target.createTarget` with `newWindow: true`), and pass the address there (or escape `#` as `%23`). Also found that way: while closing, the designed hub still told the brain it showed the page; it says "nothing" from the moment Back is pressed now.

### 2026-11-13 — The Newline by HDMI is choppy at 1920×1080 though the desktop draws 60 fps (open)
**What:** the lab desktop on the Newline's HDMI (+ the touch cable), the Newline as its screen. `/perf` showed the desktop's numbers, a steady 60 fps, but the picture on the Newline was still very choppy. After lowering the desktop's resolution to **1600×900** (Ubuntu Settings → Displays) it was smooth. So the drawing isn't the problem; the lag is between the HDMI output and the Newline's panel at 1080p. Push-to-talk showed up (whose microphone, the desktop's USB one or the Newline's over the touch cable, isn't clear) and its transcription was poor. The wake word wasn't tried.
**Fix:** open. Workaround: 1600×900. To check next: the refresh rate Ubuntu picks at 1920×1080 (Displays: 60 Hz, or 30/50?), and the Newline's picture mode (a "game" or low-latency mode in its menu; manual in `docs/device_manuals/`).

### 2026-11-13 — The Newline's own Chrome: 44–59 fps on /perf, but the startup still lags, and no mic button
**What:** the Newline on an Ethernet cable from the lab desktop, its own Chrome at `http://<desktop>:8080`. `/perf`: average **43.8 fps** over 10 s, slowest frame 50 ms, canvas 2926×1646 (1463×823 at 2×, device pixel ratio 2.625), 108 dots, 3000 stars; **59 fps with 1000 stars**. The startup itself was still very laggy, so laggy that after the tap about half the animation never showed. The Newline's microphones work (Chrome's voice search understood well), but the hub showed **no mic button**: the page is `http://<ip>`, which isn't a secure page, so the browser hides the microphone (`docs/guides/voice.md` → secure pages). STOP from the Newline stopped the arm on the desktop.
**Fix:** open. The mic: Chrome's flag on the Newline (`chrome://flags` → "Insecure origins treated as secure" → `http://<desktop>:8080`). The lag: `/perf` is near fine with fewer stars, so the startup does more than `/perf` (focus step 12).

### 2026-11-13 — The Quest's wake word sometimes doesn't fire
**What:** in the headset, "hey jarvis" usually works but sometimes nothing happens; push-to-talk always works. On the lab desktop with a USB microphone both work, though sometimes only when spoken louder (the microphone isn't great).
**Fix:** open. Cause unknown (the Quest browser pausing the microphone, the level, or the detector's threshold).

### 2026-11-13 — "Don't ask again" for the arm's move tools lasted one session
**What:** during the cube pick the builder told Claude Code not to ask again for the move tools. The next session asked again: nothing was saved, and the `ask` list in `.claude/settings.json` wins over a saved "allow" anyway (in Claude Code, ask beats allow).
**Fix:** decided 2026-11-13 to stop asking; since 2026-11-14 every brain tool is on `allow` in the repo's `.claude/settings.json` and nothing on `ask` (quick job 1; a test keeps it that way).

### 2026-11-12 — AI cube pick on so101-white: the gripper closed right next to the cube (open)
**What:** Claude drove the real `so101-white` through the MCP tools: pictures from both cameras, `home`, then a blue ~2.5 cm cube on the table. 10 moves after `home` brought the open gripper down beside the cube without bumping it. It closed at a reported (28.2, 7.7, 1.0) cm, tool angle 174°, all the way (7.8 % open: nothing in the jaws). Both cameras then showed the cube still in place, just past the jaw tips. Three things showed up:
- **The height reading looks 1–2 cm too low.** At `rest`, before anything moved, the gripper point read **z = −0.9 cm**, i.e. under the table. If the offset holds, "z 1.0" at the grip was really ~2.5–3 cm: the jaws passed over the cube's top. In the wrist picture at 30 % open, the moving jaw was drawn in front of the cube's edge, which fits. `move_to` can't go lower than `min_z_cm` (1.0), so it couldn't go lower to try again. Not yet checked by eye or with a ruler.
- **The elbow stays ~3° more bent than commanded, nearly every move.** 10 of 13 moves said `stopped_short` with `elbow_flex` 2.3–3.5° short (once also `shoulder_lift` 2.7°), the same sign every time, including holding still at `home` (43.3° for 40°). Moves near the table (z < 4 cm) were 0.9 cm off with no joint listed. So the "still open" part of the 2026-11-10 entry below looks like a steady sag (load or a servo deadband), not a one-off. Side effect: since nearly every move says "Check before gripping or moving on", the warning stops meaning much. (2026-11-20, quick job 77: a joint within 4° now counts as arrived; `move_to` still checks the gripper point within 0.5 cm.)
- **Placing the cube from the overhead picture was ~8 cm off.** From `so101-white-cam-a` alone, Claude marked the cube at (24, 13) cm; the wrist camera put it at roughly (30.5, 8). The camera's position relative to the arm isn't known, so a picture gives a direction, not a place. The wrist camera got there by small steps (look, move 2 cm, look).

Also: straight down was refused at (24.6, 0.2, 9) cm with 180° and at (29.1, 8.2, 5) with 179°; 170° worked.
**Fix:** open. First check how high the jaw tips really are when the tools say z = 1 (ruler), and whether the cube sat beside the jaws or in line with them. Fix ideas are in `docs/plan/ideas.md` ("AI picking: height, sag and camera placement").

### 2026-11-12 — Which white-arm camera sees what
**What:** the `camera_snapshot` tool told the AI this wasn't written down. From the pick run: **`so101-white-cam-a`** is fixed above the table, behind the arm, looking forward over it (the arm comes in at the bottom right; the box and pliers are top right). **`so101-white-cam-b`** is on the wrist, looking along the jaws (both jaw tips at the bottom of the picture). The exposure settles slowly: cam-a gave three very dark pictures in a row while the arm moved under it, and cam-b one washed-out yellow-white picture, both fine again on the next snapshot.
**Fix:** written into the cameras' notes in `config/devices.yaml` and the tool's description, which also says to take another picture when one is too dark or too bright.

### 2026-11-12 — Asked to say each move first, the AI made most moves without a word
**What:** in the same run the builder asked: "tell me before each move what you'll do. One move at a time." Claude (Fable 5.2) said what it would do before only 3 or 4 of its 17 moves (gripper included), and in chat it didn't wait for a go-ahead between moves. Each move was still a separate, small tool call with a look in between, but the builder couldn't follow along or stop a move before it started. Bad for the 2026-11-19 demo, where people follow the arm through what the AI says.
**Fix:** open. When asked, the AI writes one line before every move ("Next: lower 1.5 cm, straight down, to just above the cube"). An idea for making the tools do it is in `docs/plan/ideas.md` (same entry as above).

### 2026-11-12 — Custom three.js shaders mix colors in linear light; the hub's canvas mixes in sRGB
**What:** the VR jump's star lines and sky (custom `ShaderMaterial`s) used the theme colors as `THREE.Color`s, which three converts to linear light, and the output was converted back to sRGB. A 15 % cyan tint (the hub's `rgba(primary, 0.15)` over black) came out as a strong teal fog, the flash as gray, and faint line tails much too bright: "mostly black and white" in the headset.
**Fix:** the shaders mix in sRGB numbers, like the hub's canvas (`srgb()` in `hub/web/xr/stars.js`), and hand three `pow(color, 2.2)` before its `colorspace_fragment`. Also: WebGL draws lines 1 pixel wide whatever `linewidth` says (and the Quest the same), so the stars are camera-facing quads with soft edges, not `LineSegments`.

### 2026-11-12 — OpenAI's speech WAV says it's 25 hours long
**What:** the first live try of the `main` voice setup (OpenAI `gpt-4o-mini-tts`, `response_format: wav`): a 2 s sentence measured 89,478 s. OpenAI streams the WAV, so its header carries the "unknown length" placeholder (0xFFFFFFFF). The spend log prices spoken seconds, so every answer would have been logged at ~$22, and the $20 budget would have paused the chat after the first one. Browsers play such a file fine, so it doesn't show by ear.
**Fix:** the brain rewrites OpenAI's WAV with a correct header, and `wav_seconds` counts the bytes really there (`ai/speech.py`; a test with the placeholder header). Found before any OpenAI turn was logged.

### 2026-11-12 — openWakeWord's package doesn't install on Linux with Python 3.12
**What:** `openwakeword` 0.6.0 requires `tflite-runtime` on Linux (`platform_system == "Linux"`), which has no Python 3.12 build, and it pulls in scipy and scikit-learn. lab-os is Python 3.12 on the lab desktop.
**Fix:** lab-os runs openWakeWord's ONNX models itself with `onnxruntime` (`src/lab_os/ai/wake.py`, ~100 lines, the same streaming steps). Checked against the package (on the Mac, where it installs): the same scores on the same recordings (0.961 / 0.999 / 0.999 for "hey Jarvis", 0.000 for other speech). The models are in `models/openwakeword/` (non-commercial license).

### 2026-11-12 — Gemini's free key: 3 speech requests a minute per TTS model
**What:** making test recordings, the 3rd `gemini-3.8-flash-lite-tts` request within a minute got HTTP 429, "Generate content requests per minute limit exceeded on Free Tier", `quotaValue: 3`, `retryDelay: 53s`. A spoken answer uses 2 requests and the greeting 1, so the demo would go silent after about one question a minute. The limit is per model. **There's a daily one too: 10 requests a day per model** (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, hit the same day while testing; `retryDelay` ~15 h, until midnight Pacific).
**Fix:** `speak:` in `models.yaml` lists four TTS models that work on the free key (`gemini-3.8-flash-lite-tts`, `gemini-3.8-flash-tts`, `gemini-3.1-flash-tts-preview`, `gemini-2.5-flash-preview-tts`: 2.7–4.2 s a sentence, same voices); one over its limit rests for its `retryDelay` and the next speaks (`speak_any` in `ai/speech.py`). `gemini-2.5-pro-preview-tts` had no free quota. A paid key (or OpenAI's) doesn't have this.

### 2026-11-12 — Gemini: hearing through a normal model takes ~10 s; its Live transcription model ~0.4 s
**What:** sending 4 s of speech to `gemini-3.5-flash-lite` (`generateContent` with the audio inline, "transcribe this") took 7–10 s for the words, far over voice's 2–3 s budget. `gemini-3.1-flash-lite` and `gemini-3.8-flash` were overloaded (503) on the free key, `gemini-omni-1.2-flash` over quota (429). Gemini's OpenAI-compatible address has no `/audio/transcriptions` (404).
**Fix:** `gemini-3.5-transcribe-live`, a transcription model on the Live API (a WebSocket, `bidiGenerateContent`; the key goes in the `x-goog-api-key` header): the words arrive while the audio streams in, and the final words ~0.4 s after the audio ends. Each pause ends a segment with its own final text, and the next segment starts fresh, so the brain joins them (`ai/speech.py`). Also: `gemini-3.8-flash-lite-tts` answers with a whole WAV (`audio/wav`), not raw samples; the code wraps raw ones only when the type says so.

### 2026-11-12 — Headless Chrome's fake microphone was silent on macOS
**What:** for a browser check of voice, Chrome ran with `--use-fake-device-for-media-stream --use-file-for-fake-audio-capture=<question.wav>`. The page got the microphone, but every sample was 0 (also with a plain `getUserMedia({audio: true})`), so the brain "didn't catch that". Without the file, the fake device's beep came through.
**Fix:** add `--disable-features=AudioServiceOutOfProcess,AudioServiceSandbox` (the audio service then runs inside the browser and can read the file). A 48 kHz WAV, with a second of silence before the speech. Then the whole push-to-talk turn worked headless with the real Gemini key.

### 2026-11-12 — The old guard hook blocked even *reading about* the calibration
**What:** building step 11, every shell command whose text contained `huggingface/lerobot/calibration` was denied, even a `python3 script.py` heredoc that only edited lab-os's own source files, and so were commands that merely mentioned a green serial number. The rule was "never touch the calibration", and a text match can't tell reading from writing.
**Fix:** since step 11 the hook (`.claude/hooks/guard.sh`, tests in `tests/test_guard_hook.py`) allows reads (`ls`, `cat`, `jq`, `diff`, `sha256sum`) under `~/.cache/huggingface/lerobot` and denies anything that could write, move or delete there (`rm`, `mv`, `cp`, `>`, `tee`, `sed -i`, `python`, `lerobot-*`, …); the green serials aren't blocked any more. Still a text match: `jq '.x > 1' <file there>` is denied too (the `>`). Edits with the editor tools aren't checked by the hook; `.claude/settings.json` denies `Edit(…/.cache/huggingface/lerobot/**)` for those.

### 2026-11-11 — The two training cameras share one serial number
**What:** (first seen 2026-10-28: Innomaker U20CAM-1080p, USB ID `0c45:6366`, which `lsusb` calls "Microdia Webcam Vitade AF"; each shows up as two `/dev/video*` entries; the white arm's two are the same model.) `ls -l /dev/v4l/by-id/` (it lists names, opens nothing) shows only `usb-Innomaker_Innomaker-U20CAM-1080p-S1_SN0001-video-index0/1` for **two** plugged-in Innomaker cameras: both report the serial `SN0001`, so the second one has no by-id link. `/dev/v4l/by-path/` shows both: sockets `usb-0:7` and `usb-0:8`. Cheap cameras often carry a placeholder serial like this.
**Fix:** tell identical cameras apart by socket (`by-path`), never by serial or index (until 2026-11-12 the whole camera model was blocked instead; since step 11 the training cameras are `borrowed`, by socket, and refused while another program has them open). The white cameras (same model) will need fixed sockets, e.g. on their own small USB hub (the powered hub on the shopping list, `docs/plan/log.md` → "Facts about the lab").

### 2026-11-11 — `/classic/teleop` threw an error since the speed control
**What:** `teleop-page.js` (shared by `/teleop` and `/classic/teleop`) set up the speed slider without checking it's there; the classic page has none, so the script stopped at that line ("Cannot set properties of null") and everything after it in that script didn't run there. Found by a headless Chrome check of every page.
**Fix:** the slider code skips a page without it.

### 2026-11-10 — `/teleop` on the Pi: no Full screen button
**What:** on `pi01`'s Chromium the hub went full screen, but the `/teleop` page opened on its own didn't, and it showed no Full screen button. The module pages only draw that button when the browser says full screen is available (`document.fullscreenEnabled` in `web/design/kit.js`), so the Pi's Chromium most likely said no there (not checked).
**Fix (2026-11-11):** every page now has the full-screen button from one helper (`web/fullscreen.js`); where full screen isn't possible it stays and says why (tooltip, and a note when pressed) instead of hiding. Meanwhile F11 on the Pi. Still to find out *why* the Pi said no: open `/teleop` there and press the button (or hover it); the reason it gives is the answer.

### 2026-11-10 — raspbot1 Wi-Fi: IWU-AI-LAB refuses it (open), its "Raspbot" hotspot works again
**What:** raspbot1 (a Raspberry Pi 5, hostname `yahboom`, kernel 6.6.31, Wi-Fi firmware 7.45.234 from 2021, NetworkManager 1.42.4) can't join IWU-AI-LAB, and for a while its own hotspot refused phones too. Found on the way:
- IWU-AI-LAB is "Enhanced Open" (OWE). The Pi's Wi-Fi driver (brcmfmac) can't do OWE, so a profile saved as OWE never connects.
- An earlier "make it open and connect" never ran: `sudo -v && nohup sudo … &` puts the sudo password prompt in the background, so the job just stopped and waited.
- The real tries (open profile, also pinned to the open access point D8:B3:70:6C:B9:CC, also with the "minimal" firmware 7.45.241) all ended `ASSOC-REJECT status_code=16 bssid=00:…`. The driver's debug log shows the firmware itself saying no within ~50 ms; no 802.11 reason code. IT says both MACs are registered. `pi01` (also a Pi 5) joins fine with newer software: kernel 6.18.34, firmware 7.45.265 (2023), NetworkManager 1.52.1.
- Hotspot: phones "asked for the password again" and the Pi logged no join attempt at all. That was after the hotspot had been restarted many times in one boot (OWE try, radio off/on, test hotspots). It works now (wpa-psk, rsn, ccmp, pmf off, band bg, channel 6, shared 192.168.1.11/24; a phone and the desktop joined, also after a reboot). Unknown whether the profile change or the reboot fixed it.
- Not the cause (they show up when things work too): dnsmasq's "chown of PID file failed", and brcmfmac's "vndr ie set error -52" / "set chanspec fail" on every hotspot start.
- Reloading the brcmfmac driver twice in quick succession hung the Wi-Fi chip ("dongle is not responding: err=-84"). Only a reboot fixed it.
- raspbot1's logs look 13 h ahead of the desktop: its time zone is Asia/Shanghai (UTC+8). The clock is right.

**Fix:** for OWE networks on a Pi, save the profile plain open: `sudo nmcli con modify IWU-AI-LAB remove 802-11-wireless-security` (worked on `pi01`). Run sudo commands in the foreground (or in one `sudo bash -c '…'`), never behind `&`. raspbot1 on IWU-AI-LAB: open. Suspected cause is its old software; untested next step `sudo apt install firmware-brcm80211` (offered 1:20240709-2~bpo12+1+rpt4, may not contain 7.45.265). Its IWU-AI-LAB profile is open with autoconnect off; debug log `~/iwu-debug-2026-11-10.log` and profile backups `~/Raspbot-working-2026-11-10.nmconnection`, `~/IWU-AI-LAB-2026-11-10.nmconnection` are on the Pi. Left as they were: the Raspbot profile's gateway 192.168.1.0 (bogus, adds a dead default route), and the old Yahboom / Yahboom3 Wi-Fi profiles outrank Raspbot (priority 4 and 6 vs 2). Reaching it by cable: `docs/guides/network-setup-checklist.md` → Step 2.

### 2026-11-10 — The Pi's browser "kept loading" the hub: it was waiting for a password
**What:** on `pi01`, `http://192.168.7.72:8080/monitor` kept loading. The brain saw the Pi connect but never send a request: Chromium on Raspberry Pi OS was waiting behind a password prompt (most likely "Unlock login keyring", asked when Chromium first starts). The Pi also didn't reach the desktop by its name (`ai-comp-lab-ubuntu-76358.iwu.ai.lab`); the IP address works.
**Fix:** answer the prompt (the Pi user's password). For a screen that starts the hub by itself, start Chromium with `--password-store=basic` (or give the keyring an empty password), so nothing waits for a person.

### Seen once, 2026-11-10: one test failed in a full run on `main`, then 9 runs passed
**What:** `uv run pytest` once ended "1 failed, 341 passed" right after PR #29 was merged (the lab brain was running with `--host 0.0.0.0` at the same time); the failing test's name wasn't captured, and it never came back. Probably a timing-dependent test. If it shows up again, note its name here.

### 2026-11-10 — `move_to` said "arrived" 1.6 cm short of the target (real so101-white)
**What:** blind cube test (cube "10 cm in front"), the AI driving the real `so101-white` through the MCP tools. Close to the base, straight-down picks are out of reach (refused down to ~16 cm at 180°); the nearest the IK offered was (10.9, 0, 2.1) cm at 172°. Asked for (11, 0, 2.1), the arm reported "arrived" at (12.6, 0.1, 2.5) at 166°: elbow and wrist short of the command, the arm folded near its limits. The gripper closed 2.7 cm past where the cube would be, and the blind AI couldn't tell.
**Fix (2026-11-11, not yet tried on the real arm):** moves now read the motors after arriving and say `stopped_short` with how far (`off_by_cm`, `joints_short_deg`, a sentence) instead of "arrived" (`docs/guides/ai-control.md`). Found on the way, a likely cause: when an AI move reached its last waypoint, the next tick froze the arm, and the SO-101's freeze writes "hold where the motors are **now**". A joint still trailing its command (load, near a limit) was locked short there. Now the move keeps sending its target for 0.5 s before the freeze. Also: while driving, the SO-101 driver's `read_joints` returns where it *told* the motors to go, so "arrived" never saw the miss; the check uses `read_measured`. Still open: whether the rest of the miss is load, a servo deadband or the arm touching itself. Cameras (focus step 3) let the AI see it. **2026-11-12:** the elbow came up ~3° short on nearly every move of the cube pick (entry above), so it looks steady, not a one-off.

### 2026-11-10 — LeLab saves raw ttyACM names, and the white arm was its "leader"
**What:** the training project's LeLab keeps its ports as `/dev/ttyACM0` (leader) and `/dev/ttyACM1` (follower). With only `so101-white` plugged in, the white arm was `ttyACM0`: LeLab started then would have treated it as the green leader. The numbers follow the plug-in order.
**Fix:** the training launcher (`lab-os green`, `docs/guides/green-launcher.md`) refuses unless exactly the two green arms are plugged in, LeLab's ports are those two, and they're the same way round as the last good start.

### 2026-11-10 — Quest teleop: the SO-101 stretched out its elbow and went into the table
**What:** after a while of Quest teleop, `so101-white`'s elbow straightened and the arm hit the table. Reproduced offline (a wandering hand through `ClutchMapper` + the SO-101 model): with the hand 2 m forward, shoulder_lift 89°, elbow −75° (straight is −90°), the gripper 8.6 cm *below* the table. Nothing knew where the table was, and relative control lets the arm wander as the hand re-grabs. Also, each joint's speed was limited on its own, so at low speed the joints arrived at different times and the gripper didn't move along the hand's line ("doesn't follow exactly").
**Fix:** the IK mapping keeps the gripper and wrist `floor_m` (1 cm) above the base's bottom (the table) and slips there like a joint limit; a step that would dip goes as far as it can; all joints slow down together. (A rule keeping the elbow 15° from straight was tried and dropped the same day: the builder found it got in the way of some movements.) Tuning: `docs/guides/quest-setup.md` → "Tuning". Still possible: the real arm sags when stretched out flat near the table; raise `floor_m` if it touches.

### 2026-11-10 — The Newline doesn't look like 60 Hz from a laptop (open)
**What:** the laptop says the Newline runs at 60 Hz, but motion looks no smoother. Several ways tried by the builder; not solved yet. Likely suspects, cheapest first: the browser's energy saver (Chrome/Edge/Brave cap pages at 30 frames a second on battery: plug in, or turn it off under Settings → Performance / System); a 4K signal (60 Hz at 4K needs HDMI 2.0 at both ends and a "Premium High Speed" cable, and 4× the pixels for a laptop's graphics to draw: set the laptop to 1920×1080 at 60 Hz and let the Newline scale it); the Newline's HDMI/EDID version setting (1.4 vs 2.0) on its input menu, where the model has one; its USB-C input instead of HDMI, if both ends carry video over USB-C. Measure with `/perf` (frames the browser actually draws) on the Newline.
**Later the same day:** still stuck at a low rate from the laptop, though it says 60 Hz. And the hub in the Newline's own Chrome (through `pi01`) is laggy too, even at `?quality=reduced`: probably its browser on its phone-class chip. The builder now questions the Newline as the hub's screen; `/perf` numbers on it would settle how much it can carry. The builder also connected a lab desktop by HDMI (maybe DisplayPort): just as laggy as the laptop (a Mac). So it's the Newline itself (its input or how it scales the picture), not the computer behind it, and another computer on its HDMI isn't expected to help.

### 2026-11-10 — Editing `.env` does nothing until the brain restarts
**What:** the hub's core stayed red and the brain kept trying OpenAI ("OpenAI refused the API key") although `OPENAI_API_KEY` was already commented out in `.env`: the brain had started before that edit, with a placeholder key still in `.env`. `.env` is read once, at start. The core also said "No answer" for this standing problem, and the ⏻ button couldn't clear it (the page copies the brain's state every 3 s).
**Fix:** restart the brain after editing `.env`. The designed hub now says "AI not connected" with the brain's sentence for a standing problem; "No answer" is only for a question that failed.

### 2026-11-10 — Hyperspace stutters in Firefox on Linux, smooth in Brave and VS Code
**What:** the jump draws 3000 stars as up to ~36,000 short lines per frame on a 2D canvas. Chromium (Brave, VS Code) draws canvases on the graphics card; Firefox on Linux often doesn't (`about:support` → "Canvas backend"). Headless Chromium without a GPU: 3000 stars ≈ 30 fps, 1500 ≈ 41, none ≈ 60.
**Fix:** the jump measures its own frame rate: under ~40 fps it drops a fifth of the stars at a time (not below ~1000) and keeps that for the next jump; `reduced` detail starts with half. If Firefox is still choppy, use Brave or Chrome on that screen, or check `about:support` for hardware acceleration.

### 2026-11-10 — A second `lab-os serve` took the first one's AI-tools port, and the whole brain quit
**What:** with one brain already running (`lab-os serve --persona jarvis`, port 8080 + MCP 8081), a second one on `--port 8090` died at start: its MCP server couldn't bind 8081, and uvicorn calls `sys.exit()` when it can't bind, which ended the whole program with a long traceback.
**Fix:** the brain now catches that, logs "AI tools (MCP) are off: port 8081 is in use …" and runs on without them (`/api/ai-calls` says `mcp: null`). A taken hub port now stops with one sentence instead of a traceback. Two brains on one computer: give the second `--port` and `--mcp-port`.

### 2026-11-10 — The side view bent when the arm turned
**What:** AI Control's side view measured each joint's distance from the URDF base origin, but the SO-101's pan axis sits 3.9 cm in front of it (and the arm 1.8 cm to the side), so at `shoulder_pan` 60° the drawing shrank by up to 2 cm.
**Fix:** distances are measured along the arm's facing direction from the pan axis (`side_view_cm` in `hub/server.py`); a test turns the arm and checks the shape stays.

### 2026-11-10 — Gemini's free model takes 6–15 s per answer
**What:** with the `backup` setup (`gemini-3.5-flash-lite`, free key) a two-word answer took ~6 s, and a question that needs a look-up (`project_status`) ~13 s: ~7 s to decide on the tool, ~6 s to answer. A check after 9 s looked like a hang.
**Fix:** none needed in code (the page says "Looking up the current focus…" meanwhile). Expect it when demoing on the free key; the paid OpenAI `main` setup is usually faster. Test scripts wait 20 s+ for an answer.

### 2026-11-10 — Steps "built and tested" still counted as not done
**What:** the Current Project panel said "Step 1 of 10" although steps 4–6 were finished: the panel only counts a step as done when its line in `docs/plan/current-focus.md` says `(done YYYY-MM-DD)` right after the bold title; the status lines underneath don't count.
**Fix:** marked 4–6 `(done 2026-11-10)`. When a step is finished, add the `(done …)` mark (step 1 waits for its Newline check).

### 2026-11-10 — The live status line floods a narrow terminal
**What:** `lab-os serve` printed teleop's status line (`right: no controller | FROZEN | arm +0.0 -20.0 …`) 10 times a second, redrawn with `\r`. In a narrow terminal (VS Code's panel) the line wraps, and `\r` only goes back to the start of the last wrapped row, so every redraw added new lines: a constant stream.
**Fix:** `lab-os serve` doesn't print it unless `--status-line` (the hub shows the state). When it's on (also `lab-os-teleop`), it's cut to the terminal's width, drawn only when it changes, and never written when the output isn't a terminal.

### 2026-11-10 — The key went into the place template's `.env`, so the chat had no key
**What:** the hub's chat said it wasn't connected although a Gemini key had been saved. The key was in `src/lab_os/place_template/.env`: the template folder has a `.env.example` that said "Copy to .env (in this folder)", so it was copied right there. The lab's place reads the `.env` in the repo's **top folder**; nothing said that file was missing. Worse, `lab-os new-place` copied everything in the template, so the real key would have been copied into every new place folder.
**Fix:** the key file moved to the repo's top folder. `new-place` never copies a `.env` (only `.env.example`); the brain logs a warning naming the `.env` it looked for when there's none, and the chat's "isn't set up" sentence names the full path. The template's `.env.example` now says to copy it in the new place's folder, not in lab-os's template.

### 2026-11-09 — Gemini refuses a tool round without its thought signature
**What:** through Gemini's OpenAI-compatible address, the first request with tools worked (the model asked for `project_status`), but sending the tool's result back failed with HTTP 400 "Function call is missing a thought_signature in functionCall parts". Gemini attaches `"extra_content": {"google": {"thought_signature": "…"}}` to each streamed tool call (and no `index`), and wants it back on the assistant message's `tool_calls`. OpenAI sends no such field. Google's thought-signature page only covers its own Interactions API.
**Fix:** the client keeps any `extra_content` of a tool call as is (`ToolCall.extra`) and the chat sends it back (`ai/chat.py`). A test's fake service sends one like Gemini.

### 2026-11-09 — Gemini's free key: gemini-3.8-flash overloaded, flash-lite answers
**What:** with the builder's free Gemini key, `gemini-3.8-flash` answered HTTP 503 "This model is currently experiencing high demand", then on retry sent nothing for 30 s. Listing the models (the brain's connection check) worked, so the status said "connected" while answers failed. `gemini-3.5-flash-lite` answered at once through the same OpenAI-compatible address, with token counts.
**Fix:** `backup` uses `gemini-3.5-flash-lite`. A 5xx now shows "… is busy or having trouble right now". The connection check only proves the address and key, not that the model has capacity.

### 2026-11-09 — OpenAI's gpt-6-luna: tools on Chat Completions only with `reasoning_effort: none`
**What:** per OpenAI's model page, `gpt-6-luna` supports function calling on Chat Completions only when `reasoning_effort` is `none` (the Responses API has no such limit). It also defaults to `medium` reasoning, which is slower and bills reasoning tokens as output. Gemini's OpenAI-compatible address wants `max_tokens`, OpenAI's newer models `max_completion_tokens`.
**Fix:** each setup in `config/models.yaml` carries its own `options` (sent as they are): `main` has `reasoning_effort: none` + `max_completion_tokens`, `backup` has `max_tokens`.

### 2026-11-09 — llama.cpp's server and the hub both default to port 8080
**What:** `llama-server` (the `local` setup's alternative to Ollama) listens on 8080 by default, which is `lab-os serve`'s hub port; whichever starts second fails.
**Fix:** start llama.cpp with `--port 8082` and use `http://127.0.0.1:8082/v1` in `models.yaml` (Ollama's 11434 doesn't clash).

### 2026-11-09 — A test that drives the CLI with a real arm's name can reach the real driver
**What:** a new test switched to a home config folder, then called `cli.main(["serve", "--arm", "so101-white"])` expecting "not at this place". But `serve` without `--config` switches back to the repo's `config/` (the lab), where `so101-white` is active, so it built the real `SO101Arm` and tried its port. On the Mac the port wasn't there (LookupError); on the lab desktop with the arm plugged in it would have opened it.
**Fix:** CLI tests pass `--config` explicitly, and tests that name a real arm replace the drivers (`SO101Arm`, `XArm`) with one that fails the test if it's ever made (`tests/test_config.py`).

### 2026-11-09 — `mcp` 2.x: FastMCP is now MCPServer, and plain exceptions lose their message
**What:** `uv add mcp` installed 2.3.0, where `mcp.server.fastmcp.FastMCP` (in most examples online) is gone: it's `mcp.server.mcpserver.MCPServer`. A tool that raises an ordinary exception reaches the AI only as "Error executing tool …", without the reason. Also, its `run_streamable_http_async()` starts uvicorn, which takes over Ctrl+C.
**Fix:** pinned `mcp>=2.3,<3`. Refusals are raised as `mcp.server.mcpserver.exceptions.ToolError("Refused: …")`, which keeps the text. The brain runs uvicorn itself with signal capture switched off (`tools/mcp_server.py`), so Ctrl+C still stops the whole brain.

### 2026-11-09 — Near full stretch, 1 cm of gripper motion needs ~20° of joint motion
**What:** On the SO-101, moving the gripper straight forward toward full reach, the IK's joint change per 1 cm grows from ~5° to ~18° (the arm is nearly straight). Moving between waypoints that far apart in joint space bends the gripper's path off the straight line, and a simple "big jump = flip" guard at 15° refused reachable points.
**Fix:** `move_to` splits any 1 cm step needing more than 5° into smaller IK-solved steps; only more than 30° per cm counts as a flip and is refused (`tools/robot.py`).

### 2026-11-09 — Ctrl+C tests: background jobs from a script ignore SIGINT
**What:** A server started with `&` from a non-interactive shell (as Claude's tool calls are) inherits SIGINT as *ignored*, so `kill -INT` does nothing and Ctrl+C handling looks broken.
**Fix:** test Ctrl+C from a launcher that resets the signal (`subprocess.Popen(..., preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL))`), or in a real terminal.

### 2026-11-09 — New devices can't join the lab Wi-Fi quickly
**What:** only campus IT can add a device (by MAC address) to the lab Wi-Fi. The Raspbots were sent in about two weeks ago and still aren't on (IT tried; it didn't work, cause unknown). Planning had assumed the Newline could just join it.
**Fix:** plan around it: only devices already on it (the desktops, the Pis) use it; the Newline reaches the brain by cable, through a Pi, or by a phone hotspot until the lab router exists (`docs/guides/network-setup-checklist.md` → "Networks before the router").

### 2026-11-09 — Headless Chrome refuses full screen and pointer lock
**What:** In headless Chrome (`--headless=new`), `requestFullscreen()` and `requestPointerLock()` are refused even after a real (DevTools-sent) click. So the hub's tap 1 takes its "can't go full screen" path (straight to tap 2), and teleop's Desktop control never starts. Not a bug in the pages: the standalone `/teleop` page behaves the same.
**Fix:** for headless checks, fake both APIs before the page loads (DevTools `Page.addScriptToEvaluateOnNewDocument`: define `document.fullscreenElement` / `pointerLockElement` getters, patch `Element.prototype.requestFullscreen` / `requestPointerLock` to set them and fire `fullscreenchange` / `pointerlockchange`; patch the prototype, because `document.documentElement` doesn't exist yet when the script runs). The real two-tap check happens on the Newline. (Seen again 2026-11-10 with the designed hub, which logs `hub: no full screen` and starts anyway.)

### 2026-11-09 — `gh pr edit` fails on this repo
**What:** `gh pr edit <n>` (GitHub CLI 2.45, Ubuntu's package) stops with `GraphQL: Projects (classic) is being deprecated … (repository.pullRequest.projectCards)`: this old `gh` still asks GitHub for the retired "classic projects" field. Nothing is changed. Checked on PR #3.
**Fix:** use the REST API through `gh api`:
```bash
gh api -X PATCH repos/IWU-AI-Lab/lab-os/pulls/<n> -f body="..."      # or -f title="..."
gh api -X PUT repos/IWU-AI-Lab/lab-os/pulls/<n>/merge -f merge_method=merge
```
(`gh pr create`, `gh pr view --json …` work.) A newer `gh` (GitHub's own apt repository) likely fixes it.

### 2026-10-29 — wrist_roll turns the opposite way on the SO-101 and the xArm
**What:** The "shared convention" (`robots/xarm.py`) says +wrist_roll is counter-clockwise from above. The SO-101 URDF does the opposite: with the gripper pointing up, +wrist_roll is **clockwise** from above (checked two ways with forward kinematics). Other joints agree (+pan = the arm's right; +lift/elbow/wrist_flex tilt forward/down). Also: the SO-101's zero pose is an "L" (upper arm up, forearm and gripper forward), not upright like the xArm, and a gripper pointing straight down sits at the ±180° wrap of a plain `atan2` tilt angle.
**Fix:** each arm's kinematics carries `roll_sign` (xArm −1, SO-101 +1), used by the IK teleop instead of one global setting; the SO-101's tool angle runs −90…270 so "pointing down" (180) never wraps. Whether LeRobot's degrees match the URDF's signs is **not yet checked on the real arm**.

### 2026-10-29 — LeRobot's motor setup and calibrate do more than they say
**What (read in LeRobot 0.6.1's source, not seen on hardware):** (1) `setup_motor` looks for "the" motor with a broadcast ping and silently takes the *first* answer, so with two motors plugged in it can renumber the wrong one. (2) `lerobot-calibrate` first calls `connect()`, which writes PID/torque settings and **switches torque on** (motors hold, or jump to a stale goal) before `calibrate()` switches it off again. (3) `wrist_roll` isn't range-measured: it gets the full 0..4095 (±180°).
**Fix:** `lab_os.robots.so101_setup` scans all baud rates first and refuses unless exactly one STS3215 answers; it then verifies the new ID. Its `calibrate` only opens the bus and calls `calibrate()` (torque never on), and closes with torque off. Wrist roll limits come from the SO-101 driver's soft limits, not the calibration.

### 2026-10-29 — LeRobot is ~5 GB, and a plain `uv sync` uninstalls it
**What:** `lerobot[feetech]` 0.6.1 pulls in 61 packages, mostly PyTorch 2.11 with CUDA 13: `.venv` went from 51 MB to 4.9 GB (NVIDIA libraries 2.7 GB, torch 1.1 GB, triton 0.6 GB; LeRobot itself 7 MB). Importing LeRobot's SO-101 classes takes ~3 s and loads torch. It's the optional extra `so101`, so CI and other machines skip it. But `uv sync` makes the environment match *exactly* what was asked, so a plain `uv sync` on the lab desktop **removes** LeRobot and torch again (`uv run` doesn't remove anything).
**Fix:** on machines that drive an SO-101: `uv sync --extra so101` (or `./scripts/install.sh --so101`). Commands that need it say so: `uv run --extra so101 …`.

### 2026-10-29 — The snap `uv` can't run inside Claude Code's shell
**What:** `/snap/bin/uv` (first on PATH) fails in Claude's sandbox with "snap-confine is packaged without necessary permissions". `~/.local/bin/uv` (the installer's copy) works. Same family as the sudo gotcha below (the "no new privileges" flag).
**Fix:** Claude calls `~/.local/bin/uv`. In a normal terminal either works.

### 2026-10-29 — so101-white's board looks almost like green's
**What:** The white follower's controller board is the same chip (`1a86:55d3`, "USB Single Serial") with serial `5B41532410` (until 2026-10-30 it was `5B41532183`, now the spare/leader board: the two white boards are easy to swap by accident, and lab-os then refuses the port until devices.yaml is updated); green's are `…1599` and `…3501`. All start with `5B4153`.
**Rule:** always compare the last digits; use the full `/dev/serial/by-id/` path from `config/devices.yaml`. Green and its cameras were unplugged by the builder (who also owns the green project) for the white setup.

### 2026-10-29 — xArm: the shoulder→elbow servo cable snapped during hand calibration
**What:** While the builder moved the joints to their ends by hand (servos limp) for `calibrate`, the cable from the shoulder servo to the elbow servo snapped (a spare was available). Joints pushed to their extremes stretch or twist the servo cables; the calibration also came out at (or past) the full servo range for base, elbow and wrist roll. Earlier teleop had driven base and wrist roll to ±116°.
**Fix:** calibrate only to where the cables are still slack, not the mechanical end; for teleop, keep base, shoulder, elbow and wrist roll well inside the measured range (edit `calibration/xarm1/limits.yaml`). Check cable routing before long sessions.

### 2026-10-29 — Quest IK: wrist roll was mirrored
**What:** On the Quest (software xArm), rolling the controller clockwise rolled the gripper counter-clockwise. +wrist_roll is counter-clockwise *seen from the gripper tip*; the operator looks along the gripper from behind, the opposite way.
**Fix:** `MappingConfig.ik_roll_sign = -1` for IK mode (`test_rolling_the_hand_counter_clockwise_rolls_the_gripper_the_same_way_as_seen`). Joint-space mode (SO-101 fake) still uses `signs["wrist_roll"]`; check it when the SO-101 is driven.

### 2026-10-29 — Quest 3 over USB without developer mode: only Quest Link, no adb
**What:** `adb devices` listed nothing. The desktop sees the Quest 3 (`2833:5010`), but its USB interfaces are only Quest Link ones ("XRSP", "Crosswind", "Highwind"); an adb interface (class ff, subclass 42) appears only once developer mode / USB debugging is really on. The headset setting "USB connection for apps" doesn't add it. Developer mode can only be switched on from the phone that owns the headset's Meta account, which the builder doesn't have; the Quest also can't join the university network (IT).
**Fix (done 2026-10-29):** any phone signed into the headset's Meta account can switch developer mode on: the builder installed the Meta Horizon app, signed in as the lab account (adding their own phone number, removable later), turned developer mode on, and `adb devices` then listed the headset. Other options that were considered: the account owner enables developer mode once (then the USB route works with no code), or one Quest is factory-reset onto the lab's own account (professor's call), or a private network (phone hotspot / travel router) with the laptop as brain and a guarded LAN mode. Check from Linux without opening anything: `ls /sys/bus/usb/devices/*/` for idVendor 2833 and its interfaces' `bInterfaceSubClass`.

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
**Fix:** One folder per session, via **git worktrees** (several folders on the same repo, each on its own branch). Coding: `lab-os/`. Planning: `lab-os-planning/` on branch `planning`. See `docs/dev/dev-setup.md` → "Branches and folders".

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
**(Gone since step 11, 2026-11-12: the hook doesn't look for the green serials any more.)**
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
**Fix:** "AI lab admin" becomes the lab's one Meta account, verified with the professor's phone number (decision 2026-10-28 in `docs/plan/log.md`).

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
**Fix:** On the Quest, use `adb reverse tcp:8080 tcp:8080` over USB and open `http://localhost:8080` (docs/guides/quest-setup.md). Re-run `adb reverse` after every re-plug. (Since 2026-11-20, quick job 73: `lab-os serve` runs it by itself when the Quest connects.)

### 2026-10-24 — Never open so101-green's serial ports
**What:** The lab desktop has so101-green's leader + follower plugged in. Both show up as CH343 adapters (`1a86:55d3`, "USB Single Serial"), exactly what so101-white will look like.
**Why it matters:** so101-green is the training project's arm (the builder's own, separate from lab-os). Opening its port (even to read) can disturb their session.
**Rule:** Never open these:
- `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41531599-if00`
- `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41533501-if00`

They're `off_limits` in `config/devices.yaml`; `lab_os.devices` refuses them, and a Claude Code hook blocks commands that name them. The arm may be unplugged at times; that doesn't change the rule.
**Since 2026-11-12 (step 11):** loosened by the builder. lab-os may open them, but never while another program (LeLab, a run) has them open; they're `borrowed`, not `off_limits` (CLAUDE.md, "Hard rules").

### 2026-10-24 — ttyACM0/ttyACM1 swap
**What:** `/dev/ttyACM0` and `/dev/ttyACM1` are numbered in plug-in order, so they can swap after a reboot or re-plug.
**Fix:** Refer to arms only by `/dev/serial/by-id/…` (stable, includes the adapter's serial number). Find them with `ls -l /dev/serial/by-id/`. `lab_os.devices` rejects raw `ttyACM`/`ttyUSB` paths.

### 2026-10-24 — The `lerobot` conda env is shared
**What:** `~/miniforge3/envs/lerobot` (+ the editable `~/lerobot` checkout) is so101-green's training setup.
**Fix:** lab-os uses its own uv environment (`.venv/`). LeRobot for so101-white gets added to lab-os with `uv add`, never installed into the conda env. `pyproject.toml` sets uv to use only uv-managed Pythons so conda's interpreter is never picked up.

### 2026-10-24 — Sudo doesn't work inside Claude Code sessions
**What:** Claude's shell runs with the "no new privileges" flag, so `sudo` fails.
**Fix:** Run `sudo` commands yourself in a normal terminal; Claude gives the exact command.
