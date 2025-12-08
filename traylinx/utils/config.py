"""Configuration management for Traylinx CLI."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class ConfigError(Exception):
    """Configuration error."""
    pass


class Credentials(BaseModel):
    """API credentials."""
    
    agent_key: str = Field(..., min_length=1)
    secret_token: str = Field(..., min_length=1)


class Config(BaseModel):
    """Traylinx CLI configuration."""
    
    registry_url: str = Field(
        default="https://api.traylinx.com",
        description="Agent Registry base URL",
    )
    credentials: Credentials
    
    # Optional settings
    default_template: str = Field(default="basic")
    author_name: Optional[str] = None
    author_email: Optional[str] = None


def get_config_path() -> Path:
    """Get path to config file."""
    return Path.home() / ".traylinx" / "config.yaml"


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from file.
    
    Searches for config in:
    1. Provided path
    2. ./traylinx.yaml (project-local)
    3. ~/.traylinx/config.yaml (global)
    
    Raises:
        ConfigError: If no config found or invalid.
    """
    search_paths = []
    
    if config_path:
        search_paths.append(config_path)
    
    # Project-local config
    search_paths.append(Path("traylinx.yaml"))
    
    # Global config
    search_paths.append(get_config_path())
    
    # Find first existing config
    for path in search_paths:
        if path.exists():
            try:
                with open(path) as f:
                    data = yaml.safe_load(f)
                return Config.model_validate(data)
            except yaml.YAMLError as e:
                raise ConfigError(f"Invalid YAML in {path}: {e}")
            except Exception as e:
                raise ConfigError(f"Invalid config in {path}: {e}")
    
    # No config found
    raise ConfigError(
        "No configuration found.\n\n"
        "Create ~/.traylinx/config.yaml with:\n\n"
        "registry_url: https://api.traylinx.com\n"
        "credentials:\n"
        "  agent_key: your-agent-key\n"
        "  secret_token: your-secret-token\n"
    )


def save_config(config: Config, config_path: Optional[Path] = None) -> Path:
    """Save configuration to file."""
    path = config_path or get_config_path()
    
    # Create directory if needed
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save config
    with open(path, "w") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False)
    
    return path
