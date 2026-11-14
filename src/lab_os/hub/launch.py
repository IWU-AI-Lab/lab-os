"""One tap per device (focus step 8): open the hub on this computer as a named device, and the
"Start lab-os" icon for the brain's computer (docs/guides/hub.md → "Devices").

Nothing starts by itself: the brain's computer gets an icon that starts the brain and opens the
hub (`lab-os serve --open desk`); other computers get a "Lab hub" icon that only opens the hub
(Settings → This device makes one, with the brain's address filled in).
"""

import shutil
import subprocess
import sys
import urllib.request
import webbrowser
from pathlib import Path

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


def hub_url(port: int, device: str, host: str = "localhost") -> str:
    return f"http://{host}:{port}/?device={device}"


def browser_command(url: str) -> list[str] | None:
    """A Chromium-family browser as an app window, full screen; None when there's none."""
    flags = [f"--app={url}", "--start-fullscreen"]
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
    return [exe, *flags] if exe else None


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
