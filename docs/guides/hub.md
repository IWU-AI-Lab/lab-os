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

Options are the same as `lab-os-teleop`'s: `--arm fake-xarm1`, `--venue visit-day`, `--port 8090`, `--config <folder>` (another place: `docs/dev/places.md`); plus `--mcp-port` for the robot tools for AI (`docs/guides/ai-control.md`), `--persona` (`docs/dev/personas.md`), `--open desk` to open the hub on this computer as that device once the brain runs ("Devices" below), and `--status-line` to print teleop's live status line under the log (off by default for `lab-os serve`: the hub shows the state; `lab-os-teleop` still prints it unless `--quiet`). Real arms (`--arm so101-white`, `--arm xarm1`) need the builder's OK before anything moves (SAFETY.md). With a real arm and `--host 0.0.0.0`, other computers only watch (and STOP); `--drive-from pi01.iwu.ai.lab` (repeatable) lets that computer drive too.

## Two taps
Browsers allow full screen and sound only after a press, so:
1. **Tap 1, full screen** ("Tap for full screen"): the builder's tap when leaving the hub on a screen. Skipped when the page is already full screen (kiosk mode, F11, an installed app) or the browser can't do it.
2. **Tap 2, start** ("Tap, click or press any key to start"): the visitor's tap. Opens the hub.

**The Full screen button** (since 2026-11-11): on every page (both hubs' status strips, next to ⏻ and ⚙ on the designed one; the bar of each module page; the classic pages; `/perf`), shown only while the page isn't full screen. It does what tap 1 does. Where the browser can't or won't go full screen, the button stays and **says why** when pressed (also in its tooltip): no Fullscreen API, turned off by the browser (`document.fullscreenEnabled` false, e.g. a kiosk or managed policy), blocked by a permissions policy, or refused with the browser's own words. Then use the browser's own full screen (F11; Ctrl+Cmd+F on a Mac). One helper does it for every page: `src/lab_os/web/fullscreen.js`.

Leaving full screen (a swipe, holding Esc, a reload) brings back the start screen with tap 1. Modules open **inside** the hub (no page load, which would leave full screen); **Back** or **Esc** returns. In Chrome and Edge, Esc means Back without leaving full screen (Keyboard Lock API; holding Esc still leaves). In teleop's desktop control, the first Esc leaves desktop control and the next one is Back.

**Back to the start screen** after `hub.reset_after_s` (theme, 30 minutes since 2026-11-10, was 3; a venue profile can set its own `reset_after_s`; both timers are in the settings, ⚙ → The hub) with no input on the hub or the open module. It stays full screen, so the next person only needs tap 2. It also clears the conversation. Never while something is in use: while any teleop page (the hub's or the Quest's) has the arm, an AI tool moves it, a chat answer is streaming, or a voice turn runs (from the mic press until the last spoken word).

**The chat:** type anywhere on the hub (it lands in "Ask anything" under the circle) and press Enter; **History** opens the whole conversation. Keys, AI setups and the budget: `docs/dev/chat.md`. **Voice:** hold the mic button next to it (or Space) and talk; the answer is spoken. Or dictation, chosen per screen (⚙ → This device → Talking to it): tap the mic and the words go into the ask line (`docs/guides/voice.md`). The mic shows only on a secure page with a microphone.

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
- **Startup as a video** (since 2026-11-18, quick job 34; a test for the stutter at lab check 1.3): ⚙ → This device → **Startup as a video**, off by default. From the start press until the core has arrived (~6.9 s) the designed hub plays a recording (`src/lab_os/hub/web/media/startup-full.webm` or `startup-maximal.webm`, whichever matches the device's level of detail; 1920×1080, 60 frames a second) instead of drawing the stars, the jump, the flash and the core, which aren't drawn meanwhile; the words (the start screen's, the title, the checks, the greeting) stay live above it, and so do the sounds; then the live hub, in the same state by then, fades in over half a second (the core's rings may look doubled for that moment). For `maximal` (more rings on the core, a busier frame and network) set ⚙ → This device → Level of detail → maximal too. It plays only for the hyperspace startup at `full` or `maximal` detail on a screen shaped like the recording, with the theme it was recorded with (the `.json` beside each video); otherwise the startup is drawn as usual and the console says why. **The design stays the source:** after any change to the startup, record both again with `scripts/record_startup.py --quality full` and `--quality maximal` (needs Chrome and ffmpeg; its first lines say how); a test fails while the theme and the recording disagree. `--compare out.mp4` puts the live and the video startup side by side.
- **In the address:** `?quality=maximal` (adds the far-layer verses; `full` is the theme's default, `reduced`, `minimal`), `?startup=assemble` (instead of `hyperspace`), `?sound=0`, `?full=0` (don't go full screen, for a laptop), `?res=0.5` (the drawing resolution, below), `#skip`. E.g. `http://localhost:8080/design?quality=maximal`.
- **Drawing resolution** (since 2026-11-11, for slow screens like the Newline): how many pixels the moving pictures are drawn at before the screen scales them up. `auto` (the default) = the screen's own, up to 2× (a 4K panel at 2× = 3840×2160 pixels every frame); `1` = one per CSS pixel (a quarter of that on such a screen); `0.75`; `0.5` (a sixteenth: soft, but very light). Applies to the network and hyperspace, the effects layer, the arm drawings in modules, and the 3D arm in teleop/monitor and AI Control's side view. Set it per screen in ⚙ → This device (kept in that screen's browser), or in the address: `?res=` wins (also for the pages opened inside the hub). Same scale as `/perf?res=`, so a number that runs smoothly there is the one to pick. Text, the core and the frame are not affected (they're not canvases). The console says `hub: drawing at 1× (1920×1080 for 1920×1080)`.
- **System diagram** (2026-11-18, quick job 12): the network icon beside **List all** in the Devices panel opens it full screen, like a details page. The brain as its core in the middle; the screens on the left (lit with the hub open, grey if listed but not open; this screen in brackets) and an AI tool (MCP) below them; the cameras and arms on the right (lit: the arm the brain drives), LeLab below a borrowed arm; the AI service above; the brain's parts in the order a move takes them. The kind of link is the line's style (USB solid, network dashed, MCP dotted, internet long dashes), and only real links carry pulses. It isn't a second devices map: it shows how things connect, not every device (no leader arms, the cameras as one). Drawn from the same facts as the panels each time (`devices.yaml`, the devices with the hub open, the AI setup), so another place or a new arm draws what it has; the names as people say them (`so101-white` → SO-101 White). The code: `src/lab_os/hub/web/system-diagram.js`. A copy for the docs, made from a running brain with `scripts/save_system_diagram.py` (its first lines say how):

  ![System diagram](../dev/system-diagram.svg)
- **Not real yet, so not shown:** whether a robot or camera is switched on (the roll call needs the lab router: the Devices panel's Power column says "not known"), alerts (no real alert source yet). The Devices panel is still the place's `devices.yaml` (robots, cameras); the devices with the hub open are in "Open on…" (below).
- **The code:** one file, `src/lab_os/hub/web/design.html`: the concept's CSS, SVG and JavaScript, with the made-up data replaced by the brain's endpoints and the concept controls removed. Fonts are bundled in `src/lab_os/web/vendor/fonts/` (offline).

## Asking it to show something (2026-11-14)
Ask the assistant, typed or by voice: "pull up the teleop page", "show me the AI spend", "open the settings", "go back to the hub". It opens that page **on the screen you asked** and says so in a few words ("Here's Teleop."). It knows what each screen can show: the module buttons, Settings, the callouts' pages (designed hub), the conversation. Details: `docs/dev/chat.md` → "It opens pages".

**The core on an open page:** while a module or a callout's page is open, the core sits small in the bottom right corner. It works there too: **hold it to talk** (like the mic), and what it hears and says shows beside it for a while. With the wake word on, "hey Jarvis" keeps working with a page open (it used to stop), so "hey Jarvis, go back to the hub" works hands-free.

## The module pages (teleop, monitor, AI Control)
Since 2026-11-10 they're in the hub's design too (`src/lab_os/web/design/`: `kit.css`, `kit.js`, `icons.svg`, shared by every module page). Inside the hub they drop their own frame and title; on their own screen they have both, the place's name, the clock and a **Full screen** button.
- **Teleop** (`/teleop`): the arm in 3D on the left; on the right how to drive it (the Quest's Enter AR/VR, Desktop control and its keys) and what the page sends. Status (brain, control, arm) and **STOP** in the bar, always visible; while desktop control is on, "X = STOP" beside it (X on the keyboard stops in every mode).
- **Monitor** (`/monitor`): for an onlooker screen: the arm in 3D, a gauge per joint, STOP. It watches; it never drives.
- **AI Control** (`/ai`, the third button): what an AI tool (Claude Code + Fable, Codex, …) does with the arm, live: the arm seen from its side with its real geometry (from the arm's kinematics, in cm), where the last `move_to` aimed, every robot-tool call as it happens (ok / clipped / refused / stopped / error, with what came back), whether the tools are on and moves allowed, and STOP. Until the first call it says how to connect Claude Code. It never moves anything.
- **The old pages** stay at `/classic/teleop` and `/classic/monitor` (same scripts, the old look), in case the new ones break somewhere (e.g. the Quest's browser).

## What the Quest sees (2026-11-18)
On the brain's own computer, a button in the strip (the screen-with-goggles icon; **Quest view** on the plain hub) opens a window showing what the Quest on the USB cable sees, so the room can watch. It needs scrcpy, downloaded once with `uv run lab-os quest-view --install`. `docs/guides/quest-view.md`.

## Settings (the ⚙, or `/settings`)
The ⚙ in the designed hub opens this same page inside the hub. The sections sit side by side and the page **scrolls down** to the rest: the assistant (the monthly AI budget), this place, robots and the safety limits are below "This device" (since 2026-11-17; before, they spilled off to the right where they couldn't be reached).
- **The hub, the assistant, this place, robots in this venue:** values from `theme.yaml`, `place.yaml` and the running venue's file, saved the moment they change, **into those files, with their comments kept**. Each one says when it applies: at once (the hub re-reads the theme), from the next question, or after a restart (the safety ones). They're ordinary config changes: in the lab they show up in `git diff config/`; commit them like any edit, or undo with `git checkout config/<file>`.
- **Safety limits in this venue:** the AI tools' per-move limit, the speed cap and the floor, each a switch (on by default). One that's off gets an accent bar and "OFF" after its name, and the bar at the top says "Limits off: …". On a public venue or one with `limits_locked: true` (visit days) they're greyed out and say why; they apply when the brain restarts (SAFETY.md → "Limits").
- **Only on the brain's computer:** other screens see the settings but can't change them (a hallway screen shouldn't rename the lab or switch robots on).
- **This device:** level of detail, drawing resolution, sound, full screen on the start press, the startup as a video, the way in to voice, the assistant's language (input and output, `docs/guides/voice.md`), and the device's "Lab hub" icon. Kept by the brain under the device's name (below, "Devices"), so the Newline can run `full` while a Pi runs `minimal`, every monitor of a device gets the same, and a new browser under the same name starts with them. Any device can change its own (they were per browser before). A page with no name keeps them in its browser only, as before.
- **Growing with new modules:** the page draws whatever `src/lab_os/settings.py` lists. A setting is one `Field` (file, path, label, kind: choice / bool / number / text / color / list); a new module adds its own section with `settings.register(Section(...))`. No page changes needed.

## Other monitors on the brain's computer (HDMI / DisplayPort)
Monitors plugged into the brain's computer are just more screens of the same browser, so any page can go there:
- **From the hub:** open the module (Teleop, Monitor, AI Control, …), press **Open on…** next to Back, then **Another monitor of this computer** (designed hub). In Chrome on that computer the page opens on the other monitor (Chrome asks once to allow "window management"; it needs `localhost`, which the brain's own screen is); click it there for full screen. The hub closes its copy. Without that permission, or in another browser, it opens a window to drag over. Settings → This device → "Monitors on this computer" grants the permission ahead of time and lists them (and then other devices' "Open on…" lists name the monitors).
- **Or a second hub on that monitor:** open the hub there too under the same name (`/design?device=desk`). Then the device has two windows and other devices' "Open on…" offers both (below, "Devices").
- **By hand:** open `http://localhost:8080/monitor` in a new window, drag it to the monitor, press F11 (or the page's Full screen button). Or from a terminal, an app window at that monitor's position (here a second 1920-wide monitor to the right):
  ```bash
  google-chrome --new-window --app=http://localhost:8080/monitor --window-position=1920,0 --start-fullscreen
  ```
- Any page works this way: `/monitor`, `/ai`, `/teleop`, `/design` (a second hub), `/settings`.
- **The Newline on an HDMI cable + its USB touch cable** to the brain's computer is the same thing: one more monitor (with touch), and it's `localhost`, so even voice will work there.

## Devices (step 8): named devices, "Open on…", one tap each
A **device** is a computer or screen with the hub open under a name in its address: `/?device=desk`, `/?device=newline`, `/?device=quest` (lowercase letters, digits and dashes). The brain keeps the list of devices that have the hub open right now; nothing else about them.
- **The name** stays in the address (a reload keeps it), and the browser remembers it: the next time it opens `/` without a name, it's that device again. `?device=` with nothing after it opens it with no name.
- **This device** (⚙): its settings are kept by the brain under the name, in the place's `hub-devices.yaml` (above, "Settings").
- **A device's monitors:** each monitor with the hub open is a window of the device (e.g. the desk's two monitors, each with `/design?device=desk`). Other devices' "Open on…" opens on the free one (nothing open there); when two are free, or none, it asks which ("left monitor", "right monitor", or the monitor's own name once ⚙ → This device → "Monitors on this computer" was allowed).
- **Open on…** (next to Back in an open module, both looks): lists the other devices with the hub open and what each shows, and the device's own other monitors. Pick one: the page opens **inside that device's hub**, as if someone had pressed the button there (even from its start screen, with no startup and no new conversation; a module open there gives way only when you picked that monitor). This hub closes its copy, so a teleop page never holds two connections. The page there says "Opened from <device>".
- **Closing it:** **Back** there, or **Bring it back** here (a line at the top of the hub, "Monitor is on desk"): it closes there and opens here again.
- **Only devices with the hub open are listed**, so a device used for something else (the Newline showing a slide) is never taken over. The menu opens on the left, so it never covers a page's STOP.
- **When the brain restarts,** every hub page reconnects by itself within a few seconds and tells the brain again what it shows; "Bring it back" still works afterwards. (A page opened while the brain was off doesn't load at all: tap the icon again once it runs.)
- **Who may:** any hub page can open a page on another device that has the hub open (it only changes what that screen shows; a real arm's teleop page on another computer is still view-only).
- The Quest's VR hub (`/xr`) isn't a device yet: open `/design?device=quest-a` (or `quest-b`/`-c`: `config/devices.yaml`) in its browser to have the Quest listed.

**One tap per device** (nothing starts by itself):
- **The brain's computer: "Start lab-os".** Make the icon once, in `~/lab-os`:
  ```bash
  uv run lab-os icon --device desk                      # fake arm
  uv run lab-os icon --device desk -- --arm so101-white # the white arm (moves only when asked)
  ```
  It's in Ubuntu's app list (right-click → Add to Favorites puts it in the dock). It opens a terminal that runs `lab-os serve --open desk --host 0.0.0.0 …` (the brain's log; Ctrl+C stops the brain) and, once the brain runs, the hub full screen as `desk` (Chrome's app window; any Chromium browser, else the default one). Tapping it again while the brain runs only opens the hub. On macOS or Windows, `lab-os icon` prints the command for a shortcut. Which hub look it opens: `hub.look` in the theme (⚙ → The hub). `--host 0.0.0.0` is there so the other devices can reach it; with a real arm they only watch (and STOP).
- **Other computers: a "Lab hub" icon.** Open the hub there once by the brain's address with the device's name (`http://<brain's IP address>:8080/?device=newline`), then ⚙ → This device → **"Lab hub" icon**: a Linux icon (`.desktop`: put it in `~/.local/share/applications/` or on the desktop and allow launching) or a Windows one (`.bat`), with the brain's address and the name filled in. By hand, the same thing:
  ```bash
  google-chrome --app=http://<brain's IP address>:8080/?device=pi01 --start-fullscreen
  ```
  (`chromium` on a Pi). The brain's address is the desktop's IP address for now: when it changes, make the icon again.
- **The Newline (Android) or a tablet:** Chrome → `http://<brain's IP address>:8080/?device=newline` → ⋮ → **Add to Home screen**. On plain `http://` it opens as a normal tab: tap once for full screen.

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
- **Over the network:** `uv run lab-os serve --host 0.0.0.0` and open `http://<this computer's IP address>:8080/?device=<its name>` (or `/design?device=…`) on the screen ("Devices" above: the name lists it and keeps its settings). Find the address with `hostname -I` (Linux; the first one) or `ipconfig getifaddr en0` (macOS). The screen must be able to reach this computer: some networks block devices from reaching each other (`docs/guides/network-setup-checklist.md` → "Networks before the router").
  - **With a real arm** (`--arm so101-white`): other screens are **view-only**. They show the hub, the arm and the monitor, and their **STOP works**, but teleop input from them is ignored ("view only: the arm is driven from the brain's computer"). Driving stays with this computer: its own browser, the AI tools (MCP, this computer only), and the Quest over `adb reverse` (it arrives as this computer).
  - **Not a secure page** (`http://` + an address): Esc leaves full screen (no Keyboard Lock), the screen may sleep (no Wake Lock), and Copy and voice don't work. Full screen itself works. The secure address is deferred (decision 2026-11-10); its fallbacks (Chrome's flag, `adb reverse`) apply here too: `docs/guides/voice.md` → "Secure pages".

## Performance test (`/perf`)
Drifting dots linked when close, and star streaks speeding up from the middle, drawn the same way as the concept's network and hyperspace, in plain gray. It shows frames per second (last second, average over 10 s, slowest frame) and the canvas size. Settings (what to draw, dots per million pixels, stars, resolution) are in the address, e.g. `/perf?draw=net&density=90&stars=3000&res=2`, so each screen can be bookmarked. Run it full screen on each screen for a minute and note the average: 55–60 fps can carry `full` quality; lower ones `reduced` or `minimal` (DESIGN.md → "Quality levels").

## Where the code is
- `src/lab_os/cli.py`: `lab-os serve`.
- `src/lab_os/hub/`: `server.py` (pages, `/api/…` endpoints, the module list, the assistant's state, the look), `hub_devices.py` (the devices with the hub open, "open on…", each device's settings), `launch.py` (`--open`, the "Start lab-os" icon), `project.py` (the Steps list), `commits.py` (`git log`: per day, the latest few), `internet.py` (background check).
- `src/lab_os/hub/web/`: `index.html`, `hub.js`, `hub.css` (the plain hub), `design.html` (the designed hub, one file), `system-diagram.js` (the system diagram), `ai.html` + `ai.js` (AI Control), `settings.html` + `settings.js`, `perf.html`, `perf.js`.
- `src/lab_os/settings.py`: what the settings page shows and how values are checked and written.
- `src/lab_os/teleop/web/`: `index.html` (teleop), `monitor.html`, `pages.css`; their scripts; `classic/` (the old pages).
- `src/lab_os/web/design/`: the module pages' shared look (`kit.css`, `kit.js`, `icons.svg`).
- `src/lab_os/web/`: files every page shares (vendored libraries, `theme.js`, `device.js`: this page's device name, its settings, the hub's connection and the "Open on…" lists).
- Endpoints: `docs/dev/protocol.md` → "HTTP endpoints".
