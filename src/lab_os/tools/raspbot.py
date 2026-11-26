"""AI tools for the Raspbot, through the same controller and camera as the Raspbot page."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from lab_os.robots.raspbot import RaspbotDesk
from lab_os.tools.calllog import CallLog
from lab_os.tools.mcp_server import MOVE, READ, STOP

Direction = Literal["forward", "back", "left", "right"]
DriveSeconds = Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]
APPROACH_TIMEOUT_S = 10.0


def add_raspbot_tools(
    server: MCPServer,
    desk: RaspbotDesk,
    snapshot: Callable[[], Awaitable[bytes]],
    calls: CallLog,
    may_move: Callable[[], bool],
) -> None:
    """Register tools that share the page's controller and stream."""

    async def move(direction: Direction, seconds: float, *, approach: bool = False) -> dict:
        owner = object()
        until = time.monotonic() + seconds
        result = "time_limit" if approach else "done"
        message = ""
        started = False
        try:
            while True:
                now = time.monotonic()
                if not may_move():
                    result, message = "refused", "This venue does not permit motion."
                    break
                if started and desk.driver is not owner:
                    result, message = "stopped", "STOP ended the drive."
                    break
                if not desk.bot.connected:
                    result, message = "disconnected", desk.status()["message"]
                    break
                if started and desk.bot.drive_stop:
                    result = desk.bot.drive_stop
                    break
                if direction == "forward":
                    distance, limit = desk.bot.fresh_distance_mm, desk.bot.obstacle_stop_mm
                    if limit is not None and distance is not None and distance <= limit:
                        result = "obstacle"
                        break
                if now >= until:
                    break
                if desk.driver is owner and not desk.moving:
                    result, message = "stopped", "The drive input stopped."
                    break
                message = await desk.press(owner, direction, ai=True)
                if message:
                    result = "refused"
                    break
                started = True
                await asyncio.sleep(min(desk.TICK_S, max(0, until - time.monotonic())))
        finally:
            await desk.release(owner)
        return {
            "result": result,
            "distance_mm": desk.bot.fresh_distance_mm,
            "message": message,
        }

    @server.tool(annotations=READ)
    def raspbot_status() -> dict:
        """Read the Raspbot's connection, control, motion, camera and front distance in mm."""
        return calls.write("raspbot_status", {}, "ok", desk.status())["result"]

    @server.tool(annotations=READ)
    async def raspbot_camera() -> Image:
        """See one JPEG picture from the Raspbot's camera. Keep the robot still while looking."""
        try:
            jpeg = await snapshot()
        except LookupError as e:
            calls.write("raspbot_camera", {}, "refused", str(e))
            raise ToolError(str(e)) from e
        calls.write("raspbot_camera", {}, "ok", {"bytes": len(jpeg)})
        return Image(data=jpeg, format="jpeg")

    @server.tool(annotations=MOVE)
    async def raspbot_drive(direction: Direction, seconds: DriveSeconds = 0.5) -> dict:
        """Drive forward, back, left or right for up to one second, then stop.
        Check the camera and distance first. Back and turns need a person to check clearance."""
        out = await move(direction, seconds)
        calls.write(
            "raspbot_drive", {"direction": direction, "seconds": seconds}, out["result"], out
        )
        return out

    @server.tool(annotations=MOVE)
    async def raspbot_approach() -> dict:
        """Drive straight toward an object already aligned ahead. Stop at the front sensor's
        20 cm threshold, on loss of the reading, or after at most 10 seconds. Inspect the camera
        first. An obstacle result means the sensor saw an object, which may be a different one."""
        out = await move("forward", APPROACH_TIMEOUT_S, approach=True)
        calls.write("raspbot_approach", {}, out["result"], out)
        return out

    @server.tool(annotations=STOP)
    async def raspbot_stop() -> dict:
        """Press the Raspbot page's STOP, whoever has control."""
        await desk.stop("AI tool")
        return calls.write("raspbot_stop", {}, "ok", desk.status())["result"]
