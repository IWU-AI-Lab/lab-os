"""Shared test setup: no test ever sees a real API key (no .env, none from the shell), each test
starts with the repo's own config/ as the place (as committed, see `committed_config`), and nothing
is written to the repo's logs/ (AI spend, kept chats)."""

import io
import shutil
import subprocess
import tarfile

import pytest

import lab_os
from lab_os import config


@pytest.fixture(scope="session")
def committed_config(tmp_path_factory):
    """The repo's config/ as last committed, in a temporary folder. In the lab, the settings page
    writes into config/ (docs/guides/hub.md → "Saved into the files"), so the working copy holds
    the lab's own choices; the tests check the committed defaults. Without git (a source copy):
    the working copy."""
    folder = tmp_path_factory.mktemp("committed")
    try:
        tar = subprocess.run(
            ["git", "-C", str(lab_os.REPO_ROOT), "archive", "HEAD", "config"],
            capture_output=True,
            check=True,
        ).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            t.extractall(folder, filter="data")
    except (OSError, subprocess.CalledProcessError, tarfile.TarError):
        shutil.copytree(lab_os.CONFIG_DIR, folder / "config")
    return folder / "config"


@pytest.fixture(autouse=True)
def _no_env_file_and_default_place(monkeypatch, tmp_path_factory, committed_config):
    nowhere = tmp_path_factory.mktemp("no-env") / ".env"
    monkeypatch.setattr(config, "env_file", lambda: nowhere)
    monkeypatch.setattr(config, "DEFAULT_DIR", committed_config)
    monkeypatch.setattr(lab_os, "CONFIG_DIR", committed_config)
    monkeypatch.setattr(config, "_active", None)
    logs = tmp_path_factory.mktemp("logs")
    monkeypatch.setattr(config, "logs_dir", lambda: logs)
    recordings = tmp_path_factory.mktemp("recordings")  # the saved greetings: never into the repo
    monkeypatch.setattr(config, "recordings_dir", lambda: recordings)
    from lab_os.hub import hub_devices  # each device's settings: never into the repo's config/

    devices_file = tmp_path_factory.mktemp("hub-devices") / "hub-devices.yaml"
    monkeypatch.setattr(hub_devices, "settings_file", lambda: devices_file)
    monkeypatch.delenv("LAB_OS_CONFIG", raising=False)
    monkeypatch.delenv("LAB_OS_VENUE", raising=False)
    monkeypatch.delenv("LAB_OS_PERSONA", raising=False)
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(key, raising=False)  # a key in the shell never reaches a test


@pytest.fixture
def locked():
    """A registry with off-limits devices: the lab has none since step 11 (the green arms are
    borrowed now), but another place may, and off_limits must keep refusing them."""
    from lab_os.devices import Device, Registry, UsbId

    port = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_LOCKED0001-if00"
    return Registry(
        {
            "locked-arm": Device(
                "locked-arm",
                "so101",
                off_limits=True,
                ports=(port,),
                usb=(UsbId(0x1A86, serial="LOCKED0001"),),
                notes="someone else's",
            ),
            "locked-cams": Device(
                "locked-cams", "camera", off_limits=True, usb=(UsbId(0x0C45, 0x6366),)
            ),
            "xarm1": Device("xarm1", "xarm1s", usb=(UsbId(0x0483, 0x5750, "xArm", "X1"),)),
        }
    )


@pytest.fixture
def aiohttp_client(aiohttp_server, aiohttp_client):
    """pytest-aiohttp's own, set up after `aiohttp_server` so that it closes first: the brain lets
    go of the fake AI and voice services while they still answer (closed the other way round, a
    hearing's goodbye waited 3 s for a service that had stopped answering)."""
    return aiohttp_client


@pytest.fixture(autouse=True)
def _fake_arm_needs_no_settling(monkeypatch):
    """The robot tools hold the last waypoint 0.5 s and wait 0.2 s more before reading where the
    arm is, for real servos that trail behind. The fake arm arrives at once, so the tests keep one
    tick of the hold (the code still runs) and skip the rest: about 0.7 s saved per move."""
    from lab_os.tools import robot

    monkeypatch.setattr(robot, "HOLD_S", 0.02)
    monkeypatch.setattr(robot, "SETTLE_S", 0.0)
