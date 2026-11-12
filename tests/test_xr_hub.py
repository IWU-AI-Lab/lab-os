"""The hub in VR (/xr): its JavaScript modules are all served, and nothing comes from the internet.

The scene itself is tested in a browser with Meta's emulated Quest (iwer; docs/quest-setup.md →
"Testing without a headset"). These checks catch a broken import or a CDN link before that.
"""

import re

from test_hub_server import make_app

IMPORT = re.compile(
    r"""(?:import|export)\s[^;]*?from\s+["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\)"""
)


async def _module_graph(client, entry: str) -> dict[str, str]:
    """Every module reachable from `entry` by static or dynamic imports: url → source."""
    seen: dict[str, str] = {}
    todo = [entry]
    while todo:
        url = todo.pop()
        if url in seen:
            continue
        res = await client.get(url)
        assert res.status == 200, f"{url} is imported but not served"
        seen[url] = await res.text()
        for a, b in IMPORT.findall(seen[url]):
            spec = a or b
            if spec == "three":  # the import map in xr.html
                spec = "/web/vendor/three/three.module.js"
            if spec.startswith("."):
                base = url.rsplit("/", 1)[0]
                parts = []
                for p in f"{base}/{spec}".split("/"):
                    if p == "..":
                        parts.pop()
                    elif p != ".":
                        parts.append(p)
                spec = "/".join(parts)
            if not spec.startswith("/web/vendor/three/"):  # three's own files: vendored, not ours
                todo.append(spec)
    return seen


async def test_the_vr_hub_loads_only_its_own_files(aiohttp_client):
    client = await aiohttp_client(make_app())
    page = await (await client.get("/xr")).text()
    assert '<script type="module" src="/hub/xr-hub.js">' in page
    assert '"three": "/web/vendor/three/three.module.js"' in page
    graph = await _module_graph(client, "/hub/xr-hub.js")
    parts = {"/hub/xr/stars.js", "/hub/xr/core.js", "/hub/xr/ignition.js", "/hub/xr/network.js"}
    assert parts <= set(graph)
    for url, src in [("/xr", page), *graph.items()]:  # works offline: no internet-loaded code
        assert not re.search(r"""["'](https?:)?//""", src), f"{url} loads from the internet"


async def test_the_vr_jump_follows_the_theme_and_keeps_its_stars(aiohttp_client):
    """The jump's timings come from the theme (as on the screen), and the waiting stars are the ones
    that jump: starting it must not re-deal the field, or the lines don't grow out of the stars you
    were looking at (the builder, 2026-11-12)."""
    client = await aiohttp_client(make_app())
    hub = await (await client.get("/hub/xr-hub.js")).text()
    assert "theme.startup?.hyperspace" in hub and "HY.ramp_s" in hub and "HY.brake_s" in hub
    start_jump = hub.split("startJump(now) {", 1)[1].split("\n  }", 1)[0]
    assert "spawn" not in start_jump
    stars = await (await client.get("/hub/xr/stars.js")).text()
    assert "pow(along, 1.8)" in stars  # faint tail → bright head, like design.html's drawStars
