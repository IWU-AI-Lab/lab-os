"""The assistant shows a page on the screens someone names (quick job 124): "open the system
diagram on the Newline", "show AI Spend on desk3 and the Newline". The phone's remote has no
pages of its own, so a question asked there with no screen named shows the page on the brain's
own computer. It works like "Open on…" (`HubDevices.open_on`), from any screen, and only changes
what the screens show. The tool's list of screens is the devices with the hub open now, by device
name (the display names of quick job 132 come later)."""

import json
import logging

from lab_os.hub.hub_devices import DeviceError, HubDevices, Window, clean_name

log = logging.getLogger(__name__)

SHOW = "show_on_screens"
BRAIN = "brain"  # the brain's own computer (its hub windows)
HUB = "hub"  # closes what a screen shows: back to the hub
SENDER = "assistant"
MAX_SCREENS = 8


def tool(views: dict[str, str], names: list[str]) -> dict:
    listed = "; ".join(f"{vid} = {title}" for vid, title in views.items())
    screens = ", ".join(names) or "none now"
    return {
        "type": "function",
        "function": {
            "name": SHOW,
            "description": (
                'Show a page on other screens, the ones the person names ("open the system '
                'diagram on the Newline"). Pages: '
                f"{listed}; {HUB} = close what is open there. Screens with the hub open now: "
                f"{screens}; {BRAIN} = the brain's own computer. With no screen named and no "
                f"open_page tool (a phone's remote), use {BRAIN}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {"type": "string", "enum": [*views, HUB]},
                    "screens": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": f"device names, or {BRAIN}; empty = {BRAIN}",
                    },
                },
                "required": ["page"],
            },
        },
    }


class ScreensDesk:
    """The tool for the hub's chat. `devices()` is the brain's HubDevices."""

    def __init__(self, devices):
        self.devices = devices

    def tools(self, local: bool) -> list[dict]:
        d: HubDevices = self.devices()
        names = sorted({w.key for w in d.windows.values()})
        return [tool(d.modules(), names)]

    async def call(self, name: str, local: bool, arguments: str = "{}") -> tuple[str, list[dict]]:
        if name != SHOW:
            return f"Error: {name} isn't a tool you have here.", []
        try:
            args = json.loads(arguments or "{}")
        except ValueError:
            args = {}
        page = str(args.get("page") or "").strip().lower()
        screens = args.get("screens") or [BRAIN]
        if isinstance(screens, str):
            screens = [screens]
        said = [await self.show(page, str(s)) for s in list(screens)[:MAX_SCREENS]]
        line = " ".join(said)
        log.info("screens: %s", line)
        return json.dumps({"result": line}), []

    def _windows(self, screen: str) -> tuple[str, list[Window]]:
        d: HubDevices = self.devices()
        if screen.strip().lower() in (BRAIN, "the brain"):
            here = sorted((w for w in d.windows.values() if w.here), key=lambda w: w.since)
            return "the brain's computer", d.of(here[0].key) if here else []
        name = clean_name(screen)
        return name, d.of(name)

    async def show(self, page: str, screen: str) -> str:
        """Open `page` on one screen (its first free monitor, else its leftmost). A sentence."""
        d: HubDevices = self.devices()
        titles = d.modules()
        try:
            where, wins = self._windows(screen)
            if not wins:
                raise DeviceError("its hub isn't open")
            if page == HUB:
                for w in wins:
                    if w.showing:
                        await d.close_on(w.key, w.id)
                return f"Back to the hub on {where}."
            if page not in titles:
                raise DeviceError(f"{page!r} isn't a page that opens on a screen")
            target = next((w for w in wins if not w.showing), wins[0])
            if target.showing == page:
                return f"{titles[page]} is already open on {where}."
            r = await d.open_on(page, target.key, window=target.id, sender=SENDER)
            return r.get("message") or f"{titles[page]} is open on {where}."
        except DeviceError as e:
            return f"Error: not on {screen}: {e}."
