"""The designed hub (step 10, previewed at /design) and the facts it reads beyond the plain hub's:
the arm's joints, the device list, the latest commits. No hardware, no internet."""

from datetime import date
from pathlib import Path

from test_hub_facts import _git  # same folder (pytest puts it on the path)
from test_hub_server import make_app

import lab_os.hub.server as hub_server
from lab_os.hub.commits import recent_commits

SRC = Path(__file__).resolve().parents[1] / "src" / "lab_os"
DESIGN = SRC / "hub" / "web" / "design.html"


async def test_each_look_has_its_address_and_the_theme_picks_slash(aiohttp_client, monkeypatch):
    client = await aiohttp_client(make_app())
    plain = await (await client.get("/plain")).text()
    design = await (await client.get("/design")).text()
    assert "hub.js" in plain and "/web/vendor/fonts/fonts.css" in design
    assert await (await client.get("/")).text() == plain  # the repo's theme: hub.look: plain

    for look, page in (("design", design), ("nonsense", plain)):  # an unknown look falls back
        monkeypatch.setattr(hub_server, "load_theme", lambda look=look: {"hub": {"look": look}})
        assert await (await client.get("/")).text() == page


async def test_arm_readout(aiohttp_client):
    client = await aiohttp_client(make_app())
    arm = await (await client.get("/api/arm")).json()
    assert arm["name"] == "fake-arm" and arm["connected"] is True
    assert set(arm["joints"]) >= {"shoulder_pan", "elbow_flex", "gripper"}
    assert arm["control"] == "free" and isinstance(arm["held"], bool)


async def test_devices_from_config_with_the_brains_arm_linked(aiohttp_client):
    client = await aiohttp_client(make_app())
    devs = {d["name"]: d for d in (await (await client.get("/api/devices")).json())["devices"]}
    assert devs["fake-arm"]["linked"] is True
    green = devs["so101-green"]
    assert green["borrowed"] is True and green["off_limits"] is False  # drivable since step 11
    assert green["linked"] is False  # not the arm this brain drives
    assert "ports" not in green  # nothing about where it's plugged in reaches the page


def test_recent_commits(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    for i, msg in enumerate(["first", "second\twith a tab", "third"]):
        _git(
            tmp_path, "commit", "-q", "--allow-empty", "-m", msg, when=f"2026-11-0{i + 1}T12:00:00"
        )
    got = recent_commits(2, repo=tmp_path)
    assert [c["subject"] for c in got] == ["third", "second\twith a tab"]
    assert got[0]["date"] == "2026-11-03" and len(got[0]["hash"]) >= 7
    assert recent_commits(5, repo=tmp_path / "nothing") == []
    assert date.fromisoformat(got[1]["date"])


async def test_commits_endpoint_includes_the_latest(aiohttp_client):
    client = await aiohttp_client(make_app())
    c = await (await client.get("/api/commits?days=3")).json()
    assert isinstance(c["recent"], list)


def test_the_designed_page_reads_the_brain_not_made_up_data():
    html = DESIGN.read_text()
    for endpoint in (
        "/api/status",
        "/api/arm",
        "/api/project",
        "/api/spend",
        "/api/commits",
        "/api/devices",
        "/api/chat/start",
        "/api/chat/restore",
        "/theme.json",
    ):
        assert endpoint in html, endpoint
    for fake in ("ANSWERS", "GREET_EXAMPLES", "EXAMPLE", 'id="dock"', "fonts.googleapis"):
        assert fake not in html, fake


def test_the_fonts_are_bundled_with_their_license():
    fonts = SRC / "web" / "vendor" / "fonts"
    css = (fonts / "fonts.css").read_text()
    for name in ("Orbitron", "ChakraPetch-500", "Inter", "JetBrainsMono-400", "DSEG7"):
        assert f"{name}" in css and any(fonts.glob(f"{name}*.woff2")), name
    assert "SIL OPEN FONT LICENSE" in (fonts / "OFL.txt").read_text().upper()


def test_ask_bar_icons_sit_in_the_middle_of_their_cells():
    """Quick job 22: the mic and history buttons were narrower than the space between their lines
    (the bar's flex gap after the mic, its right padding after the last button), so the icons sat
    3.7 and 4.9 px left of the middle at 1600×900 (headless Chrome, 2026-11-17; now 0.5 px). The
    concept had the same history button and gets the same fix."""
    concept = Path(__file__).resolve().parents[1] / "docs" / "design" / "hub-concept.html"
    for page in (DESIGN, concept):
        css = page.read_text()
        assert "#ask-btn .in > button { align-self: stretch; }" in css, page
        assert "#ask-btn .in > button:not([hidden]) ~ button { margin-left: -0.55rem; }" in css
        assert "#ask-btn .in { padding-right: 0; }" in css
        assert "#open-chat b:empty { display: none; }" in css
        # the gap the negative margin undoes is the bar's own
        assert "#ask-btn .in { display: flex; align-items: center; gap: 0.55rem;" in css
