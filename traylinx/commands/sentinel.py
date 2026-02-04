"""
Sentinel Pass management commands for Traylinx CLI.

Commands:
    traylinx sentinel pass create   - Create a new Sentinel Pass
    traylinx sentinel pass list     - List all Sentinel Passes
    traylinx sentinel pass show     - Show pass details
    traylinx sentinel pass delete   - Delete a pass
"""

import json
import os
from datetime import datetime
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from traylinx.auth import AuthManager
from traylinx.context import ContextManager
from traylinx.utils.statebox import StateBox

# API Configuration
USERS_API_URL = os.environ.get(
    "TRAYLINX_USERS_URL", "https://api.makakoo.com/ma-users-ms/v1/api"
)
METRICS_API_URL = os.environ.get(
    "TRAYLINX_METRICS_URL", "https://api.makakoo.com/ma-metrics-wsp-ms/v1/api"
)

app = typer.Typer(
    help="Manage Sentinel Passes for agent identity",
    invoke_without_command=True,
    no_args_is_help=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

pass_app = typer.Typer(
    help="Sentinel Pass operations",
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(pass_app, name="pass")

console = Console()


# =============================================================================
# Helper Functions
# =============================================================================


def _get_auth_headers() -> dict:
    """Get auth headers for API requests."""
    creds = AuthManager.get_credentials()
    if not creds:
        return {}
    return {
        "Authorization": f"Bearer {creds['access_token']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get_agent_dir(name: str) -> Path:
    """Get directory for storing agent credentials."""
    return StateBox.agents_dir() / name


def _save_agent_credentials(name: str, data: dict) -> Path:
    """Save agent credentials securely."""
    from traylinx.utils.secure_write import secure_write_json

    agent_dir = _get_agent_dir(name)
    StateBox.ensure_dir(agent_dir)
    
    creds_file = agent_dir / "credentials.json"
    secure_write_json(creds_file, data)
    return creds_file


def _load_agent_credentials(name: str) -> dict | None:
    """Load agent credentials from local storage."""
    creds_file = _get_agent_dir(name) / "credentials.json"
    if not creds_file.exists():
        return None
    try:
        return json.loads(creds_file.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _list_local_agents() -> list[dict]:
    """List all locally stored agents."""
    agents_dir = StateBox.agents_dir()
    if not agents_dir.exists():
        return []
    
    agents = []
    for agent_path in agents_dir.iterdir():
        if agent_path.is_dir():
            creds = _load_agent_credentials(agent_path.name)
            if creds:
                agents.append({
                    "name": agent_path.name,
                    "agent_id": creds.get("agent_id"),
                    "client_id": creds.get("client_id"),
                    "pass_id": creds.get("pass_id"),
                    "created_at": creds.get("created_at"),
                })
    return agents


def _require_auth():
    """Verify user is logged in."""
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)


def _require_project() -> tuple[str, str]:
    """Get current org_id and project_id, or exit with error."""
    org_id = ContextManager.get_current_organization_id()
    project_id = ContextManager.get_current_project_id()
    
    if not org_id:
        console.print("[yellow]No organization selected.[/yellow]")
        console.print("Run [cyan]traylinx orgs use[/cyan] first.")
        raise typer.Exit(1)
    
    if not project_id:
        console.print("[yellow]No project selected.[/yellow]")
        console.print("Run [cyan]traylinx projects use[/cyan] first.")
        raise typer.Exit(1)
    
    return org_id, project_id


# =============================================================================
# Callbacks
# =============================================================================


@app.callback()
def sentinel_callback(ctx: typer.Context):
    """Manage Sentinel Passes for agent identity."""
    if ctx.invoked_subcommand is None:
        console.print()
        console.print("[bold cyan]traylinx sentinel[/bold cyan] - Agent identity management\n")
        console.print("[bold]Commands:[/bold]")
        console.print("  [cyan]pass create[/cyan]     Create a new Sentinel Pass")
        console.print("  [cyan]pass list[/cyan]       List all Sentinel Passes")
        console.print("  [cyan]pass show[/cyan]       Show pass details")
        console.print("  [cyan]pass delete[/cyan]     Delete a pass")
        console.print()
        console.print("[bold]Examples:[/bold]")
        console.print("  $ traylinx sentinel pass create --name my-agent")
        console.print("  $ traylinx sentinel pass list")
        console.print()
        console.print("[dim]For more info: traylinx help sentinel[/dim]")
        console.print()


# =============================================================================
# Pass Commands
# =============================================================================


@pass_app.command("create")
def create_pass(
    name: str = typer.Option(
        ...,
        "--name", "-n",
        help="Name for the agent (used for local storage)",
    ),
    agent_type: str = typer.Option(
        "service",
        "--type", "-t",
        help="Agent type (service, api, microservice)",
    ),
    description: str = typer.Option(
        "",
        "--description", "-d",
        help="Description of the agent",
    ),
    project: str = typer.Option(
        None,
        "--project", "-p",
        help="Project ID (defaults to current project)",
    ),
    create_project_name: str = typer.Option(
        None,
        "--create-project",
        help="Create a new project with this name and use it",
    ),
):
    """
    Create a new Sentinel Pass.

    This creates an Agent User with OAuth credentials and links it to a project.
    The client_secret is shown ONCE - save it securely!
    """
    _require_auth()
    
    # Get project context
    org_id = ContextManager.get_current_organization_id()
    # Handle explicit project creation requested via flag
    if create_project_name:
        with console.status(f"[bold green]Creating project '{create_project_name}'...[/bold green]"):
            try:
                resp = httpx.post(
                    f"{METRICS_API_URL}/organizations/{org_id}/projects",
                    json={"data": {"attributes": {"name": create_project_name}}},
                    headers=_get_auth_headers(),
                    timeout=30,
                )
                resp.raise_for_status()
                p_data = resp.json().get("data", {})
                project_id = p_data.get("id")
                console.print(f"[green]✓ Created project '{create_project_name}' ({project_id})[/green]")
                ContextManager.set_current_project_id(project_id)
            except httpx.HTTPError as e:
                console.print(f"[red]Failed to create project: {e}[/red]")
                raise typer.Exit(1)
    else:
        project_id = project or ContextManager.get_current_project_id()
    
    if not org_id:
        console.print("[yellow]No organization selected.[/yellow]")
        console.print("Run [cyan]traylinx orgs use[/cyan] first.")
        raise typer.Exit(1)
    
    # If no project specified, try interactive selection
    if not project_id:
        # Check context first
        project_id = ContextManager.get_current_project_id()
        
        if not project_id:
            console.print("[yellow]No active project found.[/yellow]")
            
            # Fetch projects interactively
            with console.status("[bold green]Fetching projects...[/bold green]"):
                projects = ContextManager.get_projects(org_id)
            
            from InquirerPy import inquirer
            
            choices = [{"name": p.get("name", "Unnamed"), "value": str(p.get("id"))} for p in projects]
            choices.append({"name": "➕ Create new project...", "value": "NEW"})
            
            selection = inquirer.select(
                message="Select a project for this Sentinel Pass:",
                choices=choices,
                pointer="→",
            ).execute()
            
            if selection == "NEW":
                new_project_name = inquirer.text(
                    message="Enter new project name:",
                    validate=lambda x: len(x) > 0,
                ).execute()
                
                with console.status(f"[bold green]Creating project '{new_project_name}'...[/bold green]"):
                    try:
                        resp = httpx.post(
                            f"{METRICS_API_URL}/organizations/{org_id}/projects",
                            json={"data": {"attributes": {"name": new_project_name}}},
                            headers=_get_auth_headers(),
                            timeout=30,
                        )
                        resp.raise_for_status()
                        project_data = resp.json().get("data", {})
                        project_id = project_data.get("id")
                        console.print(f"[green]✓ Created project '{new_project_name}' ({project_id})[/green]")
                        
                        # Update context to use this new project
                        ContextManager.set_current_project_id(project_id)
                        
                    except httpx.HTTPError as e:
                        console.print(f"[red]Failed to create project: {e}[/red]")
                        raise typer.Exit(1)
            else:
                project_id = selection
                ContextManager.set_current_project_id(project_id)
    
    # Check if agent with this name already exists locally
    existing = _load_agent_credentials(name)
    if existing:
        console.print(f"[red]Agent '{name}' already exists locally.[/red]")
        console.print(f"Use [cyan]traylinx sentinel pass show {name}[/cyan] to view it.")
        console.print(f"Or [cyan]traylinx sentinel pass delete {name}[/cyan] to remove it.")
        raise typer.Exit(1)

    # Get user ID from stored credentials
    creds = AuthManager.get_credentials()
    user_id = creds.get("user", {}).get("id")
    if not user_id:
        console.print("[red]Could not determine user ID from credentials.[/red]")
        console.print("Try logging in again with [cyan]traylinx login[/cyan].")
        raise typer.Exit(1)

    console.print(f"\n[bold]Creating Sentinel Pass for '{name}'...[/bold]\n")

    # Step 1: Create Agent User via authentication_ms
    with console.status("[bold green]Creating agent user...[/bold green]"):
        try:
            agent_payload = {
                "agent": {
                    "agentType": agent_type,
                    "name": name,
                    "description": description,
                    "metadata": {},
                    "customAttributes": {},
                }
            }
            
            response = httpx.post(
                f"{USERS_API_URL}/users/{user_id}/agents",
                json=agent_payload,
                headers=_get_auth_headers(),
                timeout=30,
            )
            response.raise_for_status()
            agent_data = response.json()
            
        except httpx.HTTPStatusError as e:
            console.print(f"[red]Failed to create agent: {e.response.status_code}[/red]")
            if e.response.status_code == 422:
                try:
                    error_detail = e.response.json()
                    console.print(f"[dim]{error_detail}[/dim]")
                except Exception:
                    pass
            raise typer.Exit(1)
        except httpx.HTTPError as e:
            console.print(f"[red]Network error: {e}[/red]")
            raise typer.Exit(1)

    # Extract agent details
    agent_id = agent_data.get("data", {}).get("id")
    agent_attrs = agent_data.get("data", {}).get("attributes", {})
    oauth_creds = agent_attrs.get("oauthCredentials", {})
    
    client_id = oauth_creds.get("clientId", "")
    client_secret = oauth_creds.get("clientSecret", "")
    
    if not agent_id or not client_id:
        console.print("[red]Unexpected response format from API.[/red]")
        console.print(f"[dim]{agent_data}[/dim]")
        raise typer.Exit(1)

    # Generate pass ID
    pass_id = f"SP-{datetime.now().year}-{agent_id[-6:]}"

    # Step 2: Create Sentinel Pass tool in metrics_workspace_ms
    with console.status("[bold green]Creating Sentinel Pass asset...[/bold green]"):
        try:
            pass_payload = {
                "studioTool": {
                    "entityType": "sentinel_pass",
                    "assetType": "security",
                    "entityId": f"sentinel-pass-{agent_id}",
                    "title": f"System Access Credentials - {name}",
                    "description": f"OAuth credentials for {name}",
                    "visibility": "private",
                    "category": "Identity & Data",
                    "tags": ["oauth", "system-access", "authentication"],
                    "metadata": {
                        "agentUserId": agent_id,
                        "clientId": client_id,
                        "passId": pass_id,
                        "accessLevel": "standard",
                        "status": "active",
                        "createdBy": user_id,
                        "autoCreated": True,
                    },
                    "active": True,
                    "deploymentStatus": "not_deployed",
                }
            }
            
            response = httpx.post(
                f"{METRICS_API_URL}/organizations/{org_id}/projects/{project_id}/studio_tools",
                json=pass_payload,
                headers=_get_auth_headers(),
                timeout=30,
            )
            response.raise_for_status()
            pass_data = response.json()
            pass_linked = True
            
        except httpx.HTTPError as e:
            console.print(f"[yellow]Warning: Could not create pass asset: {e}[/yellow]")
            console.print("[dim]Agent created successfully, but asset linking failed.[/dim]")
            pass_linked = False

    # Step 3: Save credentials locally
    local_creds = {
        "agent_id": agent_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "pass_id": pass_id,
        "agent_type": agent_type,
        "project_id": project_id,
        "org_id": org_id,
        "created_at": datetime.now().isoformat(),
        "linked": pass_linked,
    }
    
    creds_file = _save_agent_credentials(name, local_creds)

    # Display success
    console.print()
    console.print(Panel.fit(
        f"[bold green]✅ Sentinel Pass created successfully![/bold green]\n\n"
        f"   [bold]Pass ID:[/bold]       {pass_id}\n"
        f"   [bold]Agent Name:[/bold]    {name}\n"
        f"   [bold]Agent ID:[/bold]      {agent_id}\n"
        f"   [bold]Client ID:[/bold]     {client_id}\n"
        f"   [bold]Client Secret:[/bold] {client_secret[:8]}...{client_secret[-4:]}\n"
        f"   [bold]Saved to:[/bold]      {creds_file}\n\n"
        f"[yellow]⚠ The client_secret is shown ONCE. Store it securely![/yellow]",
        title="Sentinel Pass",
        border_style="green",
    ))
    
    # Show environment variable hints
    console.print("\n[bold]To use this agent, set these environment variables:[/bold]")
    console.print(f"  export TRAYLINX_CLIENT_ID=\"{client_id}\"")
    console.print(f"  export TRAYLINX_CLIENT_SECRET=\"{client_secret}\"")
    console.print(f"  export TRAYLINX_AGENT_USER_ID=\"{agent_id}\"")
    console.print()


@pass_app.command("list")
def list_passes():
    """List all locally stored Sentinel Passes."""
    _require_auth()
    
    agents = _list_local_agents()
    
    if not agents:
        console.print("[yellow]No Sentinel Passes found.[/yellow]")
        console.print("Run [cyan]traylinx sentinel pass create --name \u003cname\u003e[/cyan] to create one.")
        return

    table = Table(title="Sentinel Passes")
    table.add_column("Name", style="bold")
    table.add_column("Pass ID", style="cyan")
    table.add_column("Agent ID", style="dim")
    table.add_column("Created", style="dim")

    for agent in agents:
        created = agent.get("created_at", "")[:10] if agent.get("created_at") else ""
        table.add_row(
            agent.get("name", ""),
            agent.get("pass_id", ""),
            agent.get("agent_id", "")[:8] + "..." if agent.get("agent_id") else "",
            created,
        )

    console.print(table)


@pass_app.command("show")
def show_pass(
    name: str = typer.Argument(..., help="Name of the agent to show"),
):
    """Show details of a Sentinel Pass."""
    _require_auth()
    
    creds = _load_agent_credentials(name)
    
    if not creds:
        console.print(f"[red]Sentinel Pass '{name}' not found.[/red]")
        console.print("Run [cyan]traylinx sentinel pass list[/cyan] to see available passes.")
        raise typer.Exit(1)

    console.print()
    console.print(Panel.fit(
        f"[bold]Pass ID:[/bold]     {creds.get('pass_id', 'N/A')}\n"
        f"[bold]Agent ID:[/bold]    {creds.get('agent_id', 'N/A')}\n"
        f"[bold]Client ID:[/bold]   {creds.get('client_id', 'N/A')}\n"
        f"[bold]Agent Type:[/bold]  {creds.get('agent_type', 'N/A')}\n"
        f"[bold]Project:[/bold]     {creds.get('project_id', 'N/A')}\n"
        f"[bold]Created:[/bold]     {creds.get('created_at', 'N/A')}\n"
        f"[bold]Linked:[/bold]      {'Yes' if creds.get('linked') else 'No'}",
        title=f"Sentinel Pass: {name}",
        border_style="cyan",
    ))
    
    # Note about secret
    console.print("\n[dim]Note: client_secret is not displayed for security.[/dim]")
    console.print(f"[dim]Credentials stored at: {_get_agent_dir(name) / 'credentials.json'}[/dim]")
    console.print()


@pass_app.command("delete")
def delete_pass(
    name: str = typer.Argument(..., help="Name of the agent to delete"),
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Skip confirmation prompt",
    ),
    remote: bool = typer.Option(
        False,
        "--remote", "-r",
        help="Also delete from remote API (revokes OAuth credentials)",
    ),
):
    """Delete a Sentinel Pass."""
    _require_auth()
    
    creds = _load_agent_credentials(name)
    
    if not creds:
        console.print(f"[red]Sentinel Pass '{name}' not found locally.[/red]")
        console.print("Run [cyan]traylinx sentinel pass list[/cyan] to see available passes.")
        raise typer.Exit(1)

    # Confirm deletion
    if not force:
        from InquirerPy import inquirer
        
        confirm = inquirer.confirm(
            message=f"Delete Sentinel Pass '{name}'?",
            default=False,
        ).execute()
        
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    # Delete remote if requested
    if remote:
        agent_id = creds.get("agent_id")
        if agent_id:
            with console.status("[bold yellow]Revoking remote credentials...[/bold yellow]"):
                try:
                    # Get user ID for the API call
                    user_creds = AuthManager.get_credentials()
                    user_id = user_creds.get("user", {}).get("id")
                    
                    if user_id:
                        response = httpx.delete(
                            f"{USERS_API_URL}/agents/{agent_id}",
                            headers=_get_auth_headers(),
                            timeout=30,
                        )
                        if response.status_code in (200, 204, 404):
                            console.print("[green]Remote credentials revoked.[/green]")
                        else:
                            console.print(f"[yellow]Warning: Remote deletion returned {response.status_code}[/yellow]")
                except httpx.HTTPError as e:
                    console.print(f"[yellow]Warning: Could not revoke remote credentials: {e}[/yellow]")

    # Delete local files
    agent_dir = _get_agent_dir(name)
    if agent_dir.exists():
        import shutil
        shutil.rmtree(agent_dir)

    console.print(f"[green]✓ Sentinel Pass '{name}' deleted.[/green]")
