"""Transport utilities for MCP connections.

Provides async context managers for stdio and HTTP transports.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncIterator

if TYPE_CHECKING:
    from mcp import ClientSession


@asynccontextmanager
async def create_stdio_session(
    command: list[str],
    env: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> AsyncIterator[ClientSession]:
    """Create an MCP session via stdio transport.

    Args:
        command: Command and arguments to start the server
        env: Environment variables for the subprocess
        timeout: Connection timeout in seconds

    Yields:
        Connected MCP ClientSession
    """
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(
        command=command[0],
        args=command[1:] if len(command) > 1 else [],
        env=env,
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=timeout)
            yield session


@asynccontextmanager
async def create_http_session(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> AsyncIterator[ClientSession]:
    """Create an MCP session via HTTP transport.

    Args:
        url: Server URL
        headers: Optional HTTP headers for authentication
        timeout: Connection timeout in seconds

    Yields:
        Connected MCP ClientSession
    """
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=timeout)
            yield session


async def list_tools_stdio(
    command: list[str],
    env: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """List tools from a stdio MCP server.

    Args:
        command: Command to start the server
        env: Environment variables
        timeout: Connection timeout

    Returns:
        List of tool definitions
    """
    async with create_stdio_session(command, env, timeout) as session:
        result = await session.list_tools()
        return [_tool_to_dict(t) for t in result.tools]


async def list_tools_http(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """List tools from an HTTP MCP server.

    Args:
        url: Server URL
        headers: HTTP headers
        timeout: Connection timeout

    Returns:
        List of tool definitions
    """
    async with create_http_session(url, headers, timeout) as session:
        result = await session.list_tools()
        return [_tool_to_dict(t) for t in result.tools]


async def call_tool_stdio(
    command: list[str],
    tool_name: str,
    arguments: dict[str, Any],
    env: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Call a tool on a stdio MCP server.

    Args:
        command: Command to start the server
        tool_name: Name of tool to call
        arguments: Tool arguments
        env: Environment variables
        timeout: Execution timeout

    Returns:
        Tool result dictionary
    """
    async with create_stdio_session(command, env, timeout) as session:
        result = await asyncio.wait_for(
            session.call_tool(tool_name, arguments),
            timeout=timeout,
        )
        return _result_to_dict(result)


async def call_tool_http(
    url: str,
    tool_name: str,
    arguments: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Call a tool on an HTTP MCP server.

    Args:
        url: Server URL
        tool_name: Name of tool to call
        arguments: Tool arguments
        headers: HTTP headers
        timeout: Execution timeout

    Returns:
        Tool result dictionary
    """
    async with create_http_session(url, headers, timeout) as session:
        result = await asyncio.wait_for(
            session.call_tool(tool_name, arguments),
            timeout=timeout,
        )
        return _result_to_dict(result)


def _tool_to_dict(tool: Any) -> dict[str, Any]:
    """Convert MCP tool object to dictionary."""
    result = {
        "name": getattr(tool, "name", ""),
        "description": getattr(tool, "description", None),
    }

    # Handle input schema
    schema = getattr(tool, "inputSchema", None)
    if schema is None:
        schema = getattr(tool, "input_schema", None)
    if schema is not None:
        if hasattr(schema, "model_dump"):
            schema = schema.model_dump()
        result["inputSchema"] = schema

    return result


def _result_to_dict(result: Any) -> dict[str, Any]:
    """Convert MCP result object to dictionary."""
    output = {
        "isError": getattr(result, "isError", False),
    }

    # Handle content
    content = getattr(result, "content", [])
    if content:
        output["content"] = [
            {"type": getattr(c, "type", "text"), "text": getattr(c, "text", None)}
            for c in content
        ]

    # Handle structured content
    structured = getattr(result, "structuredContent", None)
    if structured:
        if hasattr(structured, "model_dump"):
            structured = structured.model_dump()
        output["structuredContent"] = structured

    return output
