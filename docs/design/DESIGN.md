# lab-os: design language

**In one line:** a calm, dark control room. Thin cyan light-lines float in front of a slowly drifting network of dots. They draw themselves in, turn slowly while idle, and get bright only where something is actually happening.

The numbers (colors, fonts, sizes, timings) live in `config/theme.yaml`. This page says what they mean and how to use them. **Everything here is meant to be swapped easily:** colors, fonts, layout, how busy the hub is, how alerts look, each one a single setting in the theme. The theme is the same for every persona; a persona only changes the assistant's picture, voice, lines and sounds.

**The reference: [`hub-concept.html`](hub-concept.html)** (approved by the builder 2026-11-09, after ten rounds). Open it in a browser: click to start, or add `#skip` to the address to jump to the hub; "Concept controls" (bottom right) switches quality, layout, states, alerts, devices and greeting cases. **The real hub copies its look and motion**; this page explains the why, and `config/theme.yaml` holds the numbers. See "Building the real hub" at the end.

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
- **Connecting traces** run from the core **only to things you can press** (module buttons; the status strip and log above and below), with 45° bends, ending exactly on the edge with a dot at each end. Fact panels float free: lines to everything turn into clutter around the buttons.
- **Panels are callouts** (decided). The **title sits on a thin line**: plain words, Title Case, as few as possible ("Current Project", "AI Spend", "Commits", "Devices"), with a small node at the end facing the core, like a film-HUD callout. **Everything else sits under the line** on a see-through fill with a cut corner, for readability: counts, units, dates, "this month", "1 of 8 connected", the time range.
  - Why: a bare value is mysterious (`$0.00/20` reads like division), but "icon + small spaced-out CAPS title + big number" on every panel is the stock dashboard tile, the main thing that makes a UI look AI-made (a blend of every template).
  - **The graphic leads and differs per panel** (steps bar, meter, bars, hive), so the panels don't all share one shape.
  - **Full and maximal** decorate the line, never the content: a bright lead-in, a few ticks by the end node; maximal adds a small hatch block. **Module buttons** get corner brackets just outside the frame that open slightly on hover. Reduced and minimal: plain lines.
  - **The title sits in a tab:** a small box on the line, open at the bottom (the line is its floor), its corner facing the core cut at 45°, a faint fill. Full and maximal add a bright notch on the tab's top edge.
  - **Current Project:** the project name; then the step bar with "Step 0 of 8" at its right end; then **NEXT ›› First hub page** on its own line, larger, with a small pixel double chevron between the word and the step (light runs through it now and then).
  - **Spacing:** the content sits well inside its fill (about 1 rem from every edge), stacked callouts have clear air between them (~2 rem), and callouts keep a gap from the module buttons so the two kinds never touch.
  - **Boxes are for pressing, callouts are for reading first.** Module buttons (Teleop, Monitor, Arm) stay framed boxes because pressing is all they do; facts are callouts because you read them at a glance.
  - **Every callout opens its details**, full-screen, the same way a module opens (unfolds from the callout, the core goes to its corner, Back or Esc closes it). Tap anywhere on it except its own controls (range buttons, the list button, a device), or the **open mark** (⤢) beside the title tab, which says it can open without words and is big enough for a finger. On hover the tab and line light up. The details are the whole story behind the panel: **Current Project** = the goal, every step with what it means, now/next, what comes after; **AI Spend** = the month against an even pace to the budget, spend per AI setup; **Commits** = 30 days of bars with counts, totals, the latest commit messages; **Devices** = the full table with every column (use, computer name, IP; IPs hidden on public screens), tap a row for its card.
  - **Ranges are controls, not titles:** the commits panel shows `7d 14d 30d` under the line, not "Commits, 14 days".
- **Few words, never mysterious.** The test: someone walking in for the first time can say what each thing is. So:
  - every panel says what it *is* in its title on the line;
  - numbers carry their unit (`of $20`, `step 0 of 8`, `17 of 31 online`);
  - say "Next: first hub page", not an arrow and an internal name ("brain + hub skeleton");
  - inputs get placeholder text ("Ask anything"), not just a blinking cursor;
  - the full detail goes in the tooltip.
- **Cut where the layout already says it:** buttons are an icon and one word (no subtitles); chat has no "You" / "Assistant" labels (the side of the screen says who); no numbers or labels on decorative rings.
- **Error messages are the exception: full sentences.** What broke, what still works, what happens next: "**Can't reach the AI.** OpenAI hasn't answered for 30 s, so chat is paused. Teleop, devices and everything else still work. Trying again in 20 s."
- **Words in the interface font, numbers in the digit font.** Seven-segment fonts turn letters into garbage ("5tEP0oF8"), so they never get words.
- **The screen frame** isn't a plain rectangle: cut corners, a raised tab in the middle of the top and bottom edges, notches on the sides, bright brackets on the corners and tabs.

## Hub layout
**The title** in the top-left corner is the lab's name (`name` in the place's `place.yaml`, "AI Comp Lab" for now; moved out of the theme 2026-11-09, since the theme is the same at every place), not the project's code name: people in the hallway should read where they are. The startup decodes the same text.

**The core** is the assistant's picture: the rings around a glowing center. It sits **exactly in the middle of the screen** (the layout is symmetric around it), and the startup and hyperspace jump are centered on it.

Two layouts, one setting (`hub.layout`):
- **launcher** (default): the core big in the middle, module buttons left and right of it. Each button unfolds its module full-screen. The sides hold **panels of real project facts**: current focus progress, AI spend against the budget, commits per day, connected devices.
- **panels:** modules on the left, the chat on the right, the arm's joint readouts and the typed log at the bottom.

In both: **busy at the edges, calm in the middle**; how busy is `hub.density` (`sparse`, `busy-edges`, `dense`).

**Modular:**
- **Buttons come from a list** (`hub.modules`), in order, alternating left and right of the core so it stays balanced. Any number works, **including none**.
- **Chat is not a module.** It belongs to the core and is always there. **Asking doesn't open anything:** type into the line under the core (it sits just below the core's outer ring, never on it), or **just start typing** anywhere (the letters land in that line). The answer types out **under the core**, up to three lines, and fades after ~14 s; the core listens, thinks and speaks as usual. The **conversation** (the history) opens only when you want it: the history button at the end of the ask line (with a count of questions), tapping the answer, or tapping the core. With no modules the hub is the core, its ask line and the fact panels.
- **The device panel takes any number of devices** (the lab may have 30+: arms, the headset, cameras, ~10 Raspberry Pis, ~7 ThinkCentres, ~6 desktops).
  - **Up to 8:** a star, each device a dot connected to the brain, pulses running along live links. Names show when there are 6 or fewer.
  - **More:** a **hive**, one row per kind (icon, `linked/total`, then one small hexagon per device).
  - **Two statuses per device:** *on* (plugged in, or answers on the network) and *linked* (talking to the brain). One word for it everywhere: column, count, card and button. Hexagons: lit = linked, cyan outline = on but not linked, gray outline = off, hatched = locked.
  - **Locked** devices belong to a project (today: the green SO-101 and the training cameras, locked to the SO-101 training). The hub shows them but never opens their ports.
  - **Tap any device** for a card beside the panel. Identification first: the **sticker** on the device (Pis: 1–10; desktops and ThinkCentres: the university IT number) as the title, with what it's used for. Then the two statuses. Then the facts: the lab-os name, the computer's own name, the IP address, and whatever else it reports. Lists show the sticker first, too.
  - A **framed button beside the count**, on the right ("List all" with a chevron; sized to its words, still big enough for a finger), **expands the panel into a table**, grouped by kind; the same button then says "Show map". Opening it **moves nothing above it**: the column stays pinned and the list grows downward, capped so it stops above the bottom row. When it holds more than fits it **scrolls**, with a thin cyan scroll bar and a fade at the bottom that disappears once you reach the end (and never shows while the list is closed).
  - **Statuses are words with a dot** ("● On", "○ Off", "● Yes", "🔒 Locked"), never bare icons: icons like power and link look like buttons that would switch the device off. Column heads: Power, Linked. Long names shorten with "…".
  - **Actions live in the device card,** as a real framed button: "Link to the brain" / "Unlink from the brain" ("Turn it on to link" when it's off; nothing for locked devices). Boxes are for pressing, so the table stays read-only. **Which columns show is one list** (`hub.device_columns`: id, on, linked; also available: use, host, ip), so adding information later is one word.
  - Under the line: `9 of 31 linked`. Settings: `hub.devices_view`, `hub.devices_graph_max`.
  - **System diagram** (2026-11-18): a square icon button (the network icon) before "List all" opens how everything connects, full screen like a details page: the brain as the core (rings and the glowing centre, nothing inside), screens left, robots right, the AI above, hexagon badges with icons, traces with 45° bends and a dot at each end, the line's style for the kind of link, pulses only on real links. Names Title Case as people say them; a short line under each. Built in the real hub only (`hub/system-diagram.js`), not in the concept.

**The core never disappears.** When a module opens, the core flies along with it instead of fading with the hub:
- the three small markers inside the arcs shrink with them when the core contracts (listening), so the arcs never sit on top of them;
- in **chat** it sits full size beside the conversation (left of it; above it on a portrait screen), so listening, thinking and speaking stay visible, and network pulses still flow into it;
- in **other modules** it shrinks into the bottom-right corner and keeps reacting (a voice reply, an alert).

**Chat** (the conversation page) sits on a near-black background, so the core beside it keeps its contrast. Your messages on the right in a box with broken edges (bright corners, gaps in the sides); the assistant on the left, its hexagon mark beside a thin line.

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
- **error:** rings stop and turn red, and a message appears under the assistant (what broke, what still works, what happens next).

**Modules** unfold from their button (chat unfolds from the core) while the hub shrinks back and blurs and the core flies to its dock; Back (or Esc) closes them at once: the page shrinks back toward its button and fades in about a quarter second (a page cropped by a slow fold looks broken), the hub comes forward, and the core flies home. Arm views are line-drawn "holograms": a slowly turning wireframe over a round floor grid with faint scan lines, joints as hexagons with callouts.

**Back to the start screen (2026-11-09, replaces sleep on public screens):** after ~3 minutes with nobody using it, the hub closes modules, clears the conversation from the screen and returns to the full-screen ignition screen, so the next person gets the startup. Never while teleop, an AI move or a voice turn is running.

## Startup
The first thing people see, so it's the flashiest part.
- **Ignition screen** (waiting to start): a slow spinning ring and a soft pulsing core over a **still star field** that barely drifts and twinkles. The stars are the anchor for the startup: the hyperspace lines grow out of them, and with assemble they glide into place as the network's dots while the rest fade. It says how to start with **the inputs this device actually has**: "Touch, click or press any key to start", plus their icons; a gamepad adds "press any button". (A badge-card reader types like a keyboard, so it already counts.) A line with a shield icon says **"Safe to start. This only opens the hub; no robot moves."** Venue and clock at the bottom.
- **Two taps (decided 2026-11-09, not shown in the concept page):** if the page isn't full screen yet, the ignition screen first asks to be tapped for full screen (a small line, "Tap for full screen"); that tap only enlarges the idle screen and unlocks sound. The next tap starts. The builder does the first tap when leaving the hub on a screen, so visitors only see "Touch, click or press any key to start".
- **Ignition = an unlock**, with its own sound, **finished before the startup begins** (~1.35 s). The small core sits **exactly in the middle of the screen**, where the jump's lines start and the real core lands; the words sit under it. It should feel heavy: slow-in, slow-out curves and a wind-up. The core dips slightly (a low breath) → the eight bolts around it pull back one after another (a clack each) and the words drop away → the outer ring turns a third of a turn (a heavy thunk and a slow servo groan) and opens outward (a latch clank) → the inner ring collapses into the core → the core swells and bursts a ring of light (a bright two-note chime) → the startup begins.
- **Assemble** (default): a bright line opens the screen like an old TV → the frame draws itself → the assistant, big in the center, assembles: **corner brackets close in** on where it will settle, then the rings arrive one by one, **each from its own side** (some grow out from the middle, some shrink in from outside, each turning into place), **flashing as it locks** with a rising tone and sending out **a thin ring of light**; the tick and bar rings sweep around like a radar → the core ignites, overshooting a little, with a **lens flare** across it, and a shockwave reveals the network → real checks type out while the title decodes above them: a scan bar sweeps each row open, a dotted leader draws to the value, the value lights up → **the greeting** types under the title in a title font → **everything flies to its place on the hub**: the title shrinks into the corner, the assistant settles into its spot, the panels unfold outward along growing traces.
- **Hyperspace jump** (`startup.style: hyperspace`; **the default since 2026-11-09**, with `assemble` and per-venue as the other choices; the theme still says `assemble` until the reveal step updates it), centered on the core, 2.7 s before the flash. A real 3D star field (~3,000 stars over the whole screen so the edges are full, with **a third gathered around the middle** so the place you look at isn't empty) and **one smooth speed curve**: it only ever builds, never fast-slow-fast. It starts from the ignition screen's drift, so nothing jumps.
  1. **Ramp** (~2 s): the speed is **exponential**: the dots barely crawl at first, then race. The trails lead the speed (they grow with time²), so the lines stretch while the dots are still slow, and only then does the speed catch up (anticipation). The waiting stars start drifting outward, each leaving a short fading trail. The trails stretch and brighten, and the view slowly turns faintly blue. A hum rises with the speed.
  2. **Hold** (~0.7 s): full speed. Complete lines that sweep all the way past the edges (a star leaves only when its tail does), a steady shake, the roar.
  3. **Impact frame** (optional, `impact_frame`): the streaks frozen for ~80 ms, black lines on white. Never red: red means critical.
  4. **Flash**: a burst of light from the core that clears from the edges first (an even white fade reads as gray fog). Then a long **brake** (~2.6 s), like a rollercoaster coming to a halt (follow-through). The network's dots streak in from the center and settle. The network starts **white-hot and dims** as it settles, and the core arrives big and shrinks into place on the same curve.

  Animation principles at work: slow in (the ramp), exaggeration (the trails are motion blur stretched far beyond real physics, so lines get long while each star moves only a little per frame and keeps its place), secondary action (shake, glow, sound follow the speed), follow-through (the brake). Every line looks the same the whole time: a **smooth gradient** from a faint tail to a bright head, where brighter also means whiter (whiter still at speed), so color and brightness change together; no visible bands. The arrival trails of the network's dots use the same gradient. Lines that re-randomize every frame look like noise.

  Also a candidate for the Quest.
- The hyperspace jump ends the same way: the rings assemble around the core as it lands, then the checks, title and greeting.
- **The greeting carries one line of real news** when there is some, most important first, after "Good morning/afternoon/evening": an alert ("fake-arm is waiting for the clutch."), a device that dropped out ("xarm1 has been offline since Tuesday."), the budget running low ("AI spend is at $16 of $20, with 9 days to go."), a step finished ("Step 1 is done. Next: personas."), a busy day ("31 commits yesterday."), then the calendar ("Working late.", "Saturday in the lab.", "New week."). Otherwise the persona's plain line: "All local systems are up." Never invented: each case reads a real fact. One line, so it fits under the title. The chat's first message starts with the same line.
- **Startup as a video** (2026-11-18, a test for slow screens, `docs/archive/guides-2026-11-25/hub.md`): the same startup played from a recording, the words live above it. The design stays the source: after any change to the startup, the recording is made again from the real page (`scripts/record_startup.py`).
- Any input skips straight to the hub. ≤ ~8 s with the unlock. Only real checks ("Internet: online", "AI: not connected").

**Quality levels** (`quality` in the theme):
- **maximal:** everything, plus more ring types on the core (an outer bar ring, a satellite orbit, inward-pointing markers, crosshair ticks), ruler ticks, hatched blocks and sliding markers on the frame, a denser network, more dot columns, and **Bible verses** (King James Version, public domain) typing out faintly in the far layer and fading.
- **full:** the standard look described above.
- **reduced:** rings, breathing, typing, a smaller network (no pulses, no dot columns), no blur.
- **minimal** (the lightweight mode): no idle motion at all; still lines, color changes, short fades; flat, no glow; the assistant a still circle that changes color; the network a still dot grid. If the computer asks for reduced motion, use minimal.

## Sound
Generated in the browser for now (WebAudio). Soft, airy, synthetic; mid-pitch so it carries over the lab's fans. **Silence between events**, no hum. About a third of idle events make a matching sound (a tick, a faint shimmer). Startup: a low swell, rising lock-on tones, a deep shockwave thump, a soft chord for the title, a landing whoosh (hyperspace: a swelling hum, a rising whine, the roar of the jump, then a deep arrival boom). Buttons: a short soft blip. Assistant: a two-note rise when it starts listening, a falling one when done. Warning: two falling tones. Critical: an urgent low double tone in step with the red pulse. Volume and mute live in the sound pack.

## Screens and places
**Everything scales with the screen,** the core included: sizes are set relative to the screen (the smaller of width and height decides), so the core keeps its share instead of shrinking first. **Portrait screens get their own layout:** the core on top with the ask line under it, the buttons in a row under that, the fact panels in two columns below (one column on a phone narrower than 560 px), and the page scrolls if it has to. On a phone the latest answer lies on a fill, because it can cover the buttons for a moment.

**Small screens** (a phone, the Pi's touchscreen; 1100 px wide or less, or 640 px high or less; quick job 96, 2026-11-23): every control is at least about 40 px, big enough for a finger. A small mark (the open mark ⤢) keeps its look and gets a bigger area for the tap. An open page has a thin frame, and the docked core is small in the corner with its own room, so it covers nothing. On a phone, "Open on…" shows only its icon. A small screen on its side (800 × 480) gets less frame and air and a smaller core, so the fact panels keep room for their words. Large screens keep their layout.

- **32" lab monitor (main):** seen from 1–3 m, often by visitors standing. Big text, strong contrast, the assistant readable from across the room. Left on, waiting at the ignition screen.
- **Quest headset:** panels float at arm's length; bigger text; no large bright areas. HUD arcs can wrap around tracked hands and the arm, FRIDAY-style; the network can become a 3D cloud; the hyperspace jump fits here.
- **Large touch display (Newline) and hallway screens:** seen by people passing by, so the "newcomer can tell what it is" test matters most here. The network reacts to fingers; buttons big enough for a fingertip. **Public screens hide internal details** (IP addresses, spend): the venue profile decides.
- **Projector / bright rooms:** lines must stay bright; minimal quality reads best.
- **Laptops:** same layout, scaled down; reduced quality by default.
- **Phones and the Pi's touchscreens (800 × 480, 1024 × 600):** the small-screen rules above. No sideways scroll; a page scrolls down when it has to.

## Do
- Start from darkness; add light only where it means something.
- Fill space with **real information** (progress, budget, activity, devices), not filler.
- Draw things in; let the center stay calm.
- Use an icon when it says it faster than a word; cut every word that the layout already says, but keep the few that say what a thing *is*.
- **Titles name things; details live under them.** A title is one or two words. Counts, units, dates and ranges go in the content.
- **Give content a readable surface;** put decoration on lines and edges, and let it scale with the quality level.
- **Only connect what you can act on.** Lines lead to buttons, not to every panel.
- **Anything that will grow is a table or a hive whose columns come from config,** so new information is a setting, not a redesign.
- **Animate with one curve per effect.** Speed, brightness, shake and sound follow the same curve, so the motion reads as one intention.

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

## Building the real hub
For the designed hub (`/design`, built since 2026-11-10) and every new page (no longer a surprise, 2026-11-12), **this design is the spec**: `hub-concept.html` shows how it should look, move and sound, this page says why, and `config/theme.yaml` holds the numbers. Open the concept next to the real page and compare them side by side.
- **Take from the concept:** the layout, every animation and its timing, the sounds (WebAudio recipes in its `SFX` object), the startup (unlock, hyperspace, assembly, checks, greeting), the callouts and their details pages, the device panel, the ask line under the core, the module pages and the docked core. Lift code where it fits; it's one file, written to be read.
- **Don't take:** the concept controls (`#dock`), the fake data (canned answers, `ANSWERS`, the example computers, `GREET_EXAMPLES`, the simulated arm), and the Google Fonts link. The real pages work offline: fonts are bundled (see `font.bundled` in the theme) and vendored like the three.js copy in `src/lab_os/web/vendor/`.
- **Read every number from the theme** (`/theme.json`), not from constants in the page. The concept hard-codes them; where a token exists, the token wins.
- **Real facts only:** the checks, the greeting's news line, the panels and the device statuses all read real state. Where something isn't real yet, leave it out instead of faking it.
- **Changing the design:** update this page, the theme and the concept together (a design session), so the three never disagree.
- **Where it's built (2026-11-10):** `src/lab_os/hub/web/design.html`, served at `/design` (and at `/` once `hub.look: design`). It's the concept file reworked in place: the controls and made-up data removed, the brain's endpoints in their place, fonts from `src/lab_os/web/vendor/fonts/`. A change to the design goes into the concept first (the reference), then into `design.html`. The module pages (teleop, monitor, AI Control, settings) share a small kit in the same style, `src/lab_os/web/design/` (`kit.css`: cut-corner cards, chips, buttons, STOP; `kit.js`: the theme's colors and fonts, inside-the-hub vs on its own screen; `icons.svg`).
