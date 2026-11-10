"""The Commits panel: commits per day from `git log` (all local and remote branches, no merges)."""

import subprocess
from datetime import date, timedelta
from pathlib import Path

from lab_os import REPO_ROOT


def commits_per_day(days: int = 14, repo: Path = REPO_ROOT, today: date | None = None) -> dict:
    """Counts for the last `days` days (today included, oldest first, zero days kept), by the
    commit date in this computer's time zone. `available: false` when git or the repo is missing."""
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    cmd = [
        "git",
        "-C",
        str(repo),
        "log",
        "--branches",
        "--remotes",
        "--no-merges",
        f"--since={start.isoformat()}T00:00:00",
        "--format=%cd",
        "--date=format-local:%Y-%m-%d",
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "days": days}
    counts = {(start + timedelta(days=i)).isoformat(): 0 for i in range(days)}
    for line in out.split():
        if line in counts:
            counts[line] += 1
    per_day = [{"date": d, "count": n} for d, n in counts.items()]
    return {"available": True, "days": days, "total": sum(counts.values()), "per_day": per_day}


def recent_commits(count: int = 8, repo: Path = REPO_ROOT) -> list[dict]:
    """The latest `count` commits (all branches, no merges), newest first: hash, date, subject.
    Empty when git or the repo is missing."""
    cmd = [
        "git",
        "-C",
        str(repo),
        "log",
        "--branches",
        "--remotes",
        "--no-merges",
        f"--max-count={count}",
        "--format=%h%x09%cd%x09%s",
        "--date=format-local:%Y-%m-%d",
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    rows = [line.split("\t", 2) for line in out.splitlines() if line.count("\t") >= 2]
    return [{"hash": h, "date": d, "subject": s} for h, d, s in rows]
