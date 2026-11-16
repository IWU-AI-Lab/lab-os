# Quick jobs

Small jobs that are **already decided** and can be built in one Claude Code session without the lab, or nearly. A session told "do some quick jobs" takes them from the top, does each completely (its own branch, tests without hardware, docs, `FEATURES.md`, a PR), and moves it to "Done" with the date and PR number. Anything that needs the lab gets a line in `docs/guides/lab-checklist.md` instead.

Not decided yet? It goes in `docs/plan/ideas.md`, not here. Bigger work is a focus step (`docs/plan/current-focus.md`).

## To do

6. **Shut down from the hub.** A "Shut down lab-os" button (Settings, and in the ⏻ menu on the brain's own screen), with a confirmation: stops any move, lets go of the arms the same way Ctrl+C does now (warn first that a lifted SO-101 goes limp), closes cameras and the microphone, stops the brain; every page then says it's off. Never from a public venue.
7. **Stop LeLab.** A "Stop LeLab" button on the Training page (and `lab-os green --stop`) that closes the LeLab the launcher started (`docs/guides/green-launcher.md`). Only that process, nothing else.
8. **The Quests in the device list** (`config/devices.yaml`, so they show in the Devices panel): three Meta Quest 3 headsets, `quest-a`, `quest-b`, `quest-c` (shown as Quest A, B, C; letters because "Quest 3" is the model). One is on loan to an AI club member (which one: ask the builder; its notes say so). The device name the Quest uses for `?device=` (step 8) is the same.
9. **Esc in teleop leaves full screen.** On the teleop page, Esc stops the arm but also ends full screen (the browser does that). Use Chrome's Keyboard Lock (`navigator.keyboard.lock(["Escape"])`, full screen only) so Esc only stops; holding Esc still leaves full screen (the browser's rule). Where Keyboard Lock isn't there, nothing changes.
10. **VR hub: a cluster of linked dots far away.** In `/xr` after the jump, a tight clump of connected dots sits off in the distance (seen in the headset, 2026-11-13). Find why (`hub/web/xr/network.js`) and spread them like the rest.
11. **VR hub: the chat doesn't scroll.** On the VR home, new chat text below the bottom of the panel isn't scrolled into view. Keep the newest line visible.
12. **A diagram of the system**, and a way to see it on the hub: one clear drawing (the brain, the hub pages, the devices and how each connects: USB, network, MCP), as SVG made by hand (no CDN, `docs/` and the hub), opened from the Devices panel ("How it connects"). Matches the design.
16. **"Give me a lab status report."** One read tool for the hub's assistant (`lab_status`) that returns, in one call: the arm and whether something is driving it, the devices with the hub open, voice (the way in, whether the voice service answers), this month's AI spend against the budget, the focus's next step, and warnings (limits switched off, servos warm). The assistant answers in a few spoken sentences, only real facts. Today it can look these up one by one (`docs/dev/chat.md` → "What it knows") but has no single report.

## Done
- 1. **Arm moves without asking** (done 2026-11-14, PR #73). Every brain tool on the allow list; a test checks it. Lab: the no-prompt check in lab-checklist part 0.
- 2. **Limits that can be turned off** (done 2026-11-14, PR #75). `limits:` in the venue file and Settings → Safety limits; `limits_locked: true` on visit-day. Lab: lab-checklist part 6.
- 3. **The floor at −0.5 cm** (done 2026-11-14, PR #76). `min_z_cm: -0.5` in both venues, teleop the same number. Lab: the stepped ruler check in lab-checklist part 3.
- 4. **The greeting from a recording** (done 2026-11-14, PR #77). Time of day + hint only, saved per voice in `recordings/greetings/`. Lab: lab-checklist part 9b.
- 5. **The AI budget on the Settings page.** (done 2026-11-14, PR #78). The field was there; the brain now reads the budget live. Lab: lab-checklist part 6.
- 13. **1:1 teleop scale, the part without the lab** (done 2026-11-16). No scale error in the chain (model, units, 3D arm, gripper point); fixed the hand's base on a headset without a floor (`docs/dev/GOTCHAS.md`). Lab: checks 7.2–7.4.
- 15. **Camera names: stand and wrist** (done 2026-11-16). `so101-white-cam-stand` / `-cam-wrist` in `devices.yaml`, the tool description and the docs; "overhead" → "stand camera". The green cameras keep `-a`/`-b` until the lab check says which is which.
- 14. **Teleop page: the 3D view and the joint readout in their own boxes.** (done 2026-11-14, PR #79). Fixed 3D box, one fixed-height row per joint beside it. Lab: lab-checklist part 6.
