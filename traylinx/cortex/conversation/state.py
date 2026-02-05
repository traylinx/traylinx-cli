"""Conversation state machine for multi-turn dialogues.

Manages the flow of conversation through distinct phases:
IDLE → CLASSIFYING → (CLARIFYING) → EXECUTING → RESPONDING → IDLE

States:
- IDLE: Waiting for user input
- CLASSIFYING: Processing intent
- CLARIFYING: Waiting for clarification
- EXECUTING: Running CLI command
- RESPONDING: Generating response
- ERROR: Handling error state
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConversationPhase(str, Enum):
    """Phase of the conversation state machine."""

    IDLE = "idle"               # Waiting for user input
    CLASSIFYING = "classifying"  # Processing intent
    CLARIFYING = "clarifying"    # Waiting for clarification
    EXECUTING = "executing"      # Running CLI command
    RESPONDING = "responding"    # Generating response
    ERROR = "error"              # Error state


@dataclass
class PendingClarification:
    """A pending clarification request."""

    original_input: str
    question: str
    options: list[str] = field(default_factory=list)
    context_key: str = ""  # e.g., "agent_name", "command"
    partial_intent: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    """State machine for multi-turn conversations.

    Tracks the current phase and any pending clarifications or partial intents.
    """

    phase: ConversationPhase = ConversationPhase.IDLE
    pending_clarification: PendingClarification | None = None
    accumulated_context: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3

    def transition_to(self, new_phase: ConversationPhase) -> None:
        """Transition to a new phase.

        Args:
            new_phase: Target phase
        """
        self.phase = new_phase

    def start_classification(self) -> None:
        """Begin classifying user input."""
        self.transition_to(ConversationPhase.CLASSIFYING)
        self.error_message = ""

    def request_clarification(
        self,
        original_input: str,
        question: str,
        options: list[str] | None = None,
        context_key: str = "",
        partial_intent: dict[str, Any] | None = None,
    ) -> None:
        """Enter clarification state with a follow-up question.

        Args:
            original_input: User's original input
            question: Follow-up question to ask
            options: Optional choices to present
            context_key: Key for the expected answer
            partial_intent: Partially resolved intent
        """
        self.pending_clarification = PendingClarification(
            original_input=original_input,
            question=question,
            options=options or [],
            context_key=context_key,
            partial_intent=partial_intent or {},
        )
        self.transition_to(ConversationPhase.CLARIFYING)

    def receive_clarification(self, answer: str) -> dict[str, Any]:
        """Process a clarification response.

        Args:
            answer: User's clarification answer

        Returns:
            Merged intent with clarification
        """
        if not self.pending_clarification:
            return {}

        result = self.pending_clarification.partial_intent.copy()

        # If context_key is set, add the answer under that key
        if self.pending_clarification.context_key:
            result[self.pending_clarification.context_key] = answer

        # Also store in accumulated context
        if self.pending_clarification.context_key:
            self.accumulated_context[self.pending_clarification.context_key] = answer

        self.pending_clarification = None
        self.transition_to(ConversationPhase.CLASSIFYING)

        return result

    def start_execution(self) -> None:
        """Begin command execution."""
        self.transition_to(ConversationPhase.EXECUTING)

    def start_responding(self) -> None:
        """Begin generating response."""
        self.transition_to(ConversationPhase.RESPONDING)

    def enter_error(self, message: str) -> None:
        """Enter error state.

        Args:
            message: Error description
        """
        self.error_message = message
        self.retry_count += 1
        self.transition_to(ConversationPhase.ERROR)

    def reset(self) -> None:
        """Reset to idle state."""
        self.phase = ConversationPhase.IDLE
        self.pending_clarification = None
        self.error_message = ""
        # Keep accumulated_context for multi-turn reference

    def should_retry(self) -> bool:
        """Check if retry is allowed.

        Returns:
            True if retries remaining
        """
        return self.retry_count < self.max_retries

    def is_awaiting_clarification(self) -> bool:
        """Check if waiting for clarification.

        Returns:
            True if in clarifying phase
        """
        return self.phase == ConversationPhase.CLARIFYING

    def get_clarification_prompt(self) -> str | None:
        """Get the current clarification question.

        Returns:
            Question string or None
        """
        if not self.pending_clarification:
            return None

        prompt = self.pending_clarification.question

        if self.pending_clarification.options:
            options_str = "\n".join(
                f"  {i+1}. {opt}"
                for i, opt in enumerate(self.pending_clarification.options)
            )
            prompt += f"\n\n{options_str}"

        return prompt
