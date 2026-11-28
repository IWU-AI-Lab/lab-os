# Quick jobs

Small jobs that are **already decided** and can be built in one Claude Code session without the lab, or nearly. A session told "do some quick jobs" takes them from the top, does each completely (its own branch, tests without hardware, docs, `FEATURES.md`, a PR), and moves it to "Done" with the date and PR number. Anything that needs the lab gets a line in `docs/guides/lab-checklist.md` instead.

Not decided yet? It goes in `docs/plan/ideas.md`, not here. Bigger work is a focus step (`docs/plan/current-focus.md`).

## Queue
Three coding sessions may run at the same time, one for each lane (the builder, 2026-11-25; two since 2026-11-20). The prompt for lane 1 (one job per session, the builder 2026-11-25; type `/clear` before the next): "Read AGENTS.md, then docs/plan/quick-jobs.md. Do the top job in Lane 1, then stop. Do not stop to ask. Your final report is at most two parts: one sentence on what the job did, then each problem you did not solve, one line each (leave this out if there are none)." For lanes 2 and 3, the same with "Lane 2" or "Lane 3". To run a lane to its end with no one there (the builder, 2026-11-26): "Read AGENTS.md, then docs/plan/quick-jobs.md. Do every job in Lane 1, in order. Merge each one before you start the next. Do not stop to ask. At the end, report for each job one sentence on what it did, then each problem you did not solve, one line each." This report replaces the report form in `AGENTS.md` for lane jobs; the details go in the pull request. **Lane 2 runs on the lab desktop** (the builder, 2026-11-25): its jobs need the arms, the cameras, `ssh raspbot1` or the brain's log. In every lane: when raspbot1 or an arm is off (the builder is not in the lab), build and test on the fake device, and leave the deploy and the real test to the job's lab step. In lanes 1 and 3, a job marked **(lab desktop)** needs the brain's log or the lab's devices: a session on another computer skips it and does the next job. The prompt on the lab desktop for those: "Read AGENTS.md, then docs/plan/quick-jobs.md. Do the top job marked (lab desktop) in Lane 1 or Lane 3, then stop." with the same report. Each job moves to "Done" with its date and pull request. Each job adds its lab steps: a step for a moment of the demo goes to `docs/guides/lab-checklist.md` (the demo run); every other step to `docs/guides/lab-checklist-after-demo.md` (its rules: at most 3 questions in one step). Until Tuesday 2026-12-01, the builder wants as many jobs done as possible; after that, only fixes. The lanes work on `main`; the demo's fallback is frozen on the branch `demo-freeze` (`docs/plan/log.md`, 2026-11-25).

### Lane 1: the hub (since 2026-11-26; the Raspbot before, all done)

### Lane 2: the robot pages, VR and AR

### Lane 3: the shared parts and the other pages

### Backlog: do not start until the builder says
The builder chooses when these start (2026-11-25). A session never takes a job from here by itself.
- **A black hole background** (the builder, 2026-11-26; a first version to iterate on; moved from Lane 3, where it was numbered 160, on 2026-11-26). Part 6 of `docs/plan/ux-review.md`. Lab: add a step to the after-demo list.
- **The camera pictures flicker on the Teleop page on slower devices.**
- **Animations stutter the first few times on every device.**
- **The arm cameras' pictures are low in resolution** on the Cameras page (all 4), and Quest view too (lab check T.4).
- **The mini core in VR Teleop stays at one awkward place** (lab check T.2). Make it follow the view, or else keep it on the Teleop info card.
- **The wave in visitor mode needs work** (lab check A.2).
- **The ambient sound plays while the "lab-os is off" page is open.**
- **The nearest microphone answers** did not tell the desktops apart (lab check M.2). The microphones were within 1 m of each other.
- **Fan noise:** measure the roof fan's noise and allow for it in the wake word.
- **Tic-tac-toe pieces:** the builder moved some pieces by about 0.5 cm or turned them so that the gripper took them well. A piece not held in its middle can land a little outside its cell.
- **Chrome on the builder's laptop cannot open the hub** (the builder, 2026-11-25: after the demo). Run lab step M.6 (`docs/guides/lab-checklist-after-demo.md`), then fix the cause that its error code shows (quick job 130, `docs/dev/GOTCHAS.md`). Until then, use Firefox on the laptop.
- **A contributing guide and an architecture page** (the builder, 2026-11-25), simple and clear. The contributing guide: set up, branch and pull request, tests, the principles in a short list; `AGENTS.md` points to it. The architecture page: the parts (brain, hub, robot plug-ins, safety layer, AI tools), how a command goes from the Quest to the arm, where to add a robot.

## Done
See the [completed quick jobs through 2026-11-27](../archive/quick-jobs-done-2026-11-27.md).
- 166. **Mute, solo and one greeting** (done 2026-11-27) (the builder, 2026-11-27, in a chat session). Every screen that started together played its own greeting at the same time, and the phone's answers played only on the phone. Each device card and each row of the Devices list in the Command Center now has a speaker icon with **M** (red: mute: nothing plays there, the answers and the hub's own sounds too) and **S** (amber: solo, the answers and greetings from every microphone play only on the soloed devices; the other screens make no sound). One greeting plays for all the screens that start together, on the first device of ⚙ → The Lab → **Greeting Plays On** (default: the Newline, then the brain's computer) that is on and not muted; else on the screen that started. The Quest's own page keeps its own sound. The Devices list is one line for each device, without ⤢, with **Hide all** and **Mute all** above it; the Sound setting in the focus window is gone (M replaces it). Lab: part SR in `docs/guides/lab-checklist-after-demo.md`.
