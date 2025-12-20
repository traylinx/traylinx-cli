"""Registry utilities for Traylinx CLI.

This module provides GHCR (GitHub Container Registry) integration
for publishing and pulling Docker images.
"""

import logging
import os
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class AgentManifest:
    """Agent metadata extracted from pyproject.toml or manifest file."""
    
    name: str
    version: str
    description: str
    author: Optional[str] = None
    license: Optional[str] = None
    
    @property
    def image_name(self) -> str:
        """Generate Docker image name from agent name."""
        # Convert to lowercase, replace underscores with dashes
        return self.name.lower().replace("_", "-").replace(" ", "-")
    
    @property
    def full_image_tag(self) -> str:
        """Generate full image tag with version."""
        return f"ghcr.io/traylinx/{self.image_name}:{self.version}"
    
    @property
    def latest_image_tag(self) -> str:
        """Generate latest image tag."""
        return f"ghcr.io/traylinx/{self.image_name}:latest"


def load_manifest(project_dir: Path) -> Optional[AgentManifest]:
    """Load agent manifest from project directory.
    
    Attempts to load from:
    1. traylinx-agent.yaml (if exists)
    2. pyproject.toml (Poetry metadata)
    
    Args:
        project_dir: Path to the project root
        
    Returns:
        AgentManifest or None if not found
    """
    # Try traylinx-agent.yaml first
    manifest_file = project_dir / "traylinx-agent.yaml"
    if manifest_file.exists():
        try:
            import yaml
            with open(manifest_file) as f:
                data = yaml.safe_load(f)
            return AgentManifest(
                name=data.get("name", "unnamed-agent"),
                version=data.get("version", "0.0.1"),
                description=data.get("description", ""),
                author=data.get("author"),
                license=data.get("license"),
            )
        except Exception as e:
            logger.debug(f"Failed to load traylinx-agent.yaml: {e}")
    
    # Fallback to pyproject.toml
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        try:
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            
            poetry = data.get("tool", {}).get("poetry", {})
            if poetry:
                authors = poetry.get("authors", [])
                author = authors[0] if authors else None
                
                return AgentManifest(
                    name=poetry.get("name", "unnamed-agent"),
                    version=poetry.get("version", "0.0.1"),
                    description=poetry.get("description", ""),
                    author=author,
                    license=poetry.get("license"),
                )
        except Exception as e:
            logger.debug(f"Failed to load pyproject.toml: {e}")
    
    return None


def check_buildx() -> bool:
    """Check if Docker Buildx is available for multi-arch builds."""
    try:
        result = subprocess.run(
            ["docker", "buildx", "version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_ghcr_auth() -> bool:
    """Check if user is authenticated to GHCR."""
    try:
        result = subprocess.run(
            ["docker", "login", "ghcr.io", "--get-login"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def login_ghcr(token: str, username: str = "oauth2accesstoken") -> bool:
    """Login to GHCR using a token.
    
    Args:
        token: GitHub Personal Access Token or GITHUB_TOKEN
        username: Username (default for token auth)
        
    Returns:
        True if login successful
    """
    try:
        result = subprocess.run(
            ["docker", "login", "ghcr.io", "-u", username, "--password-stdin"],
            input=token,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def build_multiarch_image(
    project_dir: Path,
    image_tag: str,
    platforms: list[str] | None = None,
    push: bool = True,
    dockerfile: str = "Dockerfile",
    latest_tag: str | None = None,
) -> subprocess.CompletedProcess:
    """Build multi-architecture Docker image using buildx.
    
    Args:
        project_dir: Path to project with Dockerfile
        image_tag: Full image tag (e.g., ghcr.io/traylinx/my-agent:1.0.0)
        platforms: Target platforms
        push: Push to registry after build
        dockerfile: Dockerfile path
        
    Returns:
        CompletedProcess result
    """
    if platforms is None:
        platforms = ["linux/amd64", "linux/arm64"]
    
    cmd = [
        "docker", "buildx", "build",
        "--platform", ",".join(platforms),
        "-t", image_tag,
        "-f", dockerfile,
    ]
    
    # Add latest tag if specified
    if latest_tag:
        cmd.extend(["-t", latest_tag])
    
    if push:
        cmd.append("--push")
    
    cmd.append(".")
    
    return subprocess.run(
        cmd,
        cwd=project_dir,
    )


def build_image(
    project_dir: Path,
    image_tag: str,
    dockerfile: str = "Dockerfile",
) -> subprocess.CompletedProcess:
    """Build Docker image for current platform only.
    
    Args:
        project_dir: Path to project with Dockerfile
        image_tag: Full image tag
        dockerfile: Dockerfile path
        
    Returns:
        CompletedProcess result
    """
    return subprocess.run(
        [
            "docker", "build",
            "-t", image_tag,
            "-f", dockerfile,
            ".",
        ],
        cwd=project_dir,
    )


def push_image(image_tag: str) -> subprocess.CompletedProcess:
    """Push Docker image to registry.
    
    Args:
        image_tag: Full image tag
        
    Returns:
        CompletedProcess result
    """
    return subprocess.run(["docker", "push", image_tag])


def pull_image(image_tag: str) -> subprocess.CompletedProcess:
    """Pull Docker image from registry.
    
    Args:
        image_tag: Full image tag
        
    Returns:
        CompletedProcess result
    """
    return subprocess.run(["docker", "pull", image_tag])


def generate_compose_file(
    agent_name: str,
    image_tag: str,
    output_dir: Path,
    port: int = 8000,
) -> Path:
    """Generate a docker-compose.yml for running a pulled agent.
    
    Args:
        agent_name: Name of the agent
        image_tag: Full image tag
        output_dir: Directory to write compose file
        port: Port to expose
        
    Returns:
        Path to generated compose file
    """
    compose_content = f"""# Auto-generated by traylinx pull
# Agent: {agent_name}

services:
  {agent_name}:
    image: {image_tag}
    container_name: {agent_name}
    ports:
      - "{port}:8000"
    environment:
      - LOG_LEVEL=INFO
      - NATS_URL=${{NATS_URL:-nats://demo.nats.io:4222}}
    volumes:
      - ~/.traylinx:/app/.traylinx:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  # Optional: Redis for caching
  redis:
    image: redis:7-alpine
    container_name: {agent_name}-redis
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
"""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    compose_path = output_dir / "docker-compose.yml"
    compose_path.write_text(compose_content)
    
    return compose_path


def get_agent_directory(agent_name: str) -> Path:
    """Get the local directory for a pulled agent.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Path to agent directory in ~/.traylinx/agents/
    """
    traylinx_dir = Path.home() / ".traylinx" / "agents" / agent_name
    return traylinx_dir
