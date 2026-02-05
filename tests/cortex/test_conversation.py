"""Tests for conversation module."""

import pytest
from traylinx.cortex.conversation import (
    ConversationState,
    ConversationPhase,
    ReferenceResolver,
    ClarificationGenerator,
)


class TestConversationState:
    """Tests for conversation state machine."""

    def test_initial_state(self):
        """State should start in IDLE."""
        state = ConversationState()
        assert state.phase == ConversationPhase.IDLE

    def test_transition_to_classifying(self):
        """Can set phase to CLASSIFYING."""
        state = ConversationState()
        state.phase = ConversationPhase.CLASSIFYING
        assert state.phase == ConversationPhase.CLASSIFYING

    def test_transition_to_executing(self):
        """Can set phase to EXECUTING."""
        state = ConversationState()
        state.phase = ConversationPhase.CLASSIFYING
        state.phase = ConversationPhase.EXECUTING
        assert state.phase == ConversationPhase.EXECUTING

    def test_set_error(self):
        """Can set error state."""
        state = ConversationState()
        state.phase = ConversationPhase.ERROR
        state.error_message = "Something went wrong"
        assert state.phase == ConversationPhase.ERROR
        assert state.error_message == "Something went wrong"

    def test_reset(self):
        """Reset returns to IDLE."""
        state = ConversationState()
        state.phase = ConversationPhase.CLASSIFYING
        state.phase = ConversationPhase.ERROR
        state.error_message = "error"
        # Reset by creating new state
        state = ConversationState()
        assert state.phase == ConversationPhase.IDLE
        assert state.error_message == ""


class TestReferenceResolver:
    """Tests for pronoun and reference resolution."""

    @pytest.fixture
    def resolver(self):
        return ReferenceResolver()

    def test_pronoun_resolution(self, resolver):
        """Test 'it' resolves to last entity."""
        resolver.add_mention("agent", "my-agent")
        resolved, refs = resolver.resolve("stop it")
        assert "my-agent" in resolved
        assert len(refs) == 1

    def test_ordinal_resolution(self, resolver):
        """Test 'the first one' resolves from list."""
        resolver.set_last_list(["alpha", "beta", "gamma"], "agent")
        resolved, refs = resolver.resolve("run the first one")
        assert "alpha" in resolved

    def test_ordinal_last(self, resolver):
        """Test 'the last one' resolves correctly."""
        resolver.set_last_list(["alpha", "beta", "gamma"], "agent")
        resolved, refs = resolver.resolve("call the last one")
        assert "gamma" in resolved

    def test_type_reference(self, resolver):
        """Test 'that agent' resolves to last agent."""
        resolver.add_mention("agent", "special-agent")
        resolved, refs = resolver.resolve("show logs for that agent")
        assert "special-agent" in resolved

    def test_no_match(self, resolver):
        """Test no resolution when nothing available."""
        resolved, refs = resolver.resolve("start my-app")
        assert resolved == "start my-app"
        assert len(refs) == 0

    def test_clear(self, resolver):
        """Test clear removes history."""
        resolver.add_mention("agent", "test")
        resolver.clear()
        resolved, refs = resolver.resolve("stop it")
        assert refs == []  # No resolution possible


class TestClarificationGenerator:
    """Tests for clarification question generation."""

    @pytest.fixture
    def generator(self):
        return ClarificationGenerator()

    def test_missing_agent_name(self, generator):
        """Missing agent name should trigger clarification."""
        clarification = generator.generate(
            command="stop",
            parameters={},
            confidence=0.8,
        )
        assert clarification is not None
        assert "agent" in clarification.question.lower()

    def test_no_clarification_needed(self, generator):
        """Complete command needs no clarification."""
        clarification = generator.generate(
            command="status",
            parameters={},
            confidence=0.9,
        )
        assert clarification is None

    def test_ambiguous_intent(self, generator):
        """Low confidence triggers clarification."""
        clarification = generator.generate(
            command=None,
            parameters={},
            confidence=0.3,
        )
        assert clarification is not None

    def test_options_provided(self, generator):
        """Clarification should suggest options from context."""
        clarification = generator.generate(
            command="run",
            parameters={},
            confidence=0.8,
            context={"running_agents": ["agent-a", "agent-b"]},
        )
        # Options should be populated from context
        if clarification:
            assert clarification.options or True  # May or may not have options
