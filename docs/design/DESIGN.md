# Lab JARVIS: design language

**In one line:** a calm, dark control room. Thin cyan light-lines float in front of black. They draw themselves in, turn slowly while idle, and get bright only where something is actually happening.

The numbers (colors, sizes, timings) live in `config/theme.yaml`. This page says what they mean and how to use them. The theme is the same for every persona; a persona only changes the assistant's picture, voice, lines and sounds.

## Colors
Dark first. One main color carries almost everything; the warm colors are kept for things that need a human.

| Token | Color | Use it for |
|---|---|---|
| `background` | near-black `#05080b` | Behind everything. Never pure gray, never a gradient fog. |
| `surface` | dark teal `#0b161c` | Panel fills, drawn see-through (about 8%) so the layers behind show. |
| `line` | dim teal `#1f3d48` | Quiet structure: grids, idle frames, background circuits. |
| `primary` | cyan `#29d4ff` | The main color: active lines, rings, the assistant, buttons. |
| `hot` | white-hot `#eafcff` | The bright core of the brightest things only (center of the assistant, a pulse, a selected item). |
| `text` / `text_dim` | `#d4eef5` / `#6d8c96` | Main text / labels. White with a hint of cyan, never pure white. |
| `accent` | amber `#ff9a2e` | "Look here": busy, waiting, hazard stripes, warnings. |
| `danger` | red `#ff4a3d` | Errors, stop, the arm frozen. Rare, so it means something. |
| `offline` | neutral gray `#56636a` | Offline, disabled, not connected. Dim, no glow. |
| `ok` | green `#3ee07f` | Only for "engaged / following" in teleop. Not a decoration color. |

Rule of thumb: about 90% cyan and dark, under 10% amber, red only when something is wrong. When the state changes, the whole room can change mood (cyan → amber → red), like the Iron Man helmet does.

**How serious is it?** Four levels, never mixed up:
| Level | Looks like | Examples |
|---|---|---|
| Normal | cyan, glowing | running, connected, idle |
| Warning | amber, glowing, may pulse slowly | busy, waiting for a key press, battery low |
| Critical | red, bright, pulses until handled | error, emergency stop, arm frozen |
| Offline / unavailable | gray, dim, **no glow**, maybe hatched | AI offline (no internet), robot not plugged in |

Offline is not an error: it's quiet, never red. Red is reserved for "a person needs to act".

**Changing the main color** is one edit: `primary` in the theme. `surface`, `line`, `hot` and `text` carry a slight cyan tint; nudge them toward the new hue to match.

## Lines, shapes and glow
- **Lines are thin.** Hairline (1 px) for structure, 2 px for active things, 4 px for the few key arcs. No filled blocks except small solid accents.
- **Glow = a sharp bright line plus a soft halo.** Two halos: a near one and a wide faint one. The brightest things get a white-hot center fading to cyan (like a neon tube). **Only active things glow**; structure lines never do.
- **Corners are cut, not rounded.** 45° chamfers, corner brackets `⌐ ¬`, small dots or screw-heads at the ends of lines.
- **The shape vocabulary:** segmented rings (rings with gaps and dashes), tick marks around circles, reticles, hexagons for icons, chevrons `›››`, dashed lines ending in a dot, diagonal hatching (for disabled or "hazard"), `+` marks at grid crossings, a faint dot grid behind everything.
- **Callouts:** a thin line with an elbow, from a thing to its label. Use them to name real parts (an arm joint, a device), Hydra-style.
- **Panels:** cut-corner outline, a small title tab at the top-left in caps, a see-through fill, maybe one accent mark (a tiny amber square or chevron). No drop shadows.

## Depth and layout
Three layers, like the Iron Man helmet shots:
1. **Back:** dot grid, faint circuit traces, very large faint rings. Dim (about a third of full brightness), slightly blurred, moves slowly.
2. **Middle:** the real stuff: panels, buttons, chat, status strip. Sharp and readable.
3. **Front:** a few bright accents: the cursor, reticles, the thing being pointed at.

**The assistant is the center.** Everything else is arranged around it and connected to it by circuit-like traces, as in the startup ending picture. The hub at rest is **busy at the edges, calm in the middle**: the area you read (chat, assistant) stays clean. How busy is one setting (`hub.density`: `sparse`, `busy-edges`, `dense`) so it's easy to try the others.

## Type
Fonts must be bundled with the code (works offline) and free to ship (SIL Open Font License).
- **Titles:** a wide, squared-off font in CAPS with extra letter spacing (e.g. *Orbitron*). Only for titles and the startup title; it's hard to read in sentences.
- **Interface and chat text:** a narrow technical sans (e.g. *Rajdhani*), at least 20 px on the 32" monitor.
- **Numbers, typed-out lines, data:** a monospace font (e.g. *JetBrains Mono*). Numbers that change use fixed-width digits so they don't jiggle.
- Labels are small CAPS in `text_dim`; content is normal case in `text`.

## Motion: cinematic
Things **never just pop in**. They are drawn:
- Lines trace from one end to the other; rings sweep open; panels unfold from their corner bracket; text types out with a block cursor.
- **Arrivals start fast and settle slowly** (like a camera landing on a shot). Exits are quick and quiet.
- **One after another, not all at once:** a short stagger (about 60 ms) between items, spreading **outward from the center**.
- **Big moments are slow, small ones are fast:** a button reacts in about 0.1 s, a panel opens in about 0.6 s, the startup's key moments last 1–1.5 s.

**Idle life on the hub** (in full and reduced quality, not in minimal):
- **Orbital rings** turn around the assistant and, smaller, around module buttons: two or three segmented rings each, different speeds (one full turn every 25–70 s), alternating directions.
- **Flowing dots:** columns of faint dots trickle down the back layer, matrix-style; small bright pulses travel along the circuit traces toward the assistant.
- **Typing text:** real things only: log lines, recent git commits, doc headings, joint angles. They type out at the edges, then fade. Obviously decorative filler (hex streams, scrolling code) in the dim back layer is one switch (`hub.filler`), off for now.
- **Breathing:** the assistant's glow swells and fades about every 5 s.
- **Small idle events** every 8–20 s, at random: a ring re-locks with a tick, a reticle scans a panel, a trace lights up. Never two at once.
- Motion in the corner of your eye is slow; nothing moves inside the area you're reading.

**Quality levels** (`quality` in the theme):
- **full:** everything above, glow, blur, particles.
- **reduced:** rings, breathing and typing; no flowing dots, no blur.
- **minimal** (the lightweight mode): no idle motion at all. Still lines, color changes and short fades only. Flat Hydra style: no glow. The assistant is a still circle that changes color.
- If the computer asks for reduced motion (an operating-system setting), use minimal.

## Sound
Generated in the browser for now (WebAudio). Soft, airy, synthetic; mid-pitch so it carries over the lab's fans without being shrill. Short sounds with a quick start and a gentle tail.
- **Ignition:** a low "whoom" that swells, then a rising sweep as things light up.
- **Typing:** very quiet ticks, a soft tone per finished line.
- **Buttons:** a short soft blip on press; hover makes nothing, or a barely audible tick.
- **Assistant:** a two-note rise when it starts listening, a falling one when it's done.
- **Warning / error:** two falling tones (amber), a lower double tone (red). Never a siren.
- No looping sound by default. Volume and mute live in the sound pack.

## Screens and places
- **32" lab monitor (main):** seen from 1–3 m, often by visitors standing. Big text, strong contrast, the assistant readable from across the room.
- **Quest headset:** panels float at arm's length on dark see-through fills; bigger text; no large bright areas (glare). HUD arcs can wrap around tracked hands and the arm, FRIDAY-style.
- **Projector / bright rooms:** black turns gray, so lines must stay bright; minimal quality reads best.
- **Laptops:** same layout, scaled down; reduced quality by default.

## Do
- Start from darkness; add light only where it means something.
- Keep real information in the middle layer, sharp and readable; decoration goes behind.
- Draw things in; let the center stay calm.
- Change the room's color with the state (normal cyan, warning amber, error red).
- Make shapes work in a single color first (like the white line-art sheet); glow comes after.

## Don't
- Rounded "app" cards, drop shadows, rainbow gradients, blue fog over everything (the stock-HUD look).
- Glow on everything, or everything moving at once.
- Fake checks or fake numbers that look real: the status strip and startup only show real facts.
- Flashing faster than 3 times per second (can trigger seizures), or strobing red.
- Tiny text, low-contrast gray text, decoration covering content.
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
