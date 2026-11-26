"""One tap per device (focus step 8): open the hub on this computer as a named device, and the
"Start lab-os" icon for the brain's computer (docs/archive/guides-2026-11-25/hub.md → "Devices").

Nothing starts by itself: the brain's computer gets an icon that starts the brain and opens the
hub (`lab-os serve --open desk`); other computers get a "Lab hub" icon that only opens the hub
(Settings → This device makes one, with the brain's address filled in).

lab-os's hub window is a browser of its own (its own profile folder, `PROFILE`), with the
browser's DevTools port on this computer only. So a second tap on the icon finds that window and
brings it to the front instead of opening another (quick job 59).
"""

import json
import shutil
import subprocess
import sys
import urllib.request
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from lab_os import REPO_ROOT

LINUX_BROWSERS = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "brave-browser",
    "microsoft-edge",
)
MAC_BROWSERS = ("Google Chrome", "Chromium", "Brave Browser", "Microsoft Edge")
WINDOWS_BROWSERS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)
ICON_FILE = "lab-os-start.desktop"
# lab-os's own browser profile: its windows only, so lab-os can find them again
PROFILE = Path.home() / ".cache" / "lab-os" / "hub-browser"


def hub_url(port: int, device: str, host: str = "localhost") -> str:
    return f"http://{host}:{port}/?device={device}"


def browser_command(url: str, profile: Path | None = None) -> list[str] | None:
    """A Chromium-family browser as an app window, full screen, in lab-os's own profile; None
    when there's none. Port 0: the browser picks a free DevTools port (on 127.0.0.1 only) and
    writes it to `DevToolsActivePort` in the profile."""
    own = [
        f"--user-data-dir={profile or PROFILE}",
        "--remote-debugging-port=0",
        "--no-first-run",
        "--no-default-browser-check",
        # sound with no press on this page: a start from another device plays the startup's
        # sound here too (quick job 139)
        "--autoplay-policy=no-user-gesture-required",
    ]
    flags = [f"--app={url}", *own, "--start-fullscreen"]
    if sys.platform == "darwin":
        for app in MAC_BROWSERS:
            if Path(f"/Applications/{app}.app").exists():
                return ["open", "-na", app, "--args", *flags]
        return None
    if sys.platform.startswith("win"):
        found = (p for p in WINDOWS_BROWSERS if Path(p).exists())
        exe = shutil.which("chrome") or next(found, None)
        return [exe, *flags] if exe else None
    exe = next((shutil.which(b) for b in LINUX_BROWSERS if shutil.which(b)), None)
    # Linux: no --start-fullscreen. On GNOME (X11, two monitors) the browser then believed it was
    # full screen while the window kept its title bar, and the hub's start press did nothing.
    # The start press makes it full screen (docs/dev/GOTCHAS.md, 2026-11-20).
    return [exe, f"--app={url}", *own] if exe else None


def open_hub(url: str) -> str:
    """Open the hub here; says how."""
    cmd = browser_command(url)
    if cmd:
        subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
        )
        return f"opened {url} in {Path(cmd[0]).name if cmd[0] != 'open' else cmd[2]}"
    webbrowser.open(url)  # no Chrome-like browser: a normal tab (tap once for full screen)
    return f"opened {url} in the default browser (no Chrome found: tap once for full screen)"


def _devtools(profile: Path | None = None) -> str | None:
    """The address of lab-os's own browser's DevTools, if that browser runs."""
    try:
        port = int(((profile or PROFILE) / "DevToolsActivePort").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return None
    return f"http://127.0.0.1:{port}"


def hub_windows(device: str, port: int, profile: Path | None = None) -> list[dict]:
    """The hub pages that lab-os's own browser shows for this brain, this device's first. Empty
    when that browser doesn't run (a file left behind by a closed browser answers nothing)."""
    base = _devtools(profile)
    if base is None:
        return []
    try:
        with urllib.request.urlopen(f"{base}/json/list", timeout=1.5) as r:
            targets = json.load(r)
    except (OSError, ValueError):
        return []
    pages = []
    for t in targets if isinstance(targets, list) else []:
        url = urlsplit(str(t.get("url", "")))
        local = url.hostname in ("localhost", "127.0.0.1") and url.port == port
        if t.get("type") == "page" and local:
            pages.append(t)
    pages.sort(key=lambda t: parse_qs(urlsplit(t["url"]).query).get("device") != [device])
    return pages


def bring_to_front(device: str, port: int, profile: Path | None = None) -> str | None:
    """Bring lab-os's hub window to the front; None when there's none to bring."""
    pages = hub_windows(device, port, profile)
    base = _devtools(profile)
    if not pages or base is None:
        return None
    try:
        with urllib.request.urlopen(f"{base}/json/activate/{pages[0]['id']}", timeout=1.5):
            pass
    except OSError:
        return None
    return f"brought the hub window to the front ({pages[0]['url']})"


def close_hub_windows(port: int, profile: Path | None = None) -> int:
    """Close every page that lab-os's own browser shows for this brain (Shut down and Ctrl+C,
    quick job 64). Returns how many it closed."""
    base = _devtools(profile)
    closed = 0
    for page in hub_windows("", port, profile) if base else []:
        try:
            with urllib.request.urlopen(f"{base}/json/close/{page['id']}", timeout=1.5):
                closed += 1
        except OSError:
            pass
    return closed


WINDOW_STATES = ("fullscreen", "normal", "keep")
BOUNDS = ("left", "top", "width", "height")


async def set_window_state(
    url: str, state: str, profile: Path | None = None, bounds: dict | None = None
) -> str:
    """Put the window of lab-os's own browser that shows `url` in full screen or back to a window
    (quick job 74): a web page may go full screen only from a press, but the browser's DevTools
    may. With `bounds` ({left, top, width, height}, screen pixels) the window first moves there:
    "Open on…" → another monitor (quick job 138). State "keep": full screen again only if it was.
    Returns "" when done, else why not (a sentence)."""
    import asyncio

    import aiohttp

    if state not in WINDOW_STATES:
        return f"Unknown window state {state!r}."
    if bounds is not None:
        try:
            bounds = {k: int(bounds[k]) for k in BOUNDS}
        except (KeyError, TypeError, ValueError):
            return "Bounds need left, top, width and height."
    try:
        lines = ((profile or PROFILE) / "DevToolsActivePort").read_text().split()
        port, path = int(lines[0]), lines[1]
    except (OSError, ValueError, IndexError):
        return "This page isn't in lab-os's own browser window (the \"Start lab-os\" icon)."
    pages = await asyncio.to_thread(hub_windows, "", urlsplit(url).port or 80, profile)
    # the exact address, else one that grew a hash or more of a query after it opened
    page = next((p for p in pages if p.get("url") == url), None) or next(
        (p for p in pages if str(p.get("url", "")).startswith(url)), None
    )
    if page is None:
        return "This page isn't in lab-os's own browser window (the \"Start lab-os\" icon)."
    try:
        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session,
            session.ws_connect(f"ws://127.0.0.1:{port}{path}") as ws,
        ):
            got = await _cdp(ws, 1, "Browser.getWindowForTarget", targetId=page["id"])
            window = got["windowId"]
            was = got.get("bounds", {}).get("windowState", "normal")
            if was != "normal" and (bounds or (state == "fullscreen" and was == "minimized")):
                # a window moves or leaves "minimized" only from "normal" (the DevTools' rule)
                await _cdp(
                    ws,
                    2,
                    "Browser.setWindowBounds",
                    windowId=window,
                    bounds={"windowState": "normal"},
                )
            if bounds:
                await _cdp(ws, 3, "Browser.setWindowBounds", windowId=window, bounds=bounds)
            if state == "keep":
                state = "fullscreen" if bounds and was in ("fullscreen", "maximized") else ""
            if state:
                await _cdp(
                    ws, 4, "Browser.setWindowBounds", windowId=window, bounds={"windowState": state}
                )
    except (OSError, TimeoutError, aiohttp.ClientError, KeyError, RuntimeError) as e:
        return f"The browser didn't change the window ({e or type(e).__name__})."
    return ""


async def _cdp(ws, n: int, method: str, **params) -> dict:
    """One DevTools call on an open browser connection; its result (RuntimeError: its error)."""
    await ws.send_json({"id": n, "method": method, "params": params})
    while True:
        msg = await ws.receive_json()
        if msg.get("id") == n:
            if "error" in msg:
                raise RuntimeError(msg["error"].get("message", "error"))
            return msg.get("result", {})


def brain_answers(port: int) -> bool:
    """Is a brain already running on this computer at that port?"""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1.5) as r:
            return r.status == 200
    except OSError:
        return False


def start_command(device: str, serve_args: list[str]) -> list[str]:
    """What the "Start lab-os" icon runs: the brain, listening for other devices, then the hub."""
    exe = Path(sys.executable).with_name("lab-os")
    program = str(exe) if exe.exists() else "lab-os"
    args = list(serve_args)
    if "--host" not in args:
        args = ["--host", "0.0.0.0", *args]  # the other devices reach the hub by this computer's IP
    return [program, "serve", "--open", device, *args]


def write_icon(device: str, serve_args: list[str], folder: Path | None = None) -> Path:
    """Linux: the "Start lab-os" app icon (the app list; right-click → Add to Favorites). A
    terminal shows the brain's log; Ctrl+C there (or closing it) stops the brain."""
    folder = folder or Path.home() / ".local" / "share" / "applications"
    folder.mkdir(parents=True, exist_ok=True)
    cmd = " ".join(start_command(device, serve_args))
    path = folder / ICON_FILE
    path.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Start lab-os\n"
        f"Comment=Start the lab's brain and open the hub here as {device}\n"
        f'Exec=gnome-terminal --title "lab-os (the brain)" -- {cmd}\n'
        f"Path={REPO_ROOT}\n"
        "Icon=applications-science\n"
        "Categories=Science;\n"
    )
    path.chmod(0o755)
    return path
