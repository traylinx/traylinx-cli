"""Chat screen for interactive agent conversation.

This module provides an interactive chat interface for
conversing with Traylinx agents using Textual.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, RichLog, Static

if TYPE_CHECKING:
    pass


class ChatMessage(Static):
    """A single chat message widget."""

    def __init__(
        self,
        content: str,
        role: str = "user",
        timestamp: datetime | None = None,
    ):
        self.role = role
        self.timestamp = timestamp or datetime.now()
        self.message_content = content

        # Style based on role
        if role == "user":
            classes = "chat-message user-message"
        elif role == "assistant":
            classes = "chat-message assistant-message"
        else:
            classes = "chat-message system-message"

        super().__init__(classes=classes)

    def compose(self) -> ComposeResult:
        time_str = self.timestamp.strftime("%H:%M")
        yield Static(f"[dim]{time_str}[/dim] [bold]{self.role}:[/bold]")
        yield Static(self.message_content)


class ChatScreen(Screen):
    """Interactive chat screen for agent conversation."""

    CSS = """
    ChatScreen {
        layout: grid;
        grid-size: 1;
        grid-rows: 1fr auto;
    }
    
    #chat-container {
        height: 100%;
        overflow-y: auto;
        padding: 1;
    }
    
    #chat-log {
        height: 100%;
        padding: 1;
        border: solid $primary;
    }
    
    #input-container {
        height: auto;
        padding: 1;
        dock: bottom;
    }
    
    #chat-input {
        width: 100%;
    }
    
    .chat-message {
        margin-bottom: 1;
        padding: 1;
    }
    
    .user-message {
        background: $primary-darken-3;
        border-left: thick $primary;
    }
    
    .assistant-message {
        background: $surface;
        border-left: thick $success;
    }
    
    .system-message {
        background: $surface-darken-1;
        border-left: thick $warning;
        color: $warning;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+l", "clear_chat", "Clear"),
    ]

    def __init__(self, project_dir: Path | None = None):
        """Initialize chat screen.

        Args:
            project_dir: Project directory for context
        """
        super().__init__()
        self.project_dir = project_dir or Path.cwd()
        self.messages: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="chat-container"):
            yield RichLog(id="chat-log", highlight=True, markup=True)
        with Container(id="input-container"):
            yield Input(
                placeholder="Type your message... (Enter to send, Esc to go back)",
                id="chat-input",
            )
        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write("[bold blue]🗣️ Traylinx Chat[/bold blue]")
        chat_log.write("")
        chat_log.write("[dim]Type your message and press Enter to send.[/dim]")
        chat_log.write("[dim]Press Esc to go back, Ctrl+L to clear.[/dim]")
        chat_log.write("")

        # Load project context
        self._load_context()

        # Focus input
        self.query_one("#chat-input", Input).focus()

    def _load_context(self) -> None:
        """Load TRAYLINX.md context if available."""
        from traylinx.context import load_traylinx_md

        context = load_traylinx_md(self.project_dir)
        if context:
            chat_log = self.query_one("#chat-log", RichLog)
            chat_log.write(
                f"[green]✓[/green] Loaded context from [cyan]{context.source_path.name}[/cyan]"
            )
            chat_log.write("")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle message submission."""
        message = event.value.strip()
        if not message:
            return

        # Clear input
        event.input.value = ""

        # Add user message to log
        chat_log = self.query_one("#chat-log", RichLog)
        time_str = datetime.now().strftime("%H:%M")
        chat_log.write(f"[dim]{time_str}[/dim] [bold cyan]You:[/bold cyan]")
        chat_log.write(f"  {message}")
        chat_log.write("")

        # Store message
        self.messages.append({"role": "user", "content": message})

        # Simulate assistant response (placeholder for actual agent integration)
        await self._send_to_agent(message, chat_log)

    async def _send_to_agent(self, message: str, chat_log: RichLog) -> None:
        """Send message to agent and stream response.

        This is a placeholder for actual agent integration.
        """
        # Show typing indicator
        chat_log.write("[dim]Agent is thinking...[/dim]")

        # Placeholder response
        time_str = datetime.now().strftime("%H:%M")
        chat_log.write(f"[dim]{time_str}[/dim] [bold green]Agent:[/bold green]")
        chat_log.write(
            "  [dim]Agent integration coming soon. "
            "This is a placeholder response.[/dim]"
        )
        chat_log.write("")

        # Store response
        self.messages.append({
            "role": "assistant",
            "content": "Agent integration coming soon.",
        })

    def action_clear_chat(self) -> None:
        """Clear the chat log."""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.clear()
        self.messages.clear()
        chat_log.write("[dim]Chat cleared.[/dim]")
        chat_log.write("")
