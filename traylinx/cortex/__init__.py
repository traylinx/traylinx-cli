"""Cortex package initialization and integration.

This is the main entry point for Traylinx Cortex - a natural language
interface for the Traylinx CLI.

Quick Start:
    from traylinx.cortex import Cortex

    # Initialize Cortex
    cortex = Cortex()

    # Process natural language input
    result = cortex.process("start my agent")

    # Start interactive mode
    cortex.start_interactive()
"""

from traylinx.cortex.types import Intent, IntentType, ExecutionResult
from traylinx.cortex.intent.classifier import IntentClassifier
from traylinx.cortex.executor.executor import CommandExecutor
from traylinx.cortex.session.manager import SessionManager
from traylinx.cortex.conversation import ConversationState, ReferenceResolver, ClarificationGenerator
from traylinx.cortex.suggestions import SuggestionEngine, get_suggestion_engine
from traylinx.cortex.errors import ErrorHandler, create_error


class Cortex:
    """Main Cortex interface.

    Provides a unified API for natural language CLI interaction:
    - Intent classification (pattern + LLM)
    - Multi-turn conversation support
    - Command execution
    - Session management
    - Suggestions and error handling
    """

    def __init__(
        self,
        workspace: str | None = None,
        use_llm: bool = True,
        use_cache: bool = True,
    ):
        """Initialize Cortex.

        Args:
            workspace: Workspace path (default: current directory)
            use_llm: Whether to use LLM for classification
            use_cache: Whether to cache intents
        """
        import os

        self._workspace = workspace or os.getcwd()
        self._classifier = IntentClassifier(use_llm=use_llm, use_cache=use_cache)
        self._executor = CommandExecutor()
        self._session_manager = SessionManager()  # Uses default storage
        self._conversation = ConversationState()
        self._resolver = ReferenceResolver()
        self._clarifier = ClarificationGenerator()
        self._suggestions = get_suggestion_engine()
        self._errors = ErrorHandler()

    def process(self, user_input: str) -> ExecutionResult:
        """Process natural language input.

        Args:
            user_input: User's natural language input

        Returns:
            Execution result
        """
        # Resolve references
        resolved_input, _ = self._resolver.resolve(user_input)

        # Classify intent
        self._conversation.start_classification()
        intent = self._classifier.classify(resolved_input)

        # Check if clarification needed (ambiguous or missing params)
        clarification = self._clarifier.generate(
            command=intent.command,
            parameters=intent.parameters,
            confidence=intent.confidence,
        )
        
        if clarification:
            self._conversation.request_clarification(
                original_input=user_input,
                question=clarification.question,
                options=clarification.options,
                context_key=clarification.context_key,
            )
            return ExecutionResult(
                success=False,
                command="clarify",
                formatted_output=f"❓ {clarification.question}",
            )

        # Execute command
        if intent.type == IntentType.CLI_COMMAND and intent.command:
            self._conversation.start_execution()
            result = self._executor.execute(intent)

            # Track for suggestions
            self._suggestions.record_command(intent.command, result.success)

            # Track for reference resolution
            if "agent_name" in intent.parameters:
                self._resolver.add_mention("agent", intent.parameters["agent_name"])

            # Add suggestions to result
            suggestions = self._suggestions.suggest(max_suggestions=2)
            if suggestions:
                result.suggestions = [s.text for s in suggestions]

            self._conversation.reset()
            return result

        # Handle conversation
        self._conversation.reset()
        return ExecutionResult(
            success=True,
            command="conversation",
            formatted_output=f"💬 I understood: {intent.raw_input}",
        )

    def start_interactive(self) -> None:
        """Start interactive REPL mode."""
        from traylinx.cortex.chat.repl import ChatREPL

        repl = ChatREPL(
            session_manager=self._session_manager,
            classifier=self._classifier,
            executor=self._executor,
        )
        repl.start()

    def get_suggestions(self, max_count: int = 3) -> list[str]:
        """Get current suggestions.

        Args:
            max_count: Maximum suggestions

        Returns:
            List of suggestion texts
        """
        suggestions = self._suggestions.suggest(max_suggestions=max_count)
        return [s.text for s in suggestions]

    def get_undo(self) -> str | None:
        """Get undo suggestion for last command.

        Returns:
            Undo command or None
        """
        if self._suggestions._history:
            last_cmd = self._suggestions._history[-1]
            undo = self._suggestions.get_undo_suggestion(last_cmd)
            if undo:
                return undo.command
        return None

    def clear_context(self) -> None:
        """Clear conversation context."""
        self._resolver.clear()
        self._conversation.reset()
        self._suggestions.clear_history()


# Convenience exports
__all__ = [
    "Cortex",
    "Intent",
    "IntentType",
    "ExecutionResult",
    "IntentClassifier",
    "CommandExecutor",
    "SessionManager",
    "ConversationState",
    "ReferenceResolver",
    "ClarificationGenerator",
    "SuggestionEngine",
    "ErrorHandler",
    "create_error",
]
