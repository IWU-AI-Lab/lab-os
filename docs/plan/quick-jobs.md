# Quick jobs

Small jobs that are **already decided** and can be built in one Claude Code session without the lab, or nearly. A session told "do some quick jobs" takes them from the top, does each completely (its own branch, tests without hardware, docs, `FEATURES.md`, a PR), and moves it to "Done" with the date and PR number. Anything that needs the lab gets a line in `docs/guides/lab-checklist.md` instead.

Not decided yet? It goes in `docs/plan/ideas.md`, not here. Bigger work is a focus step (`docs/plan/current-focus.md`).

## To do
Order: from the top (20 and 25 next: the green arms).

6. **Shut down from the hub.** A "Shut down lab-os" button (Settings, and in the ⏻ menu on the brain's own screen), with a confirmation: stops any move, lets go of the arms the same way Ctrl+C does now (warn first that a lifted SO-101 goes limp), closes cameras and the microphone, stops the brain; every page then says it's off. Never from a public venue.
10. **VR hub: a cluster of linked dots far away.** In `/xr` after the jump, a tight clump of connected dots sits off in the distance (seen in the headset, 2026-11-13). Find why (`hub/web/xr/network.js`) and spread them like the rest.
12. **A diagram of the system**, and a way to see it on the hub: one clear drawing (the brain, the hub pages, the devices and how each connects: USB, network, MCP), as SVG made by hand (no CDN, `docs/` and the hub), opened from the Devices panel ("How it connects"). Matches the design.

19. **Show "X = STOP" in desktop control.** X already stops in every mode and leaves full screen alone; the page doesn't say so where you look. Put it next to STOP and in the key help. Esc stays as it is (it can't keep full screen in Brave).
20. **Home is the folded pose** (decided 2026-11-16): `home` for the SO-101 becomes the compact rest position the builder always returns the arm to, with the gripper slightly open. Today's `home` (reaching forward, 5 cm up) is renamed `ready` and stays teleop's and the fake arm's start. The joint numbers come from the real arm: lab check 8.16.
21. **AI budget and safety limits in the hub's own ⚙.** They're on `/settings` but not in the settings that open from the gear on the designed hub (lab check 6.3). Same controls, same place.
22. **Ask bar: icons centred in their cells** (designed hub; they sit off-centre between the vertical lines, lab check 1.3).
23. **Startup: find the stutter.** About one start in three or four, the core stutters as it loads in (lab check 1.3, lab desktop); opening and closing modules also felt a bit laggy (1.1). Find what hitches (something built or loaded at that moment) and move it earlier. Playing a recorded video instead is an idea, not this job (`docs/plan/ideas.md`).
24. **Teleop readout: "outside model limit" shown wrongly.** On `so101-green`, `elbow_flex` read "97.4 clamped by driver → 96.8; outside model limit" while inside the limit (lab check 8.9). The flag should compare with the limit actually in force.
25. **Green camera names.** Unplugging the wrist camera removed `usb-0:7` (lab check 8.15): `so101-green-cam-a` → `so101-green-cam-wrist`, `-cam-b` (socket 8) → `so101-green-cam-stand`. The white arm's names say the opposite (stand in 7, wrist in 8): leave them until lab check 3.9 says which is right.

## Done
- 1. **Arm moves without asking** (done 2026-11-14, PR #73). Every brain tool on the allow list; a test checks it. Lab: the no-prompt check in lab-checklist part 0.
- 2. **Limits that can be turned off** (done 2026-11-14, PR #75). `limits:` in the venue file and Settings → Safety limits; `limits_locked: true` on visit-day. Lab: lab-checklist part 6.
- 3. **The floor at −0.5 cm** (done 2026-11-14, PR #76). `min_z_cm: -0.5` in both venues, teleop the same number. Lab: the stepped ruler check in lab-checklist part 3.
- 4. **The greeting from a recording** (done 2026-11-14, PR #77). Time of day + hint only, saved per voice in `recordings/greetings/`. Lab: lab-checklist part 9b.
- 5. **The AI budget on the Settings page.** (done 2026-11-14, PR #78). The field was there; the brain now reads the budget live. Lab: lab-checklist part 6.
- 16. **"Give me a lab status report"** (done 2026-11-16). The `lab_status` read tool (hub server, on the shared MCP server, so the hub's chat and AI tools both get it). Lab: ask the hub "give me a status report".
- 7. **Stop LeLab** (done 2026-11-16). Training page button (brain's computer, confirmation) and `lab-os green --stop`: SIGINT then SIGTERM to the LeLab the launcher started (pid + start time in `logs/green-lelab.json`), nothing else. Lab: start it from the Training page, then Stop LeLab.
- 8. **The Quests in the device list** (done 2026-11-16). `quest-a` (…300FG, the builder's), `quest-b` (…3053L), `quest-c` (…3034N) in `config/devices.yaml`, told apart by serial (no labels); B or C is on loan, which one isn't known. The hub page in a Quest: `/design?device=quest-a`.
- 9. **Esc in teleop leaves full screen** (done 2026-11-16). On the teleop page on its own, full screen locks Esc (Keyboard Lock), and Esc in desktop control lets go of the pointer itself, so it stops the arm and stays full screen; the hub already did this. Lab: lab-checklist 6.7.
- 11. **VR hub: the chat doesn't scroll** (done 2026-11-16). The answer under the core showed its *first* three lines, so the rest of a long answer never appeared; now the newest three, "…" in front when earlier ones scrolled away (`hub/web/xr/ask.js`). Lab: lab-checklist part 10.
- 13. **1:1 teleop scale, the part without the lab** (done 2026-11-16). No scale error in the chain (model, units, 3D arm, gripper point); fixed the hand's base on a headset without a floor (`docs/dev/GOTCHAS.md`). Lab: checks 7.2–7.4.
- 15. **Camera names: stand and wrist** (done 2026-11-16). `so101-white-cam-stand` / `-cam-wrist` in `devices.yaml`, the tool description and the docs; "overhead" → "stand camera". The green cameras keep `-a`/`-b` until the lab check says which is which.
- 14. **Teleop page: the 3D view and the joint readout in their own boxes.** (done 2026-11-14, PR #79). Fixed 3D box, one fixed-height row per joint beside it. Lab: lab-checklist part 6.
- 17. **The training launcher refuses while anything else has a green port** (done 2026-11-17, PR #102). Checked whether or not LeLab runs; only LeLab (told apart by its command line) may already hold a green port; a computer that can't tell refuses. Lab: lab-checklist 8.18.
- 18. **Green arms: the calibration file that matches the motors** (done 2026-11-17, PR #104). The driver reads what the motors hold and uses the equal file in LeRobot's folder (role folder first), says which, refuses if none; `calibration_file` gone. Same for the leader. Lab: lab-checklist 8.16, 8.17.
