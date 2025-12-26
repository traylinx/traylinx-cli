"""Traylinx Cortex Plugin - AI Brain Integration.

This module provides CLI commands for connecting to and managing
a self-hosted Cortex instance, enabling persistent memory and
intelligent context management for all LLM interactions.
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

app = typer.Typer(
    name="cortex",
    help="🧠 Cortex AI Brain - Memory & Intelligence",
    no_args_is_help=True,
)

# --- Configuration Management ---

CORTEX_CONFIG_FILE = Path.home() / ".traylinx" / "cortex.json"


def load_cortex_config() -> dict:
    """Load Cortex configuration from disk."""
    if CORTEX_CONFIG_FILE.exists():
        return json.loads(CORTEX_CONFIG_FILE.read_text())
    return {}


def save_cortex_config(config: dict):
    """Save Cortex configuration to disk."""
    CORTEX_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CORTEX_CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_cortex_client():
    """Get an authenticated Cortex client."""
    import httpx

    config = load_cortex_config()
    if not config.get("url"):
        return None

    return httpx.Client(
        base_url=config["url"],
        headers={"Authorization": f"Bearer {config.get('token', '')}"},
        timeout=30.0,
    )


# --- Commands ---


@app.command(name="connect")
def connect_command(
    url: str = typer.Argument(
        ...,
        help="Cortex URL (e.g., http://localhost:8000 or https://cortex.mycompany.com)",
    ),
    token: Optional[str] = typer.Option(
        None,
        "--token",
        "-t",
        help="API token (if not provided, will use Sentinel login)",
    ),
):
    """Connect to a Cortex instance.

    Registers your CLI with a self-hosted Cortex service. If no token is
    provided, the CLI will attempt to use your existing Sentinel login
    to obtain a Cortex-specific token.

    Examples:
        traylinx cortex connect http://localhost:8000
        traylinx cortex connect https://cortex.mycompany.com --token abc123
    """
    import httpx

    console.print(f"\n[bold blue]🧠 Connecting to Cortex...[/bold blue]")
    console.print(f"[dim]URL:[/dim] {url}")

    # Normalize URL
    url = url.rstrip("/")

    # If no token, try to exchange Sentinel token
    if not token:
        try:
            from traylinx.auth import get_access_token

            sentinel_token = get_access_token()
            if sentinel_token:
                console.print("[dim]Exchanging Sentinel token for Cortex access...[/dim]")
                # In a real implementation, this would call Cortex's token exchange endpoint
                token = sentinel_token  # Placeholder - use Sentinel token directly for now
            else:
                console.print("[yellow]Warning:[/yellow] No Sentinel login found.")
                console.print("Run [cyan]traylinx login[/cyan] first, or provide --token.")
        except ImportError:
            pass

    # Test connection
    with console.status("Testing connection..."):
        try:
            client = httpx.Client(
                base_url=url,
                headers={"Authorization": f"Bearer {token}"} if token else {},
                timeout=10.0,
            )
            response = client.get("/health")
            if response.status_code != 200:
                raise Exception(f"Health check failed: {response.status_code}")
        except Exception as e:
            console.print(f"[red]Connection failed:[/red] {e}")
            raise typer.Exit(1) from None

    # Save config
    config = load_cortex_config()
    config["url"] = url
    config["token"] = token
    config["enabled"] = True
    save_cortex_config(config)

    console.print("[green]✓[/green] Connected to Cortex!")
    console.print(f"  [dim]URL:[/dim] {url}")
    console.print(f"  [dim]Auto-routing:[/dim] [green]Enabled[/green]")
    console.print("\n[dim]All tx chat interactions will now use Cortex for memory.[/dim]")


@app.command(name="status")
def status_command():
    """Show Cortex connection status."""
    config = load_cortex_config()

    table = Table(title="Cortex Status", show_header=False)
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value")

    if config.get("url"):
        table.add_row("URL", config["url"])
        table.add_row(
            "Auto-Routing",
            "[green]Enabled[/green]" if config.get("enabled") else "[dim]Disabled[/dim]",
        )
        table.add_row(
            "Token",
            "[green]✓ Configured[/green]" if config.get("token") else "[yellow]Not set[/yellow]",
        )

        # Test connection
        client = get_cortex_client()
        if client:
            try:
                response = client.get("/health")
                if response.status_code == 200:
                    table.add_row("Connection", "[green]● Online[/green]")
                else:
                    table.add_row("Connection", "[red]● Error[/red]")
            except Exception:
                table.add_row("Connection", "[red]● Offline[/red]")
    else:
        table.add_row("Status", "[dim]Not connected[/dim]")
        table.add_row("", "[dim]Run: traylinx cortex connect <url>[/dim]")

    console.print(table)


@app.command(name="enable")
def enable_command():
    """Enable Cortex auto-routing for tx chat."""
    config = load_cortex_config()

    if not config.get("url"):
        console.print("[yellow]Not connected to Cortex.[/yellow]")
        console.print("Run [cyan]traylinx cortex connect <url>[/cyan] first.")
        raise typer.Exit(1) from None

    config["enabled"] = True
    save_cortex_config(config)
    console.print("[green]✓[/green] Cortex auto-routing enabled.")
    console.print("[dim]All tx chat interactions will now use Cortex for memory.[/dim]")


@app.command(name="disable")
def disable_command():
    """Disable Cortex auto-routing (use direct LLM)."""
    config = load_cortex_config()
    config["enabled"] = False
    save_cortex_config(config)
    console.print("[yellow]⚠[/yellow] Cortex auto-routing disabled.")
    console.print("[dim]tx chat will use direct LLM calls without memory.[/dim]")


@app.command(name="memory")
def memory_command(
    action: str = typer.Argument(
        ...,
        help="Action: 'search', 'save', 'list', or 'import'",
    ),
    query: Optional[str] = typer.Argument(
        None,
        help="Search query or memory content",
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results for search"),
):
    """Manage Cortex memory.

    Examples:
        traylinx cortex memory search "API keys"
        traylinx cortex memory save "Project uses FastAPI and Redis"
        traylinx cortex memory list
    """
    config = load_cortex_config()
    if not config.get("url"):
        console.print("[yellow]Not connected to Cortex.[/yellow]")
        raise typer.Exit(1) from None

    client = get_cortex_client()

    if action == "search":
        if not query:
            console.print("[red]Error:[/red] Search query required.")
            raise typer.Exit(1) from None

        with console.status("Searching memory..."):
            try:
                response = client.post(
                    "/v1/memory/search",
                    json={"query": query, "limit": limit},
                )
                results = response.json()
            except Exception as e:
                console.print(f"[red]Search failed:[/red] {e}")
                raise typer.Exit(1) from None

        if not results.get("memories"):
            console.print("[dim]No memories found.[/dim]")
            return

        console.print(f"\n[bold]Found {len(results['memories'])} memories:[/bold]\n")
        for mem in results["memories"]:
            console.print(
                Panel(
                    mem.get("content", ""),
                    title=f"[dim]{mem.get('created_at', 'Unknown')}[/dim]",
                    border_style="cyan",
                )
            )

    elif action == "save":
        if not query:
            console.print("[red]Error:[/red] Memory content required.")
            raise typer.Exit(1) from None

        with console.status("Saving memory..."):
            try:
                response = client.post(
                    "/v1/memory/save",
                    json={"content": query},
                )
            except Exception as e:
                console.print(f"[red]Save failed:[/red] {e}")
                raise typer.Exit(1) from None

        console.print("[green]✓[/green] Memory saved!")

    elif action == "list":
        with console.status("Loading memories..."):
            try:
                response = client.get("/v1/memory/list", params={"limit": limit})
                results = response.json()
            except Exception as e:
                console.print(f"[red]Failed:[/red] {e}")
                raise typer.Exit(1) from None

        console.print(json.dumps(results, indent=2))

    else:
        console.print(f"[red]Unknown action:[/red] {action}")
        console.print("[dim]Valid actions: search, save, list, import[/dim]")


@app.command(name="sessions")
def sessions_command(
    action: str = typer.Argument(
        "list",
        help="Action: 'list' or 'view'",
    ),
    session_id: Optional[str] = typer.Argument(
        None,
        help="Session ID to view",
    ),
):
    """Manage Cortex chat sessions.

    Examples:
        traylinx cortex sessions           # List recent sessions
        traylinx cortex sessions view abc  # View specific session
    """
    config = load_cortex_config()
    if not config.get("url"):
        console.print("[yellow]Not connected to Cortex.[/yellow]")
        raise typer.Exit(1) from None

    client = get_cortex_client()

    if action == "list":
        with console.status("Loading sessions..."):
            try:
                response = client.get("/v1/sessions")
                sessions = response.json().get("sessions", [])
            except Exception as e:
                console.print(f"[red]Failed:[/red] {e}")
                raise typer.Exit(1) from None

        if not sessions:
            console.print("[dim]No sessions found.[/dim]")
            return

        table = Table(title="Recent Sessions")
        table.add_column("ID", style="cyan")
        table.add_column("Created")
        table.add_column("Messages")

        for s in sessions[:20]:
            table.add_row(
                s.get("id", "")[:12] + "...",
                s.get("created_at", "Unknown"),
                str(s.get("message_count", 0)),
            )

        console.print(table)

    elif action == "view":
        if not session_id:
            console.print("[red]Error:[/red] Session ID required.")
            raise typer.Exit(1) from None

        with console.status("Loading session..."):
            try:
                response = client.get(f"/v1/sessions/{session_id}")
                session = response.json()
            except Exception as e:
                console.print(f"[red]Failed:[/red] {e}")
                raise typer.Exit(1) from None

        console.print(json.dumps(session, indent=2))


# --- Middleware for tx chat integration ---


def is_cortex_enabled() -> bool:
    """Check if Cortex auto-routing is enabled."""
    config = load_cortex_config()
    return bool(config.get("url") and config.get("enabled"))


def get_cortex_url() -> Optional[str]:
    """Get the configured Cortex URL."""
    config = load_cortex_config()
    return config.get("url") if config.get("enabled") else None
