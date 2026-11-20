"""Shared test setup: no test ever sees a real API key (no .env, none from the shell), each test
starts with the repo's own config/ as the place, without the lab's own changes (config/local/: an
empty folder instead), and nothing is written to the repo's logs/ (AI spend, kept chats)."""

import pytest

from lab_os import config


@pytest.fixture(autouse=True)
def _no_env_file_and_default_place(monkeypatch, tmp_path_factory):
    nowhere = tmp_path_factory.mktemp("no-env") / ".env"
    monkeypatch.setattr(config, "env_file", lambda: nowhere)
    lab_local = tmp_path_factory.mktemp("lab-local")  # the settings page's changes in the lab
    real_local_dir = config.local_dir

    def local_dir(folder=None):
        folder = folder or config.active_dir()
        return (
            lab_local
            if folder.resolve() == config.DEFAULT_DIR.resolve()
            else real_local_dir(folder)
        )

    monkeypatch.setattr(config, "local_dir", local_dir)
    monkeypatch.setattr(config, "_active", None)
    logs = tmp_path_factory.mktemp("logs")
    monkeypatch.setattr(config, "logs_dir", lambda: logs)
    recordings = tmp_path_factory.mktemp("recordings")  # the saved greetings: never into the repo
    monkeypatch.setattr(config, "recordings_dir", lambda: recordings)
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
