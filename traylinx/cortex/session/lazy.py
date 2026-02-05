"""Lazy loading utilities for session management.

Implements deferred loading patterns to improve startup time:
- Lazy session loading
- Deferred database connections
- On-demand message retrieval
"""

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar, Callable
import threading

from traylinx.cortex.types import Session, Message


T = TypeVar("T")


class Lazy(Generic[T]):
    """Lazy wrapper for deferred initialization.

    Usage:
        connection = Lazy(lambda: create_database_connection())
        # Connection is not created yet
        conn = connection.value  # Now it's created
    """

    def __init__(self, factory: Callable[[], T]):
        """Initialize lazy wrapper.

        Args:
            factory: Function to create the value
        """
        self._factory = factory
        self._value: T | None = None
        self._initialized = False
        self._lock = threading.Lock()

    @property
    def value(self) -> T:
        """Get the value, initializing if needed.

        Returns:
            The lazily initialized value
        """
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._value = self._factory()
                    self._initialized = True
        return self._value  # type: ignore

    @property
    def is_initialized(self) -> bool:
        """Check if value has been initialized."""
        return self._initialized

    def reset(self) -> None:
        """Reset the lazy wrapper to uninitialized state."""
        with self._lock:
            self._value = None
            self._initialized = False


@dataclass
class LazySession:
    """A session with lazy-loaded messages and context.

    Only loads full message history when needed.
    """

    session_id: str
    workspace: str
    created_at: float = 0.0
    _message_loader: Callable[[], list[Message]] | None = None
    _messages: list[Message] | None = None
    _metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def messages(self) -> list[Message]:
        """Get messages, loading lazily if needed."""
        if self._messages is None:
            if self._message_loader:
                self._messages = self._message_loader()
            else:
                self._messages = []
        return self._messages

    @property
    def message_count(self) -> int:
        """Get message count without loading all messages."""
        if self._messages is not None:
            return len(self._messages)
        return self._metadata.get("message_count", 0)

    def set_message_loader(self, loader: Callable[[], list[Message]]) -> None:
        """Set the function to load messages.

        Args:
            loader: Function that returns messages
        """
        self._message_loader = loader

    def preload(self) -> None:
        """Force load all messages."""
        _ = self.messages

    def to_session(self) -> Session:
        """Convert to full Session object.

        Returns:
            Session with all data loaded
        """
        from traylinx.cortex.types import Session

        return Session(
            id=self.session_id,
            workspace=self.workspace,
            messages=self.messages,
            created_at=self.created_at,
        )


class LazySessionLoader:
    """Loads sessions lazily from storage.

    Only loads session metadata initially, deferring
    message loading until accessed.
    """

    def __init__(self, storage: Any):
        """Initialize lazy loader.

        Args:
            storage: SessionStorage instance
        """
        self._storage = storage
        self._sessions: dict[str, LazySession] = {}

    def get_session(self, session_id: str) -> LazySession | None:
        """Get a lazy session by ID.

        Args:
            session_id: Session ID

        Returns:
            LazySession or None
        """
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Load metadata only
        metadata = self._storage.get_session_metadata(session_id)
        if metadata is None:
            return None

        lazy = LazySession(
            session_id=session_id,
            workspace=metadata.get("workspace", ""),
            created_at=metadata.get("created_at", 0.0),
            _metadata=metadata,
        )

        # Set up lazy message loading
        lazy.set_message_loader(
            lambda sid=session_id: self._storage.get_messages(sid)
        )

        self._sessions[session_id] = lazy
        return lazy

    def list_sessions(self, workspace: str | None = None) -> list[LazySession]:
        """List all sessions (lazy).

        Args:
            workspace: Optional workspace filter

        Returns:
            List of lazy sessions
        """
        session_ids = self._storage.list_session_ids(workspace=workspace)
        return [
            self.get_session(sid)
            for sid in session_ids
            if self.get_session(sid) is not None
        ]

    def invalidate(self, session_id: str) -> None:
        """Invalidate cached session.

        Args:
            session_id: Session to invalidate
        """
        self._sessions.pop(session_id, None)

    def clear_cache(self) -> None:
        """Clear all cached sessions."""
        self._sessions.clear()
