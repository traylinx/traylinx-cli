"""Multi-turn conversation support for Traylinx Cortex.

Provides:
- ConversationState: State machine for conversation flow
- ReferenceResolver: Resolve pronouns and references from history
- ClarificationGenerator: Generate follow-up questions for ambiguous input
"""

from traylinx.cortex.conversation.state import ConversationState, ConversationPhase
from traylinx.cortex.conversation.resolver import ReferenceResolver
from traylinx.cortex.conversation.clarifier import ClarificationGenerator

__all__ = [
    "ConversationState",
    "ConversationPhase",
    "ReferenceResolver",
    "ClarificationGenerator",
]
