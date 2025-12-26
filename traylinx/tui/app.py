"""Base Textual application for Traylinx CLI.

This module provides the main application class that hosts
all TUI screens (chat, logs, status).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

if TYPE_CHECKING:
    pass


class TraylinxApp(App):
    """Main Traylinx TUI application.

    Provides keyboard navigation between screens and
    a consistent header/footer across all views.
    """

    TITLE = "Traylinx"
    SUB_TITLE = "Agent Network CLI"

    CSS = """
    Screen {
        background: $surface;
    }
    
    Header {
        background: $primary;
    }
    
    Footer {
        background: $primary-darken-2;
    }
    
    #main-content {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .panel {
        border: solid $primary;
        padding: 1;
        margin: 1;
    }
    
    .status-ok {
        color: $success;
    }
    
    .status-warning {
        color: $warning;
    }
    
    .status-error {
        color: $error;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("c", "switch_chat", "Chat"),
        Binding("l", "switch_logs", "Logs"),
        Binding("s", "switch_status", "Status"),
        Binding("?", "show_help", "Help"),
    ]

    def __init__(
        self,
        project_dir: Path | None = None,
        agent_name: str | None = None,
    ):
        """Initialize the Traylinx TUI.

        Args:
            project_dir: Project directory (defaults to cwd)
            agent_name: Name of the agent to interact with
        """
        super().__init__()
        self.project_dir = project_dir or Path.cwd()
        self.agent_name = agent_name

    def compose(self) -> ComposeResult:
        """Create the main layout."""
        yield Header()
        yield Footer()

    def action_switch_chat(self) -> None:
        """Switch to the chat screen."""
        from .chat import ChatScreen

        self.push_screen(ChatScreen(self.project_dir))

    def action_switch_logs(self) -> None:
        """Switch to the logs screen."""
        from .logs import LogsScreen

        self.push_screen(LogsScreen(self.project_dir))

    def action_switch_status(self) -> None:
        """Switch to the status screen."""
        from .status import StatusScreen

        self.push_screen(StatusScreen(self.project_dir))

    def action_show_help(self) -> None:
        """Show help information."""
        self.notify(
            "Press [c]hat, [l]ogs, [s]tatus, or [q]uit",
            title="Keyboard Shortcuts",
        )
