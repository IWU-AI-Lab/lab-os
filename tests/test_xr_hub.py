"""The hub in VR (/xr): its JavaScript modules are all served, and nothing comes from the internet.

The scene itself is tested in a browser with Meta's emulated Quest (iwer; docs/guides/quest-setup.md
→ "Testing without a headset"). These checks catch a broken import or a CDN link before that.
"""

import re

from test_hub_server import SRC, make_app

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
            if spec == "three" or spec.startswith("three/"):  # the import map in xr.html: vendored
                continue
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
    ours = ("stars", "core", "hub", "panels", "pointer", "modules", "ask")
    parts = {f"/hub/xr/{m}.js" for m in ours}
    parts |= {"/static/xr.js", "/static/arm/arm-model.js", "/web/voice.js"}  # teleop, arm, voice
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


async def test_the_trigger_presses_what_you_point_at(aiohttp_client):
    """On the hub the trigger no longer replays the jump (the builder, 2026-11-12): it presses what
    the controller or hand points at; only ⏻ goes back to the start screen."""
    client = await aiohttp_client(make_app())
    hub = await (await client.get("/hub/xr-hub.js")).text()
    press = hub.split("press(now, hit) {", 1)[1].split("\n  }", 1)[0]
    assert 'this.hub.press(hit, now) === "power"' in press
    assert press.count("this.toIgnite()") == 1
    assert "e.inputSource.handedness" in hub  # each controller presses what its own ray is on


async def test_the_vr_callouts_read_the_same_facts_as_the_screen(aiohttp_client):
    client = await aiohttp_client(make_app())
    hub = await (await client.get("/hub/xr-hub.js")).text()
    for api in ("/api/project", "/api/spend", "/api/commits?days=30", "/api/devices"):
        assert api in hub, api
    panels = await (await client.get("/hub/xr/panels.js")).text()
    for title in ("Current Project", "AI Spend", "Commits", "Devices"):
        assert title in (await (await client.get("/hub/xr/hub.js")).text()), title
    assert "get available()" in panels  # hidden when the brain has no facts


async def test_the_vr_modules(aiohttp_client):
    """Teleop runs the teleop page's own XR session code inside the hub's session (one copy of the
    controller handling); Monitor and AI Control are watch-only holograms with STOP; Training
    (LeLab on the desktop) has no VR version, so no button (decision 2026-11-12, the builder)."""
    client = await aiohttp_client(make_app())
    teleop = await (await client.get("/static/xr.js")).text()
    assert "export class TeleopSession" in teleop and "new TeleopSession(link" in teleop
    mods = await (await client.get("/hub/xr/modules.js")).text()
    assert 'import("/static/xr.js")' in mods and 'new TeleopSession(getLink("input")' in mods
    vr_list = mods.split("export const VR_MODULES = {", 1)[1].split("};", 1)[0]
    assert "teleop" in vr_list and "monitor" in vr_list and "ai:" in vr_list
    assert "training" not in vr_list
    assert 'getLink("monitor")' in mods and '{ type: "stop" }' in (
        await (await client.get("/hub/xr/hub.js")).text()
    )
    page = await (await client.get("/xr")).text()
    assert '"three/examples/jsm/"' in page  # the arm's URDF loader needs it


async def test_asking_in_vr(aiohttp_client):
    """Push-to-talk on the ask line (hold the trigger), the wake word on the headset's microphone,
    and turns heard by another screen shown too (decision 2026-11-12, the builder)."""
    client = await aiohttp_client(make_app())
    hub = await (await client.get("/hub/xr-hub.js")).text()
    assert '"selectstart"' in hub and '"selectend"' in hub and "ask.pressStart(" in hub
    ask = await (await client.get("/hub/xr/ask.js")).text()
    assert 'import("/web/voice.js")' in ask and 'V.press("ask")' in ask
    assert "this.V.wake(" in ask and 'fetch("/api/chat"' in ask
    # the microphone is asked for on the page, not in VR (a prompt there is easy to miss) and not
    # right before requestSession (it would use up the click that enters VR)
    before = hub.split("navigator.xr.requestSession(", 1)[0].rsplit("async function start(", 1)[1]
    assert "getUserMedia" not in before
    assert "Allow the microphone" in hub


def test_glows_never_cover_the_room_in_ar():
    """Quick job 10: additive blending also wrote opacity, so in AR a dim or black glow (the
    network's links waiting before the jump, faint stars) covered the room as a dark clump. Every
    glow uses GLOW (xr/draw.js), which adds light and leaves the opacity alone."""
    xr = SRC / "hub/web/xr"
    draw = (xr / "draw.js").read_text()
    assert "blendSrcAlpha: THREE.ZeroFactor, blendDstAlpha: THREE.OneFactor" in draw
    for f in sorted(xr.glob("*.js")):
        assert "AdditiveBlending" not in f.read_text(), f"{f.name}: use GLOW from draw.js"


async def test_the_vr_hub_turns_off_when_the_brain_does_not_answer(aiohttp_client):
    """Quick job 78 (lab check S.4): a Quest that missed the "brain_off" message could still
    start the startup and open an empty hub. The hub in VR now also turns off when the brain
    doesn't answer: when you enter VR or AR, at a press after a quiet time, and after two failed
    status reads."""
    client = await aiohttp_client(make_app())
    hub = await (await client.get("/hub/xr-hub.js")).text()
    press = hub.split("press(now, hit) {", 1)[1].split("\n  }\n", 1)[0]
    # Exit works even when lab-os is off; nothing else does; an unsure press asks the brain first
    assert press.index('"exit"') < press.index("if (this.off) return")
    assert press.index("this.unsure()") < press.index('this.phase === "ignite"')
    assert 'getJSON("/api/status")' in press and "turnOff({ lost: true })" in press
    assert "++show.misses >= LOST_READS" in hub  # the background check, in poll()
    assert "if (!show.facts.status) show.turnOff({ lost: true })" in hub  # entering with no brain
    assert "AbortSignal.timeout(" in hub  # a read can't hang
    off = await (await client.get("/hub/xr/off.js")).text()
    assert "lab-os is not reachable" in off and "new ExitButton()" in off


async def test_exit_is_on_every_page_of_the_vr_hub(aiohttp_client):
    """Quick job 78: Exit leaves VR or AR; it sits on the stage (not in the hub's group, which a
    module hides) and is a target on every page."""
    client = await aiohttp_client(make_app())
    hub = await (await client.get("/hub/xr-hub.js")).text()
    assert "this.stage.add(this.exit.mesh)" in hub
    assert "[...this.hub.targets(), this.exit.mesh]" in hub
    assert "session.end()" in hub
    mods = await (await client.get("/hub/xr/modules.js")).text()
    assert "export class ExitButton" in mods and 'kind: "exit"' in mods


async def test_settings_in_vr_and_a_larger_hub(aiohttp_client):
    """Quick job 60: ⚙ in the strip opens Settings in VR, with the screens' groups (This Device
    first, then the brain's sections from /api/settings), saved through the same APIs; Back or B
    closes it. The whole hub is ~15 % larger, with the core at its distance."""
    client = await aiohttp_client(make_app())
    hub = await (await client.get("/hub/xr/hub.js")).text()
    assert "export const HUB_SCALE = 1.15" in hub and "this.group.scale.setScalar(HUB_SCALE)" in hub
    assert 'kind: "settings"' in hub and "this.openSettings(now)" in hub
    assert 'if (this.mode === "settings") return [this.settings.mesh]' in hub
    assert 'else if (this.mode === "settings") this.closeSettings(now)' in hub  # B
    graph = await _module_graph(client, "/hub/xr-hub.js")
    assert "/hub/xr/settings.js" in graph
    page = graph["/hub/xr/settings.js"]
    assert 'fetch("/api/settings"' in page and "setPref(" in page  # the brain's, this device's
    assert '{ id: "device", title: "This Device"' in page
    assert "Change it on a screen" in page  # text, colours and lists: no keyboard in VR
