# The UI/UX review of 2026-11-26: the merged list

Three reviewers checked every page on the maximal and minimal looks: Claude Opus (O), Codex/GPT (C) and Gemini (G, from the code and the others' screenshots). Their reports and screenshots are in `docs/archive/ux-review-2026-11-26/`. This list merges them. The planning session checked the claims against the code (`main` at `c945940` and later) and left out the wrong ones (at the end). **(B)** = the builder asked for it. Reduced and full are not reviewed: the fixes for minimal and maximal must also look right on them.

The fix jobs are quick jobs 153 to 160 (`docs/plan/quick-jobs.md`). Each line names its job. After the fixes, the builder ticks each line in the real lab.

How bad: **H** = text is lost, a control is too small to use, or a page misleads. **M** = it looks wrong or is unclear. **L** = polish.

## 1. Shared parts (quick job 153: one session, before the others)
- [ ] H · O C G · Text on every `kit.css` page stops at 22 px (`clamp(12px, …, 22px)`), so pages look tiny on the 4K and the 32". Raise the top (about 40 px) or scale from the smaller side, as the hub does.
- [ ] H · O · `design.html` uses the class `btn` but never styles it: Diagnostics, Remove and Remove from the List are gray browser buttons in the device card and the Devices details. Add the kit's button style.
- [ ] H · O C G · Every `kit.js` page ignores the device's look (⚙ → Level of Detail). A page reads it only from this browser's storage, so it shows the theme's default. In minimal, STOP and the status dots still glow, and transitions still run. Read the device's look from the brain, set a `q-minimal`/`q-reduced` class, and remove glow and motion in minimal.
- [ ] H · O C G · Controls under 40 px on touch screens (STOP 36 px on the Pi; the Command Center's icons 12–24 px; Settings arrows and switches; Wake Word; System Map list; the power menu rows 28 px). Give every control a 44 px touch area on touch screens (DESIGN.md says 40; use 44).
- [ ] M · O G · "Held" looks like a warning: the 3D arm turns salmon pink, the ARM pill is amber, and the bar says "frozen: release grip". Keep the arm steel, add a muted rust ring or outline and the pause icon, use `--frozen` for the pill, and say "Held still" (the reason in the tooltip). Also in VR (`ArmHologram`).
- [ ] M · O C G · Joint names show as code (`shoulder_pan`). Show "Shoulder Pan" from one shared helper, with the code name in the tooltip. Teleop, the Monitors, AI Control, Webcam, Diagnostics, VR.
- [ ] M · O C G · Status values and content text are lowercase ("connected", "free", "not safe", "today"). This is quick job 53: do it here, with its rule and its test.
- [ ] M · O G · A device with no name shows as "127.0.0.1 (no device name)", and it overlaps other labels. Show "Unnamed screen"; the address only in the device card. Hub graph, Devices details, Command Center, System Map.
- [ ] M · O · One thing has many names ("rv-laptop" and "Rv Laptop"; "Monitor So101"; "Monitors" against "Monitor"). Take every page title from `PAGES`, and show device names as stored or the display name.
- [ ] M · O C · The "AI isn't set up" message shows key names and a 120-character file path to visitors, and on the Pi it runs off the screen. Say "Add an AI key to config/.env, then restart."; the path in the tooltip.
- [ ] H · G · A page opened by itself has no way back to the hub. Add ← Hub at the left of the bar, hidden in a module (choice 5).
- [ ] L · O G · "·" separates words in many lines (DESIGN.md: no dot separators). Use two lines or a comma.
- [ ] L · O G · Colours written in the code, not in `theme.yaml` (`persona-table.js`, `object-labels.js`, `arm-view.js`, `raspbot-view.js`, the hub's device card fill, the VR room in `xr-scene.js`). Move them to theme tokens.
- [ ] L · O · Rectangles next to cut-corner cards (the power menu, All Pages rows, Settings rows, Command Center tiles). Give them the cut corner.
- [ ] M · O C G · Wide screens: Settings, All Pages, Monitor, Training, Diagnostics, Wake Word and Cameras use a narrow column at the left. Use the width (a grid of cards), page by page in jobs 154–157.

## 2. The hub, the start screen and the power menu (quick job 154)
- [ ] M · O C G · (B) Power menu: the title "Power" in the title font; remove "lab-os stays on" and "asks first"; about 16 rem wide; a drop-down attached to ⏻ with a small notch, a cut corner and an icon on each row, as on Windows, Linux or macOS.
- [ ] M · O C G · (B) The shut-down confirmation in the same drop-down: the title font, "Shut down" a red filled button and "Cancel" beside it, the arm warning first, focus on Cancel.
- [ ] H · C G · Open on… opens at the far top left, away from its button. Attach it to Open on… as a drop-down, in the same style as the power menu.
- [ ] M · O C G · The module's ← Back at the top right becomes × (choice 2).
- [ ] M · C · Esc closes the whole module while Open on… or the Command Center's focus window is open, and Esc does not close the device card. Close the innermost thing first.
- [ ] M · O C G · (B) The All Pages icon is a chain link. Use a grid of four squares (the usual "all apps" icon).
- [ ] M · O · ⏻, All Pages and ⚙ are small dim icons. Make them larger, in the text colour, with a 44 px area.
- [ ] L · O C G · (B) The start screen: only "Safe to start." with the shield (change DESIGN.md → Startup too).
- [ ] M · O C G · (B) The start screen's lone "lab" and the top strip's "lab" with a pin: show the place's name ("AI Comp Lab") with the pin icon, or hide it while the place is the default one.
- [ ] M · O C G · The docked core covers module content (the Teleop Mode list, STOP). Keep its corner free in the module.
- [ ] M · O · Asking while the AI is off: nothing happens except a faint line. Show the error under the core (what broke, what still works).
- [ ] M · G · The chat has no Send button (touch screens with no keyboard). Add one at the end of the ask line.
- [ ] M · O C · The Current Project says "Step 2 of 12" and its details "6 of 13 steps done". Use one count.
- [ ] M · O · The 4K: the hub is a band in the middle; scale the panels and the strip with the screen.
- [ ] H · O C G · The Pi (800×480): the tool icons wrap to a row on the left; the hatch block covers the strip's words; the bottom log line crosses the frame; the Commits range buttons become tall squares; "List all" wraps; the device list runs under the log. Fix the Pi layout of the hub.
- [ ] H · G · The phone hub (`/?hub=1`): the top strip is 4 rows, and the ask box overlaps the module buttons' brackets. Fix the phone layout.
- [ ] M · O C · Text too small on a laptop (the Commits axis 8 px, the log's time 9 px, the device graph names 7 px, the System diagram legend 7 px, the startup checks 9 px). Keep text at 11 px or more.
- [ ] L · O · Small fixes: "AI Control" breaks onto two lines; the Commits bars fill part of the width and the first date is cut off ("ct 28"); the device card covers the Monitor button; Devices details: an empty "Motor power" column and "Connected: No" with "open in 2 windows"; module content starts 50 px right of the title; Current Project and AI Spend use 60 % of the width; Remove shows on connected devices.
- [ ] L · G · The verses run behind the top strip and the power menu. Keep them away from the strip, and dim them while a menu is open.
- [ ] M · O G · The System diagram shows the docked core and its own core at once. Hide the docked core there.
- [ ] H · O C G · Minimal: the core looks the same when idle, listening, thinking and speaking. Give each state a still look (listening brighter, thinking a dashed ring, speaking the hot colour). Keep the rings (choice 3).
- [ ] M · O C G · Minimal: the startup takes 6.9 s and types its checks. Show the title and the checks at once and fade in the hub (about 1 s). Full and maximal take 9.5 s (DESIGN.md: 8 s); shorten them.
- [ ] M · C G · Minimal: a module still blurs the hub (2 px), Open on… and Power blur 6 px, and the module opens with a 700 ms clip and a 750 ms core move. Use a plain fill and a short fade.
- [ ] L · O C G · Minimal: the hub core, the System diagram and the chat core still glow. Flat in minimal. Also the grid's dots are very faint on a projector: brighter in minimal. The hub rewrites one still SVG path 60 times a second (C): update it only when it changes.
- [ ] L · G · Minimal: the bottom trace runs through the ask box. End it at the box.

## 3. The robot pages (quick job 155)
- [ ] H · C · Teleop on the Pi: Desktop control scrolls STOP out of view. Keep STOP in view (also in minimal).
- [ ] M · O C G · Teleop, Webcam, AI Control and the SO-101 Monitor on the Pi: the drive controls, the joints or "What the AI did" are below the first screen. Put them beside a shorter 3D view on 800×480.
- [ ] M · O C · Teleop and Webcam on a laptop: long help paragraphs. Fold them ("How to drive"); hide Enter AR and Enter VR where there is no XR, and say it once in dim text (not amber).
- [ ] L · O G · Teleop: "Hand → arm" breaks onto three lines. Put the labels over the lists.
- [ ] H · G · Webcam: the gripper row and the footer are cut off in the 3D view card; "Speed" shows twice. Fit all six rows; one Speed row.
- [ ] M · C · Webcam: a refused camera says "Permission denied" with no next step. Say how to allow the camera.
- [ ] L · O C G · Monitor: the three cards use a short row at the top; make the previews larger; one form ("1 connected", "None connected").
- [ ] L · O C · xArm Monitor: "No xArm is connected" three times beside an empty grid. One message in the middle.
- [ ] L · C G · Raspbot Monitor: with no camera, give the status and the model more room; "Ultrasonic Distance" wraps.
- [ ] M · O · AI Control on the 4K: the callouts stay small. Scale them with the drawing. The Open readout has no unit (C).
- [ ] H · O C G · Training: long file paths run past the card. Lead with the missing file and the action; the path folded or wrapped.
- [ ] H · O · Training on the Pi: the two cards overlap.
- [ ] L · C G · Training: two identical "Start" buttons (name LeLab and LeRobot); the top chip amber and the list red for the same unplugged arm (one level).
- [ ] L · O C G · Cameras with no camera: one small line at the top left. A centered card with the camera icon and Check Again.
- [ ] H · O C G · Raspbot on a phone: the drive buttons 27 px and the speed slider 12 px (a phone the page does not detect gets the three-column layout), and 38 px on 844×390. Use a width breakpoint too, and 44 px buttons. Upright: keep the sideways controller and show "Turn your phone" (choice 4).
- [ ] M · C · Raspbot: nothing says that a drive button must be held. Add "Hold to drive".
- [ ] M · O · Raspbot: the middle of the drive pad is empty. Put STOP there.
- [ ] L · G · Raspbot: with no camera, Picture, Record and Labels look disabled with no reason. A "Camera offline" line.
- [ ] M · C · AR Teleop: the arm models have a fixed 55 % opacity and a white floor ring. Add a stronger cyan edge, and the ring in the primary colour.

## 4. Settings, All Pages, the Command Center and the other pages (quick job 156)
- [ ] M · O C G · (B) Settings on the 32": a large empty area at the right. A live preview and help panel there (choice 1).
- [ ] M · G · Settings: Display Name comes before Device Name but needs it. Put Device Name first.
- [ ] M · O · Settings: "Safety Limits and Shut Down" is always red. The warning icon in the main colour; red only for the Shut Down button.
- [ ] L · O G · Settings on the Pi: the search and the five tabs fill the first screen. One scrolling row of tabs with the search in it.
- [ ] L · O · Settings: "Teleop 1:1 Top Joint Speed" starts with "°/s.". Write "Degrees per second.".
- [ ] M · C · Settings: the persona table's unselected name looks disabled; "Chosen" is low in contrast; the two seats line up behind each other (G). Turn the view a little; clearer states.
- [ ] M · C G · Settings on minimal and reduced: the plain persona buttons have no greeting preview or Hear It Again. Add both.
- [ ] L · C · Settings → Level of Detail: "Theme" gives no value. Show "Theme (Minimal)".
- [ ] M · O C G · All Pages: one long list of "/path · text" rows. Use the Command Center's grouped tiles with the search; the page's one line under it.
- [ ] M · C · All Pages: Teleop promises "joint sliders" that Teleop does not have. Fix the one-line texts. Each button says only "Open": put the page name in its accessible label.
- [ ] H · O C G · The Command Center on the Pi: the device list is gone, and Pages and Activity fold to bars. Use tabs on small screens (Workspace, Devices, Pages, Inspector).
- [ ] H · O · The Command Center: Zoom to Fit puts all items in one row, so live screens are 110 px wide. Fit the live devices first; the off devices in a small row at the bottom.
- [ ] M · C · The Command Center: selecting needs a pointer, and multiselect names only desktop keys. Add a touch multiselect and keyboard selection. Tab leaves the focus window: keep focus in it.
- [ ] M · C G · The Command Center's opening: "Press any key to skip" has no touch way; add a Skip button. On minimal, skip the opening (O C G) and fade in.
- [ ] L · O C G · The Command Center: the focus window leaves the width empty (put the screen beside Facts); the Pages tiles' last row is cut off (a fade); the inspector's page list repeats the tiles; the opening's dark area does not fill the module (O).
- [ ] M · O · Diagnostics: `?device=` means "only this device" here and "this screen's name" everywhere else. Use `?show=`. The bar says "Connected 1, Off 7" but shows one card: say "Showing 1 of 8".
- [ ] M · C G · Diagnostics: the filter button is an unlabeled ⤢; "Connected" and "OK" in green (DESIGN.md: green only for teleop following); "No problem found" over fake readouts.
- [ ] M · O C G · System Map: the controls' help is small and dim, mouse words on a touchscreen, Reset View covers a node on the Pi. Larger help, touch words on touch screens, Reset View in a free corner.
- [ ] L · C G · System Map on minimal: the halos stay; screen previews overlap with 4 screens.
- [ ] M · O C G · Phone Remote: "Hold Talk" when there is no Talk button (say "Type below"); the placeholder is cut off; Send clears the text after an error (keep it); "Connected" means only the brain (say "Brain connected").
- [ ] M · C · Wake Word: the microphone error shows in the Train card. Show it beside Record, with how to allow the microphone. The steps make a 3 + 1 grid: use 2 × 2. "hey Jarvis" in lowercase (O).

## 5. VR and AR (quick job 157)
- [ ] M · O C G · The VR hub reads the look from the theme's default, not this headset's choice. In minimal the core still turns and glows, the network still pulses, and the 3,000-star jump still runs. Use the device's look in `xr-hub.js`, the core, the network, the stars and the modules.
- [ ] M · O G · The VR hub's modules differ from the flat hub's (no Cameras, no System Map; Training missing). Use `hub.modules`, and leave out what VR cannot show.
- [ ] M · O · The VR Devices panel says "1 of 15 linked", the flat hub "1 of 6 connected". The same list and words.
- [ ] M · C G · Back, Exit and ⏻ are in different places on the hub and in Teleop. One place.
- [ ] M · C G · AR: panels and thin text wash out over the room; the impact frame flashes white over the real room. Stronger panel fill in AR; skip the white flash in AR. "Left VR" after an AR session: say "Left AR" (C).
- [ ] M · G · VR: Back and ⏻ are plain rectangles; the power menu is 0.82 m wide. Cut corners, narrower.
- [ ] L · C · VR Devices: the rows get smaller as devices connect. Fixed rows and a way to page.
- [ ] L · O · VR: the Current Project title is cut off.
- [ ] L · G · `/xr` on a computer: "No VR here" stays on top, and Preview on This Screen is below. Make Preview the main button there.

## 6. The builder's design changes (quick jobs 158 to 160; first versions to iterate on)
- [ ] (B) · O C G · **Depth** (quick job 158): the hub, the modules and VR look flat. Put the core clearly in front when a module opens (scale it up a little, a dark halo under it); lift the panels' decoration a few pixels off its panel, with a slight parallax when the pointer moves; blur and dim the far network more. In VR: the core about 0.3 m in front of the panels, the decoration 3–5 cm in front of its panel, the rings 2–4 cm apart. Light, not shadow first (choice 6).
- [ ] (B) · O C G · **A 3D core** (quick job 159): more intentional and original. Start from `hub/web/xr/core.js` (three.js, the same rings): each ring tilted on its own axis like a gyroscope, lining up flat when it listens; each persona its own ring set. Its shape shows listening, thinking and speaking. Minimal keeps a flat core.
- [ ] (B) · O C G · **A black hole background** (quick job 160): `hub.background: network | black-hole`, on full and maximal only. A dark disc with a thin bright ring behind the core, the network's dots bent around it, dim, with the text still readable.

## The builder's choices (2026-11-26)
1. **Settings on wide screens:** not two columns. The right side shows a live preview of what the pointed-at or changed setting does (a small hub for Level of Detail, the core and the voice for the persona, the colours for the theme) and its longer help. A setting with no good preview shows only its help. (Quick job 156.)
2. **The module's Back button:** × at the top right, in place of ←. Also in the Command Center's focus window and in VR. (Quick jobs 154, 156, 157.)
3. **The minimal core:** the rings, still, with a still look for each state. DESIGN.md changes from "a still circle". (Quick job 154.)
4. **The Raspbot page on an upright phone:** keep the sideways controller, and show "Turn your phone" when the phone is upright. (Quick job 155.)
5. **A ← Hub button** at the left of the bar on every page opened by itself; hidden in a hub module. (Quick job 153.)
6. **Depth without cheap shadows:** use light, not shadow first. The layer behind dims and blurs (like a camera's focus), and the front item (the core) casts a faint light of its own colour on what is behind it. A soft dark halo only where that is not enough; DESIGN.md then allows it. (Quick job 158.)

## Left out (wrong or not useful)
- G: "no clock on the start screen": the clock is there (`#ign-clock`).
- G: "the `requestAnimationFrame` loops burn power in background tabs": browsers already pause them in hidden tabs.
- G: severity "high" for the module's Back button and for the VR room's colours: these are a choice and polish, not lost text or controls.
- C, G: "the Raspbot page rotates the whole interface" is on purpose (a sideways controller); it is choice 4, not a fault.
