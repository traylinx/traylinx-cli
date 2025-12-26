"""MCP server registry for configuration management.

Stores MCP server configurations in ~/.traylinx/mcp-servers.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .models import ServerConfig


# Config file location
MCP_CONFIG_FILE = Path.home() / ".traylinx" / "mcp-servers.json"


def _ensure_config_dir() -> None:
    """Ensure config directory exists."""
    MCP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict:
    """Load configuration from file."""
    if not MCP_CONFIG_FILE.exists():
        return {"servers": []}

    try:
        with open(MCP_CONFIG_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"servers": []}


def _save_config(config: dict) -> None:
    """Save configuration to file."""
    _ensure_config_dir()
    with open(MCP_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def list_servers() -> list[ServerConfig]:
    """List all configured MCP servers.

    Returns:
        List of ServerConfig objects
    """
    config = _load_config()
    servers = []

    for srv in config.get("servers", []):
        try:
            servers.append(ServerConfig.model_validate(srv))
        except Exception:
            # Skip invalid entries
            continue

    return servers


def get_server(name: str) -> ServerConfig | None:
    """Get a server configuration by name.

    Args:
        name: Server name

    Returns:
        ServerConfig if found, None otherwise
    """
    for srv in list_servers():
        if srv.name == name:
            return srv
    return None


def add_server(server: ServerConfig) -> None:
    """Add or update an MCP server configuration.

    Args:
        server: Server configuration to add
    """
    config = _load_config()
    servers = config.get("servers", [])

    # Find and update existing, or append new
    found = False
    for i, srv in enumerate(servers):
        if srv.get("name") == server.name:
            servers[i] = server.model_dump()
            found = True
            break

    if not found:
        servers.append(server.model_dump())

    config["servers"] = servers
    _save_config(config)


def remove_server(name: str) -> bool:
    """Remove an MCP server configuration.

    Args:
        name: Server name to remove

    Returns:
        True if server was removed, False if not found
    """
    config = _load_config()
    servers = config.get("servers", [])

    original_count = len(servers)
    servers = [s for s in servers if s.get("name") != name]

    if len(servers) == original_count:
        return False

    config["servers"] = servers
    _save_config(config)
    return True


def update_server(name: str, **updates) -> bool:
    """Update specific fields of a server configuration.

    Args:
        name: Server name to update
        **updates: Fields to update

    Returns:
        True if server was updated, False if not found
    """
    server = get_server(name)
    if not server:
        return False

    # Apply updates
    server_dict = server.model_dump()
    server_dict.update(updates)

    try:
        updated = ServerConfig.model_validate(server_dict)
        add_server(updated)
        return True
    except Exception:
        return False


def enable_server(name: str) -> bool:
    """Enable an MCP server.

    Args:
        name: Server name

    Returns:
        True if enabled, False if not found
    """
    return update_server(name, enabled=True)


def disable_server(name: str) -> bool:
    """Disable an MCP server.

    Args:
        name: Server name

    Returns:
        True if disabled, False if not found
    """
    return update_server(name, enabled=False)


def get_enabled_servers() -> list[ServerConfig]:
    """Get all enabled MCP servers.

    Returns:
        List of enabled ServerConfig objects
    """
    return [s for s in list_servers() if s.enabled]


def get_config_path() -> Path:
    """Get the path to the MCP config file.

    Returns:
        Path to mcp-servers.json
    """
    return MCP_CONFIG_FILE
