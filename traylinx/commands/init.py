"""Init command - Create new agent project."""

import re
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from jinja2 import Environment, FileSystemLoader

from traylinx.constants import (
    MANIFEST_FILENAME,
    TEMPLATE_BASIC,
    AVAILABLE_TEMPLATES,
)

console = Console()

# Template directory (bundled with package)
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def init_command(
    name: str = typer.Argument(
        ...,
        help="Agent name (lowercase letters, numbers, and hyphens only)",
    ),
    template: str = typer.Option(
        TEMPLATE_BASIC,
        "--template",
        "-t",
        help=f"Project template: {', '.join(AVAILABLE_TEMPLATES)}",
    ),
    directory: Path = typer.Option(
        Path("."),
        "--dir",
        "-d",
        help="Parent directory for the new project",
    ),
    author_name: str = typer.Option(
        "Developer",
        "--author",
        "-a",
        help="Author name for manifest",
    ),
    author_email: str = typer.Option(
        "dev@example.com",
        "--email",
        "-e",
        help="Author email for manifest",
    ),
):
    """
    Create a new Traylinx agent project.
    
    [bold]Examples:[/bold]
    
        traylinx init my-research-agent
        traylinx init weather-bot --template basic
        traylinx init my-agent --author "John Doe" --email john@example.com
    """
    # Validate name format
    if len(name) < 2:
        console.print("[bold red]Error:[/bold red] Name must be at least 2 characters")
        raise typer.Exit(1)
    
    if not re.match(r"^[a-z][a-z0-9-]*[a-z0-9]$", name) or "--" in name:
        console.print(
            "[bold red]Error:[/bold red] Agent name must be lowercase, "
            "start with a letter, and contain only letters, numbers, and single hyphens."
        )
        console.print(f"  Invalid: [red]{name}[/red]")
        console.print(f"  Valid examples: my-agent, research-bot-v2")
        raise typer.Exit(1)
    
    # Check template exists
    template_dir = TEMPLATES_DIR / template
    if not template_dir.exists():
        console.print(f"[bold red]Error:[/bold red] Template '{template}' not found.")
        console.print(f"Available templates: {', '.join(AVAILABLE_TEMPLATES)}")
        raise typer.Exit(1)
    
    # Check target directory
    project_dir = directory / name
    if project_dir.exists():
        console.print(f"[bold red]Error:[/bold red] Directory already exists: {project_dir}")
        raise typer.Exit(1)
    
    # Create project
    console.print(f"\n[bold blue]Creating agent:[/bold blue] {name}")
    console.print(f"[dim]Template: {template}[/dim]")
    console.print(f"[dim]Location: {project_dir.absolute()}[/dim]\n")
    
    # Create directory structure
    project_dir.mkdir(parents=True)
    (project_dir / "app").mkdir()
    (project_dir / "tests").mkdir()
    (project_dir / "schemas").mkdir()
    
    # Setup Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(template_dir),
        keep_trailing_newline=True,
    )
    
    # Context for templates
    context = {
        "agent_name": name,
        "display_name": name.replace("-", " ").title(),
        "version": "0.1.0",
        "author_name": author_name,
        "author_email": author_email,
        "manifest_filename": MANIFEST_FILENAME,
    }
    
    # Process templates
    files_created = []
    for template_file in template_dir.rglob("*"):
        if template_file.is_file():
            rel_path = template_file.relative_to(template_dir)
            
            if template_file.suffix == ".j2":
                # Render Jinja2 template
                output_path = project_dir / str(rel_path).replace(".j2", "")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                template_obj = env.get_template(str(rel_path))
                content = template_obj.render(**context)
                output_path.write_text(content)
            else:
                # Copy file directly
                output_path = project_dir / rel_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(template_file, output_path)
            
            files_created.append(output_path.relative_to(project_dir))
    
    # Show created files
    console.print("[green]✓[/green] Created project structure:")
    for f in sorted(files_created):
        console.print(f"  [dim]{f}[/dim]")
    
    # Success message
    console.print(
        Panel(
            f"[bold green]Agent '{name}' created successfully![/bold green]\n\n"
            f"Next steps:\n"
            f"  [bold]cd {name}[/bold]\n"
            f"  [bold]pip install -e .[/bold]\n"
            f"  [bold]traylinx validate[/bold]\n"
            f"  [bold]traylinx publish[/bold]",
            title="🚀 Success",
            border_style="green",
        )
    )
