"""Typer CLI interface for Cortex chat command.

This module provides the `chat` command that can be mounted
into the core traylinx-cli's cortex command group.
"""

from typing import Optional

import typer
from rich.console import Console


console = Console()

# Create the chat Typer app that will be imported by core CLI
chat_app = typer.Typer(
    name="chat",
    help="💬 Natural language interface for Traylinx",
    no_args_is_help=False,
)


@chat_app.callback(invoke_without_command=True)
def chat_command(
    ctx: typer.Context,
    message: Optional[str] = typer.Argument(
        None,
        help="Single message to process (non-interactive mode)",
    ),
    no_llm: bool = typer.Option(
        False,
        "--no-llm",
        help="Disable LLM-based classification (pattern matching only)",
    ),
) -> None:
    """Start an interactive chat session with Cortex.

    In interactive mode (no message argument), opens a REPL
    where you can type natural language commands.

    In single-message mode, processes one command and exits.

    Examples:
        tx cortex chat
        tx cortex chat "start my agent"
        tx cortex chat "show logs" --no-llm
    """
    from traylinx.cortex.chat.repl import ChatREPL

    use_llm = not no_llm
    repl = ChatREPL(use_llm=use_llm)

    if message:
        # Single message mode
        result = repl.process_input(message)
        if result and result.formatted_output:
            console.print(result.formatted_output)
    else:
        # Interactive mode
        repl.run()


# Export the app for mounting in core CLI
def get_chat_app() -> typer.Typer:
    """Get the chat Typer app for mounting in core CLI."""
    return chat_app
