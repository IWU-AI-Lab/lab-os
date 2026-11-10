# The hub

The brain's start page: a start screen, then a status strip, module buttons (teleop, monitor), the assistant, and panels of real project facts. It comes in two looks:
- **plain** (`/plain`, and `/` by default): simple on purpose, the same parts and names as the approved concept without its looks;
- **designed** (`/design`): the approved concept (`docs/design/hub-concept.html`) made real, the reveal (`current-focus.md` step 10), previewed since 2026-11-10. Below: "The designed hub".

`hub.look` in `config/theme.yaml` (`plain` or `design`) picks which one `/` shows; flip it when the design should be what everyone sees.

## Start it
```bash
uv run lab-os serve                    # hub + teleop pages + the fake arm
```
Then open **http://localhost:8080/** in a browser on the same computer. In VS Code: Run and Debug → "Hub: lab-os serve (fake arm)".

| Address | What |
|---|---|
| `/` | the hub, in the look `hub.look` picks (add `#skip` to jump past the start screen, for a quick look) |
| `/design`, `/plain` | each look by name, whatever `hub.look` says |
| `/teleop` | the teleop page (the Quest opens this one under `lab-os serve`; `lab-os-teleop` still serves it at `/`) |
| `/monitor` | the arm monitor |
| `/perf` | the performance test (below) |

Options are the same as `lab-os-teleop`'s: `--arm fake-xarm1`, `--venue visit-day`, `--port 8090`, `--config <folder>` (another place: `docs/places.md`); plus `--mcp-port` for the robot tools for AI (`docs/ai-control.md`), `--persona` (`docs/personas.md`), and `--status-line` to print teleop's live status line under the log (off by default for `lab-os serve`: the hub shows the state; `lab-os-teleop` still prints it unless `--quiet`). Real arms (`--arm so101-white`, `--arm xarm1`) need the builder's OK before anything moves (SAFETY.md).

## Two taps
Browsers allow full screen and sound only after a press, so:
1. **Tap 1, full screen** ("Tap for full screen"): the builder's tap when leaving the hub on a screen. Skipped when the page is already full screen (kiosk mode, F11, an installed app) or the browser can't do it.
2. **Tap 2, start** ("Tap, click or press any key to start"): the visitor's tap. Opens the hub.

Leaving full screen (a swipe, holding Esc, a reload) brings back the start screen with tap 1. Modules open **inside** the hub (no page load, which would leave full screen); **Back** or **Esc** returns. In Chrome and Edge, Esc means Back without leaving full screen (Keyboard Lock API; holding Esc still leaves). In teleop's desktop control, the first Esc leaves desktop control and the next one is Back.

**Back to the start screen** after `hub.reset_after_s` (theme, 180 s; a venue profile can set its own `reset_after_s`) with no input on the hub or the open module. It stays full screen, so the next person only needs tap 2. It also clears the conversation. Never while something is in use: while any teleop page (the hub's or the Quest's) has the arm, an AI tool moves it, or a chat answer is streaming.

**The chat:** type anywhere on the hub (it lands in "Ask anything" under the circle) and press Enter; **History** opens the whole conversation. Keys, AI setups and the budget: `docs/chat.md`.

## The designed hub (`/design`)
The concept's look, motion and sound on the brain's real facts: the title is the place's name, the strip shows the venue, persona, internet and AI setup, the panels show the current focus (with its steps), AI spend, commits (with the latest few) and the devices from `devices.yaml`, the typed log at the bottom shows the latest commits and the current step, the **Arm** button opens a side view drawn from the arm's real joints, and the chat is the real one (answers stream in under the core; **History** is the conversation). The startup is real too: the checks (theme, sound, display, internet, AI, assistant, arm) say what just happened, and the greeting is the brain's.
- **One tap** starts it: full screen + the unlock + the startup (about 8 s; any input skips). Unlike the plain hub, leaving full screen doesn't bring back the start screen.
- **Back to the start screen** after `hub.reset_after_s` with nobody there (never while something is in use), with a fresh conversation (the last one: "Bring back").
- **Sleep:** after `motion.idle.sleep_after_s` (300 s) it dims to the network and the breathing core; any input wakes it. With the default reset time (180 s) the reset comes first, so sleep shows only where a venue sets a longer `reset_after_s`.
- **In the address:** `?quality=maximal` (adds the far-layer verses; `full` is the theme's default, `reduced`, `minimal`), `?startup=assemble` (instead of `hyperspace`), `?sound=0`, `?full=0` (don't go full screen, for a laptop), `#skip`. E.g. `http://localhost:8080/design?quality=maximal`.
- **Not real yet, so not shown:** whether a device is switched on (the roll call needs the lab router: the Power column says "not known"), voice, alerts (no real alert source yet), a module sent to another screen. The teleop and monitor pages inside it keep their own plain look for now.
- **The code:** one file, `src/lab_os/hub/web/design.html`: the concept's CSS, SVG and JavaScript, with the made-up data replaced by the brain's endpoints and the concept controls removed. Fonts are bundled in `src/lab_os/web/vendor/fonts/` (offline).

## Full screen without anyone tapping (kiosk-style)
A page can go full screen only from a press (browsers' rule, on `http://` too). To skip even that, open the browser already full screen:
- **A Linux or Windows desktop (Chrome/Chromium):** an app window, full screen, that closes like any window:
  ```bash
  google-chrome --app=http://localhost:8080/design --start-fullscreen
  ```
  (`chromium` instead of `google-chrome` on a Pi; another screen uses the brain's address instead of `localhost`). `--kiosk` instead of `--start-fullscreen` also hides the way out (Alt+F4 still closes it); keep it for screens nobody needs for anything else.
- **The Newline (Android):** Chrome's menu → **Add to Home screen** gives an icon; on plain `http://` it opens as a normal tab (an installed full-screen app needs the secure address), so tap once for full screen. Test what the Newline allows: `ideas.md` → "Screens without browser bars".

## Other screens (the Newline, a hallway desktop)
`lab-os serve` listens on this computer only. Ways to show the hub on another screen:
- **The screen is this computer's display** (HDMI + USB touch): open `http://localhost:8080/`. Everything works.
- **Over the network:** `uv run lab-os serve --host 0.0.0.0` and open `http://<this computer's IP address>:8080/` (or `/design`) on the screen. Find the address with `hostname -I` (Linux; the first one) or `ipconfig getifaddr en0` (macOS). The screen must be able to reach this computer: some networks block devices from reaching each other (`network-setup-checklist.md` → "Networks before the router").
  - **With a real arm** (`--arm so101-white`): other screens are **view-only**. They show the hub, the arm and the monitor, and their **STOP works**, but teleop input from them is ignored ("view only: the arm is driven from the brain's computer"). Driving stays with this computer: its own browser, the AI tools (MCP, this computer only), and the Quest over `adb reverse` (it arrives as this computer).
  - **Not a secure page** (`http://` + an address): Esc leaves full screen (no Keyboard Lock), the screen may sleep (no Wake Lock), and Copy and voice don't work. Full screen itself works. The secure address (`current-focus.md` → "Step 7, concretely") is deferred (decision 2026-11-10); its fallbacks (Chrome's flag, `adb reverse`) apply here too.

## Performance test (`/perf`)
Drifting dots linked when close, and star streaks speeding up from the middle, drawn the same way as the concept's network and hyperspace, in plain gray. It shows frames per second (last second, average over 10 s, slowest frame) and the canvas size. Settings (what to draw, dots per million pixels, stars, resolution) are in the address, e.g. `/perf?draw=net&density=90&stars=3000&res=2`, so each screen can be bookmarked. Run it full screen on each screen for a minute and note the average: 55–60 fps can carry `full` quality; lower ones `reduced` or `minimal` (DESIGN.md → "Quality levels").

## Where the code is
- `src/lab_os/cli.py`: `lab-os serve`.
- `src/lab_os/hub/`: `server.py` (pages, `/api/…` endpoints, the module list, the assistant's state, the look), `project.py` (the Steps list), `commits.py` (`git log`: per day, the latest few), `internet.py` (background check).
- `src/lab_os/hub/web/`: `index.html`, `hub.js`, `hub.css` (the plain hub), `design.html` (the designed hub, one file), `perf.html`, `perf.js`.
- `src/lab_os/web/`: files every page shares (vendored libraries, `theme.js`).
- Endpoints: `docs/protocol.md` → "HTTP endpoints".
