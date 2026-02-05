"""Result formatters for command output.

Formats execution results for display using Rich.
"""

from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


console = Console()


class ResultType(Enum):
    """Type of result for formatting."""

    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"


def format_result(
    result_type: ResultType,
    message: str,
    details: dict | None = None,
    suggestions: list[str] | None = None,
) -> str:
    """Format a result for display.

    Args:
        result_type: Type of result (success, error, etc.)
        message: Main message
        details: Optional key-value details
        suggestions: Optional list of suggested next actions

    Returns:
        Formatted string for display
    """
    # Icon and color based on type
    icons = {
        ResultType.SUCCESS: ("✅", "green"),
        ResultType.ERROR: ("❌", "red"),
        ResultType.INFO: ("ℹ️", "blue"),
        ResultType.WARNING: ("⚠️", "yellow"),
    }

    icon, color = icons.get(result_type, ("", "white"))

    # Build output
    lines = [f"[{color}]{icon} {message}[/{color}]"]

    if details:
        lines.append("")
        for key, value in details.items():
            lines.append(f"  [dim]{key}:[/dim] {value}")

    if suggestions:
        lines.append("")
        lines.append("[dim]Suggestions:[/dim]")
        for suggestion in suggestions:
            lines.append(f"  → {suggestion}")

    return "\n".join(lines)


def display_result(
    result_type: ResultType,
    message: str,
    details: dict | None = None,
    suggestions: list[str] | None = None,
) -> None:
    """Format and display a result.

    Args:
        result_type: Type of result
        message: Main message
        details: Optional details
        suggestions: Optional suggestions
    """
    formatted = format_result(result_type, message, details, suggestions)
    console.print(formatted)


def format_command_output(
    command: str,
    stdout: str,
    stderr: str,
    exit_code: int,
    duration_ms: int,
) -> str:
    """Format command execution output.

    Args:
        command: The executed command
        stdout: Standard output
        stderr: Standard error
        exit_code: Exit code
        duration_ms: Duration in milliseconds

    Returns:
        Formatted output string
    """
    lines = []

    if exit_code == 0:
        lines.append(f"[green]✅ Command completed successfully[/green]")
    else:
        lines.append(f"[red]❌ Command failed (exit code: {exit_code})[/red]")

    lines.append(f"[dim]Duration: {duration_ms}ms[/dim]")
    lines.append("")

    if stdout.strip():
        lines.append(stdout.strip())

    if stderr.strip() and exit_code != 0:
        lines.append("")
        lines.append(f"[red]{stderr.strip()}[/red]")

    return "\n".join(lines)


def display_executing(command: str) -> None:
    """Display 'executing' message.

    Args:
        command: Command being executed
    """
    console.print(f"\n[bold blue]🤖 Executing:[/bold blue] [cyan]tx {command}[/cyan]\n")
