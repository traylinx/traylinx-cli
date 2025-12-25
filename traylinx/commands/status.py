"""
Status command for Traylinx CLI.

Shows current authentication status, configuration, and environment info.
"""

from datetime import UTC, datetime

import typer
from rich.console import Console

from traylinx import __version__
from traylinx.auth import CREDENTIALS_FILE, AuthManager
from traylinx.branding import print_status_header
from traylinx.constants import get_settings

app = typer.Typer(help="Status commands")
console = Console()


@app.command("status")
def status():
    """Show current CLI status including auth and configuration."""
    settings = get_settings()

    # Branded header with logo
    print_status_header(version=__version__, environment=settings.env)

    # Auth status
    console.print("[bold]🔐 Authentication[/bold]")
    creds = AuthManager.get_credentials()

    if creds:
        user = creds.get("user", {})
        email = user.get("email", "unknown")
        expires_at_str = creds.get("expires_at")

        console.print("  Status: [green]✓ Logged in[/green]")
        console.print(f"  User: {email}")

        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                now = datetime.now(UTC)
                if expires_at > now:
                    remaining = expires_at - now
                    hours = remaining.total_seconds() / 3600
                    console.print(f"  Token: [green]Valid[/green] (expires in {hours:.1f}h)")
                else:
                    # Token expired - try to refresh
                    console.print("  Token: [yellow]Expired[/yellow] - attempting refresh...")
                    if AuthManager.refresh_token():
                        # Reload credentials after refresh
                        creds = AuthManager.get_credentials()
                        new_expires = creds.get("expires_at")
                        if new_expires:
                            new_dt = datetime.fromisoformat(new_expires)
                            hours = (new_dt - now).total_seconds() / 3600
                            console.print(
                                f"  Token: [green]Refreshed[/green] (expires in {hours:.1f}h)"
                            )
                    else:
                        console.print(
                            "  [dim]Refresh failed - run 'traylinx login' to re-authenticate[/dim]"
                        )
            except ValueError:
                pass

        console.print(f"  Credentials: {CREDENTIALS_FILE}")
    else:
        console.print("  Status: [yellow]Not logged in[/yellow]")
        console.print("  Run [cyan]traylinx login[/cyan] to authenticate")

    console.print()

    # Configuration
    console.print("[bold]⚙️  Configuration[/bold]")
    console.print(f"  Environment: {settings.env}")
    console.print(f"  Registry: {settings.effective_registry_url}")

    if settings.agent_key:
        console.print("  Agent Key: [green]✓ Set[/green]")
    else:
        console.print("  Agent Key: [dim]Not set[/dim]")

    if settings.secret_token:
        console.print("  Secret Token: [green]✓ Set[/green]")
    else:
        console.print("  Secret Token: [dim]Not set[/dim]")

    console.print()

    # Plugins
    from traylinx.plugins import discover_plugins

    plugins = discover_plugins()

    console.print("[bold]🔌 Plugins[/bold]")
    if plugins:
        for name in plugins.keys():
            console.print(f"  • {name}")
    else:
        console.print("  [dim]No plugins installed[/dim]")
        console.print("  Run [cyan]traylinx plugin install stargate[/cyan] to add features")

    console.print()


# Export for direct use
status_command = status
