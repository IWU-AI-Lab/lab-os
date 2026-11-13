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
- **Workspace:** each joint stays 3° inside its limits (soft limits), and the gripper and wrist stay at least 1 cm above the table (teleop's `floor_m`, the AI tools' `min_z_cm`). A box around the table area is not built yet.
- **No snapping:** relative (clutch) control, gentle ramps, start from the arm's current pose.

## Visitors
- One person at the controls; others stay outside the arm's reach.
- An operator stands next to the arm with the stop within reach at all times.
- Only approved demo commands; no free-form AI control of motion with visitors.

## AI tools
An AI tool (Claude Code, Codex, …) moves an arm only through the brain's tools on the brain's own computer: the same limits as teleop, small steps per call, and **a person approves every move** (never "always allow" a move tool). The hub's built-in chat can't move anything. `docs/guides/ai-control.md`.

## Remote mode
Remote sessions (from home, Remote Control, any off-site connection) = **no motion by default**. Read-only checks only, unless someone is physically next to the robot.

## Drones
Excluded from AI, voice and visitor control.

## The green arms (the training set)
`so101-green` is the builder's training set. Since 2026-11-12 lab-os may drive it like `so101-white` (focus step 11, built the same day), with four rules (`CLAUDE.md`): never change its motor IDs or firmware, its calibration is read-only, never touch the `lerobot` conda env, and never open a port that LeLab or a training run is using. Same safety as every arm: ask before it moves, STOP from every screen.
