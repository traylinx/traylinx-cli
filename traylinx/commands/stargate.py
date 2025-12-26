"""Stargate P2P commands for Traylinx CLI.

This module provides commands for interacting with the Stargate P2P network:
- Identity management (generate, certify)
- Network connectivity (connect, disconnect, status)
- Peer discovery
- Direct agent calls
"""

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

app = typer.Typer(
    name="stargate",
    help="Stargate P2P network commands",
    no_args_is_help=True,
)

# --- Connectivity Commands (Phase 2) ---


@app.command(name="connect")
def connect_command(
    transport: str = typer.Option(
        "nats",
        "--transport",
        "-t",
        help="Transport type: 'nats' (default) or 'libp2p'",
    ),
    server: str = typer.Option(
        None,
        "--server",
        "-s",
        help="Server URL (defaults to demo.nats.io for NATS)",
    ),
    name: str = typer.Option(
        None,
        "--name",
        "-n",
        help="Display name for this node",
    ),
    background: bool = typer.Option(
        False,
        "--background",
        "-b",
        help="Run in background mode (daemon)",
    ),
):
    """Connect to the Stargate P2P network.

    Starts a local Stargate node and connects to the network using the
    specified transport (NATS or libp2p).

    Examples:
        traylinx connect                   # Use defaults
        traylinx connect -t libp2p         # Use P2P transport
        traylinx connect -s nats://my.server:4222
    """
    try:
        from traylinx_stargate.node import StarGateNode, set_node
    except ImportError:
        console.print(
            "[red]Error:[/red] traylinx-stargate not installed. Run: pip install traylinx-stargate"
        )
        raise typer.Exit(1) from None

    # Create node
    node = StarGateNode(
        display_name=name or "CLI-Node",
        transport=transport,
        server=server,
    )

    with console.status(f"Connecting via {transport.upper()}..."):
        try:
            asyncio.run(node.start(server=server))
            set_node(node)  # Store globally for other commands
        except Exception as e:
            console.print(f"[red]Connection failed:[/red] {e}")
            raise typer.Exit(1) from None

    status = node.get_status()
    console.print("[green]✓[/green] Connected to Stargate Network!")
    console.print(f"  [dim]Peer ID:[/dim] {status['peer_id']}")
    console.print(f"  [dim]Transport:[/dim] {status['transport']}")
    console.print(f"  [dim]Server:[/dim] {status['server']}")

    if not background:
        console.print("\n[dim]Press Ctrl+C to disconnect...[/dim]")
        try:
            # H1 fix: Use modern asyncio pattern instead of deprecated get_event_loop()
            async def wait_forever():
                await asyncio.Event().wait()
            asyncio.run(wait_forever())
        except KeyboardInterrupt:
            console.print("\n[yellow]Disconnecting...[/yellow]")
            asyncio.run(node.stop())
            console.print("[green]✓[/green] Disconnected.")


@app.command(name="disconnect")
def disconnect_command():
    """Disconnect from the Stargate network.

    Stops the local Stargate node if running.
    """
    try:
        from traylinx_stargate.node import get_node
    except ImportError:
        console.print(
            "[red]Error:[/red] traylinx-stargate not installed."
        )
        raise typer.Exit(1) from None

    node = get_node()
    if not node or not node.is_running:
        console.print("[yellow]No active connection.[/yellow]")
        raise typer.Exit(0)

    asyncio.run(node.stop())
    console.print("[green]✓[/green] Disconnected from Stargate Network.")


@app.command(name="status")
def status_command():
    """Show Stargate network status.

    Displays the current connection state, transport info, and known peers.
    """
    try:
        from traylinx_stargate.node import get_node
        from traylinx_stargate.identity import IdentityManager
    except ImportError:
        console.print(
            "[red]Error:[/red] traylinx-stargate not installed."
        )
        raise typer.Exit(1) from None

    identity = IdentityManager()
    node = get_node()

    # Build status table
    table = Table(title="Stargate Network Status", show_header=False)
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value")

    # Identity info
    if identity.has_identity():
        identity.load_keypair()
        table.add_row("Peer ID", identity.get_peer_id())
        cert_status = "[green]✓ Certified[/green]" if identity.has_certificate() else "[yellow]Not certified[/yellow]"
        table.add_row("Certificate", cert_status)
    else:
        table.add_row("Identity", "[red]Not found[/red]")

    # Connection info
    if node and node.is_running:
        status = node.get_status()
        transport_info = status.get("transport", {})
        table.add_row("Connection", "[green]● Connected[/green]")
        table.add_row("Transport", transport_info.get("transport", "nats") if isinstance(transport_info, dict) else str(transport_info))
        table.add_row("Server", transport_info.get("server", "unknown") if isinstance(transport_info, dict) else "unknown")
        table.add_row("Peers Known", str(len(node.get_peers())))
        
        # NAT status (Phase 6)
        nat_status = status.get("nat_status")
        if nat_status:
            nat_type = nat_status.get("nat_type", "unknown")
            if nat_type == "public":
                table.add_row("NAT Status", "[green]Public IP[/green]")
            elif nat_type == "nat":
                table.add_row("NAT Status", "[yellow]Behind NAT[/yellow]")
            elif nat_type == "nats_native":
                table.add_row("NAT Status", "[dim]NATS (no NAT issue)[/dim]")
            else:
                table.add_row("NAT Status", f"[dim]{nat_type}[/dim]")
        
        # Relay info
        if status.get("relay_enabled"):
            table.add_row("Relay Mode", "[green]● Enabled[/green]")
        else:
            table.add_row("Relay Mode", "[dim]Disabled[/dim]")
    else:
        table.add_row("Connection", "[dim]● Offline[/dim]")

    console.print(table)



@app.command(name="identity")
def identity_command(
    generate: bool = typer.Option(
        False, "--generate", "-g", help="Generate a new identity keypair"
    ),
    show: bool = typer.Option(False, "--show", "-s", help="Show current identity info"),
):
    """Manage your Stargate P2P identity."""
    try:
        from traylinx_stargate.identity import IdentityManager
    except ImportError:
        console.print(
            "[red]Error:[/red] traylinx-stargate not installed. Run: pip install traylinx-stargate"
        )
        raise typer.Exit(1) from None

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
            raise typer.Exit(1) from None

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
            table.add_row(
                "Valid",
                "[green]Yes[/green]" if identity.is_certificate_valid() else "[red]Expired[/red]",
            )
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
            "[red]Error:[/red] traylinx-stargate not installed. Run: pip install traylinx-stargate"
        )
        raise typer.Exit(1) from None

    from traylinx.auth import get_access_token
    from traylinx.constants import get_settings

    settings = get_settings()
    identity = IdentityManager()

    # Check identity exists
    if not identity.has_identity():
        console.print("[yellow]No identity found.[/yellow]")
        console.print("Run [cyan]traylinx stargate identity --generate[/cyan] first.")
        raise typer.Exit(1) from None

    # Get access token
    access_token = get_access_token()
    if not access_token:
        console.print("[red]Not logged in.[/red]")
        console.print("Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1) from None

    # Determine Sentinel URL
    sentinel = sentinel_url or settings.effective_registry_url
    if not sentinel:
        console.print("[red]No Sentinel URL configured.[/red]")
        console.print("Set TRAYLINX_REGISTRY_URL or use --sentinel option.")
        raise typer.Exit(1) from None

    # Request certificate
    with console.status("Requesting certificate from Sentinel..."):
        try:
            result = identity.request_sentinel_certificate(
                sentinel_url=sentinel,
                access_token=access_token,
            )
        except Exception as e:
            console.print(f"[red]Certification failed:[/red] {e}")
            raise typer.Exit(1) from None

    console.print("[green]✓[/green] Certificate obtained!")
    console.print(f"  [dim]Peer ID:[/dim] {identity.get_peer_id()}")
    console.print(f"  [dim]Expires:[/dim] {result.get('expires_at', 'Unknown')}")
    console.print(f"  [dim]Saved to:[/dim] {identity.cert_file}")


@app.command(name="peers")
def peers_command(
    capability: str = typer.Option(None, "--capability", "-c", help="Filter by capability"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List discovered peers on the network.

    Shows all peers that have announced themselves on the Stargate network.
    Use --capability to filter by specific agent capabilities.
    """
    try:
        from traylinx_stargate.node import get_node
    except ImportError:
        console.print("[red]Error:[/red] traylinx-stargate not installed.")
        raise typer.Exit(1) from None

    node = get_node()
    if not node or not node.is_running:
        console.print("[yellow]No active connection.[/yellow]")
        console.print("Run [cyan]traylinx connect[/cyan] first.")
        raise typer.Exit(1) from None

    with console.status("Discovering peers..."):
        peers = asyncio.run(node.discover(capability=capability))

    if json_output:
        console.print(json.dumps([p.__dict__ for p in peers], indent=2))
        return

    if not peers:
        console.print("[dim]No peers found.[/dim]")
        return

    table = Table(title="Stargate Peers")
    table.add_column("Peer ID", style="cyan")
    table.add_column("Name")
    table.add_column("Capabilities")

    for peer in peers:
        caps = ", ".join(peer.capabilities) if peer.capabilities else "-"
        table.add_row(peer.peer_id[:16] + "...", peer.display_name or "-", caps)

    console.print(table)



@app.command(name="call")
def call_command(
    peer_id: str = typer.Argument(..., help="Target peer ID or agent key"),
    action: str = typer.Argument(..., help="Action to invoke"),
    payload: str = typer.Option("{}", "--payload", "-p", help="JSON payload for the action"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Request timeout in seconds"),
):
    """Call an action on a remote agent.

    Sends a direct P2P request to the specified agent and waits for a response.
    The agent must be online and discoverable on the Stargate network.

    Example:
        traylinx call translator-abc123 translate -p '{"text": "Hello"}'
    """
    try:
        from traylinx_stargate.node import get_node
    except ImportError:
        console.print("[red]Error:[/red] traylinx-stargate not installed.")
        raise typer.Exit(1) from None

    node = get_node()
    if not node or not node.is_running:
        console.print("[yellow]No active connection.[/yellow]")
        console.print("Run [cyan]traylinx connect[/cyan] first.")
        raise typer.Exit(1) from None

    try:
        payload_dict = json.loads(payload)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON payload:[/red] {e}")
        raise typer.Exit(1) from None

    with console.status(f"Calling {action} on {peer_id[:16]}..."):
        try:
            result = asyncio.run(node.call(peer_id, action, payload_dict, timeout=timeout))
        except Exception as e:
            console.print(f"[red]Call failed:[/red] {e}")
            raise typer.Exit(1) from None

    console.print("[green]✓[/green] Response received:")
    console.print(json.dumps(result, indent=2))


@app.command(name="announce")
def announce_command():
    """Announce your presence to the Stargate network.

    Broadcasts your identity, display name, and capabilities so other agents
    can discover you.
    """
    try:
        from traylinx_stargate.node import get_node
    except ImportError:
        console.print("[red]Error:[/red] traylinx-stargate not installed.")
        raise typer.Exit(1) from None

    node = get_node()
    if not node or not node.is_running:
        console.print("[yellow]No active connection.[/yellow]")
        console.print("Run [cyan]traylinx connect[/cyan] first.")
        raise typer.Exit(1) from None

    with console.status("Announcing to network..."):
        asyncio.run(node.announce())

    console.print("[green]✓[/green] Announcement broadcast!")
    console.print(f"  [dim]Peer ID:[/dim] {node.peer_id}")


@app.command(name="listen")
def listen_command():
    """Listen for incoming messages (debug mode).

    Displays all incoming A2A messages in real-time. Useful for debugging.
    Press Ctrl+C to stop.
    """
    try:
        from traylinx_stargate.node import get_node
    except ImportError:
        console.print("[red]Error:[/red] traylinx-stargate not installed.")
        raise typer.Exit(1) from None

    node = get_node()
    if not node or not node.is_running:
        console.print("[yellow]No active connection.[/yellow]")
        console.print("Run [cyan]traylinx connect[/cyan] first.")
        raise typer.Exit(1) from None

    console.print("[cyan]Listening for incoming messages...[/cyan]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

    # Register a catch-all handler for debug
    @node.on_message("*")
    async def debug_handler(msg):
        console.print(Panel(
            json.dumps(msg, indent=2),
            title=f"[bold]Incoming: {msg.get('action', 'unknown')}[/bold]",
            border_style="cyan"
        ))
        return None  # Don't respond

    try:
        # H1 fix: Use modern asyncio pattern instead of deprecated get_event_loop()
        async def wait_forever():
            await asyncio.Event().wait()
        asyncio.run(wait_forever())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped listening.[/yellow]")


# Standalone commands for top-level aliases
def discover_command(
    capability: str = typer.Option(None, "--capability", "-c", help="Filter by capability"),
):
    """Discover agents on the Stargate network.

    Alias for: traylinx stargate peers
    """
    peers_command(capability=capability, json_output=False)

