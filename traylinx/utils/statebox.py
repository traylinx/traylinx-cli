"""
State Box: Centralized path resolution and secure state management.

The State Box pattern ensures all mutable CLI data lives in a single,
configurable directory (~/.traylinx by default) with support for:

- Environment variable override (TRAYLINX_STATE_DIR)
- Read-only mode for immutable environments (TRAYLINX_READONLY=1)
- Consistent path resolution across all modules

Directory Structure:
    ~/.traylinx/
    ├── credentials.json      # OAuth tokens
    ├── context.json          # Org/project context cache
    ├── config.yaml           # User configuration
    ├── cortex.json           # Cortex settings
    ├── mcp-servers.json      # MCP server registry
    ├── skills/               # Global skills
    ├── agents/               # Installed agents
    ├── stargate/             # P2P identity & keys
    ├── sessions/             # Session logs
    ├── credentials/          # Provider API keys
    └── cache/                # Ephemeral cache
"""

import os
from pathlib import Path


class StateBox:
    """
    Manages the ~/.traylinx state directory.

    All path resolution goes through this class to ensure consistency
    and support for TRAYLINX_STATE_DIR override.
    """

    _root: Path | None = None

    @classmethod
    def root(cls) -> Path:
        """
        Get state box root directory.

        Resolution order:
        1. TRAYLINX_STATE_DIR environment variable
        2. Default: ~/.traylinx

        Returns:
            Path to state box root directory
        """
        if cls._root is None:
            env_dir = os.environ.get("TRAYLINX_STATE_DIR")
            if env_dir:
                cls._root = Path(env_dir).expanduser().resolve()
            else:
                cls._root = Path.home() / ".traylinx"
        return cls._root

    @classmethod
    def reset(cls) -> None:
        """Reset cached root (for testing)."""
        cls._root = None

    @classmethod
    def is_read_only(cls) -> bool:
        """
        Check if running in read-only mode.

        Set TRAYLINX_READONLY=1 for NixOS/immutable environments.
        """
        return os.environ.get("TRAYLINX_READONLY", "0") == "1"

    @classmethod
    def ensure_dir(cls, path: Path) -> Path:
        """
        Ensure directory exists with secure permissions (0700).

        Args:
            path: Directory path to create

        Returns:
            The path (for chaining)

        Raises:
            ReadOnlyError: If in read-only mode
        """
        if cls.is_read_only():
            from traylinx.utils.secure_write import ReadOnlyError

            raise ReadOnlyError("Cannot create directory in read-only mode")

        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o700)
        return path

    # =========================================================================
    # File Accessors
    # =========================================================================

    @classmethod
    def credentials_file(cls) -> Path:
        """OAuth credentials file (~/.traylinx/credentials.json)."""
        return cls.root() / "credentials.json"

    @classmethod
    def context_file(cls) -> Path:
        """Organization/project context cache (~/.traylinx/context.json)."""
        return cls.root() / "context.json"

    @classmethod
    def config_file(cls) -> Path:
        """User configuration file (~/.traylinx/config.yaml)."""
        return cls.root() / "config.yaml"

    @classmethod
    def mcp_config_file(cls) -> Path:
        """MCP server registry (~/.traylinx/mcp-servers.json)."""
        return cls.root() / "mcp-servers.json"

    @classmethod
    def cortex_config_file(cls) -> Path:
        """Cortex configuration (~/.traylinx/cortex.json)."""
        return cls.root() / "cortex.json"

    # =========================================================================
    # Directory Accessors
    # =========================================================================

    @classmethod
    def skills_dir(cls) -> Path:
        """Global skills directory (~/.traylinx/skills/)."""
        return cls.root() / "skills"

    @classmethod
    def agents_dir(cls) -> Path:
        """Installed agents directory (~/.traylinx/agents/)."""
        return cls.root() / "agents"

    @classmethod
    def stargate_dir(cls) -> Path:
        """Stargate P2P identity directory (~/.traylinx/stargate/)."""
        return cls.root() / "stargate"

    @classmethod
    def sessions_dir(cls) -> Path:
        """Session logs directory (~/.traylinx/sessions/)."""
        return cls.root() / "sessions"

    @classmethod
    def credentials_dir(cls) -> Path:
        """Provider credentials directory (~/.traylinx/credentials/)."""
        return cls.root() / "credentials"

    @classmethod
    def cache_dir(cls) -> Path:
        """Ephemeral cache directory (~/.traylinx/cache/)."""
        return cls.root() / "cache"

    @classmethod
    def api_keys_dir(cls) -> Path:
        """API keys storage directory (~/.traylinx/credentials/api-keys/)."""
        return cls.credentials_dir() / "api-keys"

    # =========================================================================
    # Utility Methods
    # =========================================================================

    @classmethod
    def resolve(cls, relative_path: str) -> Path:
        """
        Resolve a relative path within the state box.

        Args:
            relative_path: Path relative to state box root

        Returns:
            Absolute path
        """
        return cls.root() / relative_path

    @classmethod
    def status(cls) -> dict:
        """
        Get state box status for diagnostics.

        Returns:
            Dict with root path, read-only mode, and directory existence
        """
        root = cls.root()
        return {
            "root_path": str(root),
            "read_only": cls.is_read_only(),
            "exists": root.exists(),
            "credentials_file": cls.credentials_file().exists(),
            "context_file": cls.context_file().exists(),
            "config_file": cls.config_file().exists(),
            "skills_dir": cls.skills_dir().exists(),
        }
