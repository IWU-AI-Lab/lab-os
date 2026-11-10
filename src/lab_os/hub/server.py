"""The brain's web server (`lab-os serve`): the hub page, with the teleop pages inside it.

GET /                    the hub: start screen, status strip, module buttons, assistant, panels
GET /perf                performance test page (drifting dots, links, star streaks + frames/s)
GET /hub/...             the hub's own files (src/lab_os/hub/web/)
GET /api/status          venue, internet, AI, assistant state, the brain's clock, what's in use
GET /api/project         the Current Project panel (docs/current-focus.md → Steps)
GET /api/commits?days=N  commits per day for the last N days
GET /api/hub             the module buttons (hub.modules that have a page) and the reset time
Everything else is the teleop server's: /teleop, /monitor, /ws, /static, /web, /models, /theme.json.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from aiohttp import web

from lab_os import REPO_ROOT
from lab_os.hub.commits import commits_per_day
from lab_os.hub.internet import InternetCheck
from lab_os.hub.project import FOCUS_FILE, project_summary
from lab_os.teleop.loop import TeleopLoop
from lab_os.teleop.server import CONTROL, LOOP, create_app
from lab_os.theme import load_theme
from lab_os.venues import Venue

HUB_WEB_DIR = Path(__file__).parent / "web"

# Every module the hub knows: id → (button title, page). The theme's hub.modules picks which ones
# get a button and in what order; ids without a page here get no button (only claim what's real).
MODULES = {"teleop": ("Teleop", "/teleop"), "monitor": ("Monitor", "/monitor")}

ASSISTANT_STATES = ("idle", "listening", "thinking", "speaking", "offline", "error")
DEFAULT_RESET_AFTER_S = 180.0
MAX_COMMIT_DAYS = 90

log = logging.getLogger(__name__)


@dataclass
class Assistant:
    """The assistant's state (the information layer). The rest of the system sets it; the
    picture on the page only reads it. Offline until an AI is connected (focus step 5)."""

    state: str = "offline"
    loudness: float = 0.0  # 0–1 while speaking

    def set(self, state: str, loudness: float = 0.0) -> None:
        if state not in ASSISTANT_STATES:
            raise ValueError(f"unknown assistant state {state!r}")
        self.state, self.loudness = state, max(0.0, min(1.0, loudness))


@dataclass
class Brain:
    venue: Venue
    internet: InternetCheck | None  # None = don't check (tests)
    assistant: Assistant
    focus_file: Path
    repo: Path


BRAIN = web.AppKey("brain", Brain)


def hub_modules(theme: dict) -> list[dict]:
    """The buttons, in hub.modules order. Unknown ids are skipped (and logged)."""
    out = []
    for mid in (theme.get("hub") or {}).get("modules") or []:
        if mid in MODULES:
            title, page = MODULES[mid]
            out.append({"id": mid, "title": title, "page": page})
        else:
            log.info("hub.modules: %r has no page yet, so no button", mid)
    return out


def reset_after_s(theme: dict, venue: Venue) -> float:
    """The venue's value wins, then the theme's hub.reset_after_s, then 3 minutes."""
    if venue.reset_after_s:
        return venue.reset_after_s
    return float((theme.get("hub") or {}).get("reset_after_s") or DEFAULT_RESET_AFTER_S)


def in_use(app: web.Application) -> list[str]:
    """What's in use right now; the hub never goes back to the start screen while this isn't
    empty: teleop has the arm, the AI tools are moving it. Later: a voice turn runs."""
    used = []
    if app[CONTROL].get("ws") is not None:
        used.append("teleop")
    if app[LOOP].motion_active:
        used.append("ai")
    return used


async def _file(request: web.Request, name: str) -> web.FileResponse:
    return web.FileResponse(HUB_WEB_DIR / name)


async def hub_page(request: web.Request) -> web.FileResponse:
    return await _file(request, "index.html")


async def perf_page(request: web.Request) -> web.FileResponse:
    return await _file(request, "perf.html")


async def api_status(request: web.Request) -> web.Response:
    app = request.app
    brain = app[BRAIN]
    loop: TeleopLoop = app[LOOP]
    return web.json_response(
        {
            "venue": brain.venue.name,
            "internet": brain.internet.online if brain.internet else None,  # None = not known
            "ai": {"connected": False},
            "assistant": {"state": brain.assistant.state, "loudness": brain.assistant.loudness},
            "arm": {
                "name": loop.arm.name,
                "control": "ai"
                if loop.motion_active
                else "taken"
                if app[CONTROL].get("ws") is not None
                else "free",
            },
            "in_use": in_use(app),
            "time_ms": int(time.time() * 1000),
        }
    )


async def api_project(request: web.Request) -> web.Response:
    return web.json_response(project_summary(request.app[BRAIN].focus_file))


async def api_commits(request: web.Request) -> web.Response:
    try:
        days = int(request.query.get("days", 14))
    except ValueError:
        raise web.HTTPBadRequest(text="days must be a whole number") from None
    days = max(1, min(MAX_COMMIT_DAYS, days))
    result = await asyncio.to_thread(commits_per_day, days, request.app[BRAIN].repo)
    return web.json_response(result)


async def api_hub(request: web.Request) -> web.Response:
    theme = load_theme()  # re-read each time, like /theme.json: edit, then reload the page
    return web.json_response(
        {
            "modules": hub_modules(theme),
            "reset_after_s": reset_after_s(theme, request.app[BRAIN].venue),
        }
    )


async def _internet_task(app: web.Application):
    check = app[BRAIN].internet
    task = asyncio.create_task(check.run()) if check else None
    yield
    if task:
        task.cancel()


def create_brain_app(
    loop: TeleopLoop,
    venue: Venue,
    internet: InternetCheck | None = None,
    focus_file: Path = FOCUS_FILE,
    repo: Path = REPO_ROOT,
) -> web.Application:
    """The teleop server with the hub on top. Pass an `InternetCheck` to check in the background."""
    app = create_app(loop, root_page=False)
    app[BRAIN] = Brain(venue, internet, Assistant(), focus_file, repo)
    app.router.add_get("/", hub_page)
    app.router.add_get("/perf", perf_page)
    app.router.add_get("/api/status", api_status)
    app.router.add_get("/api/project", api_project)
    app.router.add_get("/api/commits", api_commits)
    app.router.add_get("/api/hub", api_hub)
    app.router.add_static("/hub", HUB_WEB_DIR)
    app.cleanup_ctx.append(_internet_task)
    return app
