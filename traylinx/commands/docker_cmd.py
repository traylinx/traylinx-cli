"""Docker-powered agent commands for Traylinx CLI.

Commands:
- traylinx run     - Start agent via Docker Compose
- traylinx stop    - Stop running agent containers
- traylinx logs    - View agent container logs
- traylinx list    - List running agents
- traylinx publish - Build and push to GHCR
- traylinx pull    - Download and run any agent
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from traylinx.utils.docker import (
    check_docker,
    find_compose_file,
    run_compose_command,
    get_running_containers,
    is_project_running,
    inject_stargate_env,
)

console = Console()


def run_command(
    path: Optional[Path] = typer.Argument(
        None,
        help="Path to agent project (default: current directory)",
    ),
    detach: bool = typer.Option(
        True,
        "--detach/--no-detach",
        "-d",
        help="Run in background (detached mode)",
    ),
    build: bool = typer.Option(
        True,
        "--build/--no-build",
        "-b",
        help="Build images before starting",
    ),
    native: bool = typer.Option(
        False,
        "--native",
        "-n",
        help="Skip Docker, use native Python execution",
    ),
    prod: bool = typer.Option(
        False,
        "--prod",
        "-p",
        help="Use production compose file (with Postgres)",
    ),
):
    """
    🚀 Start an agent via Docker Compose.
    
    This command wraps `docker compose up` with Traylinx-specific
    configuration, automatically injecting Stargate network variables.
    
    [bold]Examples:[/bold]
    
        traylinx run                  # Run agent in current directory
        traylinx run ./my-agent       # Run agent in specified directory
        traylinx run --no-detach      # Run in foreground (see logs)
        traylinx run --prod           # Use production config (Postgres)
        traylinx run --native         # Skip Docker, use local Python
    """
    project_dir = Path(path) if path else Path.cwd()
    project_dir = project_dir.resolve()
    
    if not project_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {project_dir}")
        raise typer.Exit(1)
    
    # Check for native mode
    if native:
        _run_native(project_dir)
        return
    
    # Check Docker
    docker_info = check_docker()
    
    if not docker_info.installed:
        console.print(Panel(
            "[yellow]Docker not found![/yellow]\n\n"
            "Install Docker Desktop: https://docker.com/get-started\n\n"
            "Or use [cyan]--native[/cyan] to run with local Python.",
            title="Docker Required",
        ))
        raise typer.Exit(1)
    
    if not docker_info.running:
        console.print(Panel(
            "[yellow]Docker is installed but not running.[/yellow]\n\n"
            "Please start Docker Desktop and try again.\n\n"
            "Or use [cyan]--native[/cyan] to run with local Python.",
            title="Docker Not Running",
        ))
        raise typer.Exit(1)
    
    # Find compose file
    compose_file = find_compose_file(project_dir)
    
    # Check for production override
    if prod:
        prod_file = project_dir / "docker-compose.prod.yml"
        if prod_file.exists():
            compose_file = prod_file
        else:
            console.print("[yellow]Warning:[/yellow] No docker-compose.prod.yml found, using default")
    
    if not compose_file:
        console.print(Panel(
            "[yellow]No docker-compose.yml found![/yellow]\n\n"
            "Create one or use [cyan]traylinx init[/cyan] to create a new agent.",
            title="Compose File Missing",
        ))
        raise typer.Exit(1)
    
    console.print(f"\n[bold blue]🐳 Starting agent...[/bold blue]")
    console.print(f"[dim]Project:[/dim] {project_dir.name}")
    console.print(f"[dim]Compose:[/dim] {compose_file.name}")
    console.print(f"[dim]Docker:[/dim] v{docker_info.version}")
    
    # Inject Stargate environment
    env_vars = inject_stargate_env(project_dir)
    
    # Show connection info
    if "NATS_URL" in env_vars:
        console.print(f"[dim]Stargate:[/dim] {env_vars['NATS_URL']}")
    
    console.print()
    
    # Run docker compose up
    try:
        args = []
        if prod:
            args.extend(["-f", str(compose_file)])
        
        result = run_compose_command(
            "up",
            project_dir,
            *args,
            detach=detach,
            build=build,
            env_vars=env_vars,
        )
        
        if result.returncode == 0:
            if detach:
                console.print("\n[bold green]✓ Agent started successfully![/bold green]")
                console.print("\n[dim]Commands:[/dim]")
                console.print("  [cyan]traylinx logs[/cyan]  - View logs")
                console.print("  [cyan]traylinx stop[/cyan]  - Stop agent")
                console.print("  [cyan]traylinx list[/cyan]  - List running agents")
            else:
                console.print("\n[dim]Agent stopped.[/dim]")
        else:
            console.print("\n[red]Error:[/red] Failed to start agent")
            raise typer.Exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        if not detach:
            console.print("[dim]Stopping containers...[/dim]")
            run_compose_command("down", project_dir)


def stop_command(
    path: Optional[Path] = typer.Argument(
        None,
        help="Path to agent project (default: current directory)",
    ),
    remove_volumes: bool = typer.Option(
        False,
        "--volumes",
        "-v",
        help="Remove volumes (WARNING: deletes data)",
    ),
):
    """
    ⏹️  Stop a running agent.
    
    This command wraps `docker compose down` to stop all containers
    associated with the agent project.
    
    [bold]Examples:[/bold]
    
        traylinx stop                 # Stop agent in current directory
        traylinx stop ./my-agent      # Stop agent in specified directory
        traylinx stop --volumes       # Stop and remove volumes (data loss!)
    """
    project_dir = Path(path) if path else Path.cwd()
    project_dir = project_dir.resolve()
    
    if not project_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {project_dir}")
        raise typer.Exit(1)
    
    # Check if running
    if not is_project_running(project_dir):
        console.print(f"[yellow]No running containers found for:[/yellow] {project_dir.name}")
        raise typer.Exit(0)
    
    console.print(f"\n[bold blue]⏹️  Stopping agent...[/bold blue]")
    console.print(f"[dim]Project:[/dim] {project_dir.name}")
    console.print()
    
    # Run docker compose down
    args = []
    if remove_volumes:
        args.append("-v")
        console.print("[yellow]Warning:[/yellow] Removing volumes (data will be deleted)")
    
    result = run_compose_command("down", project_dir, *args)
    
    if result.returncode == 0:
        console.print("\n[bold green]✓ Agent stopped successfully![/bold green]")
    else:
        console.print("\n[red]Error:[/red] Failed to stop agent")
        raise typer.Exit(1)


def logs_command(
    path: Optional[Path] = typer.Argument(
        None,
        help="Path to agent project (default: current directory)",
    ),
    follow: bool = typer.Option(
        True,
        "--follow/--no-follow",
        "-f",
        help="Follow log output (Ctrl+C to stop)",
    ),
    tail: int = typer.Option(
        100,
        "--tail",
        "-t",
        help="Number of lines to show",
    ),
    service: Optional[str] = typer.Option(
        None,
        "--service",
        "-s",
        help="Show logs for specific service only",
    ),
):
    """
    📋 View agent container logs.
    
    Stream logs from the running agent containers.
    
    [bold]Examples:[/bold]
    
        traylinx logs                 # Follow logs (Ctrl+C to stop)
        traylinx logs --no-follow     # Show recent logs and exit
        traylinx logs --tail 50       # Show last 50 lines
        traylinx logs -s agent        # Show only 'agent' service logs
    """
    project_dir = Path(path) if path else Path.cwd()
    project_dir = project_dir.resolve()
    
    if not project_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {project_dir}")
        raise typer.Exit(1)
    
    # Check if running
    if not is_project_running(project_dir):
        console.print(f"[yellow]No running containers found for:[/yellow] {project_dir.name}")
        console.print("\n[dim]Start the agent with:[/dim] [cyan]traylinx run[/cyan]")
        raise typer.Exit(0)
    
    console.print(f"[dim]Showing logs for:[/dim] {project_dir.name}")
    if follow:
        console.print("[dim]Press Ctrl+C to stop following[/dim]\n")
    
    # Build args
    args = ["--tail", str(tail)]
    if service:
        args.append(service)
    
    try:
        run_compose_command(
            "logs",
            project_dir,
            *args,
            follow_logs=follow,
        )
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped following logs.[/dim]")


def list_command():
    """
    📊 List all running Traylinx agents.
    
    Shows a table of all currently running agent containers
    across all projects.
    """
    import subprocess
    
    console.print("\n[bold blue]📊 Running Agents[/bold blue]\n")
    
    # Use docker ps to find running containers with traylinx labels
    try:
        result = subprocess.run(
            [
                "docker", "ps",
                "--filter", "label=com.docker.compose.project",
                "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Labels}}"
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode != 0:
            console.print("[red]Error:[/red] Failed to list containers")
            raise typer.Exit(1)
        
        lines = result.stdout.strip().split("\n")
        lines = [line for line in lines if line.strip()]
        
        if not lines:
            console.print("[dim]No running containers found.[/dim]")
            console.print("\n[dim]Start an agent with:[/dim] [cyan]traylinx run[/cyan]")
            return
        
        table = Table(show_header=True)
        table.add_column("Container ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Status")
        table.add_column("Ports", style="dim")
        
        for line in lines:
            parts = line.split("\t")
            if len(parts) >= 4:
                container_id = parts[0][:12]
                name = parts[1]
                status = parts[2]
                ports = parts[3] if parts[3] else "-"
                
                # Color status
                if "Up" in status:
                    status = f"[green]{status}[/green]"
                elif "Exited" in status:
                    status = f"[red]{status}[/red]"
                
                table.add_row(container_id, name, status, ports)
        
        console.print(table)
        
    except subprocess.TimeoutExpired:
        console.print("[red]Error:[/red] Docker command timed out")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]Error:[/red] Docker not found")
        raise typer.Exit(1)


def _run_native(project_dir: Path):
    """Run agent using native Python (fallback when Docker not available)."""
    import subprocess
    import sys
    
    console.print("\n[bold yellow]🐍 Running in native Python mode[/bold yellow]")
    console.print(f"[dim]Project:[/dim] {project_dir.name}")
    console.print()
    
    # Check for pyproject.toml or requirements.txt
    pyproject = project_dir / "pyproject.toml"
    requirements = project_dir / "requirements.txt"
    
    # Try to find the main entry point
    main_candidates = [
        project_dir / "main.py",
        project_dir / "app.py",
        project_dir / "src" / "main.py",
        project_dir / "agent" / "main.py",
    ]
    
    main_file = None
    for candidate in main_candidates:
        if candidate.exists():
            main_file = candidate
            break
    
    if not main_file:
        console.print("[red]Error:[/red] Could not find main.py or app.py")
        console.print("\n[dim]Expected locations:[/dim]")
        for c in main_candidates:
            console.print(f"  - {c.relative_to(project_dir)}")
        raise typer.Exit(1)
    
    console.print(f"[dim]Entry point:[/dim] {main_file.relative_to(project_dir)}")
    console.print()
    
    # Inject environment variables
    env_vars = inject_stargate_env(project_dir)
    import os
    env = os.environ.copy()
    env.update(env_vars)
    
    # Run with Python
    try:
        subprocess.run(
            [sys.executable, str(main_file)],
            cwd=project_dir,
            env=env,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")


def publish_command(
    path: Optional[Path] = typer.Argument(
        None,
        help="Path to agent project (default: current directory)",
    ),
    multiarch: bool = typer.Option(
        True,
        "--multiarch/--no-multiarch",
        "-m",
        help="Build for AMD64 and ARM64 (requires buildx)",
    ),
    tag: Optional[str] = typer.Option(
        None,
        "--tag",
        "-t",
        help="Override version tag (default: from pyproject.toml)",
    ),
    latest: bool = typer.Option(
        True,
        "--latest/--no-latest",
        help="Also tag as :latest",
    ),
):
    """
    📦 Build and publish agent to GHCR.
    
    This command builds a multi-architecture Docker image and pushes it
    to GitHub Container Registry (ghcr.io/traylinx/).
    
    [bold]Examples:[/bold]
    
        traylinx publish              # Build + push from current directory
        traylinx publish --no-multiarch  # Build for current platform only
        traylinx publish --tag v2.0.0    # Override version tag
    
    [bold]Requirements:[/bold]
    
        • Docker with buildx (for multi-arch builds)
        • GHCR authentication (docker login ghcr.io)
    """
    from traylinx.utils.registry import (
        load_manifest,
        check_buildx,
        check_ghcr_auth,
        build_multiarch_image,
        build_image,
        push_image,
    )
    
    project_dir = Path(path) if path else Path.cwd()
    project_dir = project_dir.resolve()
    
    if not project_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {project_dir}")
        raise typer.Exit(1)
    
    # Check for Dockerfile
    dockerfile = project_dir / "Dockerfile"
    if not dockerfile.exists():
        console.print(Panel(
            "[yellow]No Dockerfile found![/yellow]\n\n"
            "Create a Dockerfile or use [cyan]traylinx init[/cyan] to create a new agent.",
            title="Dockerfile Missing",
        ))
        raise typer.Exit(1)
    
    # Load manifest
    manifest = load_manifest(project_dir)
    if not manifest:
        console.print(Panel(
            "[yellow]No manifest found![/yellow]\n\n"
            "Create a pyproject.toml or traylinx-agent.yaml file.",
            title="Manifest Missing",
        ))
        raise typer.Exit(1)
    
    # Override tag if provided
    version = tag or manifest.version
    image_name = f"ghcr.io/traylinx/{manifest.image_name}"
    versioned_tag = f"{image_name}:{version}"
    latest_tag = f"{image_name}:latest"
    
    console.print("\n[bold blue]📦 Publishing agent to GHCR...[/bold blue]")
    console.print(f"[dim]Agent:[/dim] {manifest.name}")
    console.print(f"[dim]Version:[/dim] {version}")
    console.print(f"[dim]Image:[/dim] {versioned_tag}")
    console.print()
    
    # Check Docker
    docker_info = check_docker()
    if not docker_info.installed or not docker_info.running:
        console.print("[red]Error:[/red] Docker is not running")
        raise typer.Exit(1)
    
    # Check GHCR auth
    if not check_ghcr_auth():
        console.print(Panel(
            "[yellow]Not authenticated to GHCR![/yellow]\n\n"
            "Run: [cyan]docker login ghcr.io[/cyan]\n\n"
            "Or set GITHUB_TOKEN environment variable.",
            title="Authentication Required",
        ))
        raise typer.Exit(1)
    
    # Build and push
    if multiarch:
        if not check_buildx():
            console.print("[yellow]Warning:[/yellow] Buildx not available, falling back to single-arch")
            multiarch = False
    
    console.print("[dim]Building image...[/dim]")
    
    if multiarch:
        console.print("[dim]Platforms:[/dim] linux/amd64, linux/arm64")
        result = build_multiarch_image(
            project_dir,
            versioned_tag,
            push=True,
            latest_tag=latest_tag if latest else None,
        )
    else:
        result = build_image(project_dir, versioned_tag)
        if result.returncode == 0:
            console.print("[dim]Pushing image...[/dim]")
            result = push_image(versioned_tag)
    
    if result.returncode != 0:
        console.print("\n[red]Error:[/red] Failed to build/push image")
        raise typer.Exit(1)
    
    # Tag as latest (only for single-arch, multiarch handles this in build)
    if latest and not multiarch:
        import subprocess
        subprocess.run(["docker", "tag", versioned_tag, latest_tag])
        push_image(latest_tag)
    
    console.print("\n[bold green]✓ Published successfully![/bold green]")
    console.print(f"\n[dim]Image:[/dim] {versioned_tag}")
    if latest:
        console.print(f"[dim]Latest:[/dim] {latest_tag}")
    console.print(f"\n[dim]Anyone can now run:[/dim] [cyan]traylinx pull {manifest.image_name}[/cyan]")


def pull_command(
    agent: str = typer.Argument(
        ...,
        help="Agent name (e.g., 'weather-agent' or 'ghcr.io/user/agent:tag')",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Local port to expose",
    ),
    run_after: bool = typer.Option(
        True,
        "--run/--no-run",
        "-r",
        help="Start the agent after pulling",
    ),
):
    """
    ⬇️  Download and run any published agent.
    
    This command pulls a Docker image from GHCR and starts it locally,
    giving you the "Ollama experience" for agents.
    
    [bold]Examples:[/bold]
    
        traylinx pull weather-agent           # Pull from ghcr.io/traylinx/
        traylinx pull weather-agent --port 9000  # Use custom port
        traylinx pull ghcr.io/user/agent:v1   # Pull specific image
        traylinx pull weather-agent --no-run  # Just download, don't start
    """
    from traylinx.utils.registry import (
        pull_image,
        generate_compose_file,
        get_agent_directory,
    )
    
    # Determine full image tag
    if "/" in agent and ":" in agent:
        # Full image reference provided
        image_tag = agent
        agent_name = agent.split("/")[-1].split(":")[0]
    elif "/" in agent:
        # Image with path but no tag
        image_tag = f"{agent}:latest"
        agent_name = agent.split("/")[-1]
    else:
        # Just agent name, assume traylinx registry
        image_tag = f"ghcr.io/traylinx/{agent}:latest"
        agent_name = agent
    
    console.print("\n[bold blue]⬇️  Pulling agent...[/bold blue]")
    console.print(f"[dim]Agent:[/dim] {agent_name}")
    console.print(f"[dim]Image:[/dim] {image_tag}")
    console.print()
    
    # Check Docker
    docker_info = check_docker()
    if not docker_info.installed or not docker_info.running:
        console.print("[red]Error:[/red] Docker is not running")
        raise typer.Exit(1)
    
    # Pull image
    console.print("[dim]Downloading image...[/dim]")
    result = pull_image(image_tag)
    
    if result.returncode != 0:
        console.print(f"\n[red]Error:[/red] Failed to pull {image_tag}")
        console.print("\n[dim]Check that the image exists and you have access.[/dim]")
        raise typer.Exit(1)
    
    console.print("[bold green]✓ Image downloaded![/bold green]")
    
    # Generate compose file
    agent_dir = get_agent_directory(agent_name)
    compose_path = generate_compose_file(
        agent_name,
        image_tag,
        agent_dir,
        port=port,
    )
    
    console.print(f"[dim]Config saved to:[/dim] {compose_path}")
    
    if run_after:
        console.print("\n[dim]Starting agent...[/dim]")
        
        # Inject Stargate env
        env_vars = inject_stargate_env(agent_dir)
        
        result = run_compose_command(
            "up",
            agent_dir,
            detach=True,
            build=False,
            env_vars=env_vars,
        )
        
        if result.returncode == 0:
            console.print(f"\n[bold green]✓ Agent running at http://localhost:{port}[/bold green]")
            console.print("\n[dim]Commands:[/dim]")
            console.print(f"  [cyan]cd {agent_dir} && traylinx logs[/cyan]")
            console.print(f"  [cyan]cd {agent_dir} && traylinx stop[/cyan]")
        else:
            console.print("\n[red]Error:[/red] Failed to start agent")
            raise typer.Exit(1)
    else:
        console.print(f"\n[dim]To start the agent:[/dim]")
        console.print(f"  [cyan]cd {agent_dir} && traylinx run[/cyan]")
