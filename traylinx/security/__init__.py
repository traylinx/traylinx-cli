"""Security module for Traylinx CLI.

This module provides enterprise-grade security features:
- Shell command parsing and injection prevention
- Path traversal validation
- Docker safeguards (image verification, resource limits)
"""

from .policy import PolicyDecision, PolicyEngine, PolicyResult
from .shell_parser import ParsedCommand, ShellParser
from .path_validator import PathValidator, is_path_safe, validate_path
from .docker_safeguards import DockerSafeguards

__all__ = [
    # Policy Engine
    "PolicyEngine",
    "PolicyDecision",
    "PolicyResult",
    # Shell Parser
    "ShellParser",
    "ParsedCommand",
    # Path Validator
    "PathValidator",
    "validate_path",
    "is_path_safe",
    # Docker Safeguards
    "DockerSafeguards",
]
