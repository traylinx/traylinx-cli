"""MCP Client for interacting with MCP servers.

Provides a high-level interface for tool discovery and execution.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from .models import MCPCallResult, RemoteTool, ServerConfig, ToolResult
from .transports import (
    call_tool_http,
    call_tool_stdio,
    list_tools_http,
    list_tools_stdio,
)

if TYPE_CHECKING:
    pass


class MCPError(Exception):
    """Error from MCP operations."""

    pass


class MCPClient:
    """Client for interacting with MCP servers.

    Supports both stdio and HTTP transports.
    """

    def __init__(
        self,
        config: ServerConfig,
        timeout: float = 30.0,
    ):
        """Initialize MCP client.

        Args:
            config: Server configuration
            timeout: Default timeout for operations
        """
        self.config = config
        self.timeout = timeout

        # Validate config
        errors = config.validate_config()
        if errors:
            raise MCPError(f"Invalid config: {'; '.join(errors)}")

    @property
    def name(self) -> str:
        """Get server name."""
        return self.config.name

    @property
    def transport(self) -> str:
        """Get transport type."""
        return self.config.transport

    async def list_tools(self) -> list[RemoteTool]:
        """Discover available tools from the server.

        Returns:
            List of RemoteTool objects

        Raises:
            MCPError: If discovery fails
        """
        try:
            if self.config.transport == "stdio":
                if not self.config.command:
                    raise MCPError("No command configured for stdio server")

                raw_tools = await list_tools_stdio(
                    command=self.config.command,
                    env=self.config.env or None,
                    timeout=self.timeout,
                )
            else:  # http or streamable-http
                if not self.config.url:
                    raise MCPError("No URL configured for HTTP server")

                raw_tools = await list_tools_http(
                    url=self.config.url,
                    headers=self.config.headers or None,
                    timeout=self.timeout,
                )

            # Convert to RemoteTool objects
            tools = []
            for raw in raw_tools:
                tool = RemoteTool.model_validate(raw)
                tool.server_name = self.config.name
                tools.append(tool)

            return tools

        except asyncio.TimeoutError:
            raise MCPError(f"Timeout discovering tools from {self.name}")
        except Exception as e:
            raise MCPError(f"Failed to discover tools from {self.name}: {e}")

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ToolResult:
        """Call a tool on the server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments (defaults to empty dict)
            timeout: Execution timeout (uses default if not specified)

        Returns:
            ToolResult with call outcome

        Raises:
            MCPError: If call fails
        """
        arguments = arguments or {}
        timeout = timeout or self.timeout

        try:
            if self.config.transport == "stdio":
                if not self.config.command:
                    raise MCPError("No command configured for stdio server")

                raw_result = await call_tool_stdio(
                    command=self.config.command,
                    tool_name=tool_name,
                    arguments=arguments,
                    env=self.config.env or None,
                    timeout=timeout,
                )
            else:  # http or streamable-http
                if not self.config.url:
                    raise MCPError("No URL configured for HTTP server")

                raw_result = await call_tool_http(
                    url=self.config.url,
                    tool_name=tool_name,
                    arguments=arguments,
                    headers=self.config.headers or None,
                    timeout=timeout,
                )

            # Parse result
            parsed = MCPCallResult.model_validate(raw_result)
            return parsed.to_tool_result(self.name, tool_name)

        except asyncio.TimeoutError:
            return ToolResult(
                ok=False,
                server=self.name,
                tool=tool_name,
                error=f"Timeout after {timeout}s",
            )
        except MCPError:
            raise
        except Exception as e:
            return ToolResult(
                ok=False,
                server=self.name,
                tool=tool_name,
                error=str(e),
            )

    def list_tools_sync(self) -> list[RemoteTool]:
        """Synchronous wrapper for list_tools.

        Returns:
            List of RemoteTool objects
        """
        return asyncio.run(self.list_tools())

    def call_tool_sync(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ToolResult:
        """Synchronous wrapper for call_tool.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            timeout: Execution timeout

        Returns:
            ToolResult with call outcome
        """
        return asyncio.run(self.call_tool(tool_name, arguments, timeout))


def create_client(name: str) -> MCPClient:
    """Create an MCPClient for a configured server.

    Args:
        name: Server name from registry

    Returns:
        MCPClient instance

    Raises:
        MCPError: If server not found
    """
    from .registry import get_server

    config = get_server(name)
    if not config:
        raise MCPError(f"Server '{name}' not found in registry")

    if not config.enabled:
        raise MCPError(f"Server '{name}' is disabled")

    return MCPClient(config)


async def discover_all_tools() -> dict[str, list[RemoteTool]]:
    """Discover tools from all enabled MCP servers.

    Returns:
        Dict mapping server name to list of tools
    """
    from .registry import get_enabled_servers

    results: dict[str, list[RemoteTool]] = {}
    servers = get_enabled_servers()

    for config in servers:
        try:
            client = MCPClient(config)
            tools = await client.list_tools()
            results[config.name] = tools
        except Exception:
            # Skip servers that fail
            results[config.name] = []

    return results
