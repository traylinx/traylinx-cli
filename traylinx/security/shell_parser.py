"""Shell command parser for security validation.

Uses shlex for tokenization and pattern matching to detect
dangerous command patterns that could indicate command injection.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class ParsedCommand:
    """Represents a parsed shell command."""

    executable: str
    args: list[str] = field(default_factory=list)
    subcommands: list[ParsedCommand] = field(default_factory=list)
    has_pipe: bool = False
    has_redirect: bool = False
    has_background: bool = False
    raw_command: str = ""


# Dangerous command patterns that should be blocked
DENY_PATTERNS: list[tuple[str, str]] = [
    # Destructive file operations
    (r"rm\s+(-[rRf]+\s+|--recursive\s+|--force\s+)*(/|~|\$HOME)", "Recursive delete of root/home"),
    (r"rm\s+-[rRf]*\s+\*", "Wildcard recursive delete"),
    # Remote code execution
    (r"curl\s+.*\|\s*(ba)?sh", "Remote script execution via curl"),
    (r"wget\s+.*\|\s*(ba)?sh", "Remote script execution via wget"),
    (r"curl\s+.*-o\s+/tmp/.*&&.*sh", "Download and execute pattern"),
    # System damage
    (r"dd\s+if=.*of=/dev/sd[a-z]", "Direct disk write"),
    (r":\(\)\s*{\s*:\s*\|\s*:\s*&\s*}\s*;", "Fork bomb"),
    (r"mkfs\.", "Filesystem format"),
    (r">\s*/dev/sd[a-z]", "Direct device write"),
    # Permission issues
    (r"chmod\s+(-R\s+)?777\s+/", "Overly permissive chmod on root"),
    (r"chown\s+(-R\s+)?.*\s+/", "Chown on root"),
    # Sensitive file access
    (r"cat\s+(/etc/shadow|/etc/passwd)", "Sensitive file read"),
    (r">\s*~?/.ssh/", "SSH key modification"),
    # Network exfiltration patterns
    (r"nc\s+-[e]", "Netcat with execute"),
    (r"/dev/tcp/", "Bash TCP device"),
    # Privilege escalation
    (r"sudo\s+su\s*$", "Privilege escalation"),
    (r"sudo\s+-i\s*$", "Interactive sudo"),
]

# Commands that require additional scrutiny
WARN_PATTERNS: list[tuple[str, str]] = [
    (r"eval\s+", "Dynamic code evaluation"),
    (r"exec\s+", "Process replacement"),
    (r"\$\(.*\)", "Command substitution"),
    (r"`.*`", "Backtick command substitution"),
    (r"source\s+", "Script sourcing"),
    (r"\.\s+/", "Dot sourcing"),
]

# Operators that chain commands
CHAIN_OPERATORS = ["&&", "||", ";", "|", "&"]


class ShellParser:
    """Parser for shell commands with security validation."""

    def __init__(self, custom_deny_patterns: list[tuple[str, str]] | None = None):
        """Initialize parser with optional custom deny patterns."""
        self.deny_patterns = DENY_PATTERNS.copy()
        if custom_deny_patterns:
            self.deny_patterns.extend(custom_deny_patterns)

    def parse(self, command: str) -> ParsedCommand:
        """Parse a shell command into a structured representation.

        Args:
            command: Raw shell command string

        Returns:
            ParsedCommand with executable, args, and metadata
        """
        command = command.strip()

        # Detect operators
        has_pipe = "|" in command and "||" not in command.replace("||", "")
        has_redirect = any(op in command for op in [">", "<", ">>", "2>", "&>"])
        has_background = command.endswith("&") or " & " in command

        # Split on chain operators to get subcommands
        subcommands = self._split_chain(command)

        # Parse the first command
        if subcommands:
            first_cmd = subcommands[0]
            try:
                tokens = shlex.split(first_cmd)
            except ValueError:
                # Handle malformed commands
                tokens = first_cmd.split()

            executable = tokens[0] if tokens else ""
            args = tokens[1:] if len(tokens) > 1 else []

            # Parse remaining subcommands recursively
            parsed_subcommands = []
            for sub in subcommands[1:]:
                sub = sub.strip()
                if sub:
                    parsed_subcommands.append(self.parse(sub))

            return ParsedCommand(
                executable=executable,
                args=args,
                subcommands=parsed_subcommands,
                has_pipe=has_pipe,
                has_redirect=has_redirect,
                has_background=has_background,
                raw_command=command,
            )

        return ParsedCommand(executable="", raw_command=command)

    def _split_chain(self, command: str) -> list[str]:
        """Split command on chain operators while respecting quotes."""
        result = []
        current = []
        in_quotes = False
        quote_char = None
        i = 0

        while i < len(command):
            char = command[i]

            # Handle quotes
            if char in "\"'" and (i == 0 or command[i - 1] != "\\"):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
                current.append(char)
                i += 1
                continue

            # Check for chain operators (only outside quotes)
            if not in_quotes:
                found_op = False
                for op in sorted(CHAIN_OPERATORS, key=len, reverse=True):
                    if command[i : i + len(op)] == op:
                        if current:
                            result.append("".join(current).strip())
                            current = []
                        i += len(op)
                        found_op = True
                        break
                if found_op:
                    continue

            current.append(char)
            i += 1

        if current:
            result.append("".join(current).strip())

        return result

    def get_all_executables(self, cmd: ParsedCommand) -> list[str]:
        """Recursively extract all executables from command chain.

        Args:
            cmd: ParsedCommand to analyze

        Returns:
            List of all executable names in the command chain
        """
        executables = []
        if cmd.executable:
            executables.append(cmd.executable)
        for sub in cmd.subcommands:
            executables.extend(self.get_all_executables(sub))
        return executables

    def check_deny_patterns(self, command: str) -> list[tuple[str, str]]:
        """Check command against known dangerous patterns.

        Args:
            command: Raw command string to check

        Returns:
            List of (pattern, reason) tuples for matched patterns
        """
        matches = []
        for pattern, reason in self.deny_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                matches.append((pattern, reason))
        return matches

    def check_warn_patterns(self, command: str) -> list[tuple[str, str]]:
        """Check command against patterns that warrant user confirmation.

        Args:
            command: Raw command string to check

        Returns:
            List of (pattern, reason) tuples for matched patterns
        """
        matches = []
        for pattern, reason in WARN_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                matches.append((pattern, reason))
        return matches

    def is_safe(self, command: str) -> tuple[bool, str]:
        """Quick safety check for a command.

        Args:
            command: Raw command string to check

        Returns:
            Tuple of (is_safe, reason_if_not_safe)
        """
        # Check deny patterns
        deny_matches = self.check_deny_patterns(command)
        if deny_matches:
            return False, f"Blocked: {deny_matches[0][1]}"

        # Parse and validate structure
        try:
            parsed = self.parse(command)

            # Check for suspicious patterns in parsed command
            executables = self.get_all_executables(parsed)

            # Block if any dangerous executable is chained
            dangerous_execs = {"rm", "dd", "mkfs", "fdisk", "parted"}
            for exe in executables:
                if exe in dangerous_execs and len(executables) > 1:
                    return False, f"Dangerous command '{exe}' in chain"

        except Exception as e:
            return False, f"Parse error: {e}"

        return True, ""
