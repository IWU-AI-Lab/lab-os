"""The greeting after the start press (DESIGN.md → "Startup"): "Good morning / afternoon / evening."
and one line of real news when there is some, else the persona's `greeting` line. The news is built
here from real facts, never by the persona or the AI. So far, in this order:

1. a step of the current focus finished today or yesterday (docs/plan/current-focus.md, `(done …)`);
2. a date from the place's calendar within the next two weeks (place.yaml → `calendar`);
3. a busy day: at least BUSY_COMMITS commits yesterday, or today so far.
"""

from datetime import date, datetime, timedelta
from pathlib import Path

from lab_os.hub.commits import commits_per_day
from lab_os.hub.project import parse_steps

BUSY_COMMITS = 10
CALENDAR_DAYS = 14


HELLOS = ("Good morning.", "Good afternoon.", "Good evening.")


def time_of_day(now: datetime) -> str:
    if 5 <= now.hour < 12:
        return HELLOS[0]
    if 12 <= now.hour < 18:
        return HELLOS[1]
    return HELLOS[2]


def _when(days: int) -> str:
    return {0: "today", 1: "tomorrow", -1: "yesterday"}.get(days, f"in {days} days")


def step_news(focus_text: str, today: date) -> str | None:
    recent = [
        s
        for s in parse_steps(focus_text)
        if s.get("done_on") and 0 <= (today - date.fromisoformat(s["done_on"])).days <= 1
    ]
    if not recent:
        return None
    s = max(recent, key=lambda s: (s["done_on"], s["n"]))
    days = (today - date.fromisoformat(s["done_on"])).days
    return f"Step {s['n']}, {s['title']}, was finished {_when(-days)}."


def calendar_news(calendar: list[dict], today: date) -> str | None:
    upcoming = []
    for item in calendar or []:
        try:
            day = date.fromisoformat(str(item["date"]))
        except (KeyError, ValueError):
            continue
        if 0 <= (day - today).days <= CALENDAR_DAYS and item.get("what"):
            upcoming.append((day, str(item["what"]).rstrip(".")))
    if not upcoming:
        return None
    day, what = min(upcoming)
    return f"{what} {_when((day - today).days)}."


def commit_news(per_day: list[dict], today: date) -> str | None:
    counts = {d["date"]: d["count"] for d in per_day}
    yesterday = counts.get((today - timedelta(days=1)).isoformat(), 0)
    now = counts.get(today.isoformat(), 0)
    if now >= BUSY_COMMITS:
        return f"A busy day so far: {now} commits today."
    if yesterday >= BUSY_COMMITS:
        return f"Yesterday was a busy day: {yesterday} commits."
    return None


def greeting(
    persona_line: str,
    focus_file: Path,
    repo: Path,
    calendar: list[dict] | None = None,
    now: datetime | None = None,
) -> dict:
    """{"hello", "news" (or None), "source" (step | calendar | commits | persona), "text"}."""
    now = now or datetime.now()
    today = now.date()
    try:
        focus_text = focus_file.read_text()
    except OSError:
        focus_text = ""
    commits = commits_per_day(2, repo, today)
    candidates = [
        ("step", lambda: step_news(focus_text, today)),
        ("calendar", lambda: calendar_news(calendar or [], today)),
        ("commits", lambda: commit_news(commits.get("per_day") or [], today)),
    ]
    hello = time_of_day(now)
    for source, make in candidates:
        news = make()
        if news:
            return {"hello": hello, "news": news, "source": source, "text": f"{hello} {news}"}
    line = persona_line.strip()
    return {
        "hello": hello,
        "news": None,
        "source": "persona",
        "text": f"{hello} {line}" if line else hello,
    }
