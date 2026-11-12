#!/usr/bin/env bash
# PreToolUse hook for Bash: protects the green arms' calibration and the shared lerobot conda env.
# See CLAUDE.md "Hard rules". Since focus step 11 (2026-11-12) the green ports aren't blocked here:
# lab-os may open them, and lab_os.devices refuses a port another program (LeLab) has open.
# Denies outright; asks when a raw ttyACM/ttyUSB name is used. Tests: tests/test_guard_hook.py.
cmd=$(jq -r '.tool_input.command // empty')

decide() {
  jq -n --arg d "$1" --arg r "$2" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: $d, permissionDecisionReason: $r}}'
  exit 0
}

# LeRobot's cache: the green arms' calibration (and LeLab's saved ports). Reading is fine
# (ls, cat, jq, diff, ...); anything that could write, move or delete there is denied.
if grep -qE 'huggingface/lerobot' <<<"$cmd"; then
  quiet=$(sed -E 's/[0-9]?>&[0-9]//g; s#[0-9&]?> */dev/null##g' <<<"$cmd") # 2>/dev/null, 2>&1: fine
  if grep -qE '(^|[;&|( ]) *(rm|mv|cp|tee|touch|truncate|chmod|chown|ln|install|rsync|dd|shred|unlink|mkdir|rmdir|python3?|uv|lerobot[-_a-z]*|lelab)\b|\bsed +(-[a-zA-Z]*i|--in-place)|\bperl +-[a-zA-Z]*i|-delete|-exec|>' <<<"$quiet"; then
    decide deny "The green arms' calibration in LeRobot's cache is read only (CLAUDE.md): read it, never write, move or delete there."
  fi
fi

# Modifying the shared lerobot conda env or its source checkout.
if grep -qE '(-n|--name)[ =]lerobot\b|envs/lerobot|activate lerobot|~/lerobot\b|/home/[^/ ]+/lerobot\b' <<<"$cmd" &&
  grep -qE '\b(install|uninstall|remove|update|upgrade|rm|mv|develop)\b|pip |>' <<<"$cmd"; then
  decide deny "The lerobot conda env and ~/lerobot belong to the training project. Use lab-os's uv env."
fi

# Raw tty names can point at any arm after a re-plug.
if grep -qE '/dev/tty(ACM|USB)[0-9]' <<<"$cmd"; then
  decide ask "Raw ttyACM/ttyUSB names swap between boots; use /dev/serial/by-id/. Confirm which arm this is and that LeLab isn't using it."
fi

exit 0
