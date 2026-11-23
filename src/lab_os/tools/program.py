"""One short program instead of many moves (quick job 81, "Code as Policies"): the AI writes a
little Python that calls the brain's robot tools, and the brain runs it here, with no model call
between the steps. `calculate` (quick job 86) runs plain math the same way, with no robot.

The program is compiled by RestrictedPython (Zope's maintained restricted compiler: no imports,
no names or attributes that start with "_", no files; https://github.com/zopefoundation/
RestrictedPython) and runs in a worker thread with only the functions below and a few plain
builtins. Each robot call goes to the brain's event loop as `RobotTools.call`, so it has every
check an AI tool's call has (STOP, the soft limits, the floor, the venue, one controller at a
time) and shows on the AI Control page. The program ends:
- at the time limit, or when STOP is pressed (a line tracer checks both, also in a loop that
  calls nothing), or when a move says it was stopped;
- at a refusal, or at any error (the line is reported).
"""

import asyncio
import logging
import math
import statistics
import sys
import threading
import time
import warnings
from collections.abc import Callable
from types import BuiltinFunctionType, FunctionType, SimpleNamespace
from typing import Any

from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
from RestrictedPython.Guards import (
    full_write_guard,
    guarded_iter_unpack_sequence,
    guarded_unpack_sequence,
    safer_getattr,
)

log = logging.getLogger(__name__)

DEFAULT_LIMIT_S = 120.0
MAX_LIMIT_S = 300.0
CALL_TIMEOUT_S = 90.0  # one robot call (a pick takes ~20 s on the real arm)
MAX_CODE_CHARS = 8000
MAX_PRINTED = 60  # lines kept from print()
MAX_CALLS_KEPT = 80  # calls listed in the result (all are on AI Control)
WAIT_MAX_S = 30.0
# what a result keeps of a robot call's answer (the rest is long: joints, limits)
KEEP = (
    "result",
    "message",
    "gripper_point_cm",
    "gripper_open_pct",
    "tool_angle_deg",
    "clipped",
    "off_by_cm",
    "steps",
    "table_cm",
)

EXTRA_BUILTINS = {
    f.__name__: f
    for f in (
        abs,
        all,
        any,
        enumerate,
        len,
        max,
        min,
        range,
        reversed,
        round,
        sorted,
        sum,
        zip,
        dict,
        list,
        tuple,
        set,
        float,
        int,
        str,
        bool,
        isinstance,
    )
}
INPLACE = {
    "+=": lambda a, b: a + b,
    "-=": lambda a, b: a - b,
    "*=": lambda a, b: a * b,
    "/=": lambda a, b: a / b,
    "//=": lambda a, b: a // b,
    "%=": lambda a, b: a % b,
    "**=": lambda a, b: a**b,
}


def _only_functions(module) -> SimpleNamespace:
    """A module's own public functions and numbers only: never a module object (statistics.sys
    would reach sys.modules, and every other module from there), nor what it imported."""
    keep = {}
    for k, v in vars(module).items():
        if k.startswith("_") or isinstance(v, bool):
            continue
        own = getattr(v, "__module__", None) == module.__name__
        if (isinstance(v, (FunctionType, BuiltinFunctionType)) and own) or isinstance(
            v, (float, int)
        ):
            keep[k] = v
    return SimpleNamespace(**keep)


MATH = _only_functions(math)
STATISTICS = _only_functions(statistics)


class Stopped(Exception):
    """STOP was pressed, or a move said it was stopped."""


class TimeUp(Exception):
    """The program ran past its time limit."""


class ProgramError(Exception):
    """A robot call was refused or failed: the message says why."""


class _Printed:
    """RestrictedPython's print hook: lines go to a list (at most MAX_PRINTED)."""

    def __init__(self, lines: list[str]):
        self.lines = lines

    def __call__(self, _getattr=None):
        return self

    def _call_print(self, *args, **kwargs):
        if len(self.lines) < MAX_PRINTED:
            self.lines.append(" ".join(str(a) for a in args))


def _compile(code: str):
    if len(code) > MAX_CODE_CHARS:
        raise SyntaxError(f"the program is longer than {MAX_CODE_CHARS} characters")
    with warnings.catch_warnings():  # "prints, but never reads 'printed'": print is ours
        warnings.simplefilter("ignore", SyntaxWarning)
        return compile_restricted(code, "<program>", "exec")


def _globals(functions: dict[str, Callable], printed: list[str]) -> dict:
    return {
        "__builtins__": {**safe_builtins, **EXTRA_BUILTINS},
        "_getattr_": safer_getattr,
        "_getitem_": default_guarded_getitem,
        "_getiter_": default_guarded_getiter,
        "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
        "_unpack_sequence_": guarded_unpack_sequence,
        "_write_": full_write_guard,
        "_inplacevar_": lambda op, a, b: INPLACE[op](a, b),
        "_print_": _Printed(printed),
        "math": MATH,
        "statistics": STATISTICS,
        **functions,
    }


def _line(tb) -> int | None:
    """The program's line where an error happened (its own frames are named <program>)."""
    line = None
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == "<program>":
            line = tb.tb_lineno
        tb = tb.tb_next
    return line


def run_restricted(
    code: str,
    functions: dict[str, Callable],
    time_limit_s: float,
    should_stop: Callable[[], bool] = lambda: False,
) -> dict:
    """Run `code` in this thread with `functions`; returns {"result": "done" | "stopped" |
    "time limit" | "error", "printed", "value" (the program's `result` variable, if set),
    "error", "line", "seconds"}. Call it from a worker thread: it sets that thread's tracer."""
    printed: list[str] = []
    t0 = time.monotonic()
    out: dict[str, Any] = {"printed": printed}
    try:
        byte = _compile(code)
    except SyntaxError as e:
        return out | {"result": "error", "error": f"not a program it can run: {e}", "seconds": 0}
    deadline = t0 + time_limit_s
    glb = _globals(functions, printed)

    def tracer(frame, event, arg):
        if time.monotonic() > deadline:
            raise TimeUp(f"the time limit ({time_limit_s:g} s) was reached")
        if should_stop():
            raise Stopped("STOP was pressed")
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        exec(byte, glb)
        out["result"] = "done"
    except Stopped as e:
        out |= {"result": "stopped", "error": str(e), "line": _line(e.__traceback__)}
    except TimeUp as e:
        out |= {"result": "time limit", "error": str(e), "line": _line(e.__traceback__)}
    except Exception as e:  # the program's own mistake, or a refusal: say which line
        out |= {
            "result": "error",
            "error": f"{type(e).__name__}: {e}",
            "line": _line(e.__traceback__),
        }
    finally:
        sys.settrace(old)
    if "result" in glb and not callable(glb["result"]):
        out["value"] = _plain(glb["result"])
    out["seconds"] = round(time.monotonic() - t0, 2)
    return out


def _plain(v: Any, depth: int = 0) -> Any:
    """A value as JSON can carry it (a program may return anything)."""
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if depth > 4:
        return str(v)
    if isinstance(v, dict):
        return {str(k): _plain(x, depth + 1) for k, x in list(v.items())[:50]}
    if isinstance(v, (list, tuple, set)):
        return [_plain(x, depth + 1) for x in list(v)[:100]]
    return str(v)


class ProgramRunner:
    """Runs a robot program for the MCP tool `run_program`. `call(tool, **args)`: the robot
    tools' call (a coroutine, on `loop`); `find_cube()`: the cube finder (a coroutine returning
    (x, y)); `stops()`: how many times STOP was pressed so far."""

    def __init__(
        self,
        call: Callable[..., Any],
        loop: asyncio.AbstractEventLoop,
        stops: Callable[[], int],
        find_cube: Callable[[], Any] | None = None,
    ):
        self.call, self.loop, self.stops, self.find_cube = call, loop, stops, find_cube

    def run(self, code: str, time_limit_s: float = DEFAULT_LIMIT_S) -> dict:
        """Blocking: run it from a worker thread (asyncio.to_thread)."""
        limit = max(1.0, min(float(time_limit_s), MAX_LIMIT_S))
        start_stops = self.stops()
        calls: list[dict] = []
        stopped = threading.Event()

        def should_stop() -> bool:
            return stopped.is_set() or self.stops() != start_stops

        def robot(tool: str, **args) -> dict:
            if should_stop():
                raise Stopped("STOP was pressed")
            args = {k: v for k, v in args.items() if v is not None}
            fut = asyncio.run_coroutine_threadsafe(self.call(tool, **args), self.loop)
            try:
                r = fut.result(CALL_TIMEOUT_S)
            except Exception as e:
                calls.append({"call": tool, "args": args, "error": str(e)})
                raise ProgramError(f"{tool} {e}") from None
            brief = {k: r[k] for k in KEEP if k in r}
            if len(calls) < MAX_CALLS_KEPT:
                calls.append({"call": tool, "args": args, "result": brief})
            if r.get("result") == "stopped" and tool != "stop":
                stopped.set()
                raise Stopped(f"{tool} was stopped: {r.get('message', 'STOP')}")
            return r

        def wait(seconds: float) -> None:
            end = time.monotonic() + max(0.0, min(float(seconds), WAIT_MAX_S))
            while time.monotonic() < end:
                if should_stop():
                    raise Stopped("STOP was pressed")
                time.sleep(0.05)

        def find_cube() -> dict | None:
            if self.find_cube is None:
                return None
            fut = asyncio.run_coroutine_threadsafe(self.find_cube(), self.loop)
            try:
                x, y = fut.result(CALL_TIMEOUT_S)
            except Exception as e:
                calls.append({"call": "find_cube", "error": str(e)})
                return None
            calls.append({"call": "find_cube", "result": {"x_cm": x, "y_cm": y}})
            return {"x_cm": x, "y_cm": y}

        functions = {
            "arm_status": lambda arm=None: robot("arm_status", arm=arm),
            "list_poses": lambda arm=None: robot("list_poses", arm=arm),
            "table_point": lambda camera, x_px, y_px, width_px=640: robot(
                "table_point", camera=camera, x_px=x_px, y_px=y_px, width_px=width_px
            ),
            "move_to": lambda x_cm, y_cm, z_cm, tool_angle_deg=None, arm=None: robot(
                "move_to", x_cm=x_cm, y_cm=y_cm, z_cm=z_cm, tool_angle_deg=tool_angle_deg, arm=arm
            ),
            "pick_at": lambda x_cm, y_cm, height_cm=2.5, open_pct=100.0, arm=None: robot(
                "pick_at", x_cm=x_cm, y_cm=y_cm, height_cm=height_cm, open_pct=open_pct, arm=arm
            ),
            "gripper": lambda open_pct, arm=None: robot("gripper", open_pct=open_pct, arm=arm),
            "go_to_pose": lambda name, arm=None: robot("go_to_pose", name=name, arm=arm),
            "move_joints": lambda joints, relative=False, arm=None: robot(
                "move_joints", joints=joints, relative=relative, arm=arm
            ),
            "find_cube": find_cube,
            "wait": wait,
        }
        out = run_restricted(code, functions, limit, should_stop)
        if out["result"] != "done":
            log.info("program: %s (%s)", out["result"], out.get("error"))
        return out | {"calls": calls}


CALC_LIMIT_S = 5.0


def calculate(code: str, time_limit_s: float = CALC_LIMIT_S) -> dict:
    """Plain math for the hub's assistant (quick job 86): `math`, `statistics` and the plain
    builtins in the same restricted compiler, with no robot functions; the answer is the
    program's `result` variable (and what it prints). Runs in a thread of its own, so its line
    tracer touches nothing else."""
    box: dict = {}

    def go():
        box["out"] = run_restricted(code, {}, time_limit_s)

    t = threading.Thread(target=go, name="lab-os-calculate", daemon=True)
    t.start()
    t.join(time_limit_s + 2)
    if "out" not in box:  # stuck inside one C call (a huge power): left behind, a daemon thread
        return {"result": "time limit", "error": "the calculation took too long", "printed": []}
    return box["out"]
