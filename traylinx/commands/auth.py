"""
Authentication commands for Traylinx CLI.

Commands:
- login: Authenticate via browser
- logout: Clear stored credentials
- whoami: Show current user info
"""

import typer
from rich.console import Console
from rich.table import Table
from datetime import datetime

from traylinx.auth import AuthManager, AuthError

app = typer.Typer(help="Authentication commands")
console = Console()


@app.command("login")
def login(
    no_browser: bool = typer.Option(
        False,
        "--no-browser",
        help="Don't auto-open browser, just show URL"
    )
):
    """Log in to your Traylinx account via browser."""
    # Check if already logged in
    if AuthManager.is_logged_in():
        user = AuthManager.get_user()
        email = user.get("email", "unknown") if user else "unknown"
        console.print(f"[green]Already logged in as {email}[/green]")
        console.print("Use [cyan]traylinx logout[/cyan] to switch accounts.")
        return
    
    try:
        AuthManager.login(no_browser=no_browser)
    except AuthError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Login cancelled.[/yellow]")
        raise typer.Exit(1)


@app.command("logout")
def logout(
    all_devices: bool = typer.Option(
        False,
        "--all-devices",
        help="Logout from all devices, not just this CLI"
    )
):
    """Log out of your Traylinx account."""
    if not AuthManager.is_logged_in():
        console.print("[yellow]Not logged in.[/yellow]")
        return
    
    # Get user info before clearing
    user = AuthManager.get_user()
    email = user.get("email", "unknown") if user else "unknown"
    
    # Revoke token on backend
    AuthManager.revoke_token(all_devices=all_devices)
    
    # Clear local credentials
    AuthManager.clear_credentials()
    
    if all_devices:
        console.print(f"[green]✅ Logged out from {email} on all devices[/green]")
    else:
        console.print(f"[green]✅ Logged out from {email}[/green]")


@app.command("whoami")
def whoami():
    """Show currently logged-in user information."""
    creds = AuthManager.get_credentials()
    
    if not creds:
        console.print("[yellow]Not logged in.[/yellow]")
        console.print("Run [cyan]traylinx login[/cyan] to authenticate.")
        return
    
    user = creds.get("user", {})
    expires_at_str = creds.get("expires_at")
    
    # Create info table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")
    
    console.print("\n[bold]Traylinx CLI[/bold]")
    console.print()
    
    # User info
    if user.get("email"):
        table.add_row("Email", user.get("email"))
    if user.get("id"):
        table.add_row("User ID", str(user.get("id")))
    if user.get("first_name") or user.get("last_name"):
        name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        if name:
            table.add_row("Name", name)
    
    # Token info
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            table.add_row("Token Expires", expires_at.strftime("%Y-%m-%d %H:%M:%S UTC"))
        except ValueError:
            pass
    
    console.print(table)
    console.print()


# Export commands for direct use
login_command = login
logout_command = logout
whoami_command = whoami
