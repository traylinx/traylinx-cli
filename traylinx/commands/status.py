"""
Status command for Traylinx CLI.

Shows current authentication status, configuration, and environment info.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime, timezone

from traylinx import __version__
from traylinx.constants import get_settings
from traylinx.auth import AuthManager, CREDENTIALS_FILE
from traylinx.branding import print_status_header
from traylinx.context import ContextManager

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
        
        console.print(f"  Status: [green]✓ Logged in[/green]")
        console.print(f"  User: {email}")
        
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                now = datetime.now(timezone.utc)
                if expires_at > now:
                    remaining = expires_at - now
                    hours = remaining.total_seconds() / 3600
                    console.print(f"  Token: [green]Valid[/green] (expires in {hours:.1f}h)")
                else:
                    # Token expired - try to refresh
                    console.print(f"  Token: [yellow]Expired[/yellow] - attempting refresh...")
                    if AuthManager.refresh_token():
                        # Reload credentials after refresh
                        creds = AuthManager.get_credentials()
                        new_expires = creds.get("expires_at")
                        if new_expires:
                            new_dt = datetime.fromisoformat(new_expires)
                            hours = (new_dt - now).total_seconds() / 3600
                            console.print(f"  Token: [green]Refreshed[/green] (expires in {hours:.1f}h)")
                    else:
                        console.print(f"  [dim]Refresh failed - run 'traylinx login' to re-authenticate[/dim]")
            except ValueError:
                pass
        
        console.print(f"  Credentials: {CREDENTIALS_FILE}")
    else:
        console.print(f"  Status: [yellow]Not logged in[/yellow]")
        console.print(f"  Run [cyan]traylinx login[/cyan] to authenticate")
    
    console.print()
    
    # Configuration
    console.print("[bold]⚙️  Configuration[/bold]")
    console.print(f"  Environment: {settings.env}")
    console.print(f"  Registry: {settings.effective_registry_url}")
    
    if settings.agent_key:
        console.print(f"  Agent Key: [green]✓ Set[/green]")
    else:
        console.print(f"  Agent Key: [dim]Not set[/dim]")
    
    if settings.secret_token:
        console.print(f"  Secret Token: [green]✓ Set[/green]")
    else:
        console.print(f"  Secret Token: [dim]Not set[/dim]")
    
    console.print()
    
    # Plugins
    from traylinx.plugins import discover_plugins
    plugins = discover_plugins()
    
    console.print("[bold]🔌 Plugins[/bold]")
    if plugins:
        for name in plugins.keys():
            console.print(f"  • {name}")
    else:
        console.print(f"  [dim]No plugins installed[/dim]")
        console.print(f"  Run [cyan]traylinx plugin install stargate[/cyan] to add features")
    
    console.print()


# Export for direct use
status_command = status
