# The hub

The brain's start page: a start screen, then a status strip, module buttons (teleop, monitor), the assistant, and panels of real project facts. It comes in two looks:
- **plain** (`/plain`, and `/` by default): simple on purpose, the same parts and names as the approved concept without its looks;
- **designed** (`/design`): the approved concept (`docs/design/hub-concept.html`) made real (`docs/plan/current-focus.md` step 10), since 2026-11-10; the one demoed (the plain hub stays the default at `/`). Below: "The designed hub".

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
| `/ai` | AI Control: what an AI tool is doing with the arm (below) |
| `/settings` | the settings (also the gear in the hub's strip) |
| `/xr` | the hub in VR/AR for the Quest: the designed hub's startup around you (ignition, hyperspace jump, the core assembling, the checks, the title and greeting), then the hub around you: the core, the four callouts (with their controls and details pages), the strip with ⏻, the typed log, the frame; point with a controller or hand and pull the trigger (or pinch) to press, B or Y closes a page, ⏻ goes back to the start (and the jump). Module buttons for the modules with a VR version (Teleop: the arm scene without leaving VR, it drives like `/teleop`; Monitor and AI Control: a watch-only arm hologram with STOP; Training has none). **Asking:** hold the trigger (or a pinch) on the ask line under the core and talk; the wake word listens on the headset's microphone while the hub is up; a question asked on another screen shows here too (`docs/guides/voice.md` → "In VR"). "Preview on this screen" elsewhere (drag to look around, click to press). `?slow=10` plays it ten times slower. The designed hub's strip shows a headset button where VR works |
| `/training` | start the SO-101 training setup (green arms + LeLab) after a port check, on the brain's computer (`docs/guides/green-launcher.md`) |
| `/classic/teleop`, `/classic/monitor` | the plain teleop and monitor pages from before the design, kept in case the new ones break |
| `/teleop` | the teleop page (the Quest opens this one under `lab-os serve`; `lab-os-teleop` still serves it at `/`) |
| `/monitor` | the arm monitor |
| `/perf` | the performance test (below) |

Options are the same as `lab-os-teleop`'s: `--arm fake-xarm1`, `--venue visit-day`, `--port 8090`, `--config <folder>` (another place: `docs/dev/places.md`); plus `--mcp-port` for the robot tools for AI (`docs/guides/ai-control.md`), `--persona` (`docs/dev/personas.md`), and `--status-line` to print teleop's live status line under the log (off by default for `lab-os serve`: the hub shows the state; `lab-os-teleop` still prints it unless `--quiet`). Real arms (`--arm so101-white`, `--arm xarm1`) need the builder's OK before anything moves (SAFETY.md). With a real arm and `--host 0.0.0.0`, other computers only watch (and STOP); `--drive-from pi01.iwu.ai.lab` (repeatable) lets that computer drive too.

## Two taps
Browsers allow full screen and sound only after a press, so:
1. **Tap 1, full screen** ("Tap for full screen"): the builder's tap when leaving the hub on a screen. Skipped when the page is already full screen (kiosk mode, F11, an installed app) or the browser can't do it.
2. **Tap 2, start** ("Tap, click or press any key to start"): the visitor's tap. Opens the hub.

**The Full screen button** (since 2026-11-11): on every page (both hubs' status strips, next to ⏻ and ⚙ on the designed one; the bar of each module page; the classic pages; `/perf`), shown only while the page isn't full screen. It does what tap 1 does. Where the browser can't or won't go full screen, the button stays and **says why** when pressed (also in its tooltip): no Fullscreen API, turned off by the browser (`document.fullscreenEnabled` false, e.g. a kiosk or managed policy), blocked by a permissions policy, or refused with the browser's own words. Then use the browser's own full screen (F11; Ctrl+Cmd+F on a Mac). One helper does it for every page: `src/lab_os/web/fullscreen.js`.

Leaving full screen (a swipe, holding Esc, a reload) brings back the start screen with tap 1. Modules open **inside** the hub (no page load, which would leave full screen); **Back** or **Esc** returns. In Chrome and Edge, Esc means Back without leaving full screen (Keyboard Lock API; holding Esc still leaves). In teleop's desktop control, the first Esc leaves desktop control and the next one is Back.

**Back to the start screen** after `hub.reset_after_s` (theme, 30 minutes since 2026-11-10, was 3; a venue profile can set its own `reset_after_s`; both timers are in the settings, ⚙ → The hub) with no input on the hub or the open module. It stays full screen, so the next person only needs tap 2. It also clears the conversation. Never while something is in use: while any teleop page (the hub's or the Quest's) has the arm, an AI tool moves it, a chat answer is streaming, or a voice turn runs (from the mic press until the last spoken word).

**The chat:** type anywhere on the hub (it lands in "Ask anything" under the circle) and press Enter; **History** opens the whole conversation. Keys, AI setups and the budget: `docs/dev/chat.md`. **Voice:** hold the mic button next to it (or Space) and talk; the answer is spoken. Or dictation, chosen per screen (⚙ → This screen → Talking to it): tap the mic and the words go into the ask line (`docs/guides/voice.md`). The mic shows only on a secure page with a microphone.

## The designed hub (`/design`)
The concept's look, motion and sound on the brain's real facts: the title is the place's name, the strip shows the venue, persona, internet and AI setup, the panels show the current focus (with its steps), AI spend, commits (with the latest few) and the devices from `devices.yaml`, the typed log at the bottom shows the latest commits and the current step, the **Arm** button opens a side view drawn from the arm's real joints, and the chat is the real one (answers stream in under the core; **History** is the conversation). The startup is real too: the checks (theme, sound, display, internet, AI, assistant, arm) say what just happened, and the greeting is the brain's.
- **One tap** starts it: full screen + the unlock + the startup (about 8 s; any input skips). Unlike the plain hub, leaving full screen doesn't bring back the start screen.
- **The strip's quiet tools** (top right, after the clock): **⏻** goes back to the start screen now (a fresh conversation for the next person; the last one can be brought back), **⚙** opens the settings.
- **Answers type themselves out** at a steady ~125 characters a second (the AI streams in chunks; the page paces them), faster only when it falls far behind. `minimal` quality shows each chunk at once.
- **Bring back the last conversation:** the small amber ↶ in the ask line (hover: how many questions, when), and a line at the top of **History**.
- **Back to the start screen** after `hub.reset_after_s` with nobody there (never while something is in use), with a fresh conversation (the last one: "Bring back").
- **Sleep:** after `motion.idle.sleep_after_s` (15 minutes) it dims to the network and the breathing core; any input wakes it. Then the reset (30 minutes). Sleep shows only when it's shorter than the reset time.
- **Esc = Back keeps full screen** in Chrome and Edge (Keyboard Lock). In Firefox (and Chromium browsers without the lock) the browser also leaves full screen; the next tap or key then quietly goes full screen again (a page may only do that from a press). Leaving on purpose (F11, Esc with nothing open) stays left. Kiosk mode (`firefox --kiosk <url>`, `brave-browser --kiosk <url>`) keeps it full screen whatever Esc does.
- **A slow screen** (e.g. Firefox on Linux, which often draws the canvas without the graphics card): the hyperspace jump drops stars until it runs at ~40 frames a second (not below ~1000); `reduced` detail starts with half of the theme's `stars`.
- **In the address:** `?quality=maximal` (adds the far-layer verses; `full` is the theme's default, `reduced`, `minimal`), `?startup=assemble` (instead of `hyperspace`), `?sound=0`, `?full=0` (don't go full screen, for a laptop), `?res=0.5` (the drawing resolution, below), `#skip`. E.g. `http://localhost:8080/design?quality=maximal`.
- **Drawing resolution** (since 2026-11-11, for slow screens like the Newline): how many pixels the moving pictures are drawn at before the screen scales them up. `auto` (the default) = the screen's own, up to 2× (a 4K panel at 2× = 3840×2160 pixels every frame); `1` = one per CSS pixel (a quarter of that on such a screen); `0.75`; `0.5` (a sixteenth: soft, but very light). Applies to the network and hyperspace, the effects layer, the arm drawings in modules, and the 3D arm in teleop/monitor and AI Control's side view. Set it per screen in ⚙ → This screen (kept in that screen's browser), or in the address: `?res=` wins (also for the pages opened inside the hub). Same scale as `/perf?res=`, so a number that runs smoothly there is the one to pick. Text, the core and the frame are not affected (they're not canvases). The console says `hub: drawing at 1× (1920×1080 for 1920×1080)`.
- **Not real yet, so not shown:** whether a device is switched on (the roll call needs the lab router: the Power column says "not known"), alerts (no real alert source yet), a module sent to another screen. The teleop and monitor pages inside it keep their own plain look for now.
- **The code:** one file, `src/lab_os/hub/web/design.html`: the concept's CSS, SVG and JavaScript, with the made-up data replaced by the brain's endpoints and the concept controls removed. Fonts are bundled in `src/lab_os/web/vendor/fonts/` (offline).

## The module pages (teleop, monitor, AI Control)
Since 2026-11-10 they're in the hub's design too (`src/lab_os/web/design/`: `kit.css`, `kit.js`, `icons.svg`, shared by every module page). Inside the hub they drop their own frame and title; on their own screen they have both, the place's name, the clock and a **Full screen** button.
- **Teleop** (`/teleop`): the arm in 3D on the left; on the right how to drive it (the Quest's Enter AR/VR, Desktop control and its keys) and what the page sends. Status (brain, control, arm) and **STOP** in the bar, always visible.
- **Monitor** (`/monitor`): for an onlooker screen: the arm in 3D, a gauge per joint, STOP. It watches; it never drives.
- **AI Control** (`/ai`, the third button): what an AI tool (Claude Code + Fable, Codex, …) does with the arm, live: the arm seen from its side with its real geometry (from the arm's kinematics, in cm), where the last `move_to` aimed, every robot-tool call as it happens (ok / clipped / refused / stopped / error, with what came back), whether the tools are on and moves allowed, and STOP. Until the first call it says how to connect Claude Code. It never moves anything.
- **The old pages** stay at `/classic/teleop` and `/classic/monitor` (same scripts, the old look), in case the new ones break somewhere (e.g. the Quest's browser).

## Settings (the ⚙, or `/settings`)
- **The hub, the assistant, this place, robots in this venue:** values from `theme.yaml`, `place.yaml` and the running venue's file, saved the moment they change, **into those files, with their comments kept**. Each one says when it applies: at once (the hub re-reads the theme), from the next question, or after a restart (the safety ones). They're ordinary config changes: in the lab they show up in `git diff config/`; commit them like any edit, or undo with `git checkout config/<file>`.
- **Only on the brain's computer:** other screens see the settings but can't change them (a hallway screen shouldn't rename the lab or switch robots on).
- **This screen:** level of detail, drawing resolution, sound, full screen on the start press. Kept in this screen's browser only, so the Newline can run `full` while a Pi runs `minimal`.
- **Growing with new modules:** the page draws whatever `src/lab_os/settings.py` lists. A setting is one `Field` (file, path, label, kind: choice / bool / number / text / color / list); a new module adds its own section with `settings.register(Section(...))`. No page changes needed.

## Other monitors on the brain's computer (HDMI / DisplayPort)
Monitors plugged into the brain's computer are just more screens of the same browser, so any page can go there:
- **From the hub:** open the module (Teleop, Monitor, AI Control, …) and press **Show on another screen** next to Back. In Chrome on that computer the page opens on the other monitor (Chrome asks once to allow "window management"; it needs `localhost`, which the brain's own screen is); click it there for full screen. The hub closes its copy. Without that permission, or in another browser, it opens a window to drag over. Settings → This screen → "Monitors on this computer" grants the permission ahead of time and lists them.
- **By hand:** open `http://localhost:8080/monitor` in a new window, drag it to the monitor, press F11 (or the page's Full screen button). Or from a terminal, an app window at that monitor's position (here a second 1920-wide monitor to the right):
  ```bash
  google-chrome --new-window --app=http://localhost:8080/monitor --window-position=1920,0 --start-fullscreen
  ```
- Any page works this way: `/monitor`, `/ai`, `/teleop`, `/design` (a second hub), `/settings`.
- **The Newline on an HDMI cable + its USB touch cable** to the brain's computer is the same thing: one more monitor (with touch), and it's `localhost`, so even voice will work there.

## Full screen without anyone tapping (kiosk-style)
A page can go full screen only from a press (browsers' rule, on `http://` too). To skip even that, open the browser already full screen:
- **A Linux or Windows desktop (Chrome/Chromium):** an app window, full screen, that closes like any window:
  ```bash
  google-chrome --app=http://localhost:8080/design --start-fullscreen
  ```
  (`chromium` instead of `google-chrome` on a Pi; another screen uses the brain's address instead of `localhost`). `--kiosk` instead of `--start-fullscreen` also hides the way out (Alt+F4 still closes it); keep it for screens nobody needs for anything else.
- **The Newline (Android):** Chrome's menu → **Add to Home screen** gives an icon; on plain `http://` it opens as a normal tab (an installed full-screen app needs the secure address), so tap once for full screen. Test what the Newline allows: `docs/plan/ideas.md` → "Screens without browser bars".

## Other screens (the Newline, a hallway desktop)
`lab-os serve` listens on this computer only. Ways to show the hub on another screen:
- **The screen is this computer's display** (HDMI + USB touch): open `http://localhost:8080/`. Everything works.
- **Over the network:** `uv run lab-os serve --host 0.0.0.0` and open `http://<this computer's IP address>:8080/` (or `/design`) on the screen. Find the address with `hostname -I` (Linux; the first one) or `ipconfig getifaddr en0` (macOS). The screen must be able to reach this computer: some networks block devices from reaching each other (`docs/guides/network-setup-checklist.md` → "Networks before the router").
  - **With a real arm** (`--arm so101-white`): other screens are **view-only**. They show the hub, the arm and the monitor, and their **STOP works**, but teleop input from them is ignored ("view only: the arm is driven from the brain's computer"). Driving stays with this computer: its own browser, the AI tools (MCP, this computer only), and the Quest over `adb reverse` (it arrives as this computer).
  - **Not a secure page** (`http://` + an address): Esc leaves full screen (no Keyboard Lock), the screen may sleep (no Wake Lock), and Copy and voice don't work. Full screen itself works. The secure address is deferred (decision 2026-11-10); its fallbacks (Chrome's flag, `adb reverse`) apply here too: `docs/guides/voice.md` → "Secure pages".

## Performance test (`/perf`)
Drifting dots linked when close, and star streaks speeding up from the middle, drawn the same way as the concept's network and hyperspace, in plain gray. It shows frames per second (last second, average over 10 s, slowest frame) and the canvas size. Settings (what to draw, dots per million pixels, stars, resolution) are in the address, e.g. `/perf?draw=net&density=90&stars=3000&res=2`, so each screen can be bookmarked. Run it full screen on each screen for a minute and note the average: 55–60 fps can carry `full` quality; lower ones `reduced` or `minimal` (DESIGN.md → "Quality levels").

## Where the code is
- `src/lab_os/cli.py`: `lab-os serve`.
- `src/lab_os/hub/`: `server.py` (pages, `/api/…` endpoints, the module list, the assistant's state, the look), `project.py` (the Steps list), `commits.py` (`git log`: per day, the latest few), `internet.py` (background check).
- `src/lab_os/hub/web/`: `index.html`, `hub.js`, `hub.css` (the plain hub), `design.html` (the designed hub, one file), `ai.html` + `ai.js` (AI Control), `settings.html` + `settings.js`, `perf.html`, `perf.js`.
- `src/lab_os/settings.py`: what the settings page shows and how values are checked and written.
- `src/lab_os/teleop/web/`: `index.html` (teleop), `monitor.html`, `pages.css`; their scripts; `classic/` (the old pages).
- `src/lab_os/web/design/`: the module pages' shared look (`kit.css`, `kit.js`, `icons.svg`).
- `src/lab_os/web/`: files every page shares (vendored libraries, `theme.js`).
- Endpoints: `docs/dev/protocol.md` → "HTTP endpoints".
