"""Session manager for Traylinx Cortex.

High-level interface for session lifecycle management.
Handles session creation, retrieval, and context building.
"""

import os
from datetime import datetime
from typing import Any
from uuid import UUID

from traylinx.cortex.types import Session, Message, MessageRole, Context, CommandExecution, ExecutionStatus
from traylinx.cortex.session.storage import SessionStorage
from traylinx.cortex.workspace import ensure_workspace


class SessionManager:
    """Manages conversation sessions.

    Provides high-level methods for:
    - Creating and retrieving sessions
    - Adding messages and command executions
    - Building context from system state
    """

    def __init__(self, storage: SessionStorage | None = None):
        """Initialize manager.

        Args:
            storage: Storage backend (default: SQLite)
        """
        # Ensure workspace bootstrap files exist
        ensure_workspace()

        self._storage = storage or SessionStorage()
        self._current_session: Session | None = None

    @property
    def current_session(self) -> Session | None:
        """Get the current session."""
        return self._current_session

    def start_session(self, user_id: str = "default") -> Session:
        """Start a new session.

        Args:
            user_id: User identifier

        Returns:
            New session
        """
        self._current_session = self._storage.create_session(user_id)

        # Build initial context
        context = self.build_context()
        self._storage.update_context(self._current_session.id, context)
        self._current_session.context = context

        return self._current_session

    def resume_session(self, session_id: UUID) -> Session | None:
        """Resume an existing session.

        Args:
            session_id: Session UUID to resume

        Returns:
            Session if found, None otherwise
        """
        session = self._storage.get_session(session_id)
        if session:
            self._current_session = session
            # Refresh context
            context = self.build_context()
            self._storage.update_context(session_id, context)
            self._current_session.context = context
        return session

    def add_user_message(self, content: str) -> Message:
        """Add a user message to the current session.

        Args:
            content: Message content

        Returns:
            Created message
        """
        if not self._current_session:
            self.start_session()

        message = self._storage.add_message(
            self._current_session.id,
            MessageRole.USER,
            content,
        )
        self._current_session.conversation_history.append(message)
        return message

    def add_assistant_message(self, content: str, metadata: dict | None = None) -> Message:
        """Add an assistant message to the current session.

        Args:
            content: Message content
            metadata: Optional metadata (e.g., intent classification)

        Returns:
            Created message
        """
        if not self._current_session:
            self.start_session()

        message = self._storage.add_message(
            self._current_session.id,
            MessageRole.ASSISTANT,
            content,
            metadata,
        )
        self._current_session.conversation_history.append(message)
        return message

    def record_execution(
        self,
        command: str,
        status: ExecutionStatus,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        duration_ms: int = 0,
        parameters: dict | None = None,
    ) -> CommandExecution:
        """Record a command execution.

        Args:
            command: Executed command
            status: Execution status
            stdout: Standard output
            stderr: Standard error
            exit_code: Exit code
            duration_ms: Duration in milliseconds
            parameters: Command parameters

        Returns:
            Created execution record
        """
        if not self._current_session:
            self.start_session()

        from uuid import uuid4

        execution = CommandExecution(
            id=uuid4(),
            command=command,
            parameters=parameters or {},
            result={"stdout": stdout[:500], "exit_code": exit_code},  # Truncate long output
            status=status,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
        )

        self._storage.add_execution(self._current_session.id, execution)
        self._current_session.command_history.append(execution)

        # Update context with last command
        self._current_session.context.last_command = command
        self._storage.update_context(self._current_session.id, self._current_session.context)

        return execution

    def build_context(self) -> Context:
        """Build context from current system state.

        Returns:
            Context with current directory, auth status, etc.
        """
        context = Context(current_directory=os.getcwd())

        # Check authentication
        try:
            from traylinx.auth import get_access_token
            context.authenticated = bool(get_access_token())
        except ImportError:
            context.authenticated = False

        # Get recent results
        if self._current_session and self._current_session.command_history:
            recent = self._current_session.command_history[-5:]
            context.recent_results = [
                {"command": e.command, "status": e.status.value, "exit_code": e.exit_code}
                for e in recent
            ]

            # Get last command
            if recent:
                context.last_command = recent[-1].command

        return context

    def get_conversation_for_llm(self, max_messages: int = 20) -> list[dict[str, str]]:
        """Get conversation history formatted for LLM.

        Args:
            max_messages: Maximum messages to include

        Returns:
            List of message dicts for OpenAI API
        """
        if not self._current_session:
            return []

        history = self._current_session.conversation_history[-max_messages:]
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in history
        ]

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent sessions.

        Args:
            limit: Maximum sessions

        Returns:
            List of session summaries
        """
        return self._storage.list_sessions(limit)
