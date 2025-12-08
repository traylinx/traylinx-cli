"""Validate command - Validate traylinx-agent.yaml manifest."""

from pathlib import Path

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from traylinx.constants import MANIFEST_FILENAME
from traylinx.models.manifest import AgentManifest

console = Console()


def validate_command(
    manifest_path: Path = typer.Option(
        Path(MANIFEST_FILENAME),
        "--manifest",
        "-m",
        help="Path to manifest file",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Enable strict validation (warnings become errors)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Only show errors, no success messages",
    ),
):
    """
    Validate traylinx-agent.yaml manifest.
    
    [bold]Checks:[/bold]
    
    • YAML syntax
    • Required fields
    • Field formats (semver, URLs, etc.)
    • Capability taxonomy
    • Pricing configuration
    
    [bold]Examples:[/bold]
    
        traylinx validate
        traylinx validate --manifest custom.yaml
        traylinx validate --strict
    """
    # Check file exists
    if not manifest_path.exists():
        console.print(f"[bold red]Error:[/bold red] Manifest not found: {manifest_path}")
        console.print(f"\nCreate one with: [bold]traylinx init my-agent[/bold]")
        raise typer.Exit(1)
    
    if not quiet:
        console.print(f"\n[bold blue]Validating:[/bold blue] {manifest_path}\n")
    
    # Load YAML
    try:
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        console.print(f"[bold red]YAML Error:[/bold red] {e}")
        raise typer.Exit(1)
    
    if data is None:
        console.print("[bold red]Error:[/bold red] Manifest is empty")
        raise typer.Exit(1)
    
    # Validate with Pydantic
    try:
        manifest = AgentManifest.model_validate(data)
    except ValidationError as e:
        console.print("[bold red]Validation Failed[/bold red]\n")
        
        # Create error table
        table = Table(show_header=True)
        table.add_column("Field", style="cyan")
        table.add_column("Error", style="red")
        
        for error in e.errors():
            field = ".".join(str(p) for p in error["loc"])
            table.add_row(field, error["msg"])
        
        console.print(table)
        console.print(f"\n[dim]Total errors: {len(e.errors())}[/dim]")
        raise typer.Exit(1)
    
    # Validation passed - show summary
    if not quiet:
        _print_summary(manifest)
    
    console.print("[bold green]✓ Manifest is valid![/bold green]")


def _print_summary(manifest: AgentManifest):
    """Print manifest summary."""
    info = manifest.info
    
    table = Table(show_header=False, box=None)
    table.add_column("Field", style="dim")
    table.add_column("Value", style="bold")
    
    table.add_row("Name", info.name)
    table.add_row("Display Name", info.display_name)
    table.add_row("Version", info.version)
    table.add_row("Author", f"{info.author.name} <{info.author.email or 'N/A'}>")
    table.add_row("Capabilities", str(len(manifest.capabilities)))
    table.add_row("Endpoints", str(len(manifest.endpoints)))
    table.add_row("Pricing", manifest.pricing.model)
    
    console.print(table)
    console.print()
