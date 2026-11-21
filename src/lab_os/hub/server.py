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
GET /api/shutdown        may this page shut lab-os down, and what to warn about first
POST /api/shutdown       {"from": device}: stop any move, tell every page, stop the brain as Ctrl+C
POST /api/restart        {"from": device}: the same, then the brain starts again with the same
                         options (Settings' "Restart Now", for settings that apply on a restart)
                         does (lets go of the arm). Brain's computer only
GET /api/quest-view      what the Quest sees (scrcpy, quick job 36): installed, running, headsets
POST /api/quest-view/start  {"headset"?}: open its view in a window here (the brain's computer)
POST /api/quest-view/stop   close that window
POST /api/window-state   {"url", "state": "fullscreen" | "normal"}: a window of lab-os's own browser
                         full screen or back to a window (quick job 74). Brain's computer only
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
POST /api/venue          {"to": "visitors" | "normal"}: visitor mode on or off (Settings; here only)
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
GET /api/arm-cameras     the arm's cameras (stand, wrist) for the teleop page's pictures
GET /api/camera-feed/{name}   that camera's newest picture (JPEG); opened while asked for, closed
                         5 s after (lab_os/camera_feed.py)
Everything else is the teleop server's: /teleop, /monitor, /ws, /static, /web, /models, /theme.json.
The robot tools for AI tools run as an MCP server on their own port (lab_os.tools.mcp_server).
"""

import asyncio
import json
import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from aiohttp import web

from lab_os import REPO_ROOT, camera_feed, config, green, settings
from lab_os.ai.assistant import ASSISTANT_STATES, Assistant  # noqa: F401 (used by tests)
from lab_os.ai.chat import Conversation
from lab_os.ai.history import ChatStore
from lab_os.ai.languages import LANGUAGES, clean_language
from lab_os.ai.spend import SpendLog
from lab_os.ai.tools import ChatTools
from lab_os.ai.voices import VoiceSetup, load_voices
from lab_os.devices import load_registry
from lab_os.hub import launch
from lab_os.hub.arm_desk import Actions, ArmDesk
from lab_os.hub.commits import commits_per_day, recent_commits
from lab_os.hub.greeting import greeting
from lab_os.hub.hub_devices import DeviceError, DeviceSettings, HubDevices, clean_name
from lab_os.hub.internet import InternetCheck
from lab_os.hub.project import FOCUS_FILE, project_summary
from lab_os.hub.visitors import VisitorDesk, robots_here, spoken_name
from lab_os.hub.voice import VoiceDesk, voice_ws
from lab_os.personas import Persona, current_persona
from lab_os.quest_view import AdbReverse, QuestView, QuestViewError
from lab_os.teleop.cli import LEFT_FAKE, teleop_floor_m
from lab_os.teleop.loop import TeleopLoop
from lab_os.teleop.recording import Recorder
from lab_os.teleop.server import (
    CONTROL,
    LOOP,
    OFF_TELL_S,
    OFF_TOLD,
    OUTBOX,
    SHUTDOWN,
    brain_off_message,
    close_sockets,
    create_app,
    is_local,
)
from lab_os.theme import load_theme
from lab_os.tools.calllog import CallLog
from lab_os.tools.mcp_server import McpHttp, add_lab_status, create_mcp_server
from lab_os.tools.project import ProjectTools
from lab_os.tools.robot import Refused, RobotTools
from lab_os.venues import Venue, load_venue, visitors_venue_name

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

# Every page the brain serves: (address, name, one line). ⚙ → All Pages lists them, so each opens
# from the hub in two taps (quick job 67); a test checks that no page is missing here.
PAGES = (
    ("/", "The Hub", "The main address: the plain or the designed hub (⚙ → The Lab)."),
    ("/design", "Designed Hub", "The designed hub, whatever the main address shows."),
    ("/plain", "Plain Hub", "The plain hub, whatever the main address shows."),
    ("/teleop", "Teleop", "Drive the arm: the Quest, the desktop's keys or the joint sliders."),
    ("/monitor", "Monitor", "The arm's joints and 3D view, with STOP; drives nothing."),
    ("/ai", "AI Control", "What an AI tool does with the arm, live."),
    ("/training", "Training", "Start the green arms' LeLab after a port check."),
    ("/webcam", "Webcam Teleop", "Your bare hand in front of the webcam drives the arm (preview)."),
    ("/xr", "VR Hub", "The hub in the headset (opens only in a VR browser)."),
    ("/settings", "Settings", "This page: ⚙ on the hub."),
    ("/perf", "Performance Test", "Drifting dots and star streaks with frames per second."),
    ("/classic/teleop", "Classic Teleop", "The first teleop page, kept in case."),
    ("/classic/monitor", "Classic Monitor", "The first monitor page, kept in case."),
)

DEFAULT_RESET_AFTER_S = 1800.0
MAX_COMMIT_DAYS = 90
MAX_QUESTION_CHARS = 2000
AI_CHECK_EVERY_S = (60.0, 20.0)  # while connected / while not
# quick job 73: started on the fake arm with no --arm, the brain looks this often for an SO-101
# plugged in since, and takes it once the fake arm has been still this long
NEW_ARM_EVERY_S = 2.0
NEW_ARM_QUIET_S = 5.0
ADB_EVERY_S = 3.0  # quick job 73: how often the brain looks for a newly connected Quest

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
    visitors: VisitorDesk | None = None  # "say hello to our visitors" (quick job 35)
    started_in: str = ""  # the venue the brain started with: exiting visitor mode goes there
    # settings changed since the start that apply on a restart (key → label), for "Restart Now";
    # a value set back to what the brain runs with leaves it (quick job 45)
    restart_needed: dict = field(default_factory=dict)
    # what the brain runs with, per venue: each setting's value when first seen (key → value)
    running: dict = field(default_factory=dict)

    def running_values(self, venue: str) -> dict:
        """The settings as the brain runs with them (read once per venue: at the first look)."""
        if venue not in self.running:
            try:
                sections = settings.read(venue)
            except Exception:  # a broken file: problems() says which; nothing to compare with
                sections = []
            self.running[venue] = {f["key"]: f["value"] for s in sections for f in s["fields"]}
        return self.running[venue]


BRAIN = web.AppKey("brain", Brain)
TOOLS = web.AppKey("tools", RobotTools)
TOOLS_PROJECT = web.AppKey("tools_project", ProjectTools)
MCP = web.AppKey("mcp", McpHttp | None)
HUB_DEVICES = web.AppKey("hub_devices", HubDevices)
WAVES = web.AppKey("waves", set)  # waves playing (kept so they aren't dropped half way)
QUEST_VIEW = web.AppKey("quest_view", QuestView)
FEEDS = web.AppKey("feeds", camera_feed.CameraFeeds)  # quick job 63: the cameras open for pages
ADB_REVERSE = web.AppKey("adb_reverse", object)  # quick job 73: an AdbReverse, or None
FIND_ARM = web.AppKey("find_arm", object)  # quick job 73: lab_os.teleop.cli.arm_finder(), or None
RESTART = web.AppKey("restart", dict)  # {"asked": bool}: start again after stopping (lab_os.cli)


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


# ---------- shut down from the hub (quick job 6) ----------
SHUTDOWN_DELAY_S = 0.5  # time for "lab-os is off" to reach every page before the sockets close


def _shutdown_check(request: web.Request) -> str | None:
    """Why this page may not shut lab-os down, or None."""
    if not is_local(request):
        return "lab-os can be shut down only from the brain's computer."
    return None


def _limp_arms(loop: TeleopLoop) -> list[str]:
    """The arms that go limp when lab-os lets go (an SO-101: its torque switches off)."""
    return [
        each.arm.name
        for each in (loop, loop.left)
        if each and each.arm_connected and getattr(each.arm, "limp_on_close", False)
    ]


def _shutdown_warning(loop: TeleopLoop) -> str | None:
    """What happens to the arms, when it matters: an SO-101 goes limp (its torque switches off)."""
    limp = _limp_arms(loop)
    if not limp:
        return None
    if len(limp) == 1:
        return (
            f"{limp[0]} goes limp: if it's lifted, it drops. Put it down (home) or hold it first."
        )
    return (
        f"{' and '.join(limp)} go limp: if one is lifted, it drops. "
        "Put them down (home) or hold them first."
    )


async def api_shutdown_get(request: web.Request) -> web.Response:
    why = _shutdown_check(request)
    loop = request.app[LOOP]
    return web.json_response(
        {
            "allowed": why is None,
            "why_not": why,
            "warning": _shutdown_warning(loop),
            "limp": _limp_arms(loop),  # the confirmation names them on its button too
        }
    )


async def api_shutdown(request: web.Request) -> web.Response:
    """Shut down: stop any move now, tell every page lab-os is off, then stop the server the way
    Ctrl+C does; `lab-os serve`'s cleanup then lets go of the arm (lab_os.cli)."""
    return await _stop_brain(request, restart=False)


async def api_restart(request: web.Request) -> web.Response:
    """Restart (quick job 38): as a shutdown, then `lab-os serve` starts again with the same
    options (lab_os.cli), so settings that apply on a restart take effect. Pages reload by
    themselves once it's back."""
    return await _stop_brain(request, restart=True)


async def _stop_brain(request: web.Request, restart: bool) -> web.Response:
    why = _shutdown_check(request)
    if why:
        raise web.HTTPForbidden(text=why)
    try:
        body = await request.json()
        by = clean_name(str(body.get("from") or ""))
    except (ValueError, AttributeError, DeviceError):
        by = ""
    app = request.app
    what = "restarting" if restart else "shutting down"
    log.warning("%s: asked from the hub (%s)", what, by or "a page with no device name")
    app[LOOP].shut_down(f"lab-os is {what}")  # and nothing moves again (quick job 44)
    app[RESTART]["asked"] = restart
    await _tell_off(app, brain_off_message(by, restart))
    asyncio.get_running_loop().call_later(SHUTDOWN_DELAY_S, app[SHUTDOWN].set)
    return web.json_response({"ok": True, "message": f"lab-os is {what}."})


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


VISITORS_SETTINGS = "Settings are hidden in visitor mode. Exit visitor mode to see them again."


def _visitor_mode(request: web.Request) -> dict | None:
    """Settings → Visitor mode: on or not, its venue, where exiting goes, and whether this page may
    switch it (the brain's computer only). None: the place has no venue for visitors."""
    brain = request.app[BRAIN]
    name = brain.venue.name if brain.venue.visitors else visitors_venue_name()
    if name is None:
        return None
    return {
        "on": brain.venue.visitors,
        "venue": name,
        "back_to": brain.started_in,
        "here": is_local(request),
    }


async def api_settings_get(request: web.Request) -> web.Response:
    brain = request.app[BRAIN]
    mode = await asyncio.to_thread(_visitor_mode, request)
    if brain.venue.visitors:  # visitor mode: nothing to see or change but the way out
        return web.json_response(
            {
                "sections": [],
                "writable": False,
                "why_not": VISITORS_SETTINGS,
                "venue": brain.venue.name,
                "visitor_mode": mode,
            }
        )
    venue = brain.venue.name
    problems = await asyncio.to_thread(settings.problems, venue)
    try:
        sections = await asyncio.to_thread(settings.read, venue)
        await asyncio.to_thread(brain.running_values, venue)
    except Exception as e:  # never an empty page without a reason (quick job 45)
        log.exception("settings: couldn't read them")
        sections, problems = [], [*problems, f"The settings couldn't be read: {e}"]
    return web.json_response(
        {
            "sections": sections,
            "problems": problems,  # files that can't be read: the file and the line
            "writable": is_local(request),
            "why_not": None
            if is_local(request)
            else "Settings change only on the brain's computer.",
            "venue": brain.venue.name,
            "visitor_mode": mode,
            "restart_needed": list(brain.restart_needed.values()),
            "restart_keys": list(brain.restart_needed),
        }
    )


async def api_settings_post(request: web.Request) -> web.Response:
    """Change one setting. Only from the brain's computer: other screens may be in a hallway."""
    if not is_local(request):
        raise web.HTTPForbidden(text="Settings change only on the brain's computer.")
    if request.app[BRAIN].venue.visitors:
        return web.json_response({"ok": False, "message": VISITORS_SETTINGS}, status=403)
    try:
        body = await request.json()
        key, value = str(body["key"]), body["value"]
    except (ValueError, KeyError, TypeError):
        raise web.HTTPBadRequest(text='send {"key": "...", "value": ...}') from None
    brain = request.app[BRAIN]
    venue = brain.venue.name
    try:
        running = await asyncio.to_thread(brain.running_values, venue)  # before the change
        value = await asyncio.to_thread(settings.write, key, value, venue)
    except settings.SettingError as e:
        return web.json_response({"ok": False, "message": str(e)}, status=400)
    except config.ConfigError as e:  # a file that can't be read: the file and the line
        return web.json_response({"ok": False, "message": f"Not saved. {e}"}, status=400)
    except Exception as e:  # never a bare "500 Internal Server Error" (quick job 45)
        log.exception("settings: couldn't save %s", key)
        msg = f"Not saved: {e}. The brain's terminal has the details."
        return web.json_response({"ok": False, "message": msg}, status=500)
    field = settings.find(key)
    log.info("setting %s = %r (from the settings page)", key, value)
    needed = brain.restart_needed
    if field.applies == "restart":
        if key in running and running[key] == value:
            needed.pop(key, None)  # back to what the brain runs with: no restart for it
        else:
            needed[key] = field.label
    return web.json_response(
        {
            "ok": True,
            "key": key,
            "value": value,
            "applies": field.applies,
            "restart_needed": list(needed.values()),
            "restart_keys": list(needed),
        }
    )


def switch_venue(app: web.Application, name: str | None) -> Venue:
    """Put the running brain in another venue (None = the one it started with): its limits for
    the robot tools and teleop (top speed, starting speed, 1:1, the floor), what the hub hides,
    its cards. Read from the venue file now; lasts until the next switch or a restart. Raises
    ValueError (a sentence) when the arm it drives isn't one of that venue's devices."""
    brain, loop = app[BRAIN], app[LOOP]
    try:
        venue = load_venue(name or brain.started_in)
    except config.ConfigError as e:
        raise ValueError(str(e)) from None
    for each in (loop, loop.left):  # the second software arm (--left-arm fake) is in no venue
        name = each.arm.name if each else None
        if name and name != LEFT_FAKE and name not in venue.active_devices:
            raise ValueError(
                f"{name} isn't one of the {venue.name} venue's robots (active_devices in "
                f"venues/{venue.name}.yaml), so I stayed in {brain.venue.name}."
            )
    brain.venue = venue
    app[TOOLS].use_venue(venue)
    app[TOOLS_PROJECT].venue = venue
    loop.use_caps(venue.speed_cap_scale, venue.max_speed_scale, venue.one_to_one_cap)
    loop.mapper.config.floor_m = teleop_floor_m(venue, loop.arm.name)
    if loop.left:  # two arms at once: the caps came with use_caps, the floor is per arm
        loop.left.mapper.config.floor_m = teleop_floor_m(venue, loop.left.arm.name)
    log.info("venue: now %s (visitor mode %s)", venue.name, "on" if venue.visitors else "off")
    return venue


def _facts(app: web.Application, venue: Venue) -> dict:
    """What the visitors' welcome may say: the place, what it is, the robot arms really plugged
    in now, the cards on the screen. Only real facts: the assistant words it."""
    brain, loop = app[BRAIN], app[LOOP]
    try:
        place = config.load_place()  # re-read: the settings page may have changed it
    except (config.ConfigError, OSError):
        place = brain.place
    try:
        registry = load_registry()
        names = robots_here(registry, loop.arm.name, loop.arm_connected)
        robots = [spoken_name(n, registry.devices[n].kind) for n in names]
    except (config.ConfigError, OSError) as e:
        log.warning("visitor mode: no device list (%s)", e)
        robots = []
    facts = {"place": place.name, "about": place.about}
    if robots:  # none plugged in: left out, so the welcome doesn't dwell on what's missing
        facts["robots_here"] = robots
    return facts | {"cards_on_screen": [c["say"] for c in venue.cards]}


WAVE_REFUSED = {
    "teleop": "someone is driving the arm with teleop.",
    "ai": "the arm is already moving.",
}


async def _wave(app: web.Application) -> None:
    """Check the wave can run (raises ValueError with a sentence), then play it in the
    background: the answer doesn't wait for the arm."""
    tools = app[TOOLS]
    who = tools.who_has_control()
    if who in WAVE_REFUSED:
        raise ValueError(WAVE_REFUSED[who])
    if tools._disconnected():
        raise ValueError(f"{tools.arm.name} is disconnected.")
    try:
        tools.gesture_path("wave")
    except Refused as e:
        raise ValueError(f"{e}.") from None

    async def play():
        try:
            await tools.call("wave")
        except Exception as e:  # refused after all, or the arm stopped answering: logged
            log.warning("wave: %s", e)

    task = asyncio.create_task(play())
    app[WAVES].add(task)
    task.add_done_callback(app[WAVES].discard)


async def api_venue(request: web.Request) -> web.Response:
    """Settings → Visitor mode: start or exit it without asking the assistant (the brain's
    computer only)."""
    if not is_local(request):
        raise web.HTTPForbidden(text="Visitor mode is switched on the brain's computer.")
    body = await _body(request)
    to = body.get("to")
    if to not in ("visitors", "normal"):
        raise web.HTTPBadRequest(text='send {"to": "visitors"} or {"to": "normal"}')
    name = visitors_venue_name() if to == "visitors" else None
    if to == "visitors" and name is None:
        return web.json_response(
            {"ok": False, "message": "This place has no venue for visitors."}, status=400
        )
    try:
        venue = await asyncio.to_thread(switch_venue, request.app, name)
    except ValueError as e:
        return web.json_response({"ok": False, "message": str(e)}, status=400)
    return web.json_response({"ok": True, "venue": venue.name, "visitors": venue.visitors})


def _visitors(venue: Venue) -> dict | None:
    """What the hub shows in visitor mode: the cards (None: visitor mode is off)."""
    return {"cards": list(venue.cards)} if venue.visitors else None


async def api_quest_view(request: web.Request) -> web.Response:
    """The Quest's view (quick job 36): can it start, is it on. `here`: the asking page is on the
    brain's computer, where the window opens (only there can start it)."""
    status = await asyncio.to_thread(request.app[QUEST_VIEW].status)
    return web.json_response(status | {"here": is_local(request)})


async def api_quest_view_start(request: web.Request) -> web.Response:
    if not is_local(request):
        raise web.HTTPForbidden(text="The Quest's view opens on the brain's computer, from there.")
    try:
        body = await request.json()
    except ValueError:
        body = {}
    name = (body or {}).get("headset") if isinstance(body, dict) else None
    try:
        headset = await asyncio.to_thread(request.app[QUEST_VIEW].start, name or None)
    except QuestViewError as e:
        return web.json_response({"ok": False, "message": str(e)}, status=400)
    except OSError as e:
        return web.json_response({"ok": False, "message": f"scrcpy didn't start: {e}"}, status=500)
    return web.json_response({"ok": True, "headset": headset})


async def api_quest_view_stop(request: web.Request) -> web.Response:
    if not is_local(request):
        raise web.HTTPForbidden(text="The Quest's view is closed on the brain's computer.")
    stopped = await asyncio.to_thread(request.app[QUEST_VIEW].stop)
    return web.json_response({"ok": True, "stopped": stopped})


async def _tell_off(app: web.Application, msg: dict) -> None:
    """Tell every page lab-os is off (or restarting): teleop, monitor, AI Control and the hubs."""
    app[OFF_TOLD]["told"] = True
    app[OUTBOX].put_nowait(msg)
    await app[HUB_DEVICES].tell_all(msg)


async def _tell_off_on_stop(app: web.Application) -> None:
    """The server stops without Shut down (Ctrl+C in the brain's terminal): the pages say "lab-os
    is off" as for Shut down, not only a grey core (quick job 64). Runs before the sockets close."""
    if not app[OFF_TOLD]["told"]:
        log.warning("stopping (Ctrl+C): telling every page lab-os is off")
        await _tell_off(app, brain_off_message())
        await asyncio.sleep(OFF_TELL_S)


async def api_window_state(request: web.Request) -> web.Response:
    """Full screen without a press, for lab-os's own browser windows on the brain's computer: a page
    sent to another monitor, and the hub that sent it (quick job 74). Elsewhere `ok` is false with
    the reason, and the page asks for a press as before."""
    if not is_local(request):
        return web.json_response({"ok": False, "why": "Only on the brain's computer."})
    try:
        body = await request.json()
        url, state = str(body["url"]), str(body.get("state", "fullscreen"))
    except (ValueError, KeyError, TypeError, AttributeError):
        raise web.HTTPBadRequest(text='Send {"url": the page\'s address, "state"}.') from None
    why = await launch.set_window_state(url, state)
    if why:
        log.info("window state %s for %s: %s", state, url, why)
    return web.json_response({"ok": not why, "why": why})


async def _close_hub_pages(app: web.Application) -> None:
    """The server stops: close the hub pages' and the voice's WebSockets at once (quick job 44),
    as the teleop server does with its own."""
    hub = [w.ws for w in app[HUB_DEVICES].windows.values()]
    voice = [link.ws for link in app[BRAIN].voice.links]
    await close_sockets(hub + voice)


async def _quest_view_task(app: web.Application):
    yield
    app[QUEST_VIEW].stop()  # the brain stops: so does its window


async def perf_page(request: web.Request) -> web.FileResponse:
    return await _file(request, "perf.html")


async def api_status(request: web.Request) -> web.Response:
    app = request.app
    brain = app[BRAIN]
    loop: TeleopLoop = app[LOOP]
    return web.json_response(
        {
            "venue": brain.venue.name,
            "visitors": _visitors(brain.venue),  # visitor mode: the cards (quick job 35)
            "persona": brain.persona().public(),
            "internet": brain.internet.online if brain.internet else None,  # None = not known
            "ai": brain.chat.status(),
            "voice": brain.voice.status(),
            "assistant": {  # device: the screen that has the conversation (quick job 58)
                "state": brain.assistant.state,
                "loudness": brain.assistant.loudness,
                "device": brain.assistant.device,
            },
            "arm": {
                "name": loop.arm.name,
                "connected": loop.arm_connected,  # False: its USB was unplugged (quick job 27)
                "control": "ai"
                if loop.motion_active
                else "taken"
                if app[CONTROL].get("ws") is not None
                else "free",
            },
            # two arms at once (teleop only): the left controller's arm, or None
            "left_arm": None
            if loop.left is None
            else {"name": loop.left.arm.name, "connected": loop.left.arm_connected},
            "in_use": in_use(app),
            "time_ms": int(time.time() * 1000),
        }
    )


def lab_status(app: web.Application) -> dict:
    """The lab in one report (quick job 16): only what the brain knows right now; nothing is
    guessed, and what isn't known is left out. For the hub's assistant ("give me a status report")
    and any AI tool (the `lab_status` MCP tool)."""
    brain, loop = app[BRAIN], app[LOOP]
    control = (
        "ai" if loop.motion_active else "teleop" if app[CONTROL].get("ws") is not None else "free"
    )
    arm = {
        "name": loop.arm.name,
        "connected": loop.arm_connected,
        "driven_by": control,
        "held_still": loop.frozen,
        "motion_allowed": brain.venue.motion_allowed,
    }
    warnings = []
    if not loop.arm_connected:
        warnings.append(
            f"{loop.arm.name} is disconnected ({loop.arm_problem}); the brain reconnects when "
            "it's back"
        )
    if loop.left:  # two arms at once: the left controller's arm, teleop only
        left = loop.left
        out_left = {"name": left.arm.name, "connected": left.arm_connected}
        out_left["held_still"] = left.frozen
        arm["left_arm"] = out_left
        if not left.arm_connected:
            warnings.append(
                f"{left.arm.name} is disconnected ({left.arm_problem}); the brain reconnects "
                "when it's back"
            )
    if loop.health:
        hottest = max(h["temp_c"] for h in loop.health.values())
        arm["hottest_servo_c"] = hottest
        if loop.servos_hot:
            warnings.append(f"servos warm ({hottest:.0f} °C): 1:1 teleop is slowed")
    voice = brain.voice.status()
    ai = brain.chat.status()
    out = {
        "venue": brain.venue.name,
        "arm": arm,
        "hub_open_on": [d["name"] for d in app[HUB_DEVICES].listing()],
        "voice": {
            "available": voice["available"],
            "service": voice.get("service"),
            "wake_word": voice["wake"]["available"],
        }
        | ({"why_not": voice["why"]} if voice.get("why") else {}),
        "ai": {"connected": ai["connected"], "setup": ai["setup"], "paused": ai["paused"]},
        "internet": brain.internet.online if brain.internet else None,
    }
    if not brain.venue.hides_spend:  # a public screen or visitors: not what's spent
        m = brain.chat.spend.month()
        out["ai_spend"] = {
            "month": m["month"],
            "spent_usd": round(m["spent_usd"], 2),
            "estimated": True,  # say "about" / "estimated" (quick job 41)
            "counts": "this computer's brain only, not other brains that use the same key",
        } | ({"budget_usd": m["budget_usd"]} if m["budget_usd"] is not None else {})
    nxt = app[TOOLS_PROJECT].project_status().get("next") if TOOLS_PROJECT in app else None
    if nxt:
        out["next_step"] = nxt
    for name in brain.venue.limits_off:
        warnings.append(f"safety limit switched off in this venue: {name}")
    if ai["paused"]:
        warnings.append("the AI chat is paused (the monthly budget)")
    if ai.get("problem"):
        warnings.append(f"AI: {ai['problem']}")
    if out["internet"] is False:
        warnings.append("no internet")
    out["warnings"] = warnings
    return out


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
    # the bottom of the base: above the table when the arm stands on a plate (quick job 28)
    points = [{"name": "base", "r": 0.0, "z": round(-getattr(kin, "table_z_m", 0.0) * 100, 1)}]
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


async def api_arm_cameras(request: web.Request) -> web.Response:
    """The cameras of the arms being driven, for the teleop page's pictures (quick job 63)."""
    loop: TeleopLoop = request.app[LOOP]
    out = []
    for each, side in ((loop, ""), (loop.left, "Left arm: ")):
        if each is None:
            continue
        try:
            names = await asyncio.to_thread(camera_feed.arm_cameras, each.arm.name)
        except config.ConfigError:
            names = []
        out += [{"name": n, "label": side + n.rsplit("-cam-", 1)[-1].title()} for n in names]
    return web.json_response({"arm": loop.arm.name, "cameras": out})


async def api_camera_feed(request: web.Request) -> web.Response:
    """One camera's newest picture (quick job 63). The camera opens on the first request and
    closes IDLE_S after the last; a camera another program has open is refused (409)."""
    name = request.match_info["name"]
    try:
        jpeg = await asyncio.to_thread(request.app[FEEDS].jpeg, name)
    except camera_feed.CameraError as e:
        return web.Response(status=409, text=f"{e}")
    return web.Response(body=jpeg, content_type="image/jpeg", headers={"Cache-Control": "no-store"})


async def _camera_feeds_task(app: web.Application):
    yield
    await asyncio.to_thread(app[FEEDS].close_all)  # the brain stops: so do the cameras


async def api_arm(request: web.Request) -> web.Response:
    """The arm's joints for the hub's readouts (the driver rate-limits real reads)."""
    app = request.app
    loop: TeleopLoop = app[LOOP]
    out = {"name": loop.arm.name, "model": getattr(loop.arm, "model", "unknown")}
    if not loop.arm_connected:  # its USB was unplugged (quick job 27)
        return web.json_response(out | {"connected": False, "problem": loop.arm_problem})
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
            "pages": [{"path": p, "title": t, "line": line} for p, t, line in PAGES],
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
        answer_in = clean_language((body.get("lang") or {}).get("answer"))
        device = str(body.get("device") or "")
    except (ValueError, AttributeError):
        raise web.HTTPBadRequest(text='send {"text": "..."}') from None
    try:
        device = clean_name(device) if device else ""
    except DeviceError:
        device = ""
    resp = web.StreamResponse(headers={"Content-Type": "application/x-ndjson"})
    await resp.prepare(request)
    chat = request.app[BRAIN].chat
    log.info(  # quick job 46: the language setting with each question (not the words)
        "chat: typed question on %s: answers %s",
        device or "a screen",
        LANGUAGES.get(answer_in or "", "any language"),
    )
    async for event in chat.ask(text, pages, answer_in, local=is_local(request), device=device):
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
    if brain.venue.hides_spend:
        return web.json_response({"available": False})  # a public screen or visitors: hidden
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


def _fake_arm_in_use(app: web.Application) -> bool:
    """Someone drives the fake arm, or did a moment ago (a wave between two steps)."""
    loop = app[LOOP]
    return (
        app[CONTROL].get("ws") is not None
        or loop.motion_active
        or loop.inputs.connected
        or time.monotonic() - loop.last_command_t < NEW_ARM_QUIET_S
    )


async def take_new_arm(app: web.Application) -> bool:
    """One look for an SO-101 plugged in since the start (quick job 73). Taken only while
    nobody drives the fake arm; the pages show the new arm by its status. True: taken."""
    loop, find = app[LOOP], app[FIND_ARM]
    if loop.shutting_down or _fake_arm_in_use(app):
        return False
    new = await asyncio.to_thread(find, loop, app[BRAIN].venue)
    if new is None:
        return False
    if loop.shutting_down or _fake_arm_in_use(app):  # someone started driving meanwhile
        await asyncio.to_thread(new.arm.close)
        return False
    old = loop.adopt(new)
    app[TOOLS].use_arm()
    old.close()
    print(f"\n{loop.arm.name} was plugged in: lab-os drives it now, instead of {old.name}.")
    return True


async def _new_arm_task(app: web.Application):
    async def run():
        while True:
            await asyncio.sleep(NEW_ARM_EVERY_S)  # first: the start has just looked
            try:
                if await take_new_arm(app):
                    return
            except Exception:  # a failed look must not end the looking
                log.exception("looking for an arm plugged in since the start")

    task = asyncio.create_task(run()) if app[FIND_ARM] else None
    yield
    if task:
        task.cancel()


async def _adb_reverse_task(app: web.Application):
    rev = app[ADB_REVERSE]

    async def run():
        while True:
            try:
                await asyncio.to_thread(rev.check)
            except Exception:  # a failed look must not end the looking
                log.exception("adb reverse")
            await asyncio.sleep(ADB_EVERY_S)

    task = asyncio.create_task(run()) if rev else None
    yield
    if task:
        task.cancel()


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
        await mcp.shutdown()
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
    quest_view: QuestView | None = None,
    find_arm: Callable | None = None,
    adb_reverse: AdbReverse | None = None,
) -> web.Application:
    """The teleop server with the hub on top. Pass an `InternetCheck` to check in the background,
    and `mcp_port` to offer the robot tools over MCP (calls logged to logs/ai-tools/). `place`:
    default = the active config folder's place.yaml. `local_control_only`: only pages on this
    computer may drive the arm (a real arm served to the network). `recorder`: save the teleop
    input (`lab-os serve --record`). `voices`: the voice setups (default: models.yaml's).
    `device_settings`: where each device's own settings are kept (default: the place's
    local/hub-devices.yaml). `find_arm`: started on the fake arm with no --arm, take an SO-101
    plugged in later (`lab_os.teleop.cli.arm_finder`, quick job 73). `adb_reverse`: run `adb
    reverse` for each Quest connected by USB, also after the cable is plugged in again."""
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
    app[TOOLS_PROJECT] = project
    server = create_mcp_server(app[TOOLS], project)
    add_lab_status(server, lambda: lab_status(app), app[TOOLS].calls)
    app[MCP] = McpHttp(server, mcp_port) if mcp_port else None
    own_place = place is None  # the active place's files: the budget is re-read as it changes
    place = place or config.load_place()
    # the venue now (visitor mode switches it while running), not the one it started with
    persona = persona or (lambda: current_persona(venue=app[BRAIN].venue.name))
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
    visitors = VisitorDesk(
        venue=lambda: app[BRAIN].venue,
        visitors_venue=visitors_venue_name,
        switch=lambda name: switch_venue(app, name),
        facts=lambda v: _facts(app, v),
        wave=lambda: _wave(app),
    )
    chat.actions = Actions(visitors, ArmDesk(app[TOOLS]))  # the arm's: preview 4
    voice = VoiceDesk(
        chat,
        assistant,
        persona,
        internet=lambda: internet.online if internet else None,
        voices=voices or load_voices,
        greeting=lambda: _opening(chat),
        recordings=lambda: config.recordings_dir() / "greetings",
        venue_wake=lambda: app[BRAIN].venue.wake_word_on,
        say=chat.take_say,
    )
    app[BRAIN] = Brain(
        place,
        venue,
        internet,
        assistant,
        focus_file,
        repo,
        chat,
        persona,
        project,
        voice,
        check_ai,
        visitors=visitors,
        started_in=venue.name,
    )
    app[WAVES] = set()
    app[HUB_DEVICES] = HubDevices(
        lambda: {m["id"]: m["title"] for m in hub_modules(load_theme())}, device_settings
    )
    app[QUEST_VIEW] = quest_view or QuestView()
    app[RESTART] = {"asked": False}
    app[FIND_ARM] = find_arm
    app[FEEDS] = camera_feed.FEEDS
    app[ADB_REVERSE] = adb_reverse
    app.router.add_get("/", hub_page)
    app.router.add_get("/plain", plain_page)
    app.router.add_get("/design", design_page)
    app.router.add_get("/ai", ai_page)
    app.router.add_get("/training", training_page)
    app.router.add_get("/xr", xr_page)
    app.router.add_get("/api/green", api_green)
    app.router.add_post("/api/green/start", api_green_start)
    app.router.add_post("/api/green/stop", api_green_stop)
    app.router.add_get("/api/shutdown", api_shutdown_get)
    app.router.add_post("/api/shutdown", api_shutdown)
    app.router.add_post("/api/restart", api_restart)
    app.router.add_get("/api/quest-view", api_quest_view)
    app.router.add_post("/api/quest-view/start", api_quest_view_start)
    app.router.add_post("/api/quest-view/stop", api_quest_view_stop)
    app.router.add_post("/api/window-state", api_window_state)
    app.router.add_get("/settings", settings_page)
    app.router.add_get("/perf", perf_page)
    app.router.add_get("/api/status", api_status)
    app.router.add_get("/api/project", api_project)
    app.router.add_get("/api/commits", api_commits)
    app.router.add_get("/api/arm", api_arm)
    app.router.add_get("/api/arm-cameras", api_arm_cameras)
    app.router.add_get("/api/camera-feed/{name}", api_camera_feed)
    app.router.add_get("/api/pose-view.png", api_pose_view)
    app.router.add_get("/api/devices", api_devices)
    app.router.add_get("/api/ai-calls", api_ai_calls)
    app.router.add_get("/api/settings", api_settings_get)
    app.router.add_post("/api/settings", api_settings_post)
    app.router.add_post("/api/venue", api_venue)
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
    app.cleanup_ctx.append(_quest_view_task)
    app.cleanup_ctx.append(_new_arm_task)
    app.cleanup_ctx.append(_adb_reverse_task)
    app.cleanup_ctx.append(_camera_feeds_task)
    app.on_shutdown.insert(0, _tell_off_on_stop)  # before the teleop server closes its pages
    app.on_shutdown.append(_close_hub_pages)
    return app
