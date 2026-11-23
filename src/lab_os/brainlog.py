"""The brain's log in a file too (quick job 85), so that a session can read what happened in the
lab without the builder copying the terminal: `lab-os logs` prints the end, `lab-os logs --at 18:14`
the minutes around a time.

The file is `logs/brain.log` in the place's `local/` folder (`config/local/` for the lab: not in
git). A new file starts at midnight; the last `KEEP_DAYS` days are kept (`brain.log.2026-11-21`).
The lines are the terminal's, with the date in front and no colours."""

import logging
import re
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from lab_os import config

log = logging.getLogger(__name__)

LOG_FILE = "brain.log"
KEEP_DAYS = 4
LAST_LINES = 80  # `lab-os logs` with no time: this many entries from the end
AROUND_MIN = 3  # `--at`: this many minutes before and after the time
FILE_FORMAT = "%(asctime)s %(levelname)s %(message)s"
FILE_TIME = "%Y-%m-%d %H:%M:%S"
STAMP = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) ")


def log_folder(folder: Path | None = None) -> Path:
    """Where the brain's log files are (the place's `local/logs/`)."""
    return config.local_dir(folder) / "logs"


def log_to_file(folder: Path | None = None) -> Path | None:
    """Send the log to the file as well as the terminal. Returns the file, or None when it can't
    be written (the brain runs anyway, and says so)."""
    path = log_folder(folder) / LOG_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = TimedRotatingFileHandler(
            path, when="midnight", backupCount=KEEP_DAYS, encoding="utf-8"
        )
    except OSError as e:
        log.warning("the log goes to the terminal only: can't write %s (%s)", path, e)
        return None
    handler.setFormatter(logging.Formatter(FILE_FORMAT, datefmt=FILE_TIME))
    logging.getLogger().addHandler(handler)
    return path


def log_files(folder: Path | None = None) -> list[Path]:
    """The log files, oldest first."""
    where = log_folder(folder)
    old = sorted(where.glob(f"{LOG_FILE}.*"))
    now = where / LOG_FILE
    return old + ([now] if now.is_file() else [])


def entries(files: list[Path]) -> list[tuple[datetime | None, str]]:
    """Each log entry (its time, its text); a line with no time (a traceback) joins the one
    before it."""
    out: list[tuple[datetime | None, str]] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            m = STAMP.match(line)
            if m:
                out.append((datetime.strptime(m[1], FILE_TIME), line))
            elif out:
                out[-1] = (out[-1][0], f"{out[-1][1]}\n{line}")
            elif line.strip():
                out.append((None, line))
    return out


def parse_at(text: str, now: datetime | None = None) -> datetime:
    """ "18:14" (the last time it was 18:14) or "2026-11-21 18:14". ValueError if neither."""
    now = now or datetime.now()
    text = text.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            t = datetime.strptime(text, fmt).time()
        except ValueError:
            continue
        at = datetime.combine(now.date(), t)
        return at - timedelta(days=1) if at > now + timedelta(minutes=1) else at
    raise ValueError(f'"{text}" is not a time: write it as 18:14 or "2026-11-21 18:14".')


def show(at: str | None = None, folder: Path | None = None, now: datetime | None = None) -> str:
    """What `lab-os logs` prints: the last entries, or the ones around `at`."""
    files = log_files(folder)
    if not files:
        return (
            f"No log yet in {log_folder(folder)}. The brain (lab-os serve) writes it while it runs."
        )
    all_entries = entries(files)
    if at is None:
        picked = all_entries[-LAST_LINES:]
        head = f"The last {len(picked)} entries of {files[-1]}:"
    else:
        t = parse_at(at, now)
        lo, hi = t - timedelta(minutes=AROUND_MIN), t + timedelta(minutes=AROUND_MIN + 1)
        picked = [e for e in all_entries if e[0] is not None and lo <= e[0] < hi]
        span = f"{lo:%Y-%m-%d %H:%M} to {hi:%H:%M}"
        if not picked:
            return f"Nothing in the log from {span} ({log_folder(folder)})."
        head = f"The log from {span}:"
    return "\n".join([head, *(text for _, text in picked)])
