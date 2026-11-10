# Gotchas

Every on-the-ground surprise and its fix. Newest first. (Network/device-setup gotchas also live at the bottom of `network-setup-checklist.md`.)

---

### 2026-11-10 — `move_to` said "arrived" 1.6 cm short of the target (real so101-white)
**What:** blind cube test (cube "10 cm in front"), the AI driving the real `so101-white` through the MCP tools. Close to the base, straight-down picks are out of reach (refused down to ~16 cm at 180°); the nearest the IK offered was (10.9, 0, 2.1) cm at 172°. Asked for (11, 0, 2.1), the arm reported "arrived" at (12.6, 0.1, 2.5) at 166°: elbow and wrist short of the command, the arm folded near its limits. The gripper closed 2.7 cm past where the cube would be, and the blind AI couldn't tell.
**Fix:** open. "Arrived" should compare the end position with the target and say "stopped short by X cm"; find out if it's load, a servo deadband, or the arm touching itself. Cameras (focus step 3) let the AI see the miss.

### 2026-11-10 — LeLab saves raw ttyACM names, and the white arm was its "leader"
**What:** the training project's LeLab keeps its ports as `/dev/ttyACM0` (leader) and `/dev/ttyACM1` (follower). With only `so101-white` plugged in, the white arm was `ttyACM0`: LeLab started then would have treated it as the green leader. The numbers follow the plug-in order.
**Fix:** the training launcher (`lab-os green`, `docs/green-launcher.md`) refuses unless exactly the two green arms are plugged in, LeLab's ports are those two, and they're the same way round as the last good start.

### 2026-11-10 — Quest teleop: the SO-101 stretched out its elbow and went into the table
**What:** after a while of Quest teleop, `so101-white`'s elbow straightened and the arm hit the table. Reproduced offline (a wandering hand through `ClutchMapper` + the SO-101 model): with the hand 2 m forward, shoulder_lift 89°, elbow −75° (straight is −90°), the gripper 8.6 cm *below* the table. Nothing knew where the table was, and relative control lets the arm wander as the hand re-grabs. Also, each joint's speed was limited on its own, so at low speed the joints arrived at different times and the gripper didn't move along the hand's line ("doesn't follow exactly").
**Fix:** the IK mapping keeps the gripper and wrist `floor_m` (1 cm) above the base's bottom (the table) and slips there like a joint limit; a step that would dip goes as far as it can; all joints slow down together. (A rule keeping the elbow 15° from straight was tried and dropped the same day: the builder found it got in the way of some movements.) Tuning: `docs/quest-setup.md` → "Tuning". Still possible: the real arm sags when stretched out flat near the table; raise `floor_m` if it touches.

### 2026-11-10 — The Newline doesn't look like 60 Hz from a laptop (open)
**What:** the laptop says the Newline runs at 60 Hz, but motion looks no smoother. Several ways tried by the builder; not solved yet. Likely suspects, cheapest first: the browser's energy saver (Chrome/Edge/Brave cap pages at 30 frames a second on battery: plug in, or turn it off under Settings → Performance / System); a 4K signal (60 Hz at 4K needs HDMI 2.0 at both ends and a "Premium High Speed" cable, and 4× the pixels for a laptop's graphics to draw: set the laptop to 1920×1080 at 60 Hz and let the Newline scale it); the Newline's HDMI/EDID version setting (1.4 vs 2.0) on its input menu, where the model has one; its USB-C input instead of HDMI, if both ends carry video over USB-C. Measure with `/perf` (frames the browser actually draws) on the Newline.

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
**What:** the Current Project panel said "Step 1 of 10" although steps 4–6 were finished: the panel only counts a step as done when its line in `current-focus.md` says `(done YYYY-MM-DD)` right after the bold title; the status lines underneath don't count.
**Fix:** marked 4–6 `(done 2026-11-10)`. When a step is finished, add the `(done …)` mark (step 1 waits for its Newline check).

### 2026-11-10 — Headless Chrome refuses full screen from scripted clicks
**What:** testing the hub with headless Chrome over the DevTools protocol, `requestFullscreen()` after a dispatched click fails with "not granted"; a real press on a real screen works.
**Fix:** none; it's only the test setup. The hub logs it (`hub: no full screen`) and starts anyway.

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
**Fix:** plan around it: only devices already on it (the desktops, the Pis) use it; the Newline reaches the brain by cable, through a Pi, or by a phone hotspot until the lab router exists (`network-setup-checklist.md` → "Networks before the router").

### 2026-11-09 — Headless Chrome refuses full screen and pointer lock
**What:** In headless Chrome (`--headless=new`), `requestFullscreen()` and `requestPointerLock()` are refused even after a real (DevTools-sent) click. So the hub's tap 1 takes its "can't go full screen" path (straight to tap 2), and teleop's Desktop control never starts. Not a bug in the pages: the standalone `/teleop` page behaves the same.
**Fix:** for headless checks, fake both APIs before the page loads (DevTools `Page.addScriptToEvaluateOnNewDocument`: define `document.fullscreenElement` / `pointerLockElement` getters, patch `Element.prototype.requestFullscreen` / `requestPointerLock` to set them and fire `fullscreenchange` / `pointerlockchange`; patch the prototype, because `document.documentElement` doesn't exist yet when the script runs). The real two-tap check happens on the Newline.

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
