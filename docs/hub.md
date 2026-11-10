# The hub

The brain's start page: a start screen, then a status strip, module buttons (teleop, monitor), the assistant, and panels of real project facts. Plain on purpose until the reveal (`current-focus.md` step 10): it has the same parts and names as the approved concept (`docs/design/hub-concept.html`), without the concept's looks.

## Start it
```bash
uv run lab-os serve                    # hub + teleop pages + the fake arm
```
Then open **http://localhost:8080/** in a browser on the same computer. In VS Code: Run and Debug → "Hub: lab-os serve (fake arm)".

| Address | What |
|---|---|
| `/` | the hub (add `#skip` to jump past the start screen, for a quick look) |
| `/teleop` | the teleop page (the Quest opens this one under `lab-os serve`; `lab-os-teleop` still serves it at `/`) |
| `/monitor` | the arm monitor |
| `/perf` | the performance test (below) |

Options are the same as `lab-os-teleop`'s: `--arm fake-xarm1`, `--venue visit-day`, `--port 8090`, `--quiet`, `--config <folder>` (another place: `docs/places.md`); plus `--mcp-port` for the robot tools for AI (`docs/ai-control.md`). Real arms (`--arm so101-white`, `--arm xarm1`) need the builder's OK before anything moves (SAFETY.md).

## Two taps
Browsers allow full screen and sound only after a press, so:
1. **Tap 1, full screen** ("Tap for full screen"): the builder's tap when leaving the hub on a screen. Skipped when the page is already full screen (kiosk mode, F11, an installed app) or the browser can't do it.
2. **Tap 2, start** ("Tap, click or press any key to start"): the visitor's tap. Opens the hub.

Leaving full screen (a swipe, holding Esc, a reload) brings back the start screen with tap 1. Modules open **inside** the hub (no page load, which would leave full screen); **Back** or **Esc** returns. In Chrome and Edge, Esc means Back without leaving full screen (Keyboard Lock API; holding Esc still leaves). In teleop's desktop control, the first Esc leaves desktop control and the next one is Back.

**Back to the start screen** after `hub.reset_after_s` (theme, 180 s; a venue profile can set its own `reset_after_s`) with no input on the hub or the open module. It stays full screen, so the next person only needs tap 2. It also clears the conversation. Never while something is in use: while any teleop page (the hub's or the Quest's) has the arm, an AI tool moves it, or a chat answer is streaming.

**The chat:** type anywhere on the hub (it lands in "Ask anything" under the circle) and press Enter; **History** opens the whole conversation. Keys, AI setups and the budget: `docs/chat.md`.

## Other screens (the Newline, a hallway desktop)
`lab-os serve` listens on this computer only. Ways to show the hub on another screen:
- **The screen is this computer's display** (HDMI + USB touch): open `http://localhost:8080/`. Everything works.
- **Over the network:** `uv run lab-os serve --host 0.0.0.0` (fake arm only; real arms refuse it) and open `http://<this computer's IP address>:8080/` on the screen. Not a secure page, so the Keyboard Lock doesn't work there: Esc leaves full screen, and the start screen then asks for tap 1 again. The real fix is the secure address in `current-focus.md` → "Step 7, concretely"; until then, its fallbacks (Chrome's flag, `adb reverse`) apply here too.

## Performance test (`/perf`)
Drifting dots linked when close, and star streaks speeding up from the middle, drawn the same way as the concept's network and hyperspace, in plain gray. It shows frames per second (last second, average over 10 s, slowest frame) and the canvas size. Settings (what to draw, dots per million pixels, stars, resolution) are in the address, e.g. `/perf?draw=net&density=90&stars=3000&res=2`, so each screen can be bookmarked. Run it full screen on each screen for a minute and note the average: 55–60 fps can carry `full` quality; lower ones `reduced` or `minimal` (DESIGN.md → "Quality levels").

## Where the code is
- `src/lab_os/cli.py`: `lab-os serve`.
- `src/lab_os/hub/`: `server.py` (pages, `/api/…` endpoints, the module list, the assistant's state), `project.py` (the Steps list), `commits.py` (`git log`), `internet.py` (background check).
- `src/lab_os/hub/web/`: `index.html`, `hub.js`, `hub.css` (the hub), `perf.html`, `perf.js`.
- `src/lab_os/web/`: files every page shares (vendored libraries, `theme.js`).
- Endpoints: `docs/protocol.md` → "HTTP endpoints".
