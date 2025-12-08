"""Traylinx CLI - Main application entry point."""

import typer
from rich.console import Console

from traylinx import __version__
from traylinx.constants import get_settings


# Create main app
app = typer.Typer(
    name="traylinx",
    help="CLI for the Traylinx Agent Network",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        settings = get_settings()
        console.print(f"[bold blue]traylinx[/bold blue] v{__version__}")
        console.print(f"[dim]Environment: {settings.env}[/dim]")
        console.print(f"[dim]Registry: {settings.effective_registry_url}[/dim]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
):
    """
    [bold blue]Traylinx CLI[/bold blue] - Build and publish agents to the Traylinx Network.
    
    [bold]Commands:[/bold]
    
    • [cyan]traylinx init[/cyan] - Create a new agent project
    • [cyan]traylinx validate[/cyan] - Validate your manifest
    • [cyan]traylinx publish[/cyan] - Publish to the catalog
    
    [bold]Configuration:[/bold]
    
    Set environment variables or create ~/.traylinx/config.yaml
    
    [dim]TRAYLINX_REGISTRY_URL[/dim] - API URL
    [dim]TRAYLINX_AGENT_KEY[/dim] - Your agent key
    [dim]TRAYLINX_SECRET_TOKEN[/dim] - Your secret token
    """
    pass


# Import and register commands
from traylinx.commands import init, validate, publish

app.command(name="init")(init.init_command)
app.command(name="validate")(validate.validate_command)
app.command(name="publish")(publish.publish_command)


if __name__ == "__main__":
    app()
