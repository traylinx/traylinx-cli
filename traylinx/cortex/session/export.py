"""History export utilities.

Exports session history in various formats:
- Plain text
- JSON
- Markdown
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from traylinx.cortex.types import Session, Message


class HistoryExporter:
    """Exports session history to various formats."""

    def __init__(self, session: Session | None = None):
        """Initialize exporter.

        Args:
            session: Session to export (can be set later)
        """
        self._session = session

    def set_session(self, session: Session) -> None:
        """Set session to export.

        Args:
            session: Session to export
        """
        self._session = session

    def to_json(self, pretty: bool = True) -> str:
        """Export to JSON format.

        Args:
            pretty: Whether to format with indentation

        Returns:
            JSON string
        """
        if not self._session:
            return "{}"

        data = {
            "session_id": self._session.id,
            "workspace": self._session.workspace,
            "created_at": self._session.created_at,
            "message_count": len(self._session.messages),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp if hasattr(msg, "timestamp") else None,
                }
                for msg in self._session.messages
            ],
        }

        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)

    def to_markdown(self) -> str:
        """Export to Markdown format.

        Returns:
            Markdown string
        """
        if not self._session:
            return "# Empty Session"

        lines = [
            f"# Session: {self._session.id}",
            "",
            f"**Workspace:** {self._session.workspace}",
            f"**Messages:** {len(self._session.messages)}",
            "",
            "---",
            "",
        ]

        for msg in self._session.messages:
            role_icon = "🧑" if msg.role == "user" else "🤖"
            lines.append(f"### {role_icon} {msg.role.title()}")
            lines.append("")
            lines.append(msg.content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def to_text(self) -> str:
        """Export to plain text format.

        Returns:
            Plain text string
        """
        if not self._session:
            return "Empty session"

        lines = [
            f"Session: {self._session.id}",
            f"Workspace: {self._session.workspace}",
            f"Messages: {len(self._session.messages)}",
            "=" * 50,
            "",
        ]

        for msg in self._session.messages:
            prefix = "You:" if msg.role == "user" else "Cortex:"
            lines.append(f"{prefix}")
            lines.append(msg.content)
            lines.append("")
            lines.append("-" * 30)
            lines.append("")

        return "\n".join(lines)

    def save(
        self,
        path: Path | str,
        format: str = "json",
    ) -> bool:
        """Save export to file.

        Args:
            path: Output file path
            format: Export format ('json', 'md', 'txt')

        Returns:
            True if successful
        """
        path = Path(path)

        if format == "json":
            content = self.to_json()
        elif format in ("md", "markdown"):
            content = self.to_markdown()
        else:
            content = self.to_text()

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            return True
        except Exception:
            return False


def export_session(
    session: Session,
    output_path: Path | str | None = None,
    format: str = "json",
) -> str:
    """Export a session to a file or string.

    Args:
        session: Session to export
        output_path: Optional output file path
        format: Export format ('json', 'md', 'txt')

    Returns:
        Export content as string
    """
    exporter = HistoryExporter(session)

    if format == "json":
        content = exporter.to_json()
    elif format in ("md", "markdown"):
        content = exporter.to_markdown()
    else:
        content = exporter.to_text()

    if output_path:
        exporter.save(output_path, format)

    return content
