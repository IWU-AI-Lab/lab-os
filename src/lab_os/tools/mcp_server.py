"""The brain's MCP server: the robot tools and the project helper's read tools for AI tools
(Claude Code, Codex, Claude Desktop). The hub's own chat uses its read tools too (lab_os.ai.tools).

Listens on this computer only (127.0.0.1), on its own port next to the hub (default 8081, path
/mcp), in the brain's event loop, so the tools drive the same teleop loop as the pages. How to
connect: docs/guides/ai-control.md. Permission tiers (docs/plan/log.md): arm_status,
list_poses, pose_view, camera_snapshot and the project tools (project_status, list_docs, read_doc,
search_docs, git_status, git_log, list_devices) are read; stop is always allowed; move_joints,
gripper, move_to and go_to_pose are move (never allow-list them: each one should ask). The hub's
buttons as tools (quick job 80) are added by lab_os.hub.system_tools.
"""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

import uvicorn
from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from lab_os.tools.program import DEFAULT_LIMIT_S, ProgramRunner
from lab_os.tools.project import NotFound, ProjectTools
from lab_os.tools.robot import Refused, RobotTools

log = logging.getLogger(__name__)

MCP_HOST = "127.0.0.1"  # never anything else: the move tools are for this computer only
DEFAULT_PORT = 8081
# When the brain stops, an AI tool's open connection gets this long, then it is cut (quick job 44)
STOP_WAIT_S = 1

INSTRUCTIONS = """\
Tools for the lab's robot arm, through the lab-os brain. Call arm_status first: it gives the joint
angles, the gripper's position (cm from the arm's base: x forward, y to the arm's left, z up, 0 =
the table, also for an arm standing on a plate), the tool angle (0 = gripper pointing up, 90 =
forward, 180 = straight down), who has control and the per-call limits. Moves are small on purpose:
a call moves at most max_joint_change_deg per joint or max_move_cm (move_to) and says when it went
only part of the way; call again to continue. Every move returns where the arm really ended up:
check it before the next move. "result": "stopped_short" means the arm didn't get there (off_by_cm,
joints_short_deg and a message say how far): don't grip or carry on as if it had. Refusals say why;
don't retry a refusal unchanged. If a move result says it was stopped, don't move again until the
user says so. camera_snapshot takes a real picture from a camera; on a camera with a table map it
has a cm grid of the table on it (table_point turns a pixel into cm): use it for an object's x and
y, then the wrist camera to fine-tune. pose_view draws the arm as it is now (no camera): look at it
after a move, with marks where you think the objects are, before you grip. Moves don't wait for
approval; someone watches the arm with STOP in reach, so say one short line before each move. Named
poses (list_poses, go_to_pose): "ready" is the working pose, reaching forward a little above the
table: start a task from there. "home" is the folded pose the arm is left in: go there when the user
says you're done or asks for home.

Picking something up: find it on the stand camera's grid; move_to within max_move_cm of the
point above it; then pick_at (open, above, straight down, close, lift in one call). By hand: come
down from above pointing straight down (tool angle 180), with the gripper fully open; look with
the wrist camera before closing (the object between the jaw tips); close fully (gripper 0); lift
a few cm and look again: a held object fills much of the wrist picture and the gripper stops
part-way open. If unsure, stop and look instead of guessing; if a pick missed, look before
trying again. (Tips adapted from robot_MCP: docs/dev/existing-work-teleop-ai.md.)

Tic-tac-toe on the paper grid: camera_snapshot of the stand camera with board true shows the board
and gives everything else you need (docs/guides/tic-tac-toe.md).

One program instead of many moves (run_program): when a task takes several moves (look, go
above, pick, carry), write one short Python program that calls the functions and run it in one
call. It runs on the brain with no wait between the steps, so it is much faster than single
calls. Use loops and ifs to check results (a move that went only part of the way says so in
"clipped"; call it again). Prefer it over many single moves. Single calls are for looking first.

Two arms at once: arm_status lists "other_arms"; give a tool's `arm` to drive another one (the
first arm is the default). The hub's buttons are tools too: hub_screens and open_on_device ("Open
on…"), bring_back, set_up_the_room, list_settings and change_setting, change_device_setting,
visitor_mode, quest_view, say_aloud, teleop_speed and teleop_mode, wave_arm, the Training page's
training_lelab and training_lerobot_teleop, restart_lab_os and shut_down_lab_os (only when asked).

Project tools (read only): project_status (the current focus and its steps), list_docs, read_doc
(one doc, or one section of it), search_docs, git_status, git_log, list_devices. Use them instead
of guessing about the project.
"""

READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
MOVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True)
STOP = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True)


def create_mcp_server(
    tools: RobotTools,
    project: ProjectTools | None = None,
    other_arms: Callable[[], list[RobotTools]] = list,
    find_cube: Callable[[], Awaitable[tuple[float, float]]] | None = None,
) -> MCPServer:
    """`tools`: the first arm's (the default); `other_arms`: the tools of every other connected
    arm (two arms at once), reached by naming the arm (quick job 80)."""
    server = MCPServer(name="lab-os", instructions=INSTRUCTIONS)
    if project:
        add_project_tools(server, project, tools.calls)

    def pick(arm: str | None) -> RobotTools:
        for t in other_arms():
            if arm and t.arm.name == arm:
                return t
        return tools

    async def run(tool: str, **args) -> dict:
        args = {k: v for k, v in args.items() if v is not None}
        try:
            result = await pick(args.get("arm")).call(tool, **args)
        except Refused as e:
            others = [t.arm.name for t in other_arms()]
            more = f" (other arms: {', '.join(others)})" if others else ""
            raise ToolError(f"Refused: {e}{more}") from e
        if tool == "arm_status":
            result["other_arms"] = [
                t.arm.name for t in other_arms() if t is not pick(args.get("arm"))
            ]
            if pick(args.get("arm")) is not tools:
                result["other_arms"].append(tools.arm.name)
        return result

    @server.tool(annotations=READ)
    async def arm_status(arm: str | None = None) -> dict:
        """The arm right now: connected?, joint angles (degrees), gripper opening (%), gripper
        position (cm) and tool angle, joint limits, who has control (free / teleop / ai), whether
        it's held still, whether this venue allows motion, and the per-call limits. `arm`: the
        lab-os name (default: the connected arm)."""
        return await run("arm_status", arm=arm)

    @server.tool(annotations=READ)
    async def list_poses(arm: str | None = None) -> dict:
        """Named poses for go_to_pose (e.g. ready, home) with their joint angles."""
        return await run("list_poses", arm=arm)

    @server.tool(annotations=READ)
    async def pose_view(marks: list[dict] | None = None, arm: str | None = None) -> list:
        """A picture of the arm's 3D model in its current pose (from the joint readings, not a
        camera): side view in the arm's plane + top view, a grid in cm, the table, the gripper
        point (red dot) and the last move_to target (magenta x). `marks`: points to draw too
        (blue), e.g. where you think an object is: [{"x_cm": 15, "y_cm": 5, "z_cm": 1.5,
        "label": "cube", "size_cm": 3}] (at most 10). Use it to check a move before gripping."""
        r = await run("pose_view", marks=marks, arm=arm)
        png = r.pop("image_png")
        return [Image(data=png, format="png"), r]

    @server.tool(annotations=READ)
    async def camera_snapshot(
        camera: str, width_px: int = 640, grid: bool = True, board: bool = False
    ) -> list:
        """One picture from a camera (names in list_devices; the white arm's two:
        so101-white-cam-stand, on a stand about 2 ft up behind the arm, and so101-white-cam-wrist,
        on the wrist looking along the jaws; the green arm's: so101-green-cam-stand and
        so101-green-cam-wrist). Returns a JPEG `width_px` wide (160-1280). If a
        picture is very dark or washed out, take another. Use it to look before you reach
        and after you move; pose_view is drawn from the joints, this is real. A camera with a
        table map has the table's cm grid drawn on it ("table_grid" says how to read it; `grid`
        false = the plain picture): read where an object touches the table to get its x and y for
        move_to. A camera another program is using is refused. `board` true (tic-tac-toe, on the
        stand camera): the board's cells drawn and named (A1-C3) and the start spots of the
        robot's pieces numbered; "board" gives their positions and how to take and put down a
        piece, also when there's no picture (the fake arm has no camera)."""
        r = await run("camera_snapshot", camera=camera, width_px=width_px, grid=grid, board=board)
        jpeg = r.pop("image_jpeg", None)  # none: board true, and no picture ("picture" says why)
        return [Image(data=jpeg, format="jpeg"), r] if jpeg else [r]

    @server.tool(annotations=READ)
    async def table_point(camera: str, x_px: float, y_px: float, width_px: int = 640) -> dict:
        """Where a pixel of a camera_snapshot picture is on the table: x (forward) and y (left)
        in cm from the middle of the arm's base, as move_to takes them. `width_px`: the
        picture's width you asked for. Give the pixel where the object touches the table. Only
        cameras with a table map (the ones whose snapshot shows a grid)."""
        return await run("table_point", camera=camera, x_px=x_px, y_px=y_px, width_px=width_px)

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
    async def pick_at(
        x_cm: float,
        y_cm: float,
        height_cm: float = 2.5,
        open_pct: float = 100.0,
        arm: str | None = None,
    ) -> dict:
        """Pick up the object standing at (x, y) cm on the table (its middle, where it touches
        the table: the stand camera's grid), in one call: open the gripper (open_pct), go
        height_cm + 6 cm above it pointing straight down, straight down as deep as the jaws
        reach (4 cm below its top, never below the floor), close, lift. Start within
        max_move_cm of the point above it (move_to there first).
        Every point is checked before anything moves; each step shows on the AI Control page
        before it moves. "result": "holding" (the gripper stopped on something), "missed" (it
        shut all the way), or the step where it stopped ("steps" lists them). Check with the
        wrist camera afterwards."""
        return await run(
            "pick_at", x_cm=x_cm, y_cm=y_cm, height_cm=height_cm, open_pct=open_pct, arm=arm
        )

    @server.tool(annotations=MOVE)
    async def go_to_pose(name: str, arm: str | None = None) -> dict:
        """Go to a named pose (list_poses), at most max_joint_change_deg per joint per call."""
        return await run("go_to_pose", name=name, arm=arm)

    @server.tool(annotations=STOP)
    async def stop(arm: str | None = None) -> dict:
        """Stop the arm now and hold it still. Always allowed, whoever has control."""
        return await run("stop", arm=arm)

    @server.tool(annotations=MOVE)
    async def run_program(code: str, time_limit_s: float = DEFAULT_LIMIT_S) -> dict:
        """Run one short Python program on the brain that calls the robot functions, with no
        model call between the steps (much faster than single calls). Functions (each returns
        the same dict as the tool of that name): arm_status(), list_poses(), find_cube() (the
        blue cube on the stand camera: {"x_cm", "y_cm"}, or None), table_point(camera, x_px,
        y_px), move_to(x_cm, y_cm, z_cm, tool_angle_deg=None), pick_at(x_cm, y_cm,
        height_cm=2.5), gripper(open_pct), go_to_pose(name), move_joints(joints), wait(seconds);
        each takes arm= for another arm. Also math.*, statistics.*, print() and plain builtins.
        No imports, no files, no names starting with "_", no d[k] += x (write d[k] = d[k] + x).
        Set `result` to return a value. A move goes at most max_move_cm or max_joint_change_deg
        a call: loop until it's there (e.g. while "went" is in any of r["clipped"]). Every call
        has the usual checks; a refusal, a stopped move, STOP or the time limit (default 120 s,
        at most 300) ends the program. Returns what happened: "result" (done, stopped, time
        limit, error), each call with its result, what it printed, and where it stopped
        ("line")."""
        runner = ProgramRunner(
            lambda tool, **a: pick(a.get("arm")).call(tool, **a),
            asyncio.get_running_loop(),
            stops=lambda: tools.loop.stops,
            find_cube=find_cube,
        )
        return await asyncio.to_thread(runner.run, code, time_limit_s)

    return server


def add_lab_status(server: MCPServer, report, calls) -> None:
    """The `lab_status` read tool (quick job 16): `report()` builds it (the hub server's
    lab_status, which knows the devices, voice and spend). Each call is logged."""

    @server.tool(annotations=READ)
    def lab_status() -> dict:
        """The lab right now, in one call: the arm (who drives it, held still, servo heat), the
        devices with the hub open, voice and the AI (connected? paused?), internet, this month's
        AI spend and budget (not on a public venue), the focus's next step, and warnings (limits
        switched off, warm servos, the chat paused). Only what the brain knows; anything not
        listed isn't known. For "how's the lab?" / "give me a status report": say it in a few
        sentences, warnings first. The AI spend is an estimate that counts this computer's brain
        only: say "estimated" with the number."""
        r = report()
        calls.write("lab_status", {}, "ok", {"warnings": r.get("warnings", [])})
        return r


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
        """The current focus (docs/plan/current-focus.md): its name, every step with done or not
        (and when), the step that's next. Start here for "what's next?" or "where are we?"."""
        return run("project_status")

    @server.tool(annotations=READ)
    def list_docs() -> dict:
        """The project's docs: name, file, title. In folders by who reads them: plan/
        (current-focus: what's being worked on; quick-jobs; ideas: the backlog, incl. "On hold";
        log: plan, decisions, devices), guides/ (hub, voice, ai-control, lab-checklist,
        …), dev/ (GOTCHAS: surprises and fixes; protocol, places, chat, personas, …), design/DESIGN
        (the hub's design), archive/ (history); plus README, CHANGELOG, SAFETY, AGENTS."""
        return run("list_docs")

    @server.tool(annotations=READ)
    def read_doc(name: str, section: str | None = None) -> dict:
        """Read one doc by name ("plan/current-focus", or just "current-focus", "ideas", "GOTCHAS"
        when only one doc has that name), or only the section under the first heading containing
        `section` (e.g. "On hold", "Step 7"). Long docs are cut off at 12,000 characters with a list
        of their sections: then ask for a section."""
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
        """The place's devices (config): name, kind, off limits, borrowed (another project's:
        usable, but never set up or recalibrated by lab-os), active in this venue, notes.
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
        config = uvicorn.Config(
            app,
            host=MCP_HOST,
            port=port,
            log_level="warning",
            lifespan="on",
            timeout_graceful_shutdown=STOP_WAIT_S,
        )
        self.uvicorn = _Uvicorn(config)
        self.sessions = server.session_manager
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

    async def shutdown(self) -> None:
        """Stop: end each AI tool's session first, so its open stream closes cleanly (uvicorn
        would wait for it, then cut it with an error trace), then the server."""
        # HACK: the MCP library has no public call to end every session; this reads its own list
        # (docs/plan/current-focus.md → Hacks). If it moves, uvicorn's STOP_WAIT_S cut still works.
        for transport in list(getattr(self.sessions, "_server_instances", {}).values()):
            try:
                await transport.terminate()
            except Exception as e:  # the stop must go on
                log.warning("AI tools (MCP): ending a session: %s", e)
        self.uvicorn.should_exit = True
