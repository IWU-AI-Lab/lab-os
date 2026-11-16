"""One click to start the SO-101 training setup (so101-green + LeLab) on the lab desktop.

The launcher never opens a green port itself (lab-os may drive the green follower since step 11,
but not here). This only *looks*: at the names in /dev/serial/by-id/ (a directory listing; no port
is opened), at which programs have them open (/proc), and at LeLab's saved settings.
It starts LeLab (`lelab`, Hugging Face's web page for LeRobot, its own uv tool) only when:
- both green ports are plugged in;
- nothing else is on a serial port, the white arm above all: LeLab saves raw ttyACM names, and those
  are handed out in plug-in order, so another arm can take a green arm's number;
- LeLab's saved leader and follower ports are exactly the two green arms, one each;
- they're the same way round as at the last good start (otherwise the leader and follower swapped);
- no other program has a green port open (lab-os driving so101-green, say), unless LeLab is
  already running: then it's LeLab's.
LeLab opens the ports when you press teleop or record in its page. `lab-os green` in a terminal,
the desktop icon (docs/guides/green-launcher.md) and the hub's Training page all run this.
"""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from lab_os import REPO_ROOT
from lab_os.devices import load_registry, users_of

BY_ID = Path("/dev/serial/by-id")
# LeLab's ports/ and robots/ (its calibration/ is never read or touched)
LELAB_HOME = Path.home() / ".cache/huggingface/lerobot"
LAST_GOOD = REPO_ROOT / "logs/green-last-start.json"  # which green serial was the follower
STARTED = REPO_ROOT / "logs/green-lelab.json"  # the LeLab the launcher started: pid + start time
LELAB_PORT = 8000
LELAB_URL = f"http://127.0.0.1:{LELAB_PORT}"
GREEN = ("so101-green", "so101-green-leader")  # the follower and the leader


@dataclass
class Check:
    lines: list[tuple[bool, str]] = field(default_factory=list)  # (fine?, what was found)
    follower: str = ""  # serial number of the arm LeLab will use as the follower
    leader: str = ""
    running: bool = False  # LeLab already answers on its port

    @property
    def ok(self) -> bool:
        return all(fine for fine, _ in self.lines)

    def add(self, fine: bool, text: str) -> bool:
        self.lines.append((fine, text))
        return fine

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "lines": [{"ok": f, "text": t} for f, t in self.lines],
            "running": self.running,
            "url": LELAB_URL,
        }


def _serial(by_id: str) -> str:
    """…_5B41531599-if00 → 5B41531599"""
    return Path(by_id).name.removesuffix("-if00").rsplit("_", 1)[-1]


def _saved_ports(home: Path) -> list[tuple[str, str, str]]:
    """LeLab's saved ports: (where, role, port) from ports/*.txt and robots/*.json."""
    out = []
    for role in ("leader", "follower"):
        f = home / "ports" / f"{role}_port.txt"
        if f.is_file():
            out.append((f"ports/{f.name}", role, f.read_text().strip()))
    for f in sorted((home / "robots").glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        for role in ("leader", "follower"):
            if d.get(f"{role}_port"):
                out.append((f"robots/{f.name}", role, d[f"{role}_port"]))
    return out


def _lelab() -> str | None:
    return shutil.which("lelab") or next(
        (str(p) for p in [Path.home() / ".local/bin/lelab"] if p.is_file()), None
    )


def _answers(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def check(
    by_id: Path = BY_ID,
    home: Path = LELAB_HOME,
    last_good: Path = LAST_GOOD,
    registry=None,
    proc: Path = Path("/proc"),
) -> Check:
    """Is it safe to start LeLab for the green arms right now? Opens nothing."""
    c = Check()
    registry = registry or load_registry()
    green = [registry.devices.get(name) for name in GREEN]
    if not all(d and len(d.ports) == 1 for d in green):
        c.add(False, f"{' and '.join(GREEN)} aren't in devices.yaml with a port each")
        return c
    # compared by name, so a test can pass another folder as /dev/serial/by-id
    names = {Path(p).name: d.name for d in registry.devices.values() for p in d.ports}
    present = sorted(p.name for p in by_id.iterdir()) if by_id.is_dir() else []
    mine = [Path(d.ports[0]).name for d in green]
    for port in mine:
        c.add(
            port in present,
            f"green arm …{_serial(port)[-4:]}: "
            + ("plugged in" if port in present else "not plugged in"),
        )
    others = [p for p in present if p not in mine]
    for p in others:
        who = names.get(p, "an unknown device")
        c.add(
            False, f"unplug {who} (…{_serial(p)[-4:]}): it could take a green arm's ttyACM number"
        )
    if not others:
        c.add(True, "nothing else on a serial port (the white arm is unplugged)")
    if not c.ok:
        return c

    number = {os.path.realpath(by_id / p): _serial(p) for p in mine}  # /dev/ttyACM1 → serial
    saved = _saved_ports(home)
    if not saved:
        c.add(False, f"LeLab has no saved ports in {home}: set them up in LeLab once by hand")
    roles: dict[str, set[str]] = {"leader": set(), "follower": set()}
    for where, role, port in saved:
        serial = number.get(os.path.realpath(port))
        if serial is None:
            c.add(False, f"LeLab's {role} in {where} is {port}: not a green arm right now")
        else:
            roles[role].add(serial)
    if c.ok:
        if (
            len(roles["leader"]) == 1
            and len(roles["follower"]) == 1
            and roles["leader"] != roles["follower"]
        ):
            c.leader, c.follower = roles["leader"].pop(), roles["follower"].pop()
            c.add(True, f"LeLab: follower …{c.follower[-4:]}, leader …{c.leader[-4:]}")
        else:
            c.add(False, "LeLab's saved ports don't name one leader and one follower")
    if c.ok and last_good.is_file():
        before = json.loads(last_good.read_text())
        same = before.get("follower") == c.follower
        c.add(
            same,
            "same way round as at the last start"
            if same
            else (
                f"leader and follower swapped since the last start (follower was …"
                f"{before.get('follower', '?')[-4:]}): unplug both and plug the follower in first, "
                "or pick the ports again in LeLab"
            ),
        )
    elif c.ok:
        c.add(True, "first start: this leader/follower pairing is remembered from now on")
    c.add(_lelab() is not None, "LeLab installed" if _lelab() else "LeLab (`lelab`) not found")
    c.running = _answers(LELAB_PORT)
    if not c.running:  # LeLab not there: nobody else may have a green port (one program per port)
        for port in mine:
            users = users_of(str(by_id / port), proc) or []
            if users:
                c.add(
                    False,
                    f"green arm …{_serial(port)[-4:]} is open in {', '.join(users)}: stop it "
                    "first (one program per port)",
                )
    return c


def remember(c: Check, last_good: Path = LAST_GOOD) -> None:
    last_good.parent.mkdir(parents=True, exist_ok=True)
    last_good.write_text(json.dumps({"follower": c.follower, "leader": c.leader}))


def open_terminal() -> None:
    """The hub's Start: `lab-os green --wait` in a terminal window of this desktop (it checks
    again there), so LeLab's log is visible and Ctrl+C stops it."""
    cmd = [sys.executable, "-m", "lab_os.cli", "green", "--wait"]
    subprocess.Popen(
        ["gnome-terminal", "--title", "SO-101 training (LeLab)", "--", *cmd],
        cwd=REPO_ROOT,
        start_new_session=True,
    )


# ---------- Stop LeLab (quick job 7): only the one the launcher started ----------


def _ps(pid: int, field_: str) -> str:
    """One `ps` field of a process ("" if it's gone). Reads only; Linux and macOS alike."""
    out = subprocess.run(["ps", "-o", f"{field_}=", "-p", str(pid)], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def _note_started(pid: int, path: Path | None = None) -> None:
    path = path or STARTED
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": pid, "started": _ps(pid, "lstart")}))


def started_lelab(path: Path | None = None) -> int | None:
    """The pid of the LeLab the launcher started, if that same process still runs (same start
    time, still lelab); else None. A pid reused by another program never matches."""
    path = path or STARTED
    try:
        d = json.loads(path.read_text())
        pid, when = int(d["pid"]), d["started"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not when or _ps(pid, "lstart") != when or "lelab" not in _ps(pid, "command"):
        return None
    if "Z" in _ps(pid, "stat"):  # exited, not yet collected by its parent (a zombie): gone
        return None
    return pid


def stop_lelab(path: Path | None = None, wait_s: float = 5.0) -> str:
    """Stop the launcher's LeLab like Ctrl+C in its terminal (SIGINT, then SIGTERM after
    `wait_s`). Nothing else: one started another way is left alone. Returns a sentence."""
    pid = started_lelab(path)
    if pid is None:
        if _answers(LELAB_PORT):
            return (
                "LeLab is running, but not one the launcher started, so it was left alone: "
                "close it where it was started (Ctrl+C in its terminal)."
            )
        return "LeLab isn't running."
    group = os.getpgid(pid) == pid  # its own group: its helpers stop too, as with Ctrl+C
    send = (lambda s: os.killpg(pid, s)) if group else (lambda s: os.kill(pid, s))
    send(signal.SIGINT)
    end = time.monotonic() + wait_s
    while time.monotonic() < end:
        if started_lelab(path) is None:
            return "LeLab stopped."
        time.sleep(0.2)
    send(signal.SIGTERM)
    time.sleep(1.0)
    return (
        "LeLab stopped."
        if started_lelab(path) is None
        else "LeLab didn't stop; close its terminal."
    )


def main(wait: bool = False) -> int:
    """`lab-os green`: check, then start LeLab in this terminal (or just say so if it runs)."""
    c = check()
    print("SO-101 training setup (so101-green + LeLab)\n")
    for fine, text in c.lines:
        print(f"  {'ok ' if fine else 'NO '} {text}")
    if not c.ok:
        print("\nNot started: fix the lines marked NO, then try again. Nothing was opened.")
        if wait:
            input("\nPress Enter to close.")
        return 1
    remember(c)
    if c.running:
        print(f"\nLeLab is already running: {LELAB_URL}")
        subprocess.run(["xdg-open", LELAB_URL], check=False)
        if wait:
            input("\nPress Enter to close.")
        return 0
    print(f"\nStarting LeLab ({LELAB_URL}; it opens in the browser). Ctrl+C here stops it.\n")
    _note_started(os.getpid())  # exec keeps the pid: this process becomes LeLab
    os.execv(_lelab(), ["lelab"])
    return 0  # not reached
