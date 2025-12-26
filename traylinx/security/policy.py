"""Main Policy Engine for Traylinx CLI security.

This module orchestrates all security checks including:
- Shell command validation
- File path validation
- Docker operation security
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from .docker_safeguards import DockerSafeguards
from .path_validator import PathValidator
from .shell_parser import ShellParser

if TYPE_CHECKING:
    pass


class PolicyDecision(Enum):
    """Security policy decision."""

    ALLOW = "allow"
    DENY = "deny"
    ASK_USER = "ask_user"


@dataclass
class PolicyResult:
    """Result of a policy check."""

    decision: PolicyDecision
    reason: str
    matched_pattern: str | None = None
    suggestions: list[str] | None = None


class PolicyEngine:
    """Central security policy engine for Traylinx CLI.

    Orchestrates all security checks including command validation,
    path traversal prevention, and Docker safeguards.
    """

    def __init__(
        self,
        workdir: Path,
        config: dict | None = None,
        interactive: bool = True,
    ):
        """Initialize the PolicyEngine.

        Args:
            workdir: Base directory for allowed operations
            config: Optional configuration overrides
            interactive: Whether to allow ASK_USER decisions
        """
        self.workdir = workdir.resolve()
        self.config = config or {}
        self.interactive = interactive

        # Initialize sub-components
        self.shell_parser = ShellParser(
            custom_deny_patterns=self.config.get("custom_deny_patterns")
        )
        self.path_validator = PathValidator(
            workdir=self.workdir,
            allowed_paths=self.config.get("allowed_paths"),
        )
        self.docker_safeguards = DockerSafeguards(
            trusted_registries=self.config.get("trusted_registries"),
        )

    def check_shell_command(self, command: str) -> PolicyResult:
        """Check if a shell command is safe to execute.

        Args:
            command: Raw shell command string

        Returns:
            PolicyResult with decision and reason
        """
        # Check deny patterns first
        deny_matches = self.shell_parser.check_deny_patterns(command)
        if deny_matches:
            pattern, reason = deny_matches[0]
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=reason,
                matched_pattern=pattern,
            )

        # Check warn patterns (require confirmation)
        warn_matches = self.shell_parser.check_warn_patterns(command)
        if warn_matches and self.interactive:
            pattern, reason = warn_matches[0]
            return PolicyResult(
                decision=PolicyDecision.ASK_USER,
                reason=f"Potentially dangerous: {reason}",
                matched_pattern=pattern,
            )

        # Parse and validate structure
        try:
            parsed = self.shell_parser.parse(command)
            executables = self.shell_parser.get_all_executables(parsed)

            # Block dangerous chained commands
            dangerous = {"rm", "dd", "mkfs", "fdisk", "parted", "sudo"}
            for exe in executables:
                if exe in dangerous and len(executables) > 1:
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason=f"Dangerous command '{exe}' in command chain",
                    )

        except Exception as e:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Command parse error: {e}",
            )

        # Check for paths in command args
        for arg in parsed.args:
            if arg.startswith("/") or arg.startswith("~") or ".." in arg:
                is_valid, err = self.path_validator.validate(arg)
                if not is_valid:
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason=f"Path validation failed: {err}",
                    )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Command passed all security checks",
        )

    def check_file_operation(
        self,
        operation: str,
        path: Path | str,
    ) -> PolicyResult:
        """Check if a file operation is safe.

        Args:
            operation: Operation type (read, write, delete, etc.)
            path: Target file path

        Returns:
            PolicyResult with decision and reason
        """
        is_valid, error = self.path_validator.validate(path)

        if not is_valid:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Path validation failed: {error}",
            )

        # Require confirmation for delete operations
        if operation.lower() in ("delete", "rm", "remove") and self.interactive:
            return PolicyResult(
                decision=PolicyDecision.ASK_USER,
                reason=f"Confirm deletion of: {path}",
            )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason=f"File operation '{operation}' allowed",
        )

    def check_docker_pull(self, image: str) -> PolicyResult:
        """Check if a Docker image pull is safe.

        Args:
            image: Docker image reference

        Returns:
            PolicyResult with decision and reason
        """
        result = self.docker_safeguards.verify_image(image)

        if result.is_trusted:
            return PolicyResult(
                decision=PolicyDecision.ALLOW,
                reason=f"Image from trusted registry: {result.registry}",
            )

        # Untrusted images require confirmation in interactive mode
        if self.interactive:
            return PolicyResult(
                decision=PolicyDecision.ASK_USER,
                reason=result.reason,
                suggestions=[
                    "Use an official image from ghcr.io/traylinx/",
                    "Add the registry to trusted_registries in config",
                ],
            )

        return PolicyResult(
            decision=PolicyDecision.DENY,
            reason=result.reason,
        )

    def check_docker_compose(self, compose_config: dict) -> PolicyResult:
        """Check if a docker-compose configuration is secure.

        Args:
            compose_config: Parsed docker-compose configuration

        Returns:
            PolicyResult with decision and warnings
        """
        warnings = self.docker_safeguards.validate_compose_config(compose_config)

        if not warnings:
            return PolicyResult(
                decision=PolicyDecision.ALLOW,
                reason="Compose configuration passed security checks",
            )

        # Warnings require confirmation
        if self.interactive:
            return PolicyResult(
                decision=PolicyDecision.ASK_USER,
                reason="Security warnings found in compose configuration",
                suggestions=warnings,
            )

        return PolicyResult(
            decision=PolicyDecision.DENY,
            reason=f"Security issues: {'; '.join(warnings)}",
        )

    def is_allowed(self, result: PolicyResult) -> bool:
        """Quick check if a PolicyResult allows the action.

        Args:
            result: PolicyResult to check

        Returns:
            True if decision is ALLOW
        """
        return result.decision == PolicyDecision.ALLOW

    def requires_confirmation(self, result: PolicyResult) -> bool:
        """Check if a PolicyResult requires user confirmation.

        Args:
            result: PolicyResult to check

        Returns:
            True if decision is ASK_USER
        """
        return result.decision == PolicyDecision.ASK_USER
