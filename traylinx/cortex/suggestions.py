"""Suggestion system for proactive command recommendations.

Analyzes context and history to suggest next actions:
- Based on recent commands
- Based on current state
- Based on common workflows
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Suggestion:
    """A suggested action."""

    text: str
    command: str | None = None
    confidence: float = 0.5
    category: str = "general"  # "workflow", "fix", "explore", "undo"


class SuggestionEngine:
    """Generates contextual suggestions for next actions.

    Analyzes:
    - Recent command history
    - Current context (running agents, errors)
    - Common workflows
    """

    # Common workflow patterns: (trigger, suggestions)
    WORKFLOW_PATTERNS: list[tuple[list[str], list[Suggestion]]] = [
        # After run → suggest logs or status
        (
            ["run"],
            [
                Suggestion(
                    text="View logs",
                    command="logs",
                    confidence=0.8,
                    category="workflow",
                ),
                Suggestion(
                    text="Check status",
                    command="status",
                    confidence=0.6,
                    category="workflow",
                ),
            ],
        ),
        # After stop → suggest status or run
        (
            ["stop"],
            [
                Suggestion(
                    text="Check status",
                    command="status",
                    confidence=0.7,
                    category="workflow",
                ),
                Suggestion(
                    text="Start again",
                    command="run",
                    confidence=0.5,
                    category="undo",
                ),
            ],
        ),
        # After build → suggest run or validate
        (
            ["build"],
            [
                Suggestion(
                    text="Start the agent",
                    command="run",
                    confidence=0.8,
                    category="workflow",
                ),
                Suggestion(
                    text="Validate config",
                    command="validate",
                    confidence=0.5,
                    category="workflow",
                ),
            ],
        ),
        # After discover → suggest call
        (
            ["discover"],
            [
                Suggestion(
                    text="Call an agent",
                    command="call",
                    confidence=0.7,
                    category="workflow",
                ),
            ],
        ),
        # After login → suggest whoami
        (
            ["login"],
            [
                Suggestion(
                    text="Check identity",
                    command="whoami",
                    confidence=0.6,
                    category="workflow",
                ),
            ],
        ),
        # After error → suggest logs
        (
            ["error"],
            [
                Suggestion(
                    text="View logs for details",
                    command="logs",
                    confidence=0.9,
                    category="fix",
                ),
            ],
        ),
    ]

    # Undo mappings: command → undo command
    UNDO_COMMANDS: dict[str, str] = {
        "run": "stop",
        "start": "stop",
        "stop": "run",
        "login": "logout",
        "logout": "login",
    }

    def __init__(self) -> None:
        """Initialize suggestion engine."""
        self._history: list[str] = []
        self._errors: list[str] = []

    def record_command(self, command: str, success: bool = True) -> None:
        """Record a command execution.

        Args:
            command: Command that was executed
            success: Whether it succeeded
        """
        self._history.append(command)
        if not success:
            self._errors.append(command)

        # Keep history bounded
        if len(self._history) > 50:
            self._history = self._history[-25:]
        if len(self._errors) > 20:
            self._errors = self._errors[-10:]

    def suggest(
        self,
        context: dict[str, Any] | None = None,
        max_suggestions: int = 3,
    ) -> list[Suggestion]:
        """Generate suggestions based on context and history.

        Args:
            context: Session context (running_agents, etc.)
            max_suggestions: Maximum suggestions to return

        Returns:
            List of suggestions, highest confidence first
        """
        context = context or {}
        suggestions: list[Suggestion] = []

        # Check workflow patterns
        if self._history:
            last_command = self._history[-1]
            for pattern_commands, pattern_suggestions in self.WORKFLOW_PATTERNS:
                if last_command in pattern_commands:
                    suggestions.extend(pattern_suggestions)

        # Check for error recovery
        if self._errors:
            suggestions.append(
                Suggestion(
                    text="View logs to debug recent error",
                    command="logs",
                    confidence=0.85,
                    category="fix",
                )
            )

        # Check context-based suggestions
        running_agents = context.get("running_agents", [])
        if running_agents:
            suggestions.append(
                Suggestion(
                    text=f"View logs for {running_agents[0]}",
                    command="logs",
                    confidence=0.5,
                    category="explore",
                )
            )

        if not context.get("authenticated", True):
            suggestions.append(
                Suggestion(
                    text="Sign in to access all features",
                    command="login",
                    confidence=0.6,
                    category="general",
                )
            )

        # Deduplicate and sort by confidence
        seen = set()
        unique: list[Suggestion] = []
        for s in suggestions:
            if s.command not in seen:
                seen.add(s.command)
                unique.append(s)

        unique.sort(key=lambda s: s.confidence, reverse=True)
        return unique[:max_suggestions]

    def get_undo_suggestion(self, last_command: str) -> Suggestion | None:
        """Get an undo suggestion for the last command.

        Args:
            last_command: The command to undo

        Returns:
            Undo suggestion or None
        """
        undo_cmd = self.UNDO_COMMANDS.get(last_command)
        if undo_cmd:
            return Suggestion(
                text=f"Undo: {undo_cmd}",
                command=undo_cmd,
                confidence=0.9,
                category="undo",
            )
        return None

    def clear_history(self) -> None:
        """Clear command history."""
        self._history.clear()
        self._errors.clear()


# Global suggestion engine instance
_engine: SuggestionEngine | None = None


def get_suggestion_engine() -> SuggestionEngine:
    """Get the global suggestion engine.

    Returns:
        Global SuggestionEngine
    """
    global _engine
    if _engine is None:
        _engine = SuggestionEngine()
    return _engine
