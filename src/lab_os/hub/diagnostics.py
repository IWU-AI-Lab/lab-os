"""Diagnostics for every device (quick job 135): one list with a panel for each device, made to fit
its kind, for the Diagnostics page (`/diagnostics`; `?device=` shows one device).

- **An arm** the brain drives: each motor's position, temperature, load, voltage and error flags
  (the teleop loop reads the servos every few seconds; the fake arm has no motors to read).
- **A camera:** its picture rate and size while it is open (it opens while a page shows it).
- **The Raspbot:** the connection (a diagnostics question and its answer, in ms), the Pi's power
  (the board has no battery reading: a low battery shows as under-voltage at the Pi), its 5 V
  input, temperature and Wi-Fi, the distance, the motion and the control.
- **A screen** (a computer with the hub open): each window's monitor, resolution and page.
- **The others** (the Quest, a USB device): what the live list knows.

Only reads: nothing here changes a device. Every device of the live list is in it, the ones off
now too (with when they were last seen).
"""

import time

from aiohttp import web

from lab_os.hub.live_devices import LiveDevices
from lab_os.robots.fake import FakeArm

# a Feetech servo's status register (STS3215): one bit for each error
STATUS_BITS = ("voltage", "sensor", "temperature", "current", "angle", "overload")
WARM_C = 50.0  # a motor this warm is worth a look; HOT_C (teleop.loop) slows 1:1 down
ORDER = ("arm", "leader", "robot", "camera", "screen", "headset", "usb")


def status_errors(status: int | None) -> list[str]:
    """The servo's error flags as words ("temperature", "overload")."""
    if not status:
        return []
    return [name for bit, name in enumerate(STATUS_BITS) if status & (1 << bit)]


def arm_panel(each, now: float | None = None) -> dict:
    """An arm the brain drives (a teleop loop): its motors."""
    from lab_os.teleop.loop import HOT_C

    now = time.monotonic() if now is None else now
    arm = each.arm
    fake = isinstance(arm, FakeArm)
    joints = dict(getattr(each, "_last_joints", None) or {})
    health = each.health or {}
    motors = []
    for j in arm.joint_names:
        h = health.get(j, {})
        temp = h.get("temp_c")
        errors = status_errors(h.get("status"))
        state = (
            "bad"
            if errors or (temp is not None and temp >= HOT_C)
            else "warn"
            if temp is not None and temp >= WARM_C
            else "ok"
        )
        motors.append(
            {
                "joint": j,
                "position_deg": None if j not in joints else round(float(joints[j]), 1),
                "temp_c": temp,
                "load_pct": h.get("load_pct"),
                "volts": h.get("volts"),
                "errors": errors,
                "state": state if h else "",
            }
        )
    read_at = getattr(each, "_health_t", 0.0)
    return {
        "model": getattr(arm, "model", ""),
        "fake": fake,
        "connected": each.arm_connected,
        "problem": each.arm_problem or "",
        "frozen": each.frozen,
        "health": "none"
        if fake or not hasattr(arm, "read_health")
        else "no_answer"
        if each.health_ok is False
        else "ok"
        if each.health_ok
        else "waiting",
        "read_s_ago": round(now - read_at, 1) if each.health and read_at else None,
        "motors": motors,
    }


def raspbot_panel(desk) -> dict:
    bot = desk.bot
    status = desk.status()
    return {
        "fake": bot.is_fake,
        "connected": bot.connected,
        "address": getattr(bot, "host", ""),
        "round_trip_ms": getattr(bot, "round_trip_ms", None),
        "message": status.get("message", ""),
        "pi": dict(getattr(bot, "pi", {}) or {}),
        "distance_mm": status.get("distance_mm"),
        "moving": status.get("moving", ""),
        "control": status.get("control", ""),
        "camera": status.get("camera", False),
        "speed": status.get("speed"),
    }


def screen_panel(screen: dict) -> dict:
    wins = []
    for w in screen.get("windows", []):
        s = w.get("screen") or {}
        ratio = s.get("ratio") or 1
        wins.append(
            {
                "label": w.get("label", ""),
                "width": round((s.get("width") or 0) * ratio),
                "height": round((s.get("height") or 0) * ratio),
                "stage": w.get("stage", ""),
                "showing": (w.get("showing") or {}).get("title", ""),
            }
        )
    return {
        "address": screen.get("address", ""),
        "here": screen.get("here", False),
        "windows": wins,
    }


def collect(app: web.Application, keys: dict) -> list[dict]:
    """Every device, each with its panel. `keys`: the app keys (to keep the imports one way)."""
    out: list[dict] = []
    have: set[str] = set()
    loop = app[keys["loop"]]
    for each in (loop, getattr(loop, "left", None)):
        if each is None:
            continue
        name = each.arm.name
        have.add(name)
        panel = arm_panel(each)
        out.append(
            {
                "id": name,
                "name": name,
                "kind": "arm",
                "connected": panel["connected"],
                "what": "The fake arm (no arm plugged in)." if panel["fake"] else "",
                "panel": panel,
            }
        )
    desk = app.get(keys["raspbot"])
    if desk is not None:
        panel = raspbot_panel(desk)
        name = desk.bot.name
        have.add(name)
        out.append(
            {
                "id": name,
                "name": name,
                "kind": "robot",
                "connected": panel["connected"],
                "what": "",
                "panel": panel,
            }
        )
    screens = {s["name"]: s for s in app[keys["hub_devices"]].listing()}
    feeds = app.get(keys["feeds"])
    live: LiveDevices = app[keys["live"]]
    for d in live.listing():
        if d["id"] in have:
            continue
        kind = "leader" if d.get("leader") else d.get("kind") or "usb"
        entry = {
            "id": d["id"],
            "name": d.get("name") or d["id"],
            "kind": kind,
            "connected": d.get("connected", False),
            "what": (d.get("problem") or d.get("what") or "") if d.get("connected") else "",
            "bad": bool(d.get("problem")),
            "via": d.get("via", ""),
            "last_seen": "" if d.get("connected") else d.get("last_seen", ""),
            "panel": {},
        }
        if kind == "screen":
            name = d["id"].removeprefix("screen:")
            entry["id"] = name
            if name in screens:
                entry["panel"] = screen_panel(screens[name])
        elif kind == "camera" and feeds is not None:
            entry["panel"] = {"open": False}
            stats = feeds.stats(entry["name"]) or feeds.stats(d["id"])
            if stats:
                entry["panel"] = {"open": True, **stats}
        out.append(entry)
    rank = {k: i for i, k in enumerate(ORDER)}
    out.sort(key=lambda e: (not e["connected"], rank.get(e["kind"], len(ORDER)), e["name"]))
    return out
