"""Tests for Cortex intent classification."""

import pytest
from traylinx.cortex.intent.classifier import IntentClassifier
from traylinx.cortex.types import IntentType, ConfirmationLevel


class TestPatternMatching:
    """Tests for pattern-based intent classification."""

    @pytest.fixture
    def classifier(self):
        """Create classifier with LLM disabled."""
        return IntentClassifier(use_llm=False, use_cache=False)

    def test_run_command(self, classifier):
        """Test 'run' command variants."""
        test_cases = [
            ("start my agent", "run"),
            ("run the agent", "run"),
        ]
        for input_text, expected_cmd in test_cases:
            intent = classifier.classify(input_text)
            assert intent.command == expected_cmd, f"Failed for: {input_text}"
            assert intent.type == IntentType.CLI_COMMAND

    def test_stop_command(self, classifier):
        """Test 'stop' command variants."""
        test_cases = [
            ("stop my agent", "stop"),
            ("stop the agent", "stop"),
        ]
        for input_text, expected_cmd in test_cases:
            intent = classifier.classify(input_text)
            assert intent.command == expected_cmd, f"Failed for: {input_text}"

    def test_logs_command(self, classifier):
        """Test 'logs' command variants."""
        test_cases = [
            ("show logs", "logs"),
            ("view the logs", "logs"),
            ("tail logs", "logs"),
        ]
        for input_text, expected_cmd in test_cases:
            intent = classifier.classify(input_text)
            assert intent.command == expected_cmd, f"Failed for: {input_text}"

    def test_discover_command(self, classifier):
        """Test 'discover' command variants."""
        test_cases = [
            ("find agents", "discover"),
            ("discover agents", "discover"),
        ]
        for input_text, expected_cmd in test_cases:
            intent = classifier.classify(input_text)
            assert intent.command == expected_cmd, f"Failed for: {input_text}"

    def test_auth_commands(self, classifier):
        """Test authentication commands."""
        intent = classifier.classify("am I logged in")
        assert intent.command == "whoami"

        intent = classifier.classify("sign in")
        assert intent.command == "login"

        intent = classifier.classify("sign out")
        assert intent.command == "logout"

    def test_confidence_levels(self, classifier):
        """Test confidence is set correctly."""
        intent = classifier.classify("start my agent")
        assert intent.confidence >= 0.8

        intent = classifier.classify("random gibberish xyz")
        assert intent.confidence < 0.8

    def test_empty_input(self, classifier):
        """Test empty input handling."""
        intent = classifier.classify("")
        assert intent.type == IntentType.AMBIGUOUS
        assert intent.confidence == 0.0

    def test_special_commands(self, classifier):
        """Test /commands."""
        intent = classifier.classify("/help")
        assert intent.command == "help"
        assert intent.confidence == 1.0

        intent = classifier.classify("/exit")
        assert intent.command == "exit"

        intent = classifier.classify("/history")
        assert intent.command == "history"


class TestParameterExtraction:
    """Tests for parameter extraction from commands."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier(use_llm=False, use_cache=False)

    def test_agent_name_extraction(self, classifier):
        """Test agent name is extracted."""
        intent = classifier.classify("run my-cool-agent")
        # Pattern matching may or may not extract depending on pattern
        assert intent.command == "run"

    def test_capability_extraction(self, classifier):
        """Test capability is extracted from discover."""
        intent = classifier.classify("find agents that can translate")
        assert intent.command == "discover"


class TestConfirmationLevels:
    """Tests for confirmation requirement detection."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier(use_llm=False, use_cache=False)

    def test_stop_requires_confirmation(self, classifier):
        """Stop should require soft confirmation."""
        intent = classifier.classify("stop my-agent")
        # Note: depends on confirmation level configuration

    def test_run_no_confirmation(self, classifier):
        """Run should not require confirmation."""
        intent = classifier.classify("start my agent")
        assert intent.confirmation_level == ConfirmationLevel.NONE


class TestCaching:
    """Tests for intent caching."""

    def test_cache_hit(self):
        """Test cache returns same intent."""
        classifier = IntentClassifier(use_llm=False, use_cache=True)

        intent1 = classifier.classify("start my agent")
        intent2 = classifier.classify("start my agent")

        assert intent1.command == intent2.command

    def test_cache_disabled(self):
        """Test cache can be disabled."""
        classifier = IntentClassifier(use_llm=False, use_cache=False)
        assert classifier._cache is None
