"""Logs screen for live container log viewing.

This module provides a live log viewer for Docker container
logs with filtering and auto-scroll capabilities.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, RichLog, Static

if TYPE_CHECKING:
    pass


class LogsScreen(Screen):
    """Live log viewer for Docker containers."""

    CSS = """
    LogsScreen {
        layout: grid;
        grid-size: 1;
        grid-rows: auto 1fr auto;
    }
    
    #logs-header {
        height: 3;
        padding: 1;
        background: $primary-darken-2;
    }
    
    #logs-container {
        height: 100%;
        padding: 1;
    }
    
    #logs-output {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    
    #filter-container {
        height: auto;
        padding: 1;
        dock: bottom;
    }
    
    #filter-input {
        width: 100%;
    }
    
    .log-info {
        color: $text;
    }
    
    .log-warning {
        color: $warning;
    }
    
    .log-error {
        color: $error;
        background: $error 10%;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+l", "clear_logs", "Clear"),
        Binding("f", "toggle_filter", "Filter"),
        Binding("space", "toggle_follow", "Follow"),
    ]

    def __init__(self, project_dir: Path | None = None):
        """Initialize logs screen.

        Args:
            project_dir: Project directory for Docker context
        """
        super().__init__()
        self.project_dir = project_dir or Path.cwd()
        self.following = True
        self.filter_text = ""
        self._log_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="logs-header"):
            yield Static(
                f"[bold]📋 Logs[/bold] - [dim]{self.project_dir.name}[/dim]",
                id="logs-title",
            )
        with Container(id="logs-container"):
            yield RichLog(id="logs-output", highlight=True, markup=True, auto_scroll=True)
        with Container(id="filter-container"):
            yield Input(
                placeholder="Filter logs... (press Enter to apply)",
                id="filter-input",
            )
        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        logs = self.query_one("#logs-output", RichLog)
        logs.write("[bold blue]📋 Container Logs[/bold blue]")
        logs.write("")
        logs.write("[dim]Press Space to toggle auto-scroll, F to filter.[/dim]")
        logs.write("[dim]Press Esc to go back, Ctrl+L to clear.[/dim]")
        logs.write("")

        # Start log streaming
        self._start_log_stream()

    def _start_log_stream(self) -> None:
        """Start streaming Docker logs."""
        logs = self.query_one("#logs-output", RichLog)
        logs.write("[dim]Looking for running containers...[/dim]")

        # Placeholder: would connect to Docker here
        logs.write("")
        logs.write("[yellow]⚠ No running containers found.[/yellow]")
        logs.write("[dim]Start an agent with:[/dim] [cyan]tx run[/cyan]")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle filter input."""
        self.filter_text = event.value.strip()
        logs = self.query_one("#logs-output", RichLog)

        if self.filter_text:
            logs.write(f"[dim]Filter applied: '{self.filter_text}'[/dim]")
        else:
            logs.write("[dim]Filter cleared[/dim]")

    def action_clear_logs(self) -> None:
        """Clear the log output."""
        logs = self.query_one("#logs-output", RichLog)
        logs.clear()
        logs.write("[dim]Logs cleared.[/dim]")

    def action_toggle_follow(self) -> None:
        """Toggle auto-scroll."""
        self.following = not self.following
        logs = self.query_one("#logs-output", RichLog)
        logs.auto_scroll = self.following

        status = "enabled" if self.following else "disabled"
        logs.write(f"[dim]Auto-scroll {status}[/dim]")

    def action_toggle_filter(self) -> None:
        """Focus the filter input."""
        self.query_one("#filter-input", Input).focus()
