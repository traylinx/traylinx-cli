"""Publish command - Publish agent to Traylinx catalog."""

from pathlib import Path

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from traylinx.api.registry import RegistryClient, RegistryError
from traylinx.constants import (
    MANIFEST_FILENAME,
    get_settings,
)
from traylinx.models.manifest import AgentManifest
from traylinx.utils.config import ConfigError, load_config

console = Console()


def publish_command(
    manifest_path: Path = typer.Option(
        Path(MANIFEST_FILENAME),
        "--manifest",
        "-m",
        help="Path to manifest file",
    ),
    registry_url: str = typer.Option(
        None,
        "--registry",
        "-r",
        help="Registry URL (default: from env/config)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate but don't actually publish",
    ),
):
    """
    Publish agent to the Traylinx catalog.

    [bold]This command:[/bold]

    1. Validates your manifest
    2. Authenticates with the registry
    3. Uploads the manifest
    4. Makes your agent discoverable

    [bold]Examples:[/bold]

        traylinx publish
        traylinx publish --dry-run
        traylinx publish --registry http://localhost:8000
    """
    console.print("\n[bold blue]Publishing to Traylinx Catalog[/bold blue]\n")

    # Step 1: Load settings
    settings = get_settings()

    # Step 2: Load and validate manifest
    if not manifest_path.exists():
        console.print(f"[bold red]Error:[/bold red] Manifest not found: {manifest_path}")
        raise typer.Exit(1) from None

    try:
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
        manifest = AgentManifest.model_validate(data)
    except yaml.YAMLError as e:
        console.print(f"[bold red]YAML Error:[/bold red] {e}")
        raise typer.Exit(1) from None
    except ValidationError:
        console.print("[bold red]Validation Failed[/bold red]")
        console.print("Run [bold]traylinx validate[/bold] for details")
        raise typer.Exit(1) from None

    console.print(
        f"[green]✓[/green] Manifest valid: [bold]{manifest.info.name}[/bold] v{manifest.info.version}"
    )

    # Step 3: Get developer credentials for publishing
    # Publishing requires YOUR Sentinel Pass credentials (not the agent's)
    import os
    
    developer_agent_id = os.environ.get("TRAYLINX_DEVELOPER_AGENT_ID")
    developer_secret = os.environ.get("TRAYLINX_DEVELOPER_SECRET")

    if not developer_agent_id or not developer_secret:
        console.print("[bold red]Error:[/bold red] Developer credentials not set")
        console.print("\n[bold]Publishing requires a Sentinel Pass for authentication.[/bold]")
        console.print("\n[bold cyan]Step 1:[/bold cyan] Create a Sentinel Pass for yourself:")
        console.print("  $ traylinx sentinel pass create --name my-developer-identity")
        console.print("\n[bold cyan]Step 2:[/bold cyan] Set environment variables:")
        console.print("  export TRAYLINX_DEVELOPER_AGENT_ID=\"agent-user-xxx\"")
        console.print("  export TRAYLINX_DEVELOPER_SECRET=\"secret-xxx\"")
        console.print("\n[bold cyan]Step 3:[/bold cyan] Publish your agent:")
        console.print("  $ traylinx publish")
        console.print("\n[dim]Note: This is YOUR identity for publishing, separate from the agent's identity.[/dim]")
        raise typer.Exit(1) from None

    # Step 4: Determine registry URL
    url = registry_url or settings.effective_registry_url
    console.print(f"[green]✓[/green] Registry: {url}")

    # Step 5: Dry run check
    if dry_run:
        console.print(
            Panel(
                "[bold yellow]Dry run mode[/bold yellow]\n\n"
                "Would publish:\n"
                f"  Agent: {manifest.info.name}\n"
                f"  Version: {manifest.info.version}\n"
                f"  To: {url}",
                title="🧪 Dry Run",
                border_style="yellow",
            )
        )
        return

    # Step 6: Publish
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Publishing...", total=None)

        client = RegistryClient(
            base_url=url,
            agent_user_id=developer_agent_id,
            client_secret=developer_secret,
            agent_key=manifest.info.name,  # The agent being published
        )

        try:
            client.publish(manifest)
            progress.update(task, completed=True)
        except RegistryError as e:
            progress.stop()
            console.print(f"\n[bold red]Publish Failed:[/bold red] {e}")
            raise typer.Exit(1) from None
        except Exception as e:
            progress.stop()
            console.print(f"\n[bold red]Error:[/bold red] {e}")
            raise typer.Exit(1) from None

    # Success!
    console.print(
        Panel(
            f"[bold green]Published successfully![/bold green]\n\n"
            f"Agent: {manifest.info.name}\n"
            f"Version: {manifest.info.version}\n\n"
            f"View in catalog:\n"
            f"  {url}/catalog/agents/{manifest.info.name}",
            title="🚀 Published",
            border_style="green",
        )
    )
