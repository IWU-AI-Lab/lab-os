#!/usr/bin/env bash
# One-command setup for lab-os on a fresh Linux machine. No sudo, no conda.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null; then
  echo "==> Installing uv (to ~/.local/bin)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "==> Creating the lab-os environment (.venv)"
uv sync

if ! id -nG | grep -qw dialout; then
  echo "!!  You're not in the 'dialout' group, so serial ports (arms) won't open."
  echo "    Run: sudo usermod -aG dialout \"$USER\"   then log out and back in."
fi

[ -f .env ] || echo "==> Next: cp .env.example .env  and fill in real keys"

echo "==> Serial devices (by-id):"
ls -l /dev/serial/by-id/ 2>/dev/null || echo "    (none plugged in)"

echo "==> Running checks"
uv run pytest -q
