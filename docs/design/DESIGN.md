# Lab JARVIS: design language

**In one line:** a calm, dark control room. Thin cyan light-lines float in front of a slowly drifting network of dots. They draw themselves in, turn slowly while idle, and get bright only where something is actually happening.

The numbers (colors, fonts, sizes, timings) live in `config/theme.yaml`. This page says what they mean and how to use them. **Everything here is meant to be swapped easily:** colors, fonts, layout, how busy the hub is, how alerts look, each one a single setting in the theme. The theme is the same for every persona; a persona only changes the assistant's picture, voice, lines and sounds.

A clickable concept of all of this exists as a private artifact (the "Lab JARVIS Hub" concept page, built in the design session); it's a sketch, not the hub's code.

## Colors
Dark first. One main color carries almost everything; the warm colors are kept for things that need a human.

| Token | Color | Use it for |
|---|---|---|
| `background` | near-black `#05080b` | Behind everything. Never pure gray, never a gradient fog. |
| `surface` | dark teal `#0b161c` | Panel fills, drawn see-through (about 8%) so the layers behind show. |
| `line` | dim teal `#1f3d48` | Quiet structure: grids, idle frames, the background network. |
| `primary` | cyan `#29d4ff` | The main color: active lines, rings, the assistant, buttons. |
| `hot` | white-hot `#eafcff` | The bright core of the brightest things only (center of the assistant, a pulse, a selected item). |
| `text` / `text_dim` | `#d4eef5` / `#6d8c96` | Main text / labels. White with a hint of cyan, never pure white. |
| `accent` | amber `#ff9a2e` | Warning: busy, waiting. |
| `danger` | aggressive red `#ff2436` | Critical: a person must act. Rare, so it hits hard. |
| `offline` | neutral gray `#56636a` | Offline, disabled, not connected. |
| `frozen` | muted rust `#7a1d00` | An arm holding still (dead-man stop). |
| `ok` | green `#3ee07f` | Only for "engaged / following" in teleop. Not a decoration color. |

About 90% cyan and dark, under 10% amber, red only when something is wrong.

**How serious is it?** Never mixed up:
| Level | Looks like | Examples |
|---|---|---|
| Normal | cyan, glowing | running, connected, idle |
| Held | muted rust, pause icon, no glow, no pulse: calm | arm frozen because the clutch is released (the safety system working, not a problem) |
| Offline | gray, dim, **no glow** | AI offline (no internet), robot not plugged in |
| Warning | amber warning triangle, slow pulse | busy, waiting for the clutch, battery low |
| Critical | red warning triangle, harsh: fast pulse (1.5 per second), a short shake when it starts, a red glow around the screen edge, an urgent sound | error, emergency stop, lost connection while moving |

**How far an alert spreads** is a setting (`alerts.mood`): `local` = only the affected thing changes color; `room` = the whole screen shifts mood, Iron Man style (rings, network and edges turn amber or red).

**Changing the main color** is one edit: `primary`. `surface`, `line`, `hot` and `text` carry a slight cyan tint; nudge them toward the new hue to match.

## Lines, shapes, icons and glow
- **Lines are thin.** Hairline (1 px) for structure, 2 px for active things, 4 px for the few key arcs.
- **Glow = a sharp bright line plus a soft halo.** The brightest things get a white-hot center fading to cyan (like a neon tube). **Only active things glow**; structure lines never do.
- **Corners are cut, not rounded.** 45° chamfers, corner brackets, small dots at the ends of lines.
- **The shape vocabulary:** segmented rings, tick marks, reticles, hexagons, chevrons, dashed lines ending in a dot, diagonal hatching, `+` marks at grid crossings.
- **Icons instead of words** where the meaning is obvious: warning triangle, pause (held), globe (internet), chip (AI), pin (venue), person (persona), hand (teleop), screen (monitor), speech box (chat). Line icons drawn like everything else (same stroke, no fills).
- **Callouts:** a thin line with an elbow, from a thing to its label (arm joints → their names and angles), Hydra-style.
- **Connecting traces** run from the assistant to each panel with 45° bends and **end exactly on the panel's edge**, with a dot at each end.
- **Panels:** cut-corner outline, see-through fill, no drop shadows. **A value and an icon, not a sentence:** a coin icon and `$0.00/20` over a meter, not "AI spend this month … of the $20.00 budget". The full sentence goes in the tooltip.
- **Fewer words everywhere:** buttons are an icon and one word (no subtitles); chat has no "You" / "Assistant" labels (the side of the screen says who); no numbers or labels on decorative rings.
- **The screen frame** isn't a plain rectangle: cut corners, a raised tab in the middle of the top and bottom edges, notches on the sides, bright brackets on the corners and tabs.

## Hub layout
**The core** is the assistant's picture: the rings around a glowing center. It sits **exactly in the middle of the screen** (the layout is symmetric around it), and the startup and hyperspace jump are centered on it.

Two layouts, one setting (`hub.layout`):
- **launcher** (default): the core big in the middle, module buttons left and right of it. Each button unfolds its module full-screen. The sides hold **panels of real project facts**: current focus progress, AI spend against the budget, commits per day, connected devices.
- **panels:** modules on the left, the chat on the right, the arm's joint readouts and the typed log at the bottom.

In both: **busy at the edges, calm in the middle**; how busy is `hub.density` (`sparse`, `busy-edges`, `dense`).

**Modular:**
- **Buttons come from a list** (`hub.modules`), in order, alternating left and right of the core so it stays balanced. Any number works, **including none**.
- **Chat is not a module.** It belongs to the core and is always there: tap the core, its small chat tab, or **just start typing** anywhere (the chat opens with your letters in it). With no modules the hub is the core, its chat and the fact panels.
- **The device panel takes any number of devices.** As a graph, devices sit evenly around the brain; past six, names move into tooltips. As a compact row, one icon per device, lit when connected. A small toggle on the panel switches between them (`hub.devices_view`). The header shows `connected/total`.

**The core never disappears.** When a module opens, the core flies along with it instead of fading with the hub:
- in **chat** it sits full size beside the conversation (left of it; above it on a portrait screen), so listening, thinking and speaking stay visible, and network pulses still flow into it;
- in **other modules** it shrinks into the bottom-right corner and keeps reacting (a voice reply, an alert).

**Chat:** your messages on the right in a box with broken edges (bright corners, gaps in the sides); the assistant on the left, its hexagon mark beside a thin line.

## Depth
Three layers, like the Iron Man helmet shots:
1. **Far back: the neural network.** A field of small dots drifting slowly; a thin line links any two dots that come close (the closer, the brighter). Dots are pushed away from the mouse or a finger, then drift back. Now and then a pulse runs across a few links: a bright dot that fades in and out, with a trail that fades behind it. **While the assistant thinks, pulses run toward it; while it speaks, they run away from it, faster when it's louder.** In room-mood alerts the network takes the alert color.
2. **Middle:** the real stuff: panels, buttons, chat, status strip. Sharp and readable.
3. **Front:** the cursor, reticles, alerts, the open module.

## Type
Every font is bundled with the code (works offline) and free to ship (SIL Open Font License). **Fonts are set per role in the theme**; switching is a one-word edit.

| Role | Default | Use |
|---|---|---|
| Titles | *Orbitron* | Titles and the startup title only, CAPS, extra letter spacing. |
| Interface + chat | *Chakra Petch* | Buttons, panels, chat, at least 20 px on the 32" monitor. |
| Typed lines | *Inter*, **light weight only** | Typed-out log lines, verses, lighter secondary text. Heavier weights look bloated. |
| Digits | *DSEG7* (seven-segment) | Clock, joint values, money, timestamps: numbers only. |
| Code | *JetBrains Mono* | Commands and file names inside chat answers. |

Also bundled: Oxanium, Rajdhani, DSEG14, Doto (dot matrix), Share Tech Mono.
- **Numbers never shift:** every value has a sign slot and a fixed number of digit places (blank places use a digit-wide blank), so `-87.0` and ` 23.5` line up.
- **Clock:** 24-hour or 12-hour with AM/PM (`clock` in the theme); AM/PM is set small in the interface font.
- Labels are small CAPS in `text_dim`; content is normal case in `text`.

## Motion: cinematic
Things **never just pop in**. Lines trace, rings sweep open, panels unfold from their corner, text types out with a block cursor. **Arrivals start fast and settle slowly**; exits are quick. **One after another**, spreading **outward from the center**. A button reacts in about 0.1 s, a panel opens in about 0.6 s, big startup moments last 1–1.5 s.

**Idle life on the hub:** the network drifts and fires; two to nine rings turn around the assistant at different speeds and directions (smaller ones around module buttons, spinning up on hover); thin columns of dots trickle down the edges; real log lines and git commits type out at the bottom; the assistant breathes every ~5 s; every 8–20 s one small event (a ring re-locks with a tick, a reticle scans a panel, a pulse runs along a trace). Nothing moves inside the area you're reading.

**The assistant's states:**
- **idle:** slow breathing, rings turning lazily.
- **listening:** rings contract and line up, as if focusing; brighter.
- **thinking:** rings spin fast; network pulses run toward the assistant.
- **speaking:** the inner ring ripples like a circular sound wave; the outer bar ring jumps with the voice; pulses run outward.
- **offline:** rings stop and dim to gray.
- **error:** rings stop and turn red, and a short message appears under the assistant (what's wrong, what still works).

**Modules** unfold from their button (chat unfolds from the core) while the hub shrinks back and blurs and the core flies to its dock; Back (or Esc) folds them into the button again and the core flies home. Arm views are line-drawn "holograms": a slowly turning wireframe over a round floor grid with faint scan lines, joints as hexagons with callouts.

**Sleep:** after a few minutes with nobody using it, the hub dims to the network and the breathing assistant; any input wakes it with a re-lock.

## Startup
The first thing people see, so it's the flashiest part.
- **Ignition screen** (waiting to start): a slow spinning ring and a soft pulsing core. It says how to start with **the inputs this device actually has**: "Touch, click or press any key to start", plus their icons; a gamepad adds "press any button". (A badge-card reader types like a keyboard, so it already counts.) A line with a shield icon says **"Safe to start. This only opens the hub; no robot moves."** Venue and clock at the bottom.
- **Assemble** (default): a bright line opens the screen like an old TV → the frame draws itself → the assistant, big in the center, gets its rings one by one, each locking on with a rising tone and spinning fast before settling → the core ignites and a shockwave reveals the network → real checks type out → the title decodes from scrambled letters → **everything flies to its place on the hub**: the title shrinks into the corner, the assistant settles into its spot, the panels unfold outward along growing traces.
- **Hyperspace jump** (`startup.style: hyperspace`), centered on the core. **The speed curve is the whole effect:**
  1. **Spool** (~1 s): a still star field starts drifting toward you, slowly speeding up; a low rumble rises.
  2. **Pull back** (~0.3 s): the stars ease to a stop and drift back a little, like a breath in; the sound dips.
  3. **Launch** (~0.9 s): the speed climbs steeply, so dots stretch into long streaks; a slight shake, a glow in the center, a rising roar.
  4. **Flash**, then **brake**: the network's dots streak in from the center to their places, fast at first and settling slowly, streaks shrinking to dots as they slow. The hub assembles quickly.

  Also a candidate for the Quest.
- Any input skips straight to the hub. ≤ ~6 s. Only real checks ("Internet: online", "AI: not connected").

**Quality levels** (`quality` in the theme):
- **maximal:** everything, plus more ring types on the core (an outer bar ring, a satellite orbit, inward-pointing markers, crosshair ticks), ruler ticks, hatched blocks and sliding markers on the frame, a denser network, more dot columns, and **Bible verses** (King James Version, public domain) typing out faintly in the far layer and fading.
- **full:** the standard look described above.
- **reduced:** rings, breathing, typing, a smaller network (no pulses, no dot columns), no blur.
- **minimal** (the lightweight mode): no idle motion at all; still lines, color changes, short fades; flat, no glow; the assistant a still circle that changes color; the network a still dot grid. If the computer asks for reduced motion, use minimal.

## Sound
Generated in the browser for now (WebAudio). Soft, airy, synthetic; mid-pitch so it carries over the lab's fans. **Silence between events**, no hum. About a third of idle events make a matching sound (a tick, a faint shimmer). Startup: a low swell, rising lock-on tones, a deep shockwave thump, a soft chord for the title, a landing whoosh (hyperspace: a long rising roar, then a deep arrival boom). Buttons: a short soft blip. Assistant: a two-note rise when it starts listening, a falling one when done. Warning: two falling tones. Critical: an urgent low double tone in step with the red pulse. Volume and mute live in the sound pack.

## Screens and places
**Everything scales with the screen,** the core included: sizes are set relative to the screen (the smaller of width and height decides), so the core keeps its share instead of shrinking first. **Portrait screens get their own layout:** the core on top, the buttons in a row under it, the fact panels in two columns below, and the page scrolls if it has to.

- **32" lab monitor (main):** seen from 1–3 m, often by visitors standing. Big text, strong contrast, the assistant readable from across the room. Left on, waiting at the ignition screen.
- **Quest headset:** panels float at arm's length; bigger text; no large bright areas. HUD arcs can wrap around tracked hands and the arm, FRIDAY-style; the network can become a 3D cloud; the hyperspace jump fits here.
- **Touchscreen (later):** the network reacts to fingers; buttons big enough for a fingertip.
- **Projector / bright rooms:** lines must stay bright; minimal quality reads best.
- **Laptops:** same layout, scaled down; reduced quality by default.

## Do
- Start from darkness; add light only where it means something.
- Fill space with **real information** (progress, budget, activity, devices), not filler.
- Draw things in; let the center stay calm.
- Use an icon when it says it faster than a word; cut every word that the layout already says.

## Don't
- **Generic "AI-made" interface habits:** labels that say nothing, section eyebrows, dots `•` used as separators.
- Rounded "app" cards, drop shadows, rainbow gradients, blue fog over everything.
- Glow on everything, or everything moving at once.
- Fake checks or fake numbers that look real.
- Flashing faster than 3 times per second (seizure risk). The critical pulse stays at 1.5; the hyperspace flash happens once.
- Tiny text, low-contrast gray text, decoration covering content, heavy font weights.
- Film screenshots, logos or Marvel names inside the interface (references are private).

## What each reference contributes
| Reference | Takeaway |
|---|---|
| `startup_design_beginning.jpg` | The startup's first frame: almost black, a frame with `+` corners and a dotted border, one ring spinning, a small chip in the middle, an amber hazard stripe. |
| `startup_design_ending.jpg` | Where the startup lands: dense but organized, circuit traces running out from the center into panels, white-hot cores in cyan glow. |
| `marvel_ironman_hud_collage.png` | Depth: the HUD floats in layers in front of a dark scene. The whole HUD shifts color with mood: blue/white normal, red alarm, gold. |
| `marvel_friday_hands.webp` | Arcs and tick marks wrapped around real things (hands): the model for Quest overlays. Hexagon icons, partial rings. |
| `hud_elements_1.jpg` | The two-color system (cyan + orange) on a dot grid; cut-corner panels, chevrons, reticles and hexagons. |
| `hud_elements_2.jpg` | Shapes in plain white: corner brackets, segmented rings, frames with screw dots, circuit lines ending in dots. Proof the shapes work without color. |
| `hud_elements_3.jpg` (Hydra) | Restrained two colors on slate; callout lines labeling wireframe objects; flat, no glow: a model for minimal quality. |
| `hud_elements_4.jpg`, `hud_elements_5.jpg` | Composition: one core of rings in the center, everything around it. Also what to avoid: blue haze, filler charts, everything equally bright. |
| `hud_elements_cyberpunk_1.jpg` | Big bold numbers, diagonal hatching, `+` grid marks, triangle icons. |
| `hud_elements_cyberpunk_2.jpg` | Text panels: title tab, chevrons, dot rows, soft neon glow on outlines with readable text inside. |
