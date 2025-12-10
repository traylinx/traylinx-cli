"""Plugin management commands for traylinx CLI.

Commands:
    traylinx plugin list    - Show installed plugins
    traylinx plugin info    - Show plugin details
    traylinx plugin install - Install a plugin
    traylinx plugin remove  - Remove a plugin
"""

import subprocess
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from traylinx.plugins import (
    discover_plugins,
    get_plugin_info,
    get_plugin_version,
    list_installed_plugins,
)

app = typer.Typer(
    name="plugin",
    help="Manage traylinx CLI plugins",
    no_args_is_help=True,
)

console = Console()


@app.command("list")
def list_plugins():
    """
    List all installed plugins.
    
    Shows plugin name, version, and available commands.
    """
    plugins = list_installed_plugins()
    
    if not plugins:
        console.print("\n[dim]No plugins installed.[/dim]")
        console.print("\n💡 Install a plugin with: [cyan]traylinx plugin install <name>[/cyan]")
        console.print("\nAvailable plugins:")
        console.print("  • [cyan]stargate[/cyan] - P2P networking for agents")
        console.print("  • [cyan]templates[/cyan] - Extended agent templates")
        console.print("  • [cyan]dev[/cyan] - Local development tools")
        return
    
    table = Table(
        title="Installed Plugins",
        title_style="bold blue",
        header_style="bold",
    )
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Commands", style="yellow")
    table.add_column("Description")
    
    for plugin in plugins:
        if "error" in plugin:
            continue
        table.add_row(
            plugin["name"],
            plugin["version"],
            ", ".join(plugin.get("commands", [])) or "-",
            plugin.get("description", "")[:50] or "-",
        )
    
    console.print()
    console.print(table)
    console.print()


@app.command("info")
def plugin_info(
    name: str = typer.Argument(..., help="Plugin name"),
):
    """
    Show detailed information about a plugin.
    """
    info = get_plugin_info(name)
    
    if "error" in info:
        console.print(f"\n[red]✗ {info['error']}[/red]")
        raise typer.Exit(1)
    
    content = f"""
[bold]Version:[/bold] {info['version']}
[bold]Package:[/bold] {info['package']}
[bold]Description:[/bold] {info.get('description') or 'No description'}

[bold]Commands:[/bold]
"""
    for cmd in info.get("commands", []):
        content += f"  • [cyan]traylinx {name} {cmd}[/cyan]\n"
    
    if not info.get("commands"):
        content += "  [dim]No commands[/dim]\n"
    
    console.print()
    console.print(Panel(
        content.strip(),
        title=f"[bold blue]{name}[/bold blue]",
        border_style="blue",
    ))
    console.print()


@app.command("install")
def install_plugin(
    name: str = typer.Argument(..., help="Plugin name or path"),
    upgrade: bool = typer.Option(False, "--upgrade", "-U", help="Upgrade if already installed"),
):
    """
    Install a plugin from PyPI.
    
    Examples:
        traylinx plugin install stargate
        traylinx plugin install ./my-local-plugin
        traylinx plugin install stargate --upgrade
    """
    # Determine package name
    if name.startswith("./") or name.startswith("/"):
        # Local path
        package = name
        display_name = name.split("/")[-1]
    else:
        # PyPI package
        package = f"traylinx-{name}"
        display_name = name
    
    # Build pip command
    cmd = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        cmd.append("--upgrade")
    cmd.append(package)
    
    console.print(f"\n[bold]Installing {display_name}...[/bold]\n")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            version = get_plugin_version(name if not name.startswith(("./", "/")) else display_name)
            console.print(f"[green]✓ Installed {display_name}[/green] v{version}")
            console.print(f"\n💡 Use: [cyan]traylinx {name} --help[/cyan]")
        else:
            console.print(f"[red]✗ Failed to install {display_name}[/red]")
            if "Could not find a version" in result.stderr or "No matching distribution" in result.stderr:
                console.print(f"\n[dim]Package '{package}' not found on PyPI.[/dim]")
            else:
                console.print(f"\n[dim]{result.stderr}[/dim]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("remove")
def remove_plugin(
    name: str = typer.Argument(..., help="Plugin name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Remove an installed plugin.
    """
    # Check if installed
    plugins = discover_plugins()
    if name not in plugins:
        console.print(f"\n[red]✗ Plugin '{name}' is not installed[/red]")
        raise typer.Exit(1)
    
    # Confirm
    if not yes:
        confirm = typer.confirm(f"Remove plugin '{name}'?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)
    
    package = f"traylinx-{name}"
    
    console.print(f"\n[bold]Removing {name}...[/bold]\n")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", package],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            console.print(f"[green]✓ Removed {name}[/green]")
        else:
            console.print(f"[red]✗ Failed to remove {name}[/red]")
            console.print(f"\n[dim]{result.stderr}[/dim]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("update")
def update_plugin(
    name: str = typer.Argument(..., help="Plugin name"),
):
    """
    Update a plugin to the latest version.
    """
    # Just call install with --upgrade
    install_plugin(name, upgrade=True)
