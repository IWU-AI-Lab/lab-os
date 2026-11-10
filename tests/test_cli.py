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


def test_a_real_arm_on_the_network_is_driven_from_this_computer_only(no_run, monkeypatch):
    """--host 0.0.0.0 with a real arm: other screens may open the hub, but only watch the arm
    (local_control_only); with the fake arm, any screen may drive it."""
    from lab_os.robots.fake import FakeArm
    from lab_os.teleop.loop import InputState, TeleopLoop

    seen = []
    real = cli.create_brain_app
    monkeypatch.setattr(
        cli,
        "create_brain_app",
        lambda *a, **kw: seen.append(kw["local_control_only"]) or real(*a, **kw),
    )
    arm = FakeArm()  # stands in for so101-white: no hardware in tests
    monkeypatch.setattr(cli, "make_loop", lambda args: TeleopLoop(arm=arm, inputs=InputState()))
    cli.main(["serve", "--host", "0.0.0.0", "--arm", "so101-white"])
    cli.main(["serve", "--host", "0.0.0.0"])
    cli.main(["serve", "--arm", "so101-white"])
    assert seen == [True, False, False] and no_run == ["serve"] * 3
