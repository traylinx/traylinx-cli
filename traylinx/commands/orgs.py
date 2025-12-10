"""
Organizations management command for Traylinx CLI.

Commands:
    traylinx orgs list    - List available organizations
    traylinx orgs use     - Switch current organization
    traylinx orgs current - Show current organization
"""

import typer
from rich.console import Console
from rich.table import Table

from traylinx.auth import AuthManager
from traylinx.context import ContextManager

app = typer.Typer(
    help="Manage organizations",
    invoke_without_command=True,
    no_args_is_help=False
)
console = Console()


@app.callback()
def orgs_callback(ctx: typer.Context):
    """Manage your organizations."""
    if ctx.invoked_subcommand is None:
        # Show friendly help instead of error
        console.print()
        console.print("[bold cyan]traylinx orgs[/bold cyan] - Manage organizations\n")
        console.print("[bold]Commands:[/bold]")
        console.print("  [cyan]list[/cyan]      List your organizations")
        console.print("  [cyan]use[/cyan]       Switch organization (interactive selector)")
        console.print("  [cyan]current[/cyan]   Show current organization and project")
        console.print("  [cyan]refresh[/cyan]   Reload data from Traylinx API")
        console.print()
        console.print("[bold]Examples:[/bold]")
        console.print("  $ traylinx orgs list")
        console.print("  $ traylinx orgs use")
        console.print()
        console.print("[dim]For more info: traylinx help orgs[/dim]")
        console.print()


@app.command("list")
def list_orgs():
    """List available organizations."""
    # Require authentication
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    orgs = ContextManager.get_organizations()
    
    if not orgs:
        console.print("[yellow]No organizations found.[/yellow]")
        console.print("Try running [cyan]traylinx login[/cyan] to refresh your context.")
        return
    
    current_org_id = ContextManager.get_current_organization_id()
    
    table = Table(title="Organizations")
    table.add_column("", style="dim", width=2)
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Projects", justify="right")
    
    for org in orgs:
        is_current = str(org.get("id")) == str(current_org_id)
        marker = "→" if is_current else ""
        project_count = len(org.get("projects", []))
        
        table.add_row(
            marker,
            str(org.get("id", "")),
            org.get("name", ""),
            str(project_count)
        )
    
    console.print(table)
    
    if current_org_id:
        console.print(f"\n[dim]Current organization: {current_org_id}[/dim]")


@app.command("use")
def use_org(
    org_id: str = typer.Argument(None, help="Organization ID to switch to (interactive if not provided)")
):
    """Switch to a different organization."""
    # Require authentication
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    orgs = ContextManager.get_organizations()
    
    if not orgs:
        console.print("[yellow]No organizations found.[/yellow]")
        console.print("Run [cyan]traylinx login[/cyan] to refresh your context.")
        raise typer.Exit(1)
    
    # Interactive selection if org_id not provided
    if org_id is None:
        from InquirerPy import inquirer
        
        choices = [
            {"name": f"{o.get('name')} ({len(o.get('projects', []))} projects)", "value": str(o.get('id'))}
            for o in orgs
        ]
        
        org_id = inquirer.select(
            message="Select organization:",
            choices=choices,
            pointer="→",
            style={"pointer": "#00c3ff", "highlighted": "#8800ff"}
        ).execute()
    
    # Validate org exists in context
    org = next((o for o in orgs if str(o.get("id")) == str(org_id)), None)
    
    if not org:
        console.print(f"[red]Organization '{org_id}' not found.[/red]")
        console.print("Run [cyan]traylinx orgs list[/cyan] to see available organizations.")
        raise typer.Exit(1)
    
    # Switch organization
    ContextManager.set_current_organization_id(org_id)
    
    console.print(f"[green]✓ Switched to organization:[/green] {org.get('name')}")
    
    # Show projects in this org
    projects = org.get("projects", [])
    if projects:
        console.print(f"\n[dim]Available projects ({len(projects)}):[/dim]")
        for p in projects[:5]:  # Show first 5
            console.print(f"  • {p.get('name')} [dim]({p.get('id')})[/dim]")
        if len(projects) > 5:
            console.print(f"  [dim]... and {len(projects) - 5} more[/dim]")
        console.print("\nRun [cyan]traylinx projects list[/cyan] to see all projects.")



@app.command("current")
def current_org():
    """Show current organization."""
    # Require authentication
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    org = ContextManager.get_current_organization()
    
    if not org:
        console.print("[yellow]No organization selected.[/yellow]")
        console.print("Run [cyan]traylinx orgs use <id>[/cyan] to select one.")
        return
    
    console.print(f"[bold]Current Organization[/bold]")
    console.print(f"  ID:   [cyan]{org.get('id')}[/cyan]")
    console.print(f"  Name: {org.get('name')}")
    
    projects = org.get("projects", [])
    console.print(f"  Projects: {len(projects)}")
    
    # Show current project if set
    project = ContextManager.get_current_project()
    if project:
        console.print(f"\n[bold]Current Project[/bold]")
        console.print(f"  ID:   [cyan]{project.get('id')}[/cyan]")
        console.print(f"  Name: {project.get('name')}")


@app.command("refresh")
def refresh_orgs():
    """Refresh organization and project data from Traylinx."""
    # Require authentication
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)
    
    console.print("[dim]Refreshing context from Traylinx...[/dim]")
    
    result = ContextManager.load_from_api()
    
    if result:
        orgs = result.get("organizations", [])
        console.print(f"[green]✓ Loaded {len(orgs)} organization(s)[/green]")
        
        # Show summary
        for org in orgs:
            project_count = len(org.get("projects", []))
            console.print(f"  • {org.get('name')} ({project_count} projects)")
    else:
        console.print("[yellow]Could not refresh context. Check your connection.[/yellow]")
        raise typer.Exit(1)

