"""The brain's web server (`lab-os serve`): the hub page, with the teleop pages inside it.

GET /                    the hub: start screen, status strip, module buttons, assistant, panels
GET /perf                performance test page (drifting dots, links, star streaks + frames/s)
GET /hub/...             the hub's own files (src/lab_os/hub/web/)
GET /api/status          venue, internet, AI, assistant state, the brain's clock, what's in use
GET /api/project         the Current Project panel (docs/current-focus.md → Steps)
GET /api/commits?days=N  commits per day for the last N days
GET /api/hub             the place's name (the title), the module buttons (hub.modules that have
                         a page) and the reset time
GET /api/greeting        "Good evening." + one line of real news, else the persona's line
POST /api/chat/start     start a fresh conversation with the greeting (the start press)
GET /api/chat            the conversation so far and the chat's status
POST /api/chat           {"text": "..."} → one turn, streamed as JSON lines (docs/protocol.md)
POST /api/chat/clear     forget the conversation (the hub's reset)
GET /api/spend           this month's AI spend and budget (hidden on a public venue)
Everything else is the teleop server's: /teleop, /monitor, /ws, /static, /web, /models, /theme.json.
The robot tools for AI tools run as an MCP server on their own port (lab_os.tools.mcp_server).
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aiohttp import web

from lab_os import REPO_ROOT, config
from lab_os.ai.assistant import ASSISTANT_STATES, Assistant  # noqa: F401 (used by tests)
from lab_os.ai.chat import Conversation
from lab_os.ai.spend import SpendLog
from lab_os.ai.tools import ChatTools
from lab_os.hub.commits import commits_per_day
from lab_os.hub.greeting import greeting
from lab_os.hub.internet import InternetCheck
from lab_os.hub.project import FOCUS_FILE, project_summary
from lab_os.personas import Persona, persona_for_venue
from lab_os.teleop.loop import TeleopLoop
from lab_os.teleop.server import CONTROL, LOOP, create_app
from lab_os.theme import load_theme
from lab_os.tools.calllog import CallLog
from lab_os.tools.mcp_server import McpHttp, create_mcp_server
from lab_os.tools.project import ProjectTools
from lab_os.tools.robot import RobotTools
from lab_os.venues import Venue

HUB_WEB_DIR = Path(__file__).parent / "web"

# Every module the hub knows: id → (button title, page). The theme's hub.modules picks which ones
# get a button and in what order; ids without a page here get no button (only claim what's real).
MODULES = {"teleop": ("Teleop", "/teleop"), "monitor": ("Monitor", "/monitor")}

DEFAULT_RESET_AFTER_S = 180.0
MAX_COMMIT_DAYS = 90
MAX_QUESTION_CHARS = 2000
AI_CHECK_EVERY_S = (60.0, 20.0)  # while connected / while not

log = logging.getLogger(__name__)


@dataclass
class Brain:
    place: config.Place
    venue: Venue
    internet: InternetCheck | None  # None = don't check (tests)
    assistant: Assistant
    focus_file: Path
    repo: Path
    chat: Conversation
    persona: Callable[[], Persona]  # the venue's persona, re-read each time (edit + reload)
    check_ai: bool = False  # check the AI service in the background (off in tests)


BRAIN = web.AppKey("brain", Brain)
TOOLS = web.AppKey("tools", RobotTools)
MCP = web.AppKey("mcp", McpHttp | None)


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
    if app[BRAIN].chat.busy:
        used.append("chat")
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
            "persona": brain.persona().public(),
            "internet": brain.internet.online if brain.internet else None,  # None = not known
            "ai": brain.chat.status(),
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
            "title": request.app[BRAIN].place.name,
            "modules": hub_modules(theme),
            "reset_after_s": reset_after_s(theme, request.app[BRAIN].venue),
        }
    )


def _greeting(brain: Brain) -> dict:
    line = brain.persona().lines.get("greeting", "")
    return greeting(line, brain.focus_file, brain.repo, list(brain.place.calendar))


async def api_greeting(request: web.Request) -> web.Response:
    return web.json_response(await asyncio.to_thread(_greeting, request.app[BRAIN]))


async def api_chat_start(request: web.Request) -> web.Response:
    """The start press: a fresh conversation whose first message is the greeting."""
    brain = request.app[BRAIN]
    hello = await asyncio.to_thread(_greeting, brain)
    brain.chat.clear(opening=hello["text"])
    return web.json_response(hello)


async def api_chat_get(request: web.Request) -> web.Response:
    chat = request.app[BRAIN].chat
    return web.json_response({"messages": chat.messages, "status": chat.status()})


async def api_chat_post(request: web.Request) -> web.StreamResponse:
    """One turn, streamed as JSON lines: state / text / done / error events."""
    try:
        text = str((await request.json()).get("text", ""))[:MAX_QUESTION_CHARS]
    except (ValueError, AttributeError):
        raise web.HTTPBadRequest(text='send {"text": "..."}') from None
    resp = web.StreamResponse(headers={"Content-Type": "application/x-ndjson"})
    await resp.prepare(request)
    async for event in request.app[BRAIN].chat.ask(text):
        await resp.write((json.dumps(event) + "\n").encode())
    await resp.write_eof()
    return resp


async def api_chat_clear(request: web.Request) -> web.Response:
    request.app[BRAIN].chat.clear()
    return web.json_response({"ok": True})


async def api_spend(request: web.Request) -> web.Response:
    brain = request.app[BRAIN]
    if brain.venue.public:
        return web.json_response({"available": False})  # a public screen hides spend
    return web.json_response({"available": True} | brain.chat.spend.month())


async def _ai_task(app: web.Application):
    brain = app[BRAIN]

    async def run():
        while True:
            internet = brain.internet.online if brain.internet else None
            ok = await brain.chat.check(internet)
            await asyncio.sleep(AI_CHECK_EVERY_S[0] if ok else AI_CHECK_EVERY_S[1])

    task = asyncio.create_task(run()) if brain.check_ai else None
    yield
    if task:
        task.cancel()
    await brain.chat.close()


async def _internet_task(app: web.Application):
    check = app[BRAIN].internet
    task = asyncio.create_task(check.run()) if check else None
    yield
    if task:
        task.cancel()


async def _mcp_task(app: web.Application):
    mcp = app[MCP]
    task = asyncio.create_task(mcp.serve()) if mcp else None
    yield
    if task:
        mcp.shutdown()
        try:
            await asyncio.wait_for(task, 3)
        except (TimeoutError, asyncio.CancelledError):
            task.cancel()


def create_brain_app(
    loop: TeleopLoop,
    venue: Venue,
    internet: InternetCheck | None = None,
    focus_file: Path = FOCUS_FILE,
    repo: Path = REPO_ROOT,
    mcp_port: int | None = None,
    place: config.Place | None = None,
    chat: Conversation | None = None,
    check_ai: bool = False,
    persona: Callable[[], Persona] | None = None,
) -> web.Application:
    """The teleop server with the hub on top. Pass an `InternetCheck` to check in the background,
    and `mcp_port` to offer the robot tools over MCP (calls logged to logs/ai-tools/). `place`:
    default = the active config folder's place.yaml."""
    app = create_app(loop, root_page=False)
    calls = CallLog.for_this_run() if mcp_port else CallLog()
    app[TOOLS] = RobotTools(loop, venue, app[CONTROL], calls=calls)
    # one MCP server: offered to AI tools over HTTP (with mcp_port), and its read tools to the
    # hub's own chat (always, in-process)
    server = create_mcp_server(app[TOOLS], ProjectTools(repo, venue))
    app[MCP] = McpHttp(server, mcp_port) if mcp_port else None
    place = place or config.load_place()
    persona = persona or (lambda: persona_for_venue(venue.name))
    assistant = chat.assistant if chat else Assistant()
    chat = chat or Conversation(
        assistant,
        SpendLog(budget_usd=place.ai_budget_usd_month),
        place_name=place.name,
        persona=persona,
        tools=ChatTools(server),
    )
    app[BRAIN] = Brain(place, venue, internet, assistant, focus_file, repo, chat, persona, check_ai)
    app.router.add_get("/", hub_page)
    app.router.add_get("/perf", perf_page)
    app.router.add_get("/api/status", api_status)
    app.router.add_get("/api/project", api_project)
    app.router.add_get("/api/commits", api_commits)
    app.router.add_get("/api/hub", api_hub)
    app.router.add_get("/api/greeting", api_greeting)
    app.router.add_post("/api/chat/start", api_chat_start)
    app.router.add_get("/api/chat", api_chat_get)
    app.router.add_post("/api/chat", api_chat_post)
    app.router.add_post("/api/chat/clear", api_chat_clear)
    app.router.add_get("/api/spend", api_spend)
    app.router.add_static("/hub", HUB_WEB_DIR)
    app.cleanup_ctx.append(_internet_task)
    app.cleanup_ctx.append(_mcp_task)
    app.cleanup_ctx.append(_ai_task)
    return app
