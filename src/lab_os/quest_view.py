"""What the Quest sees, on the brain's computer (quick job 36): scrcpy mirrors the headset over the
same USB adb link teleop uses (docs/guides/quest-view.md). Without the cable (quick job 103), over
the router's Wi-Fi: adb in TCP mode at the headset's `host` (devices.yaml), port 5555. The headset
leaves TCP mode at each restart, so `lab-os quest-view --wifi` switches it on again over USB once.
USB stays the first choice when it is plugged in.

scrcpy (github.com/Genymobile/scrcpy, Apache 2.0) isn't installed system-wide: `lab-os quest-view
--install` downloads one pinned release into the repo's `downloads/scrcpy/` (no sudo, checked
against its SHA-256), and `--remove` deletes that folder again. A scrcpy on the PATH works too.

The release brings its own adb. Two different adb versions stop each other's server, which would
drop teleop's `adb reverse`, so scrcpy is told to use the system's adb when there is one (`ADB`).
"""

import hashlib
import logging
import os
import platform
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from lab_os import REPO_ROOT
from lab_os.devices import Registry, load_registry

log = logging.getLogger(__name__)

VERSION = "v5.0.1"  # 2026-10-08; v4.0 fixed mirroring a Meta Quest (scrcpy issue #5913)
URL = "https://github.com/Genymobile/scrcpy/releases/download/{v}/{name}"
# the release's SHA256SUMS.txt
ASSETS = {
    ("Linux", "x86_64"): (
        "scrcpy-linux-x86_64-v5.0.1.tar.gz",
        "9f969d30cc574816077edecda65719c1c70b0aee1df1ba5fa00779ac07b8fd6e",
    ),
    ("Darwin", "arm64"): (
        "scrcpy-macos-aarch64-v5.0.1.tar.gz",
        "33611e51977a8289e2e124b220f727895181ef2eb9060e0987a4dc2db9cf0d6b",
    ),
    ("Darwin", "x86_64"): (
        "scrcpy-macos-x86_64-v5.0.1.tar.gz",
        "31a5467a9e907f162b093267cbbab1276b15c6e709c2ea8159566a8d165beb50",
    ),
    ("Windows", "AMD64"): (
        "scrcpy-win64-v5.0.1.zip",
        "b12a2c4ee8be317422451fc7dcf8ee20a71b5ea7ef9ad73ddd825a25316227a5",
    ),
}
FOLDER = REPO_ROOT / "downloads" / "scrcpy"  # gitignored
# watch only (a click in the window never reaches the headset), no sound taken off the headset,
# 30 frames/s to leave the Quest's GPU for VR
BASE_ARGS = ["--no-control", "--no-audio", "--max-fps=30"]
BIT_RATE = {"usb": "--video-bit-rate=8M", "wifi": "--video-bit-rate=4M"}  # scrcpy: lower on Wi-Fi
ADB_PORT = 5555  # adb's TCP port on the headset (adb tcpip 5555)


class QuestViewError(Exception):
    """Why the view can't start (a full sentence for the page)."""


def asset() -> tuple[str, str]:
    key = (platform.system(), platform.machine())
    if key not in ASSETS:
        raise QuestViewError(
            f"There's no scrcpy download for {key[0]} {key[1]} here: install scrcpy yourself "
            "(github.com/Genymobile/scrcpy) so it's on the PATH."
        )
    return ASSETS[key]


def install(folder: Path = FOLDER) -> Path:
    """Download the pinned scrcpy into `folder`, check it, unpack it. Returns the scrcpy program."""
    name, sha = asset()
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / name
    with urllib.request.urlopen(URL.format(v=VERSION, name=name), timeout=60) as r:
        data = r.read()
    if hashlib.sha256(data).hexdigest() != sha:
        raise QuestViewError(f"The download of {name} doesn't match its checksum: not unpacked.")
    archive.write_bytes(data)
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            z.extractall(folder)
    else:
        with tarfile.open(archive) as t:
            t.extractall(folder, filter="data")
    archive.unlink()
    program = downloaded(folder)
    if program is None:
        raise QuestViewError(f"Unpacked {name}, but there's no scrcpy program in it.")
    return program


def remove(folder: Path = FOLDER) -> bool:
    """Delete the downloaded copy (the whole `downloads/scrcpy/` folder)."""
    if not folder.exists():
        return False
    shutil.rmtree(folder)
    return True


def downloaded(folder: Path = FOLDER) -> Path | None:
    """The downloaded scrcpy program, if there is one."""
    exe = "scrcpy.exe" if platform.system() == "Windows" else "scrcpy"
    found = sorted(folder.glob(f"scrcpy-*{VERSION}/{exe}")) if folder.exists() else []
    return found[-1] if found else None


def find_scrcpy(folder: Path = FOLDER) -> Path | None:
    """The downloaded copy first, else a scrcpy on the PATH."""
    own = downloaded(folder)
    if own:
        return own
    on_path = shutil.which("scrcpy")
    return Path(on_path) if on_path else None


def find_adb(scrcpy: Path | None) -> str | None:
    """The system's adb (the one teleop's `adb reverse` uses), else the one beside scrcpy."""
    system = shutil.which("adb")
    if system:
        return system
    beside = (
        scrcpy.parent / ("adb.exe" if platform.system() == "Windows" else "adb") if scrcpy else None
    )
    return str(beside) if beside and beside.exists() else None


def adb_devices(adb: str) -> list[str]:
    """Serial numbers of the devices adb sees ready ("device", not "unauthorized")."""
    try:
        out = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    lines = [line.split() for line in out.splitlines()[1:]]
    return [p[0] for p in lines if len(p) >= 2 and p[1] == "device"]


def adb_connect(adb: str, address: str) -> bool:
    """`adb connect <address>`: does adb reach the headset over the network now?"""
    try:
        r = subprocess.run([adb, "connect", address], capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return False
    out = (r.stdout + r.stderr).lower()
    return "connected to" in out and "cannot" not in out and "failed" not in out


def wifi_address(host: str) -> str:
    """adb's name for a headset on the network: "192.168.8.180:5555"."""
    return f"{host}:{ADB_PORT}"


@dataclass
class AdbReverse:
    """`adb reverse` by itself (quick job 73): the Quest's browser opens `http://localhost:<port>`
    through its USB cable, and a new connection of the cable forgets the reverse (GOTCHAS
    2026-10-24). The brain calls `check()` every few seconds: each device that adb sees ready and
    that wasn't there at the last look gets `adb reverse tcp:<port> tcp:<port>`. The system's adb
    (`find_adb`), so a second adb version can't stop the server."""

    port: int
    find: Callable[[], str | None] = lambda: find_adb(find_scrcpy())
    devices: Callable[[str], list[str]] = adb_devices
    run: Callable = subprocess.run
    done: set[str] = field(default_factory=set)  # reversed, and still connected
    failed: dict[str, str] = field(default_factory=dict)  # serial → why (said once, tried again)

    def check(self) -> list[str]:
        """Reverse the port for each newly connected device; returns their serials."""
        adb = self.find()
        if adb is None:
            return []
        here = set(self.devices(adb))
        self.done &= here  # gone: reversed again when it's back
        new = []
        for serial in sorted(here - self.done):
            port = f"tcp:{self.port}"
            cmd = [adb, "-s", serial, "reverse", port, port]
            try:
                r = self.run(cmd, capture_output=True, text=True, timeout=10)
                why = None if r.returncode == 0 else (r.stderr or r.stdout).strip()
            except (OSError, subprocess.TimeoutExpired) as e:
                why = str(e)
            if why:
                if self.failed.get(serial) != why:
                    log.warning("adb reverse for %s failed: %s", serial, why)
                self.failed[serial] = why
                continue
            self.failed.pop(serial, None)
            self.done.add(serial)
            new.append(serial)
            log.info(
                "%s connected: adb reverse %s %s (its browser reaches this brain)",
                serial,
                port,
                port,
            )
        return new


@dataclass
class QuestView:
    """One scrcpy window at a time, started and stopped from the hub."""

    folder: Path = FOLDER
    registry: Callable[[], Registry] = load_registry
    proc: subprocess.Popen | None = None
    headset: str = ""
    devices: Callable[[str], list[str]] = adb_devices  # (adb) → serials (tests replace it)
    popen: Callable = subprocess.Popen
    connect: Callable[[str, str], bool] = adb_connect  # (adb, "ip:5555") → reached (Wi-Fi)
    via: str = ""  # "usb" or "wifi": how the open window gets its picture

    def running(self) -> bool:
        if self.proc is not None and self.proc.poll() is not None:
            log.info("quest view: scrcpy ended (exit %s)", self.proc.returncode)
            self.proc, self.headset = None, ""
        return self.proc is not None

    def _headsets(self, reg: Registry, adb: str | None) -> list[dict]:
        """The place's headsets with a serial, and how adb sees each one now: by USB (its serial),
        on Wi-Fi (its `host`:5555), or not ("via": None). USB first when it is both."""
        seen = set(self.devices(adb)) if adb else set()
        out = []
        for d in reg.devices.values():
            if d.kind != "quest" or not d.serial:
                continue
            via = "usb" if d.serial in seen else None
            if via is None and d.host and wifi_address(d.host) in seen:
                via = "wifi"
            out.append({"name": d.name, "connected": via is not None, "via": via, "host": d.host})
        return out

    def status(self) -> dict:
        scrcpy = find_scrcpy(self.folder)
        adb = find_adb(scrcpy)
        headsets = self._headsets(self.registry(), adb)
        why = None
        if scrcpy is None:
            why = "scrcpy isn't installed: run `uv run lab-os quest-view --install` once."
        elif adb is None:
            why = "There's no adb on this computer (docs/guides/quest-setup.md)."
        elif not any(h["connected"] or h["host"] for h in headsets):
            why = "No headset is connected by USB with USB debugging allowed (adb devices)."
        # a headset with an address: the press tries Wi-Fi (adb connect), so the button stays usable
        return {
            "installed": scrcpy is not None,
            "running": self.running(),
            "headset": self.headset,
            "via": self.via if self.proc is not None else "",
            "headsets": headsets,
            "why_not": why,
        }

    def start(self, name: str | None = None) -> str:
        """Open the window for headset `name` (default: the first one connected). Returns which."""
        if self.running():
            return self.headset
        scrcpy = find_scrcpy(self.folder)
        if scrcpy is None:
            raise QuestViewError(
                "scrcpy isn't installed: run `uv run lab-os quest-view --install` once."
            )
        adb = find_adb(scrcpy)
        reg = self.registry()
        heads = self._headsets(reg, adb)
        if name:
            heads = [h for h in heads if h["name"] == name]
        # USB first, then a headset adb already reaches on Wi-Fi, then one to reach (adb connect)
        heads.sort(key=lambda h: {"usb": 0, "wifi": 1}.get(h["via"], 2))
        pick = next((h for h in heads if h["connected"]), None)
        if pick is None and adb:
            for h in heads:
                if h["host"] and self.connect(adb, wifi_address(h["host"])):
                    pick = h | {"connected": True, "via": "wifi"}
                    break
        if pick is None:
            raise QuestViewError(self._why_not_reached(heads, name))
        name = pick["name"]
        d = reg.devices[name]
        serial = d.serial if pick["via"] == "usb" else wifi_address(d.host)
        cmd = [
            str(scrcpy),
            f"--serial={serial}",
            *BASE_ARGS,
            BIT_RATE[pick["via"]],
            f"--window-title=Quest view ({name})",
        ]
        cmd += list(d.mirror)
        env = dict(os.environ, ADB=adb) if adb else None
        log.info("quest view (%s): %s", pick["via"], " ".join(cmd))
        self.proc = self.popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.headset, self.via = name, pick["via"]
        return name

    @staticmethod
    def _why_not_reached(heads: list[dict], name: str | None) -> str:
        on_wifi = [h for h in heads if h["host"]]
        if not on_wifi:
            if name:
                return f"{name} isn't connected by USB with USB debugging allowed."
            return "No headset is connected by USB with USB debugging allowed (adb devices)."
        where = ", ".join(f"{h['name']} at {wifi_address(h['host'])}" for h in on_wifi)
        return (
            f"No headset is connected by USB, and adb can't reach {where} on Wi-Fi. "
            "Is the headset on and on the router's Wi-Fi? After each restart of the headset, "
            "connect it by USB once and run `uv run lab-os quest-view --wifi`."
        )

    def stop(self) -> bool:
        if not self.running():
            return False
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc, self.headset, self.via = None, "", ""
        return True


def wifi(
    registry: Callable[[], Registry] = load_registry,
    devices: Callable[[str], list[str]] = adb_devices,
    run: Callable = subprocess.run,
    connect: Callable[[str, str], bool] = adb_connect,
) -> list[str]:
    """`lab-os quest-view --wifi`: each headset on USB that has a `host` gets adb's TCP mode
    (`adb tcpip 5555`), then `adb connect`. Then Quest view also works without the cable, until
    the headset restarts. Returns one sentence for each headset."""
    adb = find_adb(find_scrcpy())
    if adb is None:
        raise QuestViewError("There's no adb on this computer (docs/guides/quest-setup.md).")
    reg = registry()
    seen = set(devices(adb))
    quests = [d for d in reg.devices.values() if d.kind == "quest" and d.serial]
    said = []
    for d in quests:
        if d.serial not in seen:
            continue
        if not d.host:
            said.append(f"{d.name}: no address in devices.yaml (host), so no Wi-Fi.")
            continue
        try:
            r = run([adb, "-s", d.serial, "tcpip", str(ADB_PORT)], capture_output=True, text=True,
                    timeout=15)  # fmt: skip
            why = None if r.returncode == 0 else (r.stderr or r.stdout).strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            why = str(e)
        if why:
            said.append(f"{d.name}: adb tcpip failed: {why}")
            continue
        address = wifi_address(d.host)
        ok = any(connect(adb, address) for _ in range(3))  # adbd restarts on the headset first
        said.append(
            f"{d.name}: ready on Wi-Fi at {address}. You can unplug the USB cable."
            if ok
            else f"{d.name}: TCP mode is on, but adb can't reach {address}. Is it on the "
            "router's Wi-Fi, at that address?"
        )
    if not said:
        raise QuestViewError(
            "No headset is connected by USB with USB debugging allowed (adb devices). Connect it "
            "by USB first."
        )
    return said


def main(install_it: bool, remove_it: bool, wifi_it: bool = False) -> str:
    """`lab-os quest-view --install / --remove / --wifi`, or where things stand."""
    if wifi_it:
        return "\n".join(wifi())
    if install_it:
        program = install()
        remove_cmd = "uv run lab-os quest-view --remove"
        return f"Installed scrcpy {VERSION}: {program}\nRemove it with: {remove_cmd}"
    if remove_it:
        if remove():
            return f"Removed {FOLDER}."
        return f"Nothing to remove ({FOLDER} isn't there)."
    s = QuestView().status()
    lines = [f"scrcpy: {find_scrcpy() or 'not installed'}"]
    via = {"usb": "connected by USB", "wifi": "connected on Wi-Fi", None: "not connected"}
    lines += [
        f"{h['name']}: {via[h['via']]}"
        + (f" (Wi-Fi address {wifi_address(h['host'])})" if h["host"] else "")
        for h in s["headsets"]
    ]
    if s["why_not"]:
        lines.append(s["why_not"])
    return "\n".join(lines)
