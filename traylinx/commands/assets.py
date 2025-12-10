"""
Assets management command for Traylinx CLI.

Commands:
    traylinx assets list                     - List assets in current project
    traylinx assets create sentinel-pass     - Create Sentinel Pass for A2A auth
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional
from pathlib import Path
import httpx
import json
import os
import uuid

from traylinx.auth import AuthManager
from traylinx.context import ContextManager

# API Configuration
METRICS_API_URL = os.environ.get(
    "TRAYLINX_METRICS_URL",
    "https://api.makakoo.com/ma-metrics-wsp-ms/v1/api"
)

# Credentials storage directory
CREDENTIALS_DIR = Path.home() / ".traylinx" / "credentials"

app = typer.Typer(
    help="Manage project assets",
    invoke_without_command=True,
    no_args_is_help=False
)
console = Console()


@app.callback()
def assets_callback(ctx: typer.Context):
    """Manage assets in your project."""
    if ctx.invoked_subcommand is None:
        # Show friendly help instead of error
        console.print()
        console.print("[bold cyan]traylinx assets[/bold cyan] - Manage project assets\n")
        console.print("[bold]Commands:[/bold]")
        console.print("  [cyan]list[/cyan]                     List assets in current project")
        console.print("  [cyan]create sentinel-pass[/cyan]     Create A2A authentication credentials")
        console.print()
        console.print("[bold]Examples:[/bold]")
        console.print("  $ traylinx assets list")
        console.print("  $ traylinx assets create sentinel-pass my-agent")
        console.print("  $ traylinx assets create sentinel-pass my-agent --save")
        console.print()
        console.print("[dim]For more info: traylinx help assets[/dim]")
        console.print()


def _get_headers() -> dict:
    """Get auth headers for API requests."""
    creds = AuthManager.get_credentials()
    if not creds:
        return {}
    return {
        "Authorization": f"Bearer {creds['access_token']}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


@app.command("list")
def list_assets(
    asset_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by asset type (ai, security, dataset, app, media, defi)"),
    project_id: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID")
):
    """List assets in current project."""
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    org_id = ContextManager.require_organization()
    
    if project_id is None:
        project_id = ContextManager.require_project()
    
    console.print(f"[dim]Fetching assets...[/dim]")
    
    try:
        params = {}
        if asset_type:
            params["asset_type"] = asset_type
        
        response = httpx.get(
            f"{METRICS_API_URL}/organizations/{org_id}/projects/{project_id}/studio_tools",
            params=params,
            headers=_get_headers(),
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        assets = data.get("data", [])
        
        if not assets:
            console.print("[yellow]No assets found.[/yellow]")
            console.print("Run [cyan]traylinx assets create sentinel-pass <name>[/cyan] to create one.")
            return
        
        # Get project name
        project = ContextManager.get_current_project()
        project_name = project.get("name", project_id) if project else project_id
        
        table = Table(title=f"Assets in {project_name}")
        table.add_column("ID", style="cyan", max_width=36)
        table.add_column("Name", style="bold")
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="dim")
        
        for asset in assets:
            attrs = asset.get("attributes", {})
            table.add_row(
                str(asset.get("id", ""))[:36],
                attrs.get("title", ""),
                attrs.get("assetType", ""),
                "Active" if attrs.get("active") else "Inactive"
            )
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(assets)} assets[/dim]")
        
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error fetching assets: {e.response.status_code}[/red]")
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        raise typer.Exit(1)


@app.command("create")
def create_asset(
    asset_type: str = typer.Argument(..., help="Asset type: sentinel-pass"),
    name: str = typer.Argument(..., help="Asset name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description"),
    project_id: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID"),
    save: bool = typer.Option(False, "--save", "-s", help="Save credentials to file")
):
    """
    Create a new asset.
    
    Currently supports:
      - sentinel-pass: Create OAuth credentials for A2A authentication
    """
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    org_id = ContextManager.require_organization()
    
    if project_id is None:
        project_id = ContextManager.require_project()
    
    # Normalize asset type
    asset_type_lower = asset_type.lower().replace("-", "_")
    
    if asset_type_lower == "sentinel_pass":
        _create_sentinel_pass(org_id, project_id, name, description, save)
    else:
        console.print(f"[red]Unknown asset type: {asset_type}[/red]")
        console.print("Supported types: sentinel-pass")
        raise typer.Exit(1)


def _create_sentinel_pass(org_id: str, project_id: str, name: str, description: Optional[str], save: bool):
    """Create a Sentinel Pass (Security & Identity asset)."""
    console.print(f"Creating Sentinel Pass [bold]{name}[/bold]...")
    
    # Generate unique entity ID
    entity_id = f"sentinel-pass-{uuid.uuid4().hex[:8]}"
    
    payload = {
        "studioTool": {
            "entityType": "sentinel_pass",
            "assetType": "security",  # Security & Identity category
            "entityId": entity_id,
            "title": name,
            "description": description or "OAuth credentials for A2A authentication",
            "visibility": "privately_visible",
            "tags": ["oauth", "a2a", "sentinel-pass", "authentication"],
            "metadata": {
                "accessLevel": "standard",
                "permissions": "read,write",
                "usageType": "CLI created",
                "autoCreated": False
            },
            "active": True,
            "deploymentStatus": "not_deployed"
        }
    }
    
    try:
        response = httpx.post(
            f"{METRICS_API_URL}/organizations/{org_id}/projects/{project_id}/studio_tools",
            json=payload,
            headers=_get_headers(),
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        asset = data.get("data", {})
        asset_id = asset.get("id")
        attrs = asset.get("attributes", {})
        
        # Extract OAuth credentials from response
        # These may be in attributes.metadata or a separate credentials field
        metadata = attrs.get("metadata", {})
        credentials = attrs.get("oauthCredentials", metadata.get("oauthCredentials", {}))
        
        client_id = credentials.get("clientId", credentials.get("client_id", ""))
        client_secret = credentials.get("clientSecret", credentials.get("client_secret", ""))
        
        # Display success
        console.print(f"\n[green]✓ Sentinel Pass created![/green]")
        console.print(Panel(
            f"[bold]{name}[/bold]\n"
            f"Asset ID: {asset_id}\n"
            f"Type: Security & Identity",
            title="🔐 Sentinel Pass"
        ))
        
        if client_id and client_secret:
            console.print("\n[bold yellow]⚠️  Save these credentials - they will only be shown once![/bold yellow]\n")
            console.print(f"  [bold]Client ID:[/bold]     {client_id}")
            console.print(f"  [bold]Client Secret:[/bold] {client_secret}")
            
            if save:
                _save_credentials(project_id, name, {
                    "asset_id": asset_id,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "name": name
                })
        else:
            console.print("\n[dim]Note: OAuth credentials may need to be retrieved separately.[/dim]")
            console.print(f"Asset ID: [cyan]{asset_id}[/cyan]")
        
        console.print("\n[dim]Use these credentials in your agent's manifest for A2A authentication.[/dim]")
        
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error creating Sentinel Pass: {e.response.status_code}[/red]")
        try:
            error_data = e.response.json()
            if "message" in error_data:
                console.print(f"[dim]{error_data['message']}[/dim]")
            elif "errors" in error_data:
                for err in error_data.get("errors", []):
                    console.print(f"[dim]- {err.get('detail', err)}[/dim]")
        except Exception:
            if e.response.text:
                console.print(f"[dim]{e.response.text[:200]}[/dim]")
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        raise typer.Exit(1)


def _save_credentials(project_id: str, name: str, credentials: dict):
    """Save credentials to a local file."""
    # Create project-specific credentials directory
    project_dir = CREDENTIALS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate safe filename
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    creds_file = project_dir / f"{safe_name}.json"
    
    with open(creds_file, "w") as f:
        json.dump(credentials, f, indent=2)
    
    # Set restrictive permissions (owner read/write only)
    os.chmod(creds_file, 0o600)
    
    console.print(f"\n[green]✓ Credentials saved to:[/green] {creds_file}")
