"""Command executor for Traylinx Cortex.

Executes CLI commands via subprocess with:
- Confirmation gates
- Timeout handling
- Result formatting
"""

from traylinx.cortex.executor.executor import CommandExecutor
from traylinx.cortex.executor.confirmation import ConfirmationGate, get_confirmation
from traylinx.cortex.executor.formatters import format_result, ResultType

__all__ = [
    "CommandExecutor",
    "ConfirmationGate",
    "get_confirmation",
    "format_result",
    "ResultType",
]
