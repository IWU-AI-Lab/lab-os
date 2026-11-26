"""The Command Center (quick job 134, spec: docs/design/command-center.md): a page on the brain's
own computer that shows every connected device and screen in one 2D workspace.

The page reads the lists that already exist (the hub's devices and their windows, the live device
list) and changes the real devices through the endpoints that already exist (Open on…, back to the
hub, each device's settings). Two things are its own:

- **The workspace's layout**: where each item sits, which items are hidden, and which screens a
  person grouped under another device. It is only the picture in the workspace: it never changes a
  real device. Kept in the place's `local/command-center.yaml` (not in git).
- **The teleop permission**: which devices may drive a real arm (`drive_from` in `place.yaml`, read
  at start before this job). A change applies at once (the brain's set of addresses) and is kept in
  the place's `local/place.yaml`. A device's Teleop or Raspbot page checks it when it connects.

Both endpoints answer only to the brain's own computer: another screen can't give itself the right
to drive an arm.
"""

import asyncio
import logging
import re
import socket
from collections.abc import Callable
from pathlib import Path

import yaml
from aiohttp import web

from lab_os import config, settings
from lab_os.activity import ACTIVITY
from lab_os.hub.hub_devices import on_this_computer
from lab_os.teleop.server import DRIVE_FROM

log = logging.getLogger(__name__)

FILE_NAME = "command-center.yaml"
KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:#-]{0,120}$")  # an item of the workspace
MAX_ITEMS = 400
LIMIT = 100_000  # a place in the workspace, in its own units
ADDRESS = re.compile(r"^[0-9A-Fa-f.:]{2,45}$")


def layout_file() -> Path:
    return config.local_dir() / FILE_NAME


class LayoutStore:
    """The workspace's layout: `places` (item → [x, y]), `hidden` (items), `groups` (a screen →
    the device it was grouped under). Read and written whole; a broken file starts empty."""

    def __init__(self, path: Callable[[], Path] | None = None):
        self._path = path or layout_file

    def read(self) -> dict:
        p = self._path()
        try:
            raw = yaml.safe_load(p.read_text()) if p.is_file() else None
        except (OSError, yaml.YAMLError) as e:
            log.warning("%s: %s; starting from an empty workspace", p, e)
            raw = None
        return clean_layout(raw if isinstance(raw, dict) else {})

    def write(self, layout: dict) -> dict:
        layout = clean_layout(layout)
        p = self._path()
        head = (
            "# The Command Center's workspace (quick job 134): where each item sits, what is\n"
            "# hidden and which screens are grouped under another device. Only the picture: it\n"
            "# changes no device. Written by the Command Center; delete this file to start again.\n"
        )
        tmp = p.with_suffix(".tmp")
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(head + yaml.safe_dump(layout, sort_keys=True, allow_unicode=True))
        tmp.replace(p)
        return layout


def clean_layout(raw: dict) -> dict:
    """Only what the layout may hold: valid item keys, places as two numbers in range."""
    places = {}
    for k, v in (raw.get("places") or {}).items() if isinstance(raw.get("places"), dict) else ():
        if KEY.match(str(k)) and isinstance(v, (list, tuple)) and len(v) == 2:
            try:
                x, y = (max(-LIMIT, min(LIMIT, round(float(n), 1))) for n in v)
            except (TypeError, ValueError):
                continue
            places[str(k)] = [x, y]
    hidden = raw.get("hidden") if isinstance(raw.get("hidden"), list) else []
    groups = raw.get("groups") if isinstance(raw.get("groups"), dict) else {}
    return {
        "places": dict(list(places.items())[:MAX_ITEMS]),
        "hidden": sorted({str(k) for k in hidden if KEY.match(str(k))})[:MAX_ITEMS],
        "groups": {
            str(k): str(v)
            for k, v in list(groups.items())[:MAX_ITEMS]
            if KEY.match(str(k)) and KEY.match(str(v))
        },
    }


# ---------- the teleop permission ----------
def _resolve(name: str) -> str:
    try:
        return socket.gethostbyname(name)
    except OSError:
        return ""


def place_drive_from() -> list[str]:
    """place.yaml's `drive_from` as it is now (every layer), names or addresses."""
    try:
        return list(config.load_place().drive_from)
    except (config.ConfigError, OSError):
        return []


def set_drive_from(app: web.Application, address: str, allowed: bool) -> list[str]:
    """Let the device at `address` drive a real arm, or not: at once (the brain's set) and kept
    (local/place.yaml). A name in place.yaml that stands for this address goes too. Returns the
    addresses that may drive now."""
    now: set = app[DRIVE_FROM]
    listed = place_drive_from()
    if allowed:
        now.add(address)
        keep = listed if address in listed else [*listed, address]
    else:
        now.discard(address)
        keep = [n for n in listed if n != address and _resolve(n) != address]
    if keep != listed:
        settings.write_value("place", "drive_from", keep, flow=True)
    log.info("command center: %s %s drive a real arm", address, "may" if allowed else "may not")
    return sorted(now)


# ---------- the endpoints ----------
STORE = web.AppKey("command_center_layout", LayoutStore)


def _brain_only(request: web.Request) -> web.Response | None:
    if on_this_computer(request):
        return None
    return web.json_response(
        {"ok": False, "message": "The Command Center works only on the brain's own computer."},
        status=403,
    )


async def api_state(request: web.Request) -> web.Response:
    """The layout and the addresses that may drive now."""
    if (no := _brain_only(request)) is not None:
        return no
    layout = await asyncio.to_thread(request.app[STORE].read)
    return web.json_response({"layout": layout, "drive_from": sorted(request.app[DRIVE_FROM])})


async def api_layout(request: web.Request) -> web.Response:
    if (no := _brain_only(request)) is not None:
        return no
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(text="send a JSON object")
    try:
        layout = await asyncio.to_thread(request.app[STORE].write, body)
    except OSError as e:
        return web.json_response({"ok": False, "message": f"Couldn't save: {e}"}, status=500)
    return web.json_response({"ok": True, "layout": layout})


async def api_drive(request: web.Request) -> web.Response:
    """{"addresses": [...], "allowed": bool}: those devices may (or may not) drive a real arm."""
    if (no := _brain_only(request)) is not None:
        return no
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict) or not isinstance(body.get("allowed"), bool):
        raise web.HTTPBadRequest(text='send {"addresses": [...], "allowed": true or false}')
    addresses = [str(a) for a in body.get("addresses") or [] if ADDRESS.match(str(a))]
    if not addresses:
        return web.json_response({"ok": False, "message": "No device address."}, status=400)
    try:
        for a in addresses:
            now = await asyncio.to_thread(set_drive_from, request.app, a, body["allowed"])
    except (config.ConfigError, OSError) as e:
        return web.json_response({"ok": False, "message": f"Couldn't save: {e}"}, status=500)
    return web.json_response({"ok": True, "drive_from": now})


async def api_activity(request: web.Request) -> web.Response:
    """The activity list (quick job 149): the newest events first."""
    if (no := _brain_only(request)) is not None:
        return no
    events = request.app[ACTIVITY].recent() if ACTIVITY in request.app else []
    return web.json_response({"events": events})


def add_routes(app: web.Application, store: LayoutStore | None = None) -> None:
    app[STORE] = store or LayoutStore()
    app.router.add_get("/api/command-center", api_state)
    app.router.add_get("/api/command-center/activity", api_activity)
    app.router.add_post("/api/command-center/layout", api_layout)
    app.router.add_post("/api/command-center/drive", api_drive)
