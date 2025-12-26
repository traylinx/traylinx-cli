"""Chat command for interactive TUI conversations.

This module implements the `tx chat` command for interactive
agent conversations using the Textual TUI framework.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console

if TYPE_CHECKING:
    pass


console = Console()


def chat_command(
    path: Path | None = typer.Argument(
        None,
        help="Path to agent project (default: current directory)",
    ),
    model: str = typer.Option(
        "gemini-2.0-flash",
        "--model",
        "-m",
        help="Model to use for chat",
    ),
    no_context: bool = typer.Option(
        False,
        "--no-context",
        help="Disable TRAYLINX.md context loading",
    ),
):
    """
    🗣️ Interactive chat with your agent.

    Opens an interactive TUI for chatting with an agent.
    Supports TRAYLINX.md project context and conversation history.

    [bold]Examples:[/bold]

        tx chat                    # Chat in current directory
        tx chat ./my-agent         # Chat with specific agent
        tx chat --model gpt-4      # Use different model

    [bold]Keyboard Shortcuts:[/bold]

        Enter     Send message
        Escape    Exit chat
        Ctrl+L    Clear chat history
    """
    project_dir = Path(path) if path else Path.cwd()
    project_dir = project_dir.resolve()

    if not project_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {project_dir}")
        raise typer.Exit(1) from None

    # Check for TRAYLINX.md context
    if not no_context:
        from traylinx.context import load_traylinx_md

        context = load_traylinx_md(project_dir)
        if context:
            console.print(
                f"[dim]Context:[/dim] Loaded from [cyan]{context.source_path.name}[/cyan]"
            )

    console.print(f"[dim]Project:[/dim] {project_dir.name}")
    console.print(f"[dim]Model:[/dim] {model}")
    console.print()

    # Launch TUI
    try:
        from traylinx.tui import TraylinxApp, ChatScreen

        app = TraylinxApp(project_dir=project_dir)
        app.push_screen(ChatScreen(project_dir))
        app.run()

    except ImportError as e:
        console.print(
            "[yellow]Textual TUI not available.[/yellow]\n"
            f"[dim]Error: {e}[/dim]\n"
            "[dim]Install with:[/dim] [cyan]pip install textual[/cyan]"
        )
        raise typer.Exit(1) from None


def logs_command(
    path: Path | None = typer.Argument(
        None,
        help="Path to agent project (default: current directory)",
    ),
    follow: bool = typer.Option(
        True,
        "--follow/--no-follow",
        "-f",
        help="Follow log output",
    ),
    filter_text: str | None = typer.Option(
        None,
        "--filter",
        help="Filter logs by text",
    ),
):
    """
    📋 View agent logs with live filtering.

    Opens an interactive TUI for viewing and filtering agent logs.

    [bold]Examples:[/bold]

        tx logs                    # View logs in current directory
        tx logs --no-follow        # Don't auto-scroll
        tx logs --filter error     # Filter by text
    """
    project_dir = Path(path) if path else Path.cwd()
    project_dir = project_dir.resolve()

    if not project_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {project_dir}")
        raise typer.Exit(1) from None

    try:
        from traylinx.tui import TraylinxApp, LogsScreen

        app = TraylinxApp(project_dir=project_dir)
        app.push_screen(LogsScreen(project_dir))
        app.run()

    except ImportError as e:
        console.print(
            "[yellow]Textual TUI not available.[/yellow]\n"
            f"[dim]Error: {e}[/dim]\n"
            "[dim]Install with:[/dim] [cyan]pip install textual[/cyan]"
        )
        raise typer.Exit(1) from None


def dashboard_command(
    path: Path | None = typer.Argument(
        None,
        help="Path to agent project (default: current directory)",
    ),
):
    """
    📊 Open the agent status dashboard.

    Shows real-time status of running agents, Docker containers,
    and project context.

    [bold]Examples:[/bold]

        tx dashboard               # Open dashboard
        tx dashboard ./my-agent    # Dashboard for specific project
    """
    project_dir = Path(path) if path else Path.cwd()
    project_dir = project_dir.resolve()

    if not project_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {project_dir}")
        raise typer.Exit(1) from None

    try:
        from traylinx.tui import TraylinxApp, StatusScreen

        app = TraylinxApp(project_dir=project_dir)
        app.push_screen(StatusScreen(project_dir))
        app.run()

    except ImportError as e:
        console.print(
            "[yellow]Textual TUI not available.[/yellow]\n"
            f"[dim]Error: {e}[/dim]\n"
            "[dim]Install with:[/dim] [cyan]pip install textual[/cyan]"
        )
        raise typer.Exit(1) from None
