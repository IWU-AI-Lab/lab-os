"""Where the sound plays (quick job 166, changed 2026-11-27): each device plays its own sounds;
mute, solo and cover per device; one greeting for every start; the Quest keeps its own sound."""

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
    address_key: str = ""  # a page with no name: its address key (quick job 169)

    @property
    def key(self) -> str:  # noqa: F811 (as VoiceLink.key: its name, else its address key)
        return self.device or self.address_key


def link(device="", local=False, own=False, since=0.0, address=""):
    return Page(device, local, own, since, address)


def desk(links, sounds=None):
    d = VoiceDesk(
        chat=None,
        assistant=None,
        persona=lambda: None,
        sound_settings=lambda: sounds or {},
    )
    d.links = set(links)
    return d


def test_an_answer_plays_where_it_was_asked_unless_muted():
    phone = link("phone")
    d = desk([phone, link("newline")])
    assert d.outputs(phone) == [phone]
    d = desk([phone], {"phone": {"sound": False}})
    assert d.outputs(phone) == []


def test_solo_silences_the_other_devices():
    phone, nl, desk1 = link("phone"), link("newline"), link("desk")
    d = desk([phone, nl, desk1], {"newline": {"solo": True}})
    assert d.outputs(nl) == [nl]  # its own sound
    assert d.outputs(phone) == [] and d.outputs(desk1) == []  # not sent to the soloed device
    d = desk([phone, nl, desk1], {"newline": {"solo": True}, "desk": {"solo": True}})
    assert d.outputs(nl) == [nl] and d.outputs(desk1) == [desk1] and d.outputs(phone) == []
    d = desk([phone, nl, desk1], {"newline": {"solo": True, "sound": False}})
    assert d.outputs(nl) == [] and d.outputs(phone) == []  # M + S, no cover: quiet everywhere


def test_a_cover_plays_the_soloed_devices_sounds():
    phone, nl1, nl2, desk1 = (
        link("phone"),
        link("newline", since=1),
        link("newline", since=2),
        link("desk"),
    )
    d = desk([phone, nl1, nl2, desk1], {"newline": {"cover": True}})
    assert d.outputs(phone) == [phone] and d.outputs(desk1) == [desk1]  # no solo: own sound
    assert d.outputs(nl1) == [nl1]
    d = desk([phone, nl1, nl2, desk1], {"phone": {"solo": True}, "newline": {"cover": True}})
    assert d.outputs(phone) == [phone, nl1]  # the cover's oldest page only: one set of speakers
    assert d.outputs(nl1) == [] and d.outputs(desk1) == []  # its own sound is quiet
    sounds = {"phone": {"solo": True}, "newline": {"cover": True}, "desk": {"cover": True}}
    d = desk([phone, nl1, desk1], sounds)
    assert set(d.outputs(phone)) == {phone, nl1, desk1}  # a few covers
    sounds = {"phone": {"solo": True}, "newline": {"cover": True, "solo": True}}
    d = desk([phone, nl1], sounds)
    assert d.outputs(nl1) == [nl1] and d.outputs(phone) == [phone, nl1]  # soloed and a cover
    sounds = {"phone": {"solo": True}, "newline": {"cover": True, "sound": False}}
    d = desk([phone, nl1], sounds)
    assert d.outputs(phone) == [phone]  # a muted cover plays nothing


def test_mute_and_solo_play_only_on_the_covers():
    """M + S: the device's sounds play on the covers, not on the device itself."""
    pi, phone, nl, desk1 = link("pi03"), link("phone"), link("newline"), link("desk")
    sounds = {
        "pi03": {"sound": False, "solo": True},
        "phone": {"sound": False, "solo": True},
        "newline": {"cover": True},
    }
    d = desk([pi, phone, nl, desk1], sounds)
    assert d.outputs(pi) == [nl] and d.outputs(phone) == [nl]
    assert d.outputs(desk1) == [] and d.outputs(nl) == []  # the others are quiet
    assert {lk.key for lk in d.soloed()} == {"pi03", "phone"}


def test_mute_is_a_full_mute():
    phone, nl = link("phone"), link("newline")
    d = desk([phone, nl], {"phone": {"sound": False}, "newline": {"cover": True}})
    assert d.outputs(phone) == []


def test_the_quest_keeps_its_own_sound():
    quest, nl = link("quest", own=True), link("newline")
    d = desk([quest, nl], {"newline": {"solo": True}, "quest": {"sound": False, "solo": True}})
    assert d.outputs(quest) == [quest]
    assert d.soloed() == [nl]  # its solo doesn't count for the others
    d = desk([quest, nl], {"newline": {"solo": True}, "quest": {"cover": True}})
    assert d.outputs(nl) == [nl]  # and it is never a cover


def test_each_window_plays_its_own_sound():
    """Two windows on one computer: the one that started speaks, not the one open longest."""
    old, new, pi = link("desk", local=True, since=1), link("desk", local=True, since=2), link("pi")
    d = desk([old, new, pi])
    assert d.outputs(new) == [new] and d.outputs(old) == [old] and d.outputs(pi) == [pi]


async def connect(client, name):
    return await client.ws_connect(f"/ws/voice?device={name}")


async def settings(client, name, body):
    r = await client.post(f"/api/hub-devices/{name}/settings", json=body)
    assert r.status == 200, await r.text()


@pytest.mark.usefixtures("key")
async def test_a_soloed_phones_answer_plays_on_the_cover(aiohttp_client, aiohttp_server, tmp_path):
    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    await settings(client, "newline", {"cover": True})
    await settings(client, "phone", {"solo": True})
    newline = await connect(client, "newline")
    phone = await connect(client, "phone")
    await phone.send_json({"type": "listen", "mode": "ask"})
    await until(phone, "listening", [])
    await phone.send_bytes(SECOND)
    await phone.send_json({"type": "end"})
    asked = []
    end = await until(phone, "audio_end", asked)
    assert end["count"] == 2 and len([e for e in asked if e["type"] == "audio"]) == 2
    played = []
    end = await until(newline, "audio_end", played)
    kinds = [e["type"] for e in played]
    assert kinds[0] == "audio_begin" and kinds.count("audio") == 2 and end["count"] == 2
    await newline.send_json({"type": "played", "done": True})
    await phone.send_json({"type": "played", "done": True})
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
async def test_one_greeting_on_the_screen_that_started(aiohttp_client, aiohttp_server, tmp_path):
    app, conv, _ = await voice_app(aiohttp_server, tmp_path)
    conv.clear(opening="Good evening.")
    client = await aiohttp_client(app)
    newline = await connect(client, "newline")
    pi = await connect(client, "pi03")
    await pi.send_json({"type": "greet", "way": "none"})
    played = []
    end = await until(pi, "audio_end", played)
    assert end["greeting"] and end["count"] == 1
    assert [e["text"] for e in played if e["type"] == "audio"] == ["Good evening."]
    # another screen of the same start asks too: no second greeting
    await newline.send_json({"type": "greet", "way": "none"})
    events = []
    end = await until(newline, "audio_end", events)
    assert end["count"] == 0 and not [e for e in events if e["type"] == "audio"]
    await pi.send_json({"type": "played", "done": True})
    await asyncio.sleep(0.1)
    for ws in (newline, pi):
        await ws.close()


@pytest.mark.usefixtures("key")
async def test_the_command_center_sees_mute_and_solo(aiohttp_client, aiohttp_server, tmp_path):
    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    await settings(client, "newline", {"sound": False, "solo": True, "cover": True})
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
    assert by["newline"]["cover"] is True
    assert not by["newline"]["own_sound"] and by["quest"]["own_sound"]
    for ws in (quest, hub, qhub):
        await ws.close()


def test_a_page_with_no_name_is_muted_and_soloed_by_its_address():
    """Quick job 169: the key of a page with no name is its address key."""
    laptop, nl = link(address="addr-127-0-0-1"), link("newline")
    d = desk([laptop, nl], {"addr-127-0-0-1": {"sound": False}})
    assert d.outputs(laptop) == []
    d = desk([laptop, nl], {"addr-127-0-0-1": {"solo": True}})
    assert d.outputs(nl) == [] and d.outputs(laptop) == [laptop]
    d = desk([laptop, nl], {"newline": {"solo": True}, "addr-127-0-0-1": {"cover": True}})
    assert d.outputs(nl) == [nl, laptop]


async def test_a_page_with_no_name_keeps_only_its_sound(aiohttp_client, aiohttp_server, tmp_path):
    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    hub = await client.ws_connect("/ws/hub-device")
    welcome = await hub.receive_json()
    name = welcome["key"]
    assert name.startswith("addr-") and welcome["device"] == ""
    r = await client.post(f"/api/hub-devices/{name}/settings", json={"quality": "minimal"})
    assert r.status == 400  # only its sound
    await settings(client, name, {"sound": False})
    while (m := await hub.receive_json())["type"] != "settings":
        pass
    assert m["settings"]["sound"] is False  # the page mutes its own sounds too
    listing = (await (await client.get("/api/hub-devices")).json())["devices"]
    assert listing[0]["name"] == name and listing[0]["sound"] is False
    again = await client.ws_connect("/ws/hub-device")
    assert (await again.receive_json())["settings"] == {"sound": False}
    for ws in (hub, again):
        await ws.close()


def test_changes_at_the_same_time_are_all_kept(tmp_path):
    """The Command Center's Mute all: two changes at once lost one (quick job 166)."""
    from concurrent.futures import ThreadPoolExecutor

    from lab_os.hub.hub_devices import DeviceSettings

    store = DeviceSettings(lambda: tmp_path / "hub-devices.yaml")
    names = [f"pi{i:02d}" for i in range(12)]
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda n: store.update(n, {"sound": False}), names))
    assert all(store.get(n).get("sound") is False for n in names)
