"""Skills commands - Manage AgentSkills from the CLI.

Commands:
- list: List all discovered skills
- info: Show skill details
- init: Scaffold a new skill
- validate: Validate a skill directory
- package: Create a .skill file
- install: Install a skill from file or URL
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from traylinx.skills.loader import SkillLoader, parse_skill_md
from traylinx.skills.validator import validate_skill
from traylinx.skills.packager import package_skill

app = typer.Typer(
    name="skills",
    help="🎯 Manage AgentSkills - discover, create, validate, and package skills",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

console = Console()


def get_default_skills_dir() -> Path:
    """Get the default skills directory."""
    from traylinx.utils.statebox import StateBox

    return StateBox.skills_dir()


@app.command(name="list")
def list_command(
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-p",
        help="Additional path to search for skills",
    ),
) -> None:
    """List all discovered skills."""
    search_paths = [get_default_skills_dir(), Path.cwd() / ".traylinx" / "skills"]
    if path:
        search_paths.append(path)

    loader = SkillLoader(search_paths)
    skills = loader.discover()

    if not skills:
        console.print("[yellow]No skills found.[/yellow]")
        console.print(f"[dim]Searched: {', '.join(str(p) for p in search_paths)}[/dim]")
        return

    table = Table(title="🎯 Discovered Skills")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_column("Resources", style="dim")
    table.add_column("Path", style="dim")

    for name, skill in sorted(skills.items()):
        resources = []
        if skill.has_scripts:
            resources.append("📜 scripts")
        if skill.has_references:
            resources.append("📚 refs")
        if skill.has_assets:
            resources.append("🎨 assets")

        table.add_row(
            name,
            skill.description[:60] + "..." if len(skill.description) > 60 else skill.description,
            ", ".join(resources) if resources else "-",
            str(skill.path),
        )

    console.print(table)
    console.print(f"[dim]Total: {len(skills)} skill(s)[/dim]")


@app.command(name="info")
def info_command(
    name: str = typer.Argument(..., help="Skill name to show details for"),
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-p",
        help="Additional path to search for skills",
    ),
) -> None:
    """Show detailed information about a skill."""
    search_paths = [get_default_skills_dir(), Path.cwd() / ".traylinx" / "skills"]
    if path:
        search_paths.append(path)

    loader = SkillLoader(search_paths)
    skill = loader.get(name)

    if not skill:
        console.print(f"[red]Skill '{name}' not found.[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]🎯 {skill.name}[/bold cyan]")
    console.print(f"[white]{skill.description}[/white]\n")
    console.print(f"[dim]Path: {skill.path}[/dim]")

    if skill.resources:
        console.print("\n[bold]Resources:[/bold]")
        for resource_type, files in skill.resources.items():
            console.print(f"  📁 {resource_type}/")
            for f in files[:5]:
                console.print(f"     └─ {f}")
            if len(files) > 5:
                console.print(f"     └─ ... and {len(files) - 5} more")

    if skill.body:
        console.print("\n[bold]Instructions Preview:[/bold]")
        preview = skill.body[:500]
        if len(skill.body) > 500:
            preview += "..."
        console.print(f"[dim]{preview}[/dim]")


@app.command(name="init")
def init_command(
    name: str = typer.Argument(..., help="Name for the new skill"),
    output: Path = typer.Option(
        Path.cwd(),
        "--output",
        "-o",
        help="Directory to create the skill in",
    ),
    resources: Optional[str] = typer.Option(
        None,
        "--resources",
        "-r",
        help="Comma-separated resource types to create (scripts,references,assets)",
    ),
) -> None:
    """Scaffold a new skill with a SKILL.md template."""
    skill_dir = output / name
    if skill_dir.exists():
        console.print(f"[red]Directory already exists: {skill_dir}[/red]")
        raise typer.Exit(1)

    skill_dir.mkdir(parents=True)

    # Create resource directories
    if resources:
        for resource_type in resources.split(","):
            resource_type = resource_type.strip()
            if resource_type in ["scripts", "references", "assets"]:
                (skill_dir / resource_type).mkdir()

    # Create SKILL.md template
    skill_md = skill_dir / "SKILL.md"
    template = f"""---
name: {name}
description: TODO - Describe what this skill does and when to use it.
---

# {name.replace('-', ' ').title()}

TODO: Add instructions for using this skill.

## Overview

Describe the skill's purpose and capabilities.

## Usage

Explain how to use this skill effectively.

## Examples

Provide concrete examples of the skill in action.
"""
    skill_md.write_text(template)

    console.print(f"[green]✅ Created skill scaffold: {skill_dir}[/green]")
    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  1. Edit [cyan]{skill_dir / 'SKILL.md'}[/cyan]")
    console.print("  2. Add any scripts, references, or assets")
    console.print(f"  3. Validate with: [cyan]traylinx skills validate {skill_dir}[/cyan]")
    console.print(f"  4. Package with: [cyan]traylinx skills package {skill_dir}[/cyan]")


@app.command(name="validate")
def validate_command(
    path: Path = typer.Argument(..., help="Path to the skill directory"),
) -> None:
    """Validate a skill directory."""
    path = path.resolve()

    console.print(f"[dim]Validating: {path}[/dim]\n")

    result = validate_skill(path)

    if result.errors:
        console.print("[red bold]❌ Validation Failed[/red bold]\n")
        for error in result.errors:
            console.print(f"  [red]• {error}[/red]")
    else:
        console.print("[green bold]✅ Validation Passed[/green bold]\n")

    if result.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"  [yellow]• {warning}[/yellow]")

    if not result.valid:
        raise typer.Exit(1)


@app.command(name="package")
def package_command(
    path: Path = typer.Argument(..., help="Path to the skill directory"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for the .skill file",
    ),
    skip_validation: bool = typer.Option(
        False,
        "--skip-validation",
        help="Skip validation before packaging",
    ),
) -> None:
    """Package a skill into a distributable .skill file."""
    path = path.resolve()

    console.print(f"[dim]Packaging: {path}[/dim]\n")

    result = package_skill(path, output, validate_first=not skip_validation)

    if result is None:
        console.print("[red]❌ Packaging failed - validation errors[/red]")
        console.print("[dim]Run 'traylinx skills validate' for details[/dim]")
        raise typer.Exit(1)

    console.print(f"[green]✅ Created: {result}[/green]")
    console.print(f"[dim]Size: {result.stat().st_size} bytes[/dim]")


@app.command(name="install")
def install_command(
    source: str = typer.Argument(..., help="Path to .skill file or skill directory"),
    target: Optional[Path] = typer.Option(
        None,
        "--target",
        "-t",
        help="Target directory to install to",
    ),
) -> None:
    """Install a skill from a .skill file or directory."""
    import shutil
    import zipfile

    source_path = Path(source)
    target_dir = target or get_default_skills_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    if source_path.suffix == ".skill":
        # Extract .skill file
        with zipfile.ZipFile(source_path, "r") as zf:
            zf.extractall(target_dir)
            # Get the skill name from the extracted contents
            skill_dirs = [n for n in zf.namelist() if "/" in n]
            if skill_dirs:
                skill_name = skill_dirs[0].split("/")[0]
                console.print(f"[green]✅ Installed skill: {skill_name}[/green]")
            else:
                console.print("[green]✅ Installed skill[/green]")
    elif source_path.is_dir():
        # Copy directory
        skill_name = source_path.name
        dest = target_dir / skill_name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source_path, dest)
        console.print(f"[green]✅ Installed skill: {skill_name}[/green]")
    else:
        console.print(f"[red]Invalid source: {source}[/red]")
        raise typer.Exit(1)

    console.print(f"[dim]Location: {target_dir}[/dim]")
