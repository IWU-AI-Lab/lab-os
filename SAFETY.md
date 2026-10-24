# Safety

Short and printable. Applies to every robot, every venue, every session.

## Stop
- **Physical:** pull the arm's power plug. Know where it is before the first motion.
- **Software:** the STOP button (Quest overlay / screen) and `Ctrl+C` in the teleop program both freeze the arm.
- **Test both stops** at the start of every session and every demo.

## Dead-man rule
The arm **freezes** whenever any of these happens: clutch released · hand/controller tracking lost · headset taken off · connection drops · program crashes. Motion only continues while the operator is actively holding the clutch.

## Limits
- **Speed:** capped per venue (`config/venues/*.yaml`, `max_speed_scale`). Visitors get the slowest setting.
- **Workspace:** a box around the table area; commands outside it are clamped. Red warning near the edge.
- **No snapping:** relative (clutch) control, gentle ramps, start from the arm's current pose.

## Visitors
- One person at the controls; others stay outside the arm's reach.
- An operator stands next to the arm with the stop within reach at all times.
- Only approved demo commands; no free-form AI control of motion with visitors.

## Remote mode
Remote sessions (from home, Remote Control, any off-site connection) = **no motion by default**. Read-only checks only, unless someone is physically next to the robot.

## Drones
Excluded from AI, voice and visitor control.

## Arms that aren't ours
`so101-green` belongs to another project: never connect to it, never recalibrate it (see `CLAUDE.md`).
