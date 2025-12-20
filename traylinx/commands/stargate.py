"""Stargate P2P commands for Traylinx CLI.

This module provides commands for interacting with the Stargate P2P network:
- Identity management (generate, certify)
- Peer discovery
- Direct agent calls
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

app = typer.Typer(
    name="stargate",
    help="Stargate P2P network commands",
    no_args_is_help=True,
)


@app.command(name="identity")
def identity_command(
    generate: bool = typer.Option(
        False, "--generate", "-g", help="Generate a new identity keypair"
    ),
    show: bool = typer.Option(
        False, "--show", "-s", help="Show current identity info"
    ),
):
    """Manage your Stargate P2P identity."""
    try:
        from traylinx_stargate.identity import IdentityManager
    except ImportError:
        console.print(
            "[red]Error:[/red] traylinx-stargate not installed. "
            "Run: pip install traylinx-stargate"
        )
        raise typer.Exit(1)
    
    identity = IdentityManager()
    
    if generate:
        if identity.has_identity():
            console.print("[yellow]Warning:[/yellow] Identity already exists.")
            if not typer.confirm("Overwrite existing identity?"):
                raise typer.Exit(0)
        
        identity.generate_keypair()
        console.print("[green]✓[/green] Generated new Ed25519 keypair")
        console.print(f"  [dim]Peer ID:[/dim] {identity.get_peer_id()}")
        console.print(f"  [dim]Key file:[/dim] {identity.key_file}")
    
    elif show or not generate:
        if not identity.has_identity():
            console.print("[yellow]No identity found.[/yellow]")
            console.print("Run [cyan]traylinx stargate identity --generate[/cyan] to create one.")
            raise typer.Exit(1)
        
        identity.load_keypair()
        
        table = Table(title="Stargate Identity")
        table.add_column("Property", style="cyan")
        table.add_column("Value")
        
        table.add_row("Peer ID", identity.get_peer_id())
        table.add_row("Public Key", identity.get_public_key_hex()[:32] + "...")
        table.add_row("Key File", str(identity.key_file))
        
        if identity.has_certificate():
            cert = identity.get_certificate()
            table.add_row("Certificate", "[green]✓ Present[/green]")
            table.add_row("Issuer", cert.get("issuer", "Unknown"))
            table.add_row("Expires", cert.get("expires_at", "Unknown"))
            table.add_row("Valid", "[green]Yes[/green]" if identity.is_certificate_valid() else "[red]Expired[/red]")
        else:
            table.add_row("Certificate", "[yellow]Not certified[/yellow]")
        
        console.print(table)


@app.command(name="certify")
def certify_command(
    sentinel_url: str = typer.Option(
        None,
        "--sentinel",
        "-s",
        help="Sentinel URL (defaults to TRAYLINX_REGISTRY_URL)",
        envvar="TRAYLINX_REGISTRY_URL",
    ),
):
    """Request a P2P certificate from Sentinel.
    
    This command signs a challenge with your identity keypair and sends it
    to Sentinel for verification. Upon success, a JWT certificate is saved
    locally for P2P authentication.
    
    Requires: Valid OAuth login (run `traylinx login` first)
    """
    try:
        from traylinx_stargate.identity import IdentityManager
    except ImportError:
        console.print(
            "[red]Error:[/red] traylinx-stargate not installed. "
            "Run: pip install traylinx-stargate"
        )
        raise typer.Exit(1)
    
    from traylinx.constants import get_settings
    from traylinx.auth import get_access_token
    
    settings = get_settings()
    identity = IdentityManager()
    
    # Check identity exists
    if not identity.has_identity():
        console.print("[yellow]No identity found.[/yellow]")
        console.print("Run [cyan]traylinx stargate identity --generate[/cyan] first.")
        raise typer.Exit(1)
    
    # Get access token
    access_token = get_access_token()
    if not access_token:
        console.print("[red]Not logged in.[/red]")
        console.print("Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    # Determine Sentinel URL
    sentinel = sentinel_url or settings.effective_registry_url
    if not sentinel:
        console.print("[red]No Sentinel URL configured.[/red]")
        console.print("Set TRAYLINX_REGISTRY_URL or use --sentinel option.")
        raise typer.Exit(1)
    
    # Request certificate
    with console.status("Requesting certificate from Sentinel..."):
        try:
            result = identity.request_sentinel_certificate(
                sentinel_url=sentinel,
                access_token=access_token,
            )
        except Exception as e:
            console.print(f"[red]Certification failed:[/red] {e}")
            raise typer.Exit(1)
    
    console.print("[green]✓[/green] Certificate obtained!")
    console.print(f"  [dim]Peer ID:[/dim] {identity.get_peer_id()}")
    console.print(f"  [dim]Expires:[/dim] {result.get('expires_at', 'Unknown')}")
    console.print(f"  [dim]Saved to:[/dim] {identity.cert_file}")


@app.command(name="peers")
def peers_command(
    capability: str = typer.Option(
        None, "--capability", "-c", help="Filter by capability"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON"
    ),
):
    """List discovered peers on the network.
    
    Shows all peers that have announced themselves on the Stargate network.
    Use --capability to filter by specific agent capabilities.
    """
    console.print("[yellow]Peer discovery requires a running Stargate node.[/yellow]")
    console.print("This command is a placeholder for the full implementation.")
    console.print("\n[dim]Coming in Phase 3: Global Connectivity[/dim]")


@app.command(name="call")
def call_command(
    peer_id: str = typer.Argument(..., help="Target peer ID or agent key"),
    action: str = typer.Argument(..., help="Action to invoke"),
    payload: str = typer.Option(
        "{}", "--payload", "-p", help="JSON payload for the action"
    ),
    timeout: int = typer.Option(
        30, "--timeout", "-t", help="Request timeout in seconds"
    ),
):
    """Call an action on a remote agent.
    
    Sends a direct P2P request to the specified agent and waits for a response.
    The agent must be online and discoverable on the Stargate network.
    
    Example:
        traylinx stargate call translator-abc123 translate -p '{"text": "Hello"}'
    """
    console.print("[yellow]Direct P2P calls require a running Stargate node.[/yellow]")
    console.print("This command is a placeholder for the full implementation.")
    console.print("\n[dim]Coming in Phase 3: Global Connectivity[/dim]")


# Standalone commands for top-level aliases
def discover_command(
    capability: str = typer.Option(
        None, "--capability", "-c", help="Filter by capability"
    ),
):
    """Discover agents on the Stargate network.
    
    Alias for: traylinx stargate peers
    """
    peers_command(capability=capability, json_output=False)
