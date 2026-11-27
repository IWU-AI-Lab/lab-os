"""Where the sound plays (quick job 166): mute and solo per device, one greeting for every start
on the first device of `greeting_from`, and the Quest's page with its own sound."""

import asyncio
from dataclasses import dataclass

import pytest
from test_voice import SECOND, key, until, voice_app  # noqa: F401 (key: the fixture, used below)

from lab_os.hub.voice import VoiceDesk


@dataclass(eq=False)
class Page:  # a page's voice connection, as far as the routing looks at it
    device: str = ""
    local: bool = False
    own: bool = False
    since: float = 0.0


def link(device="", local=False, own=False, since=0.0):
    return Page(device, local, own, since)


def desk(links, sounds=None, order=("newline", "brain")):
    d = VoiceDesk(
        chat=None,
        assistant=None,
        persona=lambda: None,
        sound_settings=lambda: sounds or {},
        greeting_from=lambda: list(order),
    )
    d.links = set(links)
    return d


def test_an_answer_plays_where_it_was_asked_unless_muted():
    phone = link("phone")
    d = desk([phone, link("newline")])
    assert d.outputs(phone) == [phone]
    d = desk([phone], {"phone": {"sound": False}})
    assert d.outputs(phone) == []


def test_solo_takes_every_answer_one_page_per_device():
    phone, nl1, nl2, desk1 = (
        link("phone"),
        link("newline", since=1),
        link("newline", since=2),
        link("desk"),
    )
    d = desk([phone, nl1, nl2, desk1], {"newline": {"solo": True}})
    assert d.outputs(phone) == [nl1]  # its oldest page only: one set of speakers
    assert d.outputs(desk1) == [nl1]
    d = desk([phone, nl1, desk1], {"newline": {"solo": True, "sound": False}})
    assert d.outputs(phone) == [phone]  # muted wins over solo
    d = desk([phone, nl1, desk1], {"newline": {"solo": True}, "desk": {"solo": True}})
    assert set(d.outputs(phone)) == {nl1, desk1}  # a few soloed devices


def test_the_quest_keeps_its_own_sound():
    quest, nl = link("quest", own=True), link("newline")
    d = desk([quest, nl], {"newline": {"solo": True}, "quest": {"sound": False, "solo": True}})
    assert d.outputs(quest) == [quest] and d.greeting_outputs(quest) == [quest]
    assert d.soloed() == [nl]  # its solo doesn't count for the others


def test_the_greeting_plays_on_the_first_device_of_the_order():
    pi, nl, brain = link("pi03"), link("newline"), link("desk", local=True)
    d = desk([pi, nl, brain])
    assert d.greeting_outputs(pi) == [nl]
    d = desk([pi, nl, brain], {"newline": {"sound": False}})
    assert d.greeting_outputs(pi) == [brain]  # then the brain's computer
    d = desk([pi, nl, brain], {"newline": {"sound": False}, "desk": {"sound": False}})
    assert d.greeting_outputs(pi) == [pi]  # then the screen that started
    d = desk([pi, nl], {"pi03": {"sound": False}, "newline": {"sound": False}})
    assert d.greeting_outputs(pi) == []  # every screen muted
    d = desk([pi, nl, brain], {"pi03": {"solo": True}})
    assert d.greeting_outputs(nl) == [pi]  # a soloed device wins


async def connect(client, name):
    return await client.ws_connect(f"/ws/voice?device={name}")


async def settings(client, name, body):
    r = await client.post(f"/api/hub-devices/{name}/settings", json=body)
    assert r.status == 200, await r.text()


@pytest.mark.usefixtures("key")
async def test_a_phones_answer_plays_on_the_soloed_device(aiohttp_client, aiohttp_server, tmp_path):
    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    await settings(client, "newline", {"solo": True})
    newline = await connect(client, "newline")
    phone = await connect(client, "phone")
    st = await (await client.get("/api/status")).json()
    assert st["voice"]["solo"] == ["newline"]  # the other screens make no sound
    await phone.send_json({"type": "listen", "mode": "ask"})
    await until(phone, "listening", [])
    await phone.send_bytes(SECOND)
    await phone.send_json({"type": "end"})
    asked = []
    end = await until(phone, "audio_end", asked)
    assert end["count"] == 0 and not [e for e in asked if e["type"] == "audio"]
    assert any(e["type"] == "text" for e in asked)  # the words still show on the phone
    played = []
    end = await until(newline, "audio_end", played)
    kinds = [e["type"] for e in played]
    assert kinds[0] == "audio_begin" and kinds.count("audio") == 2 and end["count"] == 2
    await newline.send_json({"type": "played", "done": True})
    await phone.close()
    await newline.close()


@pytest.mark.usefixtures("key")
async def test_a_muted_screen_gets_no_spoken_answer(aiohttp_client, aiohttp_server, tmp_path):
    seen = []
    app, _, _ = await voice_app(aiohttp_server, tmp_path, seen=seen)
    client = await aiohttp_client(app)
    await settings(client, "phone", {"sound": False})
    phone = await connect(client, "phone")
    await phone.send_json({"type": "listen", "mode": "ask"})
    await until(phone, "listening", [])
    await phone.send_bytes(SECOND)
    await phone.send_json({"type": "end"})
    events = []
    end = await until(phone, "audio_end", events)
    assert end["count"] == 0 and not [e for e in events if e["type"] == "audio"]
    assert not [s for s in seen if "tts" in s]  # nothing spoken, nothing paid
    await phone.close()


@pytest.mark.usefixtures("key")
async def test_one_greeting_for_the_screens_that_start(aiohttp_client, aiohttp_server, tmp_path):
    app, conv, _ = await voice_app(aiohttp_server, tmp_path)
    conv.clear(opening="Good evening.")
    client = await aiohttp_client(app)
    newline = await connect(client, "newline")
    pi = await connect(client, "pi03")  # the card reader's Pi: no speakers
    await pi.send_json({"type": "greet", "way": "none"})
    asked = []
    end = await until(pi, "audio_end", asked)
    assert end["greeting"] and end["count"] == 0 and not [e for e in asked if e["type"] == "audio"]
    played = []
    await until(newline, "audio_end", played)
    assert [e["text"] for e in played if e["type"] == "audio"] == ["Good evening."]
    # another screen of the same start asks too: no second greeting
    desk = await connect(client, "desk")
    await desk.send_json({"type": "greet", "way": "none"})
    events = []
    end = await until(desk, "audio_end", events)
    assert end["count"] == 0 and not [e for e in events if e["type"] == "audio"]
    await asyncio.sleep(0.1)
    for ws in (newline, pi, desk):
        await ws.close()


@pytest.mark.usefixtures("key")
async def test_the_command_center_sees_mute_and_solo(aiohttp_client, aiohttp_server, tmp_path):
    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    await settings(client, "newline", {"sound": False, "solo": True})
    r = await client.post("/api/hub-devices/newline/settings", json={"solo": "yes"})
    assert r.status == 400  # true or false
    quest = await client.ws_connect("/ws/voice?device=quest&own=1")
    hub = await client.ws_connect("/ws/hub-device?device=newline")
    await hub.receive_json()  # welcome
    qhub = await client.ws_connect("/ws/hub-device?device=quest")
    await qhub.receive_json()
    listing = (await (await client.get("/api/hub-devices")).json())["devices"]
    by = {d["name"]: d for d in listing}
    assert by["newline"]["sound"] is False and by["newline"]["solo"] is True
    assert not by["newline"]["own_sound"] and by["quest"]["own_sound"]
    for ws in (quest, hub, qhub):
        await ws.close()


def test_the_greeting_order_is_a_setting():
    from lab_os import settings as st

    f = st.find("place:greeting_from")
    assert f.kind == "list" and f.default == ["newline", "brain"]
    assert f.options()[:2] == ["newline", "brain"]
    assert st.check(f, ["brain", "newline"]) == ["brain", "newline"]


def test_changes_at_the_same_time_are_all_kept(tmp_path):
    """The Command Center's Mute all: two changes at once lost one (quick job 166)."""
    from concurrent.futures import ThreadPoolExecutor

    from lab_os.hub.hub_devices import DeviceSettings

    store = DeviceSettings(lambda: tmp_path / "hub-devices.yaml")
    names = [f"pi{i:02d}" for i in range(12)]
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda n: store.update(n, {"sound": False}), names))
    assert all(store.get(n).get("sound") is False for n in names)
