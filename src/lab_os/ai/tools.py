"""The hub chat's tools: the brain's own MCP tools, offered to the chat model in the OpenAI-style
"tools" format. **Read tools only** (rule 5): every tool must be annotated read-only, and a few
names are refused outright, so a move tool never reaches the hub's chat, unless ⚙ → Assistant →
Full Access is on (quick job 80): then every tool, the move and picture tools included; a
picture goes to the model as an image (`take_images`)."""

import json
import logging
from collections.abc import Callable

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

log = logging.getLogger(__name__)

NEVER = {
    "move_joints",
    "gripper",
    "move_to",
    "go_to_pose",
    "pick_at",
    "stop",
    "wave",
}  # belt and braces
NOT_FOR_CHAT = {
    "pose_view",
    "camera_snapshot",
    "raspbot_camera",
    "table_point",
}  # read tools about a picture: the chat takes text
MAX_RESULT_CHARS = 14_000


class ChatTools:
    def __init__(self, server: MCPServer, full_access: Callable[[], bool] = lambda: False):
        self.server = server
        self.full_access = full_access  # read when the tools are listed for a question
        self._names: set[str] = set()
        self._images: list[dict] = []  # pictures from the last calls, for the model

    async def openai_tools(self, skip: set[str] | frozenset = frozenset()) -> list[dict]:
        """The tools for one question (`skip`: names the chat has its own tool for)."""
        full = self.full_access()
        tools = []
        for t in await self.server.list_tools():
            ann = t.annotations
            if t.name in skip:
                continue
            if not full and (t.name in NEVER | NOT_FOR_CHAT or not (ann and ann.read_only_hint)):
                continue
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.input_schema,
                    },
                }
            )
        self._names = {t["function"]["name"] for t in tools}
        return tools

    async def call(self, name: str, arguments: str) -> str:
        """Run a read tool; the result (or the reason it failed) as text for the model."""
        if name not in self._names:
            return f"Error: {name!r} isn't a tool you have now."
        try:
            args = json.loads(arguments or "{}")
            if not isinstance(args, dict):
                raise ValueError("arguments must be an object")
        except ValueError as e:
            return f"Error: the arguments aren't valid JSON ({e})."
        try:
            result = await self.server.call_tool(name, args)
        except ToolError as e:
            return f"Error: {e}"
        except Exception as e:  # a tool crashed: tell the model, keep the chat alive
            log.warning("chat tool %s failed: %r", name, e)
            return f"Error: {name} failed."
        for c in result.content:  # a picture (camera_snapshot, pose_view): kept for the model
            if getattr(c, "type", "") == "image":
                url = f"data:{c.mime_type};base64,{c.data}"
                self._images.append({"tool": name, "url": url})
        if getattr(result, "structured_content", None):
            text = json.dumps(result.structured_content, ensure_ascii=False)
        else:
            text = "\n".join(getattr(c, "text", "") for c in result.content)
        if getattr(result, "is_error", False):
            text = f"Error: {text}"
        return text[:MAX_RESULT_CHARS]

    def take_images(self) -> list[dict]:
        """The pictures the tool calls since the last time returned ({"tool", "url"}), once."""
        images, self._images = self._images, []
        return images
