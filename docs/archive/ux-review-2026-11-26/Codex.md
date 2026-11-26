# lab-os UX review, 2026-11-26

## Scope

Maximal on `main` at `c945940`. I used Chrome with the fake SO-101 and fake Raspbot at 800×480 (Pi), 1440×900 (laptop), and 1600×900 (Newline HDMI). I also used 390×844 (phone) and 844×390 for Raspbot in landscape. The browser emulated the viewport sizes, touch, and the iPhone user agent. The brain used a temporary place without API keys or physical devices. Screenshots are in [Codex/](Codex/).

I checked the screen routes in `PAGES`, the `/design` redirect, and the phone route at `/`. I opened the hub's cards, pages, details, power menu and confirmation, device list and card, and Open on…. I compared the hub with the approved concept and read the VR and AR code. I used taps, mouse drags, keys, and in-place viewport changes. I verified that dragging Cameras onto a test screen opened it there. Live camera frames, speech replies, training with hardware, physical displays and headset comfort remain unverified.

Each finding gives the page, size and look, problem, proposed fix, severity, and a screenshot where available. **High** means a primary control or task can fail. **Medium** means a task is harder to find or use. **Low** means readability or visual polish needs work. **Builder** marks a request from the builder. **Design override** marks a proposed change to `DESIGN.md`.

## Across pages

- **Teleop, Monitor, AI Control, Webcam Teleop and Raspbot — Pi, maximal:** STOP is 36 px high on the stand-alone pages. Give STOP a persistent position and a target of at least 44 px. **Medium.** [teleop-pi.png](Codex/teleop-pi.png), [monitor-pi.png](Codex/monitor-pi.png)
- **Hub modules with Open on… — Pi and laptop, maximal:** Escape closes the whole module while the Open on… menu is open. Close the menu first and return focus to Open on…. **Medium.** [open-on-pi.png](Codex/open-on-pi.png)
- **Hub, Phone Remote, Settings — Pi, laptop, Newline and phone, maximal:** The visitor sees API key names and a server file path when the assistant is unavailable. Show a short visitor message and put setup details in Settings or Diagnostics. **Medium.** [hub-pi.png](Codex/hub-pi.png), [remote-iphone-send.png](Codex/remote-iphone-send.png)
- **Teleop, AI Control, Diagnostics and SO-101 Monitor — Pi and Newline, maximal:** Joint captions expose identifiers such as `shoulder_pan`, and status chips use lowercase fragments. Use “Shoulder pan” and sentence case for visible captions. **Low.** [diagnostics-pi.png](Codex/diagnostics-pi.png), [monitor-so101-newline.png](Codex/monitor-so101-newline.png)
- **Hub and stand-alone pages — Newline, maximal:** Much of the interface text stays close to laptop size even when the page has room. Add a few shared text sizes for viewing at a distance. **Medium.** [settings-newline.png](Codex/settings-newline.png), [monitor-newline.png](Codex/monitor-newline.png)
- **Hub and desktop modules — all sizes, maximal, Builder, Design override:** Most decoration reads as part of the same flat surface. Put selected callout brackets on a foreground layer and place the docked core in front of modules. **Low.**
- **Hub background — all sizes, maximal, Builder, Design override:** The builder wants an alternative to the network. Try a dark black-hole background and check that it preserves text contrast. **Low.**

## Startup, hub, and power

- **Startup — Pi, laptop and Newline, maximal, Builder, Design override:** The safety line repeats the meaning of “Safe to start.” Keep the shield and “Safe to start.” **Low.** [startup-pi.png](Codex/startup-pi.png)
- **Startup — Pi, laptop and Newline, maximal, Builder, Design override:** The footer says “lab” with no label or icon. Remove the venue label or add a pin and an understandable venue name. **Low.** [startup-pi.png](Codex/startup-pi.png)
- **Startup motion — Pi, maximal:** Two frame intervals exceeded 50 ms in the headless Chrome sample. The longest was 167 ms. Profile the same transition on the physical Pi and reduce the work in its slowest frame. **Low.**
- **Hub status strip — Pi, maximal:** The tool icons wrap to the left while the status facts stay on the right. Give the controls one dedicated row so the power icon and its menu stay together. **Medium.** [hub-pi.png](Codex/hub-pi.png)
- **Hub — Pi, maximal:** The bottom activity line crosses the bright screen border and cuts off long text. Keep the line inside the frame and end it with a visible ellipsis. **Low.** [hub-pi.png](Codex/hub-pi.png)
- **Hub — Pi, maximal:** The device count, the diagram button and “List all” wrap awkwardly under Devices. Give the count its own row and align both actions below it. **Low.** [hub-device-list-pi.png](Codex/hub-device-list-pi.png)
- **Hub device card — Pi, maximal:** Escape leaves the device card open. Close the card with Escape and return focus to the device. **Medium.** [hub-device-card-pi.png](Codex/hub-device-card-pi.png)
- **Hub device card — all sizes, maximal:** The card fill uses a fixed RGB value even when the theme changes. Derive the fill from the background token and keep its opacity. **Low.** [hub-device-card-pi.png](Codex/hub-device-card-pi.png)
- **Hub — all sizes, maximal, Builder:** The chain icon for All Pages suggests a connection. Use a page stack or a list icon. **Low.** [hub-pi.png](Codex/hub-pi.png)
- **Assistant core — all sizes, maximal, Builder, Design override:** The core looks like rings on one plane. Give it a distinct 3D shape and make the shape communicate listening, thinking, and speaking. **Low.** [hub-pi.png](Codex/hub-pi.png)
- **Power and shutdown confirmation — all sizes, maximal, Builder:** The headings use the small menu font. Use the display font for both headings. **Low.** [power-pi.png](Codex/power-pi.png), [power-confirm-pi.png](Codex/power-confirm-pi.png)
- **Power — all sizes, maximal, Builder:** “lab-os stays on” and “asks first” widen the menu. Remove both labels and size the menu to its action names. **Low.** [power-pi.png](Codex/power-pi.png)
- **Power — Pi, laptop and Newline, maximal, Builder:** The menu floats away from the button. Anchor a cut-corner dropdown to the power icon and align it when the header wraps. **Medium.** [power-pi.png](Codex/power-pi.png)
- **Shutdown confirmation — Pi, laptop and Newline, maximal, Builder:** The confirmation replaces the floating menu and puts focus on Shut down. Keep it anchored to the power icon. Give Cancel initial focus and keep the arm warning above the actions. **Medium.** [power-confirm-pi.png](Codex/power-confirm-pi.png)
- **Power and shutdown confirmation — Pi, maximal:** The tested rows are 28 px high. Increase their tap targets to at least 44 px. **Medium.** [power-confirm-pi.png](Codex/power-confirm-pi.png)

## Hub details and conversation

- **Current Project — Pi, maximal:** The hub shows “Step 2 of 12,” and its details count 13 steps. Use the same count in both views and say whether step 0 counts. **Low.** [hub-pi.png](Codex/hub-pi.png), [module-project-pi.png](Codex/module-project-pi.png)
- **AI Spend — Pi, maximal:** The budget chart and date labels are tiny despite the space below them. Stack the amount and the chart so the date labels can use a larger size. **Low.** [module-spend-pi.png](Codex/module-spend-pi.png)
- **Commits — Pi, maximal:** The 30-day chart shows a count above every active bar, including several near the baseline. Label the highest bar and the current day. Reveal other counts on focus or tap. **Low.** [module-commits-pi.png](Codex/module-commits-pi.png)
- **Devices — Pi, maximal:** Each connected row has a gray “Remove” button even though removal applies to devices that are off. Hide the unavailable action and use the shared button style where it applies. **Low.** [module-devices-pi.png](Codex/module-devices-pi.png)
- **System Diagram — Pi, maximal:** The diagram scales its labels and legend down with the whole drawing. Keep the legend at a readable size and add fit and zoom controls. **Medium.** [module-system-diagram-pi.png](Codex/module-system-diagram-pi.png)
- **Conversation — Pi, maximal:** The large core uses nearly half the module while the ask field has a small placeholder. Dock the core above the conversation and make the composer easier to read. **Medium.** [module-conversation-pi.png](Codex/module-conversation-pi.png)

## Teleop

- **Teleop — Pi, maximal:** Selecting Desktop control scrolls the page to its controls and captures the pointer. STOP is entirely above the viewport while the fake arm accepts keyboard control. Keep STOP in view and retain the X shortcut. **High.** [teleop-drive-pi.png](Codex/teleop-drive-pi.png)
- **Teleop — Pi and phone, maximal:** The 3D view and readings fill the first screen. The only available drive option is below them. Put the available drive action and its input requirements above the model. **Medium.** [teleop-pi.png](Codex/teleop-pi.png), [teleop-phone.png](Codex/teleop-phone.png)
- **Teleop — laptop and Newline, maximal:** Disabled AR and VR actions and a long Quest paragraph compete with the PC action. Show a compact headset note on desktop and put headset instructions in Controls. **Low.** [teleop-newline.png](Codex/teleop-newline.png)

## Monitor and robot monitors

- **Monitor — laptop and Newline, maximal:** Three narrow cards leave the right half and most of the bottom empty. Increase the live preview area and make each robot state legible at a distance. **Low.** [monitor-newline.png](Codex/monitor-newline.png)
- **SO-101 Monitor — Pi, maximal:** The joint readings start near the bottom of the viewport, below the full-width model. Put the readings beside a shorter view at 800×480. **Medium.** [monitor-so101-pi.png](Codex/monitor-so101-pi.png)
- **xArm Monitor — Pi and Newline, maximal:** An empty floor grid and enabled model selector take most of the space when the arm is absent. Put the disconnected state in the center and show the selector when a model can display an arm. **Low.** [monitor-xarm-newline.png](Codex/monitor-xarm-newline.png)
- **Raspbot Monitor — phone and Newline, maximal:** The camera area remains dominant with no feed, and the model and status get a narrow column. Give status and the model more room when the camera is unavailable. **Low.** [monitor-raspbot-phone.png](Codex/monitor-raspbot-phone.png), [monitor-raspbot-newline.png](Codex/monitor-raspbot-newline.png)

## AI Control

- **AI Control — Pi, maximal:** The arm plot takes the first screen. “What the AI did” and setup are below it. Keep the latest tool activity or the idle message next to the plot at compact sizes. **Medium.** [ai-pi.png](Codex/ai-pi.png)
- **AI Control — Newline, maximal:** The Open readout shows 36 with no unit. Label it “Gripper open” and add the percent sign. **Low.** [ai-newline.png](Codex/ai-newline.png)

## Training

- **Training — Pi, laptop and Newline, maximal:** Full calibration paths make it hard to scan the failed checks. Lead with the missing file and the action. Put the path in expandable details. **Medium.** [training-newline.png](Codex/training-newline.png)
- **Training — Pi, maximal:** The two sections have identical Start and Check again actions. Identify LeLab and LeRobot in the action names so the selected workflow is clear. **Low.** [training-pi.png](Codex/training-pi.png)

## Webcam Teleop and Cameras

- **Webcam Teleop — Pi, maximal:** The empty camera and 3D view push Start webcam control and its status out of the first screen. Put the start action and status above both panels. **Medium.** [webcam-pi.png](Codex/webcam-pi.png)
- **Webcam Teleop — Pi, maximal:** The camera permission error repeats “Permission denied” without giving a recovery step. Tell the user how to allow the camera and retry. **Medium.** [webcam-camera-denied-pi.png](Codex/webcam-camera-denied-pi.png)
- **Cameras — Pi, laptop and Newline, maximal:** The empty state is a small plain line in a large dark area. Use a titled empty state with a camera icon and a clear connection instruction. **Low.** [cameras-newline.png](Codex/cameras-newline.png)

## Raspbot

- **Raspbot — 390×844 iPhone emulation, maximal:** The page rotates the whole interface 90° and shows no instruction. Provide a portrait layout or tell the user to rotate before they reach the controls. **Medium.** [raspbot-iphone-portrait.png](Codex/raspbot-iphone-portrait.png)
- **Raspbot — 844×390 iPhone emulation, maximal:** Direction buttons are 38 px wide and the speed track is 46 px long. Give the drive pad three 44 px targets and a wider speed row. **Medium.** [raspbot-iphone-landscape.png](Codex/raspbot-iphone-landscape.png)
- **Raspbot — 390×844 with the desktop user agent, maximal:** The three-column layout shrinks the direction buttons to 27 px and the speed input to 12 px. Use a viewport breakpoint as well as phone detection. **Medium.** [raspbot-phone.png](Codex/raspbot-phone.png)
- **Raspbot — Pi and phone, maximal:** The arrow grid gives little visible guidance that each control requires a hold. Add “Hold to drive” beside Drive and put the keyboard instructions beside the pad on desktop. **Medium.** [raspbot-pi.png](Codex/raspbot-pi.png)

## Wake Word

- **Wake Word — Pi, maximal:** The wake-word selector is 31 px high and the record actions are 38 px high. Give all three controls at least 44 px of touch height. **Medium.** [wake-word-pi.png](Codex/wake-word-pi.png)
- **Wake Word — Pi, maximal:** The permission error appears in the Train card after Record fails in another card. Show the error beside Record and tell the user where to allow the microphone. **Medium.** [wake-word-mic-denied-pi.png](Codex/wake-word-mic-denied-pi.png)
- **Wake Word — laptop and Newline, maximal:** A three-column layout places the fourth step under step 1. Use a two-by-two layout or a single horizontal sequence when each step fits. **Low.** [wake-word-newline.png](Codex/wake-word-newline.png)

## Phone Remote

- **Phone Remote — phone, maximal:** The page says “Hold Talk” when the Talk button is hidden. Change the instruction to “Type below” when voice is unavailable. **Medium.** [remote-iphone-send.png](Codex/remote-iphone-send.png)
- **Phone Remote — phone, maximal:** Send clears the draft when the assistant returns an error. Keep the text in the input so the user can retry or copy it. **Medium.** [remote-iphone-send.png](Codex/remote-iphone-send.png)
- **Phone Remote — Pi and phone, maximal:** “Connected” only means the brain answered, even when voice or chat is unavailable. Label the indicator “Brain connected” and show assistant availability beside the input. **Low.** [remote-phone.png](Codex/remote-phone.png)

## Command Center

- **Command Center — Pi and phone, maximal:** The compact layout stacks Devices, workspace, Pages and Inspector. A user cannot see the page tiles and their drop targets together on the first screen. Put the device list and inspector in switchable panels and keep the workspace visible. **Medium.** [command-center-resized-pi.png](Codex/command-center-resized-pi.png), [command-center-phone.png](Codex/command-center-phone.png)
- **Command Center — Pi and phone, maximal:** Focus and Hide targets shrink to 24 px in the device list and about 16 px on fitted workspace cards. Keep action hit areas at least 40 px even when the preview shrinks. **Medium.** [command-center-pi.png](Codex/command-center-pi.png)
- **Command Center — Newline, maximal:** Tab moves to a background Hide button while the device focus dialog is open. Move focus into the dialog, keep it there, and return it to Focus on close. **Medium.** [command-center-focus-newline.png](Codex/command-center-focus-newline.png)
- **Command Center — Pi, laptop and Newline, maximal:** Device and screen selection requires a pointer. The only multiselect instruction names desktop modifier keys. Add keyboard selection and a visible touch multiselect action. **Medium.** [command-center-newline.png](Codex/command-center-newline.png)
- **Command Center inside the hub — Newline, maximal:** Escape closes both the focused device and the entire Command Center. Let the inner dialog consume Escape first. **Medium.** [command-center-more-newline.png](Codex/command-center-more-newline.png)
- **Command Center — Newline, maximal:** A one-screen focus dialog leaves most of the width empty above Facts. Put the screen and its open action beside Facts and Modules. **Low.** [command-center-focus-newline.png](Codex/command-center-focus-newline.png)
- **Command Center — Pi and Newline, maximal:** “Press any key to skip” gives no touch instruction and disappears with the animation. Add a visible Skip control and focus it when the opening starts. **Medium.** [module-command-center-pi.png](Codex/module-command-center-pi.png)

## Diagnostics

- **Diagnostics — Pi, maximal:** “No problem found” sits over fake device readouts and unread motor values. Say “No problems reported” and add a separate “Motor readings unavailable” status. **Low.** [diagnostics-pi.png](Codex/diagnostics-pi.png)
- **Diagnostics — Pi, maximal:** The unlabeled 34 px filter button uses the same expand icon as a modal. Give it a visible “Only this device” label and a larger hit area. **Medium.** [diagnostics-pi.png](Codex/diagnostics-pi.png), [diagnostics-filter-pi.png](Codex/diagnostics-filter-pi.png)

## System Map

- **System Map — Pi and phone, maximal:** The gesture legend uses small text at 60% opacity. Make a high-contrast Controls button that opens a short list for touch or mouse. **Medium.** [system-map-pi.png](Codex/system-map-pi.png), [system-map-phone.png](Codex/system-map-phone.png)
- **System Map — Pi and phone, maximal:** Map labels are about 15 px high and list buttons are 32 px high. Keep the 3D labels small and enlarge the corresponding list targets to 44 px. **Medium.** [system-map-phone.png](Codex/system-map-phone.png)

## Settings

- **Settings — Newline, maximal, Builder:** The rows stop short of the right edge, and their controls stop well before the rows end. Center the settings area or move the controls toward the right edge of each row. **Low.** [settings-newline.png](Codex/settings-newline.png)
- **Settings — Pi and phone, maximal:** Search has a 26 px input and switches have 30 px targets. Give both controls a 44 px touch target. **Medium.** [settings-pi.png](Codex/settings-pi.png), [settings-phone.png](Codex/settings-phone.png)
- **Settings, Persona — Newline, maximal:** The unselected persona's name and outline are dim enough to look disabled. Give each selectable name a readable button treatment with focus and hover states. **Medium.** [settings-persona-newline.png](Codex/settings-persona-newline.png)
- **Settings, Persona — Newline, maximal:** The preview can say “Everything is running” directly above the voice setup error. Keep the sample greeting and label it as an example. Show whether audio is available next to Hear It Again. **Low.** [settings-persona-preview-newline.png](Codex/settings-persona-preview-newline.png)

## All Pages

- **All Pages — Pi, laptop and Newline, maximal:** All 19 entries are in one list. Put a short search above the list and group related pages. **Medium.** [pages-pi.png](Codex/pages-pi.png)
- **All Pages — Pi and Newline, maximal:** Teleop promises joint sliders, but Teleop shows desktop key modes and a speed slider. List the current input methods. **Medium.** [pages-pi.png](Codex/pages-pi.png), [teleop-newline.png](Codex/teleop-newline.png)
- **All Pages — Pi and laptop, maximal:** Each control says “Open,” so the buttons have identical accessible names. Include the page name in each button's accessible label. **Low.** [module-pages-pi.png](Codex/module-pages-pi.png)

## VR Hub and VR Teleop

- **VR Hub and Teleop — headset, maximal, from the code:** The hub module tab and Teleop place Back and Exit in different positions. Keep one consistent location in reachable view. **Medium.** `xr.html`, `xr/hub.js`, `xr/teleop-panel.js`
- **VR Hub, Devices — headset, maximal, from the code:** The details canvas shrinks every row as more devices connect. Use fixed-height text rows and a way to advance the list. **Medium.** `xr/panels.js`
- **VR Hub — headset, maximal, from the code:** The core and network read the theme default directly. Read the current device's selected look and reduced-motion preference before building the scene. **Medium.** `xr/core.js`, `xr/network.js`

## AR Hub and AR Teleop

- **VR and AR hub — headset, maximal, Builder, Design override, from the code:** Callouts and detail pages use flat canvas planes. Bring a few semantic elements forward in depth while keeping the text on a stable and readable plane. **Low.** `xr/hub.js`, `xr/draw.js`
- **AR Hub — headset, maximal, from the code:** Leaving the AR session displays “Left VR.” Show “Left AR” for a passthrough session. **Low.** `xr-hub.js`
- **AR Hub — headset, maximal, from the code:** Passthrough clears the background, while labels use the same dim palette as VR. Add a local contrast surface behind text that appears over the room. **Medium.** `xr-hub.js`, `xr/draw.js`, `xr/hub.js`

- **AR Teleop — headset, maximal, from the code:** Both arm models use a fixed opacity of 55% in passthrough. Keep the arm translucent and give its outline a stronger edge so it stays visible over the real arm. **Medium.** `xr-scene.js`

## Minimal review

Same commit, fake devices and viewport sizes as the maximal pass. I set the temporary theme default to Minimal so that stand-alone pages also received it. I repeated the page and module sweep, checked the `/design` redirect, and resized every stand-alone screen page in place. Screenshots are in [Codex/minimal/](Codex/minimal/).

The hub showed a still dot grid, stopped its idle rings, and removed the verses. Settings used the plain Persona buttons. The System Map stopped its idle orbit and still responded to input. The 60 stand-alone viewport checks kept the same scroll bounds as maximal. The issues below are new in minimal or affect how minimal works. The maximal findings still apply where the controls and layout stayed the same.

### Across pages

- **Hub modules — Pi, minimal:** Opening a module still blurs the hub by 2 px. Open on… and Power still blur the area behind them by 6 px. Use an opaque fill and a short fade when the effective look is Minimal. **Medium.** [module-pages-pi.png](Codex/minimal/module-pages-pi.png), [open-on-pi.png](Codex/minimal/open-on-pi.png)
- **Hub modules — Pi, minimal:** The opening still takes a 700 ms clip transition, and the core travels to its dock for 750 ms. Show the controls at once and use a short fade for the panel and dock. **Medium.** [module-settings-pi.png](Codex/minimal/module-settings-pi.png)
- **Stand-alone pages and their hub modules — Pi, laptop and Newline, minimal:** The shared page styles keep glowing status dots and the STOP halo. Apply the effective look in the shared styles and keep STOP prominent with its red fill and outline. **Low.** [monitor-pi.png](Codex/minimal/monitor-pi.png), [module-teleop-pi.png](Codex/minimal/module-teleop-pi.png)

### Startup and hub

- **Startup — Pi, minimal:** A second after a tap, the instructions have faded and the hub is still hidden. Show an immediate “Starting” state or open the hub with a short fade. **Medium.** [startup-after-press-pi.png](Codex/minimal/startup-after-press-pi.png)
- **Startup — Pi, minimal:** Minimal replaces hyperspace with a multi-step assembly. Rings still ease in and the checks type out one character at a time. Show the checks as static text and shorten the transition to the hub. **Medium.** [startup-assemble-pi.png](Codex/minimal/startup-assemble-pi.png)
- **Hub while idle — Pi, minimal:** The hub rewrote the same static SVG path 60 times in one second. Update the path when the look changes so the idle screen does less work. **Low.**
- **Hub core — Pi, minimal:** The center still uses a bright radial gradient with five visible ring layers. Use the flat status circle from the minimal design. **Low.** [hub-settled-pi.png](Codex/minimal/hub-settled-pi.png)

### System Diagram and System Map

- **System Diagram — Pi, minimal:** The diagram stops its pulses but retains a bright center halo and glowing rings. Use solid strokes and a flat center in Minimal. **Low.** [module-system-diagram-pi.png](Codex/minimal/module-system-diagram-pi.png)
- **System Map — Pi, minimal:** The core and screen previews retain halos after the scene stops moving. Remove the halos in Minimal and keep selection visible with a high-contrast outline. **Low.** [system-map-after-input-pi.png](Codex/minimal/system-map-after-input-pi.png)

### Command Center

- **Command Center — Pi, minimal:** The opening still plays a bright sweep and animated brackets. It skips only when the operating system requests reduced motion or the user intervenes. Apply the effective look so Minimal opens the workspace with a short fade. **Medium.** [command-center-intro-pi.png](Codex/minimal/command-center-intro-pi.png)

### Teleop

- **Teleop — Pi, minimal:** Desktop control still scrolls STOP above the viewport. Keep STOP visible while the fake arm accepts keyboard input. **High.** Reproduced from maximal. [teleop-drive-pi.png](Codex/minimal/teleop-drive-pi.png)

### Settings

- **Settings, Persona — Pi, minimal:** The plain buttons save a choice directly and give no way to hear its voice first. Add a plain Preview action for each persona. **Low.** [settings-persona-plain-pi.png](Codex/minimal/settings-persona-plain-pi.png)
- **Settings, Level of Detail — Pi, minimal:** “Theme” is selected when Minimal is the theme default, and the row gives no effective value. Show “Theme (Minimal)” when the device follows the default. **Low.** [settings-pi.png](Codex/minimal/settings-pi.png)

### VR and AR

- **VR Hub — headset, minimal, from the code:** The core still rotates and breathes, and the network still turns and sends pulses. Share the desktop's minimal motion choice with the immersive scene. Keep head tracking active and remove decorative motion. **Medium.** `xr/core.js`, `xr/network.js`
- **AR Hub — headset, minimal, from the code:** The core and network still use additive glow over passthrough. Use a flat core and static markers in Minimal so the room stays legible. **Medium.** `xr/core.js`, `xr/network.js`, `xr-hub.js`

### Next looks

Full and reduced still need checks for their own motion, blur, contrast, transitions, System Map cues, Persona controls, and any resulting layout or touch changes.
