# Current Focus: the JARVIS core (brain + plug-in interfaces)

**Read this at the start of every Claude Code session.** It says what to work on *now*. The long-term plan, decisions and module list live in **lab-jarvis-log.md**; this file only sets the current priority. When this focus is done, move it to `docs/archive/` and write the next one. Previous focus: the teleop demo, closed 2026-10-30 (`docs/archive/focus-2026-10-teleop-demo.md`; what's left of it is in `docs/ideas.md` → "On hold").

**Status: draft (2026-10-30).** Refine it with the builder at the start of the first session on this focus, then drop this line.

---

## The goal right now
One `lab-os` brain program that knows which plug-ins the venue has, starts them, and shows which devices are there and healthy (**roll call**). Teleop becomes its first module instead of a separate program. Robots, inputs and clients plug in and out without touching the core (log → "Architecture sketch").

## Before the lab router arrives
**Can be done now:** everything that runs on one computer with fake devices or USB-attached ones: the interfaces, the registry, roll call, the brain program, the message protocol, tests, the install on Windows/macOS. Mostly at home, against fakes.
**Waits for the router (Milestone 1):** robots reporting in over the network (Raspbots, Pis, Jetsons), SSH keys + nicknames, deploys, network checks.

## Rules for this focus
1. **Grow it out of the teleop code** (decision 2026-10-24): extract what exists and is used. A slot gets a formal interface only when a second real plug-in needs it.
2. **Fake first, at home**: every step testable without hardware; then once on real devices (ask before anything moves).
3. **Roll call is read-only**: it never moves anything and never opens an off-limits port or camera (`so101-green`, the training cameras), not even "just checking".
4. **Portable**: Linux, Windows, macOS (decision 2026-10-27).
5. **Plain names** in code, show names in config (decision 2026-10-28).

## Steps (each one is a small, testable win)
1. **Map what exists.** The teleop work already has core-shaped pieces: the `Arm` protocol (`robots/base.py`) with three drivers (fake, xArm, SO-101); the device registry with off-limits devices (`config/devices.yaml`, `lab_os.devices`); venue profiles (`lab_os.venues`); the WebSocket server with control handover and STOP (`teleop/server.py`); the message format (`docs/protocol.md`); the theme file. One page (`docs/architecture.md`): what each piece is, which slot it belongs to, what's still teleop-specific.
2. **Plug-in description.** A plug-in says its name, slot, requirements (Python extra, OS, device in `devices.yaml`) and offers a read-only `check()` that returns a short health report. Start with the robot slot ("every robot plug-in declares its requirements" is already a project rule).
3. **Roll call command.** `lab-os roll-call`: for the venue's devices, is it plugged in? requirements met? off limits? Prints a table and writes a report file (the seed of the troubleshooting suite). Robots are optional (decision 2026-10-28): missing ones are normal, not errors.
4. **The brain program.** `lab-os serve`: one process that loads the venue's plug-ins and serves one page with the roll call and the teleop. `lab-os-teleop` becomes a module of it (the old command keeps working until it's replaced).
5. **Inputs as plug-ins.** Quest page, desktop control and replay become the input slot, picked in the page instead of by command-line flags.
6. **Robots report in.** A stand-in "network robot" talking to the brain over a WebSocket on `localhost`, so the network path exists and is tested before the router does.

## Open questions for the builder
- What should the brain's first screen show? (Guess: roll call + a button into teleop.)
- Second robot through the core: `xarm1` (USB, works now) or a Raspbot (needs the router)?
- Troubleshooting suite: fold its robot and Quest checks into roll call now, the rest later?

## Hacks to clean up
- `robots/xarm.py`: 240°/1000 units is the datasheet scale, not measured (zero = the "Run" pose, signs observed 2026-10-27). Motion tuning (`lead_s` 0.3 s, `max_deg_per_s` 120, `idle_read_after_s` 0.6, `min_read_interval_s` 0.25) is from first tests, not optimized. Default limits (until hand calibration) come from the builder's grab script.

## Up next (after this focus)
Milestone 1, "Connected lab", once the router is here (lab-jarvis-log.md → "Milestones"). On hold until then, or until picked: `docs/ideas.md` → "On hold".
