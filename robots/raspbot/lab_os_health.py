#!/usr/bin/env python3
"""lab-os's health log on the Raspbot: one line every 10 s, forced to disk at once.

raspbot1 stops at times with no warning (docs/dev/GOTCHAS.md, 2026-11-24). The system log keeps
lines in memory for up to 5 minutes, so the last minutes before a sudden stop are lost there. This
file keeps them: after a stop, `ssh raspbot1 tail -n 20 lab-os/health.log` shows the last minute.

Each line: time, uptime, the power flags (vcgencmd get_throttled), the 5 V input, the core's
current, the temperature, the Wi-Fi link (quality, level dBm), the load, free memory, free disk.
The file is kept under MAX_BYTES (the old part moves to health.log.1). Standard library only.
"""

import os
import shutil
import subprocess
import time
from pathlib import Path

LOG = Path.home() / "lab-os" / "health.log"
EVERY_S = 10.0
MAX_BYTES = 2_000_000


def _run(*cmd: str) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def throttled(out: str) -> str:
    """'throttled=0x50005' → '0x50005' ('?' when not read). Bit 0 = under-voltage now, 16 = since
    the start; 1/17 = frequency capped; 2/18 = throttled; 3/19 = the soft temperature limit."""
    return out.strip().partition("=")[2] or "?"


def pmic(out: str, name: str) -> str:
    """One value from `vcgencmd pmic_read_adc`, e.g. 'EXT5V_V' → '5.198V'."""
    for line in out.splitlines():
        if line.strip().startswith(name):
            value = line.partition("=")[2].strip()
            num = value.rstrip("AV")
            try:
                return f"{float(num):.3f}{value[-1:]}"
            except ValueError:
                return value
    return "?"


def temperature(out: str) -> str:
    """ "temp=48.3'C" → '48.3C'."""
    return out.strip().partition("=")[2].replace("'", "") or "?"


def wifi(text: str) -> str:
    """/proc/net/wireless → 'q70 -23dBm' for wlan0, or 'none' (no Wi-Fi link)."""
    for line in text.splitlines():
        if line.strip().startswith("wlan0:"):
            parts = line.split()
            return f"q{parts[2].rstrip('.')} {parts[3].rstrip('.')}dBm"
    return "none"


def sample() -> str:
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    up = Path("/proc/uptime").read_text().split()[0]
    adc = _run("vcgencmd", "pmic_read_adc")
    load = Path("/proc/loadavg").read_text().split()[0]
    mem = next(
        (int(line.split()[1]) // 1024 for line in Path("/proc/meminfo").read_text().splitlines()
         if line.startswith("MemAvailable")),
        -1,
    )  # fmt: skip
    disk = shutil.disk_usage("/").free // 2**30
    try:
        link = wifi(Path("/proc/net/wireless").read_text())
    except OSError:
        link = "?"
    return (
        f"{now} up={float(up):.0f}s throttled={throttled(_run('vcgencmd', 'get_throttled'))} "
        f"5V={pmic(adc, 'EXT5V_V')} core={pmic(adc, 'VDD_CORE_A')} "
        f"temp={temperature(_run('vcgencmd', 'measure_temp'))} wifi={link} load={load} "
        f"mem={mem}MB disk={disk}GB"
    )


def write(line: str, log: Path = LOG, max_bytes: int = MAX_BYTES) -> None:
    """Append one line and force it to disk; move the file to .1 when it is full."""
    log.parent.mkdir(parents=True, exist_ok=True)
    if log.exists() and log.stat().st_size > max_bytes:
        log.replace(log.with_name(log.name + ".1"))
    with open(log, "a") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


def main() -> None:
    write(f"--- start (boot at {_run('uptime', '-s').strip()})")
    while True:
        write(sample())
        time.sleep(EVERY_S)


if __name__ == "__main__":
    main()
