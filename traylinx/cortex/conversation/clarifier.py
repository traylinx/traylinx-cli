"""Clarification generator for ambiguous inputs.

Generates follow-up questions when intent classification needs more context:
- Missing required parameters (agent name, capability)
- Ambiguous commands (run vs start)
- Incomplete references
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Clarification:
    """A clarification request to present to the user."""

    question: str
    options: list[str]
    context_key: str  # Key for storing the answer
    required: bool = True


class ClarificationGenerator:
    """Generates follow-up questions for ambiguous intents.

    Analyzes intent classification results and generates appropriate
    clarification questions when required parameters are missing.
    """

    # Command requirements: what parameters are required for each command
    COMMAND_REQUIREMENTS: dict[str, list[str]] = {
        "run": ["agent_name"],
        "stop": ["agent_name"],
        "logs": ["agent_name"],
        "call": ["agent_name", "method"],
        "discover": [],  # Can run without params
        "status": [],
        "whoami": [],
        "login": [],
        "logout": [],
        "build": [],  # Uses current directory by default
        "validate": [],
        "publish": [],
    }

    # Friendly parameter descriptions
    PARAM_DESCRIPTIONS: dict[str, str] = {
        "agent_name": "agent",
        "method": "method to call",
        "capability": "capability to search for",
        "file": "file path",
        "directory": "directory",
    }

    def __init__(self) -> None:
        """Initialize clarification generator."""
        self._recent_suggestions: list[str] = []

    def needs_clarification(
        self,
        command: str | None,
        parameters: dict[str, Any],
        confidence: float,
    ) -> bool:
        """Check if clarification is needed.

        Args:
            command: Detected command
            parameters: Extracted parameters
            confidence: Classification confidence

        Returns:
            True if clarification needed
        """
        # Low confidence always needs clarification
        if confidence < 0.6:
            return True

        # No command detected
        if not command:
            return False  # Probably conversation, not command

        # Check for missing required parameters
        required = self.COMMAND_REQUIREMENTS.get(command, [])
        for param in required:
            if param not in parameters or not parameters[param]:
                return True

        return False

    def generate(
        self,
        command: str | None,
        parameters: dict[str, Any],
        confidence: float,
        context: dict[str, Any] | None = None,
    ) -> Clarification | None:
        """Generate a clarification question.

        Args:
            command: Detected command
            parameters: Extracted parameters
            confidence: Classification confidence
            context: Session context (recent agents, etc.)

        Returns:
            Clarification object or None
        """
        context = context or {}

        # Low confidence: ask what they meant
        # Low confidence: ask what they meant
        if confidence < 0.5:
            if command:
                question = f"Did you want to run the '{command}' command?"
                options = ["Yes", "No, I meant something else"]
                context_key = "intent_confirmed"
            else:
                question = "I'm not sure what you meant. Could you clarify?"
                options = ["List commands", "Show help"]
                context_key = "clarification_needed"
            
            return Clarification(
                question=question,
                options=options,
                context_key=context_key,
            )

        # No command but seems like an intent
        if not command:
            return None

        # Check for missing required parameters
        required = self.COMMAND_REQUIREMENTS.get(command, [])
        for param in required:
            if param not in parameters or not parameters[param]:
                return self._generate_param_clarification(param, command, context)

        return None

    def _generate_param_clarification(
        self,
        param: str,
        command: str,
        context: dict[str, Any],
    ) -> Clarification:
        """Generate clarification for a missing parameter.

        Args:
            param: Missing parameter name
            command: Target command
            context: Session context

        Returns:
            Clarification with question and options
        """
        param_desc = self.PARAM_DESCRIPTIONS.get(param, param)
        options: list[str] = []

        # Build smart options from context
        if param == "agent_name":
            # Suggest from running agents or recent history
            running = context.get("running_agents", [])
            recent = context.get("recent_agents", [])
            seen = set()
            for agent in running + recent:
                if agent not in seen:
                    options.append(agent)
                    seen.add(agent)
                if len(options) >= 5:
                    break

        # Generate question
        if command in ("run", "start"):
            question = f"Which agent would you like to start?"
        elif command in ("stop", "kill"):
            question = f"Which agent would you like to stop?"
        elif command == "logs":
            question = f"Which agent's logs would you like to view?"
        elif command == "call":
            if param == "agent_name":
                question = f"Which agent would you like to call?"
            else:
                question = f"What {param_desc} should I use?"
        else:
            question = f"What {param_desc} should I use for {command}?"

        return Clarification(
            question=question,
            options=options,
            context_key=param,
        )

    def generate_disambiguation(
        self,
        candidates: list[dict[str, Any]],
        category: str = "command",
    ) -> Clarification:
        """Generate disambiguation for multiple possible interpretations.

        Args:
            candidates: List of possible interpretations
            category: Type of disambiguation (command, agent, etc.)

        Returns:
            Clarification asking user to choose
        """
        if category == "command":
            question = "I found multiple possible commands. Which did you mean?"
            options = [
                f"{c.get('command', 'unknown')}: {c.get('description', '')}"
                for c in candidates[:5]
            ]
        elif category == "agent":
            question = "Multiple agents match. Which one?"
            options = [c.get("name", str(c)) for c in candidates[:5]]
        else:
            question = f"Please choose one of the following:"
            options = [str(c) for c in candidates[:5]]

        return Clarification(
            question=question,
            options=options,
            context_key=f"{category}_choice",
        )

    def merge_clarification(
        self,
        original_params: dict[str, Any],
        clarification_key: str,
        answer: str,
    ) -> dict[str, Any]:
        """Merge clarification answer into parameters.

        Args:
            original_params: Original extracted parameters
            clarification_key: Key for the clarification
            answer: User's answer

        Returns:
            Merged parameters dict
        """
        result = original_params.copy()

        # Handle numbered choices (e.g., "1", "2")
        if answer.isdigit():
            # Assume this is an index into recent suggestions
            idx = int(answer) - 1
            if 0 <= idx < len(self._recent_suggestions):
                answer = self._recent_suggestions[idx]

        result[clarification_key] = answer
        return result

    def set_recent_suggestions(self, suggestions: list[str]) -> None:
        """Store recent suggestions for numbered selection.

        Args:
            suggestions: List of suggestions shown to user
        """
        self._recent_suggestions = suggestions.copy()
