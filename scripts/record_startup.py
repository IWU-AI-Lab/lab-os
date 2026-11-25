"""Record the designed hub's startup as a video (quick job 34;
docs/archive/guides-2026-11-25/hub.md, "Startup as a
video"). The design stays the source: record again whenever the startup changes.

    uv run lab-os serve --port 8090 --mcp-port 0    # a brain to record from (its chat is reset)
    uv run --with playwright python scripts/record_startup.py --url http://localhost:8090

Needs Google Chrome and ffmpeg (with libvpx-vp9). The page runs in slow motion (its clock, timers,
CSS animations and videos SLOW times slower) while Chrome's screencast captures its frames, so the
recording is smooth whatever the computer; the frames are then put back at 60 a second. The words
are hidden: the hub types them live. Writes src/lab_os/hub/web/media/startup-<quality>.webm and
.json (what it was recorded with: the page plays the video only while these still match the theme).
--quality full (the default) or maximal: the hub plays the one matching the device's detail level.

    --compare OUT.mp4   instead: the startup drawn live (left) and as the video (right), words
                        included, side by side (needs a recording already)
"""

import argparse
import asyncio
import base64
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
from datetime import date
from pathlib import Path

from playwright.async_api import async_playwright

MEDIA = Path(__file__).resolve().parents[1] / "src/lab_os/hub/web/media"
FPS = 60
SLOW = 8
UNLOCK_MS = 1350  # design.html: the unlock before the startup begins
IMPACT_MS = 80
SETTLE_MS = 200  # after the core's arrival, before the live hub takes over

# The page's clock, timers and videos SLOW times slower (CSS animations: Animation.setPlaybackRate).
# One drawn frame per K of the browser's, stamped with the slowed clock (Chrome's own frame times
# are already slowed by setPlaybackRate): each frame then steps 1/60 s as at full speed, so what the
# page draws from the step (the jump's streaks) looks the same.
SLOW_JS = """(() => {
  const K = __SLOW__, pn = performance.now.bind(performance), base = pn();
  performance.now = () => base + (pn() - base) / K;
  const dn = Date.now, dbase = dn();
  Date.now = () => dbase + (dn() - dbase) / K;
  const raf = window.requestAnimationFrame.bind(window);
  let queue = new Map(), id = 0, tick = 0;
  (function pump() {
    if (++tick % K === 0 && queue.size) {
      const now = performance.now(), q = queue;
      queue = new Map();
      q.forEach((cb) => cb(now));
    }
    raf(pump);
  })();
  window.requestAnimationFrame = (cb) => { queue.set(++id, cb); return id; };
  window.cancelAnimationFrame = (n) => { queue.delete(n); };
  const st = window.setTimeout.bind(window), si = window.setInterval.bind(window);
  window.setTimeout = (f, ms, ...a) => st(f, (ms || 0) * K, ...a);
  window.setInterval = (f, ms, ...a) => si(f, (ms || 0) * K, ...a);
  const play = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function () {
    this.playbackRate = 1 / K;
    return play.call(this);
  };
})();"""
NO_WORDS = (
    "#boot-title-wrap, #boot-greet, #bootlines, #ignite .stack, #ignite .ign-foot"
    " { visibility: hidden !important; }"
)


def theme_numbers(url: str) -> dict:
    """What the page's startup is made of (the same defaults as design.html's HYPER)."""
    t = json.load(urllib.request.urlopen(f"{url}/theme.json"))
    hy = (t.get("startup") or {}).get("hyperspace") or {}
    return {
        "ramp_ms": round((hy.get("ramp_s") or 2.0) * 1000),
        "hold_ms": round((hy.get("hold_s") or 0.7) * 1000),
        "brake_ms": round((hy.get("brake_s") or 2.6) * 1000),
        "impact": hy.get("impact_frame") is not False,
        "primary": str((t.get("colors") or {}).get("primary") or "#29d4ff").lower(),
    }


def set_device(url: str, name: str, video: bool) -> None:
    body = json.dumps({"startup_video": True if video else ""}).encode()
    req = urllib.request.Request(
        f"{url}/api/hub-devices/{name}/settings", body, {"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req).read()


async def capture(
    page_url: str, size: tuple[int, int], ms: int, words: bool, out_dir: Path
) -> None:
    """Press start and keep `ms` of the startup as FPS frames f00000.jpg … in `out_dir`."""
    w, h = size
    frames: list[tuple[float, bytes]] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome")
        page = await browser.new_page(viewport={"width": w, "height": h})
        await page.add_init_script(SLOW_JS.replace("__SLOW__", str(SLOW)))
        await page.goto(page_url)
        await page.wait_for_timeout(5000)  # the theme, the brain's facts, the video (real time)
        if not words:
            await page.add_style_tag(content=NO_WORDS)
        cdp = await page.context.new_cdp_session(page)
        await cdp.send("Animation.enable")
        await cdp.send("Animation.setPlaybackRate", {"playbackRate": 1 / SLOW})

        def on_frame(ev):
            frames.append((ev["metadata"]["timestamp"], base64.b64decode(ev["data"])))
            asyncio.ensure_future(
                cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
            )

        cdp.on("Page.screencastFrame", on_frame)
        await cdp.send(
            "Page.startScreencast",
            {"format": "jpeg", "quality": 92, "maxWidth": w, "maxHeight": h, "everyNthFrame": 1},
        )
        await page.wait_for_timeout(1500)
        pressed = time.time()
        await page.mouse.click(w / 2, h * 0.8)
        await page.wait_for_timeout(ms * SLOW + 1500)
        await cdp.send("Page.stopScreencast")
        await browser.close()
    # back to real time: each output frame shows the last captured one at or before its moment
    timed = sorted(((ts - pressed) * 1000 / SLOW, jpg) for ts, jpg in frames)
    print(f"  {len(timed)} frames captured for {ms} ms of startup")
    j = 0
    for i in range(ms * FPS // 1000):
        t = i * 1000 / FPS
        while j + 1 < len(timed) and timed[j + 1][0] <= t:
            j += 1
        (out_dir / f"f{i:05d}.jpg").write_bytes(timed[j][1])


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


async def record(url: str, size: tuple[int, int], quality: str) -> None:
    nums = theme_numbers(url)
    handoff = (
        UNLOCK_MS
        + nums["ramp_ms"]
        + nums["hold_ms"]
        + (IMPACT_MS if nums["impact"] else 0)
        + nums["brake_ms"]
        + SETTLE_MS
    )
    with tempfile.TemporaryDirectory() as tmp:
        print(f"recording {handoff + 500} ms of the startup at {size[0]}×{size[1]} …")
        await capture(
            f"{url}/design?sound=0&quality={quality}&startup=hyperspace",
            size,
            handoff + 500,
            False,
            Path(tmp),
        )
        MEDIA.mkdir(exist_ok=True)
        video = MEDIA / f"startup-{quality}.webm"
        ffmpeg(
            "-framerate", str(FPS), "-i", f"{tmp}/f%05d.jpg",
            "-c:v", "libvpx-vp9", "-crf", "48", "-b:v", "0", "-row-mt", "1", "-pix_fmt", "yuv420p",
            str(video),
        )  # fmt: skip
    meta = {
        "file": video.name,
        "width": size[0],
        "height": size[1],
        "quality": quality,
        "startup": "hyperspace",
        **nums,
        "handoff_ms": handoff,
        "recorded": date.today().isoformat(),
    }
    video.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"wrote {video} ({video.stat().st_size / 1e6:.1f} MB) and its .json")


async def compare(url: str, size: tuple[int, int], out: Path, quality: str, ms=11000) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for name, video in (("live", False), ("video", True)):
            print(f"recording the startup {name} …")
            set_device(url, f"rec-{name}", video)
            d = Path(tmp) / name
            d.mkdir()
            page = f"{url}/design?sound=0&quality={quality}&device=rec-{name}"
            await capture(page, size, ms, True, d)
        half = f"scale={size[0] // 2}:-2"
        ffmpeg(
            "-framerate", str(FPS), "-i", f"{tmp}/live/f%05d.jpg",
            "-framerate", str(FPS), "-i", f"{tmp}/video/f%05d.jpg",
            "-filter_complex", f"[0]{half}[a];[1]{half}[b];[a][b]hstack",
            "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(out),
        )  # fmt: skip
    print(f"wrote {out}: left drawn live, right the video")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8080", help="a running brain")
    ap.add_argument("--size", default="1920x1080", help="the screen it's for (the lab desktop's)")
    ap.add_argument("--quality", default="full", choices=("full", "maximal"), help="detail level")
    ap.add_argument("--compare", type=Path, help="write a side-by-side comparison here instead")
    a = ap.parse_args()
    if not shutil.which("ffmpeg"):
        raise SystemExit("needs ffmpeg")
    size = tuple(int(n) for n in a.size.split("x"))
    asyncio.run(
        compare(a.url, size, a.compare, a.quality) if a.compare else record(a.url, size, a.quality)
    )


if __name__ == "__main__":
    main()
