"""Confirmation gate for command execution.

Provides user confirmation prompts before executing
potentially destructive or sensitive commands.
"""

from enum import Enum
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from traylinx.cortex.types import ConfirmationLevel


console = Console()


class ConfirmationGate:
    """Gates command execution behind user confirmation.

    Supports three levels:
    - NONE: Execute immediately
    - SOFT: Show command, auto-proceed after delay
    - HARD: Require explicit yes/no
    """

    def __init__(self, level: ConfirmationLevel):
        self.level = level

    def check(self, command: str, description: str | None = None) -> bool:
        """Check if user confirms execution.

        Args:
            command: The CLI command to execute
            description: Optional description of what the command does

        Returns:
            True if confirmed, False if cancelled
        """
        if self.level == ConfirmationLevel.NONE:
            return True

        # Display the command
        panel_content = f"[bold]$ {command}[/bold]"
        if description:
            panel_content += f"\n\n[dim]{description}[/dim]"

        console.print(
            Panel(
                panel_content,
                title="[yellow]About to execute[/yellow]",
                border_style="yellow",
            )
        )

        if self.level == ConfirmationLevel.SOFT:
            # Show countdown, allow interrupt
            import time

            console.print("[dim]Executing in 2 seconds... (Ctrl+C to cancel)[/dim]")
            try:
                time.sleep(2)
                return True
            except KeyboardInterrupt:
                console.print("\n[yellow]Cancelled[/yellow]")
                return False

        elif self.level == ConfirmationLevel.HARD:
            # Require explicit confirmation
            return Confirm.ask("Continue?", default=False)

        return True


def get_confirmation(
    command: str,
    level: ConfirmationLevel = ConfirmationLevel.NONE,
    description: str | None = None,
) -> bool:
    """Convenience function to get user confirmation.

    Args:
        command: Command to execute
        level: Confirmation level required
        description: Optional description

    Returns:
        True if confirmed
    """
    gate = ConfirmationGate(level)
    return gate.check(command, description)


# Command descriptions for confirmation prompts
COMMAND_DESCRIPTIONS: dict[str, str] = {
    "publish": "This will publish your agent to the public registry.",
    "delete": "This will permanently delete the resource.",
    "stop": "This will stop the running agent.",
    "logout": "This will end your current session.",
    "destroy": "This will destroy all resources.",
}


def get_command_description(command: str) -> str | None:
    """Get description for a command.

    Args:
        command: Command name

    Returns:
        Description if available
    """
    return COMMAND_DESCRIPTIONS.get(command)
