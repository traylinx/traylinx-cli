"""Command executor using subprocess.

Executes Traylinx CLI commands via subprocess, handling:
- Argument building from Intent
- Timeout management
- Output capture
- Error handling
"""

import subprocess
import time
from pathlib import Path
from typing import Any

from traylinx.cortex.types import Intent, ExecutionResult, ConfirmationLevel
from traylinx.cortex.executor.confirmation import (
    get_confirmation,
    get_command_description,
)
from traylinx.cortex.executor.formatters import (
    display_executing,
    format_command_output,
    display_result,
    ResultType,
)
from traylinx.cortex.config import load_config


class CommandExecutor:
    """Executes CLI commands via subprocess.

    Handles the full execution lifecycle:
    1. Build command arguments
    2. Check for confirmation
    3. Execute via subprocess
    4. Capture and format output
    """

    def __init__(self, timeout: int = 300, show_commands: bool = True):
        """Initialize executor.

        Args:
            timeout: Command timeout in seconds
            show_commands: Whether to display commands before execution
        """
        config = load_config()
        self.timeout = timeout or config.execution.timeout
        self.show_commands = show_commands if show_commands is not None else config.execution.show_commands
        self._tx_path = self._find_tx()

    def _find_tx(self) -> str:
        """Find the tx executable path."""
        # Try to find tx in PATH
        import shutil

        tx_path = shutil.which("tx")
        if tx_path:
            return tx_path

        # Try traylinx as fallback
        traylinx_path = shutil.which("traylinx")
        if traylinx_path:
            return traylinx_path

        # Default to tx (will fail at execution if not found)
        return "tx"

    def build_command_args(self, intent: Intent) -> list[str]:
        """Build command line arguments from intent.

        Args:
            intent: Classified intent with command and parameters

        Returns:
            List of command arguments
        """
        if not intent.command:
            return []

        args = [self._tx_path, intent.command]

        # Add parameters as flags
        for key, value in intent.parameters.items():
            if isinstance(value, bool) and value:
                # Boolean flag
                args.append(key if key.startswith("--") else f"--{key}")
            elif value is not None:
                # Key-value parameter
                flag = key if key.startswith("--") else f"--{key}"
                args.extend([flag, str(value)])

        return args

    def execute(self, intent: Intent) -> ExecutionResult:
        """Execute a command from an intent.

        Args:
            intent: Classified intent to execute

        Returns:
            ExecutionResult with output and status
        """
        if not intent.command or intent.command in ("help", "exit", "clear", "history", "undo"):
            # Special commands handled by REPL, not subprocess
            return ExecutionResult(
                success=True,
                command=intent.command or "",
                formatted_output=f"Special command: {intent.command}",
            )

        # Build command
        args = self.build_command_args(intent)
        command_str = " ".join(args)

        # Check confirmation
        if intent.requires_confirmation:
            description = get_command_description(intent.command)
            if not get_confirmation(command_str, intent.confirmation_level, description):
                return ExecutionResult(
                    success=False,
                    command=command_str,
                    exit_code=-1,
                    formatted_output="[yellow]Cancelled by user[/yellow]",
                )

        # Display 'executing' message
        if self.show_commands:
            display_executing(intent.command)

        # Execute
        start_time = time.time()
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=Path.cwd(),
            )
            duration_ms = int((time.time() - start_time) * 1000)

            # Format output
            formatted = format_command_output(
                command_str,
                result.stdout,
                result.stderr,
                result.returncode,
                duration_ms,
            )

            # Generate suggestions based on result
            suggestions = self._generate_suggestions(intent.command, result.returncode)

            return ExecutionResult(
                success=result.returncode == 0,
                command=command_str,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration_ms=duration_ms,
                suggestions=suggestions,
                formatted_output=formatted,
            )

        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                command=command_str,
                exit_code=-1,
                duration_ms=duration_ms,
                formatted_output=f"[red]Command timed out after {self.timeout}s[/red]",
                suggestions=["Try running with a longer timeout", "Check if the agent is responding"],
            )

        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                command=command_str,
                exit_code=-1,
                formatted_output="[red]Error: tx command not found[/red]",
                suggestions=[
                    "Make sure traylinx-cli is installed",
                    "Run: pip install traylinx-cli",
                ],
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                command=command_str,
                exit_code=-1,
                formatted_output=f"[red]Error: {e}[/red]",
            )

    def _generate_suggestions(self, command: str, exit_code: int) -> list[str]:
        """Generate contextual suggestions based on command result.

        Args:
            command: Executed command
            exit_code: Exit code from execution

        Returns:
            List of suggested next actions
        """
        if exit_code != 0:
            # Error suggestions
            return [
                "Check the error message above",
                "Run with --verbose for more details",
                f"Run 'tx {command} --help' for usage",
            ]

        # Success suggestions per command
        suggestions_map = {
            "run": ["View logs: 'show logs'", "Check status: 'status'", "Stop agent: 'stop'"],
            "stop": ["Restart: 'start agent'", "View final logs: 'logs'"],
            "discover": ["Call an agent: 'call <peer_id>'"],
            "login": ["Check identity: 'whoami'", "List agents: 'discover'"],
            "build": ["Validate: 'validate'", "Publish: 'publish'"],
            "validate": ["Fix issues if any", "Build: 'build'", "Publish: 'publish'"],
        }

        return suggestions_map.get(command, [])

    def execute_raw(self, command: str) -> ExecutionResult:
        """Execute a raw command string.

        Args:
            command: Full command string (e.g., "tx run --detach")

        Returns:
            ExecutionResult
        """
        args = command.split()

        start_time = time.time()
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=Path.cwd(),
            )
            duration_ms = int((time.time() - start_time) * 1000)

            formatted = format_command_output(
                command,
                result.stdout,
                result.stderr,
                result.returncode,
                duration_ms,
            )

            return ExecutionResult(
                success=result.returncode == 0,
                command=command,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration_ms=duration_ms,
                formatted_output=formatted,
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                command=command,
                exit_code=-1,
                formatted_output=f"[red]Error: {e}[/red]",
            )
