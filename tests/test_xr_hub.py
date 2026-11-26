"""The hub in VR (/xr): its JavaScript modules are all served, and nothing comes from the internet.

The scene itself is tested in a browser with Meta's emulated Quest (iwer; docs/guides/quest-setup.md
→ "Testing without a headset"). These checks catch a broken import or a CDN link before that.
"""

import json
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
    parts |= {"/static/arm/arm-model.js", "/web/voice.js"}  # the holograms' arm, voice
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
    assert 'r === "power") this.toIgnite()' in press  # ⏻'s menu → "Back to the start screen"
    assert 'r === "exit") this.leave()' in press  # ⏻'s menu → Exit
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
    controller handling): it opens as a module, like Monitor and AI Control (quick job 97; from
    2026-11-21 to 11-23 it left VR for the teleop page). Monitor and AI Control are watch-only
    holograms with STOP; Training (LeLab on the desktop) has no VR version, so no button
    (decision 2026-11-12, the builder)."""
    client = await aiohttp_client(make_app())
    teleop = await (await client.get("/static/xr.js")).text()
    assert "export class TeleopSession" in teleop and "export function armStyle" in teleop
    mods = await (await client.get("/hub/xr/modules.js")).text()
    module = mods.split("export class TeleopModule", 1)[1].split("\n}\n", 1)[0]
    assert 'import("/static/xr.js")' in module and 'getLink("input")' in module
    assert "new TeleopSession(link" in module and "this.style = armStyle()" in module
    assert 'type: "hello"' in module and "deviceName()" in module  # who has control, by name
    assert "this.tele?.end()" in module  # closing it: session_end, the arm freezes
    vr_list = mods.split("export const VR_MODULES = {", 1)[1].split("};", 1)[0]
    assert "teleop" in vr_list and "monitor" in vr_list and "ai:" in vr_list
    assert "training" not in vr_list
    hub = await (await client.get("/hub/xr/hub.js")).text()
    assert "new TeleopModule({ ar: this.ar, refType: this.refType })" in hub
    assert "onTeleop" not in hub
    assert 'getLink("monitor")' in mods and '{ type: "stop" }' in hub
    page = await (await client.get("/xr")).text()
    assert '"three/examples/jsm/"' in page  # the arm's URDF loader needs it
    assert 'id="teleop"' not in page  # the teleop page no longer opens over the VR hub
    main = await (await client.get("/hub/xr-hub.js")).text()
    assert "openTeleop" not in main
    assert "show.hub.module.view.frame(performance.now(), frame, ref)" in main
    assert 'show.hub.module?.id === "teleop" && key === "left") return' in main  # the clutch
    assert "show.hub.closeModule(clockNow())" in main  # leaving VR: the arm freezes


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
    assert 'if (this.mode === "settings") return [this.settings.mesh, this.power.mesh]' in hub
    assert 'else if (this.mode === "settings") this.closeSettings(now)' in hub  # B
    graph = await _module_graph(client, "/hub/xr-hub.js")
    assert "/hub/xr/settings.js" in graph
    page = graph["/hub/xr/settings.js"]
    assert 'fetch("/api/settings"' in page and "setPref(" in page  # the brain's, this device's
    assert '{ id: "device", title: "This Device"' in page
    assert "Change it on a screen" in page  # text, colours and lists: no keyboard in VR


async def test_power_opens_a_menu_with_exit_on_every_page(aiohttp_client):
    """The builder, 2026-11-20: ⏻ on every page of the hub in VR opens a menu with Exit. The
    strip's ⏻ stays pressable on the details pages and Settings; a module's tab has its own ⏻
    (the hub hides while a module is open); the open menu is the only thing to press; B closes
    it."""
    client = await aiohttp_client(make_app())
    hub = await (await client.get("/hub/xr/hub.js")).text()
    assert "if (this.menu.mesh.visible) return [this.menu.mesh]" in hub
    assert "return [this.page.mesh, this.power.mesh]" in hub
    assert "return [this.settings.mesh, this.power.mesh]" in hub
    assert 'if (w.kind === "power") { this.sfx.blip(); this.openMenu(hit.obj)' in hub
    assert "if (this.menu.mesh.visible) return this.closeMenu();" in hub  # B
    mods = await (await client.get("/hub/xr/modules.js")).text()
    assert "export class PowerMenu" in mods and '["exit", "i-headset", "Exit"]' in mods
    assert '{ kind: "power" }' in mods.split("class ModuleTab", 1)[1].split("class ", 1)[0]


QUEST_UA = (
    "Mozilla/5.0 (X11; Linux x86_64; Quest 3) AppleWebKit/537.36 OculusBrowser/38.0 Chrome/130"
)


async def test_a_quest_gets_the_start_page_first(aiohttp_client):
    """The builder, 2026-11-21: a Quest opening the hub gets three choices in the middle (Enter VR,
    Enter AR, the hub in the browser), not the idle page. ?flat=1 is the hub in the browser."""
    client = await aiohttp_client(make_app())
    for path in ("/", "/design"):
        page = await (await client.get(path, headers={"User-Agent": QUEST_UA})).text()
        assert 'id="vr"' in page and 'id="ar"' in page and 'id="flat"' in page, path
        flat = await (await client.get(f"{path}?flat=1", headers={"User-Agent": QUEST_UA})).text()
        assert 'id="vr"' not in flat, path
    desk = await (await client.get("/design")).text()  # a computer: the hub, as before
    assert 'id="vr"' not in desk
    main = await (await client.get("/hub/xr-hub.js")).text()
    assert "Insecure origins treated as secure" in main  # over Wi-Fi: how to make VR possible


async def test_the_hub_installs_as_an_app(aiohttp_client):
    """The builder, 2026-11-21: a bookmark or an app icon instead of typing in the headset."""
    client = await aiohttp_client(make_app())
    res = await client.get("/manifest.webmanifest")
    assert res.status == 200 and res.content_type == "application/manifest+json"
    m = await res.json()
    assert m["start_url"] == "/" and m["display"] == "standalone"
    for icon in m["icons"]:
        assert (await client.get(icon["src"])).status == 200
    for path in ("/", "/design", "/xr"):
        assert 'rel="manifest"' in await (await client.get(path)).text(), path


def test_the_teleop_page_has_the_headset_options():
    """The builder, 2026-11-21: Teleop opens the teleop page on every hub version; there you choose
    relative or 1:1 and the rest, then Enter VR or Enter AR, each doing what it says. Desktop
    control can't be chosen in a headset."""
    from test_hub_server import SRC

    web = SRC / "teleop" / "web"
    page = (web / "index.html").read_text()
    for el in ('id="enter"', 'id="enter-ar"', 'id="mode-set"', 'id="speed-set"', 'id="xr-style"',
               'id="xr-place-reset"'):  # fmt: skip
        assert el in page, el
    xr = (web / "xr.js").read_text()
    assert '"immersive-ar", "This device' in xr and '"immersive-vr", "This device' in xr
    assert "STYLE_KEY" in xr and "localStorage.removeItem(PLACE_KEY)" in xr
    tp = (web / "teleop-page.js").read_text()
    assert "if (isHeadset())" in tp and 'd.dataset.unavailable = "1"' in tp  # test_teleop_buttons


def _options(call: str):
    """Run xr/teleop-options.js (no imports) with node and return what `call` gives."""
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("node isn't installed")
    url = (SRC / "hub/web/xr/teleop-options.js").as_uri()
    script = f"import({json.dumps(url)}).then(m => console.log(JSON.stringify({call})))"
    out = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


STATUS = {"speed_scale": 0.5, "max_speed_scale": 0.8, "mode": "relative",
          "modes": ["relative", "one_to_one"], "one_to_one_deg_per_s": 180}  # fmt: skip


def test_the_vr_teleop_options_are_the_teleop_pages():
    """Quick job 102: the hub's VR and AR Teleop has the Teleop page's options for the headset:
    the speed (5 % a step, up to the venue's cap), relative or 1:1 (only where the brain offers
    it), the 3D arm's look, and putting the 3D arm back."""
    rows = _options(f"m.optionRows({json.dumps(STATUS)}, 'stick')")
    assert [r["key"] for r in rows] == ["speed", "mode", "auto", "style", "place"]
    speed, mode, _, style, _ = rows
    assert speed["value"] == "50%" and speed["can"] == {"minus": True, "plus": True}
    enabled = [c["value"] for c in mode["choices"] if c["enabled"]]
    assert enabled == ["relative", "one_to_one", "hands"]
    assert style["value"] == "stick"
    only = _options(f"m.optionRows({json.dumps(STATUS | {'modes': ['relative']})})")
    assert [c["enabled"] for c in only[1]["choices"]] == [True, False, True]
    assert "1:1 is off in this venue" in only[1]["help"]
    at_cap = _options(f"m.optionRows({json.dumps(STATUS | {'speed_scale': 0.8})})")
    assert at_cap[0]["can"]["plus"] is False
    msg = _options(f"m.optionMessage('speed', 'plus', null, {json.dumps(STATUS)})")
    assert msg == {"type": "set_speed", "speed_scale": 0.55}
    capped = STATUS | {"speed_scale": 0.78}
    assert _options(f"m.optionMessage('speed', 'plus', null, {json.dumps(capped)})") == {
        "type": "set_speed",
        "speed_scale": 0.8,
    }
    assert _options(f"m.optionMessage('mode', 'pick', 'one_to_one', {json.dumps(STATUS)})") == {
        "type": "set_mode",
        "mode": "one_to_one",
    }
    no_1to1 = STATUS | {"modes": ["relative"]}
    assert _options(f"m.optionMessage('mode', 'pick', 'one_to_one', {json.dumps(no_1to1)})") is None
    assert _options("m.optionMessage('speed', 'plus', null, null)") is None  # no brain yet


def _hand_choice(call: str):
    """Run teleop/web/hand-choice.js (no imports) with node and return what `call` gives."""
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("node isn't installed")
    url = (SRC / "teleop/web/hand-choice.js").as_uri()
    script = f"import({json.dumps(url)}).then(m => console.log(JSON.stringify({call})))"
    out = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_hand_control_only_when_you_choose_it():
    """Quick job 114 (the builder, 2026-11-24: "HUGE issue"): putting the controllers down no
    longer switches to the hands by itself. Off by default: the controllers drive, and with them
    down the arm holds still (no hands are sent). Hands is a mode next to Relative and 1:1; a switch
    turns the old automatic change back on."""
    pick = "m.pickSource({}, {}, {})"
    off = '{"hands": false, "auto": false}'
    hands = '{"hands": true, "auto": false}'
    auto = '{"hands": false, "auto": true}'
    assert _hand_choice("m.loadHandChoice(null)") == {"hands": False, "auto": False}
    # (controllers seen, hands seen) → the source that drives
    assert _hand_choice(pick.format("false", "true", off)) == "controllers"  # put down: holds
    assert _hand_choice(pick.format("true", "true", off)) == "controllers"
    assert _hand_choice(pick.format("true", "false", hands)) == "hands"  # controllers do nothing
    assert _hand_choice(pick.format("false", "true", auto)) == "hands"  # the old way
    assert _hand_choice(pick.format("true", "true", auto)) == "controllers"
    assert _hand_choice(pick.format("false", "false", auto)) is None
    xr = (SRC / "teleop/web/xr.js").read_text()
    assert "pickSource(" in xr and "loadHandChoice()" in xr and "setHandChoice(c)" in xr

    rows = _options(f"m.optionRows({json.dumps(STATUS)}, '', {hands})")
    mode, switch = rows[1], rows[2]
    assert mode["value"] == "hands" and "left pinch" in mode["help"]
    assert switch["label"] == "Switch to Hands by Itself" and switch["value"] == "off"
    rows = _options(f"m.optionRows({json.dumps(STATUS)}, '', {auto})")
    assert rows[1]["value"] == "relative" and rows[2]["value"] == "on"
    assert [c["enabled"] for c in rows[1]["choices"]] == [True, True, False]  # auto: no Hands
    assert _options(f"m.optionRows({json.dumps(STATUS)})")[2]["value"] == "off"  # the default
    # Hands drive relative: from 1:1 the brain goes to relative
    one = STATUS | {"mode": "one_to_one"}
    assert _options(f"m.optionMessage('mode', 'pick', 'hands', {json.dumps(one)})") == {
        "type": "set_mode",
        "mode": "relative",
    }
    assert _options(f"m.optionMessage('mode', 'pick', 'hands', {json.dumps(STATUS)})") is None
    after = "m.handChoiceAfter('{}', 'pick', '{}', {})"
    assert _options(after.format("mode", "hands", off)) == {"hands": True, "auto": False}
    assert _options(after.format("mode", "relative", hands)) == {"hands": False, "auto": False}
    assert _options(after.format("auto", "on", hands)) == {"hands": False, "auto": True}
    assert _options(f"m.handChoiceAfter('speed', 'plus', null, {off})") is None
    mods = (SRC / "hub/web/xr/modules.js").read_text()
    assert "handChoiceAfter(" in mods and "this.tele.setHandChoice(choice)" in mods


async def test_the_way_out_of_vr_teleop_is_beside_its_status_box(aiohttp_client):
    """Quick job 102 (the builder did not find a way out): in the VR and AR Teleop, STOP, Options,
    Back and Exit sit under the status box, in the teleop room, where you look while you drive. The
    right controller or right hand points at them (its beam shows while it is on one); the floating
    tab and the Exit at the floor are not shown there. B still closes Teleop."""
    client = await aiohttp_client(make_app())
    graph = await _module_graph(client, "/hub/xr-hub.js")
    assert "/hub/xr/teleop-panel.js" in graph and "/hub/xr/teleop-options.js" in graph
    panel = graph["/hub/xr/teleop-panel.js"]
    for kind in ('kind: "stop"', 'op: "options"', 'kind: "back"', 'kind: "exit"'):
        assert kind in panel, kind
    mods = graph["/hub/xr/modules.js"]
    module = mods.split("export class TeleopModule", 1)[1].split("\n}\n", 1)[0]
    assert "sc.root.add(m)" in module  # in the teleop room, beside the status box
    assert "this.link = link" in module  # STOP on the bar
    assert "this.tele.xrScene.setStyle(" in module and "this.tele.putBack()" in module
    hub = graph["/hub/xr/hub.js"]
    assert 'this.tab.mesh.visible = inModule && this.module?.id !== "teleop"' in hub
    assert 'if (w.kind === "tele" || w.kind === "rasp")' in hub
    main = graph["/hub/xr-hub.js"]
    assert 'this.exit.mesh.visible = P === "hub" && this.hub.module?.id !== "teleop"' in main
    assert 'teleop ? "on-hit" : true' in main
    assert 'show === "on-hit" ? !!found : show' in graph["/hub/xr/pointer.js"]


def test_two_arms_on_every_screen():
    """Quick job 119: with two arms, Monitor in VR shows both arms (each on its own floor grid,
    the left one on your left); the desktop 3D view's grid is under both arms; and on the Monitor
    page the left arm's joints card is built and styled like the right arm's."""
    mods = (SRC / "hub/web/xr/modules.js").read_text()
    holo = mods.split("export class ArmHologram", 1)[1].split("\n}\n", 1)[0]
    assert 'getArmFeed(this.link, "left")' in holo and 'id === "monitor"' in holo
    view = (SRC / "teleop/web/arm/arm-view.js").read_text()
    assert "setGrid(!!models.left)" in view
    page = (SRC / "teleop/web/monitor.html").read_text()
    assert 'class="in gauges" id="joints"' in page and 'class="in gauges" id="joints-left"' in page
    css = (SRC / "teleop/web/pages.css").read_text()
    assert "#joints .joint" not in css and ".gauges .joint" in css
