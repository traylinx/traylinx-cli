"""Docker utilities for Traylinx CLI.

This module provides Docker detection, management, and compose wrappers
for running agents in containers.
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


@dataclass
class DockerInfo:
    """Information about Docker installation."""
    
    installed: bool
    version: Optional[str] = None
    compose_available: bool = False
    compose_version: Optional[str] = None
    running: bool = False
    error: Optional[str] = None


def check_docker() -> DockerInfo:
    """Check if Docker is installed and running.
    
    Returns:
        DockerInfo with installation and runtime status
    """
    info = DockerInfo(installed=False)
    
    # Check if docker command exists
    docker_path = shutil.which("docker")
    if not docker_path:
        info.error = "Docker not found in PATH"
        return info
    
    info.installed = True
    
    # Get Docker version
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            info.version = result.stdout.strip()
            info.running = True
        else:
            # Docker installed but daemon not running
            info.running = False
            info.error = "Docker daemon not running"
    except subprocess.TimeoutExpired:
        info.error = "Docker command timed out"
    except Exception as e:
        info.error = str(e)
    
    # Check for Docker Compose
    try:
        # Try new docker compose (v2)
        result = subprocess.run(
            ["docker", "compose", "version", "--short"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            info.compose_available = True
            info.compose_version = result.stdout.strip()
    except Exception:
        pass
    
    # Fallback to docker-compose (v1)
    if not info.compose_available:
        try:
            result = subprocess.run(
                ["docker-compose", "version", "--short"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                info.compose_available = True
                info.compose_version = result.stdout.strip()
        except Exception:
            pass
    
    return info


def get_compose_command() -> list[str]:
    """Get the appropriate compose command (v2 or v1).
    
    Returns:
        List of command parts, e.g. ["docker", "compose"] or ["docker-compose"]
    """
    # Try docker compose v2 first
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return ["docker", "compose"]
    except Exception:
        pass
    
    # Fallback to docker-compose v1
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    
    # Default to v2 style
    return ["docker", "compose"]


def find_compose_file(project_dir: Path) -> Optional[Path]:
    """Find the docker-compose file in a project directory.
    
    Args:
        project_dir: Path to the project root
        
    Returns:
        Path to compose file, or None if not found
    """
    candidates = [
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
    ]
    
    for name in candidates:
        compose_path = project_dir / name
        if compose_path.exists():
            return compose_path
    
    return None


def run_compose_command(
    command: str,
    project_dir: Path,
    *args: str,
    detach: bool = False,
    build: bool = False,
    follow_logs: bool = False,
    env_vars: Optional[dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Run a docker compose command.
    
    Args:
        command: The compose command (up, down, logs, etc.)
        project_dir: Path to the project directory
        *args: Additional arguments
        detach: Run in detached mode (for 'up')
        build: Build images before starting (for 'up')
        follow_logs: Follow log output (for 'logs')
        env_vars: Additional environment variables
        
    Returns:
        CompletedProcess result
    """
    compose_cmd = get_compose_command()
    full_cmd = compose_cmd + [command]
    
    if command == "up":
        if detach:
            full_cmd.append("-d")
        if build:
            full_cmd.append("--build")
    elif command == "logs":
        if follow_logs:
            full_cmd.append("-f")
    
    full_cmd.extend(args)
    
    # Prepare environment
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    return subprocess.run(
        full_cmd,
        cwd=project_dir,
        env=env,
    )


def get_running_containers(project_dir: Path) -> list[dict]:
    """Get running containers for a compose project.
    
    Args:
        project_dir: Path to the project directory
        
    Returns:
        List of container info dicts
    """
    compose_cmd = get_compose_command()
    
    try:
        result = subprocess.run(
            compose_cmd + ["ps", "--format", "json"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode == 0 and result.stdout.strip():
            import json
            # Handle both single JSON object and JSON lines
            output = result.stdout.strip()
            if output.startswith("["):
                return json.loads(output)
            else:
                # JSON lines format
                return [json.loads(line) for line in output.split("\n") if line.strip()]
    except Exception:
        pass
    
    return []


def is_project_running(project_dir: Path) -> bool:
    """Check if a compose project has running containers.
    
    Args:
        project_dir: Path to the project directory
        
    Returns:
        True if any containers are running
    """
    containers = get_running_containers(project_dir)
    return len(containers) > 0


def inject_stargate_env(project_dir: Path) -> dict[str, str]:
    """Get Stargate environment variables to inject into containers.
    
    Args:
        project_dir: Path to the project directory
        
    Returns:
        Dict of environment variables
    """
    from traylinx.constants import get_settings
    
    settings = get_settings()
    
    env_vars = {
        "TRAYLINX_ENV": settings.env,
        "TRAYLINX_REGISTRY_URL": settings.effective_registry_url,
    }
    
    # Add credentials if available
    if settings.agent_key:
        env_vars["TRAYLINX_AGENT_KEY"] = settings.agent_key
    if settings.secret_token:
        env_vars["TRAYLINX_SECRET_TOKEN"] = settings.secret_token
    
    # Add NATS URL for Stargate
    nats_url = os.environ.get("NATS_URL", "nats://demo.nats.io:4222")
    env_vars["NATS_URL"] = nats_url
    
    # Add Stargate P2P identity variables if identity exists
    stargate_dir = Path.home() / ".traylinx" / "stargate"
    identity_key = stargate_dir / "identity.key"
    identity_cert = stargate_dir / "identity.cert"
    
    if identity_key.exists():
        # Load peer ID from identity
        try:
            from traylinx_stargate.identity import IdentityManager
            identity = IdentityManager(config_dir=stargate_dir)
            if identity.has_identity():
                env_vars["STARGATE_PEER_ID"] = identity.get_peer_id()
                env_vars["STARGATE_PUBLIC_KEY"] = identity.get_public_key_hex()
                env_vars["STARGATE_IDENTITY_DIR"] = str(stargate_dir)
                
                if identity.has_certificate():
                    env_vars["STARGATE_CERT_PATH"] = str(identity_cert)
        except ImportError:
            # traylinx-stargate not installed, use file-based detection
            env_vars["STARGATE_IDENTITY_DIR"] = str(stargate_dir)
            if identity_cert.exists():
                env_vars["STARGATE_CERT_PATH"] = str(identity_cert)
    
    return env_vars


def get_stargate_volume_mounts() -> list[dict]:
    """Get volume mount configurations for Stargate identity.
    
    Returns:
        List of volume mount dicts for docker-compose
    """
    stargate_dir = Path.home() / ".traylinx" / "stargate"
    
    # Ensure directory exists
    stargate_dir.mkdir(parents=True, exist_ok=True)
    
    return [
        {
            "source": str(stargate_dir),
            "target": "/root/.traylinx/stargate",
            "type": "bind",
            "read_only": True,
        }
    ]


def get_oci_labels(
    agent_name: str,
    agent_version: str = "1.0.0",
    agent_key: Optional[str] = None,
    capabilities: Optional[list[str]] = None,
) -> dict[str, str]:
    """Generate OCI-compliant labels for agent containers.
    
    Args:
        agent_name: Name of the agent
        agent_version: Version string
        agent_key: Registered agent key (optional)
        capabilities: List of agent capabilities
        
    Returns:
        Dict of OCI labels
    """
    import datetime
    
    labels = {
        # Standard OCI labels
        "org.opencontainers.image.title": agent_name,
        "org.opencontainers.image.version": agent_version,
        "org.opencontainers.image.created": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        "org.opencontainers.image.vendor": "Traylinx",
        
        # Traylinx-specific labels
        "org.traylinx.agent.name": agent_name,
        "org.traylinx.agent.version": agent_version,
        "org.traylinx.agent.protocol": "stargate",
    }
    
    if agent_key:
        labels["org.traylinx.agent.key"] = agent_key
    
    if capabilities:
        labels["org.traylinx.agent.capabilities"] = ",".join(capabilities)
    
    # Add peer ID if available
    stargate_dir = Path.home() / ".traylinx" / "stargate"
    try:
        from traylinx_stargate.identity import IdentityManager
        identity = IdentityManager(config_dir=stargate_dir)
        if identity.has_identity():
            labels["org.traylinx.agent.peer_id"] = identity.get_peer_id()
    except (ImportError, FileNotFoundError):
        pass
    
    return labels


def format_docker_labels(labels: dict[str, str]) -> list[str]:
    """Format labels as Docker build arguments.
    
    Args:
        labels: Dict of label key-value pairs
        
    Returns:
        List of --label arguments for docker build
    """
    args = []
    for key, value in labels.items():
        args.extend(["--label", f"{key}={value}"])
    return args
