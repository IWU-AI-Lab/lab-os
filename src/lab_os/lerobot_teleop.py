"""LeRobot's own teleop for the green set, with its Rerun view (quick job 91).

The Training page's second choice, beside LeLab: `lerobot-teleoperate` (the leader drives the
follower) with `--display_data=true`, which streams the cameras and the joints to Rerun. Run through
lab-os's own `so101` extra (`uv run --extra so101 …`), never the `lerobot` conda env.

The green rules (AGENTS.md → "Hard rules") and how this keeps them:
- **Calibration read only:** the ids of the training files (`sheep`, `shepherd`), but LeRobot reads
  them from a fresh temporary copy (`--robot.calibration_dir`), so nothing it does can write into
  LeRobot's cache. If it wants to calibrate (the motors hold another calibration than the file),
  it is stopped at once and the page says why. Its question is never answered: its input is
  closed, so even a question that gets through ends LeRobot.
- **One program per port:** the same checks as LeLab's (`lab_os.green`), and more: no program has a
  green port or a green camera open, LeLab doesn't run, and the brain itself doesn't drive a green
  arm or show a green camera.
- **No motor setup:** LeRobot's teleop connects and drives; it never sets IDs or baud rates.

Stop is like Ctrl+C: LeRobot lets go of the arms, so the follower goes limp. It bypasses lab-os's
own safety layer (STOP on the pages, the soft limits): it is LeRobot's tool, as LeLab is.
Rerun opens in its own window on this computer (not in the page: Rerun's web viewer in a frame
crashed the browser tab, 2026-11-24). The brain starts that window, so Stop closes it too.
"""

import contextlib
import importlib.util
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from lab_os import REPO_ROOT
from lab_os.devices import Registry, camera_paths, load_registry, users_of
from lab_os.green import GREEN, LELAB_PORT, Check, _answers, _serial

log = logging.getLogger(__name__)

FOLLOWER_ID, LEADER_ID = "sheep", "shepherd"  # the training files' ids (AGENTS.md)
CAMERAS = ("so101-green-cam-stand", "so101-green-cam-wrist")
RERUN_PORT = 9876  # Rerun's data server (LeRobot sends there)
# LeRobot's lines when it would calibrate (lerobot 0.6.1, so_follower.py / so_leader.py)
CALIBRATION_SIGNS = (
    "Mismatch between calibration values",
    "Press ENTER to use provided calibration",
    "Running calibration",
    "middle of its range of motion",
)
CALIBRATION_REFUSED = (
    "Stopped: LeRobot wanted to calibrate a green arm (the motors hold another calibration than "
    "the training file). Nothing was answered and nothing was written. Ask the builder."
)
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def child_env() -> dict[str, str]:
    """The environment for LeRobot and Rerun. HACK: `CI=1` turns off Rerun's anonymous usage
    data (its viewer and SDK skip it "on CI"; Rerun 0.33 has no other switch but a setting in the
    user's own config). Only for these two programs (docs/plan/current-focus.md → Hacks)."""
    return os.environ | {"CI": "1"}


def calibration_root() -> Path:
    """LeRobot's own calibration cache, where the training files are (read only)."""
    hf_home = os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface"
    return Path(hf_home) / "lerobot" / "calibration"


@dataclass
class Plan:
    """What to run, after the check: the two ports, the two training files, the cameras."""

    follower_port: str = ""
    leader_port: str = ""
    follower_calibration: Path = Path()
    leader_calibration: Path = Path()
    cameras: dict[str, str] = field(default_factory=dict)  # name in Rerun → /dev/v4l/by-path/…


def installed() -> bool:
    return all(importlib.util.find_spec(m) is not None for m in ("lerobot", "rerun"))


def check(
    registry: Registry | None = None,
    root: Path | None = None,
    proc: Path = Path("/proc"),
    by_path: str = "/dev/v4l/by-path/",
    brain_uses: tuple[str, ...] = (),
    is_installed=installed,
) -> tuple[Check, Plan]:
    """Is it safe to start LeRobot's teleop on the green set now? Opens nothing. `brain_uses`: the
    devices the brain itself has open (its arms, its open cameras): the brain's own process isn't
    seen by `users_of`."""
    c, plan = Check(), Plan()
    registry = registry or load_registry()
    root = root or calibration_root()
    c.add(
        is_installed(),
        "LeRobot and Rerun installed (lab-os's so101 extra)"
        if is_installed()
        else "LeRobot isn't installed here: run uv sync --extra so101",
    )
    follower, leader = (registry.devices.get(n) for n in GREEN)
    if not (follower and leader and len(follower.ports) == 1 and len(leader.ports) == 1):
        c.add(False, f"{' and '.join(GREEN)} aren't in devices.yaml with a port each")
        return c, plan
    plan.follower_port, plan.leader_port = follower.ports[0], leader.ports[0]
    for device, port in ((follower, plan.follower_port), (leader, plan.leader_port)):
        there = Path(port).exists()
        c.add(there, f"{device.name} (…{_serial(port)[-4:]}): plugged in" if there else
              f"{device.name} (…{_serial(port)[-4:]}): not plugged in")  # fmt: skip
    for device, ident in ((follower, FOLLOWER_ID), (leader, LEADER_ID)):
        path = root / device.training_calibration
        if not device.training_calibration or path.stem != ident:
            c.add(False, f"{device.name}: devices.yaml doesn't name the training file {ident}.json")
        elif not path.is_file():
            c.add(False, f"{device.name}: its training file {path} isn't on this computer")
        else:
            c.add(True, f"{device.name}: training calibration {path.name} (read only)")
            if device is follower:
                plan.follower_calibration = path
            else:
                plan.leader_calibration = path
    for name in CAMERAS:
        try:
            plan.cameras[name.rsplit("-", 1)[-1]] = camera_paths(name, registry, by_path)[0]
        except (KeyError, LookupError) as e:
            c.add(True, f"{name}: not used ({str(e).strip(chr(39))})")
    if _answers(LELAB_PORT):
        c.add(False, "LeLab is running: stop it first (it can open the green arms at any time)")
    mine = [n for n in (*GREEN, *CAMERAS) if n in brain_uses]
    if mine:
        c.add(
            False,
            f"lab-os itself has {', '.join(mine)} open: start lab-os with another arm, or close "
            "the Teleop page (a camera closes about 5 s later)",
        )
    for label, path in [
        (n, p) for n, p in ((GREEN[0], plan.follower_port), (GREEN[1], plan.leader_port))
    ] + [(f"camera {n}", p) for n, p in plan.cameras.items()]:
        if not Path(path).exists():
            continue
        users = users_of(path, proc)
        if users is None:
            c.add(False, f"can't tell on this computer whether another program has {label} open")
        elif users:
            who = ", ".join(users)
            c.add(False, f"{label} is open in {who}: stop it first (one program per port)")
    return c, plan


def command(plan: Plan, calibration_dir: Path, rerun_port: int | None = RERUN_PORT) -> list[str]:
    """LeRobot's teleop command for the green set. `calibration_dir`: the temporary copy (robot/
    and teleop/ inside). `rerun_port`: send to the brain's Rerun window, or None: LeRobot opens
    a Rerun window itself."""
    cameras = {
        name: {"type": "opencv", "index_or_path": path, "width": 640, "height": 480, "fps": 30}
        for name, path in plan.cameras.items()
    }
    argv = [
        "uv", "run", "--extra", "so101", "lerobot-teleoperate",
        "--robot.type=so101_follower",
        f"--robot.port={plan.follower_port}",
        f"--robot.id={FOLLOWER_ID}",
        f"--robot.calibration_dir={calibration_dir / 'robot'}",
        f"--robot.cameras={json.dumps(cameras)}",
        "--teleop.type=so101_leader",
        f"--teleop.port={plan.leader_port}",
        f"--teleop.id={LEADER_ID}",
        f"--teleop.calibration_dir={calibration_dir / 'teleop'}",
        "--display_data=true",
    ]  # fmt: skip
    if rerun_port:
        argv += ["--display_ip=127.0.0.1", f"--display_port={rerun_port}"]
    return argv


def viewer_command() -> list[str]:
    """Rerun's own window, which listens for LeRobot on this computer only."""
    return [
        "uv",
        "run",
        "--extra",
        "so101",
        "rerun",
        "--bind",
        "127.0.0.1",
        "--port",
        str(RERUN_PORT),
    ]


def copy_calibration(plan: Plan) -> Path:
    """A fresh temporary copy of the two training files, under their ids. Only reads the cache."""
    tmp = Path(tempfile.mkdtemp(prefix="lab-os-lerobot-"))
    for sub, src, ident in (
        ("robot", plan.follower_calibration, FOLLOWER_ID),
        ("teleop", plan.leader_calibration, LEADER_ID),
    ):
        (tmp / sub).mkdir()
        (tmp / sub / f"{ident}.json").write_bytes(src.read_bytes())
    return tmp


class Runner:
    """The one LeRobot teleop the brain started (and its Rerun server). `popen` for the tests."""

    def __init__(self, popen=subprocess.Popen):
        self.popen = popen
        self.proc = None
        self.viewer = None
        self.tmp: Path | None = None
        self.lines: deque[str] = deque(maxlen=30)
        self.said = ""
        self.window = False  # the brain opened Rerun's window (Stop closes it)
        self.lock = threading.Lock()

    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def state(self) -> dict:
        return {
            "running": self.running(),
            "said": self.said,
            "log": list(self.lines)[-12:],
        }

    def start(self, plan: Plan, wait_viewer_s: float = 20.0) -> str:
        with self.lock:
            if self.running():
                return "LeRobot's teleop is already running."
            self.lines.clear()
            self.said = ""
            self.tmp = copy_calibration(plan)
            self.window = self._start_viewer(wait_viewer_s)
            argv = command(plan, self.tmp, RERUN_PORT if self.window else None)
            log.info("LeRobot teleop: %s", " ".join(argv))
            self.proc = self.popen(
                argv,
                cwd=REPO_ROOT,
                env=child_env(),
                stdin=subprocess.DEVNULL,  # its calibration question can never be answered
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True,  # its own group: Stop reaches uv and LeRobot alike
            )
            threading.Thread(target=self._read, args=(self.proc,), daemon=True).start()
            return "Starting LeRobot's teleop: the follower follows the leader."

    def _start_viewer(self, wait_s: float) -> bool:
        if shutil.which("uv") is None or wait_s <= 0:
            return False
        try:
            self.viewer = self.popen(
                viewer_command(),
                cwd=REPO_ROOT,
                env=child_env(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            return False
        end = time.monotonic() + wait_s
        while time.monotonic() < end:
            if self.viewer.poll() is not None:
                return False
            if _answers(RERUN_PORT):
                return True
            time.sleep(0.3)
        return False  # LeRobot then opens a Rerun window itself

    def _read(self, proc) -> None:
        for raw in proc.stdout:
            line = ANSI.sub("", raw).rstrip()
            if line:
                self.lines.append(line)
            if any(sign in line for sign in CALIBRATION_SIGNS):
                self.said = CALIBRATION_REFUSED
                log.warning("LeRobot teleop: %s (%s)", CALIBRATION_REFUSED, line)
                self._signal(proc, signal.SIGTERM)  # not torqued yet: it was still connecting
        code = proc.wait()
        if not self.said:
            last = next((x for x in reversed(self.lines) if "Error" in x), "")
            self.said = "LeRobot's teleop stopped." + (f" {last}" if code and last else "")
        self._stop_viewer()

    @staticmethod
    def _signal(proc, sig) -> None:
        with contextlib.suppress(ProcessLookupError, PermissionError):  # already gone
            os.killpg(proc.pid, sig)

    def _stop_viewer(self) -> None:
        if self.viewer is not None and self.viewer.poll() is None:
            self._signal(self.viewer, signal.SIGTERM)
        self.viewer = None
        if self.tmp is not None:
            shutil.rmtree(self.tmp, ignore_errors=True)
            self.tmp = None

    def stop(self, wait_s: float = 5.0) -> str:
        """Like Ctrl+C: LeRobot lets go of the arms (the follower goes limp), then exits."""
        proc = self.proc
        if proc is None or proc.poll() is not None:
            self._stop_viewer()
            return "LeRobot's teleop isn't running."
        self._signal(proc, signal.SIGINT)
        try:
            proc.wait(timeout=wait_s)
        except subprocess.TimeoutExpired:
            self._signal(proc, signal.SIGTERM)
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._signal(proc, signal.SIGKILL)
        self._stop_viewer()
        self.said = "LeRobot's teleop stopped. The green follower is limp."
        return self.said


RUNNER = Runner()
