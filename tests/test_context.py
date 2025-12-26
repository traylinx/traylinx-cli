"""Tests for the context module."""

from pathlib import Path
import pytest
from datetime import datetime

from traylinx.context import (
    ProjectContext,
    load_traylinx_md,
    CompactionMiddleware,
    ConversationMessage,
)
from traylinx.context.project import _parse_traylinx_md


class TestProjectContext:
    """Tests for TRAYLINX.md loading."""

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from directory without TRAYLINX.md."""
        result = load_traylinx_md(tmp_path)
        assert result is None

    def test_load_basic_traylinx_md(self, tmp_path):
        """Test loading a basic TRAYLINX.md file."""
        traylinx_file = tmp_path / "TRAYLINX.md"
        traylinx_file.write_text("""# Project Instructions

This is a test agent.

## Memory

- **project_name**: Test Project
- **version**: 1.0.0

## Workflows

- build
- deploy
- test
""")
        result = load_traylinx_md(tmp_path)

        assert result is not None
        assert "test agent" in result.instructions
        assert result.memory.get("project_name") == "Test Project"
        assert "build" in result.workflows

    def test_case_insensitive_filename(self, tmp_path):
        """Test that lowercase traylinx.md is also loaded."""
        traylinx_file = tmp_path / "traylinx.md"
        traylinx_file.write_text("Test instructions")

        result = load_traylinx_md(tmp_path)
        assert result is not None

    def test_to_system_prompt(self, tmp_path):
        """Test converting context to system prompt."""
        context = ProjectContext(
            instructions="Be helpful.",
            memory={"key": "value"},
            workflows=["build"],
        )

        prompt = context.to_system_prompt()
        assert "Be helpful" in prompt
        assert "key" in prompt
        assert "build" in prompt


class TestCompactionMiddleware:
    """Tests for conversation compaction."""

    def test_estimate_tokens(self):
        """Test token estimation."""
        msg = ConversationMessage(role="user", content="Hello world")
        tokens = msg.estimate_tokens()
        # ~11 chars / 4 + 1 = ~3-4 tokens
        assert tokens > 0
        assert tokens < 10

    def test_should_compact_under_threshold(self):
        """Test that compaction is not triggered under threshold."""
        middleware = CompactionMiddleware(max_tokens=1000, threshold=0.8)
        messages = [
            ConversationMessage(role="user", content="Hello"),
            ConversationMessage(role="assistant", content="Hi there"),
        ]
        assert not middleware.should_compact(messages)

    def test_should_compact_over_threshold(self):
        """Test that compaction is triggered over threshold."""
        middleware = CompactionMiddleware(max_tokens=100, threshold=0.8)
        # Create messages totaling ~100 tokens
        messages = [
            ConversationMessage(
                role="user",
                content="x" * 400  # ~100 tokens
            )
        ]
        assert middleware.should_compact(messages)

    def test_get_compaction_stats(self):
        """Test getting compaction statistics."""
        middleware = CompactionMiddleware(max_tokens=1000, threshold=0.8)
        messages = [
            ConversationMessage(role="user", content="Hello world"),
        ]
        stats = middleware.get_compaction_stats(messages)

        assert "total_tokens" in stats
        assert "max_tokens" in stats
        assert stats["max_tokens"] == 1000
        assert "usage_percent" in stats

    @pytest.mark.asyncio
    async def test_compact_preserves_recent(self):
        """Test that compaction preserves recent messages."""
        middleware = CompactionMiddleware(
            max_tokens=1000,
            threshold=0.5,
            preserve_recent=2,
        )

        messages = [
            ConversationMessage(role="user", content="Message 1"),
            ConversationMessage(role="assistant", content="Response 1"),
            ConversationMessage(role="user", content="Message 2"),
            ConversationMessage(role="assistant", content="Response 2"),
            ConversationMessage(role="user", content="Message 3"),
            ConversationMessage(role="assistant", content="Response 3"),
        ]

        compacted, result = await middleware.compact(messages)

        # Should preserve last 2 messages
        assert result.compacted_messages < result.original_messages
        assert any("Message 3" in m.content for m in compacted)

    @pytest.mark.asyncio
    async def test_compact_nothing_to_compact(self):
        """Test compaction when there are few messages."""
        middleware = CompactionMiddleware(preserve_recent=5)

        messages = [
            ConversationMessage(role="user", content="Hello"),
            ConversationMessage(role="assistant", content="Hi"),
        ]

        compacted, result = await middleware.compact(messages)

        assert len(compacted) == len(messages)
        assert result.summary == ""


class TestTUIImports:
    """Tests for TUI module imports."""

    def test_tui_module_imports(self):
        """Test that TUI module can be imported."""
        from traylinx.tui import TraylinxApp, ChatScreen, LogsScreen, StatusScreen

        assert TraylinxApp is not None
        assert ChatScreen is not None
        assert LogsScreen is not None
        assert StatusScreen is not None

    def test_context_module_imports(self):
        """Test that context module can be imported."""
        from traylinx.context import (
            ProjectContext,
            load_traylinx_md,
            CompactionMiddleware,
        )

        assert ProjectContext is not None
        assert load_traylinx_md is not None
        assert CompactionMiddleware is not None
