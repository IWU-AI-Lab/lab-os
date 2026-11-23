"""Quick job 85: the brain's log in a file, and `lab-os logs` to read it."""

import logging
from datetime import datetime

import pytest

from lab_os import brainlog


def write(folder, name, lines):
    where = brainlog.log_folder(folder)
    where.mkdir(parents=True, exist_ok=True)
    (where / name).write_text("\n".join(lines) + "\n")


def test_the_log_goes_to_a_file_too(tmp_path):
    root = logging.getLogger()
    path = brainlog.log_to_file(tmp_path)
    try:
        assert path == tmp_path / "local" / "logs" / "brain.log"
        logging.getLogger("lab_os.test").warning("voice: desk heard the wake word")
    finally:
        handler = root.handlers[-1]
        root.removeHandler(handler)
        handler.close()
    text = path.read_text()
    assert "WARNING voice: desk heard the wake word" in text
    assert brainlog.STAMP.match(text)  # the date and time first
    assert "\x1b[" not in text  # no colours


def test_logs_prints_the_end_or_the_minutes_around_a_time(tmp_path):
    write(
        tmp_path,
        "brain.log.2026-11-21",
        [
            "2026-11-21 18:05:00 INFO too early",
            "2026-11-21 18:12:30 INFO voice: question on desk",
            "2026-11-21 18:14:10 ERROR it broke",
            "Traceback (most recent call last):",
            '  File "x.py", line 1',
            "2026-11-21 18:20:00 INFO too late",
        ],
    )
    write(tmp_path, "brain.log", ["2026-11-22 09:00:00 INFO started"])
    now = datetime(2026, 11, 22, 10, 0)
    out = brainlog.show("18:14", tmp_path, now)  # yesterday's 18:14: today's is still to come
    assert "voice: question on desk" in out and "it broke" in out and "Traceback" in out
    assert "too early" not in out and "too late" not in out
    assert "2026-11-21 18:11 to 18:18" in out
    last = brainlog.show(None, tmp_path, now)
    assert last.endswith("2026-11-22 09:00:00 INFO started") and "too early" in last
    assert "Nothing in the log" in brainlog.show("2026-11-20 12:00", tmp_path, now)


def test_logs_says_when_there_is_no_log_or_the_time_is_wrong(tmp_path):
    assert "No log yet" in brainlog.show(None, tmp_path)
    write(tmp_path, "brain.log", ["2026-11-22 09:00:00 INFO started"])
    with pytest.raises(ValueError, match="18:14"):
        brainlog.show("teatime", tmp_path)


def test_parse_at():
    now = datetime(2026, 11, 22, 18, 30)
    assert brainlog.parse_at("18:14", now) == datetime(2026, 11, 22, 18, 14)
    assert brainlog.parse_at("19:00", now) == datetime(2026, 11, 21, 19, 0)
    assert brainlog.parse_at("2026-11-20 08:05", now) == datetime(2026, 11, 20, 8, 5)


def test_old_files_are_kept_a_few_days():
    assert 2 <= brainlog.KEEP_DAYS <= 7
