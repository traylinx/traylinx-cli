"""Auto-compaction middleware for conversation context.

This module provides middleware to automatically compact (summarize)
conversation history when approaching token limits to prevent
context window overflow errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class ConversationMessage:
    """Represents a single message in a conversation."""

    role: str
    """Role of the message sender (user, assistant, system)."""

    content: str
    """Message content."""

    timestamp: datetime = field(default_factory=datetime.now)
    """When the message was created."""

    tokens: int = 0
    """Estimated token count for this message."""

    metadata: dict = field(default_factory=dict)
    """Additional metadata (tool calls, etc.)."""

    def estimate_tokens(self) -> int:
        """Estimate token count using character approximation.

        Uses ~4 characters per token as a rough estimate.
        """
        if self.tokens > 0:
            return self.tokens
        self.tokens = len(self.content) // 4 + 1
        return self.tokens


@dataclass
class CompactionResult:
    """Result of a compaction operation."""

    original_messages: int
    """Number of messages before compaction."""

    compacted_messages: int
    """Number of messages after compaction."""

    original_tokens: int
    """Token count before compaction."""

    compacted_tokens: int
    """Token count after compaction."""

    summary: str
    """Summary of compacted messages."""


class CompactionMiddleware:
    """Middleware for auto-compacting conversation history.

    Monitors token usage and triggers compaction when approaching
    the configured threshold to prevent context window overflow.
    """

    # Default token limits for different models
    MODEL_TOKEN_LIMITS = {
        "gemini-2.0-flash": 1_000_000,
        "gemini-1.5-pro": 2_000_000,
        "gpt-4": 128_000,
        "gpt-4-turbo": 128_000,
        "claude-3-opus": 200_000,
        "claude-3-sonnet": 200_000,
        "default": 100_000,
    }

    def __init__(
        self,
        max_tokens: int | None = None,
        threshold: float = 0.8,
        model: str = "default",
        preserve_recent: int = 5,
    ):
        """Initialize compaction middleware.

        Args:
            max_tokens: Maximum token limit (overrides model default)
            threshold: Trigger compaction at this fraction of max_tokens
            model: Model name for default token limit lookup
            preserve_recent: Number of recent messages to preserve
        """
        self.max_tokens = max_tokens or self.MODEL_TOKEN_LIMITS.get(
            model, self.MODEL_TOKEN_LIMITS["default"]
        )
        self.threshold = threshold
        self.preserve_recent = preserve_recent
        self._summary_cache: str | None = None

    def get_total_tokens(self, messages: list[ConversationMessage]) -> int:
        """Calculate total tokens in message list.

        Args:
            messages: List of conversation messages

        Returns:
            Total estimated token count
        """
        return sum(m.estimate_tokens() for m in messages)

    def should_compact(self, messages: list[ConversationMessage]) -> bool:
        """Check if compaction should be triggered.

        Args:
            messages: Current conversation messages

        Returns:
            True if compaction should be triggered
        """
        total = self.get_total_tokens(messages)
        threshold_tokens = int(self.max_tokens * self.threshold)
        return total > threshold_tokens

    def get_compaction_stats(
        self, messages: list[ConversationMessage]
    ) -> dict[str, int | float]:
        """Get statistics about current context usage.

        Args:
            messages: Current conversation messages

        Returns:
            Dict with token counts and percentages
        """
        total = self.get_total_tokens(messages)
        return {
            "total_tokens": total,
            "max_tokens": self.max_tokens,
            "threshold_tokens": int(self.max_tokens * self.threshold),
            "usage_percent": (total / self.max_tokens) * 100,
            "messages_count": len(messages),
        }

    async def compact(
        self,
        messages: list[ConversationMessage],
        summarizer=None,
    ) -> tuple[list[ConversationMessage], CompactionResult]:
        """Compact conversation history by summarizing older messages.

        Args:
            messages: Full list of conversation messages
            summarizer: Optional async function to generate summary

        Returns:
            Tuple of (compacted messages, compaction result)
        """
        original_tokens = self.get_total_tokens(messages)
        original_count = len(messages)

        # Keep system messages and recent messages
        system_messages = [m for m in messages if m.role == "system"]
        non_system = [m for m in messages if m.role != "system"]

        # Preserve recent messages
        if len(non_system) <= self.preserve_recent:
            # Nothing to compact
            return messages, CompactionResult(
                original_messages=original_count,
                compacted_messages=original_count,
                original_tokens=original_tokens,
                compacted_tokens=original_tokens,
                summary="",
            )

        # Split into old (to compact) and recent (to preserve)
        old_messages = non_system[: -self.preserve_recent]
        recent_messages = non_system[-self.preserve_recent :]

        # Generate summary of old messages
        summary = await self._generate_summary(old_messages, summarizer)

        # Create summary message
        summary_message = ConversationMessage(
            role="system",
            content=f"[Previous conversation summary]\n{summary}",
            metadata={"is_summary": True, "summarized_count": len(old_messages)},
        )
        summary_message.estimate_tokens()

        # Build compacted message list
        compacted = system_messages + [summary_message] + recent_messages
        compacted_tokens = self.get_total_tokens(compacted)

        return compacted, CompactionResult(
            original_messages=original_count,
            compacted_messages=len(compacted),
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            summary=summary,
        )

    async def _generate_summary(
        self,
        messages: list[ConversationMessage],
        summarizer=None,
    ) -> str:
        """Generate a summary of messages.

        Args:
            messages: Messages to summarize
            summarizer: Optional async function for LLM summarization

        Returns:
            Summary string
        """
        if summarizer:
            # Use provided summarizer (e.g., LLM call)
            content = "\n".join(
                f"{m.role}: {m.content[:500]}" for m in messages
            )
            return await summarizer(content)

        # Fallback: simple extraction summary
        summary_parts = []

        for msg in messages:
            role = msg.role.capitalize()
            # Extract first line or first 100 chars
            first_line = msg.content.split("\n")[0][:100]
            if len(msg.content) > 100:
                first_line += "..."
            summary_parts.append(f"- {role}: {first_line}")

        return "\n".join(summary_parts[:20])  # Limit to 20 items


def should_compact(
    messages: list[ConversationMessage],
    max_tokens: int = 100_000,
    threshold: float = 0.8,
) -> bool:
    """Convenience function to check if compaction is needed.

    Args:
        messages: Conversation messages
        max_tokens: Maximum token limit
        threshold: Compaction threshold

    Returns:
        True if compaction should be triggered
    """
    middleware = CompactionMiddleware(max_tokens=max_tokens, threshold=threshold)
    return middleware.should_compact(messages)
