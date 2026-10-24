#!/usr/bin/env bash
# PreToolUse hook for Bash: protects so101-green and the shared lerobot conda env.
# See CLAUDE.md "Hard rules". Denies outright; asks when a raw ttyACM/ttyUSB name is used.
cmd=$(jq -r '.tool_input.command // empty')

decide() {
  jq -n --arg d "$1" --arg r "$2" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: $d, permissionDecisionReason: $r}}'
  exit 0
}

# so101-green serial ports (by-id serial numbers).
if grep -qE '5B41531599|5B41533501' <<<"$cmd"; then
  decide deny "That is so101-green's serial port. Never open it (CLAUDE.md)."
fi

# Green calibration files.
if grep -qE 'huggingface/lerobot/calibration' <<<"$cmd"; then
  decide deny "LeRobot calibration cache belongs to so101-green's training project. Don't touch it."
fi

# Modifying the shared lerobot conda env or its source checkout.
if grep -qE '(-n|--name)[ =]lerobot\b|envs/lerobot|activate lerobot|~/lerobot\b|/home/[^/ ]+/lerobot\b' <<<"$cmd" &&
  grep -qE '\b(install|uninstall|remove|update|upgrade|rm|mv|develop)\b|pip |>' <<<"$cmd"; then
  decide deny "The lerobot conda env and ~/lerobot belong to the training project. Use lab-os's uv env."
fi

# Raw tty names can point at any arm after a re-plug.
if grep -qE '/dev/tty(ACM|USB)[0-9]' <<<"$cmd"; then
  decide ask "Raw ttyACM/ttyUSB names swap between boots; use /dev/serial/by-id/. Confirm this is not so101-green."
fi

exit 0
