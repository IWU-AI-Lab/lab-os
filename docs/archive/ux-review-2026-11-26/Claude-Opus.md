# UX review, 2026-11-26: Claude Opus (maximal and minimal looks)

**Scope:** every page in `PAGES` (`src/lab_os/hub/server.py`), every hub module and details page, the power menu, the device card, the start screen and the startup. **Look:** lines 1–78 are the maximal look. Lines 79–88 ("The minimal look") are the minimal look. Reduced and full are not reviewed yet: see the end.

**How:** a separate brain (`lab-os serve --arm fake`, port 8092, a copy of `config/`), so the repo's settings did not change. Chrome (Playwright) took the screenshots at device scale 1. The sizes:

| Name | Size | Meaning |
|---|---|---|
| Pi | 800 × 480, touch | the Pi's touchscreen |
| Laptop | 1440 × 900 | a laptop |
| Newline | 1600 × 900 | a computer on the Newline by HDMI |
| 4K | 3840 × 2160 | the Newline (or a 4K 32") at 100 % scale. At 150–200 % scale it looks like the 32" and laptop shots. |
| 32" | 2560 × 1440 | the 32" lab monitor |
| Phone | 390 × 844, touch | a phone |

**Conditions:** no AI key, so the AI is off; no cameras; no Raspbot; the fake arm. Lines about the VR and AR pages say **from the code** (the VR line with a screenshot also used the VR hub's "Preview on this screen").

**Marks:** **(Builder)** = a change the builder asked for. **(Overrules DESIGN.md)** = my opinion goes against DESIGN.md; the line says which rule.

**Screenshots:** `Claude-Opus/`. A file `sheet-<page>.png` shows the Pi, laptop, Newline and 4K shots of one page side by side (top left, top right, bottom left, bottom right).

**How bad:** High = text is lost, a control is too small to use, or a page misleads. Medium = it looks wrong or is unclear. Low = polish.

## Problems on many pages

| # | Page | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|---|
| 1 | All pages except the hub (Teleop, Monitor, AI Control, Training, Cameras, Raspbot, Wake Word, Command Center, Diagnostics, System Map, Settings, All Pages) | 4K, 32" | The text stops growing at 22 px (`kit.css`: `clamp(12px, …, 22px)`). On the 4K screen the pages look tiny, and most of the screen is empty. | Raise the top of the clamp (about 40 px), or scale from the smaller screen side, as the hub does. | High | sheet-settings.png, sheet-ai.png, training-uhd.png |
| 2 | Settings, All Pages, Monitor, Training, Diagnostics, Wake Word, Cameras | Newline, 4K, 32" | The content is a narrow column at the left or top. The right half of the screen is empty. | Put the cards in a grid that fills the width, or center one column with a max width. See Settings below for the builder's case. | Medium | monitor-newline.png, pages-newline.png, wake-word-uhd.png |
| 3 | Hub: the device card, Devices details | All | "Diagnostics", "Remove" and "Remove from the list" are gray browser buttons. The hub uses the class `btn` but `design.html` never styles it (it does not load `kit.css`). | Add the kit's `.btn` style to `design.html`. | High | sheet-hub-x.png (device card), hubx-laptop-detail-devices.png |
| 4 | The status chips (Teleop, Monitor, AI Control, Training, Cameras, Webcam, Wake Word) and the hub's top strip | All | The values are all lowercase: "connected", "free", "none", "off", "not safe", "answering", "online", "lab". | Write the values in sentence case ("Connected", "Not safe"). Keep the small CAPS label before them. | Medium | teleop-laptop.png |
| 5 | The 3D arm (Teleop, SO-101 Monitor, Webcam, Monitor) | All | The "held" tint (`frozen` as a glow on the steel body) makes the arm salmon pink, not muted rust. The arm is held at start, so most people first see a pink arm. | Keep the body steel. Show "held" with a rust floor ring or outline and the pause icon, as DESIGN.md says. | Medium | teleop-laptop.png, monitor-so101-newline.png |
| 6 | Teleop, Monitor, SO-101 Monitor, Webcam | All | At start, with nobody driving, the bar says "frozen: release grip" or "frozen: let go of the clutch". It reads like a fault. | Say "Held still" with the pause icon. Put the reason in the tooltip. | Medium | teleop-laptop.png |
| 7 | Teleop, SO-101 Monitor, AI Control, Webcam | All | Joint names show as code names: "shoulder_pan", "wrist_flex". | Show "Shoulder Pan" (or a plain name such as "Base Turn"). Keep the code name in the tooltip. | Medium | monitor-so101-laptop.png |
| 8 | Hub devices graph, Devices details, Command Center, System Map | All | A device with no name shows as "127.0.0.1 (no device name)". It shows an address, and it is long, so it overlaps other labels. | Show "Unnamed screen". Show the address only in the device card. | Medium | hub-laptop.png, system-map-pi.png |
| 9 | System diagram, Settings, Command Center | All | One thing has many names: "rv-laptop" and "Rv Laptop" (System diagram); "Monitor So101", "Monitor Xarm" (Settings → Buttons Around the Core); "Monitors" and "SO-101" (Command Center tiles) against "Monitor" and "SO-101 Monitor" (All Pages). | Take every page title from `PAGES`. Show device names as they are stored, or the display name. | Medium | hubx-laptop-detail-system.png, sheet-settings-x.png |
| 10 | Hub toast, Settings → Talking to It, Phone Remote | All; Pi clipped | The "AI isn't set up" message prints a 120-character file path. On the Pi the toast runs off the right edge and the words are lost. | Say "Add an AI key to config/.env, then restart." Put the full path in the tooltip. Make the toast fit the screen. | High (Pi), Medium | hub-pi.png, remote-phone.png |
| 11 | Every hub module | Laptop | The docked core in the bottom-right corner covers content: in Teleop it covers the Mode list's arrow and the STOP line. | Keep the core's corner free (padding in the module), or make the docked core smaller. | Medium | hubx-laptop-mod-teleop.png |
| 12 | Hub, Command Center, Settings, Teleop, System Map, Raspbot | Pi, Phone | Controls are smaller than 40 px (measured): the hub's ⤢ marks 21 × 18; Command Center ⋯ and ⤢ 12 × 12 and the eye 24 × 24; Settings ↑↓ 22 × 22 and switches 52 × 30; the Teleop check box 22; System Map labels 15 high; on the phone the Raspbot drive buttons are 27 wide and the speed slider 12 wide. | Give every control a 40 px tap area on small screens (DESIGN.md already says so). | High | ccx-pi-live.png, raspbot-phone.png |
| 13 | Hub, AI Control, Command Center, System Map | Laptop | Text is too small (measured): the commits axis 8.2 px, the log's time 9.3 px, the range buttons 9.6 px, AI Control's "Gripper x y z Open" 9.1 px, Command Center group heads 9.4 px, the device graph names about 7 px. | Keep text at 11 px or more on a laptop, and more on the 32". | Medium | hub-laptop.png, ai-laptop.png |
| 14 | Power menu, All Pages rows, Settings rows, Command Center tiles | All | These are plain rectangles. Cut-corner cards sit next to them on the same page. | Give them the cut corner (`lines.corner_cut_px`). | Low | hubx-laptop-power-menu.png |
| 15 | All Pages, Command Center Pages list | All | All Pages is a plain list with "/path · text" rows. The Command Center shows the same pages as grouped tiles with icons. The two work differently. | Use the Command Center's grouped tiles (with search) on All Pages too. Show each page's one line under its tile on hover. | Medium | pages-laptop.png, ccx-laptop-selected.png |
| 16 | All Pages, AI Spend, Devices details, the arm caption | All | "·" separates words in many lines. DESIGN.md says not to use dots as separators. | Use two lines, or a comma. | Low | pages-laptop.png |
| 17 | Hub, modules, VR | All | **(Builder)** The interface is flat: the panels, the core and the decoration all sit on one layer. The film references show layers at different depths. | Add three steps: (1) when a module opens, scale the core up a little and put a dark halo under it, so it is clearly in front; (2) put the panels' decoration (ticks, notches, hatch blocks, corner brackets) 2–4 px off the panel, with a slight shift when the pointer moves (parallax), so it floats over its panel; (3) blur and dim the far network a little more. In VR see the VR Hub lines. **(Overrules DESIGN.md: "no drop shadows")**: a soft dark halo under the front layer is the cheapest way to show depth. | Medium | hubx-laptop-mod-teleop.png |

## The Hub (`/`)

| # | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|
| 18 | All | **(Builder)** The All Pages icon is a chain link. It reads as "copy a link". | Use a grid of four squares, the usual "all apps" icon. A document icon means a file, so it does not fit. | Medium | hub-laptop.png |
| 19 | Laptop, Newline, 4K | ⏻, All Pages and ⚙ are small (about 14 px), dim gray icons in the far corner. People do not find them. | Make them bigger, in the text color, with a 40 px area. | Medium | hub-laptop.png |
| 20 | All | **(Builder)** Power menu: the title "Power" is in the interface font. | Use the title font (Orbitron), as other titles do. | Low | hubx-laptop-power-menu.png |
| 21 | All | **(Builder)** Power menu: "lab-os stays on" and "asks first" add nothing, and they make the menu wide. | Remove them. Make the menu about 16 rem wide. | Low | hubx-laptop-power-menu.png |
| 22 | All | **(Builder)** The power menu floats free in the corner. It is not attached to ⏻ and has no icons. It also covers the Commits title. | Make it a drop-down under ⏻, as on Windows, Linux or macOS: a small notch that points at ⏻, a cut corner, one icon per row (↩ for the start screen, ⏻ for shut down), the glow line on top. | Medium | hubx-laptop-power-menu.png |
| 23 | All | **(Builder)** The shut-down confirmation looks the same as the menu, and its title is in spaced capitals. | Keep it in the same drop-down. Make "Shut down" a red filled button and "Cancel" a plain button, side by side. Put the arm warning first. | Medium | hubx-laptop-power-confirm.png |
| 24 | All | **(Builder)** The start screen says "Safe to start. This only opens the hub; no robot moves." | Keep only "Safe to start." with the shield. **(Overrules DESIGN.md → Startup, the "Safe to start" line.)** | Low | hub-start-laptop.png |
| 25 | All | **(Builder)** The start screen shows a lone "lab" at the bottom, beside the clock. It is the venue's code name. | Show the place's name ("AI Comp Lab") with the pin icon there, or remove it. I suggest the place's name: the start screen has no title. | Medium | hub-start-laptop.png |
| 26 | All | The top strip shows the venue as "lab" with a pin. People do not know what it means. | Show the venue's own name in Title Case, or hide it while the venue is the default one. | Medium | hub-laptop.png |
| 27 | All | **(Builder)** The AI core is a flat drawing of rings. | Make a 3D core: start from `hub/web/xr/core.js` (three.js, the same rings). Tilt each ring on its own axis like a gyroscope, so they cross in depth; let them line up flat when it listens. For an original shape, give each persona its own ring set (`picture` in the persona). Minimal keeps the flat core. | Medium | hub-laptop.png |
| 28 | Full, maximal | **(Builder)** Another background: a black hole. | Add `hub.background: network | black-hole`. Draw a dark disc with a thin bright ring (the accretion disc) behind the core, and bend the network's dots around it. Use it only in full and maximal. **(Overrules DESIGN.md: "calm in the middle")**: put it behind the core, so the core is its center, and keep it dim. | Low | — |
| 29 | Laptop, Newline | "AI Control" breaks onto two lines. The other buttons have one line, so the button is taller. | Let the button grow wider, or use the same height for all. | Low | hub-laptop.png |
| 30 | Laptop | Asking while the AI is off: the question shows faintly under the ask line, and nothing else happens. | Show the error under the core (DESIGN.md's error rule: what broke, what still works). | Medium | hubx-laptop-type-answer.png |
| 31 | All | The Current Project panel says "Step 2 of 12". Its details page says "6 of 13 steps done". | Use one count in both places ("Step 2 of 13, 6 done"). | Medium | hubx-laptop-detail-project.png |
| 32 | 4K | The hub uses a band in the middle. The panels are small, and the top and bottom thirds are empty. | Scale the panels and the strip with the screen, as the core does. | Medium | hub-uhd.png |
| 33 | Newline, 4K | The Commits bars fill only part of the chart's width. | Spread the bars over the full width. | Low | hub-uhd.png |
| 34 | Pi | The strip leaves out the AI fact. The frame's hatch block sits on the strip's words. ⏻, All Pages and ⚙ move to a row under the title. | Keep the AI fact as an icon only. Move the hatch block clear of the strip. | Low | hub-pi.png |
| 35 | Pi | "List all" opens a list that runs past the frame and under the log lines (the last device is cut off). The graph's names are about 6 px. | Cap the list above the log, and scroll it, as DESIGN.md says. Hide the log lines while the list is open. | Medium | hubx-pi-detail-listall.png |
| 36 | Laptop | The device card covers the Monitor button. | Open the card over the Devices panel, not over the buttons. | Low | sheet-hub-x.png |
| 37 | Laptop | The startup's checks ("Theme loaded", "Display 1440×900") are about 9 px. | Make them the interface size. | Low | hubx-laptop-start-t52.png |
| 38 | 4K | One frame took 83 ms in 3 s (in a headless Chrome on a Mac; other sizes ran at 60 a second). | Check the frame rate on the Newline's computer. | Low | — |

## Hub details pages and modules

| # | Page | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|---|
| 39 | Commits details | Laptop, Pi | The first date ("Oct 28") is cut off at the left ("ct 28"). | Keep the first label inside the chart (align it left). | Medium | hubx-laptop-detail-commits.png |
| 40 | Devices details | All | "Motor power" is an empty column. A device marked "Connected: No" also says "The hub is open in 2 windows". | Hide empty columns. Say "Last open in 2 windows" for a device that is off. | Medium | hubx-laptop-detail-devices.png |
| 41 | Current Project, AI Spend details | Laptop, Newline | The content uses the left 60 % of the page. | Use the width (for example the steps in two columns). | Low | hubx-laptop-detail-project.png |
| 42 | System diagram | Laptop | The legend is about 7 px. | Make it 11 px or more. | Low | hubx-laptop-detail-system.png |
| 43 | Command Center as a module | Laptop, Pi | The opening's dark area does not fill the module. Lighter bands show at the left and right. | Make the opening fill the module's whole inner area. | Medium | hubx-laptop-mod-command.png |
| 44 | Every module page | Laptop | The page's content starts about 50 px to the right of the module's title. STOP sits alone on a row at the right. | Line up the content with the title. Put STOP in the module's top bar, next to Open on…. | Low | hubx-laptop-mod-teleop.png |

## Settings (`/settings`)

| # | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|
| 45 | 32", 4K, Newline | **(Builder)** There is a large empty area to the right of the settings (about 700 px on the 32"). | Above about 1800 px wide, show two columns of sections (This Device and Assistant on the left, The Lab and Robots on the right), and keep the menu at the left. This is better than centering: the space shows more settings at once. | Medium | settingsx-32in.png |
| 46 | All | "Safety Limits and Shut Down" is always red in the menu and as a section title. Red means "a person must act now". | Use the warning icon in the main color. Keep red for the Shut Down button. | Medium | settings-laptop.png |
| 47 | All | The arrows that order the hub's buttons are 16–22 px. | Make them 40 px on touch screens, or let people drag the rows. | Medium | sheet-settings-x.png |
| 48 | All | "Teleop 1:1 Top Joint Speed" says "°/s. None: the servos' own top speed." The line starts with a unit. | Write "Degrees per second. None: …". | Low | sheet-settings-x.png |
| 49 | Pi | The search and the five tabs fill the first screen. The first setting is cut off at the bottom. | Make the tabs one scrolling row, and put the search in it. | Low | settings-pi.png |

## Teleop (`/teleop`) and Webcam Teleop (`/webcam`)

| # | Page | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|---|
| 50 | Teleop | Pi | "Drive it" is below the first screen. Someone on the Pi must scroll to find the controls. | On small screens, show "Drive it" first, or use two tabs (View, Drive). | Medium | teleop-pi.png |
| 51 | Teleop, Webcam | Laptop | "Drive it" holds a long paragraph (the Quest's controls, six lines; Webcam: three paragraphs). | Put the help in a folded "How to drive" part. Show only the step that applies now. | Medium | teleop-laptop.png, webcam-laptop.png |
| 52 | Teleop | Laptop | On a laptop, "Enter AR" and "Enter VR" are gray, and an amber line says "No immersive XR on this device". Amber means a warning, but this is normal. | Hide the two buttons where there is no XR. Say it once in dim text. | Low | teleop-laptop.png |
| 53 | Teleop | Laptop | "Hand → arm" breaks onto three lines; "3D arm in the headset" onto two. | Put the label over the list. | Low | teleop-laptop.png |

## Monitor pages

| # | Page | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|---|
| 54 | Monitor | All | The cards say "1 connected", "none connected" and "Not connected". | Use one form: "1 connected", "None connected". | Low | monitor-laptop.png |
| 55 | xArm Monitor | All | It says "No xArm is connected" three times, beside an empty 3D grid. | Show one message in the middle of the 3D area with the arm icon. | Low | monitor-xarm-laptop.png |
| 56 | SO-101 Monitor, Raspbot Monitor | Pi | The joints (or the status list) are below the first screen. | On the Pi, put the 3D view and the joints side by side. | Low | monitor-so101-pi.png |

## AI Control (`/ai`)

| # | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|
| 57 | 4K | The arm drawing grows with the screen, but its callouts stay small. | Scale the callouts with the drawing. | Medium | ai-uhd.png |
| 58 | Pi | "What the AI did" is below the first screen. | On the Pi, put it in a tab or under a button. | Low | ai-pi.png |

## Training (`/training`)

| # | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|
| 59 | Laptop, Newline | Long file paths run past the card's right edge and are cut off ("sheep.json isn't o"). | Break long paths (`overflow-wrap: anywhere`), or show the file name and put the path in the tooltip. | High | training-laptop.png |
| 60 | Pi | The two cards overlap: the line "Not safe to start: …" is under the second card. | Fix the grid's row height on small screens. | High | training-pi.png |

## Cameras (`/cameras`)

| # | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|
| 61 | All | With no camera, the page is one small sentence at the top left of an empty screen. | Show the camera icon and the sentence in the middle. | Low | cameras-laptop.png |

## Raspbot (`/raspbot`, made for a phone)

| # | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|
| 62 | Phone | The three columns (Drive, Camera, Pan and Tilt) are squeezed into 390 px. The drive buttons are 27 px wide, the speed slider is 12 px wide, and "Labels off" breaks onto two lines. | Stack it on a phone: the camera on top, the drive pad full width (buttons 64 px or more), then pan and tilt, then the status. | High | raspbot-phone.png |
| 63 | All | The middle of the drive pad is empty. | Put STOP there, under the thumb. | Medium | raspbot-laptop.png |

## Phone Remote (`/remote`)

| # | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|
| 64 | Phone | The page says "Hold Talk and ask", but there is no Talk button when voice is not set up. | Say "Type below" when voice is off. | Medium | remote-phone.png |
| 65 | Phone | The placeholder is cut off ("Ask, e.g. open the system diagr"). | Use a shorter placeholder ("Ask anything"). | Low | remote-phone.png |

## Wake Word (`/wake-word`)

| # | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|
| 66 | All | The word shows as "hey Jarvis (active)", in lowercase. | Write "Hey Jarvis (active)". | Low | wake-word-laptop.png |

## Command Center (`/command-center`)

| # | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|
| 67 | Laptop, Newline | "Zoom to fit" puts all six items in one row. The two live screens are about 110 px wide with 5–6 px text. Devices that are off take as much room as live ones. | Fit the live devices first. Put the devices that are off in a small row at the bottom of the workspace. | High | ccx-laptop-selected.png |
| 68 | Pi | The device list is not there. Activity and Pages fold to bars. The controls are 12–28 px. | On the Pi, show the device list as a tab. Make the controls 40 px. | Medium | ccx-pi-live.png |
| 69 | All | The inspector asks for a page in a list, then "Open". The Pages tiles above already do this. | Remove the list from the inspector, or make a tile press open the page on the selected screen. | Low | ccx-laptop-selected.png |

## Diagnostics (`/diagnostics`)

| # | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|
| 70 | All | On this page `?device=` means "show only this device". On every other page it means "this screen's name". A screen named rv-pi that opens `/diagnostics?device=rv-pi` sees only itself, as "Off". | Use another word for the filter (`?show=`). | Medium | diagnostics-laptop.png |
| 71 | All | The bar says "Connected 1, Off 7", but the page shows one card. | Say "Showing 1 of 8" and make "All devices" clear. | Low | diagnostics-laptop.png |

## System Map (`/system-map`)

| # | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|
| 72 | 4K, laptop | The controls' help (bottom left) is 10–11 px and dim. On the 4K screen it cannot be read. | Make it 12 px or more, and scale it with the screen. | Low | system-map-uhd.png |

## VR Hub (`/xr`) and Teleop's AR and VR

| # | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|
| 73 | Quest (from the code) | The VR hub has its own module list (`VR_MODULES` in `xr/modules.js`: Teleop, Monitor, AI Control, Raspbot). The flat hub shows Teleop, Training, Cameras, AI Control, Monitor (`hub.modules`). | Use `hub.modules` in VR too, and leave out the ones VR cannot show. | Medium | xr-preview-laptop-hub.png |
| 74 | Quest (from the code) | The VR Devices panel says "1 of 15 linked". The flat hub says "1 of 6 connected". | Use the same list and the same word. | Medium | xr-preview-laptop-hub.png |
| 75 | Quest (from the code) | `xr/core.js` reads the look from `theme.quality.default`, not from this device's choice (⚙ → Level of Detail). | Read the device's look as `persona-table.js` does (`currentLook()`). | Medium | — |
| 76 | Quest (from the code) | **(Builder)** There is little depth: all panels sit on one curve 2.4 m away, the ask line is 1 cm in front of the core, and the core's rings are "a few millimetres apart". | Put the rings 2–4 cm apart and tilt them. Put the core about 0.3 m in front of the panels. Put each panel's decoration 3–5 cm in front of its panel. When a page opens, keep the core in front of the page. | Medium | xr-preview-laptop-hub.png |
| 77 | Quest (from the code) | The Current Project title is cut off with "…". | Allow two lines, or a smaller size for long titles. | Low | xr-preview-laptop-hub.png |
| 78 | Quest AR and VR teleop (from the code) | The floor, table and wall colors are written in `teleop/web/xr-scene.js` (`0x24272b`, `0x8a7458`, `0x4a4f57`, …), not in `theme.yaml`. | Move them to `arm3d` in the theme. | Low | — |

## The minimal look

**How:** the same brain and sizes, with each review device set to minimal (⚙ → This Device → Level of Detail). I checked the parts that change with the look: the hub, the start screen, the startup, the core's states, the hub's modules and details pages, the System Map, the persona table, the Command Center's opening and the VR preview. A "motion test" takes two screenshots 2–3 s apart and compares them pixel by pixel.

**Lines 1–78 still apply in minimal**, except the glow and motion parts of 17, 27, 28 and 38. The pages that use `kit.css` do not change with the look: Teleop in minimal and in maximal differ only in the clock and the live numbers. The start screen, the Monitor and the Command Center workspace are still (only the clock changes). The hub's network is a still dot grid, and only the log changes.

| # | Page | Size, look | Problem | Fix | How bad | Screenshot |
|---|---|---|---|---|---|---|
| 79 | System Map, Settings (persona table), and every page opened on its own | All, minimal | A page opened on its own reads the look only from this browser's storage (`prefs()` in `web/device.js`). It never asks the brain. A browser that did not open the hub first gets the theme's default (maximal). The motion test shows that the System Map turns, and the persona table is 3D. With `?quality=minimal` in the address, the map is still. | Get the device's settings from the brain (`/api/hub-devices/<name>/settings`) in `kit.js`, for every page. | High | min-system-map-laptop.png, min-settings-laptop-assistant.png, motion-sysmap2-a.png |
| 80 | Hub: the core | All, minimal | Idle, listening, thinking and speaking look the same: the core is still and keeps one color. Only offline (gray) and error (red) differ. Nobody can see that the assistant listens. DESIGN.md says the minimal core "changes color". | Give each state a still look: listening brighter, thinking with a dashed ring, speaking in the hot color. No motion is needed. | High | sheet-min-cores.png (top row maximal, bottom row minimal: idle, listening, thinking, speaking, offline, error) |
| 81 | Hub: the startup | Laptop, minimal | It takes 6.9 s from the press to the finished hub: a dim core, a scrambled title ("FX 1E/I P54") that decodes, and checks that type out. Minimal is the lightweight mode, so this is too long. | Show the title and the checks at once, then fade in the hub (about 1 s in all). | Medium | min-hubx-laptop-start-t30.png, sheet-min2.png |
| 82 | Hub: the startup | Laptop, full and maximal | It takes 9.4–9.5 s from the press to the finished hub. DESIGN.md says about 8 s or less, the unlock included. | Shorten the brake or the checks. | Low | — |
| 83 | Command Center (on its own and as a module) | Laptop, Pi, minimal | The 3.5 s opening (rings, lens flare, a beam of light, the sweep) plays in minimal. It skips only when the computer asks for reduced motion (`command-center-intro.js`). | Skip it in minimal too. Fade in the workspace. | Medium | min-command-center-laptop-t06.png |
| 84 | VR Hub | Laptop preview, minimal (from the code and the preview) | The preview confirms line 75: the network's lines, the glow and the moving rings stay in minimal. | See line 75. | Medium | min-xr-preview-laptop-hub.png |
| 85 | System diagram, Chat (in the hub) | Laptop, minimal | The system diagram's core still has a white-hot glow, and the chat's large core keeps its soft glow. DESIGN.md says minimal is flat, with no glow. | Draw a flat filled circle in minimal. | Low | min-hubx-laptop-system.png, min-hubx-laptop-chat.png |
| 86 | All `kit.css` pages | All, minimal | STOP has an 18 px red glow, and the status dots glow. These stay in minimal. | Remove the glows in minimal (a `q-minimal` class on the page, set from the device's look). | Low | min-teleop-laptop.png |
| 87 | Hub | Laptop, minimal | The still dot grid is very faint (the `line` color on near-black). On a projector it will not show, and the hub looks empty around the panels. DESIGN.md says minimal reads best on a projector. | Make the grid's dots a little brighter in minimal only. | Low | min-hub-laptop.png |
| 88 | Hub: the core | All, minimal | DESIGN.md says the minimal core is "a still circle". The page shows all the rings, still. I think the still rings are better: they keep the assistant recognizable. **(Overrules DESIGN.md → Quality levels, minimal.)** | Keep the rings. Change DESIGN.md to say "the rings, still". | Low | sheet-min-cores.png |

## What this review does not cover

Reduced and full are not reviewed yet. The pages that use `kit.css` look the same on every look, so lines 1–78 cover them. A review of reduced and full must check the parts that change: reduced's smaller network, no blur, no pulses and the persona table's plain buttons; full's network, pulses and core rings without the maximal extras; the System Map's motion and decoration at each level; and the startup (hyperspace or the video) at each level. Line 79 means that a page opened on its own shows maximal until it reads the device's look from the brain. Run those checks with `?quality=` in the address, or open the hub in the same browser first.
