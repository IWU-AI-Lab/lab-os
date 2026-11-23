"""The room's layout (quick job 71): which device shows which page, from the place's `room.yaml`.
"Set up the room" (by voice), ⚙ → The Lab → Set Up the Room and `lab-os room` all open each page
on its device, the same way as "Open on…". A device that doesn't have the hub open is skipped and
named. Change the layout by editing the file."""

import json
import logging

from lab_os import config
from lab_os.hub.hub_devices import DeviceError, HubDevices, clean_name

log = logging.getLogger(__name__)

ROOM_FILE = "room.yaml"
CORE = "core"  # the hub itself: nothing opened on it
SET_UP = "set_up_room"
TOOL = {
    "type": "function",
    "function": {
        "name": SET_UP,
        "description": (
            "Set up the room: open each page on its screen, as the room's layout file says "
            "(when someone asks to set up the room or the screens). Then say in one sentence "
            "what opened and which screens were skipped."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}


def load_layout() -> list[tuple[str, str]]:
    """(device, page) pairs in the file's order. ConfigError names a file that can't be read."""
    layout = config.load_yaml(ROOM_FILE).get("layout") or {}
    if not isinstance(layout, dict):
        raise config.ConfigError(f"{ROOM_FILE}: `layout:` must hold `device: page` lines.")
    return [(str(d), str(p or CORE).strip().lower()) for d, p in layout.items()]


async def set_up(devices: HubDevices) -> dict:
    """Open each page of the layout on its device. Returns what opened and what was skipped (why),
    with a sentence for the page and the assistant."""
    try:
        layout = load_layout()
    except config.ConfigError as e:
        return {"ok": False, "opened": [], "skipped": [], "message": str(e)}
    if not layout:
        return {
            "ok": False,
            "opened": [],
            "skipped": [],
            "message": f"The room's layout is empty: add `device: page` lines to {ROOM_FILE}.",
        }
    titles = devices.modules()
    opened, skipped = [], []
    for raw, page in layout:
        try:
            device = clean_name(raw)
            wins = devices.of(device)
            if not wins:
                raise DeviceError("not connected (its hub isn't open)")
            if page == CORE:
                for w in wins:
                    if w.showing:
                        await devices.close_on(device, w.id)
                opened.append({"device": device, "page": CORE, "title": "the core"})
                continue
            if page not in titles:
                raise DeviceError(f"{page!r} isn't a page that opens on a device")
            first = wins[0]  # its leftmost monitor
            if first.showing != page:
                r = await devices.open_on(page, device, window=first.id, sender="room")
                if not r.get("ok"):
                    raise DeviceError(r.get("message") or "it didn't open")
            opened.append({"device": device, "page": page, "title": titles[page]})
        except DeviceError as e:
            skipped.append({"device": str(raw), "page": page, "why": str(e)})
    message = room_sentence(opened, skipped)
    log.info("room: %s", message)
    return {"ok": bool(opened), "opened": opened, "skipped": skipped, "message": message}


def room_sentence(opened: list[dict], skipped: list[dict]) -> str:
    done = "; ".join(f"{o['title']} on {o['device']}" for o in opened) or "nothing"
    out = f"Set up the room: {done}."
    if skipped:
        out += " Skipped: " + "; ".join(f"{s['device']} ({s['why']})" for s in skipped) + "."
    return out


class RoomDesk:
    """The assistant's tool for it ("set up the room"), from any screen: it only
    changes what the screens show."""

    def __init__(self, devices):
        self.devices = devices  # a callable: the brain's HubDevices

    def tools(self, local: bool) -> list[dict]:
        return [TOOL]

    async def call(self, name: str, local: bool, arguments: str = "{}") -> tuple[str, list[dict]]:
        if name != SET_UP:
            return f"Error: {name} isn't a tool you have here.", []
        r = await set_up(self.devices())
        return json.dumps({"result": r["message"]}), []
