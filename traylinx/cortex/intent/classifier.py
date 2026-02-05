"""Intent classifier combining pattern matching and LLM classification.

Two-tier classification:
1. Pattern matching (fast, deterministic) - Reflex tier
2. LLM classification (flexible, semantic) - Reasoning tier

Falls back to pattern matching if LLM is unavailable.
Includes caching for repeated queries.
"""

from traylinx.cortex.types import Intent, IntentType, ConfirmationLevel
from traylinx.cortex.intent.patterns import match_pattern, get_confirmation_level
from traylinx.cortex.intent.extractors import extract_parameters
from traylinx.cortex.intent.cache import get_intent_cache
from traylinx.cortex.config import load_config


class IntentClassifier:
    """Classifies user input into executable intents.

    Uses pattern matching as primary method with optional LLM fallback
    for ambiguous or conversational inputs. Includes caching for performance.
    """

    def __init__(self, use_llm: bool = True, use_cache: bool = True):
        """Initialize classifier.

        Args:
            use_llm: Whether to use LLM for ambiguous cases
            use_cache: Whether to cache classification results
        """
        self._use_llm = use_llm
        self._use_cache = use_cache
        self._config = load_config()
        self._switchai_client = None
        self._cache = get_intent_cache() if use_cache else None

    def classify(self, user_input: str) -> Intent:
        """Classify user input into an Intent.

        Args:
            user_input: Raw user input string

        Returns:
            Intent with classification result
        """
        # Normalize input
        normalized = user_input.strip()
        if not normalized:
            return Intent(
                type=IntentType.AMBIGUOUS,
                confidence=0.0,
                raw_input=user_input,
            )

        # Check cache first
        if self._cache:
            cached = self._cache.get(normalized)
            if cached:
                return cached

        # Try pattern matching first (fast path)
        pattern_match = match_pattern(normalized)
        if pattern_match and pattern_match.confidence >= 0.8:
            # Extract parameters for the matched command
            params = extract_parameters(pattern_match.command, normalized)

            # Merge any captured groups from pattern
            params.update({k: v for k, v in pattern_match.groups.items() if v})

            # Determine confirmation level
            conf_level = get_confirmation_level(pattern_match.command)
            requires_conf = conf_level in ("soft", "hard")

            return Intent(
                type=IntentType.CLI_COMMAND,
                command=pattern_match.command,
                parameters=params,
                confidence=pattern_match.confidence,
                requires_confirmation=requires_conf,
                confirmation_level=ConfirmationLevel(conf_level),
                raw_input=user_input,
            )

        # Check for special commands (help, exit, etc.)
        if normalized.startswith("/"):
            return self._classify_special_command(normalized)

        # Low confidence pattern match or no match
        if pattern_match:
            # Partial match - might need clarification
            params = extract_parameters(pattern_match.command, normalized)
            params.update({k: v for k, v in pattern_match.groups.items() if v})

            return Intent(
                type=IntentType.CLI_COMMAND,
                command=pattern_match.command,
                parameters=params,
                confidence=pattern_match.confidence,
                raw_input=user_input,
            )

        # No pattern match - treat as conversation or use LLM
        if self._use_llm and self._config.intent_classification.use_llm:
            return self._classify_with_llm(normalized)

        # Default: treat as conversation
        return Intent(
            type=IntentType.CONVERSATION,
            confidence=0.5,
            raw_input=user_input,
        )

    def _classify_special_command(self, normalized: str) -> Intent:
        """Classify /commands."""
        command = normalized.split()[0].lower()

        special_commands = {
            "/help": "help",
            "/exit": "exit",
            "/quit": "exit",
            "/clear": "clear",
            "/history": "history",
            "/undo": "undo",
        }

        if command in special_commands:
            return Intent(
                type=IntentType.CLI_COMMAND,
                command=special_commands[command],
                confidence=1.0,
                raw_input=normalized,
            )

        return Intent(
            type=IntentType.AMBIGUOUS,
            confidence=0.3,
            raw_input=normalized,
        )

    def _classify_with_llm(self, user_input: str) -> Intent:
        """Classify using LLM (SwitchAILocal).

        This is called when pattern matching fails or has low confidence.
        """
        # Lazy load SwitchAI client
        if self._switchai_client is None:
            try:
                from traylinx.cortex.switchai.client import SwitchAIClient

                self._switchai_client = SwitchAIClient()
            except ImportError:
                # SwitchAI not available
                return Intent(
                    type=IntentType.CONVERSATION,
                    confidence=0.5,
                    raw_input=user_input,
                )

        try:
            return self._switchai_client.classify_intent(user_input)
        except Exception:
            # LLM classification failed, fall back to conversation
            return Intent(
                type=IntentType.CONVERSATION,
                confidence=0.5,
                raw_input=user_input,
            )

    def get_available_commands(self) -> list[str]:
        """Get list of available CLI commands."""
        from traylinx.cortex.intent.patterns import COMMAND_PATTERNS

        return list(COMMAND_PATTERNS.keys())
