"""The system diagram (quick job 12): drawn from the real facts, so it follows the place's devices.
Runs the hub's own module with node (skipped without node); the hub wiring is checked as text."""

import json
import shutil
import subprocess

import pytest

from lab_os import REPO_ROOT

MODULE = REPO_ROOT / "src/lab_os/hub/web/system-diagram.js"
DESIGN = REPO_ROOT / "src/lab_os/hub/web/design.html"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node isn't installed")

LAB = [
    {"name": "so101-white", "kind": "so101", "linked": True},
    {"name": "so101-green", "kind": "so101", "borrowed": True},
    {"name": "so101-green-leader", "kind": "so101-leader", "borrowed": True},
    {"name": "so101-white-cam-wrist", "kind": "camera"},
    {"name": "so101-green-cam-wrist", "kind": "camera", "borrowed": True},
    {"name": "fake-arm", "kind": "fake"},
    {"name": "quest-b", "kind": "quest"},
]
HUB = [{"name": "desk", "address": "127.0.0.1"}, {"name": "newline", "address": "192.168.1.30"}]
STATUS = {"ai": {"where": "OpenAI", "connected": True}}


def run(expr: str, **data):
    script = (
        f"import({json.dumps(MODULE.as_uri())}).then(m => {{"
        f"const d = {json.dumps(data)};"
        f"console.log(JSON.stringify({expr})); }})"
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def facts(devices=LAB, hub=HUB, status=STATUS, mcp=True):
    return run(
        "m.systemFacts({devices: d.dv, hubDevices: d.hub, status: d.st, mcp: d.mcp, here: 'desk'})",
        dv=devices,
        hub=hub,
        st=status,
        mcp=mcp,
    )


@needs_node
def test_facts_follow_the_place():
    f = facts()
    assert [s["name"] for s in f["screens"]] == ["desk", "newline", "quest-b"]
    desk, newline, quest = f["screens"]
    assert desk["live"] and desk["local"] and desk["here"]
    assert newline["live"] and not newline["local"]
    assert not quest["live"]  # listed, hub not open
    # arms: no leaders, no fake arm unless it's the one driven, the borrowed one last
    assert [a["name"] for a in f["arms"]] == ["so101-white", "so101-green"]
    assert f["arms"][0]["linked"] and f["arms"][1]["borrowed"]
    assert f["cameras"] == {"count": 2, "borrowed": 1}
    assert f["ai"] == {"name": "OpenAI", "connected": True} and f["mcp"] and f["training"]


@needs_node
def test_another_place_draws_what_it_has():
    # a home: a new arm, no SO-101s, no cameras, no AI set up, no robot tools
    f = facts(
        devices=[{"name": "myarm", "kind": "arm", "linked": True}], hub=[], status=None, mcp=False
    )
    assert [a["name"] for a in f["arms"]] == ["myarm"]
    assert f["screens"][0]["name"] == "desk" and f["screens"][0]["here"]  # always this screen
    assert not f["training"] and not f["mcp"] and f["cameras"]["count"] == 0
    svg = run(
        "m.systemSVG(m.systemFacts({devices: d.dv, here: 'desk'}))",
        dv=[{"name": "myarm", "kind": "arm", "linked": True}],
    )
    assert "Myarm" in svg and "SO-101" not in svg and "LeLab" not in svg and "AI tools" not in svg
    assert "Not set up" in svg


@needs_node
def test_only_real_links_pulse():
    svg = run("m.systemSVG(d.f)", f=facts())
    # live: desk, newline, so101-white, the AI; not quest-b, so101-green, the cameras, MCP
    assert svg.count("<animateMotion") == 4
    assert run("m.systemSVG(d.f, {animate: false})", f=facts()).count("<animateMotion") == 0


@needs_node
def test_names_as_people_say_them():
    names = ["desk", "quest-a", "so101-white", "xarm1", "fake-arm", "pi01"]
    got = run("d.n.map(m.displayName)", n=names)
    assert got == ["Desk", "Quest A", "SO-101 White", "xArm 1", "Fake Arm", "Pi 01"]


@needs_node
def test_long_lists_fold():
    many = [{"name": f"arm{i}", "kind": "arm"} for i in range(9)]
    svg = run("m.systemSVG(m.systemFacts({devices: d.dv}))", dv=many)
    assert "+4 more" in svg  # 5 shown, the rest folded


def test_the_hub_opens_it_from_the_devices_panel():
    html = DESIGN.read_text()
    assert 'id="devsys" data-detail="system"' in html
    assert 'system: ["System diagram"' in html
    assert 'import("/hub/system-diagram.js")' in html
