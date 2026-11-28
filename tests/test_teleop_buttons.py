"""The Arm Control page's buttons (quick job 87): a headset is told by its browser, so a desktop
with the WebXR emulator keeps Desktop control; the order is Desktop control, Enter AR, Enter VR,
and the control settings are in their own Controls box. Runs the page's module with node;
skipped without node."""

import json
import shutil
import subprocess

import pytest

from lab_os import REPO_ROOT

WEB = REPO_ROOT / "src/lab_os/teleop/web"
NODE = shutil.which("node")
QUEST_UA = "Mozilla/5.0 (X11; Linux x86_64; Quest 3) AppleWebKit/537.36 OculusBrowser/38.0"
MAC_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131"


def headset(ua: str, xr: str = "native", platform: str | None = None) -> bool:
    """`xr`: "native" (the browser's own WebXR), "emulated" (a JavaScript copy) or "none"."""
    xr_js = {
        "native": "{ requestSession: Math.max }",  # a built-in: "[native code]"
        "emulated": "{ requestSession: function requestSession() { return 1; } }",
        "none": "undefined",
    }[xr]
    data = f"{{ platform: {json.dumps(platform)} }}" if platform else "undefined"
    script = (
        f"import({json.dumps((WEB / 'headset.js').as_uri())}).then(m => console.log(JSON.stringify("
        f"m.isHeadset({{ userAgent: {json.dumps(ua)}, xr: {xr_js}, userAgentData: {data} }}))))"
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.skipif(NODE is None, reason="node isn't installed")
def test_a_quest_is_a_headset():
    assert headset(QUEST_UA) is True
    assert headset(QUEST_UA, platform="Android") is True


@pytest.mark.skipif(NODE is None, reason="node isn't installed")
def test_a_desktop_is_not_a_headset_even_with_the_emulator():
    assert headset(MAC_UA) is False
    assert headset(MAC_UA, xr="none") is False
    # lab check L.5: the emulator gives the page a Quest's browser name and its own WebXR
    assert headset(QUEST_UA, xr="emulated") is False
    assert headset(QUEST_UA, platform="macOS") is False


def test_the_buttons_order_and_the_controls_box():
    page = (WEB / "index.html").read_text()
    order = [page.index(f'id="{i}"') for i in ("desktop", "enter-ar", "enter", "desk-help")]
    assert order == sorted(order)
    box = page.split('id="desk-help"', 1)[1].split("</details>", 1)[0]
    assert "<summary>Controls</summary>" in box
    for setting in ("speed-set", "mode-set", "xr-style", "desk-mode", "desk-sens"):
        assert f'id="{setting}"' in box, setting
    assert 'id="desk-controls"' not in page  # Controls is its own box now, not a button
