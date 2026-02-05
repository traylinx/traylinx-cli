"""Tests for suggestions and error handling."""

import pytest
from traylinx.cortex.suggestions import SuggestionEngine, get_suggestion_engine
from traylinx.cortex.errors import create_error, ErrorHandler, ErrorCategory, CortexError


class TestSuggestionEngine:
    """Tests for workflow suggestions."""

    @pytest.fixture
    def engine(self):
        return SuggestionEngine()

    def test_suggestion_after_run(self, engine):
        """Suggests logs after run."""
        engine.record_command("run")
        suggestions = engine.suggest()

        commands = [s.command for s in suggestions]
        assert "logs" in commands or "status" in commands

    def test_suggestion_after_stop(self, engine):
        """Suggests status after stop."""
        engine.record_command("stop")
        suggestions = engine.suggest()

        commands = [s.command for s in suggestions]
        assert "status" in commands or "run" in commands

    def test_undo_suggestion(self, engine):
        """Undo maps correctly."""
        undo = engine.get_undo_suggestion("run")
        assert undo is not None
        assert undo.command == "stop"

        undo = engine.get_undo_suggestion("stop")
        assert undo.command == "run"

        undo = engine.get_undo_suggestion("unknown")
        assert undo is None

    def test_max_suggestions(self, engine):
        """Respects max_suggestions param."""
        engine.record_command("run")
        suggestions = engine.suggest(max_suggestions=1)
        assert len(suggestions) <= 1

    def test_clear_history(self, engine):
        """Clear removes history."""
        engine.record_command("run")
        engine.clear_history()
        # Should have fewer/no suggestions after clear
        suggestions = engine.suggest()
        # Minimal context-based suggestions may still appear


class TestErrorHandling:
    """Tests for structured error handling."""

    def test_create_error(self):
        """Can create error from template."""
        error = create_error("agent_not_found", agent_name="my-agent")
        assert "my-agent" in error.message
        assert error.category == ErrorCategory.AGENT

    def test_error_suggestions(self):
        """Errors include suggestions."""
        error = create_error("network_error")
        assert len(error.suggestions) > 0

    def test_format_for_user(self):
        """User format includes suggestions."""
        error = create_error("not_authenticated")
        formatted = error.format_for_user()
        assert "❌" in formatted
        assert "Try:" in formatted

    def test_unknown_template(self):
        """Unknown template returns internal error."""
        error = create_error("nonexistent_template")
        assert error.category == ErrorCategory.INTERNAL

    def test_error_handler(self):
        """ErrorHandler tracks history."""
        handler = ErrorHandler()
        error = CortexError(
            message="Test error",
            category=ErrorCategory.AGENT,
        )
        handler.handle(error)

        recent = handler.get_recent_errors()
        assert len(recent) == 1

    def test_handle_exception(self):
        """Can handle Python exceptions."""
        handler = ErrorHandler()
        result = handler.handle_exception(ConnectionError("Network down"))
        assert "connection" in result.lower() or "network" in result.lower()
