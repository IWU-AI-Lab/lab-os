"""Keeping the hub's conversation for a while: an accidental reset or a restart doesn't lose it,
and it's gone after the place's chat_keep_minutes. No internet: a fake OpenAI-style service."""

from pathlib import Path

import pytest
from test_chat import fake_service, make_app, setup_for  # same folder (pytest puts it on the path)

from lab_os import config
from lab_os.ai.assistant import Assistant
from lab_os.ai.chat import Conversation
from lab_os.ai.history import ChatStore
from lab_os.ai.spend import SpendLog
from lab_os.hub.server import _chat_store

REPO = Path(__file__).resolve().parents[1]
Q = [{"role": "assistant", "content": "Good evening."}, {"role": "user", "content": "hi"}]


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("LAB_TEST_KEY", "test-key")


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


def test_saved_then_gone_after_the_keep_time(tmp_path):
    clock = Clock()
    store = ChatStore(tmp_path, keep_minutes=30, clock=clock)
    store.save(Q)
    assert store.load() == Q
    clock.t += 30 * 60 + 1
    assert store.load() == []
    assert not (tmp_path / "current.json").exists()  # deleted, not only hidden


def test_put_aside_needs_a_question(tmp_path):
    store = ChatStore(tmp_path)
    store.put_aside([{"role": "assistant", "content": "Good evening."}])
    assert store.previous() is None  # a greeting alone never replaces a kept conversation
    store.put_aside(Q)
    assert store.previous()["questions"] == 1
    assert store.take_previous() == Q and store.previous() is None


def test_a_broken_file_is_dropped(tmp_path, caplog):
    tmp_path.joinpath("current.json").write_text("{not json")
    assert ChatStore(tmp_path).load() == []
    assert "unreadable" in caplog.text


def conv_with(store, setup=None):
    return Conversation(
        Assistant(),
        SpendLog(store.folder / "spend"),
        setups=(lambda: {"main": setup}) if setup else (lambda: {}),
        store=store,
    )


async def test_reset_then_bring_back_then_restart(aiohttp_server, key, tmp_path):
    server = await aiohttp_server(fake_service())
    store = ChatStore(tmp_path)
    conv = conv_with(store, setup_for(server))
    conv.clear(opening="Good evening.")
    _ = [e async for e in conv.ask("What's next?")]
    asked = list(conv.messages)
    assert [m["role"] for m in asked] == ["assistant", "user", "assistant"]

    conv.clear()  # the reset (by accident)
    conv.clear(opening="Good evening.")  # and the next start press: the kept one stays
    assert conv.previous()["questions"] == 1
    assert conv.restore() and conv.messages == asked
    assert conv.previous() is None  # the greeting-only one wasn't worth keeping

    restarted = conv_with(ChatStore(tmp_path), setup_for(server))  # the brain restarts
    assert restarted.messages == asked
    restarted.clear(opening="Good morning.")  # start press after the restart
    assert restarted.restore() and restarted.messages == asked
    await conv.close()


def test_bring_back_twice_swaps_back(tmp_path):
    store = ChatStore(tmp_path)
    conv = conv_with(store)
    conv.messages = [{"role": "user", "content": "new"}]
    store.put_aside(Q)
    assert conv.restore() and conv.messages == Q
    assert conv.restore() and conv.messages == [{"role": "user", "content": "new"}]
    assert conv_with(ChatStore(tmp_path / "empty")).restore() is False


def test_keep_minutes_from_the_place_and_zero_keeps_nothing(tmp_path, monkeypatch):
    assert config.load_place().chat_keep_minutes == 30
    monkeypatch.setattr(config, "logs_dir", lambda: tmp_path)
    ChatStore().save(Q)
    place = config.Place(name="X", chat_keep_minutes=0)
    assert _chat_store(place) is None
    assert not (tmp_path / "chat" / "current.json").exists()  # switched off: old files go too
    assert _chat_store(config.Place(name="X", chat_keep_minutes=5)).keep_s == 300


async def test_the_endpoints(aiohttp_client, tmp_path):
    store = ChatStore(tmp_path)
    store.put_aside(Q)
    client = await aiohttp_client(make_app(conv_with(store)))
    chat = await (await client.get("/api/chat")).json()
    assert chat["previous"]["questions"] == 1
    back = await (await client.post("/api/chat/restore")).json()
    assert back["ok"] and back["messages"] == Q and back["previous"] is None
    again = await (await client.post("/api/chat/restore")).json()
    assert again["ok"] is False


def test_the_page_can_bring_it_back():
    js = (REPO / "src" / "lab_os" / "hub" / "web" / "hub.js").read_text()
    html = (REPO / "src" / "lab_os" / "hub" / "web" / "index.html").read_text()
    assert "/api/chat/restore" in js and 'id="restore-chat"' in html
