"""The place's config folder (rule 9): --config, place files vs. shared files, .env, off limits."""

import os
import re
from pathlib import Path

import pytest

from lab_os import cli, config
from lab_os.devices import PortNotAllowed, default_device, load_registry, serial_port
from lab_os.theme import load_theme
from lab_os.venues import load_venue

SRC = Path(__file__).resolve().parents[1] / "src" / "lab_os"


@pytest.fixture
def home(tmp_path):
    """A second place, made with the starter, and switched to."""
    folder = config.new_place(tmp_path / "my-lab-os")
    config.use(folder)
    return folder


@pytest.fixture
def no_run(monkeypatch):
    started = []

    def fake_run(coro):
        started.append(coro)
        coro.close()

    monkeypatch.setattr("asyncio.run", fake_run)
    return started


def test_the_repo_config_is_the_lab():
    assert config.is_default()
    place = config.load_place()
    assert place.name == "AI Comp Lab"
    assert place.domain == "hub.indwesailab.com"
    assert load_venue().name == "lab"


def test_hub_title_left_the_theme():
    assert "title" not in (load_theme().get("hub") or {})


def test_nothing_place_specific_in_code():
    """The lab's name and domain live in config/place.yaml, never in the code or the pages."""
    for path in SRC.rglob("*"):
        if path.suffix in {".py", ".js", ".html", ".css"} and "vendor" not in path.parts:
            text = path.read_text()
            for word in ("AI Comp Lab", "indwesailab"):
                assert word not in text, f"{word!r} in {path.relative_to(SRC)}"


def test_new_place_writes_a_starter(home):
    for name in ("place.yaml", "devices.yaml", "venues/home.yaml", ".env.example"):
        assert (home / name).is_file(), name
    assert config.load_place().name == "My lab"
    assert load_venue().name == "home"
    assert load_venue().active_devices == ("fake-arm",)


def test_new_place_never_copies_keys(tmp_path, monkeypatch):
    """Someone's .env saved in the template (by mistake) must not spread to every new place."""
    import shutil

    template = tmp_path / "template"
    shutil.copytree(config.TEMPLATE_DIR, template)
    (template / ".env").write_text("GEMINI_API_KEY=real-key\n")
    monkeypatch.setattr(config, "TEMPLATE_DIR", template)
    folder = config.new_place(tmp_path / "home")
    assert (folder / ".env.example").is_file() and not (folder / ".env").exists()


def test_a_missing_env_is_named(tmp_path, caplog):
    with caplog.at_level("WARNING"):
        config.use(tmp_path)
    assert f"no {config.env_file()}: no API keys" in caplog.text


def test_new_place_never_overwrites(home):
    with pytest.raises(config.ConfigError, match="already has a place.yaml"):
        config.new_place(home)


def test_place_files_never_come_from_the_lab(tmp_path):
    config.use(tmp_path)
    with pytest.raises(config.ConfigError, match="no place.yaml"):
        config.load_place()
    with pytest.raises(config.ConfigError, match="no devices.yaml"):
        load_registry()
    (tmp_path / "venues").mkdir()
    with pytest.raises(config.ConfigError, match="no venue 'lab'"):
        load_venue("lab")


def test_shared_files_fall_back_to_the_repo(home):
    assert config.shared_path("theme.yaml") == config.DEFAULT_DIR / "theme.yaml"
    assert load_theme()["colors"]["primary"]
    (home / "poses.yaml").write_text("so101: {}\n")
    assert config.shared_path("poses.yaml") == home / "poses.yaml"


def test_the_lab_borrowed_devices_stay_borrowed_at_every_place(home):
    (home / "devices.yaml").write_text(
        "devices:\n"
        "  fake-arm: {kind: fake}\n"
        "  so101-green: {kind: so101, ports: [/dev/serial/by-id/usb-1a86_x-if00]}\n"
    )
    reg = load_registry()
    green = reg.devices["so101-green"]
    assert green.borrowed and green.training_calibration  # the home entry can't drop the rules
    assert green.ports[0].endswith("5B41533501-if00")
    assert reg.devices["so101-green-cam-wrist"].borrowed
    assert "so101-white" not in reg.devices  # the lab's other devices don't come along


def test_the_repos_off_limits_devices_stay_off_limits_at_every_place(home, tmp_path, monkeypatch):
    repo = tmp_path / "repo-config"
    repo.mkdir()
    (repo / "devices.yaml").write_text(
        "devices:\n  locked-arm: {kind: so101, off_limits: true, "
        "ports: [/dev/serial/by-id/usb-1a86_LOCKED-if00]}\n"
    )
    monkeypatch.setattr(config, "DEFAULT_DIR", repo)
    (home / "devices.yaml").write_text(
        "devices:\n  locked-arm: {kind: so101, ports: [/dev/serial/by-id/usb-1a86_x-if00]}\n"
    )
    reg = load_registry()
    assert reg.devices["locked-arm"].off_limits  # the home entry can't make it openable
    with pytest.raises(PortNotAllowed):
        serial_port("locked-arm", reg)


def test_default_device_is_the_only_usable_one():
    assert default_device(("so101",)) == "so101-white"  # green is borrowed: name it
    assert default_device(("xarm1s",)) == "xarm1"  # xarm2 has no port or USB entry
    with pytest.raises(LookupError, match="which camera"):
        default_device(("camera",))


def test_env_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "# comment\n\nLAB_TEST_A=one\nexport LAB_TEST_B='two words'\nLAB_TEST_C=new\nnot a line\n"
    )
    monkeypatch.setenv("LAB_TEST_C", "already set")
    for key in ("LAB_TEST_A", "LAB_TEST_B"):
        monkeypatch.delenv(key, raising=False)
    assert config.load_env(env) == ["LAB_TEST_A", "LAB_TEST_B"]
    assert os.environ["LAB_TEST_A"] == "one"
    assert os.environ["LAB_TEST_B"] == "two words"
    assert os.environ["LAB_TEST_C"] == "already set"  # the real environment wins
    for key in ("LAB_TEST_A", "LAB_TEST_B"):
        monkeypatch.delenv(key)


def test_the_place_env_file_is_in_its_folder(home, monkeypatch):
    monkeypatch.undo()  # the real env_file(), not the tests' "nowhere"
    config.use(home)
    assert config.env_file() == home / ".env"


def test_unknown_place_fields_are_kept_with_a_warning(home, caplog):
    (home / "place.yaml").write_text("version: 1\nname: Garage\nfavourite_color: green\n")
    place = config.load_place()
    assert place.name == "Garage"
    assert place.extra == {"favourite_color": "green"}
    assert "favourite_color" in caplog.text


def test_serve_with_another_config_folder(tmp_path, no_run, capsys):
    folder = tmp_path / "home-config"
    cli.main(["new-place", str(folder)])
    assert "Wrote" in capsys.readouterr().out
    cli.main(["serve", "--config", str(folder), "--quiet", "--mcp-port", "0"])
    assert len(no_run) == 1
    assert config.active_dir() == folder.resolve()


def test_serve_refuses_an_unknown_persona(home, no_run):
    at_home = ["serve", "--config", str(home), "--quiet", "--mcp-port", "0"]
    with pytest.raises(SystemExit, match="no persona 'jarvsi'"):
        cli.main([*at_home, "--persona", "jarvsi"])
    cli.main([*at_home, "--persona", "jarvis"])
    assert len(no_run) == 1


def test_serve_refuses_a_missing_folder(tmp_path, no_run):
    with pytest.raises(SystemExit, match="doesn't exist"):
        cli.main(["serve", "--config", str(tmp_path / "nope"), "--quiet"])


def test_arm_must_be_in_the_device_list(home, no_run, monkeypatch):
    """Both refusals happen before any driver is made, so nothing real is ever opened here."""

    def no_driver(*a, **kw):
        raise AssertionError("a real driver was made")

    monkeypatch.setattr("lab_os.robots.so101.SO101Arm", no_driver)
    monkeypatch.setattr("lab_os.robots.xarm.XArm", no_driver)
    at_home = ["serve", "--config", str(home), "--quiet"]
    with pytest.raises(SystemExit, match="fake, fake-xarm1 or an arm from devices.yaml: none"):
        cli.main([*at_home, "--arm", "so101-white"])  # the lab's arm isn't at this place
    with pytest.raises(SystemExit, match="so101-green is not active in venue 'home'"):
        cli.main([*at_home, "--arm", "so101-green"])  # the lab's green arm isn't here either
    assert no_run == []


def test_the_green_follower_is_driven_like_the_white_one_at_the_lab(no_run, monkeypatch):
    made = []

    def driver(**kw):
        made.append(kw)
        raise RuntimeError("stop here: no real arm in tests")

    monkeypatch.setattr("lab_os.robots.so101.SO101Arm", driver)
    with pytest.raises(RuntimeError, match="stop here"):
        cli.main(["serve", "--quiet", "--arm", "so101-green"])
    assert made == [{"name": "so101-green", "allow_motion": True}]
    with pytest.raises(SystemExit, match="not an arm lab-os can drive"):
        cli.main(["serve", "--quiet", "--arm", "so101-green-leader"])  # a leader isn't driven
    assert no_run == []


async def test_the_hub_title_is_the_place_name(aiohttp_client, home):
    from lab_os.hub.server import create_brain_app
    from lab_os.robots.fake import FakeArm
    from lab_os.teleop.loop import InputState, TeleopLoop

    arm = FakeArm()
    arm.connect()
    app = create_brain_app(TeleopLoop(arm=arm, inputs=InputState()), load_venue())
    client = await aiohttp_client(app)
    assert (await (await client.get("/api/hub")).json())["title"] == "My lab"
    js = (SRC / "hub" / "web" / "hub.js").read_text()
    assert re.search(r"cfg\?\.title", js) and "hubCfg.title" not in js


def test_one_to_one_speed_per_venue():
    from lab_os.venues import one_to_one_speed

    assert one_to_one_speed(180) == 180.0
    assert one_to_one_speed("240") == 240.0
    assert one_to_one_speed(None) == one_to_one_speed("off") == one_to_one_speed(0) == 0.0
    assert one_to_one_speed("none") == float("inf")
    with pytest.raises(config.ConfigError):
        one_to_one_speed(-5)
    assert load_venue("lab", config.DEFAULT_DIR).one_to_one_deg_per_s == 180.0
    assert load_venue("visit-day", config.DEFAULT_DIR).one_to_one_deg_per_s == 180.0  # 2026-11-18


def test_a_port_in_use_stops_serve_with_a_sentence(no_run, monkeypatch):
    from lab_os.devices import InUse

    class Busy:
        name = "so101-green"

        def __init__(self, **kw):
            pass

        def connect(self):
            raise InUse("so101-green is in use by lelab (pid 42): one program per port. …")

    monkeypatch.setattr("lab_os.robots.so101.SO101Arm", Busy)
    with pytest.raises(SystemExit, match="--arm so101-green: not opened. so101-green is in use"):
        cli.main(["serve", "--quiet", "--arm", "so101-green"])
    assert no_run == []
