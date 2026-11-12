"""The Claude Code guard hook (.claude/hooks/guard.sh): since step 11 the green ports are fine,
LeRobot's cache is read only, and the lerobot env stays untouched. Runs the script on sample
commands; nothing is executed."""

import json
import shutil
import subprocess

import pytest

from lab_os import REPO_ROOT

HOOK = REPO_ROOT / ".claude" / "hooks" / "guard.sh"
CAL = "~/.cache/huggingface/lerobot/calibration/robots/so101_follower"
GREEN = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41533501-if00"

pytestmark = pytest.mark.skipif(
    not (shutil.which("jq") and shutil.which("bash")), reason="the hook needs bash and jq"
)


def decision(command: str) -> str:
    """deny / ask / allow (the hook said nothing)."""
    out = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else "allow"


@pytest.mark.parametrize(
    "command",
    [
        f"ls -l {GREEN}",
        "ls -l /dev/serial/by-id/",
        "uv run --extra so101 lab-os serve --arm so101-green --speed 0.3",
        f"uv run python -m lab_os.robots.so101 so101-green  # reads {GREEN}",
        f"ls -l {CAL}/",
        f"cat {CAL}/green.json",
        f"jq . {CAL}/green.json 2>/dev/null",
        f"diff {CAL}/a.json {CAL}/b.json 2>&1",
    ],
)
def test_allowed(command):
    assert decision(command) == "allow"


@pytest.mark.parametrize(
    "command",
    [
        f"rm {CAL}/green.json",
        f"mv {CAL}/green.json /tmp/x",
        f"cp other.json {CAL}/green.json",
        f"echo '{{}}' > {CAL}/green.json",
        f"cat x | tee {CAL}/green.json",
        f"sed -i s/1/2/ {CAL}/green.json",
        f"find {CAL} -name '*.json' -delete",
        f'python3 -c \'open("{CAL}/g.json","w")\'',
        f"lerobot-calibrate --robot.calibration_dir={CAL}",
        "rm ~/.cache/huggingface/lerobot/ports/leader_port.txt",  # LeLab's settings too
        "conda run -n lerobot pip install torch",
        "~/miniforge3/envs/lerobot/bin/pip install x",
        "rm -rf ~/lerobot",
    ],
)
def test_denied(command):
    assert decision(command) == "deny"


def test_raw_tty_names_ask():
    assert decision("ls -l /dev/ttyACM0") == "ask"
