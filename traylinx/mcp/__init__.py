"""MCP (Model Context Protocol) integration for Traylinx CLI.

This module provides MCP client functionality:
- Server configuration management
- Tool discovery and execution
- HTTP and stdio transport support
"""

from .models import RemoteTool, ToolResult, ServerConfig
from .registry import list_servers, add_server, remove_server, get_server
from .client import MCPClient

__all__ = [
    # Models
    "RemoteTool",
    "ToolResult",
    "ServerConfig",
    # Registry
    "list_servers",
    "add_server",
    "remove_server",
    "get_server",
    # Client
    "MCPClient",
]
