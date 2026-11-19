# The long-term vision: a real JARVIS

**What this is:** where lab-os is heading over years, not a list of tasks. Concrete pieces become ideas in `docs/plan/ideas.md` (one entry each) and then focus steps, one small win at a time. Written 2026-11-14 from a spec the builder drafted with ChatGPT, shortened and checked against what exists.

## The goal
One AI brain, today's `lab-os serve`, that understands the place it's in, works the computers and devices around it, helps design and build things, keeps track of projects, and coordinates everything. It's the Iron Man workshop as far as today's technology allows. It grows out of the existing brain, hub, MCP tools and config. It is never a second system next to it.

## Things that shape it
- **The builder graduates in May 2027.** After that, lab-os goes home with the builder and runs there (another place's config folder, `docs/dev/places.md`). It has to run at home as well as in the lab (the builder will probably use it there).
- **The lab must be able to unplug it cleanly.** When lab-os leaves, nothing tangled stays behind for other students and projects. In practice:
  - everything lab-specific lives in the lab's config folder;
  - nothing is installed system-wide on lab computers without a written undo;
  - robots, Pis and the training set keep working without lab-os;
  - no other project depends on lab-os being there;
  - the borrowed devices (the green set) are left as they were found.

  A "leaving the lab" checklist will be written before May 2027.
- **No ceiling camera.** Cameras are at table height or close to it: each SO-101's stand camera (on the 3D-printed stand, about 2 ft up) and wrist camera, plus webcams, laptop and phone cameras, and the Kinect. Seeing the room means combining several of these.
- **Look for existing work first** (AGENTS.md): most pieces below exist somewhere already. Use and extend them before building our own.

## The parts, and where they stand
1. **Personal assistant:** long-term memory of the lab, projects, people and decisions; tasks and reminders; calendar and email (with permission); research and summaries; a daily briefing. Can tell a chat from a project question from a command that changes real things. *Today:* the hub's chat with the project read tools, personas, the greeting with real facts.
2. **The room itself:** lights, plugs, displays, speakers, sensors; modes like "demo", "shutdown", "maintenance". "Get the lab ready for a demo" switches things on and checks the robots. Built on `devices.yaml`, never a separate device system. *Today:* the device list; smart plugs are an idea.
3. **Computers and software:** opening apps and pages, files, documents, code, installing with permission, watching performance, handing big jobs to coding agents and following their progress. *Today:* the project tools, `/perf`; the "send to harness" direction (`lab-jarvis-log.md` → "AI-assisted development").
4. **Seeing:** reading camera pictures, labels, screens and drawings; noticing changes; helping troubleshoot from a photo ("what's wrong with this arm?"). Continuous watching only step by step, with privacy, cost and bandwidth in mind. *Today:* `camera_snapshot`, `pose_view`.
5. **Engineering partner** (one of the most important): from requirements to calculations, parts, CAD, wiring, code, simulation and a working build, with a person approving each stage. Uses the robot list, models, calibration and MCP tools. *Today:* the robot tools; the rest is ahead.
6. **Status and health:** devices that go offline, unusual behaviour, events over time, "JARVIS, give me a lab status report". Real safety and security stay with dedicated hardware; the AI only adds awareness. *Today:* the status strip, servo health logs, AI spend.
7. **Outside devices** (low priority): e.g. a car's diagnostics through an OBD-II adapter.
8. **Research and many agents:** bigger jobs broken into pieces, handed to agents, checked, and written up. *Today:* MCP, Claude Code, the planning/coding session workflow.
9. **The command center:** the hub grows into one place for all of the above: status, robots, cameras, agents, projects, events. It's reachable by voice, touch, phone, other computers and the Quest, with one source of truth. *Today:* the hub, the VR hub, voice, devices (step 8).

## How it's built
- **Shared foundations before features:** one picture of the devices and their state, one tool interface for every AI, one project context, one event and automation system, one permission and safety layer. A new ability should reuse these, not bring its own.
- **Human approval** for anything that moves real equipment, touches security or money, or can't be undone; the robots' safety layer stays in charge of motion.
- **Visible and recorded:** important actions, errors and states are logged and shown.
- **Graceful:** unplugged devices, timeouts and missing services are expected, not crashes.
- The project rules still apply: fake first, offline first, small steps, config not code, docs updated.
