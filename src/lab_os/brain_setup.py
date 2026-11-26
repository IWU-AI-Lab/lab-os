"""`uv run lab-os setup`: make this computer ready as the brain, or say what is still missing
(quick job 150). `scripts/install.sh` runs it at its end.

It checks each part the brain needs and says in one line what it found or did. It does the steps
that need no sudo itself (the `.env` file, scrcpy, the labels model, the Raspbot's ssh name). It
never runs sudo: it prints the exact commands at the end, for the builder to paste. Running it
again is safe: a part that is ready stays as it is.

The pattern is a "doctor" command (like `flutter doctor` or `brew doctor`) behind a bootstrap
script (GitHub's "Scripts to Rule Them All"). uv installs the Python parts; it can't install
system packages, so those are apt commands.
"""

import grp
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable
from ctypes.util import find_library
from dataclasses import dataclass
from pathlib import Path

from lab_os import REPO_ROOT, config

OK, DONE, TODO, OPTIONAL = "OK", "DONE", "TO DO", "OPTIONAL"

XARM_RULE = Path("/etc/udev/rules.d/99-xarm.rules")
XARM_RULE_TEXT = (
    'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5750", MODE="0666"'
)
CHROME_DEB = "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
LELAB = "uv tool install --with huggingface-hub git+https://github.com/huggingface/leLab.git"
# models that are in git (models/*/README.md): the wake words and the end-of-turn model
GIT_MODELS = (
    "models/openwakeword/hey_jarvis_v0.1.onnx",
    "models/openwakeword/melspectrogram.onnx",
    "models/openwakeword/embedding_model.onnx",
    "models/smart-turn/smart-turn-v3.2-cpu.onnx",
    "models/so101/so101_new_calib.urdf",
    "models/raspbot/Raspbot-V2.urdf",
)
# programs from apt: (program or library, apt package, what the brain uses it for)
APT_PROGRAMS = (
    ("ffmpeg", "ffmpeg", "the Raspbot's recordings as .mp4"),
    ("adb", "adb", "the Quest by USB and Wi-Fi"),
    ("lsof", "lsof", "the check that no other program uses a port"),
    ("ssh", "openssh-client", "the Raspbot"),
    ("rsync", "rsync", "lab-os raspbot deploy"),
)


@dataclass
class Line:
    """One part: its state, its name, what the setup found or did, and what is still to do."""

    state: str
    part: str
    text: str
    apt: str = ""  # an apt package to install
    sudo: str = ""  # another command that needs sudo
    run: str = ""  # a command without sudo that the builder runs (the setup can't do it itself)
    log_out: bool = False  # a new group: works after the next log-in

    def __str__(self) -> str:
        more = f". Run: {self.run}" if self.state == OPTIONAL and self.run else ""
        return f"{self.state:<9}{self.part}: {self.text}{more}"


def _user() -> str:
    return os.environ.get("USER") or os.environ.get("LOGNAME") or "$USER"


# --- the checks (each returns one Line) ------------------------------------------------------


def check_environment() -> Line:
    venv = Path(sys.prefix).resolve() == (REPO_ROOT / ".venv").resolve()
    where = ".venv" if venv else sys.prefix
    return Line(OK, "Python", f"{platform.python_version()} in {where}")


def check_lerobot(want: bool = True) -> Line:
    part = "LeRobot (the SO-101 arms and the cameras)"
    if importlib.util.find_spec("lerobot") and importlib.util.find_spec("cv2"):
        return Line(OK, part, "installed (the so101 extra)")
    if not want:
        return Line(OPTIONAL, part, "not installed (--no-so101)")
    return Line(TODO, part, "not installed", run="uv sync --extra so101")


def check_git_models(root: Path = REPO_ROOT) -> Line:
    missing = [m for m in GIT_MODELS if not (root / m).is_file()]
    if missing:
        return Line(TODO, "Models in git", f"missing {', '.join(missing)}", run="git pull")
    return Line(OK, "Models in git", "the wake words, the end-of-turn model and the robot models")


def check_labels_model(build: Callable[[], int] | None = None) -> Line:
    """The Raspbot labels' model: built here (not in git) when it is missing or old."""
    from lab_os import object_labels

    part = "Labels model (the Raspbot's labels)"
    why = ""
    if not object_labels.MODEL.is_file():
        why = "built it"
    else:
        try:
            names = object_labels.Detector(threads=1).names
        except Exception as e:  # noqa: BLE001 (a broken file: build it again)
            names, why = [], f"built it again (the old file did not load: {e})"
        if not why and names and names != object_labels.load_words():
            why = "built it again (the words in config/labels.yaml changed)"
        if not why:
            return Line(OK, part, config.shown_path(object_labels.MODEL))
    print("Building the labels model. It needs the internet and takes some minutes.")
    if (build or object_labels.build)() == 0:
        return Line(DONE, part, why)
    return Line(TODO, part, "the build failed (read its lines above)", run=object_labels.BUILD)


def check_scrcpy(install: Callable[[], Path] | None = None) -> Line:
    from lab_os import quest_view

    part = "scrcpy (Quest view)"
    found = quest_view.find_scrcpy()
    if found:
        return Line(OK, part, config.shown_path(found))
    try:
        program = (install or quest_view.install)()
    except (quest_view.QuestViewError, OSError) as e:
        return Line(
            TODO, part, f"the download failed ({e})", run="uv run lab-os quest-view --install"
        )
    return Line(DONE, part, f"downloaded {quest_view.VERSION} to {config.shown_path(program)}")


def check_env_file(path: Path | None = None) -> list[Line]:
    """The .env file (made from .env.example when missing) and the AI keys in it."""
    path = path or config.env_file()
    shown = config.shown_path(path)
    lines = []
    if not path.is_file():
        example = REPO_ROOT / ".env.example"
        shutil.copyfile(example, path)
        lines.append(Line(DONE, ".env", f"made {shown} from .env.example"))
    else:
        lines.append(Line(OK, ".env", shown))
    config.load_env(path)

    def real(name: str) -> bool:
        value = os.environ.get(name, "")
        return bool(value) and not value.startswith("fake-")

    keys = [n for n in ("OPENAI_API_KEY", "GEMINI_API_KEY") if real(n)]
    if keys:
        lines.append(Line(OK, "AI keys", ", ".join(keys)))
    else:
        lines.append(
            Line(
                TODO,
                "AI keys",
                f"put OPENAI_API_KEY or GEMINI_API_KEY in {shown} (docs/dev/chat.md)",
            )
        )
    return lines


def check_apt_programs(which: Callable[[str], str | None] = shutil.which) -> list[Line]:
    lines = []
    for program, package, why in APT_PROGRAMS:
        found = which(program)
        if found:
            lines.append(Line(OK, program, found))
        else:
            lines.append(Line(TODO, program, f"not found ({why})", apt=package))
    return lines


def check_browser(command: Callable[[str], list[str] | None] | None = None) -> Line:
    from lab_os.hub import launch

    found = (command or launch.browser_command)("http://localhost:8080/")
    if found:
        return Line(OK, "Browser (the hub's window)", Path(found[0]).name)
    return Line(
        TODO,
        "Browser (the hub's window)",
        "no Chrome-like browser found",
        sudo=f"wget -P /tmp {CHROME_DEB} && sudo apt install /tmp/{CHROME_DEB.rsplit('/', 1)[1]}",
    )


def check_group(name: str, why: str, gids: list[int] | None = None) -> Line:
    """The user is in group `name` (dialout: the arms' serial ports)."""
    part = f"Group {name} ({why})"
    try:
        group = grp.getgrnam(name)
    except KeyError:
        return Line(OK, part, f"there is no group {name} on this computer")
    if group.gr_gid in (os.getgroups() if gids is None else gids):
        return Line(OK, part, f"{_user()} is in it")
    if _user() in group.gr_mem:
        return Line(TODO, part, "added, but not yet in use: log out and in again", log_out=True)
    return Line(
        TODO, part, f"{_user()} is not in it", sudo=f"sudo usermod -aG {name} $USER", log_out=True
    )


def check_cameras(dev: Path = Path("/dev")) -> Line:
    cams = sorted(dev.glob("video*"))
    part = "Cameras"
    if not cams:
        return Line(OK, part, "none plugged in now")
    closed = [c.name for c in cams if not os.access(c, os.R_OK | os.W_OK)]
    if not closed:
        return Line(OK, part, f"{len(cams)} video devices, all open to {_user()}")
    return Line(
        TODO,
        part,
        f"{', '.join(closed)} are closed to {_user()}",
        sudo="sudo usermod -aG video $USER",
        log_out=True,
    )


def check_hidapi(lib: Callable[[str], str | None] = find_library) -> Line:
    part = "hidapi (the xArm arms)"
    if lib("hidapi-hidraw"):
        return Line(OK, part, "installed")
    return Line(TODO, part, "not installed", apt="libhidapi-hidraw0")


def check_xarm_rule(rule: Path = XARM_RULE) -> Line:
    part = "xArm USB rule"
    if rule.is_file():
        return Line(OK, part, str(rule))
    return Line(
        TODO,
        part,
        "missing (the xArm opens only as root)",
        sudo=f"echo '{XARM_RULE_TEXT}' | sudo tee {rule} && sudo udevadm control --reload-rules "
        "&& sudo udevadm trigger --subsystem-match=hidraw",
    )


def ssh_hostname(name: str) -> str:
    """The address `ssh name` goes to (`ssh -G`, which connects to nothing)."""
    try:
        out = subprocess.run(["ssh", "-G", name], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return name
    for line in out.splitlines():
        if line.startswith("hostname "):
            return line.split(" ", 1)[1].strip()
    return name


def ssh_answers(name: str) -> str:
    """Try `ssh name true` without a password (it only connects and runs `true`): "yes", "key"
    (the Raspbot answered but refused the key) or "off" (no answer)."""
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", name, "true"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "off"
    if r.returncode == 0:
        return "yes"
    return "key" if "Permission denied" in r.stderr else "off"


def check_raspbot_ssh(
    name: str,
    host: str,
    ssh_config: Path | None = None,
    hostname: Callable[[str], str] = ssh_hostname,
    answers: Callable[[str], str] = ssh_answers,
    home: Path | None = None,
) -> list[Line]:
    """`ssh <name>` reaches the Raspbot: its ssh name (added to ~/.ssh/config when missing), a
    key, and the key on the Raspbot."""
    home = home or Path.home()
    ssh_config = ssh_config or home / ".ssh" / "config"
    part = f"ssh {name}"
    lines = []
    if hostname(name) == name and host:
        ssh_config.parent.mkdir(mode=0o700, exist_ok=True)
        with ssh_config.open("a") as f:
            f.write(f"\n# lab-os setup: the Raspbot (config/devices.yaml)\nHost {name}\n")
            f.write(f"    HostName {host}\n    User pi\n")
        lines.append(Line(DONE, part, f"added {name} → pi@{host} to ~/.ssh/config"))
    if not any((home / ".ssh" / k).is_file() for k in ("id_ed25519", "id_ecdsa", "id_rsa")):
        lines.append(Line(TODO, part, "this computer has no ssh key", run="ssh-keygen -t ed25519"))
        return lines
    answer = answers(name)
    if answer == "yes":
        lines.append(Line(OK, part, "answers without a password"))
    elif answer == "key":
        lines.append(
            Line(
                TODO,
                part,
                "the Raspbot does not know this computer's key",
                run=f"ssh-copy-id {name}",
            )
        )
    else:
        lines.append(
            Line(
                TODO,
                part,
                f"no answer: switch the Raspbot on, then run this again. If it asks for a "
                f"password, run: ssh-copy-id {name}",
            )
        )
    return lines


def check_lelab(find: Callable[[], str | None] | None = None) -> Line:
    from lab_os import green

    part = "LeLab (the Training page)"
    found = (find or green._lelab)()
    if found:
        return Line(OK, part, found)
    return Line(OPTIONAL, part, "not installed (only for the green arms' training)", run=LELAB)


def check_icon(folder: Path | None = None) -> Line:
    from lab_os.hub import launch

    folder = folder or Path.home() / ".local" / "share" / "applications"
    part = 'The "Start lab-os" icon'
    if (folder / launch.ICON_FILE).is_file():
        return Line(OK, part, config.shown_path(folder / launch.ICON_FILE))
    return Line(OPTIONAL, part, "not made", run="uv run lab-os icon --device desk")


# --- the whole setup -------------------------------------------------------------------------


def all_checks(so101: bool = True) -> list[Line]:
    """Every part, in order. Linux only for the system parts."""
    from lab_os.devices import load_registry

    lines = [check_environment(), check_lerobot(so101), check_git_models()]
    lines += check_env_file()
    lines += [check_scrcpy(), check_labels_model()]
    if not sys.platform.startswith("linux"):
        lines.append(Line(OPTIONAL, "System parts", "lab-os setup checks them on Linux only"))
        return lines
    registry = load_registry()
    kinds = {d.kind for d in registry.devices.values()}
    lines += check_apt_programs()
    lines += [check_browser(), check_group("dialout", "the arms' serial ports"), check_cameras()]
    if kinds & {"xarm1s"}:
        lines += [check_hidapi(), check_xarm_rule()]
    for d in registry.devices.values():
        if d.kind == "raspbot":
            lines += check_raspbot_ssh(d.name, d.host)
    lines += [check_lelab(), check_icon()]
    return lines


def next_steps(lines: list[Line]) -> list[str]:
    """The commands still to run, sudo first, as lines to paste."""
    out = []
    packages = [line.apt for line in lines if line.apt]
    sudo = [line.sudo for line in lines if line.sudo]
    groups = [c.rsplit(" ", 1)[0].split()[-1] for c in sudo if c.startswith("sudo usermod -aG")]
    sudo = [c for c in sudo if not c.startswith("sudo usermod -aG")]
    if packages:
        sudo.insert(0, f"sudo apt install {' '.join(packages)}")
    if groups:
        sudo.append(f"sudo usermod -aG {','.join(groups)} $USER")
    if sudo:
        out.append("Paste these in a terminal (they need sudo):")
        out += [f"  {c}" for c in sudo]
    if any(line.log_out for line in lines if line.state == TODO):
        out.append("Then log out and in again (a new group works after the next log-in).")
    runs = [line.run for line in lines if line.run and line.state == TODO]
    if runs:
        out.append("Run these here:")
        out += [f"  {c}" for c in runs]
    if out or any(line.state == TODO for line in lines):
        out.append("Then run this again: uv run lab-os setup")
    return out


def main(so101: bool = True) -> int:
    """`lab-os setup`: 0 when this computer is ready as the brain."""
    from lab_os import term

    lines = all_checks(so101)
    for line in lines:
        print(term.warning(str(line)) if line.state == TODO else str(line))
    steps = next_steps(lines)
    if not any(line.state == TODO for line in lines):
        print("This computer is ready as the brain. Start it: uv run lab-os serve")
        return 0
    print()
    print("\n".join(steps))
    return 1
