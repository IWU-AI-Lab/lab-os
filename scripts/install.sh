#!/usr/bin/env bash
# Make a new Linux computer ready as the lab-os brain (quick job 150). No sudo, no conda.
# It installs uv, makes the project's environment (.venv, with LeRobot for the SO-101 arms), then
# runs `lab-os setup`: that checks every other part, installs what needs no sudo, and prints the
# sudo commands to paste. Running it again is safe.
# --no-so101: a computer that drives no SO-101 arm (no LeRobot and PyTorch, ~5 GB less).
# (--so101 is the default now; the old option still works.)
set -euo pipefail
cd "$(dirname "$0")/.."

extra=(--extra so101)
setup=()
case "${1:-}" in
  --no-so101) extra=(); setup=(--no-so101) ;;
  --so101 | "") ;;
  *) echo "Unknown option: $1 (use --no-so101 or nothing)"; exit 2 ;;
esac

if ! command -v uv >/dev/null; then
  echo "==> Installing uv (to ~/.local/bin)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "==> Making the lab-os environment (.venv)"
uv sync "${extra[@]}"

echo "==> Checking the other parts"
uv run lab-os setup "${setup[@]}"
