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
    assert (await client.get("/plain")).status == 404  # removed 2026-11-20: / shows it
    plain = await (await client.get("/")).text()
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


def test_the_startup_builds_nothing_big_as_the_core_arrives():
    """Quick job 23 (headless Chrome, 4× CPU slowdown, 2026-11-17): as the core arrived, the
    arrival sound made 2.6 s of fresh noise (130,000 random numbers) in the same task, and each
    jump frame threw away its line batches (megabytes), so garbage collections fell on random
    frames. Now the noise is made once at load and the batches are kept between frames."""
    html = DESIGN.read_text()
    noise = html.index("const NOISE = new Float32Array(")
    assert noise < html.index("function audio()")  # made at load, before anything plays
    whoosh = html.split("function whoosh(", 1)[1].split("\n}\n", 1)[0]
    assert "createBuffer(" not in whoosh and "Math.random() * 2 - 1" not in whoosh
    assert "src.buffer = noise; src.loop = true;" in whoosh and "src.stop(t + dur + 0.05)" in whoosh
    stars = html.split("function drawStars(", 1)[1].split("\n}\n", 1)[0]
    assert ".push(" not in stars and "Array.from(" not in stars  # nothing new per frame
    assert "put4(lineB[" in stars and "put2(pointB[" in stars
    assert "lastLines" not in html  # the impact frame reads the kept batch


# ---------- the startup as a video (quick job 34) ----------
MEDIA = SRC / "hub" / "web" / "media"


def test_the_startup_videos_match_the_theme():
    # the design stays the source: a change to the startup's numbers or color needs new recordings
    # (scripts/record_startup.py --quality …); the page would quietly draw it live otherwise
    import json

    from lab_os.theme import load_theme

    t = load_theme()
    hy = t["startup"]["hyperspace"]
    found = sorted(p.stem for p in MEDIA.glob("startup-*.json"))
    assert found == ["startup-full", "startup-maximal"]
    for name in found:
        meta = json.loads((MEDIA / f"{name}.json").read_text())
        again = f"record {name} again"
        assert name == f"startup-{meta['quality']}"
        assert (MEDIA / meta["file"]).stat().st_size > 100_000
        assert t["startup"]["style"] == meta["startup"] == "hyperspace"
        assert round(hy["ramp_s"] * 1000) == meta["ramp_ms"], again
        assert round(hy["hold_s"] * 1000) == meta["hold_ms"], again
        assert round(hy["brake_s"] * 1000) == meta["brake_ms"], again
        assert hy["impact_frame"] == meta["impact"], again
        assert t["colors"]["primary"].lower() == meta["primary"], again
    assert round(t["startup"]["unlock_s"] * 1000) == 1350  # the recorder's UNLOCK_MS


async def test_the_startup_video_is_served_and_off_by_default(aiohttp_client, tmp_path):
    from lab_os.hub.hub_devices import DeviceError, DeviceSettings

    client = await aiohttp_client(make_app())
    resp = await client.get("/hub/media/startup-full.json")
    assert resp.status == 200 and (await resp.json())["handoff_ms"] > 5000
    s = DeviceSettings(lambda: tmp_path / "hub-devices.yaml")
    assert s.get("desk") == {}  # off unless a device turns it on
    assert s.update("desk", {"startup_video": True}) == {"startup_video": True}
    import pytest

    with pytest.raises(DeviceError):
        s.update("desk", {"startup_video": "yes"})
    page = DESIGN.read_text()
    assert "screenPrefs().startup_video === true" in page and "#startup-video" in page


def test_a_card_swipe_starts_the_hub_its_own_way():
    """Quick job 79: the card reader types fast, then Enter. Only a plain number starts the hub,
    with its own unlock and sound; a person's key still starts it as before. The card's data is
    never sent, stored or logged (tried in headless Chrome: a student card, a bank card, one key,
    slow typing, Enter alone)."""
    page = DESIGN.read_text()
    detector = page.split("function startKey(e)")[1].split("\n}\n")[0]
    assert 'ignite("card")' in detector and "SWIPE.gap" in detector
    assert "fetch(" not in detector and "localStorage" not in detector
    assert "console" not in detector.replace('console.info("hub: a card swipe that', "")
    assert 'if ($("#ignite")) { startKey(e); return; }' in page
    assert "card() {" in page and "#ignite.card" in page and "CARD_MS" in page
