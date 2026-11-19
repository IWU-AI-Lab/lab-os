"""Colours in the terminal (quick job 40), after clig.dev and no-color.org: colour only when the
output is a terminal, never in a log file or a pipe; `NO_COLOR` set (not empty) = no colour;
`FORCE_COLOR` set = colour anyway. Warnings amber, errors red, the rest plain; each log line
starts with a short time. The words of each line stay the same: lab checks copy them.

The log's colours come from `colorlog` (small, maintained; it also makes them work in Windows'
old console through colorama)."""

import logging
import os
import sys
from typing import TextIO

import colorlog
from colorlog.escape_codes import escape_codes

LOG_FORMAT = "\n%(asctime)s %(log_color)s%(levelname)s %(message)s%(reset)s"
TIME_FORMAT = "%H:%M:%S"
LOG_COLOURS = {"WARNING": "yellow", "ERROR": "red", "CRITICAL": "bold_red"}


def use_colour(stream: TextIO) -> bool:
    """True when `stream` may get colour codes."""
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("NO_COLOR"):
        return False
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def log_handler(stream: TextIO) -> logging.Handler:
    """Log lines on `stream`: "12:04:31 WARNING …", coloured when `stream` may get colour."""
    colour = use_colour(stream)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        colorlog.ColoredFormatter(
            LOG_FORMAT,
            datefmt=TIME_FORMAT,
            log_colors=LOG_COLOURS,
            no_color=not colour,
            force_color=colour,
        )
    )
    return handler


def setup_logging(level: int = logging.INFO) -> None:
    """The commands' log: on stderr, as `log_handler` writes it."""
    logging.basicConfig(level=level, handlers=[log_handler(sys.stderr)])


def _paint(text: str, colour: str, stream: TextIO | None) -> str:
    if not use_colour(stream or sys.stdout):
        return text
    return f"{escape_codes[colour]}{text}{escape_codes['reset']}"


def warning(text: str, stream: TextIO | None = None) -> str:
    """`text` in amber when it goes to a terminal (`stream`, default stdout), else unchanged."""
    return _paint(text, LOG_COLOURS["WARNING"], stream)


def error(text: str, stream: TextIO | None = None) -> str:
    """`text` in red when it goes to a terminal (`stream`, default stdout), else unchanged."""
    return _paint(text, LOG_COLOURS["ERROR"], stream)


def exit_in_red(main):
    """Wrap a command's `main`: a `SystemExit("message")` prints the same message, red on a
    terminal, and exits with 1 (as Python does)."""

    def run(*args, **kwargs):
        try:
            return main(*args, **kwargs)
        except SystemExit as e:
            if isinstance(e.code, str):
                print(error(e.code, sys.stderr), file=sys.stderr)
                raise SystemExit(1) from None
            raise

    run.__doc__ = main.__doc__
    return run
