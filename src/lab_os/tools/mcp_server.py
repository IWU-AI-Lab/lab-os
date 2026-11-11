"""The brain's MCP server: the robot tools and the project helper's read tools for AI tools
(Claude Code, Codex, Claude Desktop). The hub's own chat uses its read tools too (lab_os.ai.tools).

Listens on this computer only (127.0.0.1), on its own port next to the hub (default 8081, path
/mcp), in the brain's event loop, so the tools drive the same teleop loop as the pages. How to
connect: docs/ai-control.md. Permission tiers (current-focus.md): arm_status, list_poses and the
project tools (project_status, list_docs, read_doc, search_docs, git_status, git_log, list_devices)
are read; stop is always allowed; move_joints, gripper, move_to and go_to_pose are move (never
allow-list them: each one should ask).
"""

import contextlib
import logging

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from lab_os.tools.project import NotFound, ProjectTools
from lab_os.tools.robot import Refused, RobotTools

log = logging.getLogger(__name__)

MCP_HOST = "127.0.0.1"  # never anything else: the move tools are for this computer only
DEFAULT_PORT = 8081

INSTRUCTIONS = """\
Tools for the lab's robot arm, through the lab-os brain. Call arm_status first: it gives the joint
angles, the gripper's position (cm from the arm's base: x forward, y to the arm's left, z up, 0 =
the table), the tool angle (0 = gripper pointing up, 90 = forward, 180 = straight down), who has
control and the per-call limits. Moves are small on purpose: a call moves at most
max_joint_change_deg per joint or max_move_cm (move_to) and says when it went only part of the way;
call again to continue. Every move returns where the arm really ended up: check it before the next
move. "result": "stopped_short" means the arm didn't get there (off_by_cm, joints_short_deg and a
message say how far): don't grip or carry on as if it had. Refusals say why; don't retry a
refusal unchanged. If a move result says it was stopped, don't move again until the user says so.
The user approves each move.

Project tools (read only): project_status (the current focus and its steps), list_docs, read_doc
(one doc, or one section of it), search_docs, git_status, git_log, list_devices. Use them instead
of guessing about the project.
"""

READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
MOVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True)
STOP = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True)


def create_mcp_server(tools: RobotTools, project: ProjectTools | None = None) -> MCPServer:
    server = MCPServer(name="lab-os", instructions=INSTRUCTIONS)
    if project:
        add_project_tools(server, project, tools.calls)

    async def run(tool: str, **args) -> dict:
        args = {k: v for k, v in args.items() if v is not None}
        try:
            return await tools.call(tool, **args)
        except Refused as e:
            raise ToolError(f"Refused: {e}") from e

    @server.tool(annotations=READ)
    async def arm_status(arm: str | None = None) -> dict:
        """The arm right now: connected?, joint angles (degrees), gripper opening (%), gripper
        position (cm) and tool angle, joint limits, who has control (free / teleop / ai), whether
        it's held still, whether this venue allows motion, and the per-call limits. `arm`: the
        lab-os name (default: the connected arm)."""
        return await run("arm_status", arm=arm)

    @server.tool(annotations=READ)
    async def list_poses(arm: str | None = None) -> dict:
        """Named poses for go_to_pose (e.g. home, rest) with their joint angles."""
        return await run("list_poses", arm=arm)

    @server.tool(annotations=MOVE)
    async def move_joints(
        joints: dict[str, float], relative: bool = False, arm: str | None = None
    ) -> dict:
        """Move some joints, in degrees. `joints`: e.g. {"shoulder_pan": 20, "elbow_flex": 45};
        names: shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper.
        `relative`: true = change by these amounts instead of going to them. Clipped to the joint
        limits and to max_joint_change_deg per call (then it goes part of the way: call again).
        Returns where the arm really ended up."""
        return await run("move_joints", joints=joints, relative=relative, arm=arm)

    @server.tool(annotations=MOVE)
    async def gripper(open_pct: float, arm: str | None = None) -> dict:
        """Open or close the gripper: 0 = closed, 100 = fully open."""
        return await run("gripper", open_pct=open_pct, arm=arm)

    @server.tool(annotations=MOVE)
    async def move_to(
        x_cm: float,
        y_cm: float,
        z_cm: float,
        tool_angle_deg: float | None = None,
        arm: str | None = None,
    ) -> dict:
        """Move the gripper point (between the fingertips) in a straight line to (x, y, z) cm from
        the arm's base: x forward, y to the arm's left, z up (0 = the table). `tool_angle_deg`:
        the gripper's tilt, 0 = up, 90 = forward, 180 = straight down (for picking from above);
        default: keep the current one. At most max_move_cm per call (then it goes part of the way:
        call again). Refuses points it can't reach or below min_z_cm, instead of guessing."""
        return await run(
            "move_to", x_cm=x_cm, y_cm=y_cm, z_cm=z_cm, tool_angle_deg=tool_angle_deg, arm=arm
        )

    @server.tool(annotations=MOVE)
    async def go_to_pose(name: str, arm: str | None = None) -> dict:
        """Go to a named pose (list_poses), at most max_joint_change_deg per joint per call."""
        return await run("go_to_pose", name=name, arm=arm)

    @server.tool(annotations=STOP)
    async def stop(arm: str | None = None) -> dict:
        """Stop the arm now and hold it still. Always allowed, whoever has control."""
        return await run("stop", arm=arm)

    return server


def add_project_tools(server: MCPServer, project: ProjectTools, calls) -> None:
    """The project helper's read tools (step 6). Each call is logged, with the result's size."""

    def run(tool: str, **args) -> dict:
        args = {k: v for k, v in args.items() if v is not None}
        try:
            result = getattr(project, tool)(**args)
        except NotFound as e:
            calls.write(tool, args, "refused", str(e))
            raise ToolError(f"Not found: {e}") from e
        calls.write(tool, args, "ok", f"{len(str(result))} characters")
        return result

    @server.tool(annotations=READ)
    def project_status() -> dict:
        """The current focus (docs/current-focus.md): its name, every step with done or not (and
        when), the step that's next. Start here for "what's next?" or "where are we?"."""
        return run("project_status")

    @server.tool(annotations=READ)
    def list_docs() -> dict:
        """The project's docs: name, file, title. Includes current-focus (what's being worked on),
        ideas (the backlog, incl. "On hold"), lab-jarvis-log (plan, decisions, devices), GOTCHAS
        (surprises and fixes), protocol, places, chat, personas, hub, ai-control, CHANGELOG."""
        return run("list_docs")

    @server.tool(annotations=READ)
    def read_doc(name: str, section: str | None = None) -> dict:
        """Read one doc by name (e.g. "current-focus", "ideas", "GOTCHAS"), or only the section
        under the first heading containing `section` (e.g. "On hold", "Step 7"). Long docs are
        cut off at 12,000 characters with a list of their sections: then ask for a section."""
        return run("read_doc", name=name, section=section)

    @server.tool(annotations=READ)
    def search_docs(text: str) -> dict:
        """Lines in the docs containing `text` (any case), with the doc, line number and heading.
        At most 30 hits."""
        return run("search_docs", text=text)

    @server.tool(annotations=READ)
    def git_status() -> dict:
        """The repository: branch (and ahead/behind its remote as of the last fetch), changed
        files, the last commit. Nothing is fetched."""
        return run("git_status")

    @server.tool(annotations=READ)
    def git_log(count: int = 15, path: str | None = None) -> dict:
        """Recent commits on the current branch, newest first (hash, date, author, subject); at
        most 50. `path`: only commits touching this file or folder."""
        return run("git_log", count=count, path=path)

    @server.tool(annotations=READ)
    def list_devices() -> dict:
        """The place's devices (config): name, kind, off limits, active in this venue, notes.
        Whether a device is switched on isn't known yet."""
        return run("list_devices")


class _Uvicorn(uvicorn.Server):
    @contextlib.contextmanager
    def capture_signals(self):
        yield  # Ctrl+C belongs to the brain, which stops this server itself


class McpHttp:
    """Runs the MCP server over HTTP (streamable HTTP, at /mcp) inside the brain's event loop."""

    def __init__(self, server: MCPServer, port: int = DEFAULT_PORT):
        app = server.streamable_http_app(streamable_http_path="/mcp", host=MCP_HOST)
        config = uvicorn.Config(app, host=MCP_HOST, port=port, log_level="warning", lifespan="on")
        self.uvicorn = _Uvicorn(config)
        self.port = port
        self.url = f"http://{MCP_HOST}:{port}/mcp"
        self.failed = False  # couldn't start (the port is taken): the brain runs on without it

    async def serve(self) -> None:
        try:
            await self.uvicorn.serve()
        except SystemExit:  # uvicorn exits the whole program when it can't bind; keep the brain
            self.failed = True
            log.error(
                "AI tools (MCP) are off: port %d is in use (another lab-os serve running?). The "
                "hub works without them; stop the other brain, or pick a port with --mcp-port.",
                self.port,
            )

    def shutdown(self) -> None:
        self.uvicorn.should_exit = True
