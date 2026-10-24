"""Record XR input to a JSONL file and replay it later (no headset needed).

File format: one JSON object per line: `{"dt": seconds since start, "msg": <raw message>}`.
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from pathlib import Path


class Recorder:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path.open("w")
        self._start = time.monotonic()

    def write(self, msg: dict) -> None:
        line = {"dt": round(time.monotonic() - self._start, 4), "msg": msg}
        self._file.write(json.dumps(line) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()


def read_recording(path: Path) -> list[tuple[float, dict]]:
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            entry = json.loads(line)
            out.append((float(entry["dt"]), entry["msg"]))
    return out


async def replay(path: Path, speed: float = 1.0, loop: bool = False) -> AsyncIterator[dict]:
    """Yield recorded messages with their original timing (`speed` > 1 = faster)."""
    entries = read_recording(path)
    while True:
        start = time.monotonic()
        for dt, msg in entries:
            delay = dt / speed - (time.monotonic() - start)
            if delay > 0:
                await asyncio.sleep(delay)
            yield msg
        if not loop:
            return
