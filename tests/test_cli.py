"""Both programs get as far as serving (the server isn't started: asyncio.run is faked)."""

import pytest

from lab_os import cli
from lab_os.teleop import cli as teleop_cli


@pytest.fixture
def no_run(monkeypatch):
    started = []

    def fake_run(coro):
        started.append(coro.__qualname__)
        coro.close()

    monkeypatch.setattr("asyncio.run", fake_run)
    return started


def test_lab_os_teleop_serve_starts(no_run):
    teleop_cli.main(["--quiet", "serve"])
    assert no_run == ["serve"]


def test_lab_os_serve_starts(no_run):
    cli.main(["serve", "--quiet", "--port", "8099"])
    assert no_run == ["serve"]


def test_real_arms_are_never_served_to_the_network(no_run):
    with pytest.raises(SystemExit, match="this computer only"):
        cli.main(["serve", "--host", "0.0.0.0", "--arm", "so101-white"])
    assert no_run == []
