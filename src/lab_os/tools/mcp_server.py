"""The brain's MCP server: the robot tools for AI tools (Claude Code, Codex, Claude Desktop).

Listens on this computer only (127.0.0.1), on its own port next to the hub (default 8081, path
/mcp), in the brain's event loop, so the tools drive the same teleop loop as the pages. How to
connect: docs/ai-control.md. Permission tiers (current-focus.md): arm_status and list_poses are
read; stop is always allowed; move_joints, gripper, move_to and go_to_pose are move (never
allow-list them: each one should ask).
"""

import contextlib
import logging

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

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
move. Refusals say why; don't retry a refusal unchanged. If a move result says it was stopped,
don't move again until the user says so. The user approves each move.
"""

READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
MOVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True)
STOP = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True)


def create_mcp_server(tools: RobotTools) -> MCPServer:
    server = MCPServer(name="lab-os", instructions=INSTRUCTIONS)

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

    async def serve(self) -> None:
        await self.uvicorn.serve()

    def shutdown(self) -> None:
        self.uvicorn.should_exit = True
