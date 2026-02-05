"""SQLite-based session storage.

Stores sessions, messages, and command executions in SQLite.
Also maintains JSONL transcripts for OpenClaw compatibility.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from traylinx.cortex.types import (
    Session,
    Message,
    MessageRole,
    CommandExecution,
    ExecutionStatus,
    Context,
)
from traylinx.cortex.config import get_cortex_dir, ensure_cortex_dir


def get_db_path() -> Path:
    """Get path to sessions database."""
    return get_cortex_dir() / "sessions.db"


def get_sessions_dir() -> Path:
    """Get path to session transcripts directory."""
    return get_cortex_dir() / "sessions"


class SessionStorage:
    """SQLite storage for sessions and messages.

    Tables:
    - sessions: id, user_id, started_at, last_active, context (JSON)
    - messages: id, session_id, role, content, timestamp, metadata (JSON)
    - command_executions: id, session_id, command, parameters, result, status, timestamp, duration_ms
    """

    def __init__(self, db_path: Path | None = None):
        """Initialize storage.

        Args:
            db_path: Path to SQLite database (default from config)
        """
        ensure_cortex_dir()
        self.db_path = db_path or get_db_path()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL DEFAULT 'default',
                    started_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    context TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS command_executions (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    command TEXT NOT NULL,
                    parameters TEXT NOT NULL DEFAULT '{}',
                    result TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    stdout TEXT NOT NULL DEFAULT '',
                    stderr TEXT NOT NULL DEFAULT '',
                    exit_code INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
                CREATE INDEX IF NOT EXISTS idx_executions_session ON command_executions(session_id);
            """)

    def create_session(self, user_id: str = "default") -> Session:
        """Create a new session.

        Args:
            user_id: User identifier

        Returns:
            New Session instance
        """
        session = Session(
            id=uuid4(),
            user_id=user_id,
            started_at=datetime.now(),
            last_active=datetime.now(),
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO sessions (id, user_id, started_at, last_active, context)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(session.id),
                    session.user_id,
                    session.started_at.isoformat(),
                    session.last_active.isoformat(),
                    json.dumps(session.context.model_dump()),
                ),
            )

        return session

    def get_session(self, session_id: UUID) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: Session UUID

        Returns:
            Session if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (str(session_id),),
            ).fetchone()

            if not row:
                return None

            # Load messages
            messages = self._load_messages(conn, session_id)

            # Load command executions
            executions = self._load_executions(conn, session_id)

            return Session(
                id=UUID(row["id"]),
                user_id=row["user_id"],
                started_at=datetime.fromisoformat(row["started_at"]),
                last_active=datetime.fromisoformat(row["last_active"]),
                context=Context.model_validate(json.loads(row["context"])),
                conversation_history=messages,
                command_history=executions,
            )

    def _load_messages(self, conn: sqlite3.Connection, session_id: UUID) -> list[Message]:
        """Load messages for a session."""
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp",
            (str(session_id),),
        ).fetchall()

        return [
            Message(
                id=UUID(row["id"]),
                role=MessageRole(row["role"]),
                content=row["content"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                metadata=json.loads(row["metadata"]),
            )
            for row in rows
        ]

    def _load_executions(self, conn: sqlite3.Connection, session_id: UUID) -> list[CommandExecution]:
        """Load command executions for a session."""
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM command_executions WHERE session_id = ? ORDER BY timestamp",
            (str(session_id),),
        ).fetchall()

        return [
            CommandExecution(
                id=UUID(row["id"]),
                command=row["command"],
                parameters=json.loads(row["parameters"]),
                result=json.loads(row["result"]),
                status=ExecutionStatus(row["status"]),
                timestamp=datetime.fromisoformat(row["timestamp"]),
                duration_ms=row["duration_ms"],
                stdout=row["stdout"],
                stderr=row["stderr"],
                exit_code=row["exit_code"],
            )
            for row in rows
        ]

    def add_message(self, session_id: UUID, role: MessageRole, content: str, metadata: dict | None = None) -> Message:
        """Add a message to a session.

        Args:
            session_id: Session UUID
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata

        Returns:
            Created Message
        """
        message = Message(
            id=uuid4(),
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO messages (id, session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(message.id),
                    str(session_id),
                    message.role.value,
                    message.content,
                    message.timestamp.isoformat(),
                    json.dumps(message.metadata),
                ),
            )

            # Update last_active
            conn.execute(
                "UPDATE sessions SET last_active = ? WHERE id = ?",
                (datetime.now().isoformat(), str(session_id)),
            )

        # Append to JSONL transcript
        self._append_transcript(session_id, message)

        return message

    def add_execution(self, session_id: UUID, execution: CommandExecution) -> None:
        """Add a command execution record.

        Args:
            session_id: Session UUID
            execution: CommandExecution to record
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO command_executions
                (id, session_id, command, parameters, result, status, timestamp, duration_ms, stdout, stderr, exit_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(execution.id),
                    str(session_id),
                    execution.command,
                    json.dumps(execution.parameters),
                    json.dumps(execution.result),
                    execution.status.value,
                    execution.timestamp.isoformat(),
                    execution.duration_ms,
                    execution.stdout,
                    execution.stderr,
                    execution.exit_code,
                ),
            )

    def _append_transcript(self, session_id: UUID, message: Message) -> None:
        """Append message to JSONL transcript (OpenClaw pattern)."""
        sessions_dir = get_sessions_dir()
        sessions_dir.mkdir(parents=True, exist_ok=True)

        transcript_path = sessions_dir / f"{session_id}.jsonl"
        with open(transcript_path, "a") as f:
            f.write(json.dumps({
                "role": message.role.value,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "metadata": message.metadata,
            }) + "\n")

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent sessions.

        Args:
            limit: Maximum number of sessions

        Returns:
            List of session summaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT s.id, s.user_id, s.started_at, s.last_active,
                       COUNT(m.id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                GROUP BY s.id
                ORDER BY s.last_active DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            return [
                {
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "started_at": row["started_at"],
                    "last_active": row["last_active"],
                    "message_count": row["message_count"],
                }
                for row in rows
            ]

    def update_context(self, session_id: UUID, context: Context) -> None:
        """Update session context.

        Args:
            session_id: Session UUID
            context: Updated context
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET context = ?, last_active = ? WHERE id = ?",
                (json.dumps(context.model_dump()), datetime.now().isoformat(), str(session_id)),
            )
