"""The project helper (step 6): read tools for the docs, git and devices; the same tools over MCP;
the hub chat using them (read only). No internet: a fake OpenAI-style service."""

import json
import subprocess
from pathlib import Path

import pytest
from aiohttp import web
from mcp.server.mcpserver.exceptions import ToolError

from lab_os.ai.assistant import Assistant
from lab_os.ai.chat import MAX_TOOL_ROUNDS, Conversation
from lab_os.ai.models import Setup
from lab_os.ai.spend import SpendLog
from lab_os.ai.tools import ChatTools
from lab_os.robots.fake import FakeArm
from lab_os.teleop.loop import InputState, TeleopLoop
from lab_os.tools.mcp_server import create_mcp_server
from lab_os.tools.project import MAX_CHARS, NotFound, ProjectTools
from lab_os.tools.robot import RobotTools
from lab_os.venues import Venue

REPO = Path(__file__).resolve().parents[1]
VENUE = Venue("test", ("fake-arm",), True, 0.5)
READ_TOOLS = {
    "project_status",
    "list_docs",
    "read_doc",
    "search_docs",
    "git_status",
    "git_log",
    "list_devices",
    "arm_status",
    "list_poses",
}


@pytest.fixture
def repo(tmp_path):
    """A tiny project: docs (one design doc), README, two commits."""
    (tmp_path / "docs" / "design").mkdir(parents=True)
    (tmp_path / "docs" / "current-focus.md").write_text(
        "# Current Focus: tiny\n## Steps\n1. **First** (done 2026-11-01).\n2. **Second.** x\n"
    )
    (tmp_path / "docs" / "ideas.md").write_text(
        "# Ideas\n## On hold\n- The router.\n- Roll call.\n## Later\n- Voice wake word.\n"
        "```\n# not a heading\n```\n"
    )
    (tmp_path / "docs" / "design" / "DESIGN.md").write_text("# The design\n")
    (tmp_path / "docs" / "long.md").write_text("# Long\n## Part A\n" + "a" * (MAX_CHARS + 50))
    (tmp_path / "README.md").write_text("# Tiny project\n")
    git = ["git", "-C", str(tmp_path), "-c", "user.name=T", "-c", "user.email=t@example.com"]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "First commit"], check=True)
    (tmp_path / "docs" / "ideas.md").write_text("# Ideas\n## On hold\n- The router.\n")
    subprocess.run([*git, "commit", "-q", "-am", "Ideas: trim"], check=True)
    (tmp_path / "scratch.txt").write_text("x")
    return tmp_path


def robot_tools():
    arm = FakeArm()
    arm.connect()
    return RobotTools(TeleopLoop(arm=arm, inputs=InputState()), VENUE, {}, poses={})


# ---------- the tools ----------


def test_docs_are_listed_with_the_design(repo):
    names = [d["name"] for d in ProjectTools(repo).list_docs()["docs"]]
    assert names == ["current-focus", "design/DESIGN", "ideas", "long", "README"]
    assert ProjectTools(repo).read_doc("design/DESIGN")["text"] == "# The design\n"  # no surprise


def test_read_doc_whole_section_and_cut_off(repo):
    tools = ProjectTools(repo)
    assert tools.read_doc("docs/ideas.md")["text"].startswith("# Ideas")  # any spelling works
    part = tools.read_doc("IDEAS", section="on hold")
    assert part["text"] == "## On hold\n- The router."
    long = tools.read_doc("long")
    assert long["truncated"] and len(long["text"]) == MAX_CHARS
    assert long["sections"] == ["Long", "Part A"]
    with pytest.raises(NotFound, match="sections"):
        tools.read_doc("ideas", section="nope")


def test_search_docs(repo):
    hits = ProjectTools(repo).search_docs("router")["hits"]
    assert hits == [{"doc": "ideas", "line": 3, "heading": "On hold", "text": "- The router."}]
    with pytest.raises(NotFound):
        ProjectTools(repo).search_docs("x")


def test_project_status(repo):
    st = ProjectTools(repo).project_status()
    assert st["focus"] == "Tiny" and st["step"] == 2 and st["next"] == "Second"
    assert st["steps"][0]["done_on"] == "2026-11-01"


def test_git(repo):
    tools = ProjectTools(repo)
    st = tools.git_status()
    assert st["branch"] == "main" and st["changed"] == ["?? scratch.txt"]
    assert st["last_commit"].endswith("Ideas: trim")
    log = tools.git_log()["commits"]
    assert [c["subject"] for c in log] == ["Ideas: trim", "First commit"]
    assert log[0]["author"] == "T"
    assert [c["subject"] for c in tools.git_log(path="README.md")["commits"]] == ["First commit"]
    for bad in ("../outside", "--output=/tmp/x"):
        with pytest.raises(NotFound):
            tools.git_log(path=bad)
    assert ProjectTools(repo / "docs" / "nope").git_status() == {"available": False}


def test_list_devices():
    devices = {d["name"]: d for d in ProjectTools(REPO, VENUE).list_devices()["devices"]}
    assert devices["so101-green"]["borrowed"] is True
    assert devices["so101-green"]["off_limits"] is False
    assert devices["fake-arm"]["active_in_venue"] is True
    assert devices["so101-white"]["active_in_venue"] is False


def test_the_real_docs():
    tools = ProjectTools(REPO)
    names = {d["name"] for d in tools.list_docs()["docs"]}
    assert {"current-focus", "ideas", "GOTCHAS", "lab-jarvis-log", "CLAUDE"} <= names
    assert "design/DESIGN" in names
    assert "On hold" in tools.read_doc("ideas", section="On hold")["text"]


# ---------- over MCP ----------


async def test_the_mcp_server_offers_the_read_tools(repo):
    server = create_mcp_server(robot_tools(), ProjectTools(repo))
    tools = {t.name: t for t in await server.list_tools()}
    for name in READ_TOOLS:
        assert tools[name].annotations.read_only_hint, name
    result = await server.call_tool("read_doc", {"name": "ideas", "section": "On hold"})
    assert json.loads(result.content[0].text)["text"] == "## On hold\n- The router."
    with pytest.raises(ToolError, match="Not found: no doc 'nope'"):
        await server.call_tool("read_doc", {"name": "nope"})


async def test_the_hub_chat_gets_read_tools_only(repo):
    chat_tools = ChatTools(create_mcp_server(robot_tools(), ProjectTools(repo)))
    offered = {t["function"]["name"] for t in await chat_tools.openai_tools()}
    assert offered == READ_TOOLS  # no move_joints, gripper, move_to, go_to_pose, stop
    assert not {"pose_view", "camera_snapshot"} & offered  # read tools, but the answer is a picture
    assert "isn't a tool you have" in await chat_tools.call("move_joints", '{"joints": {}}')
    assert "isn't a tool you have" in await chat_tools.call("stop", "{}")
    assert "aren't valid JSON" in await chat_tools.call("read_doc", "{oops")
    assert "Not found" in await chat_tools.call("read_doc", '{"name": "nope"}')
    text = await chat_tools.call("project_status", "{}")
    assert json.loads(text)["next"] == "Second"


# ---------- the chat looks things up ----------


def tool_calling_service(seen, always_tools=False):
    """Round 1: asks for project_status. Then answers in words (or keeps asking, if
    `always_tools`, until the tools aren't offered any more)."""

    async def completions(request):
        body = await request.json()
        seen.append(body)
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await resp.prepare(request)
        wants_tool = "tools" in body and (always_tools or body["messages"][-1]["role"] != "tool")
        if wants_tool:
            call = {
                "index": 0,
                "id": f"call_{len(seen)}",
                "type": "function",
                "function": {"name": "project_status", "arguments": ""},
                "extra_content": {"google": {"thought_signature": "sig"}},  # like Gemini
            }
            for delta in (
                {"tool_calls": [call]},
                {"tool_calls": [{"index": 0, "function": {"arguments": "{}"}}]},
            ):
                chunk = {"choices": [{"index": 0, "delta": delta}]}
                await resp.write(f"data: {json.dumps(chunk)}\n\n".encode())
            end = {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}
        else:
            words = {"choices": [{"index": 0, "delta": {"content": "Next is step 2."}}]}
            await resp.write(f"data: {json.dumps(words)}\n\n".encode())
            end = {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        usage = {"choices": [], "usage": {"prompt_tokens": 100, "completion_tokens": 10}}
        await resp.write(f"data: {json.dumps(end)}\n\ndata: {json.dumps(usage)}\n\n".encode())
        await resp.write(b"data: [DONE]\n\n")
        return resp

    app = web.Application()
    app.router.add_post("/v1/chat/completions", completions)
    return app


async def make_conv(aiohttp_server, repo, tmp_path, monkeypatch, always_tools=False):
    monkeypatch.setenv("LAB_TEST_KEY", "k")
    seen = []
    server = await aiohttp_server(tool_calling_service(seen, always_tools))
    setup = Setup(
        "main", str(server.make_url("/v1")), "m", key_env="LAB_TEST_KEY", price_in=1, price_out=1
    )
    conv = Conversation(
        Assistant(),
        SpendLog(tmp_path / "spend"),
        setups=lambda: {"main": setup},
        tools=ChatTools(create_mcp_server(robot_tools(), ProjectTools(repo))),
    )
    return conv, seen


async def test_the_chat_looks_it_up_then_answers(aiohttp_server, repo, tmp_path, monkeypatch):
    conv, seen = await make_conv(aiohttp_server, repo, tmp_path, monkeypatch)
    events = [e async for e in conv.ask("What's next?")]
    assert {"type": "tool", "name": "project_status"} in events
    assert "".join(e["text"] for e in events if e["type"] == "text") == "Next is step 2."
    assert events[-1]["tools"] == 1
    # round 2 carried the tool's answer back to the model
    tool_msg = seen[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and json.loads(tool_msg["content"])["next"] == "Second"
    asked = seen[1]["messages"][-2]["tool_calls"][0]
    assert asked["function"]["name"] == "project_status"
    assert asked["extra_content"] == {"google": {"thought_signature": "sig"}}  # sent back
    assert "draft a prompt" in seen[0]["messages"][0]["content"]  # the system prompt says how
    month = conv.spend.month()
    assert month["chats"] == 1 and month["spent_usd"] == pytest.approx(220 / 1e6)  # both rounds
    assert conv.messages[-1] == {"role": "assistant", "content": "Next is step 2."}
    await conv.close()


async def test_look_ups_are_capped(aiohttp_server, repo, tmp_path, monkeypatch):
    conv, seen = await make_conv(aiohttp_server, repo, tmp_path, monkeypatch, always_tools=True)
    events = [e async for e in conv.ask("Loop forever")]
    assert sum(e["type"] == "tool" for e in events) == MAX_TOOL_ROUNDS
    assert "tools" not in seen[-1]  # the last request offers no tools: the model must answer
    assert events[-1]["type"] == "done"
    await conv.close()


def test_the_page_names_the_look_ups():
    js = (REPO / "src" / "lab_os" / "hub" / "web" / "hub.js").read_text()
    assert 'ev.type === "tool"' in js and "copyButton" in js
