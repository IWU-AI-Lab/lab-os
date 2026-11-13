# Lab checklist: plans and results of the visits 2026-11-10 to 2026-11-12

**Archived 2026-11-13** from the top of `docs/guides/lab-checklist.md`, as it was: what each lab visit was planned to do and what was new at the time. The checklist itself (the parts, how to test) stays in `docs/guides/lab-checklist.md`; the results went into the focus steps (`docs/archive/focus-2026-11-13-hub-voice-ai.md`) and `docs/dev/GOTCHAS.md`.

**Done on Tuesday 2026-11-10** (the builder, ~6–7 h): part 1 (the designed hub on the desktop, Gemini answered; `/perf` not run), the hub on `pi01` and the other desktop as well, all full screen except `/teleop` on the Pi (GOTCHAS); the Newline through `pi01` (laggy, part 2); Fable on the real arm (part 3; STOP from other screens not tried). Still open: `/perf` everywhere, STOP from another screen, parts 4–6.

**New since 2026-11-11 (built away from the lab, not tried on hardware yet):** honest "arrived" (part 3), `pose_view` (part 3), the Full screen button that says why (parts 1, 2 and 6), the drawing resolution per screen (part 2), teleop's 1:1 mode (part 7). Part 0 installs one new library (Pillow, for `pose_view`).

**Thursday 2026-11-12, in this order** (Fable ends Monday 2026-11-16, so the real-arm parts first; the white arm and its cameras only fit by unplugging the green ones):
1. Part 5, the training launcher, while the green arms are still plugged in.
2. Swap: unplug the green arms, plug in `so101-white` (and the leader for teleop).
3. Part 3, Fable with `pose_view` and the honest "arrived", plus STOP from another screen.
4. Part 7, teleop 1:1 on the real arm.
5. Voice prep: plug in the microphone, check Ubuntu Settings → Sound → Input shows it and the level moves when you talk; check the speakers too.
6. Part 1's `/perf` on the desktop's monitor (the demo screen for now), then the Newline (part 2) if there's time.
7. Part 4, the white cameras: list their socket names (they go in the green cameras' sockets). Since step 11 the camera-model block is gone; cameras go in `config/devices.yaml` by socket (`docs/dev/places.md`).
8. Put the green arms and cameras back as they were.

**New since 2026-11-12 (step 11, built away from the lab, tested without hardware):** the green arms in lab-os (part 8): `so101-green` drivable like the white arm, its calibration read only, `so101_setup` refusing the greens, "in use by LeLab" refusals, the training cameras by socket. Part 8 goes while the green arms are plugged in, before the swap (step 2 of the order above), or after putting them back.

**New since 2026-11-12 (step 7, voice, built away from the lab, tried on a laptop with recorded voices):** push-to-talk with a spoken answer, the spoken greeting, dictation, the wake word (part 9). Part 0 installs one new library (`onnxruntime`, for the wake word). **Gemini's free key speaks only ~15–20 answers a day** (10 requests per TTS model per day, GOTCHAS): if answers come silent with "…sending too much voice", that's it for the day (it resets at midnight Pacific).

**New since 2026-11-12 (step 10, the hub in VR, tried only in an emulated Quest):** the jump matching the main hub's, the hub around you with callouts, ⏻, module buttons (Teleop without leaving VR, Monitor and AI Control holograms) and asking by voice (part 10).

From part 3, as it was:
- 2026-11-10: Fable drove the real arm; it clearly needed more to go on than words (cameras, or at least `pose_view`). See `docs/plan/current-focus.md` step 2.
