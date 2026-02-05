"""Configuration management for Traylinx Cortex.

Uses StateBox from traylinx-cli for consistent state management.
Configuration is stored at ~/.traylinx/state/cortex.json.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SwitchAIConfig(BaseModel):
    """SwitchAILocal connection settings."""

    base_url: str = Field(default="http://localhost:18080/v1")
    default_model: str = Field(default="auto")
    timeout: int = Field(default=30)
    api_key: str = Field(default="sk-test-123")  # Default API key for local instance


class IntentConfig(BaseModel):
    """Intent classification settings."""

    model: str = Field(default="ollama:qwen:0.5b")
    confidence_threshold: float = Field(default=0.7)
    use_llm: bool = Field(default=True)


class ExecutionConfig(BaseModel):
    """Command execution settings."""

    require_confirmation: list[str] = Field(
        default_factory=lambda: ["publish", "delete", "destroy"]
    )
    show_commands: bool = Field(default=True)
    timeout: int = Field(default=300)


class CortexConfig(BaseModel):
    """Complete Cortex configuration."""

    # Core settings (shared with existing cortex_cmd.py)
    url: str | None = Field(default=None)
    token: str | None = Field(default=None)
    enabled: bool = Field(default=False)

    # Cortex-specific settings
    switchai: SwitchAIConfig = Field(default_factory=SwitchAIConfig)
    intent_classification: IntentConfig = Field(default_factory=IntentConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)


def get_state_dir() -> Path:
    """Get the state directory, using StateBox if available."""
    try:
        from traylinx.utils.statebox import StateBox

        return StateBox.root()
    except ImportError:
        # Fallback for standalone usage
        return Path.home() / ".traylinx"


def get_config_path() -> Path:
    """Get path to Cortex configuration file."""
    return get_state_dir() / "cortex.json"


def get_cortex_dir() -> Path:
    """Get path to Cortex workspace directory."""
    return get_state_dir() / "cortex"


def load_config() -> CortexConfig:
    """Load Cortex configuration from disk.

    Returns:
        CortexConfig with values from disk or defaults
    """
    config_path = get_config_path()
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text())
            return CortexConfig.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            # Invalid config, return defaults
            pass
    return CortexConfig()


def save_config(config: CortexConfig) -> None:
    """Save Cortex configuration to disk.

    Uses secure_write if available, otherwise atomic write pattern.
    """
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    try:
        from traylinx.utils.secure_write import secure_write_json

        secure_write_json(config_path, config.model_dump())
    except ImportError:
        # Fallback: atomic write
        temp_path = config_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(config.model_dump(), indent=2))
        temp_path.rename(config_path)


def update_config(**kwargs: Any) -> CortexConfig:
    """Update specific configuration values.

    Args:
        **kwargs: Configuration values to update

    Returns:
        Updated configuration
    """
    config = load_config()
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    save_config(config)
    return config


def ensure_cortex_dir() -> Path:
    """Ensure Cortex workspace directory exists.

    Creates:
        ~/.traylinx/cortex/
        ~/.traylinx/cortex/sessions/

    Returns:
        Path to cortex directory
    """
    cortex_dir = get_cortex_dir()
    cortex_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    (cortex_dir / "sessions").mkdir(exist_ok=True, mode=0o700)
    return cortex_dir
