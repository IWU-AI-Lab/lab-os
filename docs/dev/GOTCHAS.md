# Gotchas

Every on-the-ground surprise and its fix. Newest first. (Network/device-setup gotchas also live at the bottom of `docs/guides/network-setup-checklist.md`.)

---

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
- **The elbow stays ~3° more bent than commanded, nearly every move.** 10 of 13 moves said `stopped_short` with `elbow_flex` 2.3–3.5° short (once also `shoulder_lift` 2.7°), the same sign every time, including holding still at `home` (43.3° for 40°). Moves near the table (z < 4 cm) were 0.9 cm off with no joint listed. So the "still open" part of the 2026-11-10 entry below looks like a steady sag (load or a servo deadband), not a one-off. Side effect: since nearly every move says "Check before gripping or moving on", the warning stops meaning much.
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
**Fix:** tell identical cameras apart by socket (`by-path`), never by serial or index (until 2026-11-12 the whole camera model was blocked instead; since step 11 the training cameras are `borrowed`, by socket, and refused while another program has them open). The white cameras (same model) will need fixed sockets, e.g. on their own small USB hub (the powered hub on the shopping list, `docs/plan/lab-jarvis-log.md` → "Facts about the lab").

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
**Fix:** "AI lab admin" becomes the lab's one Meta account, verified with the professor's phone number (decision 2026-10-28 in `docs/plan/lab-jarvis-log.md`).

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
**Fix:** On the Quest, use `adb reverse tcp:8080 tcp:8080` over USB and open `http://localhost:8080` (docs/guides/quest-setup.md). Re-run `adb reverse` after every re-plug.

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
