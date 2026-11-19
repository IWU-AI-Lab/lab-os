# CLAUDE.md — lab-os

The rules for Claude Code are the same as for every agent. They are in `AGENTS.md`, the one copy. Change them there, not here.

@AGENTS.md

## Claude Code only
- The hook (`.claude/hooks/guard.sh`) and the permissions (`.claude/settings.json`) apply to Claude Code. They deny writes to LeRobot's cache and changes to the `lerobot` env, and they ask before `sudo`, `rm`, reboots and force pushes.
