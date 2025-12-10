"""Plugin discovery and management for Traylinx CLI.

This module provides the plugin framework that allows external packages
to extend the traylinx CLI with additional commands.

Plugins register via Python entry points:

    [project.entry-points."traylinx.plugins"]
    stargate = "traylinx_stargate.cli:app"
"""

from __future__ import annotations

import sys
from importlib.metadata import entry_points, version as pkg_version
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    import typer

console = Console()

# Entry point group name for plugins
PLUGIN_GROUP = "traylinx.plugins"


def discover_plugins() -> dict[str, "typer.Typer"]:
    """
    Discover all installed traylinx plugins.
    
    Plugins register themselves via entry points in their pyproject.toml:
    
        [project.entry-points."traylinx.plugins"]
        myplugin = "my_package.cli:app"
    
    Returns:
        Dict mapping plugin name to Typer app
    """
    plugins: dict[str, typer.Typer] = {}
    
    try:
        # Python 3.10+ style
        eps = entry_points(group=PLUGIN_GROUP)
        
        for ep in eps:
            try:
                plugin_app = ep.load()
                plugins[ep.name] = plugin_app
            except Exception as e:
                # Log but don't crash if a plugin fails to load
                console.print(
                    f"[yellow]⚠ Warning: Failed to load plugin '{ep.name}': {e}[/yellow]",
                    highlight=False,
                )
    except Exception:
        # No plugins installed or entry_points failed
        pass
    
    return plugins


def get_plugin_version(name: str) -> str:
    """
    Get the version of an installed plugin.
    
    Args:
        name: Plugin name (e.g., 'stargate')
    
    Returns:
        Version string or 'unknown'
    """
    package_name = f"traylinx-{name}"
    try:
        return pkg_version(package_name)
    except Exception:
        # Try without prefix
        try:
            return pkg_version(name)
        except Exception:
            return "unknown"


def get_plugin_info(name: str) -> dict:
    """
    Get detailed information about a plugin.
    
    Args:
        name: Plugin name
    
    Returns:
        Dict with plugin information
    """
    plugins = discover_plugins()
    
    if name not in plugins:
        return {"error": f"Plugin '{name}' not installed"}
    
    plugin_app = plugins[name]
    version = get_plugin_version(name)
    
    # Get module for additional metadata
    module_name = plugin_app.__module__.split('.')[0] if hasattr(plugin_app, '__module__') else None
    module = sys.modules.get(module_name) if module_name else None
    
    # Extract commands from Typer app
    commands = []
    if hasattr(plugin_app, 'registered_commands'):
        commands = [cmd.name or cmd.callback.__name__ for cmd in plugin_app.registered_commands]
    
    return {
        "name": name,
        "version": version,
        "description": getattr(module, '__plugin_description__', plugin_app.info.help or ''),
        "commands": commands,
        "package": f"traylinx-{name}",
    }


def list_installed_plugins() -> list[dict]:
    """
    List all installed plugins with their information.
    
    Returns:
        List of plugin info dicts
    """
    plugins = discover_plugins()
    return [get_plugin_info(name) for name in plugins]
