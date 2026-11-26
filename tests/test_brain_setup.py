"""`lab-os setup` (quick job 150): each check says one line, does what needs no sudo, and gives
the sudo commands to paste."""

import os

from lab_os import brain_setup as bs
from lab_os import object_labels


def test_a_missing_program_gives_its_apt_package():
    lines = bs.check_apt_programs(which=lambda p: None if p == "ffmpeg" else f"/usr/bin/{p}")
    ffmpeg = next(line for line in lines if line.part == "ffmpeg")
    assert ffmpeg.state == bs.TODO and ffmpeg.apt == "ffmpeg"
    assert all(line.state == bs.OK for line in lines if line.part != "ffmpeg")


def test_the_sudo_commands_come_together_and_never_run():
    lines = [
        bs.Line(bs.TODO, "ffmpeg", "not found", apt="ffmpeg"),
        bs.Line(bs.TODO, "adb", "not found", apt="adb"),
        bs.Line(bs.TODO, "g", "", sudo="sudo usermod -aG dialout $USER", log_out=True),
        bs.Line(bs.TODO, "c", "", sudo="sudo usermod -aG video $USER", log_out=True),
        bs.Line(bs.TODO, "ssh", "", run="ssh-copy-id raspbot1"),
        bs.Line(bs.OPTIONAL, "LeLab", "", run=bs.LELAB),
    ]
    steps = bs.next_steps(lines)
    assert "  sudo apt install ffmpeg adb" in steps
    assert "  sudo usermod -aG dialout,video $USER" in steps
    assert any("log out" in s for s in steps)
    assert "  ssh-copy-id raspbot1" in steps
    assert not any(bs.LELAB in s for s in steps)  # optional: only on its own line
    assert steps[-1] == "Then run this again: uv run lab-os setup"


def test_nothing_to_do_gives_no_steps():
    assert bs.next_steps([bs.Line(bs.OK, "x", "y"), bs.Line(bs.OPTIONAL, "z", "", run="a")]) == []


def test_an_optional_line_shows_its_command():
    line = bs.Line(bs.OPTIONAL, "LeLab", "not installed", run="uv tool install lelab")
    assert str(line).endswith("Run: uv tool install lelab")


def test_the_env_file_is_made_from_the_example(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "environ", {})  # load_env writes here: not into the real one
    path = tmp_path / ".env"
    lines = bs.check_env_file(path)
    assert path.is_file() and lines[0].state == bs.DONE
    assert lines[1].state == bs.TODO  # the example's keys are fake


def test_a_real_key_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "environ", {})  # load_env writes here: not into the real one
    path = tmp_path / ".env"
    path.write_text("GEMINI_API_KEY=abc123\n")
    lines = bs.check_env_file(path)
    assert [line.state for line in lines] == [bs.OK, bs.OK]
    assert lines[1].text == "GEMINI_API_KEY"


def test_scrcpy_is_downloaded_when_missing(monkeypatch, tmp_path):
    from lab_os import quest_view

    monkeypatch.setattr(quest_view, "find_scrcpy", lambda: None)
    line = bs.check_scrcpy(install=lambda: tmp_path / "scrcpy")
    assert line.state == bs.DONE

    def fails():
        raise OSError("no internet")

    line = bs.check_scrcpy(install=fails)
    assert line.state == bs.TODO and "quest-view --install" in line.run


def test_the_labels_model_is_built_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(object_labels, "MODEL", tmp_path / "none.onnx")
    built = []
    line = bs.check_labels_model(build=lambda: built.append(1) or 0)
    assert built and line.state == bs.DONE
    line = bs.check_labels_model(build=lambda: 1)
    assert line.state == bs.TODO and line.run == object_labels.BUILD


def test_a_group_added_but_not_yet_in_use(monkeypatch):
    import grp

    class G:
        gr_gid, gr_mem = 20, ["someone"]

    monkeypatch.setattr(grp, "getgrnam", lambda name: G)
    monkeypatch.setenv("USER", "someone")
    assert bs.check_group("dialout", "ports", gids=[20]).state == bs.OK
    line = bs.check_group("dialout", "ports", gids=[1])
    assert line.state == bs.TODO and line.log_out and not line.sudo
    monkeypatch.setenv("USER", "other")
    line = bs.check_group("dialout", "ports", gids=[1])
    assert line.sudo == "sudo usermod -aG dialout $USER"


def test_no_cameras_is_fine(tmp_path):
    assert bs.check_cameras(tmp_path).state == bs.OK


def test_the_xarm_rule(tmp_path):
    rule = tmp_path / "99-xarm.rules"
    line = bs.check_xarm_rule(rule)
    assert line.state == bs.TODO and f"sudo tee {rule}" in line.sudo
    rule.write_text(bs.XARM_RULE_TEXT)
    assert bs.check_xarm_rule(rule).state == bs.OK


def test_the_raspbots_ssh_name_is_added(tmp_path):
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "id_ed25519").write_text("key")
    lines = bs.check_raspbot_ssh(
        "raspbot1", "192.168.8.175", hostname=lambda n: n, answers=lambda n: "yes", home=tmp_path
    )
    text = (tmp_path / ".ssh" / "config").read_text()
    assert "Host raspbot1\n    HostName 192.168.8.175\n    User pi" in text
    assert [line.state for line in lines] == [bs.DONE, bs.OK]


def test_the_raspbot_without_a_key_or_an_answer(tmp_path):
    known = lambda n: "192.168.8.175"  # noqa: E731
    lines = bs.check_raspbot_ssh(
        "raspbot1", "x", hostname=known, answers=lambda n: "yes", home=tmp_path
    )
    assert lines[0].run == "ssh-keygen -t ed25519"
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "id_ed25519").write_text("key")
    lines = bs.check_raspbot_ssh(
        "raspbot1", "x", hostname=known, answers=lambda n: "key", home=tmp_path
    )
    assert lines == [lines[0]] and lines[0].run == "ssh-copy-id raspbot1"
    assert not (tmp_path / ".ssh" / "config").exists()  # it had its name: nothing added
    lines = bs.check_raspbot_ssh(
        "raspbot1", "x", hostname=known, answers=lambda n: "off", home=tmp_path
    )
    assert lines[0].state == bs.TODO and "switch the Raspbot on" in lines[0].text
    assert not lines[0].run  # nothing to run while it is off


def test_the_browser_and_lelab_and_icon(tmp_path):
    assert bs.check_browser(command=lambda url: None).sudo.startswith("wget")
    assert bs.check_browser(command=lambda url: ["/usr/bin/chromium", url]).state == bs.OK
    assert bs.check_lelab(find=lambda: None).state == bs.OPTIONAL
    assert bs.check_icon(tmp_path).state == bs.OPTIONAL


def test_lerobot_missing(monkeypatch):
    import importlib.util

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert bs.check_lerobot(True).run == "uv sync --extra so101"
    assert bs.check_lerobot(False).state == bs.OPTIONAL


def test_the_install_script_runs_the_setup():
    text = (bs.REPO_ROOT / "scripts" / "install.sh").read_text()
    code = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    assert "uv run lab-os setup" in text and not any("sudo" in line for line in code)
    assert os.access(bs.REPO_ROOT / "scripts" / "install.sh", os.X_OK)
