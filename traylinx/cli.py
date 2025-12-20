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
        
        # Show installed plugins
        from traylinx.plugins import discover_plugins
        plugins = discover_plugins()
        if plugins:
            console.print(f"[dim]Plugins: {', '.join(plugins.keys())}[/dim]")
        
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
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
    
    [bold]Docker-Powered Agent Commands:[/bold]
    
    • [cyan]traylinx run[/cyan] - Start agent via Docker Compose
    • [cyan]traylinx stop[/cyan] - Stop running agent
    • [cyan]traylinx logs[/cyan] - View agent logs
    • [cyan]traylinx list[/cyan] - List running agents
    
    [bold]Core Commands:[/bold]
    
    • [cyan]traylinx init[/cyan] - Create a new agent project
    • [cyan]traylinx validate[/cyan] - Validate your manifest
    • [cyan]traylinx publish[/cyan] - Publish to the catalog
    
    [bold]Plugin Commands:[/bold]
    
    • [cyan]traylinx plugin list[/cyan] - Show installed plugins
    • [cyan]traylinx plugin install[/cyan] - Install a plugin
    
    [bold]Configuration:[/bold]
    
    Set environment variables or create ~/.traylinx/config.yaml
    
    [dim]TRAYLINX_REGISTRY_URL[/dim] - API URL
    [dim]TRAYLINX_AGENT_KEY[/dim] - Your agent key
    [dim]TRAYLINX_SECRET_TOKEN[/dim] - Your secret token
    
    💡 [dim]Install more features:[/dim] [cyan]traylinx plugin install stargate[/cyan]
    """
    pass


# Import and register core commands
from traylinx.commands import init, validate, publish
from traylinx.commands import plugin as plugin_cmd
from traylinx.commands import auth as auth_cmd
from traylinx.commands import status as status_cmd
from traylinx.commands import help as help_cmd
from traylinx.commands import orgs as orgs_cmd
from traylinx.commands import projects as projects_cmd
from traylinx.commands import assets as assets_cmd
from traylinx.commands import open_cmd
from traylinx.commands import docker_cmd
from traylinx.commands import stargate as stargate_cmd


app.command(name="init")(init.init_command)
app.command(name="validate")(validate.validate_command)
app.command(name="publish")(publish.publish_command)
app.command(name="open")(open_cmd.open_command)


# Register auth commands
app.command(name="login")(auth_cmd.login_command)
app.command(name="logout")(auth_cmd.logout_command)
app.command(name="whoami")(auth_cmd.whoami_command)

# Register status command
app.command(name="status")(status_cmd.status_command)

# Register help command
app.command(name="help")(help_cmd.help_command)

# Register plugin management commands
app.add_typer(plugin_cmd.app, name="plugin")

# Register organization, project, and asset commands
app.add_typer(orgs_cmd.app, name="orgs")
app.add_typer(projects_cmd.app, name="projects")
app.add_typer(assets_cmd.app, name="assets")

# Register Docker-powered agent commands
app.command(name="run")(docker_cmd.run_command)
app.command(name="stop")(docker_cmd.stop_command)
app.command(name="logs")(docker_cmd.logs_command)
app.command(name="list")(docker_cmd.list_command)
app.command(name="publish")(docker_cmd.publish_command)
app.command(name="pull")(docker_cmd.pull_command)

# Register Stargate P2P commands
app.add_typer(stargate_cmd.app, name="stargate")

# Top-level aliases for common Stargate commands (Phase 2)
app.command(name="discover", help="Alias for 'stargate peers'")(stargate_cmd.peers_command)
app.command(name="call", help="Alias for 'stargate call'")(stargate_cmd.call_command)
app.command(name="certify", help="Alias for 'stargate certify'")(stargate_cmd.certify_command)


# Load plugins at import time so they're available for command matching
def _load_plugins():
    """Load all discovered plugins as sub-apps."""
    from traylinx.plugins import discover_plugins
    
    for name, plugin_app in discover_plugins().items():
        app.add_typer(plugin_app, name=name)


# Load plugins immediately
_load_plugins()


if __name__ == "__main__":
    app()
