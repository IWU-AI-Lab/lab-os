"""The Current Project panel: read the Steps list in docs/current-focus.md.

Each step is a top-level numbered line with a bold title, e.g. `1. **Plain hub.** ...`; a finished
one has `(done YYYY-MM-DD)` right after its title. The panel shows "Step N of M" and the title of
the first step that isn't done.
"""

import re
from pathlib import Path

from lab_os import REPO_ROOT

FOCUS_FILE = REPO_ROOT / "docs" / "current-focus.md"

_STEP = re.compile(r"^(\d+)\.\s+\*\*(.+?)\*\*(.*)$")
_DONE = re.compile(r"^\s*\(done \d{4}-\d{2}-\d{2}\)")


def parse_steps(text: str) -> list[dict]:
    """The steps under `## Steps` (the heading may go on, e.g. `## Steps (each one ...)`), until
    the next `## ` heading: number, title, done."""
    steps = []
    in_steps = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_steps = line.split("(")[0].strip() == "## Steps"
            continue
        m = _STEP.match(line) if in_steps else None
        if m:
            title = m.group(2).strip().rstrip(".").strip()
            done = bool(_DONE.match(m.group(3)))
            steps.append({"n": int(m.group(1)), "title": title, "done": done})
    return steps


def focus_title(text: str) -> str | None:
    """The focus's name from the first heading: `# Current Focus: the hub` → `The hub`."""
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].split(":", 1)[-1].strip()
            return title[:1].upper() + title[1:] if title else None
    return None


def project_summary(path: Path = FOCUS_FILE) -> dict:
    """What the panel shows. `available: false` when the file is missing or has no steps."""
    try:
        text = path.read_text()
    except OSError:
        return {"available": False}
    steps = parse_steps(text)
    if not steps:
        return {"available": False}
    total = max(s["n"] for s in steps)
    current = next((s for s in steps if not s["done"]), None)
    return {
        "available": True,
        "focus": focus_title(text),
        "step": current["n"] if current else total,
        "of": total,
        "next": current["title"] if current else None,
        "steps": steps,
    }
