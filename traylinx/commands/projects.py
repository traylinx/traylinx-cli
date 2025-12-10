"""
Projects management command for Traylinx CLI.

Commands:
    traylinx projects list         - List projects in current organization
    traylinx projects show         - Show project details
    traylinx projects create       - Create a new project
    traylinx projects use          - Switch current project
    traylinx projects keys list    - List API keys
    traylinx projects keys create  - Create API key
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional
import httpx
import os

from traylinx.auth import AuthManager
from traylinx.context import ContextManager

# API Configuration
METRICS_API_URL = os.environ.get(
    "TRAYLINX_METRICS_URL",
    "https://api.makakoo.com/ma-metrics-wsp-ms/v1/api"
)

app = typer.Typer(
    help="Manage projects",
    invoke_without_command=True,
    no_args_is_help=False
)
keys_app = typer.Typer(help="Manage API keys")
app.add_typer(keys_app, name="keys")

console = Console()


@app.callback()
def projects_callback(ctx: typer.Context):
    """Manage projects in your organization."""
    if ctx.invoked_subcommand is None:
        # Show friendly help instead of error
        console.print()
        console.print("[bold cyan]traylinx projects[/bold cyan] - Manage projects\n")
        console.print("[bold]Commands:[/bold]")
        console.print("  [cyan]list[/cyan]           List projects in current organization")
        console.print("  [cyan]use[/cyan]            Switch project (interactive selector)")
        console.print("  [cyan]create <name>[/cyan]  Create a new project")
        console.print("  [cyan]show[/cyan]           Show project details")
        console.print("  [cyan]keys[/cyan]           Manage API keys")
        console.print()
        console.print("[bold]Examples:[/bold]")
        console.print("  $ traylinx projects list")
        console.print("  $ traylinx projects use")
        console.print("  $ traylinx projects create my-agent")
        console.print()
        console.print("[dim]For more info: traylinx help projects[/dim]")
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
def list_projects():
    """List projects in current organization."""
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    org_id = ContextManager.get_current_organization_id()
    if not org_id:
        console.print("[yellow]No organization selected.[/yellow]")
        console.print("Run [cyan]traylinx orgs use <id>[/cyan] to select one.")
        raise typer.Exit(1)
    
    # Get projects from context (cached)
    projects = ContextManager.get_projects(org_id)
    current_project_id = ContextManager.get_current_project_id()
    
    if not projects:
        console.print("[yellow]No projects found in this organization.[/yellow]")
        console.print("Run [cyan]traylinx projects create <name>[/cyan] to create one.")
        return
    
    org = ContextManager.get_current_organization()
    org_name = org.get("name", org_id) if org else org_id
    
    table = Table(title=f"Projects in {org_name}")
    table.add_column("", style="dim", width=2)
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="bold")
    
    for project in projects:
        is_current = str(project.get("id")) == str(current_project_id)
        marker = "→" if is_current else ""
        
        table.add_row(
            marker,
            str(project.get("id", "")),
            project.get("name", "")
        )
    
    console.print(table)
    
    if current_project_id:
        console.print(f"\n[dim]Current project: {current_project_id}[/dim]")


@app.command("use")
def use_project(
    project_id: str = typer.Argument(None, help="Project ID to switch to (interactive if not provided)")
):
    """Switch to a different project."""
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    org_id = ContextManager.get_current_organization_id()
    if not org_id:
        console.print("[yellow]No organization selected.[/yellow]")
        console.print("Run [cyan]traylinx orgs use[/cyan] first.")
        raise typer.Exit(1)
    
    # Get projects
    projects = ContextManager.get_projects(org_id)
    
    if not projects:
        console.print("[yellow]No projects found in this organization.[/yellow]")
        console.print("Run [cyan]traylinx projects create <name>[/cyan] to create one.")
        raise typer.Exit(1)
    
    # Interactive selection if project_id not provided
    if project_id is None:
        from InquirerPy import inquirer
        
        choices = [
            {"name": p.get('name', 'Unnamed'), "value": str(p.get('id'))}
            for p in projects
        ]
        
        project_id = inquirer.select(
            message="Select project:",
            choices=choices,
            pointer="→",
            style={"pointer": "#00c3ff", "highlighted": "#8800ff"}
        ).execute()
    
    # Validate project exists
    project = next((p for p in projects if str(p.get("id")) == str(project_id)), None)
    
    if not project:
        console.print(f"[red]Project '{project_id}' not found.[/red]")
        console.print("Run [cyan]traylinx projects list[/cyan] to see available projects.")
        raise typer.Exit(1)
    
    # Switch project
    ContextManager.set_current_project_id(project_id)
    
    console.print(f"[green]✓ Switched to project:[/green] {project.get('name')}")


@app.command("show")
def show_project(
    project_id: Optional[str] = typer.Argument(None, help="Project ID (defaults to current)")
):
    """Show project details."""
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    org_id = ContextManager.require_organization()
    
    if project_id is None:
        project_id = ContextManager.get_current_project_id()
        if not project_id:
            console.print("[yellow]No project specified or selected.[/yellow]")
            console.print("Run [cyan]traylinx projects use <id>[/cyan] or provide a project ID.")
            raise typer.Exit(1)
    
    # Fetch project details from API
    try:
        response = httpx.get(
            f"{METRICS_API_URL}/organizations/{org_id}/projects/{project_id}",
            params={"secret": "true"},
            headers=_get_headers(),
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        project = data.get("data", {})
        attrs = project.get("attributes", {})
        meta = data.get("meta", {})
        secrets = meta.get("secrets", {})
        
        console.print(Panel(f"[bold]{attrs.get('name', project_id)}[/bold]", subtitle=f"Project ID: {project_id}"))
        
        console.print(f"  Organization: [cyan]{org_id}[/cyan]")
        
        if secrets:
            console.print("\n[bold]API Credentials[/bold]")
            console.print(f"  Public Key:  [dim]{secrets.get('publicKey', 'N/A')}[/dim]")
            console.print(f"  Secret Key:  [dim]{secrets.get('secretKey', '********')}[/dim]")
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Project '{project_id}' not found.[/red]")
        else:
            console.print(f"[red]Error fetching project: {e.response.status_code}[/red]")
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        raise typer.Exit(1)


@app.command("create")
def create_project(
    name: str = typer.Argument(..., help="Project name")
):
    """Create a new project."""
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    org_id = ContextManager.require_organization()
    
    console.print(f"Creating project [bold]{name}[/bold]...")
    
    try:
        response = httpx.post(
            f"{METRICS_API_URL}/organizations/{org_id}/projects",
            json={
                "data": {
                    "attributes": {
                        "name": name
                    }
                }
            },
            headers=_get_headers(),
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        project = data.get("data", {})
        project_id = project.get("id")
        
        console.print(f"[green]✓ Project created![/green]")
        console.print(f"  ID:   [cyan]{project_id}[/cyan]")
        console.print(f"  Name: {name}")
        console.print(f"\nRun [cyan]traylinx projects use {project_id}[/cyan] to switch to it.")
        
        # Refresh context to include new project
        ContextManager.load_from_api()
        
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error creating project: {e.response.status_code}[/red]")
        if e.response.text:
            console.print(f"[dim]{e.response.text}[/dim]")
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# API Keys Subcommands
# ============================================================================

@keys_app.command("list")
def list_keys(
    project_id: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID")
):
    """List API keys for a project."""
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    org_id = ContextManager.require_organization()
    
    if project_id is None:
        project_id = ContextManager.require_project()
    
    # Fetch project with secrets to get API keys
    try:
        response = httpx.get(
            f"{METRICS_API_URL}/organizations/{org_id}/projects/{project_id}",
            params={"secret": "true"},
            headers=_get_headers(),
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # API keys are in the included or relationships
        included = data.get("included", [])
        api_keys = [item for item in included if item.get("type") == "api_key"]
        
        if not api_keys:
            console.print("[yellow]No API keys found for this project.[/yellow]")
            console.print("Run [cyan]traylinx projects keys create[/cyan] to create one.")
            return
        
        table = Table(title="API Keys")
        table.add_column("ID", style="cyan")
        table.add_column("Note")
        table.add_column("Created At", style="dim")
        
        for key in api_keys:
            attrs = key.get("attributes", {})
            table.add_row(
                str(key.get("id", "")),
                attrs.get("note", ""),
                attrs.get("created_at", "")[:10] if attrs.get("created_at") else ""
            )
        
        console.print(table)
        
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error fetching API keys: {e.response.status_code}[/red]")
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        raise typer.Exit(1)


@keys_app.command("create")
def create_key(
    note: str = typer.Option("CLI created", "--note", "-n", help="Note for the API key"),
    project_id: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID")
):
    """Create a new API key."""
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    org_id = ContextManager.require_organization()
    
    if project_id is None:
        project_id = ContextManager.require_project()
    
    console.print(f"Creating API key...")
    
    try:
        response = httpx.post(
            f"{METRICS_API_URL}/organizations/{org_id}/projects/{project_id}/api_keys",
            json={
                "data": {
                    "attributes": {
                        "note": note
                    }
                }
            },
            headers=_get_headers(),
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        key_data = data.get("data", {})
        attrs = key_data.get("attributes", {})
        
        console.print(f"[green]✓ API key created![/green]")
        console.print(f"\n[bold]Save this key - it will only be shown once![/bold]")
        console.print(f"  Key: [cyan]{attrs.get('key', attrs.get('api_key', 'N/A'))}[/cyan]")
        console.print(f"  Note: {note}")
        
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error creating API key: {e.response.status_code}[/red]")
        if e.response.text:
            console.print(f"[dim]{e.response.text}[/dim]")
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        raise typer.Exit(1)
