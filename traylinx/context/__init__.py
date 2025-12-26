"""Context management for Traylinx CLI.

This module provides project context loading and conversation
management features:
- Organization/project context (ContextManager)
- TRAYLINX.md project context files
- Auto-compaction middleware for token limits
"""

# Re-export ContextManager for backward compatibility
from .organization import ContextManager

# New Phase 3 context features
from .project import ProjectContext, load_traylinx_md
from .compaction import CompactionMiddleware, ConversationMessage

__all__ = [
    # Backward compatibility
    "ContextManager",
    # Project context
    "ProjectContext",
    "load_traylinx_md",
    # Compaction
    "CompactionMiddleware",
    "ConversationMessage",
]
