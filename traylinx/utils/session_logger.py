"""Session Logger - High-fidelity interaction tracing for Traylinx CLI.

This module provides comprehensive logging of all agent interactions,
tool calls, and LLM conversations with rich metadata for debugging,
auditing, and replay.
"""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4


class SessionLogger:
    """High-fidelity logger for agent interactions.

    Saves detailed JSON logs of all interactions to ~/.traylinx/sessions/
    with Git context, environment metadata, and full tool traces.
    """

    SESSIONS_DIR = Path.home() / ".traylinx" / "sessions"

    def __init__(self, session_name: Optional[str] = None):
        """Initialize a new session.

        Args:
            session_name: Optional name for the session (defaults to timestamp)
        """
        self.session_id = uuid4().hex[:12]
        self.session_name = session_name or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.messages: list[dict] = []
        self.tool_calls: list[dict] = []
        self.metadata = self._capture_metadata()

        # Ensure sessions directory exists
        self.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    def _capture_metadata(self) -> dict:
        """Capture environment and Git metadata."""
        metadata = {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "started_at": self.start_time,
            "cwd": os.getcwd(),
            "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
            "hostname": os.environ.get("HOSTNAME", "unknown"),
            "cli_version": self._get_cli_version(),
        }

        # Git metadata (if in a git repo)
        git_info = self._get_git_info()
        if git_info:
            metadata["git"] = git_info

        # Stargate identity (if available)
        stargate_info = self._get_stargate_info()
        if stargate_info:
            metadata["stargate"] = stargate_info

        # Cortex connection (if enabled)
        cortex_info = self._get_cortex_info()
        if cortex_info:
            metadata["cortex"] = cortex_info

        return metadata

    def _get_cli_version(self) -> str:
        """Get the CLI version."""
        try:
            from traylinx import __version__

            return __version__
        except ImportError:
            return "unknown"

    def _get_git_info(self) -> Optional[dict]:
        """Get Git repository information."""
        try:
            # Check if we're in a git repo
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None

            # Get commit hash
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()

            # Get branch name
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()

            # Check for uncommitted changes
            dirty = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()

            return {
                "commit": commit[:12] if commit else None,
                "branch": branch if branch else None,
                "dirty": bool(dirty),
            }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _get_stargate_info(self) -> Optional[dict]:
        """Get Stargate identity information."""
        try:
            from traylinx_stargate.identity import IdentityManager

            identity = IdentityManager()
            if identity.has_identity():
                return {
                    "peer_id": identity.get_peer_id(),
                    "certified": identity.has_certificate(),
                }
        except ImportError:
            pass
        return None

    def _get_cortex_info(self) -> Optional[dict]:
        """Get Cortex connection information."""
        try:
            from traylinx.commands.cortex_cmd import load_cortex_config

            config = load_cortex_config()
            if config.get("url"):
                return {
                    "url": config["url"],
                    "enabled": config.get("enabled", False),
                }
        except ImportError:
            pass
        return None

    def log_message(
        self,
        role: str,
        content: str,
        model: Optional[str] = None,
        tokens: Optional[int] = None,
    ):
        """Log a chat message.

        Args:
            role: 'user', 'assistant', or 'system'
            content: Message content
            model: Optional model identifier
            tokens: Optional token count
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "role": role,
            "content": content,
        }
        if model:
            entry["model"] = model
        if tokens:
            entry["tokens"] = tokens

        self.messages.append(entry)

    def log_tool_call(
        self,
        tool_name: str,
        input_data: Any,
        output_data: Any = None,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
    ):
        """Log a tool invocation.

        Args:
            tool_name: Name of the tool
            input_data: Input parameters
            output_data: Tool output (if successful)
            duration_ms: Execution time in milliseconds
            error: Error message (if failed)
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "tool": tool_name,
            "input": input_data,
        }
        if output_data is not None:
            entry["output"] = output_data
        if duration_ms is not None:
            entry["duration_ms"] = duration_ms
        if error:
            entry["error"] = error

        self.tool_calls.append(entry)

    def save(self):
        """Save the session to disk."""
        session_file = self.SESSIONS_DIR / f"{self.session_name}_{self.session_id}.json"

        session_data = {
            "metadata": self.metadata,
            "messages": self.messages,
            "tool_calls": self.tool_calls,
            "ended_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        session_file.write_text(json.dumps(session_data, indent=2))
        return session_file

    @classmethod
    def list_sessions(cls, limit: int = 20) -> list[dict]:
        """List recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session metadata dicts
        """
        if not cls.SESSIONS_DIR.exists():
            return []

        sessions = []
        for path in sorted(cls.SESSIONS_DIR.glob("*.json"), reverse=True)[:limit]:
            try:
                data = json.loads(path.read_text())
                sessions.append({
                    "file": path.name,
                    "session_id": data.get("metadata", {}).get("session_id", ""),
                    "started_at": data.get("metadata", {}).get("started_at", ""),
                    "message_count": len(data.get("messages", [])),
                    "tool_count": len(data.get("tool_calls", [])),
                })
            except (json.JSONDecodeError, KeyError):
                continue

        return sessions

    @classmethod
    def load_session(cls, session_id: str) -> Optional[dict]:
        """Load a session by ID.

        Args:
            session_id: Session ID (partial match supported)

        Returns:
            Session data dict, or None if not found
        """
        if not cls.SESSIONS_DIR.exists():
            return None

        for path in cls.SESSIONS_DIR.glob("*.json"):
            if session_id in path.name:
                try:
                    return json.loads(path.read_text())
                except json.JSONDecodeError:
                    return None

        return None


# Global session for CLI use
_current_session: Optional[SessionLogger] = None


def get_session() -> Optional[SessionLogger]:
    """Get the current session logger."""
    return _current_session


def start_session(name: Optional[str] = None) -> SessionLogger:
    """Start a new session and set it as current."""
    global _current_session
    _current_session = SessionLogger(session_name=name)
    return _current_session


def end_session() -> Optional[Path]:
    """End the current session and save it."""
    global _current_session
    if _current_session:
        path = _current_session.save()
        _current_session = None
        return path
    return None
