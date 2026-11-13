# Early notes from the log (2026-10-20 to 2026-10-23)

**Archived 2026-11-13** from `docs/plan/lab-jarvis-log.md`, as they were: the first planning notes, now history. What they decided is in the log's decisions table (2026-10-20 to 2026-10-23); the teleop they shaped is built (`docs/guides/quest-setup.md`), and the goals they set are in the log's "The goal".

## Quest teleop input & display (2026-10-23) — details in archive/focus-2026-10-teleop-demo.md
Inputs: **controllers first** (grip = clutch, analog trigger = gripper, button = stop), **then hand tracking** (wow); keep both. Display: passthrough + minimal overlay (status, stop, workspace box, visitor hint); later ghost arm + camera feed; cast to a monitor.

## Teleoperation module: "your hand becomes the robot's hand" (2026-10-23)
**Origin:** first-principles "what would impress most?" check, inspired by Tesla's Oct 15, 2026 Roadster demo (staged at a private site; double-take reactions; skepticism about unproven claims). **Lessons:** break an expectation; seconds to understand; narrow, controlled demo; filmable; never overclaim; fewest moving parts.
**The module:** Quest input → arm copies it live. Practical and true (teleop is how robots get taught). Needs only Quest + computer + arm (USB). Fast-tracked; rest of the plan stays.

## Grill session answers (2026-10-20)
1. One thing this semester: most lab devices connected, AI agents able to access them. 2. For: primarily the builder. 3. MVP done: it connects and inspires continuing. 4. 3–7 h/week. 5. After May 2027: handoff docs; builder lives ~5 min from campus. 6. Professor: "connect devices for faster development." 7. Willing to learn Unity if needed. 8. Visitors: ~30 s in the headset. 9. Camera privacy deferred. 10. Worst failures → offline lite mode. 11. Auto-restart + AI diagnosis. 12. AI budget ≤ $20/month. 13. Modularity via AI; hardcode when needed. 14. Safety in the harness.
- **2026-10-23:** also **impress** → teleop fast track; visitor routes may not pass the lab → **must travel**; trained arm should **generalize** → "look, then reach" + pretrained models.

### The walk-in moment (2026-10-20)
Open the door → one trigger → screens on → greeting → use. Animation ≤ several seconds.
