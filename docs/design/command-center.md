# Command Center: the spec

The builder's spec (2026-11-25), for quick job 134. Follow `docs/design/DESIGN.md` for the look. The far-future parts (a 3D lab scene, gestures) are in `docs/plan/ideas.md` → "Far future".

## Overview
The Command Center is a page, only on the brain for now, to see and manage the lab's connected devices and screens. It feels like a monitor wall for the lab. Users see the devices and what is open on their screens, and arrange the screens in one virtual space. The first version is a 2D workspace. A 3D view can come later.

## Main tasks
1. See all connected devices and screens at once.
2. Select several devices or screens, and change a setting or the page they show, on all of them at once.
3. Focus on one device: see its screen or screens in detail, with its actions and modules.

**Highlight and focus are different.** Selecting an item highlights it, to arrange and select items in the workspace. Focusing opens a modal with the device's screens and its actions, pages and modules.

## Workspace and layout
- Show each connected device and its screens (the live device list, quick job 109).
- Users move screens and devices to new places in the virtual workspace.
- Users group several screens under one device. Group a device's monitors by itself where possible.
- Users give a screen a page or view, as with Open on….
- The virtual layout is separate from the real devices. Moving an item changes only its place in the workspace. Moving a window or its state between devices is a future idea.

## Screen previews
- A light preview of each connected screen, for about 20 screens (or as many as on demo day), without high load or lag in the page.
- The previews show what is open on each screen. They need not stream at full quality, but the best quality possible is good.
- Select a preview to highlight it. Focus on it to open the modal.

## Layout of the page
- Left: a list of devices, each with its screens under it. Center: the virtual workspace. Right: the Pages list on top and the inspector below it (the builder, 2026-11-26).
- **The Pages list:** every page in the system (the hub, Arm Control, Monitor, AI Control and the others, as in All Pages). It is compact (the builder, 2026-11-26: the list is long): small tiles with an icon and the short name, 3 in a row, in groups (for example robots, cameras and the hub's own pages), with a search. It leaves out the pages that cannot open on another screen (for example VR Hub, Phone Remote, All Pages and the Command Center itself). Its part collapses to one row, so the inspector gets the room. Tiles are also easier to hover over with a hand than thin rows. Drag a page onto a screen in the workspace, or onto a device or screen in the left list, to open it there (as Open on… does). Later, hand gestures with the webcam do the same: hover over a page, close the hand, move to a screen, open the hand (`docs/plan/ideas.md` → "Far future"). Build the drag so that a second kind of pointer can use it later.
- **The inspector:** the selected item's details, settings and actions; with several items selected, only what applies to all of them. The settings at the bottom of the page move here. With nothing selected, it says how to select.
- An item selected in a list is highlighted in the workspace, and an item selected in the workspace is highlighted in its list.
- Highlighting never opens the focus modal. Focus has its own action, for example a small icon.
- Below each preview: the device name (a little larger), the screen name, then the resolution (less prominent). The screen name is "Screen" and its number for now. Leave it out when the device has one screen.
- A search, and a way to show or hide items in the workspace.
- The screen previews keep their smaller sizes; they do not grow to fill the space (the builder, 2026-11-26: large previews looked wrong).
- No opening animation (the builder, 2026-11-27, quick job 164: it was clunky): the page unfolds from the hub's button as every module does. The last opening (a 1 s radar sweep over a circular grid, quick jobs 160, 161 and 163) is in `docs/archive/command-center-opening-2026-11-27/`.
- **Select multiple** shows when it is on: the button fills and reads "Selecting multiple" (quick job 169: the same size in both states; before, "Selecting multiple: On"), and the workspace gets a dashed edge (quick job 160).
- A device that is off is not shown (the builder, 2026-11-27, quick job 169; before, a dim card that lit up when it connected).
- Below the device list on the left: an activity list, newest first ("Pi 3 opened Arm Control", "so101-white connected", "STOP pressed").
- Use the same names as Open on…. When display names exist (quick job 132), show both.

## Device controls and the focus modal
- The focus modal shows the device's screens and its actions, pages and modules.
- Modules match the device, for example diagnostics and Arm Control for the Raspbot, Monitor for an arm. These are examples, not a fixed list. A module opens in a modal, as usual, or as its own page.
- On a device that is not selected: a ⚙ or ⋯ menu for its settings and actions.
- The controls include the drive permission (which devices may drive a real arm, today `drive_from` in `config/place.yaml`), the device's settings, and the screen and window actions.
- With as few words as possible, the design makes clear which actions change the real device and which change only the virtual workspace.

## Several items at once
- Select several devices or screens and apply a change to all of them.
- Show only the actions that apply to every selected item. Make clear when an action changes more than one device or screen.

## 2D and 3D
The 2D workspace is the first version and does every main task by itself. Keep the design open to a 3D view later. The hub’s separate **System Map** shows live connections in 3D (quick job 152).

## Order of the work
1. The 2D workspace for devices and screens.
2. Light previews, grouping, search, show and hide.
3. Highlight (for arranging and selecting several) and focus (the modal).
4. Give pages or views to screens, also to several screens at once.
5. The device controls and the related modules.
6. Keep the virtual layout separate from changes to real devices.
7. Keep the design open to a 3D lab scene and new ways to interact.

## Built (quick job 134, 2026-11-26)
The first version, at `/command-center` (All Pages; it opens only on the brain's own computer). How it works for the code: `docs/dev/protocol.md` → "The Command Center".
- **Items:** each device with the hub open (its monitors grouped under it by themselves), and each connected device of the live list (arms, cameras, raspbot1, the Quest).
- **Previews:** a drawing of what each screen shows (the start screen, the hub, or the page and its icon, and who sent it), from the brain's list. They are not pictures of the screen, so 20 screens cost almost nothing.
- **Real or only the workspace:** a button that changes the real device has the Open on… mark (two screens); a button that changes only the workspace has a dashed frame. The legend is above the workspace.
- **Grouping:** drag a screen onto another device to group it there, or onto empty space to put it on its own. "Ungroup" puts it back under its own device.
- **Modules in the focus modal:** an arm: its kind's Monitor (SO-101 or xArm), Arm Control, AI Control; raspbot1: Raspbot; a camera: Cameras; the Quest: Arm Control. Each opens in the Command Center, with "Own window".
- **Start (quick job 139):** **Start All** above the workspace starts every screen that shows the start screen; **Start** starts the highlighted ones. Each shows only while a screen waits on its start screen.
- **Settings in the focus modal:** the display name, the level of detail and the way in to voice (the sound until quick job 166: **M** replaces it). The other "This device" settings stay in ⚙ on that device.

## Built (quick job 148, 2026-11-26)
- **The left list:** each device, with the screens grouped under it (as in the workspace). A line joins the device's icon to each of its screens, and a screen under its device has one compact line ("Screen 2, Arm Control"; quick job 161: before, a screen looked like one more device, indented). A screen on its own has its own row.
- **The Pages list:** a tile for each page that can open on another screen, in three groups (Robots, Cameras, The hub; a new page goes in "Other"). "The Hub" closes what a screen shows. A press chooses the page for the inspector's **Open** (quick job 167: a press opens the page at once on the highlighted screens); a drag onto a screen or a device opens it there. ⌃ folds the list; the page remembers it.
- **The drag:** one carrier with four steps (start, move, drop, cancel) at screen coordinates. The mouse and touch use it through pointer events. A webcam hand can call the same steps later.
- **The inspector:** in place of the actions under the workspace. One device: its details, actions, modules and settings. One screen: what it shows, its resolution and its actions. Several items: only the actions for all of them.

## Built (quick job 149, 2026-11-26)
- **Zoom to fit:** the workspace zooms to fit its items again when an item comes or goes, or the page changes size. A pan or a zoom by hand stops that; **Fit** starts it again.
- **Devices that are off** (quick job 169 removed them: a device that is off is not shown): each device of the seen list (quick job 109) that is off now is a dim card with a dashed frame and no text, in the workspace and in the list. Since quick job 156, it sits below the connected devices, and it lights up once when it connects. The inspector shows when it was last seen.
- **The activity list:** under the device list, the newest event first, with its time. The brain keeps the last 100 events in memory: a device connected or disconnected, a screen opened the hub, a page, or went back to the hub, and STOP (the arms' pages and the Raspbot Control page).

## Built (quick job 140, 2026-11-26)
- **The way in:** on the brain's own hub, a **Command Center** panel under the top strip, in the middle above the core, as the ask box is below it (quick job 161; before, in the strip, where a long fact pushed it off the middle): a turning reticle and the name, with a light that passes now and then. A note at the top of the core shows under it. Other screens do not show it. It opens the Command Center as a module that unfolds from it. "Open the Command Center" by voice unfolds from it too.
- The radar opening in “Screen previews” replaced this opening in quick job 156, quick job 160 replaced that with a 1 s sweep, and quick job 164 removed the opening.

## Built (quick job 135, 2026-11-26)
- **Diagnostics in the modules:** every device's modules (the focus window and the inspector) have **Diagnostics**: the Diagnostics page for that device only. The Pages list has Diagnostics too (all devices).

## Built (quick job 166, 2026-11-27)
- **Mute, solo and cover:** each card and each row of the left list for a named computer or screen has a speaker icon (a label, not a button) with **M**, **S** and **C**, as on a mixing desk. Each device plays its own answers and greeting. **M** (red when on): nothing plays there (the answers, the greeting and the hub's own sounds), and its sounds play nowhere. **S** (amber when on): only the soloed devices play their own sounds; a few devices can be soloed. While a device is soloed, the **M** of the others is dim red ("Quiet"), except on a cover. **C** (green when on): the soloed devices' answers and greetings play there too, while a device is soloed; a few devices can be covers. **M** + **S**: the device's sounds play only on the covers (a device without speakers, or a phone that stays quiet). Mute wins over cover. Kept in each device's settings (`sound`, `solo`, `cover`). The Quest's own page keeps its own sound: no buttons.
- **The left list, more compact:** one line for each device (its device name after a display name, dimmer); no ⤢ in the list (it stays on the card). Above the list: **Hide all** / **Show all** (only the workspace; it replaces **Show all** above the workspace) and **Mute all** / **Unmute all**.

## Built (quick job 167, 2026-11-27)
- **A page opens at once:** a choice in a page list (the inspector, the focus window, the ⋯ menu) opens the page; there is no **Open** button. A press on a page tile opens it on the highlighted screens. The lists and the marked tile show what the screens show now, also after another device changed it.
- **All to the Hub:** above the workspace (quick job 168 replaced it with **All to the Start Screen**). Every screen goes back to the hub, except the screens that show Arm Control, Webcam Control, Raspbot, AI Control, Training or the Command Center.
- **The inspector, in order:** the name, the page, the sound (**M** and **S**, with what they mean now), the actions, the modules, the settings, the details.
- **The focus window, a grid:** the screens on the top row, left to right, each with its page list and buttons on its right. Under them, three equal columns: Modules, Facts, and Actions (with the sound and the settings).
- A device with no name shows as "Unnamed device" (before: "Unnamed screen").

## Built (quick job 168, 2026-11-27)
- **All to the Start Screen:** above the workspace, in place of All to the Hub. Every screen goes back to its start screen (the hub and the pages that only show information too), except the screens that show Arm Control, Webcam Control, Raspbot, AI Control, Training or the Command Center. **Start screen** in a screen's controls does the same for the highlighted screens.
- **No sound buttons without a name:** the sound settings are kept by device name. A device with no name says how to give it one (⚙ → This Device → Device Name) in place of **M** and **S**.

## Built (quick job 169, 2026-11-27)
- **Sound for every page:** a page with no device name has **M** and **S** too. The brain keeps them under its address key (`addr-127-0-0-1`), and only them.
- **The hub says "Muted":** a muted device shows "Muted" in red in its top strip.
- **The cards:** the display name, with the device name under it in smaller type. With no name: "Unnamed device", with its address key under it. Under each preview: "Screen 1", "Screen 2" and so on, then the resolution (the device's name is on the card's head).
- **Off devices:** not shown.
- **The panels:** the search is above the Devices list. Activity is shorter. A line between two panels changes their sizes: the Devices and the Pages columns' widths, Activity's height and the Pages list's height. The page remembers them; a double click puts one back. The centre is at most 72rem wide.
- **Select multiple:** the same size in both states ("Select multiple", "Selecting multiple").
