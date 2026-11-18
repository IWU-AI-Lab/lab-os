"""Talk to an AI service through the OpenAI-style chat interface (POST {base_url}/chat/completions,
streamed as server-sent events). The same code serves OpenAI, Gemini's OpenAI-compatible address
and local servers (Ollama, llama.cpp). Plain aiohttp: no vendor library.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import aiohttp

from lab_os.ai.models import Setup

log = logging.getLogger(__name__)

CONNECT_TIMEOUT_S = 10.0
QUIET_TIMEOUT_S = 30.0  # no data for this long while answering = the service is stuck


class AiError(RuntimeError):
    """The AI service didn't answer. The message is a full sentence for the screen."""


@dataclass
class Usage:
    tokens_in: int = 0
    tokens_out: int = 0
    tokens_cached: int = 0
    estimated: bool = False  # the service didn't report usage: counted ~4 characters per token

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            self.tokens_in + other.tokens_in,
            self.tokens_out + other.tokens_out,
            self.tokens_cached + other.tokens_cached,
            self.estimated or other.estimated,
        )


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str = ""  # JSON text, as the model wrote it
    extra: dict | None = None  # `extra_content` as sent (Gemini's thought_signature): sent back


@dataclass
class Reply:
    """What one request produced, filled in while it streams."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    finish_reason: str | None = None


def _headers(setup: Setup) -> dict:
    headers = {"Content-Type": "application/json"}
    if setup.key:
        headers["Authorization"] = f"Bearer {setup.key}"
    return headers


def _http_error(setup: Setup, status: int, body: str) -> AiError:
    who = setup.where or setup.name
    if status in (401, 403):
        return AiError(f"{who} refused the API key ({setup.key_env}), so chat is paused.")
    if status == 429:
        return AiError(f"{who} says we're sending too much or the account is out of credit.")
    if status in (500, 502, 503, 504):
        return AiError(
            f"{who} is busy or having trouble right now (HTTP {status}). Try again soon."
        )
    if status == 404:
        return AiError(f"{who} doesn't know the model {setup.model!r} (models.yaml).")
    log.warning("%s: HTTP %s: %s", setup.name, status, body[:500])
    return AiError(f"{who} answered with an error (HTTP {status}). Try again in a moment.")


def estimate(messages: list[dict], text: str) -> Usage:
    chars_in = sum(len(json.dumps(m.get("content") or "")) for m in messages)
    return Usage(tokens_in=chars_in // 4 + 1, tokens_out=len(text) // 4 + 1, estimated=True)


async def stream_chat(
    session: aiohttp.ClientSession,
    setup: Setup,
    messages: list[dict],
    reply: Reply,
    tools: list[dict] | None = None,
) -> AsyncIterator[str]:
    """Send `messages`, yield the answer's text as it arrives, and fill `reply` (text, tool calls,
    usage). Raises AiError with a sentence for the screen when the service doesn't answer."""
    body = {"model": setup.model, "messages": messages, "stream": True} | setup.options
    body["stream_options"] = {"include_usage": True}
    if tools:
        body["tools"] = tools
    calls: dict[int, ToolCall] = {}
    timeout = aiohttp.ClientTimeout(sock_connect=CONNECT_TIMEOUT_S, sock_read=QUIET_TIMEOUT_S)
    who = setup.where or setup.name
    try:
        async with session.post(
            f"{setup.base_url}/chat/completions",
            json=body,
            headers=_headers(setup),
            timeout=timeout,
        ) as resp:
            if resp.status != 200:
                raise _http_error(setup, resp.status, await resp.text())
            async for raw in resp.content:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                if chunk.get("error"):
                    raise AiError(f"{who} stopped with an error: {chunk['error'].get('message')}")
                if chunk.get("usage"):
                    u = chunk["usage"]
                    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
                    reply.usage = Usage(
                        u.get("prompt_tokens") or 0, u.get("completion_tokens") or 0, cached
                    )
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    if delta.get("content"):
                        reply.text += delta["content"]
                        yield delta["content"]
                    for tc in delta.get("tool_calls") or []:
                        i = tc.get("index", len(calls))
                        fn = tc.get("function") or {}
                        call = calls.setdefault(
                            i, ToolCall(id=tc.get("id") or f"call_{i}", name="")
                        )
                        call.name += fn.get("name") or ""
                        call.arguments += fn.get("arguments") or ""
                        if tc.get("extra_content"):
                            call.extra = tc["extra_content"]
                    if choice.get("finish_reason"):
                        reply.finish_reason = choice["finish_reason"]
    except AiError:
        raise
    except TimeoutError:
        raise AiError(
            f"{who} didn't answer in time, so I stopped. Try again in a moment."
        ) from None
    except aiohttp.ClientError as e:
        log.warning("%s: %s", setup.name, e)
        where = "the local AI server isn't running" if setup.local else "is there internet?"
        raise AiError(f"I can't reach {who} ({where}).") from None
    except (json.JSONDecodeError, asyncio.IncompleteReadError):
        raise AiError(f"{who} sent something I couldn't read. Try again.") from None
    reply.tool_calls = [calls[i] for i in sorted(calls)]
    if not reply.usage.tokens_in and not reply.usage.tokens_out:
        reply.usage = estimate(messages, reply.text)


async def reach(session: aiohttp.ClientSession, setup: Setup) -> str | None:
    """Can we reach the service with this key? Lists the models (free; nothing is generated).
    None = yes; else why not, in a few words for the log ("HTTP 503", "no answer in 10 s", the
    connection error: a failed name lookup says so)."""
    try:
        async with session.get(
            f"{setup.base_url}/models",
            headers=_headers(setup),
            timeout=aiohttp.ClientTimeout(total=CONNECT_TIMEOUT_S),
        ) as resp:
            return None if resp.status == 200 else f"HTTP {resp.status}"
    except TimeoutError:
        return f"no answer in {CONNECT_TIMEOUT_S:.0f} s"
    except aiohttp.ClientError as e:
        return f"{type(e).__name__}: {e}"


async def check(session: aiohttp.ClientSession, setup: Setup) -> bool:
    """Can we reach the service with this key? (`reach`, as yes or no.)"""
    return await reach(session, setup) is None
