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
- **The Pages list:** every page in the system (the hub, Teleop, Monitor, AI Control and the others, as in All Pages). It is compact (the builder, 2026-11-26: the list is long): small tiles with an icon and the short name, 3 in a row, in groups (for example robots, cameras and the hub's own pages), with a search. It leaves out the pages that cannot open on another screen (for example VR Hub, Phone Remote, All Pages and the Command Center itself). Its part collapses to one row, so the inspector gets the room. Tiles are also easier to hover over with a hand than thin rows. Drag a page onto a screen in the workspace, or onto a device or screen in the left list, to open it there (as Open on… does). Later, hand gestures with the webcam do the same: hover over a page, close the hand, move to a screen, open the hand (`docs/plan/ideas.md` → "Far future"). Build the drag so that a second kind of pointer can use it later.
- **The inspector:** the selected item's details, settings and actions; with several items selected, only what applies to all of them. The settings at the bottom of the page move here. With nothing selected, it says how to select.
- An item selected in a list is highlighted in the workspace, and an item selected in the workspace is highlighted in its list.
- Highlighting never opens the focus modal. Focus has its own action, for example a small icon.
- Below each preview: the device name (a little larger), the screen name, then the resolution (less prominent). The screen name is "Screen" and its number for now. Leave it out when the device has one screen.
- A search, and a way to show or hide items in the workspace.
- The workspace zooms to fit its items, so a few devices get large previews (the builder, 2026-11-26).
- Devices seen before but off now show as dim cards, with no text on what to do; they light up when they connect.
- Below the device list on the left: an activity list, newest first ("Pi 3 opened Teleop", "so101-white connected", "STOP pressed").
- Use the same names as Open on…. When display names exist (quick job 132), show both.

## Device controls and the focus modal
- The focus modal shows the device's screens and its actions, pages and modules.
- Modules match the device, for example diagnostics and teleop for the Raspbot, Monitor for an arm. These are examples, not a fixed list. A module opens in a modal, as usual, or as its own page.
- On a device that is not selected: a ⚙ or ⋯ menu for its settings and actions.
- The controls include the teleop permission (which devices may drive a real arm, today `drive_from` in `config/place.yaml`), the device's settings, and the screen and window actions.
- With as few words as possible, the design makes clear which actions change the real device and which change only the virtual workspace.

## Several items at once
- Select several devices or screens and apply a change to all of them.
- Show only the actions that apply to every selected item. Make clear when an action changes more than one device or screen.

## 2D and 3D
The 2D workspace is the first version and does every main task by itself. Keep the design open to a 3D view later. 3D is not part of the first version.

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
- **Modules in the focus modal:** an arm: its kind's Monitor (SO-101 or xArm), Teleop, AI Control; raspbot1: Raspbot; a camera: Cameras; the Quest: Teleop. Each opens in the Command Center, with "Own window".
- **Start (quick job 139):** **Start All** above the workspace starts every screen that shows the start screen; **Start** starts the highlighted ones. Each shows only while a screen waits on its start screen.
- **Settings in the focus modal:** the display name, the level of detail, the way in to voice and the sound. The other "This device" settings stay in ⚙ on that device.

## Built (quick job 148, 2026-11-26)
- **The left list:** each device, with the screens grouped under it (as in the workspace). A screen on its own has its own row.
- **The Pages list:** a tile for each page that can open on another screen, in three groups (Robots, Cameras, The hub; a new page goes in "Other"). "The Hub" closes what a screen shows. A press chooses the page for the inspector's **Open**; a drag onto a screen or a device opens it there. ⌃ folds the list; the page remembers it.
- **The drag:** one carrier with four steps (start, move, drop, cancel) at screen coordinates. The mouse and touch use it through pointer events. A webcam hand can call the same steps later.
- **The inspector:** in place of the actions under the workspace. One device: its details, actions, modules and settings. One screen: what it shows, its resolution and its actions. Several items: only the actions for all of them.

## Built (quick job 149, 2026-11-26)
- **Zoom to fit:** the workspace zooms to fit its items again when an item comes or goes, or the page changes size. A pan or a zoom by hand stops that; **Fit** starts it again.
- **Devices that are off:** each device of the seen list (quick job 109) that is off now is a dim card with a dashed frame and no text, in the workspace and in the list. It keeps its place, and it lights up once when it connects. The inspector shows when it was last seen.
- **The activity list:** under the device list, the newest event first, with its time. The brain keeps the last 100 events in memory: a device connected or disconnected, a screen opened the hub, a page, or went back to the hub, and STOP (the arms' pages and the Raspbot page).

## Built (quick job 140, 2026-11-26)
- **The way in:** on the brain's own hub, a **Command Center** panel in the top strip, between the lab's name and the facts: a turning reticle and the name, with a light that passes now and then. Other screens do not show it. It opens the Command Center as a module that unfolds from it. "Open the Command Center" by voice unfolds from it too.
- **The opening** (about 3.5 s, in the style of the startup): a bright line opens the screen like an old TV; corner brackets close in and the tick ring sweeps around; two rings arrive from their own sides and lock with a flash and a thin ring of light; the core ignites with a lens flare and a shockwave that shows the grid; the title decodes and the real numbers type out (devices connected, screens, devices off now, events); a radar sweep goes around once; the screen opens from the middle, the reticle flies to the title, and the panels unfold outward, then the cards arrive one by one. Any press or key skips it. A screen set to reduce motion does not play it. Its sounds are the hub's own: in the hub, the hub plays them.

## Built (quick job 135, 2026-11-26)
- **Diagnostics in the modules:** every device's modules (the focus window and the inspector) have **Diagnostics**: the Diagnostics page for that device only. The Pages list has Diagnostics too (all devices).
