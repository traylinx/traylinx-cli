"""
Traylinx CLI - Open Command.

Opens the Traylinx platform in the default browser.
"""

import httpx
from rich.console import Console

from traylinx.auth import AuthManager, SENTINEL_URL

console = Console()
PLATFORM_URL = "https://traylinx.com"


def open_command():
    """
    Open the Traylinx platform in your default web browser.
    
    If you are logged into the CLI, this will automatically log you
    into the web platform via a magic link.
    """
    target_url = PLATFORM_URL

    if AuthManager.is_logged_in():
        token = AuthManager.get_access_token()
        if token:
            try:
                with console.status("[bold green]Generating magic link..."):
                    response = httpx.post(
                        f"{SENTINEL_URL}/devices/cli_link",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=5,
                    )
                
                if response.status_code == 201:
                    data = response.json()
                    target_url = data.get("redirect_url", PLATFORM_URL)
                    console.print("[green]✓ Magic link generated![/green]")
                else:
                    console.print("[dim]Could not generate magic link, opening standard login.[/dim]")
            
            except Exception as e:
                console.print(f"[dim]Connection error ({str(e)}), opening standard login.[/dim]")

    console.print(f"Opening [bold blue]{target_url}[/bold blue]...")
    webbrowser.open(target_url)
