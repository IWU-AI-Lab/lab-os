"""The assistant opens pages (decision 2026-11-14): "pull up the teleop page", "show me the AI
spend", "go back to the hub". The asking page sends what it can show; the chat model gets an
open_page tool for those; the answer carries an `open` event for that page, typed or spoken.
A fake chat service plays the model: no internet, no keys."""

import json
from pathlib import Path

from aiohttp import web
from test_chat import setup_for
from test_voice import SECOND, fake_voice, gemini_setup, key, until  # noqa: F401 (key: a fixture)

from lab_os.ai.assistant import Assistant
from lab_os.ai.chat import Conversation, clean_pages, opened_line
from lab_os.ai.spend import SpendLog
from lab_os.personas import Persona

SRC = Path(__file__).resolve().parents[1] / "src" / "lab_os"
PAGES = {"hub": "the hub", "chat": "the conversation", "teleop": "Teleop", "spend": "AI Spend"}


def scripted_service(script, seen):
    """Each request gets the next reply of `script`: ("tool", [(name, args), …]) or
    ("words", text)."""

    async def completions(request):
        body = await request.json()
        seen.append(body)
        kind, what = script[min(len(seen), len(script)) - 1]
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await resp.prepare(request)
        if kind == "tool":
            for i, (name, args) in enumerate(what):
                call = {"index": i, "id": f"c{len(seen)}{i}", "type": "function"}
                call["function"] = {"name": name, "arguments": json.dumps(args)}
                chunk = {"choices": [{"index": 0, "delta": {"tool_calls": [call]}}]}
                await resp.write(f"data: {json.dumps(chunk)}\n\n".encode())
            end = {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}
        else:
            chunk = {"choices": [{"index": 0, "delta": {"content": what}}]}
            await resp.write(f"data: {json.dumps(chunk)}\n\n".encode())
            end = {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        usage = {"choices": [], "usage": {"prompt_tokens": 100, "completion_tokens": 10}}
        await resp.write(f"data: {json.dumps(end)}\n\ndata: {json.dumps(usage)}\n\n".encode())
        await resp.write(b"data: [DONE]\n\n")
        return resp

    async def models(request):
        return web.json_response({"data": []})

    app = web.Application()
    app.router.add_post("/v1/chat/completions", completions)
    app.router.add_get("/v1/models", models)
    return app


async def make_conv(aiohttp_server, tmp_path, script):
    seen: list = []
    server = await aiohttp_server(scripted_service(script, seen))
    setup = setup_for(server)
    conv = Conversation(
        Assistant(), SpendLog(tmp_path / "spend"), setups=lambda: {setup.name: setup}
    )
    return conv, seen


def texts(events) -> str:
    return "".join(e["text"] for e in events if e["type"] == "text")


async def test_opening_a_page_answers_at_once(aiohttp_server, tmp_path, key):  # noqa: F811
    conv, seen = await make_conv(
        aiohttp_server, tmp_path, [("tool", [("open_page", {"page": "teleop"})])]
    )
    events = [e async for e in conv.ask("Pull up the teleop page", PAGES)]
    assert {"type": "open", "page": "teleop", "title": "Teleop"} in events
    assert texts(events) == "Here's Teleop."
    assert len(seen) == 1  # no second round: nothing left to ask the model
    assert events[-1]["type"] == "done"
    tool = next(t for t in seen[0]["tools"] if t["function"]["name"] == "open_page")
    assert tool["function"]["parameters"]["properties"]["page"]["enum"] == list(PAGES)
    system = seen[0]["messages"][0]["content"]
    assert "open pages on this screen" in system and "AI Spend (spend)" in system
    assert conv.messages[-1] == {"role": "assistant", "content": "Here's Teleop."}
    assert conv.spend.month()["chats"] == 1  # the one round is still logged
    await conv.close()


async def test_back_to_the_hub(aiohttp_server, tmp_path, key):  # noqa: F811
    conv, _ = await make_conv(
        aiohttp_server, tmp_path, [("tool", [("open_page", {"page": "hub"})])]
    )
    events = [e async for e in conv.ask("Go back to the hub", PAGES)]
    assert {"type": "open", "page": "hub", "title": "the hub"} in events
    assert texts(events) == "Back to the hub."
    await conv.close()


async def test_no_pages_no_tool(aiohttp_server, tmp_path, key):  # noqa: F811
    """A page that sends nothing (an older page, another client) gets no open_page tool."""
    conv, seen = await make_conv(aiohttp_server, tmp_path, [("words", "Hello.")])
    events = [e async for e in conv.ask("Show me teleop")]
    offered = {t["function"]["name"] for t in seen[0].get("tools") or []}
    assert "open_page" not in offered and texts(events) == "Hello."  # (calculate: job 86)
    assert "open pages" not in seen[0]["messages"][0]["content"]
    await conv.close()


async def test_a_page_this_screen_lacks_is_refused(aiohttp_server, tmp_path, key):  # noqa: F811
    script = [
        ("tool", [("open_page", {"page": "monitor"})]),
        ("words", "This screen has no Monitor."),
    ]
    conv, seen = await make_conv(aiohttp_server, tmp_path, script)
    events = [e async for e in conv.ask("Show the monitor", PAGES)]
    assert not any(e["type"] == "open" for e in events)
    assert seen[1]["messages"][-1]["content"].startswith("Error: not a page here")
    assert texts(events) == "This screen has no Monitor."
    await conv.close()


async def test_opening_and_looking_something_up_asks_again(aiohttp_server, tmp_path, key):  # noqa: F811
    """Another tool in the same round (here one the chat doesn't have): the model answers after."""
    script = [
        ("tool", [("open_page", {"page": "spend"}), ("project_status", {})]),
        ("words", "Here's the spend; $1 so far."),
    ]
    conv, seen = await make_conv(aiohttp_server, tmp_path, script)
    events = [e async for e in conv.ask("Show me the AI spend and what's next", PAGES)]
    assert {"type": "open", "page": "spend", "title": "AI Spend"} in events
    assert len(seen) == 2 and texts(events) == "Here's the spend; $1 so far."
    await conv.close()


def test_clean_pages():
    junk = {"teleop": "Teleop", "Bad Id": "x", "x" * 30: "y", "ok": "", "n": 3, "monitor": "M" * 99}
    assert clean_pages(junk) == {"teleop": "Teleop", "monitor": "M" * 40}
    assert clean_pages(["teleop"]) == {} and clean_pages(None) == {}
    assert opened_line("monitor", "Monitor") == "Here's Monitor."


async def test_typed_over_the_brains_api(aiohttp_client, aiohttp_server, tmp_path, key):  # noqa: F811
    app, seen = await brain(
        aiohttp_server, tmp_path, [("tool", [("open_page", {"page": "spend"})])]
    )
    client = await aiohttp_client(app)
    resp = await client.post("/api/chat", json={"text": "show me the AI spend", "pages": PAGES})
    events = [json.loads(line) for line in (await resp.text()).splitlines() if line]
    assert {"type": "open", "page": "spend", "title": "AI Spend"} in events
    assert texts(events) == "Here's AI Spend."


async def test_spoken_the_page_opens_and_the_answer_is_said(
    aiohttp_client,
    aiohttp_server,
    tmp_path,
    key,  # noqa: F811
):
    app, seen = await brain(
        aiohttp_server, tmp_path, [("tool", [("open_page", {"page": "teleop"})])]
    )
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice")
    await ws.send_json({"type": "listen", "mode": "ask", "pages": PAGES})
    events: list = []
    await until(ws, "listening", events)
    await ws.send_bytes(SECOND)
    await ws.send_json({"type": "end"})
    await until(ws, "audio_end", events)
    assert {"type": "open", "page": "teleop", "title": "Teleop"} in events
    spoken = [e["text"] for e in events if e["type"] == "audio"]
    assert spoken == ["Here's Teleop."]
    assert "open_page" in [t["function"]["name"] for t in seen[0]["tools"]]
    await ws.close()


async def brain(aiohttp_server, tmp_path, script):
    from lab_os.hub.server import create_brain_app
    from lab_os.robots.fake import FakeArm
    from lab_os.teleop.loop import InputState, TeleopLoop
    from lab_os.venues import Venue

    seen: list = []
    ai = await aiohttp_server(scripted_service(script, seen))
    voice = await aiohttp_server(fake_voice())
    setup = setup_for(ai)
    conv = Conversation(
        Assistant(), SpendLog(tmp_path / "spend"), setups=lambda: {setup.name: setup}
    )
    arm = FakeArm()
    arm.connect()
    app = create_brain_app(
        TeleopLoop(arm=arm, inputs=InputState()),
        Venue("v", ("fake-arm",), True, 0.5),
        chat=conv,
        persona=lambda: Persona(id="p", display_name="P", voice="test", wake_word="hey_jarvis"),
        voices=lambda: {"test": gemini_setup(voice)},
    )
    return app, seen


def test_the_pages_open_what_the_assistant_says():
    design = (SRC / "hub/web/design.html").read_text()
    vr = (SRC / "hub/web/xr/hub.js").read_text()
    assert "function pagesHere" in design and "function showPage" in design
    assert "pages: pagesHere()" in design  # sent with a typed question
    assert '"text", "open", "error", "done"' in design  # a spoken turn's open event
    assert 'id="dock-say"' in design  # the docked core's reply
    assert "pagesHere()" in vr and "showPage(id, now)" in vr
    assert 'ev.type === "open"' in (SRC / "hub/web/xr/ask.js").read_text()
    js = (SRC / "web/voice.js").read_text()
    assert "pages: pages()" in js
    # the wake word keeps listening with a page open (the builder, 2026-11-14)
    assert "!S.moduleOpen && document.visibilityState" not in design
