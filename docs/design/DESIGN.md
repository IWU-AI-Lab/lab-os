# Lab JARVIS: design language

**In one line:** a calm, dark control room. Thin cyan light-lines float in front of a slowly drifting network of dots. They draw themselves in, turn slowly while idle, and get bright only where something is actually happening.

The numbers (colors, fonts, sizes, timings) live in `config/theme.yaml`. This page says what they mean and how to use them. **Everything here is meant to be swapped easily:** colors, fonts, how busy the hub is, how alerts look, each one a single setting in the theme. The theme is the same for every persona; a persona only changes the assistant's picture, voice, lines and sounds.

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
| `accent` | amber `#ff9a2e` | Warning: busy, waiting, hazard stripes. |
| `danger` | aggressive red `#ff2436` | Critical: a person must act. Rare, so it hits hard. |
| `offline` | neutral gray `#56636a` | Offline, disabled, not connected. |
| `frozen` | muted rust `#7a1d00` | An arm holding still (dead-man stop). |
| `ok` | green `#3ee07f` | Only for "engaged / following" in teleop. Not a decoration color. |

About 90% cyan and dark, under 10% amber, red only when something is wrong.

**How serious is it?** Never mixed up:
| Level | Looks like | Examples |
|---|---|---|
| Normal | cyan, glowing | running, connected, idle |
| Held | muted rust, no glow, no pulse: calm | arm frozen because the clutch is released (that's the safety system working, not a problem) |
| Offline | gray, dim, **no glow**, maybe hatched | AI offline (no internet), robot not plugged in |
| Warning | amber, glowing, slow pulse | busy, waiting for a key press, battery low |
| Critical | red, harsh: fast pulse (1.5 per second), a short glitch jolt when it starts, a red edge around the screen, an urgent sound | error, emergency stop, lost connection while moving |

Offline and held are quiet, never red. **How far an alert spreads** is a setting (`alerts.mood`): `local` = only the affected thing changes color; `room` = the whole screen shifts mood, Iron Man style (rings, network and edges turn amber or red).

**Changing the main color** is one edit: `primary`. `surface`, `line`, `hot` and `text` carry a slight cyan tint; nudge them toward the new hue to match.

## Lines, shapes and glow
- **Lines are thin.** Hairline (1 px) for structure, 2 px for active things, 4 px for the few key arcs. No filled blocks except small solid accents.
- **Glow = a sharp bright line plus a soft halo.** Two halos: a near one and a wide faint one. The brightest things get a white-hot center fading to cyan (like a neon tube). **Only active things glow**; structure lines never do.
- **Corners are cut, not rounded.** 45° chamfers, corner brackets `⌐ ¬`, small dots at the ends of lines.
- **The shape vocabulary:** segmented rings (rings with gaps and dashes), tick marks around circles, reticles, hexagons for icons, chevrons `›››`, dashed lines ending in a dot, diagonal hatching (disabled or hazard), `+` marks at grid crossings.
- **Callouts:** a thin line with an elbow, from a thing to its label. Use them to name real parts (an arm joint, a device), Hydra-style.
- **Panels:** cut-corner outline, see-through fill, maybe one accent mark (a tiny amber square or chevron). A title tab only when the panel needs a name. No drop shadows.

## Depth and layout
Three layers, like the Iron Man helmet shots:
1. **Far back: the neural network.** A field of small dots drifting slowly; a thin line links any two dots that come close (the closer, the brighter the line). Dots are gently pushed away from the mouse or a touching finger, then drift back. Now and then a pulse "fires" along a few links. When the assistant is thinking, the network fires more often; in room-mood alerts it takes the alert color. Dim (about a third of full brightness).
2. **Middle:** the real stuff: panels, buttons, chat, status strip. Sharp and readable.
3. **Front:** a few bright accents: the cursor, reticles, the thing being pointed at.

**The assistant is the center.** Everything else is arranged around it and connected to it by circuit-like traces, as in the startup ending picture. The hub at rest is **busy at the edges, calm in the middle**: the area you read (chat, assistant) stays clean. How busy is one setting (`hub.density`: `sparse`, `busy-edges`, `dense`).

## Type
Every font is bundled with the code (works offline) and free to ship (SIL Open Font License). **Fonts are set per role in the theme**, and every font below is bundled, so switching is a one-word edit, like the "Mix your own" picker on the comparison page.

| Role | Default | Use |
|---|---|---|
| Titles | *Orbitron* | Titles and the startup title only, CAPS, extra letter spacing. Hard to read in sentences. |
| Interface + chat | *Chakra Petch* | Buttons, panels, chat, at least 20 px on the 32" monitor. |
| Typed lines | *Inter*, **light weight only** | Typed-out log lines and lighter secondary text. Heavier weights look bloated. |
| Digits | *DSEG7* (seven-segment) | Clock, joint values, timestamps: numbers only. Words stay in a readable font. |
| Code | *JetBrains Mono* | Commands and file names inside chat answers. |

Also bundled to switch to: Oxanium, Rajdhani, DSEG14, Doto (dot matrix), Share Tech Mono.
- Labels are small CAPS in `text_dim`; content is normal case in `text`. Keep CAPS to short labels; long CAPS text looks heavy.
- Numbers that change use fixed-width digits so they don't jiggle.

## Motion: cinematic
Things **never just pop in**. They are drawn:
- Lines trace from one end to the other; rings sweep open; panels unfold from their corner bracket; text types out with a block cursor.
- **Arrivals start fast and settle slowly** (like a camera landing on a shot). Exits are quick and quiet.
- **One after another, not all at once:** a short stagger (about 60 ms) between items, spreading **outward from the center**.
- **Big moments are slow, small ones are fast:** a button reacts in about 0.1 s, a panel opens in about 0.6 s, the startup's key moments last 1–1.5 s.

**Idle life on the hub** (full and reduced quality, not minimal):
- **The network** drifts and fires (see Depth).
- **Orbital rings** turn around the assistant and, smaller, around module buttons: two or three segmented rings each, different speeds (one turn every 25–70 s), alternating directions.
- **Flowing dots:** thin columns of dots trickle down in the busy edge areas, matrix-style; bright pulses travel along the circuit traces toward the assistant.
- **Typing text:** real things only: log lines, recent git commits, doc headings, joint angles. They type out at the edges, then fade. Obviously decorative filler (hex streams) in the far layer is one switch (`hub.filler`), off for now.
- **Breathing:** the assistant's glow swells and fades about every 5 s.
- **Small idle events** every 8–20 s, at random: a ring re-locks with a tick, a reticle scans a panel, a trace lights up. Never two at once.
- Motion in the corner of your eye is slow; nothing moves inside the area you're reading.

**The assistant's states** (the picture only reads the state):
- **idle:** slow breathing, rings turning lazily.
- **listening:** rings contract and line up, as if focusing; brighter.
- **thinking:** ring segments chase each other around; the network fires faster.
- **speaking:** the inner ring ripples with the voice's loudness, like a circular sound wave.
- **offline:** rings slow to a stop and dim to gray.
- **error:** a ring breaks apart with a glitch, red; it reassembles when the error clears.

**Moving between pages:** a module button's ring speeds up and locks when hovered; clicking it unfolds the module from the button while the hub folds back toward the edges. Going back reverses it. No hard page cuts.

**Sleep:** after a few minutes with nobody using it, the hub dims to just the network and the assistant breathing; any key, mouse movement or touch wakes it with a short re-lock.

**Quality levels** (`quality` in the theme):
- **full:** everything above, glow, blur, the interactive network.
- **reduced:** rings, breathing, typing, a smaller network (fewer dots, no firing); no flowing dots, no blur.
- **minimal** (the lightweight mode): no idle motion at all. Still lines, color changes and short fades only. Flat, no glow (the Hydra sheet). The assistant is a still circle that changes color. The network becomes a still dot grid.
- If the computer asks for reduced motion (an operating-system setting), use minimal.

## Sound
Generated in the browser for now (WebAudio). Soft, airy, synthetic; mid-pitch so it carries over the lab's fans without being shrill. Short sounds with a quick start and a gentle tail.
- **Between events: silence.** No hum, no loops.
- **Idle events:** some of the random idle events (about a third) make a matching sound: a soft tick when a ring re-locks, a faint shimmer when a trace lights up.
- **Ignition:** a low "whoom" that swells, then a rising sweep as things light up.
- **Typing:** very quiet ticks, a soft tone per finished line.
- **Buttons:** a short soft blip on press; hover makes nothing, or a barely audible tick.
- **Assistant:** a two-note rise when it starts listening, a falling one when it's done.
- **Warning:** two falling tones. **Critical:** an urgent, low, pulsing double tone in step with the red pulse, until handled. Not a siren.
- Volume and mute live in the sound pack.

## Screens and places
- **32" lab monitor (main):** seen from 1–3 m, often by visitors standing. Big text, strong contrast, the assistant readable from across the room.
- **Quest headset:** panels float at arm's length on dark see-through fills; bigger text; no large bright areas (glare). HUD arcs can wrap around tracked hands and the arm, FRIDAY-style. The network can become a 3D cloud around the user.
- **Touchscreen (later):** the network reacts to fingers; buttons big enough for a fingertip.
- **Projector / bright rooms:** black turns gray, so lines must stay bright; minimal quality reads best.
- **Laptops:** same layout, scaled down; reduced quality by default.

## Do
- Start from darkness; add light only where it means something.
- Keep real information in the middle layer, sharp and readable; decoration goes behind.
- Draw things in; let the center stay calm.
- Make shapes work in a single color first (like the white line-art sheet); glow comes after.
- Make every label carry information.

## Don't
- **Generic "AI-made" interface habits:** labels that say nothing (a subtitle like "LAB · HUB" under the title), section eyebrows, dots `•` used as separators. Separate things with space and lines instead.
- Rounded "app" cards, drop shadows, rainbow gradients, blue fog over everything (the stock-HUD look).
- Glow on everything, or everything moving at once.
- Fake checks or fake numbers that look real: the status strip and startup only show real facts.
- Flashing faster than 3 times per second (can trigger seizures). The critical pulse stays at 1.5.
- Tiny text, low-contrast gray text, decoration covering content, heavy font weights.
- Film screenshots, logos or Marvel names inside the interface (references are private).

## What each reference contributes
| Reference | Takeaway |
|---|---|
| `startup_design_beginning.jpg` | The startup's first frame: almost black, a frame with `+` corners and a dotted border, one ring spinning, a small chip in the middle, an amber hazard stripe ("BUFFERING"). |
| `startup_design_ending.jpg` | Where the startup lands: dense but organized, circuit traces running out from the center chip into panels, white-hot cores in cyan glow. |
| `marvel_ironman_hud_collage.png` | Depth: the HUD floats in layers in front of a dark scene, back layers soft and dim. The whole HUD shifts color with mood: blue/white normal, red alarm, gold. |
| `marvel_friday_hands.webp` | Arcs and tick marks wrapped around real things (hands): the model for Quest overlays. Hexagon icons, partial rings. |
| `hud_elements_1.jpg` | The two-color system (cyan + orange) on a dot grid; cut-corner panels, chevrons, a library of reticles and hexagons. |
| `hud_elements_2.jpg` | Shapes in plain white: corner brackets, segmented rings, frames with screw dots, circuit lines ending in dots, segmented bars. Proof the shapes work without color. |
| `hud_elements_3.jpg` (Hydra) | Restrained two colors (coral `#FF6E58`, cream `#DBEECE`) on slate; callout lines labeling wireframe objects; flat, no glow: a model for minimal quality. |
| `hud_elements_4.jpg`, `hud_elements_5.jpg` | Composition: one core of rings in the center, everything around it, a floor grid in perspective. Also what to avoid: blue haze, filler charts, everything equally bright. |
| `hud_elements_cyberpunk_1.jpg` | Big bold numbers (`95%`), diagonal hatching, `+` grid marks, glitchy pixel blocks, triangle icons. |
| `hud_elements_cyberpunk_2.jpg` | Text panels: title tab, chevrons, dot rows, soft neon glow on outlines with readable text inside. |
