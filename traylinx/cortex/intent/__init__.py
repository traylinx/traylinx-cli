"""Intent classification for Traylinx Cortex.

Provides pattern-based and LLM-based classification of user input
to determine the intended CLI command or action.
"""

from traylinx.cortex.intent.classifier import IntentClassifier
from traylinx.cortex.intent.patterns import COMMAND_PATTERNS, match_pattern
from traylinx.cortex.intent.extractors import extract_parameters

__all__ = [
    "IntentClassifier",
    "COMMAND_PATTERNS",
    "match_pattern",
    "extract_parameters",
]
