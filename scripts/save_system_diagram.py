"""Save the hub's system diagram as an SVG file for the docs (quick job 12;
docs/archive/guides-2026-11-25/hub.md,
"System diagram"). The hub draws it live from the brain's facts; this keeps a copy of what it shows.

    uv run lab-os serve --port 8090 --mcp-port 8091    # a brain to draw from (its devices.yaml)
    uv run --with playwright python scripts/save_system_diagram.py --url http://localhost:8090

Needs Google Chrome. Draws it in the brain's own page with hub/system-diagram.js, the icons copied
in, no pulses, the theme's colours written in (a file has no page around it), and writes
docs/dev/system-diagram.svg (or --out).
"""

import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

REPO = Path(__file__).resolve().parents[1]

DRAW = """async () => {
  const m = await import('/hub/system-diagram.js');
  const j = (u) => fetch(u).then((r) => r.json());
  const [dv, hd, st, calls] = await Promise.all([j('/api/devices'), j('/api/hub-devices'),
    j('/api/status'), j('/api/ai-calls')]);
  const facts = m.systemFacts({ devices: dv.devices, hubDevices: hd.devices, status: st,
    mcp: !!calls.mcp });
  const icons = (id) => document.getElementById(id)?.outerHTML || '';
  let svg = m.systemSVG(facts, { animate: false, icons });
  // the page's CSS variables → their values: the file has no page around it
  const cs = getComputedStyle(document.documentElement);
  svg = svg.replace(/var\\((--[a-z0-9-]+)(?:, ([^()]*(?:\\([^()]*\\))?[^()]*))?\\)/g,
    (all, name, fallback) => cs.getPropertyValue(name).trim() || fallback || all);
  return svg.replace('class="sysdiag"', 'class="sysdiag" style="background:#05080b"');
}"""


async def main(url: str, out: Path) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome")
        page = await browser.new_page()
        await page.goto(f"{url}/design")
        svg = await page.evaluate(DRAW)
        await browser.close()
    out.write_text(svg + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default="http://localhost:8080", help="a running brain")
    ap.add_argument("--out", type=Path, default=REPO / "docs" / "dev" / "system-diagram.svg")
    args = ap.parse_args()
    asyncio.run(main(args.url.rstrip("/"), args.out))
