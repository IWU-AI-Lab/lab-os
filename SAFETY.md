# Safety

Short and printable. Applies to every robot, every venue, every session.

## Stop
- **Physical:** pull the arm's power plug. Know where it is before the first motion.
- **Software:** the STOP button (every page, any screen; A/X on the Quest) freezes the arm and holds it. `Ctrl+C` in the brain's terminal ends the program: the SO-101 then goes **limp** (torque off), so hold it or park it low first.
- **Test both stops** at the start of every session and every demo.

## Dead-man rule
The arm **freezes** whenever any of these happens: clutch released · hand/controller tracking lost · headset taken off · connection drops · program crashes. Motion only continues while the operator is actively holding the clutch.

## Limits
- **Speed:** capped per venue (`config/venues/*.yaml`, `max_speed_scale`). Visitors get the slowest setting. Teleop's **1:1 mode** has its own per-venue cap, `one_to_one_max_deg_per_s` (lab: 180°/s per joint; off on visit days), because it follows the hand as fast as it moves; a servo at 60 °C slows it down.
- **Workspace:** each joint stays 3° inside its limits (soft limits), and the gripper and wrist stay above a floor, `min_z_cm` in the venue, for the AI tools and teleop alike. Since 2026-11-18 (quick job 28) it's measured from the table: 1.1 cm in both venues. Each arm's `table_z_cm` in `config/devices.yaml` says where the table is in its own heights (`so101-white` stands on the stand camera's 1.6 cm plate: −1.6). Before: −0.5 cm from the arm's base (2026-11-14, the same place for `so101-white`), 1 cm before that. The height reading may itself be 1–2 cm low (GOTCHAS 2026-11-12): check it with a ruler before trusting the floor near the table. A box around the table area is not built yet.
- **Limits that can be switched off** (decision 2026-11-13, built 2026-11-14): the AI tools' per-move limit, the speed cap (`max_speed_scale`, `one_to_one_max_deg_per_s`) and the floor, each `on` by default (`limits:` in the venue file, or Settings → Safety limits; applies when the brain restarts, which then prints `LIMITS OFF …`). Never on a public venue or one with `limits_locked: true` (the visit-day venue): the brain refuses to start with one off there, and Settings refuses to switch one off. **Always kept:** STOP on every screen, the soft joint limits, one controller at a time.
- **No snapping:** relative (clutch) control, gentle ramps, start from the arm's current pose.

## Visitors
- One person at the controls; others stay outside the arm's reach.
- An operator stands next to the arm with the stop within reach at all times.
- Only approved demo commands; no free-form AI control of motion with visitors.

## AI tools
An AI tool (Claude Code, Codex, …) moves an arm only through the brain's tools on the brain's own computer: the same limits as teleop, small steps per call. Claude Code doesn't ask before each move (decided 2026-11-13, the move tools are on the repo's allow list), because STOP on every screen is enough when it does something it shouldn't; a coding session still asks before it runs anything that moves a real arm (CLAUDE.md). Someone stays near the arm with STOP in reach. The hub's built-in chat can't move anything. `docs/guides/ai-control.md`.

## Remote mode
Remote sessions (from home, Remote Control, any off-site connection) = **no motion by default**. Read-only checks only, unless someone is physically next to the robot.

## Drones
Excluded from AI, voice and visitor control.

## The green arms (the training set)
`so101-green` is the builder's training set. Since 2026-11-12 lab-os may drive it like `so101-white` (focus step 11, built the same day), with four rules (`CLAUDE.md`): never change its motor IDs or firmware, its calibration is read-only, never touch the `lerobot` conda env, and never open a port that LeLab or a training run is using. Same safety as every arm: the builder present when it moves, STOP from every screen.
