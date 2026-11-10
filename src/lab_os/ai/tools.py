"""The hub chat's tools: the brain's own MCP read tools, offered to the chat model in the
OpenAI-style "tools" format. **Read tools only** (rule 5): every tool must be annotated
read-only, and a few names are refused outright, so a move tool can never reach the hub's chat."""

import json
import logging

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

log = logging.getLogger(__name__)

NEVER = {"move_joints", "gripper", "move_to", "go_to_pose", "stop"}  # belt and braces
MAX_RESULT_CHARS = 14_000


class ChatTools:
    def __init__(self, server: MCPServer):
        self.server = server
        self._names: set[str] = set()

    async def openai_tools(self) -> list[dict]:
        tools = []
        for t in await self.server.list_tools():
            ann = t.annotations
            if t.name in NEVER or not (ann and ann.read_only_hint):
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
            return f"Error: {name!r} isn't a tool you have (read tools only)."
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
        if getattr(result, "structured_content", None):
            text = json.dumps(result.structured_content, ensure_ascii=False)
        else:
            text = "\n".join(getattr(c, "text", "") for c in result.content)
        if getattr(result, "is_error", False):
            text = f"Error: {text}"
        return text[:MAX_RESULT_CHARS]
