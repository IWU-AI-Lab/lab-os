# Quick jobs

Small jobs that are **already decided** and can be built in one Claude Code session without the lab, or nearly. A session told "do some quick jobs" takes them from the top, does each completely (its own branch, tests without hardware, docs, `FEATURES.md`, a PR), and moves it to "Done" with the date and PR number. Anything that needs the lab gets a line in `docs/guides/lab-checklist.md` instead.

Not decided yet? It goes in `docs/plan/ideas.md`, not here. Bigger work is a focus step (`docs/plan/current-focus.md`).

## Queue
Two coding sessions may run at the same time, one for each lane (the builder, 2026-11-20). The prompt for lane 1: "Read AGENTS.md, then docs/plan/quick-jobs.md. Do the jobs in Lane 1 from the top, one at a time, until the lane is empty. Do not stop to ask between jobs." For lane 2, the same with "Lane 2". Each job moves to "Done" with its date and pull request. Each job adds its lab steps to `docs/guides/lab-checklist.md` (its rules: at most 3 questions in one step). Until Tuesday 2026-12-01, the builder wants as many jobs done as possible; after that, only fixes.

### Lane 1: voice and the hub pages
(Empty.)

### Lane 2: arms, teleop and VR
- 72. **Raspbot teleop as a page** (the builder, 2026-11-20). **Only after lab check N.11 says that raspbot1 joined the router; until then, skip this job.** A page drives raspbot1 (forward, back, turn, stop; its camera if easy) through the brain, with STOP and a freeze when input stops. Look first at Yahboom's own Raspbot v2 software and examples. Robots stay thin: a small program on the Raspbot, deployed from this repo.
- 94. **A plugged-in arm whose motors do not answer: a sentence and the fake arm** (the builder, 2026-11-23). Lab check N.17: with the white arm's USB connected and its motor power off, `lab-os serve` stopped with a LeRobot traceback (`docs/dev/GOTCHAS.md`, 2026-11-23). Make the brain catch the motor errors when it opens an arm (`RuntimeError` from the motor check, `ConnectionError` from a write) and print one sentence, for example "so101-white: the motors do not answer. Is the arm's power on?". When the arm was found plugged in (no `--arm`), the brain then starts with the fake arm, as it does for a busy arm. With `--arm so101-white`, it stops with the sentence and no traceback. Test it with a fake bus that raises.

### Last, when both lanes are empty
- 53. **Capital letters in content text.** A lot of text is all lowercase, for example on AI Control ("clipped", "arrived · clipped: …", "name home") and the status words. `docs/design/DESIGN.md` says labels are small CAPS and content is normal case. Start sentences and status words with a capital letter on every page. Names of commands, files, poses and settings stay as they are.

## Done
The jobs done up to 2026-11-23 (1 to 93) are in `docs/archive/quick-jobs-done-to-2026-11-23.md`. Put each new done job here, the newest first.
