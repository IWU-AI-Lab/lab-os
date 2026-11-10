"""Typed chat (step 5): setups, the client, the conversation manager, spend, the endpoints.
A fake OpenAI-style server stands in for the AI service: no internet, no keys."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from aiohttp import web

from lab_os import config
from lab_os.ai.assistant import Assistant
from lab_os.ai.chat import Conversation
from lab_os.ai.client import AiError, Reply, Usage, check, stream_chat
from lab_os.ai.models import NoSetup, Setup, load_setups, pick
from lab_os.ai.spend import SpendLog

SRC = Path(__file__).resolve().parents[1] / "src" / "lab_os"


# ---------- a fake OpenAI-style AI service ----------


def fake_service(words=("Hello", " there", "."), status=200, usage=True, seen=None):
    """aiohttp app answering /v1/chat/completions (streamed) and /v1/models."""

    async def completions(request):
        body = await request.json()
        if seen is not None:
            seen.append({"body": body, "auth": request.headers.get("Authorization")})
        if status != 200:
            return web.json_response({"error": {"message": "nope"}}, status=status)
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await resp.prepare(request)
        for w in words:
            chunk = {"choices": [{"index": 0, "delta": {"content": w}, "finish_reason": None}]}
            await resp.write(f"data: {json.dumps(chunk)}\n\n".encode())
        end = {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        await resp.write(f"data: {json.dumps(end)}\n\n".encode())
        if usage:
            u = {
                "choices": [],
                "usage": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 200,
                    "prompt_tokens_details": {"cached_tokens": 400},
                },
            }
            await resp.write(f"data: {json.dumps(u)}\n\n".encode())
        await resp.write(b"data: [DONE]\n\n")
        return resp

    async def models(request):
        ok = request.headers.get("Authorization") == "Bearer test-key"
        return web.json_response({"data": []}, status=200 if ok else 401)

    app = web.Application()
    app.router.add_post("/v1/chat/completions", completions)
    app.router.add_get("/v1/models", models)
    return app


def setup_for(server, **kw) -> Setup:
    return Setup(
        name=kw.pop("name", "main"),
        base_url=str(server.make_url("/v1")),
        model="test-model",
        key_env="LAB_TEST_KEY",
        where="Test AI",
        price_in=0.10,
        price_cached=0.01,
        price_out=0.50,
        options={"max_completion_tokens": 100},
        **kw,
    )


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("LAB_TEST_KEY", "test-key")


def conversation(setup, tmp_path, budget=None, assistant=None):
    return Conversation(
        assistant or Assistant(),
        SpendLog(tmp_path / "spend", budget),
        setup_name=setup.name,
        personality="Be brief.",
        place_name="Test Lab",
        setups=lambda: {setup.name: setup},
    )


async def collect(conv, text):
    return [e async for e in conv.ask(text)]


# ---------- setups ----------


def test_models_yaml_setups():
    setups = load_setups()
    assert {"main", "backup", "local"} <= set(setups)
    main = setups["main"]
    assert main.base_url == "https://api.openai.com/v1"
    assert main.key_env == "OPENAI_API_KEY"
    assert main.fallback == "backup"
    assert setups["backup"].key_env == "GEMINI_API_KEY"
    assert "generativelanguage.googleapis.com" in setups["backup"].base_url
    assert setups["local"].key_env is None and setups["local"].local
    assert not main.local


def test_fallback_when_a_key_is_missing(monkeypatch):
    setups = load_setups()
    with pytest.raises(NoSetup, match=r"add OPENAI_API_KEY or GEMINI_API_KEY to /.+/\.env, then"):
        pick("main", setups)
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    assert pick("main", setups).name == "backup"
    monkeypatch.setenv("OPENAI_API_KEY", "o")
    assert pick("main", setups).name == "main"
    assert pick("local", setups).name == "local"  # no key needed
    with pytest.raises(NoSetup, match="no AI setup called 'nope'"):
        pick("nope", setups)


def test_cost():
    s = Setup("x", "http://h/v1", "m", price_in=0.10, price_cached=0.01, price_out=0.50)
    # 600 fresh input + 400 cached + 200 output
    assert s.cost(1000, 200, 400) == pytest.approx((600 * 0.10 + 400 * 0.01 + 200 * 0.50) / 1e6)


# ---------- the client ----------


async def test_stream_chat(aiohttp_server, key):
    seen = []
    server = await aiohttp_server(fake_service(seen=seen))
    setup = setup_for(server)
    reply = Reply()
    import aiohttp

    async with aiohttp.ClientSession() as session:
        pieces = [
            p async for p in stream_chat(session, setup, [{"role": "user", "content": "hi"}], reply)
        ]
        assert await check(session, setup)
    assert pieces == ["Hello", " there", "."]
    assert reply.text == "Hello there."
    assert reply.finish_reason == "stop"
    assert reply.usage == Usage(1000, 200, 400)
    body = seen[0]["body"]
    assert body["model"] == "test-model" and body["stream"] is True
    assert body["max_completion_tokens"] == 100  # the setup's options go along
    assert body["stream_options"] == {"include_usage": True}
    assert seen[0]["auth"] == "Bearer test-key"


async def test_usage_is_estimated_when_the_service_says_nothing(aiohttp_server, key):
    server = await aiohttp_server(fake_service(usage=False))
    reply = Reply()
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async for _ in stream_chat(
            session, setup_for(server), [{"role": "user", "content": "hi"}], reply
        ):
            pass
    assert reply.usage.estimated and reply.usage.tokens_out > 0


@pytest.mark.parametrize(
    "status, words", [(401, "refused the API key"), (429, "out of credit"), (404, "doesn't know")]
)
async def test_http_errors_become_sentences(aiohttp_server, key, status, words):
    server = await aiohttp_server(fake_service(status=status))
    import aiohttp

    async with aiohttp.ClientSession() as session:
        with pytest.raises(AiError, match=words):
            async for _ in stream_chat(session, setup_for(server), [], Reply()):
                pass


async def test_unreachable_service(key, unused_tcp_port):
    import aiohttp

    setup = Setup("main", f"http://127.0.0.1:{unused_tcp_port}/v1", "m", key_env="LAB_TEST_KEY")
    async with aiohttp.ClientSession() as session:
        with pytest.raises(AiError, match="can't reach"):
            async for _ in stream_chat(session, setup, [], Reply()):
                pass
        assert not await check(session, setup)


# ---------- the conversation manager ----------


async def test_a_turn_sets_the_states_and_logs_the_cost(aiohttp_server, key, tmp_path):
    seen = []
    server = await aiohttp_server(fake_service(seen=seen))
    assistant = Assistant()
    conv = conversation(setup_for(server), tmp_path, assistant=assistant)
    assert await conv.check() is True and assistant.state == "idle"
    events = await collect(conv, "What's next?")
    states = [e["state"] for e in events if e["type"] == "state"]
    assert states == ["thinking", "speaking", "idle"]
    assert "".join(e["text"] for e in events if e["type"] == "text") == "Hello there."
    done = events[-1]
    assert done["type"] == "done" and done["cost_usd"] == pytest.approx(0.000164)
    assert conv.messages == [
        {"role": "user", "content": "What's next?"},
        {"role": "assistant", "content": "Hello there."},
    ]
    system = seen[0]["body"]["messages"][0]
    assert system["role"] == "system"
    assert "Be brief." in system["content"] and "Test Lab" in system["content"]
    assert "can't change or move anything" in system["content"]
    month = conv.spend.month()
    assert month["chats"] == 1 and month["by_setup"] == {"main": pytest.approx(0.000164)}
    await conv.close()


async def test_the_conversation_goes_along_and_clears(aiohttp_server, key, tmp_path):
    seen = []
    server = await aiohttp_server(fake_service(seen=seen))
    conv = conversation(setup_for(server), tmp_path)
    await collect(conv, "one")
    await collect(conv, "two")
    assert [m["content"] for m in seen[1]["body"]["messages"][1:]] == ["one", "Hello there.", "two"]
    conv.clear()
    assert conv.messages == []
    await conv.close()


async def test_an_error_is_a_sentence_and_the_question_is_dropped(aiohttp_server, key, tmp_path):
    server = await aiohttp_server(fake_service(status=401))
    assistant = Assistant("idle")
    conv = conversation(setup_for(server), tmp_path, assistant=assistant)
    events = await collect(conv, "hi")
    assert events[-2] == {
        "type": "error",
        "message": "Test AI refused the API key (LAB_TEST_KEY), so chat is paused.",
    }
    assert assistant.state == "error"
    assert conv.messages == [] and not conv.busy
    assert conv.status()["problem"].startswith("Test AI refused")
    await conv.close()


async def test_no_key_pauses_with_a_sentence(tmp_path):
    setup = Setup("main", "https://example.invalid/v1", "m", key_env="LAB_TEST_KEY_UNSET")
    conv = conversation(setup, tmp_path)
    events = await collect(conv, "hi")
    assert events == [
        {
            "type": "error",
            "message": "The AI isn't set up here yet: add LAB_TEST_KEY_UNSET to "
            f"{config.env_file()}, then restart.",
        }
    ]
    assert await conv.check() is False


async def test_the_budget_pauses_the_chat(aiohttp_server, key, tmp_path):
    server = await aiohttp_server(fake_service())
    conv = conversation(setup_for(server), tmp_path, budget=0.0001)
    events = await collect(conv, "first")  # under budget: answered (costs 0.000164)
    assert events[-1]["type"] == "done"
    events = await collect(conv, "second")
    assert events[0]["type"] == "error"
    assert "This month's AI budget ($0.00) is used up" in events[0]["message"]
    assert "Everything else on the hub still works." in events[0]["message"]
    assert conv.status()["paused"]
    await conv.close()


async def test_offline_without_internet(key, tmp_path):
    cloud = Setup("main", "https://example.invalid/v1", "m", key_env="LAB_TEST_KEY")
    assistant = Assistant("idle")
    conv = conversation(cloud, tmp_path, assistant=assistant)
    assert await conv.check(internet=False) is False  # not even tried: it needs internet
    assert assistant.state == "offline"
    await conv.close()


async def test_a_local_setup_needs_no_internet(aiohttp_server, key, tmp_path):
    server = await aiohttp_server(fake_service())  # on 127.0.0.1, like Ollama
    conv = conversation(setup_for(server), tmp_path)
    assert await conv.check(internet=False) is True
    await conv.close()


def test_spend_log_months(tmp_path):
    log = SpendLog(tmp_path, budget_usd=20)
    log.write("main", "m", Usage(10, 10), 0.5)
    log.write("backup", "g", Usage(10, 10), 0.0)
    (tmp_path / f"{datetime.now():%Y-%m}.jsonl").open("a").write('{"half a line')
    m = log.month()
    assert m["spent_usd"] == 0.5 and m["chats"] == 2 and m["budget_usd"] == 20
    assert m["by_setup"] == {"main": 0.5, "backup": 0.0}
    assert log.month(datetime(2000, 1, 1))["chats"] == 0  # another month starts at zero
    assert not log.over_budget()


# ---------- the hub: endpoints and page ----------


def make_app(conv, venue=None):
    from lab_os.hub.server import create_brain_app
    from lab_os.robots.fake import FakeArm
    from lab_os.teleop.loop import InputState, TeleopLoop
    from lab_os.venues import Venue

    arm = FakeArm()
    arm.connect()
    venue = venue or Venue("test", ("fake-arm",), True, 0.5)
    return create_brain_app(TeleopLoop(arm=arm, inputs=InputState()), venue, chat=conv)


async def test_chat_endpoints(aiohttp_client, aiohttp_server, key, tmp_path):
    server = await aiohttp_server(fake_service())
    conv = conversation(setup_for(server), tmp_path, budget=20)
    client = await aiohttp_client(make_app(conv))
    resp = await client.post("/api/chat", json={"text": "What's next?"})
    assert resp.headers["Content-Type"].startswith("application/x-ndjson")
    events = [json.loads(line) for line in (await resp.text()).splitlines()]
    assert events[-1]["type"] == "done"
    chat = await (await client.get("/api/chat")).json()
    assert [m["role"] for m in chat["messages"]] == ["user", "assistant"]
    st = await (await client.get("/api/status")).json()
    assert st["ai"]["setup"] == "main" and st["ai"]["connected"] is True
    assert st["assistant"]["state"] == "idle"
    spend = await (await client.get("/api/spend")).json()
    assert spend["available"] and spend["chats"] == 1 and spend["budget_usd"] == 20
    await client.post("/api/chat/clear")
    assert (await (await client.get("/api/chat")).json())["messages"] == []
    assert (await client.post("/api/chat", data="not json")).status == 400


async def test_a_public_venue_hides_spend(aiohttp_client, tmp_path):
    from lab_os.venues import Venue

    conv = conversation(Setup("main", "http://x/v1", "m"), tmp_path)
    venue = Venue("hallway", ("fake-arm",), True, 0.5, public=True)
    client = await aiohttp_client(make_app(conv, venue))
    assert await (await client.get("/api/spend")).json() == {"available": False}


def test_the_page_has_the_chat_parts():
    html = (SRC / "hub" / "web" / "index.html").read_text()
    for part in (
        'id="ask-btn"',
        'id="quick"',
        'placeholder="Ask anything"',
        'id="reply"',
        'id="open-chat"',
        'id="log-chat"',
        'id="ask"',
        'data-detail="spend"',
        'id="errmsg"',
    ):
        assert part in html, part
    js = (SRC / "hub" / "web" / "hub.js").read_text()
    assert "clearChat(); // the next visitor" in js  # the reset clears the conversation
    assert "/api/chat" in js and "/api/spend" in js
