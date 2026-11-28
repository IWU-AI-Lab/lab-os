"""The rest of the system as MCP tools (quick job 80): each action a button on a hub page does,
for Claude Code, Codex and the hub's assistant with Full Access on.

Each tool calls the same function as its button (`lab_os.hub.server`: `change_setting`,
`stop_brain`, `visitor_mode`, `quest_view_start`, …; `HubDevices.open_on` and `close_on`; the
room's `set_up`; the teleop server's `handle_message` for the speed and the mode), so a check
the button has, the tool has too. Nothing new for safety: the wave goes through the robot tools
like every move (STOP, the soft limits, the floor, one controller at a time). They run in the
brain's own process, as the brain's own computer, like a button pressed on its screen.
"""

import asyncio
import logging

from aiohttp import web
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

log = logging.getLogger(__name__)

READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
# changes what the system does or shows; nothing moves
ACT = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)
# stops the brain (the arms go limp)
STOPS = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=False)
MOVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True)
ASKER = "an AI tool (MCP)"


def _out(status_and_answer) -> dict:
    """A button's (HTTP status, answer) as a tool's result: an error is a ToolError."""
    status, out = status_and_answer
    if status >= 400 or out.get("ok") is False:
        raise ToolError(out.get("message") or f"didn't work (HTTP {status})")
    return out


def add_system_tools(server: MCPServer, app: web.Application) -> None:
    from lab_os import settings
    from lab_os.hub import server as hub  # the buttons' own functions (imported late: a cycle)
    from lab_os.hub.hub_devices import DeviceError
    from lab_os.hub.room import set_up
    from lab_os.teleop.server import handle_message

    # ---------- the screens: open or close a module, set up the room ----------

    @server.tool(annotations=READ)
    def hub_screens() -> dict:
        """The devices with the hub open now: each device, its windows (monitors) and what each
        shows; the pages that can open on a device ("views"). For open_on_device."""
        views = {vid: title for vid, (title, _) in hub.DEVICE_VIEWS.items()}
        devices = app[hub.HUB_DEVICES]
        return {"devices": devices.listing(), "sent": devices.sent(), "views": views}

    @server.tool(annotations=ACT)
    async def open_on_device(view: str, device: str, window: str | None = None) -> dict:
        """Open a page on a device's screen, like "Open on…" (`view`: an id from hub_screens'
        views, e.g. monitor, teleop, spend, system; `device`: a device name, e.g. newline, or
        its display name, e.g. "The Newline").
        When the device has several free monitors it asks which: then call again with
        `window`."""
        try:
            return await app[hub.HUB_DEVICES].open_on(
                view, device, window=window or "", sender="ai"
            )
        except DeviceError as e:
            raise ToolError(str(e)) from None

    @server.tool(annotations=ACT)
    async def bring_back(device: str, window: str) -> dict:
        """Close the module on a device's window (window: from hub_screens)."""
        try:
            return await app[hub.HUB_DEVICES].close_on(device, window)
        except DeviceError as e:
            raise ToolError(str(e)) from None

    @server.tool(annotations=ACT)
    async def set_up_the_room() -> dict:
        """Open each page of the room's layout (room.yaml) on its device, like ⚙ → Set Up the
        Room. A device without the hub open is skipped and named."""
        return await set_up(app[hub.HUB_DEVICES])

    # ---------- settings ----------

    @server.tool(annotations=READ)
    async def list_settings() -> dict:
        """Every setting of ⚙ (not "This device"): its key, label, kind, choices and value now,
        and what waits for a restart."""
        brain = app[hub.BRAIN]
        sections = await asyncio.to_thread(settings.read, brain.venue.name)
        fields = [
            {k: f[k] for k in ("key", "label", "kind", "choices", "min", "max", "unit", "value")}
            | {"group": s["title"], "applies": f["applies"]}
            for s in sections
            for f in s["fields"]
        ]
        return {"settings": fields, "restart_needed": list(brain.restart_needed.values())}

    @server.tool(annotations=ACT)
    async def change_setting(key: str, value: bool | int | float | str | list[str]) -> dict:
        """Change one setting, like ⚙ (key and the values it takes: list_settings). A setting
        that applies on a restart says so ("restart_needed"); restart_lab_os then applies it."""
        return _out(await hub.change_setting(app, key, value, by=ASKER))

    @server.tool(annotations=ACT)
    async def change_device_setting(device: str, key: str, value: bool | int | str) -> dict:
        """Change one of a device's own settings, like ⚙ → This Device on that device (e.g.
        `voice`: push-to-talk, dictation or wake word; `wake_sensitivity` 1-9; `sound`;
        `quality`; `display_name`: the name people read, e.g. "Windows desktop 3"). Every window
        of that device gets it at once."""
        return _out(await hub.device_settings(app, device, {key: value}))

    # ---------- the brain ----------

    @server.tool(annotations=STOPS)
    async def restart_lab_os() -> dict:
        """Restart lab-os, like ⚙ → Restart Now: stop any move, let go of the arms (an SO-101
        goes limp: if it's lifted, it drops), and start again with the same options. Every page
        comes back by itself. This connection ends too."""
        return await hub.stop_brain(app, restart=True, asker=ASKER)

    @server.tool(annotations=STOPS)
    async def shut_down_lab_os() -> dict:
        """Shut lab-os down, like ⚙ → Shut Down: stop any move, let go of the arms (an SO-101
        goes limp: if it's lifted, it drops), tell every page it's off. It doesn't start again
        by itself."""
        return await hub.stop_brain(app, restart=False, asker=ASKER)

    # ---------- visitor mode, the Quest's view, the voice ----------

    @server.tool(annotations=ACT)
    async def visitor_mode(on: bool) -> dict:
        """Visitor mode on (the visit-day venue: its cards, Settings and the AI spend hidden) or
        off (back to the venue the brain started in), like ⚙ → Visitor Mode."""
        return _out(await hub.visitor_mode(app, on))

    @server.tool(annotations=ACT)
    async def quest_view(on: bool, headset: str | None = None) -> dict:
        """Show what the Quest sees in a window on the brain's computer (scrcpy), or close it,
        like the strip's Quest view button. `headset`: which one, when several are plugged in."""
        if not on:
            return await hub.quest_view_stop(app)
        return _out(await hub.quest_view_start(app, headset))

    @server.tool(annotations=ACT)
    async def say_aloud(text: str, device: str | None = None) -> dict:
        """Say a sentence aloud with the assistant's voice, on a screen with the hub open (its
        speakers): `device` names it, else the brain's own screen."""
        said = await app[hub.BRAIN].voice.say_text(text, device)
        if said.startswith("Error: "):
            raise ToolError(said[len("Error: ") :])
        return {"ok": True, "message": said}

    # ---------- teleop ----------

    @server.tool(annotations=ACT)
    def teleop_speed(speed_scale: float) -> dict:
        """Arm Control's speed, like the slider on the Arm Control page: 0.05 up to the
        venue's top speed (both arms)."""
        try:
            handle_message(app, {"type": "set_speed", "speed_scale": float(speed_scale)})
        except ValueError as e:
            raise ToolError(str(e)) from None
        return {"ok": True, "speed_scale": app[hub.LOOP].speed_scale}

    @server.tool(annotations=ACT)
    def teleop_mode(mode: str) -> dict:
        """Arm Control's hand → arm mode, like the Arm Control page's choice: "relative" (the
        hand's moves move the arm) or "one_to_one" (1:1: the arm follows the hand, where the venue
        allows it). A change drops the clutch: the person grips again to move."""
        try:
            handle_message(app, {"type": "set_mode", "mode": str(mode)})
        except ValueError as e:
            raise ToolError(str(e)) from None
        loop = app[hub.LOOP]
        return {"ok": True, "mode": loop.mapper.config.mode, "modes": loop.modes()}

    @server.tool(annotations=MOVE)
    async def wave_arm() -> dict:
        """The arm's fixed, gentle wave, like visitor mode's "Ask me to wave" card. Through the
        robot tools' checks; STOP ends it."""
        try:
            await hub._wave(app)
        except ValueError as e:
            raise ToolError(str(e)) from None
        return {"ok": True, "message": "Waving now."}

    # ---------- the Training page ----------

    @server.tool(annotations=ACT)
    async def training_lelab(on: bool) -> dict:
        """The Training page's LeLab (the green arms' training setup): on = check the green
        ports again, then start LeLab in a terminal on the brain's computer; off = stop the LeLab
        that was started so. It refuses while lab-os or another program has a green port."""
        return await (hub.green_start() if on else hub.green_stop())

    @server.tool(annotations=ACT)
    async def training_lerobot_teleop(on: bool) -> dict:
        """The Training page's LeRobot Control (the green leader drives the green follower, with
        the Rerun view): start after its checks, or stop."""
        return await (hub.lerobot_start(app) if on else hub.lerobot_stop(app))
