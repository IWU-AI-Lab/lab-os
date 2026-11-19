"""The lab status report (quick job 16): one read tool with the arm, devices, voice, AI, spend,
the next step and warnings, offered to the hub's chat too. Fake arm, no internet."""

import json
from dataclasses import replace

from mcp import Client
from test_hub_server import VENUE, make_app

from lab_os.ai.tools import ChatTools
from lab_os.hub.server import BRAIN, lab_status


def test_the_report_has_only_real_facts():
    app = make_app()
    r = lab_status(app)
    assert r["arm"] == {
        "name": "fake-arm",
        "connected": True,
        "driven_by": "free",
        "held_still": r["arm"]["held_still"],
        "motion_allowed": True,
    }
    assert r["hub_open_on"] == []  # no hub page connected
    assert r["internet"] is None  # not checked here: not claimed either way
    assert "next_step" in r and isinstance(r["warnings"], list)
    assert "budget_usd" not in r.get("ai_spend", {}) or r["ai_spend"]["budget_usd"] is not None
    assert r["ai_spend"]["estimated"] is True  # quick job 41: the assistant says "estimated"
    assert "this computer's brain only" in r["ai_spend"]["counts"]


def test_limits_off_and_warm_servos_are_warnings():
    app = make_app(venue=replace(VENUE, floor=False))
    from lab_os.teleop.server import LOOP

    loop = app[LOOP]
    loop.health = {"elbow_flex": {"temp_c": 63.0, "load_pct": 10.0, "volts": 12.0}}
    w = lab_status(app)["warnings"]
    assert "safety limit switched off in this venue: floor" in w
    assert any(x.startswith("servos warm (63") for x in w)


def test_a_public_venue_says_nothing_about_spend():
    app = make_app(venue=replace(VENUE, public=True))
    assert "ai_spend" not in lab_status(app)


async def test_the_hub_chat_and_ai_tools_get_it(aiohttp_client):
    app = make_app()
    await aiohttp_client(app)  # startup builds the MCP server
    chat_tools = app[BRAIN].chat.tools
    assert isinstance(chat_tools, ChatTools)
    offered = {t["function"]["name"] for t in await chat_tools.openai_tools()}
    assert "lab_status" in offered
    r = json.loads(await chat_tools.call("lab_status", "{}"))
    assert r["arm"]["name"] == "fake-arm"
    async with Client(chat_tools.server) as c:
        names = {t.name for t in (await c.list_tools()).tools}
    assert "lab_status" in names


async def test_an_unplugged_arm_is_a_warning_and_the_api_says_disconnected(aiohttp_client):
    from lab_os.teleop.server import LOOP

    app = make_app()
    client = await aiohttp_client(app)
    loop = app[LOOP]
    loop.arm.plugged = False
    loop.check_link(100.0, force=True)
    r = lab_status(app)
    assert r["arm"]["connected"] is False
    assert any("disconnected" in w for w in r["warnings"])
    st = await (await client.get("/api/status")).json()
    assert st["arm"]["connected"] is False
    arm = await (await client.get("/api/arm")).json()
    assert arm["connected"] is False and "unplugged" in arm["problem"]
