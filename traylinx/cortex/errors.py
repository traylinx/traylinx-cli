"""Enhanced error handling for Cortex.

Provides:
- Structured error types
- User-friendly error messages
- Automatic recovery suggestions
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    """Categories of errors."""

    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AGENT = "agent"
    CONFIG = "config"
    PERMISSION = "permission"
    INTERNAL = "internal"
    USER_INPUT = "user_input"


class ErrorSeverity(str, Enum):
    """Severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CortexError:
    """Structured error with user-friendly details."""

    message: str
    category: ErrorCategory
    severity: ErrorSeverity = ErrorSeverity.ERROR
    code: str = ""
    suggestions: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    recoverable: bool = True

    def format_for_user(self) -> str:
        """Format error for display to user.

        Returns:
            Formatted error string
        """
        parts = [f"❌ {self.message}"]

        if self.suggestions:
            parts.append("\n💡 Try:")
            for suggestion in self.suggestions:
                parts.append(f"   • {suggestion}")

        return "\n".join(parts)

    def format_for_log(self) -> str:
        """Format error for logging.

        Returns:
            Detailed log string
        """
        return (
            f"[{self.severity.value.upper()}] [{self.category.value}] "
            f"{self.code}: {self.message} | Details: {self.details}"
        )


# Common error templates
ERROR_TEMPLATES: dict[str, CortexError] = {
    "agent_not_found": CortexError(
        message="Agent '{agent_name}' not found",
        category=ErrorCategory.AGENT,
        suggestions=[
            "Check the agent name spelling",
            "Run 'tx status' to see running agents",
            "Run 'tx discover' to find available agents",
        ],
    ),
    "agent_not_running": CortexError(
        message="Agent '{agent_name}' is not running",
        category=ErrorCategory.AGENT,
        suggestions=[
            "Start the agent with 'tx run {agent_name}'",
            "Check agent status with 'tx status'",
        ],
    ),
    "not_authenticated": CortexError(
        message="You are not signed in to Sentinel",
        category=ErrorCategory.AUTHENTICATION,
        suggestions=[
            "Sign in with 'tx login'",
            "Check your credentials",
        ],
    ),
    "network_error": CortexError(
        message="Could not connect to the network",
        category=ErrorCategory.NETWORK,
        suggestions=[
            "Check your internet connection",
            "Verify the service is running",
            "Try again in a few moments",
        ],
    ),
    "switchai_unavailable": CortexError(
        message="SwitchAILocal is not available",
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.WARNING,
        suggestions=[
            "Start SwitchAILocal: 'switchai start'",
            "Cortex will use pattern matching as fallback",
        ],
        recoverable=True,
    ),
    "config_invalid": CortexError(
        message="Configuration file is invalid",
        category=ErrorCategory.CONFIG,
        suggestions=[
            "Run 'tx validate' to check your config",
            "Check the config file syntax",
        ],
    ),
    "permission_denied": CortexError(
        message="Permission denied for this operation",
        category=ErrorCategory.PERMISSION,
        suggestions=[
            "Check your authentication status with 'tx whoami'",
            "Ensure you have the required permissions",
        ],
    ),
    "ambiguous_command": CortexError(
        message="I'm not sure what you meant",
        category=ErrorCategory.USER_INPUT,
        severity=ErrorSeverity.WARNING,
        suggestions=[
            "Try being more specific",
            "Use '/help' to see available commands",
        ],
        recoverable=True,
    ),
}


def create_error(
    template_name: str,
    **kwargs: Any,
) -> CortexError:
    """Create an error from a template.

    Args:
        template_name: Name of the error template
        **kwargs: Values to substitute in the template

    Returns:
        CortexError instance
    """
    if template_name not in ERROR_TEMPLATES:
        return CortexError(
            message=f"Unknown error: {template_name}",
            category=ErrorCategory.INTERNAL,
        )

    template = ERROR_TEMPLATES[template_name]

    # Substitute values in message
    message = template.message.format(**kwargs)

    # Substitute values in suggestions
    suggestions = [s.format(**kwargs) for s in template.suggestions]

    return CortexError(
        message=message,
        category=template.category,
        severity=template.severity,
        code=template_name,
        suggestions=suggestions,
        details=kwargs,
        recoverable=template.recoverable,
    )


class ErrorHandler:
    """Handles errors with recovery strategies."""

    def __init__(self) -> None:
        """Initialize error handler."""
        self._history: list[CortexError] = []

    def handle(self, error: CortexError) -> str:
        """Handle an error and return user message.

        Args:
            error: Error to handle

        Returns:
            User-friendly message
        """
        self._history.append(error)
        return error.format_for_user()

    def handle_exception(self, exc: Exception) -> str:
        """Convert exception to CortexError and handle.

        Args:
            exc: Exception to handle

        Returns:
            User-friendly message
        """
        # Map common exceptions to errors
        if isinstance(exc, ConnectionError):
            error = create_error("network_error")
        elif isinstance(exc, PermissionError):
            error = create_error("permission_denied")
        elif isinstance(exc, FileNotFoundError):
            error = CortexError(
                message=f"File not found: {exc}",
                category=ErrorCategory.CONFIG,
                suggestions=["Check the file path"],
            )
        else:
            error = CortexError(
                message=str(exc),
                category=ErrorCategory.INTERNAL,
                details={"exception_type": type(exc).__name__},
            )

        return self.handle(error)

    def get_recent_errors(self, count: int = 5) -> list[CortexError]:
        """Get recent errors.

        Args:
            count: Number of errors to return

        Returns:
            List of recent errors
        """
        return self._history[-count:]

    def clear_history(self) -> None:
        """Clear error history."""
        self._history.clear()
