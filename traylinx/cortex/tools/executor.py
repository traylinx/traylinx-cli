"""Tool executor for running OpenAI-style tool calls.

Handles:
- Parsing tool calls from LLM responses
- Validating parameters against tool schemas
- Executing tools via CLI CommandExecutor
- Tool chaining (multiple sequential tools)
"""

import json
from dataclasses import dataclass, field
from typing import Any

from traylinx.cortex.types import Intent, IntentType, ConfirmationLevel, ExecutionResult
from traylinx.cortex.executor.executor import CommandExecutor
from traylinx.cortex.tools.definitions import (
    TOOL_DEFINITIONS,
    TOOL_TO_COMMAND,
    get_tool_by_name,
)


@dataclass
class ToolCall:
    """A parsed tool call from LLM response."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolChain:
    """A chain of tools to execute sequentially."""

    calls: list[ToolCall] = field(default_factory=list)
    current_index: int = 0
    results: list[ExecutionResult] = field(default_factory=list)

    def add(self, call: ToolCall) -> None:
        """Add a tool call to the chain."""
        self.calls.append(call)

    def is_complete(self) -> bool:
        """Check if all tools have been executed."""
        return self.current_index >= len(self.calls)

    def next(self) -> ToolCall | None:
        """Get the next tool to execute."""
        if self.is_complete():
            return None
        call = self.calls[self.current_index]
        self.current_index += 1
        return call

    def add_result(self, result: ExecutionResult) -> None:
        """Record a tool execution result."""
        self.results.append(result)


class ToolExecutor:
    """Executes tool calls from LLM responses.

    Handles parameter validation, tool execution via CLI,
    and chained tool execution.
    """

    # Commands that require confirmation
    CONFIRMATION_REQUIRED = {"stop", "logout", "publish"}

    # Commands that are high risk (HARD confirmation)
    HIGH_RISK_COMMANDS = {"logout", "publish"}

    def __init__(self, command_executor: CommandExecutor | None = None):
        """Initialize tool executor.

        Args:
            command_executor: Optional CLI executor (creates default if not provided)
        """
        self._executor = command_executor or CommandExecutor()
        self._current_chain: ToolChain | None = None

    def parse_tool_calls(self, response: dict[str, Any]) -> list[ToolCall]:
        """Parse tool calls from an OpenAI API response.

        Args:
            response: OpenAI chat completion response

        Returns:
            List of parsed tool calls
        """
        calls: list[ToolCall] = []

        # Check for tool_calls in response
        message = response.get("choices", [{}])[0].get("message", {})
        tool_calls = message.get("tool_calls", [])

        for tc in tool_calls:
            if tc.get("type") != "function":
                continue

            function = tc.get("function", {})
            name = function.get("name", "")
            args_str = function.get("arguments", "{}")

            try:
                arguments = json.loads(args_str)
            except json.JSONDecodeError:
                arguments = {}

            calls.append(
                ToolCall(
                    id=tc.get("id", ""),
                    name=name,
                    arguments=arguments,
                )
            )

        return calls

    def validate_tool_call(self, call: ToolCall) -> tuple[bool, str]:
        """Validate a tool call against its schema.

        Args:
            call: Tool call to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        tool_def = get_tool_by_name(call.name)
        if not tool_def:
            return False, f"Unknown tool: {call.name}"

        schema = tool_def["function"]["parameters"]
        required = schema.get("required", [])

        # Check required parameters
        for param in required:
            if param not in call.arguments:
                return False, f"Missing required parameter: {param}"

        # Check parameter types (basic validation)
        properties = schema.get("properties", {})
        for key, value in call.arguments.items():
            if key not in properties:
                continue  # Allow extra arguments

            expected_type = properties[key].get("type")
            if expected_type == "string" and not isinstance(value, str):
                return False, f"Parameter '{key}' must be a string"
            elif expected_type == "integer" and not isinstance(value, int):
                return False, f"Parameter '{key}' must be an integer"
            elif expected_type == "boolean" and not isinstance(value, bool):
                return False, f"Parameter '{key}' must be a boolean"
            elif expected_type == "object" and not isinstance(value, dict):
                return False, f"Parameter '{key}' must be an object"

        return True, ""

    def to_intent(self, call: ToolCall) -> Intent:
        """Convert a tool call to an Intent for execution.

        Args:
            call: Tool call to convert

        Returns:
            Intent for CLI execution
        """
        command = TOOL_TO_COMMAND.get(call.name)

        # Determine confirmation level
        if command in self.HIGH_RISK_COMMANDS:
            conf_level = ConfirmationLevel.HARD
            requires_conf = True
        elif command in self.CONFIRMATION_REQUIRED:
            conf_level = ConfirmationLevel.SOFT
            requires_conf = True
        else:
            conf_level = ConfirmationLevel.NONE
            requires_conf = False

        return Intent(
            type=IntentType.CLI_COMMAND,
            command=command,
            parameters=call.arguments,
            confidence=1.0,  # Tool calls are explicit
            requires_confirmation=requires_conf,
            confirmation_level=conf_level,
            raw_input=f"tool:{call.name}",
        )

    def execute(self, call: ToolCall) -> ExecutionResult:
        """Execute a single tool call.

        Args:
            call: Tool call to execute

        Returns:
            Execution result
        """
        # Validate first
        valid, error = self.validate_tool_call(call)
        if not valid:
            return ExecutionResult(
                success=False,
                command=call.name,
                stderr=error,
                exit_code=1,
                formatted_output=f"[red]❌ Validation error: {error}[/red]",
            )

        # Convert to intent and execute
        intent = self.to_intent(call)
        return self._executor.execute(intent)

    def execute_chain(self, calls: list[ToolCall]) -> list[ExecutionResult]:
        """Execute a chain of tool calls sequentially.

        Useful for commands like "start my agent and show logs"
        which translates to [traylinx_run, traylinx_logs].

        Args:
            calls: List of tool calls to execute

        Returns:
            List of execution results
        """
        self._current_chain = ToolChain(calls=calls)
        results: list[ExecutionResult] = []

        while not self._current_chain.is_complete():
            call = self._current_chain.next()
            if call is None:
                break

            result = self.execute(call)
            results.append(result)
            self._current_chain.add_result(result)

            # Stop chain on error unless it's a non-critical failure
            if not result.success and result.exit_code != 0:
                break

        self._current_chain = None
        return results

    def get_tool_result_message(self, call: ToolCall, result: ExecutionResult) -> dict[str, Any]:
        """Format a tool result for sending back to the LLM.

        Args:
            call: Original tool call
            result: Execution result

        Returns:
            Tool result message in OpenAI format
        """
        content = {
            "success": result.success,
            "exit_code": result.exit_code,
            "output": result.stdout[:1000] if result.stdout else "",
        }

        if result.stderr:
            content["error"] = result.stderr[:500]

        if result.suggestions:
            content["suggestions"] = result.suggestions

        return {
            "role": "tool",
            "tool_call_id": call.id,
            "content": json.dumps(content),
        }


def parse_chained_command(text: str) -> list[str]:
    """Parse a chained command request into individual commands.

    Examples:
        "start my agent and show logs" -> ["run", "logs"]
        "stop it then start again" -> ["stop", "run"]

    Args:
        text: User input with chained commands

    Returns:
        List of command names
    """
    import re

    # Split by common conjunctions
    parts = re.split(r'\b(?:and|then|also|after that)\b', text.lower())
    commands: list[str] = []

    # Command keywords
    COMMAND_KEYWORDS = {
        "start": "run",
        "run": "run",
        "launch": "run",
        "stop": "stop",
        "kill": "stop",
        "halt": "stop",
        "logs": "logs",
        "show logs": "logs",
        "tail": "logs",
        "status": "status",
        "check": "status",
        "find": "discover",
        "discover": "discover",
        "search": "discover",
        "call": "call",
        "build": "build",
        "compile": "build",
    }

    for part in parts:
        part = part.strip()
        for keyword, cmd in COMMAND_KEYWORDS.items():
            if keyword in part:
                commands.append(cmd)
                break

    return commands
