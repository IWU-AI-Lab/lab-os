"""Shared test setup: no test ever sees a real API key (no .env, none from the shell), each test
starts with the repo's own config/ as the place, and nothing is written to the repo's logs/ (AI
spend, kept chats)."""

import pytest

from lab_os import config


@pytest.fixture(autouse=True)
def _no_env_file_and_default_place(monkeypatch, tmp_path_factory):
    nowhere = tmp_path_factory.mktemp("no-env") / ".env"
    monkeypatch.setattr(config, "env_file", lambda: nowhere)
    monkeypatch.setattr(config, "_active", None)
    logs = tmp_path_factory.mktemp("logs")
    monkeypatch.setattr(config, "logs_dir", lambda: logs)
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
