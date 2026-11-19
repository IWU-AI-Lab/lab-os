"""Colours in the terminal (quick job 40): only on a terminal, never with NO_COLOR, never in a
pipe or a file; the words of each line stay the same."""

import io
import logging
import re

import pytest

from lab_os import term

TIME = r"\d\d:\d\d:\d\d"
ESC = "\x1b["


class Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.fixture(autouse=True)
def plain_env(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)


def log_to(stream) -> logging.Logger:
    logger = logging.getLogger(f"test-term-{id(stream)}")
    logger.handlers = [term.log_handler(stream)]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    return logger


def test_a_pipe_or_file_gets_no_colour_and_the_same_words():
    out = io.StringIO()
    log = log_to(out)
    log.info("so101-white reconnected")
    log.warning("voice timing: 1.2 s")
    text = out.getvalue()
    assert ESC not in text
    assert re.search(rf"^{TIME} INFO so101-white reconnected$", text, re.M)
    assert re.search(rf"^{TIME} WARNING voice timing: 1.2 s$", text, re.M)


def test_a_terminal_gets_amber_warnings_red_errors_and_plain_info():
    out = Tty()
    log = log_to(out)
    log.info("so101-white reconnected")
    log.warning("careful")
    log.error("broken")
    lines = [line for line in out.getvalue().splitlines() if line]
    assert re.match(rf"^{TIME} INFO so101-white reconnected", lines[0])  # no colour before INFO
    assert "\x1b[33mWARNING careful" in lines[1]  # amber (the terminal's yellow)
    assert "\x1b[31mERROR broken" in lines[2]


def test_no_color_wins_on_a_terminal(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    out = Tty()
    log_to(out).warning("careful")
    assert ESC not in out.getvalue()
    assert term.warning("careful", Tty()) == "careful"
    assert term.error("broken", Tty()) == "broken"


def test_an_empty_no_color_is_not_set(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "")  # no-color.org: only when not empty
    assert term.use_colour(Tty())


def test_force_color_colours_a_pipe(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert term.use_colour(io.StringIO())


def test_printed_warnings_and_errors():
    assert term.warning("LIMITS OFF", io.StringIO()) == "LIMITS OFF"
    assert term.warning("LIMITS OFF", Tty()) == "\x1b[33mLIMITS OFF\x1b[0m"
    assert term.error("NO  port", Tty()) == "\x1b[31mNO  port\x1b[0m"


def test_a_command_s_exit_message_is_the_same_words_and_exit_code(capsys):
    def main():
        raise SystemExit("--arm so101-green: not opened.")

    with pytest.raises(SystemExit) as e:
        term.exit_in_red(main)()
    assert e.value.code == 1
    assert capsys.readouterr().err == "--arm so101-green: not opened.\n"  # captured: not a terminal

    def ends_well():
        raise SystemExit(0)

    with pytest.raises(SystemExit) as e:
        term.exit_in_red(ends_well)()
    assert e.value.code == 0
