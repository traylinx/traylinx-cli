"""Configuration hot-reload support.

Watches config files for changes and reloads automatically:
- File watcher using stat polling
- Config validation on reload
- Callback notification for changes
"""

import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from traylinx.cortex.config import CortexConfig, load_config


@dataclass
class WatchedFile:
    """A file being watched for changes."""

    path: Path
    last_modified: float = 0.0
    last_size: int = 0


class ConfigWatcher:
    """Watches config files and triggers reload on change.

    Uses stat-based polling (cross-platform, no dependencies).
    """

    def __init__(
        self,
        config_path: Path | str,
        poll_interval: float = 2.0,
        on_reload: Callable[[CortexConfig], None] | None = None,
    ):
        """Initialize watcher.

        Args:
            config_path: Path to config file
            poll_interval: Seconds between checks (default: 2s)
            on_reload: Callback when config is reloaded
        """
        self._path = Path(config_path)
        self._interval = poll_interval
        self._on_reload = on_reload
        self._watched = WatchedFile(path=self._path)
        self._running = False
        self._thread: threading.Thread | None = None
        self._config: CortexConfig | None = None

        # Initialize last modified time
        self._update_file_stats()

    def _update_file_stats(self) -> bool:
        """Update file stats and check for changes.

        Returns:
            True if file changed
        """
        try:
            stat = self._path.stat()
            mtime = stat.st_mtime
            size = stat.st_size

            changed = (
                mtime != self._watched.last_modified
                or size != self._watched.last_size
            )

            self._watched.last_modified = mtime
            self._watched.last_size = size

            return changed
        except FileNotFoundError:
            return False

    def _reload_config(self) -> bool:
        """Reload configuration.

        Returns:
            True if reload succeeded
        """
        try:
            self._config = load_config()

            if self._on_reload:
                self._on_reload(self._config)

            return True
        except Exception:
            return False

    def _watch_loop(self) -> None:
        """Main watch loop."""
        while self._running:
            if self._update_file_stats():
                self._reload_config()

            time.sleep(self._interval)

    def start(self) -> None:
        """Start watching for changes."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop watching."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self._interval * 2)
            self._thread = None

    @property
    def config(self) -> CortexConfig | None:
        """Get current config."""
        return self._config

    def force_reload(self) -> bool:
        """Force an immediate reload.

        Returns:
            True if reload succeeded
        """
        return self._reload_config()


class HotReloadableConfig:
    """A configuration that automatically reloads on file changes.

    Usage:
        config = HotReloadableConfig()
        config.start()
        # Config will now auto-update when file changes
        print(config.use_llm)  # Always returns current value
    """

    def __init__(
        self,
        config_path: Path | str | None = None,
        poll_interval: float = 2.0,
    ):
        """Initialize hot-reloadable config.

        Args:
            config_path: Path to config file (uses default if not provided)
            poll_interval: Seconds between checks
        """
        if config_path is None:
            config_path = Path.home() / ".traylinx" / "cortex" / "config.yaml"

        self._watcher = ConfigWatcher(
            config_path=config_path,
            poll_interval=poll_interval,
            on_reload=self._on_config_change,
        )
        self._config = load_config()
        self._change_callbacks: list[Callable[[CortexConfig], None]] = []

    def _on_config_change(self, new_config: CortexConfig) -> None:
        """Handle config change.

        Args:
            new_config: New configuration
        """
        self._config = new_config
        for callback in self._change_callbacks:
            try:
                callback(new_config)
            except Exception:
                pass  # Don't let callback errors break the watcher

    def on_change(self, callback: Callable[[CortexConfig], None]) -> None:
        """Register a callback for config changes.

        Args:
            callback: Function to call when config changes
        """
        self._change_callbacks.append(callback)

    def start(self) -> None:
        """Start watching for changes."""
        self._watcher.start()

    def stop(self) -> None:
        """Stop watching."""
        self._watcher.stop()

    def reload(self) -> None:
        """Force reload config."""
        self._watcher.force_reload()

    # Proxy common config properties
    @property
    def use_llm(self) -> bool:
        """Whether to use LLM for classification."""
        return self._config.intent_classification.use_llm

    @property
    def confidence_threshold(self) -> float:
        """Confidence threshold for classification."""
        return self._config.intent_classification.confidence_threshold

    @property
    def switchai_url(self) -> str:
        """SwitchAI base URL."""
        return self._config.switchai.base_url

    @property
    def raw(self) -> CortexConfig:
        """Get the raw config object."""
        return self._config
