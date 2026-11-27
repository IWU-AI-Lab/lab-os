"""Reset to default in Settings (quick job 161): a setting's line leaves the place's local/ copy,
so the files below it decide again; one row, a section or all. No hardware."""

import pytest
from test_hub_server import make_app  # same folder (pytest puts it on the path)

from lab_os import config, settings
from lab_os.hub import server as hub_server

KEY = "venue:ai_tools.max_move_cm"


@pytest.fixture
def home(tmp_path):
    folder = config.new_place(tmp_path / "home")
    config.use(folder)
    (folder / "venues" / "home.yaml").write_text(
        "name: home\nactive_devices: [fake-arm]\nmotion_allowed: true\nai_tools:\n  min_z_cm: 1\n"
    )
    return folder


def field(key: str) -> dict:
    return next(f for s in settings.read("home") for f in s["fields"] if f["key"] == key)


def test_a_changed_setting_says_so_and_its_default(home):
    assert not field(KEY)["changed"]
    assert field(KEY)["default"] == 10 == field(KEY)["value"]
    settings.write(KEY, 20, "home")
    f = field(KEY)
    assert f["value"] == 20 and f["default"] == 10 and f["changed"]


def test_reset_takes_the_line_out_and_keeps_the_rest(home):
    settings.write(KEY, 20, "home")
    settings.write("venue:ai_tools.max_joint_change_deg", 45, "home")
    local = settings.file_path("venue", "home")
    assert settings.reset(KEY, "home") == 10
    text = local.read_text()
    assert "max_move_cm" not in text and "max_joint_change_deg: 45" in text
    assert text.startswith("# This place's own settings")  # its head comment stays
    assert not field(KEY)["changed"] and field("venue:ai_tools.max_joint_change_deg")["changed"]
    # the last one: the empty section goes too, the head comment stays
    settings.reset("venue:ai_tools.max_joint_change_deg", "home")
    assert "ai_tools" not in local.read_text() and local.read_text().startswith("#")
    assert settings.reset(KEY, "home") == 10  # nothing to take out: no change, no error


def test_the_default_is_the_files_below_not_the_schema(home):
    """A place's own venue file gives the default when it has the value (not the Field's)."""
    venue = home / "venues" / "home.yaml"
    venue.write_text(venue.read_text() + "  max_move_cm: 7\n")
    settings.write(KEY, 20, "home")
    assert field(KEY)["default"] == 7
    assert settings.reset(KEY, "home") == 7


async def test_the_page_resets_several_at_once(aiohttp_client, monkeypatch):
    done = []
    monkeypatch.setattr(settings, "reset", lambda key, venue=None: done.append(key) or 1)
    client = await aiohttp_client(make_app())
    keys = ["theme:clock", "venue:max_speed_scale"]
    r = await client.post("/api/settings/reset", json={"keys": keys})
    out = await r.json()
    assert r.status == 200 and out["ok"] and done == keys and set(out["values"]) == set(keys)
    assert out["message"] == "2 settings back to the default."
    assert (await client.post("/api/settings/reset", json={"keys": ["no:such"]})).status == 400


async def test_reset_only_from_the_brains_computer(aiohttp_client, monkeypatch):
    monkeypatch.setattr(hub_server, "is_local", lambda request: False)
    client = await aiohttp_client(make_app())
    assert (await client.post("/api/settings/reset", json={"keys": ["theme:clock"]})).status == 403
