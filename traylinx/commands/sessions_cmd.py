"""Session management commands for Traylinx CLI.

This module provides commands for viewing and managing session logs
created by the SessionLogger.
"""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from traylinx.utils.session_logger import SessionLogger

console = Console()

app = typer.Typer(
    name="sessions",
    help="📜 Session logs & audit trail",
    no_args_is_help=True,
)


@app.command(name="list")
def list_command(
    limit: int = typer.Option(20, "--limit", "-l", help="Max sessions to show"),
):
    """List recent session logs.

    Shows a table of recent interaction sessions with message and tool counts.
    """
    sessions = SessionLogger.list_sessions(limit=limit)

    if not sessions:
        console.print("[dim]No sessions found.[/dim]")
        console.print(f"[dim]Session logs are saved to: {SessionLogger.SESSIONS_DIR}[/dim]")
        return

    table = Table(title="Recent Sessions")
    table.add_column("ID", style="cyan")
    table.add_column("Started")
    table.add_column("Messages", justify="right")
    table.add_column("Tools", justify="right")

    for s in sessions:
        table.add_row(
            s["session_id"],
            s["started_at"][:19].replace("T", " "),
            str(s["message_count"]),
            str(s["tool_count"]),
        )

    console.print(table)
    console.print(f"\n[dim]View details: traylinx sessions view <id>[/dim]")


@app.command(name="view")
def view_command(
    session_id: str = typer.Argument(..., help="Session ID (partial match OK)"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw JSON"),
):
    """View a specific session.

    Displays the full session log including metadata, messages, and tool calls.
    """
    session = SessionLogger.load_session(session_id)

    if not session:
        console.print(f"[red]Session not found:[/red] {session_id}")
        raise typer.Exit(1) from None

    if raw:
        console.print(json.dumps(session, indent=2))
        return

    # Metadata panel
    metadata = session.get("metadata", {})
    meta_lines = [
        f"[cyan]Session ID:[/cyan] {metadata.get('session_id', 'unknown')}",
        f"[cyan]Started:[/cyan] {metadata.get('started_at', 'unknown')}",
        f"[cyan]CWD:[/cyan] {metadata.get('cwd', 'unknown')}",
        f"[cyan]User:[/cyan] {metadata.get('user', 'unknown')}",
    ]

    if metadata.get("git"):
        git = metadata["git"]
        meta_lines.append(
            f"[cyan]Git:[/cyan] {git.get('branch', '')} @ {git.get('commit', '')} {'[dirty]' if git.get('dirty') else ''}"
        )

    if metadata.get("stargate"):
        sg = metadata["stargate"]
        meta_lines.append(
            f"[cyan]Stargate:[/cyan] {sg.get('peer_id', '')[:16]}..."
        )

    console.print(Panel("\n".join(meta_lines), title="Session Metadata"))

    # Messages
    messages = session.get("messages", [])
    if messages:
        console.print(f"\n[bold]Messages ({len(messages)}):[/bold]\n")
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:500]
            if role == "user":
                console.print(f"[bold blue]User:[/bold blue] {content}")
            elif role == "assistant":
                console.print(f"[bold green]Assistant:[/bold green] {content}")
            else:
                console.print(f"[bold dim]{role}:[/bold dim] {content}")
            console.print()

    # Tool calls
    tools = session.get("tool_calls", [])
    if tools:
        console.print(f"\n[bold]Tool Calls ({len(tools)}):[/bold]\n")
        for tool in tools:
            name = tool.get("tool", "unknown")
            duration = tool.get("duration_ms", "?")
            error = tool.get("error")

            status = "[red]ERROR[/red]" if error else f"[green]{duration}ms[/green]"
            console.print(f"  • [cyan]{name}[/cyan] - {status}")


# Standalone commands for top-level access
def sessions_list_command(
    limit: int = typer.Option(20, "--limit", "-l", help="Max sessions to show"),
):
    """List recent sessions (top-level alias)."""
    list_command(limit=limit)
