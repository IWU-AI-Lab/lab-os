"""The brain's web server (`lab-os serve`): the hub page, with the teleop pages inside it.

GET /                    the hub: start screen, status strip, module buttons, assistant, panels
                         (plain, or the designed one when the theme says hub.look: design)
GET /plain, /design      each look by name (the design = the reveal, docs/design/DESIGN.md)
GET /ai                  AI Control: the arm and every robot-tool call, live (a module page)
GET /xr                  the hub in VR/AR for the Quest (watch-only)
GET /training            the training launcher's page (so101-green + LeLab,
                         docs/guides/green-launcher.md)
GET /api/green           the training launcher's port check (port names only, nothing opened)
POST /api/green/start    check again, then start LeLab in a terminal (the brain's computer only)
POST /api/green/stop     stop the LeLab the launcher started, nothing else (brain's computer only)
GET /settings            the settings page (also opened from the hub's gear)
GET /perf                performance test page (drifting dots, links, star streaks + frames/s)
GET /hub/...             the hub's own files (src/lab_os/hub/web/)
GET /api/status          venue, internet, AI, assistant state, the brain's clock, what's in use
GET /api/project         the Current Project panel (docs/plan/current-focus.md → Steps)
GET /api/commits?days=N  commits per day for the last N days, and the latest few commits
GET /api/arm             the arm now: name, joints (degrees), held still, who has control
GET /api/pose-view.png   the AI's pose_view picture of the arm now (side + top, grid in cm)
GET /api/devices         the place's devices (devices.yaml): kind, off limits, linked to the brain
GET /api/ai-calls?after=T  the robot tools' calls (after time T), the MCP address, motion allowed
GET /api/settings        the settings (src/lab_os/settings.py) and their values
POST /api/settings       {"key": "theme:hub.look", "value": "design"}: change one (here only)
GET /api/hub             the place's name (the title), the module buttons (hub.modules that have
                         a page) and the reset time
GET /api/greeting        "Good evening." + one line of real news, else the persona's line
POST /api/chat/start     start a fresh conversation with the greeting (the start press)
GET /api/chat            the conversation so far and the chat's status
POST /api/chat           {"text": "..."} → one turn, streamed as JSON lines (docs/dev/protocol.md)
POST /api/chat/clear     put the conversation aside (the hub's reset; kept chat_keep_minutes)
POST /api/chat/restore   bring back the conversation put aside
GET /ws/voice            voice: the page's microphone in, spoken answers out (hub/voice.py)
GET /api/voice/timings   the last voice turns' timing: where the time went, step by step
GET /ws/hub-device       one hub page of a device (?device=desk): the brain's list of devices,
                         "open on…" and the device's settings (hub/hub_devices.py)
GET /api/hub-devices     the devices with the hub open now, their windows, what each shows
POST /api/hub-devices/open   {"module", "device", "window"?}: open a module on another device
POST /api/hub-devices/close  {"device", "window"}: close it there ("bring it back")
GET/POST /api/hub-devices/{name}/settings   a device's own settings ("This device")
GET /api/spend           this month's AI spend and budget (hidden on a public venue)
Everything else is the teleop server's: /teleop, /monitor, /ws, /static, /web, /models, /theme.json.
The robot tools for AI tools run as an MCP server on their own port (lab_os.tools.mcp_server).
"""

import asyncio
import json
import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aiohttp import web

from lab_os import REPO_ROOT, config, green, settings
from lab_os.ai.assistant import ASSISTANT_STATES, Assistant  # noqa: F401 (used by tests)
from lab_os.ai.chat import Conversation
from lab_os.ai.history import ChatStore
from lab_os.ai.spend import SpendLog
from lab_os.ai.tools import ChatTools
from lab_os.ai.voices import VoiceSetup, load_voices
from lab_os.hub.commits import commits_per_day, recent_commits
from lab_os.hub.greeting import greeting
from lab_os.hub.hub_devices import DeviceError, DeviceSettings, HubDevices
from lab_os.hub.internet import InternetCheck
from lab_os.hub.project import FOCUS_FILE, project_summary
from lab_os.hub.voice import VoiceDesk, voice_ws
from lab_os.personas import Persona, current_persona
from lab_os.teleop.loop import TeleopLoop
from lab_os.teleop.recording import Recorder
from lab_os.teleop.server import CONTROL, LOOP, create_app, is_local
from lab_os.theme import load_theme
from lab_os.tools.calllog import CallLog
from lab_os.tools.mcp_server import McpHttp, create_mcp_server
from lab_os.tools.project import ProjectTools
from lab_os.tools.robot import Refused, RobotTools
from lab_os.venues import Venue

HUB_WEB_DIR = Path(__file__).parent / "web"
LOOKS = {"plain": "index.html", "design": "design.html"}  # theme hub.look picks the one at /

# Every module the hub knows: id → (button title, page). The theme's hub.modules picks which ones
# get a button and in what order; ids without a page here get no button (only claim what's real).
MODULES = {
    "teleop": ("Teleop", "/teleop"),
    "monitor": ("Monitor", "/monitor"),
    "ai": ("AI Control", "/ai"),  # what an AI tool is doing with the arm, live
    "training": ("Training", "/training"),  # start so101-green + LeLab after a port check
}

DEFAULT_RESET_AFTER_S = 1800.0
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
    persona: Callable[[], Persona]  # the chosen persona, re-read each time (edit + reload)
    project: ProjectTools  # the read tools' device list, docs, git (shared with the MCP server)
    voice: VoiceDesk
    check_ai: bool = False  # check the AI service in the background (off in tests)


BRAIN = web.AppKey("brain", Brain)
TOOLS = web.AppKey("tools", RobotTools)
MCP = web.AppKey("mcp", McpHttp | None)
HUB_DEVICES = web.AppKey("hub_devices", HubDevices)


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
    """The venue's value wins, then the theme's hub.reset_after_s, then 30 minutes."""
    if venue.reset_after_s:
        return venue.reset_after_s
    return float((theme.get("hub") or {}).get("reset_after_s") or DEFAULT_RESET_AFTER_S)


def in_use(app: web.Application) -> list[str]:
    """What's in use right now; the hub never goes back to the start screen while this isn't
    empty: teleop has the arm, the AI tools are moving it, an answer streams, a voice turn runs
    (from the press until the last spoken word)."""
    used = []
    if app[CONTROL].get("ws") is not None:
        used.append("teleop")
    if app[LOOP].motion_active:
        used.append("ai")
    if app[BRAIN].chat.busy:
        used.append("chat")
    if app[BRAIN].voice.active():
        used.append("voice")
    return used


async def _file(request: web.Request, name: str) -> web.FileResponse:
    return web.FileResponse(HUB_WEB_DIR / name)


async def hub_page(request: web.Request) -> web.FileResponse:
    look = str((load_theme().get("hub") or {}).get("look") or "plain")
    if look not in LOOKS:
        log.warning("theme hub.look: %r isn't one of %s; showing plain", look, ", ".join(LOOKS))
        look = "plain"
    return await _file(request, LOOKS[look])


async def plain_page(request: web.Request) -> web.FileResponse:
    return await _file(request, LOOKS["plain"])


async def design_page(request: web.Request) -> web.FileResponse:
    return await _file(request, LOOKS["design"])


async def ai_page(request: web.Request) -> web.FileResponse:
    return await _file(request, "ai.html")


async def settings_page(request: web.Request) -> web.FileResponse:
    return await _file(request, "settings.html")


async def xr_page(request: web.Request) -> web.FileResponse:
    return await _file(request, "xr.html")


async def training_page(request: web.Request) -> web.FileResponse:
    return await _file(request, "training.html")


async def api_green(request: web.Request) -> web.Response:
    """The green launcher's check (lab_os.green): looks at port names only, opens nothing."""
    c = await asyncio.to_thread(green.check)
    return web.json_response(c.as_dict() | {"here": is_local(request)})


async def api_green_start(request: web.Request) -> web.Response:
    """Start: checks again, then opens a terminal on this desktop that starts LeLab. Only from the
    brain's computer (it opens a window there)."""
    if not is_local(request):
        raise web.HTTPForbidden(text="The training setup starts only on the brain's computer.")
    c = await asyncio.to_thread(green.check)
    if c.ok and not c.running:
        green.remember(c)
        green.open_terminal()
        log.info("green launcher: LeLab starting in a terminal")
    return web.json_response(c.as_dict() | {"here": True, "started": c.ok and not c.running})


async def api_green_stop(request: web.Request) -> web.Response:
    """Stop LeLab: only the one the launcher started (lab_os.green.stop_lelab)."""
    if not is_local(request):
        raise web.HTTPForbidden(text="LeLab can be stopped only from the brain's computer.")
    said = await asyncio.to_thread(green.stop_lelab)
    log.info("green launcher: %s", said)
    c = await asyncio.to_thread(green.check)
    return web.json_response(c.as_dict() | {"here": True, "said": said})


async def api_ai_calls(request: web.Request) -> web.Response:
    """The robot tools' calls this run (newest last), for the AI Control page."""
    try:
        after = float(request.query.get("after", 0))
    except ValueError:
        raise web.HTTPBadRequest(text="after must be a number (epoch seconds)") from None
    app = request.app
    tools = app[TOOLS]
    calls = [c for c in tools.calls.entries if c["t"] > after]
    mcp = app[MCP]
    return web.json_response(
        {
            "calls": calls[-50:],
            "mcp": mcp.url if mcp and not mcp.failed else None,
            "motion_allowed": app[BRAIN].venue.motion_allowed,
            "control": tools.who_has_control(),
        },
        dumps=lambda o: json.dumps(o, default=str),
    )


async def api_settings_get(request: web.Request) -> web.Response:
    brain = request.app[BRAIN]
    return web.json_response(
        {
            "sections": settings.read(brain.venue.name),
            "writable": is_local(request),
            "why_not": None
            if is_local(request)
            else "Settings change only on the brain's computer.",
            "venue": brain.venue.name,
        }
    )


async def api_settings_post(request: web.Request) -> web.Response:
    """Change one setting. Only from the brain's computer: other screens may be in a hallway."""
    if not is_local(request):
        raise web.HTTPForbidden(text="Settings change only on the brain's computer.")
    try:
        body = await request.json()
        key, value = str(body["key"]), body["value"]
    except (ValueError, KeyError, TypeError):
        raise web.HTTPBadRequest(text='send {"key": "...", "value": ...}') from None
    try:
        value = await asyncio.to_thread(settings.write, key, value, request.app[BRAIN].venue.name)
    except settings.SettingError as e:
        return web.json_response({"ok": False, "message": str(e)}, status=400)
    except (OSError, config.ConfigError) as e:
        return web.json_response({"ok": False, "message": f"Couldn't save: {e}"}, status=500)
    field = settings.find(key)
    log.info("setting %s = %r (from the settings page)", key, value)
    return web.json_response({"ok": True, "key": key, "value": value, "applies": field.applies})


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
            "voice": brain.voice.status(),
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


def side_view_cm(kin, joints: dict[str, float]) -> list[dict] | None:
    """The arm seen from its side: each joint's distance forward from the base and height (cm),
    base first, the gripper's tip last. None when the arm has no joint-by-joint kinematics."""
    frames = getattr(kin, "frames", None)
    if frames is None:
        return None
    pan = math.radians(joints.get("shoulder_pan", 0.0))
    all_frames = frames(joints)
    # measured along the way the arm faces, from its pan axis (which isn't at the base's origin), so
    # the drawing stays the same shape when the arm turns; +pan turns toward -y (as in fk)
    ax, ay, _ = all_frames.get("shoulder_pan", ((0.0, 0.0, 0.0), None))[0]
    points = [{"name": "base", "r": 0.0, "z": 0.0}]
    for name, (p, _rot) in all_frames.items():
        if name == "gripper_frame_joint":
            continue  # the same point as "tip"
        forward = ax + (p[0] - ax) * math.cos(pan) - (p[1] - ay) * math.sin(pan)
        points.append({"name": name, "r": round(forward * 100, 1), "z": round(p[2] * 100, 1)})
    return points


async def api_pose_view(request: web.Request) -> web.Response:
    """The same picture the AI tool pose_view returns (no marks), for people to check it."""
    try:
        r = await request.app[TOOLS].pose_view()
    except Refused as e:
        return web.Response(status=404, text=str(e))
    except Exception as e:  # the arm stopped answering
        return web.Response(status=503, text=f"can't read the arm: {e}")
    return web.Response(
        body=r["image_png"], content_type="image/png", headers={"Cache-Control": "no-store"}
    )


async def api_arm(request: web.Request) -> web.Response:
    """The arm's joints for the hub's readouts (the driver rate-limits real reads)."""
    app = request.app
    loop: TeleopLoop = app[LOOP]
    out = {"name": loop.arm.name, "model": getattr(loop.arm, "model", "unknown")}
    try:
        joints = {j: round(v, 1) for j, v in loop.arm.read_joints().items()}
        where = app[TOOLS].position()  # the gripper point (cm) where the arm has kinematics
    except Exception as e:  # the arm stopped answering: say so, don't fail the page
        return web.json_response(out | {"connected": False, "problem": str(e)})
    out |= {k: where[k] for k in ("gripper_point_cm", "gripper_open_pct") if k in where}
    side = side_view_cm(app[TOOLS].kin, joints)
    if side:
        out["side_cm"] = side
    control = (
        "ai" if loop.motion_active else "teleop" if app[CONTROL].get("ws") is not None else "free"
    )
    return web.json_response(
        out | {"connected": True, "joints": joints, "held": loop.frozen, "control": control}
    )


async def api_devices(request: web.Request) -> web.Response:
    """The place's devices, from config only: whether one is switched on isn't known until the
    roll call (lab router). `linked` = the arm this brain drives. Off-limits ones are listed,
    never opened."""
    brain = request.app[BRAIN]
    arm = request.app[LOOP].arm.name
    try:
        devices = brain.project.list_devices()["devices"]
    except (config.ConfigError, OSError) as e:
        log.warning("devices: %s", e)
        devices = []
    for d in devices:
        d["linked"] = d["name"] == arm
    if not any(d["linked"] for d in devices):
        devices.append(
            {"name": arm, "kind": "arm", "off_limits": False, "linked": True, "notes": ""}
        )
    return web.json_response({"devices": devices, "arm": arm})


async def api_project(request: web.Request) -> web.Response:
    return web.json_response(project_summary(request.app[BRAIN].focus_file))


async def api_commits(request: web.Request) -> web.Response:
    try:
        days = int(request.query.get("days", 14))
    except ValueError:
        raise web.HTTPBadRequest(text="days must be a whole number") from None
    days = max(1, min(MAX_COMMIT_DAYS, days))
    repo = request.app[BRAIN].repo
    result = await asyncio.to_thread(commits_per_day, days, repo)
    return web.json_response(result | {"recent": await asyncio.to_thread(recent_commits, 8, repo)})


async def api_hub(request: web.Request) -> web.Response:
    theme = load_theme()  # re-read each time, like /theme.json: edit, then reload the page
    try:
        title = config.load_place().name  # re-read: the settings page can rename the place
    except (config.ConfigError, OSError):
        title = request.app[BRAIN].place.name
    return web.json_response(
        {
            "title": title,
            "modules": hub_modules(theme),
            "reset_after_s": reset_after_s(theme, request.app[BRAIN].venue),
        }
    )


def _opening(chat: Conversation) -> str:
    """The greeting the conversation started with (the start press), for the spoken greeting."""
    first = chat.messages[0] if chat.messages else None
    return first["content"] if first and first["role"] == "assistant" else ""


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
    return web.json_response(hello | {"previous": brain.chat.previous()})


async def api_chat_get(request: web.Request) -> web.Response:
    chat = request.app[BRAIN].chat
    return web.json_response(
        {"messages": chat.messages, "status": chat.status(), "previous": chat.previous()}
    )


async def api_chat_post(request: web.Request) -> web.StreamResponse:
    """One turn, streamed as JSON lines: state / text / open / done / error events. `pages`: what
    the asking page can show ({id: title}), for the assistant's open_page tool."""
    try:
        body = await request.json()
        text = str(body.get("text", ""))[:MAX_QUESTION_CHARS]
        pages = body.get("pages")
    except (ValueError, AttributeError):
        raise web.HTTPBadRequest(text='send {"text": "..."}') from None
    resp = web.StreamResponse(headers={"Content-Type": "application/x-ndjson"})
    await resp.prepare(request)
    async for event in request.app[BRAIN].chat.ask(text, pages):
        await resp.write((json.dumps(event) + "\n").encode())
    await resp.write_eof()
    return resp


async def api_chat_clear(request: web.Request) -> web.Response:
    request.app[BRAIN].chat.clear()
    return web.json_response({"ok": True})


async def api_chat_restore(request: web.Request) -> web.Response:
    chat = request.app[BRAIN].chat
    ok = chat.restore()
    return web.json_response({"ok": ok, "messages": chat.messages, "previous": chat.previous()})


async def api_voice_ws(request: web.Request) -> web.WebSocketResponse:
    return await voice_ws(request, request.app[BRAIN].voice)


async def api_voice_timings(request: web.Request) -> web.Response:
    return web.json_response({"timings": list(request.app[BRAIN].voice.timings)})


async def api_hub_device_ws(request: web.Request) -> web.WebSocketResponse:
    return await request.app[HUB_DEVICES].connection(request)


async def api_hub_devices(request: web.Request) -> web.Response:
    devices = request.app[HUB_DEVICES]
    return web.json_response({"devices": devices.listing(), "sent": devices.sent()})


async def _body(request: web.Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(text="send a JSON object")
    return body


def _refused(e: DeviceError) -> web.Response:
    return web.json_response({"ok": False, "message": str(e)}, status=400)


async def api_hub_devices_open(request: web.Request) -> web.Response:
    """Open a module on another device's hub ("open on…"). Any hub page may: it only changes
    what that screen shows, and only on a device that has the hub open."""
    b = await _body(request)
    try:
        r = await request.app[HUB_DEVICES].open_on(
            str(b.get("module", "")),
            str(b.get("device", "")),
            window=str(b.get("window") or ""),
            sender=str(b.get("from") or "")[:32],
            sender_window=str(b.get("from_window") or ""),
        )
    except DeviceError as e:
        return _refused(e)
    if r["ok"]:
        log.info("open on: %s → %s (from %s)", b.get("module"), r["device"], b.get("from") or "?")
    return web.json_response(r)


async def api_hub_devices_close(request: web.Request) -> web.Response:
    b = await _body(request)
    try:
        r = await request.app[HUB_DEVICES].close_on(
            str(b.get("device", "")), str(b.get("window", ""))
        )
    except DeviceError as e:
        return _refused(e)
    return web.json_response(r)


async def api_hub_device_settings_get(request: web.Request) -> web.Response:
    devices = request.app[HUB_DEVICES]
    try:
        values = await asyncio.to_thread(devices.settings.get, request.match_info["name"])
    except DeviceError as e:
        return _refused(e)
    return web.json_response({"ok": True, "settings": values})


async def api_hub_device_settings_post(request: web.Request) -> web.Response:
    """Change a device's own settings; every window of that device gets them at once. Any page
    may (they were per browser before, so any screen could change its own)."""
    devices = request.app[HUB_DEVICES]
    name = request.match_info["name"]
    b = await _body(request)
    try:
        values = await asyncio.to_thread(devices.settings.update, name, b)
    except DeviceError as e:
        return _refused(e)
    except OSError as e:
        return web.json_response({"ok": False, "message": f"Couldn't save: {e}"}, status=500)
    await devices.push_settings(name, values)
    return web.json_response({"ok": True, "settings": values})


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
    await brain.voice.close()


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


def _chat_store(place: config.Place) -> ChatStore | None:
    if place.chat_keep_minutes > 0:
        return ChatStore(keep_minutes=place.chat_keep_minutes)
    ChatStore().forget()  # keeping is off: nothing from before stays on disk either
    return None


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
    local_control_only: bool = False,
    recorder: Recorder | None = None,
    drive_from: frozenset[str] = frozenset(),
    voices: Callable[[], dict[str, VoiceSetup]] | None = None,
    device_settings: DeviceSettings | None = None,
) -> web.Application:
    """The teleop server with the hub on top. Pass an `InternetCheck` to check in the background,
    and `mcp_port` to offer the robot tools over MCP (calls logged to logs/ai-tools/). `place`:
    default = the active config folder's place.yaml. `local_control_only`: only pages on this
    computer may drive the arm (a real arm served to the network). `recorder`: save the teleop
    input (`lab-os serve --record`). `voices`: the voice setups (default: models.yaml's).
    `device_settings`: where each device's own settings are kept (default: the place's
    hub-devices.yaml)."""
    app = create_app(
        loop,
        recorder,
        root_page=False,
        local_control_only=local_control_only,
        drive_from=drive_from,
    )
    calls = CallLog.for_this_run() if mcp_port else CallLog()
    app[TOOLS] = RobotTools(loop, venue, app[CONTROL], calls=calls)
    # one MCP server: offered to AI tools over HTTP (with mcp_port), and its read tools to the
    # hub's own chat (always, in-process)
    project = ProjectTools(repo, venue)
    server = create_mcp_server(app[TOOLS], project)
    app[MCP] = McpHttp(server, mcp_port) if mcp_port else None
    own_place = place is None  # the active place's files: the budget is re-read as it changes
    place = place or config.load_place()
    persona = persona or (lambda: current_persona(venue=venue.name))
    assistant = chat.assistant if chat else Assistant()
    chat = chat or Conversation(
        assistant,
        SpendLog(
            budget_usd=place.ai_budget_usd_month,
            budget_from=config.ai_budget if own_place else None,
        ),
        place_name=place.name,
        persona=persona,
        tools=ChatTools(server),
        store=_chat_store(place),
    )
    voice = VoiceDesk(
        chat,
        assistant,
        persona,
        internet=lambda: internet.online if internet else None,
        voices=voices or load_voices,
        greeting=lambda: _opening(chat),
        recordings=lambda: config.recordings_dir() / "greetings",
        venue_wake=lambda: venue.wake_word_on,
    )
    app[BRAIN] = Brain(
        place, venue, internet, assistant, focus_file, repo, chat, persona, project, voice, check_ai
    )
    app[HUB_DEVICES] = HubDevices(
        lambda: {m["id"]: m["title"] for m in hub_modules(load_theme())}, device_settings
    )
    app.router.add_get("/", hub_page)
    app.router.add_get("/plain", plain_page)
    app.router.add_get("/design", design_page)
    app.router.add_get("/ai", ai_page)
    app.router.add_get("/training", training_page)
    app.router.add_get("/xr", xr_page)
    app.router.add_get("/api/green", api_green)
    app.router.add_post("/api/green/start", api_green_start)
    app.router.add_post("/api/green/stop", api_green_stop)
    app.router.add_get("/settings", settings_page)
    app.router.add_get("/perf", perf_page)
    app.router.add_get("/api/status", api_status)
    app.router.add_get("/api/project", api_project)
    app.router.add_get("/api/commits", api_commits)
    app.router.add_get("/api/arm", api_arm)
    app.router.add_get("/api/pose-view.png", api_pose_view)
    app.router.add_get("/api/devices", api_devices)
    app.router.add_get("/api/ai-calls", api_ai_calls)
    app.router.add_get("/api/settings", api_settings_get)
    app.router.add_post("/api/settings", api_settings_post)
    app.router.add_get("/api/hub", api_hub)
    app.router.add_get("/api/greeting", api_greeting)
    app.router.add_post("/api/chat/start", api_chat_start)
    app.router.add_get("/api/chat", api_chat_get)
    app.router.add_post("/api/chat", api_chat_post)
    app.router.add_post("/api/chat/clear", api_chat_clear)
    app.router.add_post("/api/chat/restore", api_chat_restore)
    app.router.add_get("/api/spend", api_spend)
    app.router.add_get("/ws/voice", api_voice_ws)
    app.router.add_get("/api/voice/timings", api_voice_timings)
    app.router.add_get("/ws/hub-device", api_hub_device_ws)
    app.router.add_get("/api/hub-devices", api_hub_devices)
    app.router.add_post("/api/hub-devices/open", api_hub_devices_open)
    app.router.add_post("/api/hub-devices/close", api_hub_devices_close)
    app.router.add_get("/api/hub-devices/{name}/settings", api_hub_device_settings_get)
    app.router.add_post("/api/hub-devices/{name}/settings", api_hub_device_settings_post)
    app.router.add_static("/hub", HUB_WEB_DIR)
    app.cleanup_ctx.append(_internet_task)
    app.cleanup_ctx.append(_mcp_task)
    app.cleanup_ctx.append(_ai_task)
    return app
