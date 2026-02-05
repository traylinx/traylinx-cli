"""Core type definitions for Traylinx Cortex.

This module defines all data types used throughout the plugin:
- Intent classification results
- Session and message structures
- Command execution tracking
- Context management
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class IntentType(str, Enum):
    """Classification of user intent."""

    CLI_COMMAND = "cli_command"
    INFORMATION_REQUEST = "information_request"
    CONVERSATION = "conversation"
    AMBIGUOUS = "ambiguous"


class MessageRole(str, Enum):
    """Message role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ExecutionStatus(str, Enum):
    """Status of command execution."""

    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ConfirmationLevel(str, Enum):
    """Confirmation requirement level."""

    NONE = "none"  # No confirmation (read operations)
    SOFT = "soft"  # Show command, auto-proceed after delay
    HARD = "hard"  # Require explicit yes/no


# =============================================================================
# Intent Classification
# =============================================================================


class Intent(BaseModel):
    """Result of intent classification.

    Represents the parsed user intent including the detected command,
    extracted parameters, confidence score, and any missing context.
    """

    type: IntentType = Field(description="Classification category")
    command: str | None = Field(default=None, description="Mapped CLI command (e.g., 'run', 'logs')")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Extracted parameters")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Classification confidence")
    requires_confirmation: bool = Field(default=False, description="Whether command needs user confirmation")
    confirmation_level: ConfirmationLevel = Field(default=ConfirmationLevel.NONE)
    context_needed: list[str] = Field(default_factory=list, description="Missing context that requires clarification")
    raw_input: str = Field(default="", description="Original user input")


# =============================================================================
# Session & Messages
# =============================================================================


class Message(BaseModel):
    """A single message in the conversation history."""

    id: UUID
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommandExecution(BaseModel):
    """Record of a CLI command execution."""

    id: UUID
    command: str = Field(description="Full CLI command (e.g., 'tx run --detach')")
    parameters: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    status: ExecutionStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_ms: int = Field(default=0, ge=0)
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    exit_code: int = Field(default=0)


class Context(BaseModel):
    """Accumulated context for the current session.

    Built from system state and conversation history to inform
    intent classification and response generation.
    """

    current_directory: str = Field(default="")
    authenticated: bool = Field(default=False)
    running_agents: list[str] = Field(default_factory=list)
    last_command: str | None = Field(default=None)
    recent_results: list[dict[str, Any]] = Field(default_factory=list)
    user_preferences: dict[str, Any] = Field(default_factory=dict)


class Session(BaseModel):
    """A conversation session with history and context."""

    id: UUID
    user_id: str = Field(default="default")
    started_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    conversation_history: list[Message] = Field(default_factory=list)
    command_history: list[CommandExecution] = Field(default_factory=list)
    context: Context = Field(default_factory=Context)


# =============================================================================
# Execution Results
# =============================================================================


class ExecutionResult(BaseModel):
    """Result of executing a CLI command.

    Contains the outcome, output, and any suggestions for next actions.
    """

    success: bool
    command: str = Field(description="The exact command that was executed")
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    exit_code: int = Field(default=0)
    duration_ms: int = Field(default=0)
    suggestions: list[str] = Field(default_factory=list, description="Suggested next actions")
    formatted_output: str = Field(default="", description="Rich-formatted output for display")
