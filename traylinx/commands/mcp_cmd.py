"""MCP commands for Traylinx CLI.

Commands to manage and interact with MCP servers:
- tx mcp list: List configured servers
- tx mcp add: Add a new server
- tx mcp remove: Remove a server
- tx mcp tools: List tools from a server
- tx mcp call: Execute a tool
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    pass


console = Console()

mcp_app = typer.Typer(
    name="mcp",
    help="MCP (Model Context Protocol) server management",
    no_args_is_help=True,
)


@mcp_app.command("list")
def list_command():
    """
    📋 List configured MCP servers.

    Shows all MCP servers configured in ~/.traylinx/mcp-servers.json
    """
    from traylinx.mcp import list_servers

    servers = list_servers()

    if not servers:
        console.print("[dim]No MCP servers configured.[/dim]")
        console.print("\n[dim]Add one with:[/dim] [cyan]tx mcp add <name>[/cyan]")
        return

    table = Table(title="MCP Servers", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Transport")
    table.add_column("Endpoint")
    table.add_column("Status")

    for srv in servers:
        endpoint = srv.url if srv.transport == "http" else " ".join(srv.command or [])
        status = "[green]✓ enabled[/green]" if srv.enabled else "[dim]disabled[/dim]"
        table.add_row(srv.name, srv.transport, endpoint[:50], status)

    console.print(table)


@mcp_app.command("add")
def add_command(
    name: str = typer.Argument(..., help="Server name (alphanumeric, dash, underscore)"),
    transport: str = typer.Option(
        "stdio",
        "--transport",
        "-t",
        help="Transport type: stdio or http",
    ),
    command: str | None = typer.Option(
        None,
        "--command",
        "-c",
        help="Command to start stdio server (e.g., 'python -m myserver')",
    ),
    url: str | None = typer.Option(
        None,
        "--url",
        "-u",
        help="URL for HTTP server",
    ),
    description: str | None = typer.Option(
        None,
        "--description",
        "-d",
        help="Server description",
    ),
):
    """
    ➕ Add an MCP server.

    [bold]Examples:[/bold]

        # Add a stdio server
        tx mcp add weather -t stdio -c "python -m weather_server"

        # Add an HTTP server
        tx mcp add api -t http -u http://localhost:8000/mcp
    """
    from traylinx.mcp import ServerConfig, add_server, get_server

    # Validate inputs
    if transport == "stdio" and not command:
        console.print("[red]Error:[/red] --command is required for stdio transport")
        raise typer.Exit(1) from None

    if transport in ("http", "streamable-http") and not url:
        console.print("[red]Error:[/red] --url is required for http transport")
        raise typer.Exit(1) from None

    # Parse command into list
    command_list = command.split() if command else None

    try:
        config = ServerConfig(
            name=name,
            transport=transport,
            command=command_list,
            url=url,
            description=description,
        )
    except ValueError as e:
        console.print(f"[red]Invalid config:[/red] {e}")
        raise typer.Exit(1) from None

    # Check if exists
    existing = get_server(name)
    if existing:
        if not typer.confirm(f"Server '{name}' already exists. Overwrite?"):
            raise typer.Exit(0)

    add_server(config)
    console.print(f"[green]✓[/green] Added MCP server: [cyan]{name}[/cyan]")
    console.print(f"[dim]Test with:[/dim] [cyan]tx mcp tools {name}[/cyan]")


@mcp_app.command("remove")
def remove_command(
    name: str = typer.Argument(..., help="Server name to remove"),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation",
    ),
):
    """
    ➖ Remove an MCP server.
    """
    from traylinx.mcp import get_server, remove_server

    server = get_server(name)
    if not server:
        console.print(f"[yellow]Server not found:[/yellow] {name}")
        raise typer.Exit(1) from None

    if not force and not typer.confirm(f"Remove server '{name}'?"):
        raise typer.Exit(0)

    remove_server(name)
    console.print(f"[green]✓[/green] Removed server: [cyan]{name}[/cyan]")


@mcp_app.command("tools")
def tools_command(
    server: str = typer.Argument(..., help="Server name"),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output as JSON",
    ),
):
    """
    🔧 List tools available from an MCP server.

    [bold]Example:[/bold]

        tx mcp tools weather
    """
    from traylinx.mcp import MCPClient, get_server
    from traylinx.mcp.client import MCPError

    config = get_server(server)
    if not config:
        console.print(f"[red]Server not found:[/red] {server}")
        console.print("[dim]List servers with:[/dim] [cyan]tx mcp list[/cyan]")
        raise typer.Exit(1) from None

    try:
        with console.status(f"Discovering tools from {server}..."):
            client = MCPClient(config)
            tools = client.list_tools_sync()

    except MCPError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    if not tools:
        console.print(f"[yellow]No tools found on server:[/yellow] {server}")
        return

    if json_output:
        output = [t.model_dump() for t in tools]
        console.print_json(json.dumps(output))
        return

    table = Table(title=f"Tools on '{server}'", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for tool in tools:
        desc = (tool.description or "")[:60]
        if len(tool.description or "") > 60:
            desc += "..."
        table.add_row(tool.name, desc)

    console.print(table)
    console.print(f"\n[dim]Call a tool:[/dim] [cyan]tx mcp call {server} <tool>[/cyan]")


@mcp_app.command("call")
def call_command(
    server: str = typer.Argument(..., help="Server name"),
    tool: str = typer.Argument(..., help="Tool name"),
    args: str = typer.Option(
        "{}",
        "--args",
        "-a",
        help="Tool arguments as JSON",
    ),
    timeout: float = typer.Option(
        60.0,
        "--timeout",
        "-t",
        help="Execution timeout in seconds",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output as JSON",
    ),
):
    """
    ▶️  Call an MCP tool.

    [bold]Examples:[/bold]

        tx mcp call weather get_forecast -a '{"city": "London"}'
        tx mcp call db query -a '{"sql": "SELECT * FROM users"}'
    """
    from traylinx.mcp import MCPClient, get_server
    from traylinx.mcp.client import MCPError

    config = get_server(server)
    if not config:
        console.print(f"[red]Server not found:[/red] {server}")
        raise typer.Exit(1) from None

    # Parse arguments
    try:
        arguments = json.loads(args)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON args:[/red] {e}")
        raise typer.Exit(1) from None

    try:
        with console.status(f"Calling {server}/{tool}..."):
            client = MCPClient(config, timeout=timeout)
            result = client.call_tool_sync(tool, arguments)

    except MCPError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    if json_output:
        console.print_json(result.model_dump_json())
        return

    if result.ok:
        console.print(f"[green]✓[/green] {server}/{tool}")
        console.print()
        console.print(Panel(result.content, title="Result"))
    else:
        console.print(f"[red]✗[/red] {server}/{tool}")
        console.print(f"[red]Error:[/red] {result.error}")
        raise typer.Exit(1) from None


@mcp_app.command("enable")
def enable_command(name: str = typer.Argument(..., help="Server name")):
    """Enable an MCP server."""
    from traylinx.mcp.registry import enable_server

    if enable_server(name):
        console.print(f"[green]✓[/green] Enabled: [cyan]{name}[/cyan]")
    else:
        console.print(f"[yellow]Server not found:[/yellow] {name}")
        raise typer.Exit(1) from None


@mcp_app.command("disable")
def disable_command(name: str = typer.Argument(..., help="Server name")):
    """Disable an MCP server."""
    from traylinx.mcp.registry import disable_server

    if disable_server(name):
        console.print(f"[green]✓[/green] Disabled: [cyan]{name}[/cyan]")
    else:
        console.print(f"[yellow]Server not found:[/yellow] {name}")
        raise typer.Exit(1) from None
