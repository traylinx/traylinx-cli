"""Command chaining execution with DAG support.

Handles sequential and parallel execution of multiple commands:
- "start my agent and show logs" → run, then logs
- "build and run" → build, then run
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import asyncio

from traylinx.cortex.types import Intent, IntentType, ExecutionResult


class ChainStatus(str, Enum):
    """Status of a command chain."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ChainNode:
    """A node in the command execution DAG."""

    id: str
    command: str
    parameters: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)  # IDs of dependency nodes
    status: ChainStatus = ChainStatus.PENDING
    result: ExecutionResult | None = None


@dataclass
class ExecutionChain:
    """A DAG of commands to execute.

    Supports:
    - Sequential execution (A → B → C)
    - Parallel execution (A, B in parallel → C)
    - Dependency-based ordering
    """

    nodes: dict[str, ChainNode] = field(default_factory=dict)
    execution_order: list[str] = field(default_factory=list)

    def add_node(
        self,
        node_id: str,
        command: str,
        parameters: dict[str, Any] | None = None,
        depends_on: list[str] | None = None,
    ) -> ChainNode:
        """Add a node to the chain.

        Args:
            node_id: Unique identifier for the node
            command: CLI command to execute
            parameters: Command parameters
            depends_on: IDs of nodes that must complete first

        Returns:
            Created ChainNode
        """
        node = ChainNode(
            id=node_id,
            command=command,
            parameters=parameters or {},
            depends_on=depends_on or [],
        )
        self.nodes[node_id] = node
        return node

    def add_sequential(self, commands: list[tuple[str, dict[str, Any] | None]]) -> None:
        """Add commands to execute sequentially.

        Args:
            commands: List of (command, parameters) tuples
        """
        prev_id: str | None = None

        for i, (command, params) in enumerate(commands):
            node_id = f"step_{i}"
            depends = [prev_id] if prev_id else []
            self.add_node(node_id, command, params, depends)
            prev_id = node_id

    def get_ready_nodes(self) -> list[ChainNode]:
        """Get nodes that are ready to execute.

        A node is ready if:
        - Status is PENDING
        - All dependencies are COMPLETED

        Returns:
            List of ready nodes
        """
        ready: list[ChainNode] = []

        for node in self.nodes.values():
            if node.status != ChainStatus.PENDING:
                continue

            # Check if all dependencies are complete
            deps_complete = all(
                self.nodes[dep_id].status == ChainStatus.COMPLETED
                for dep_id in node.depends_on
                if dep_id in self.nodes
            )

            if deps_complete:
                ready.append(node)

        return ready

    def mark_running(self, node_id: str) -> None:
        """Mark a node as running."""
        if node_id in self.nodes:
            self.nodes[node_id].status = ChainStatus.RUNNING

    def mark_completed(self, node_id: str, result: ExecutionResult) -> None:
        """Mark a node as completed."""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.status = ChainStatus.COMPLETED
            node.result = result
            self.execution_order.append(node_id)

    def mark_failed(self, node_id: str, result: ExecutionResult) -> None:
        """Mark a node as failed."""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.status = ChainStatus.FAILED
            node.result = result

    def is_complete(self) -> bool:
        """Check if the entire chain is complete."""
        return all(
            node.status in (ChainStatus.COMPLETED, ChainStatus.FAILED, ChainStatus.CANCELLED)
            for node in self.nodes.values()
        )

    def has_failed(self) -> bool:
        """Check if any node has failed."""
        return any(node.status == ChainStatus.FAILED for node in self.nodes.values())

    def get_results(self) -> list[ExecutionResult]:
        """Get all execution results in order."""
        return [
            self.nodes[node_id].result
            for node_id in self.execution_order
            if self.nodes[node_id].result is not None
        ]


class ChainExecutor:
    """Executes command chains with proper dependency handling."""

    def __init__(self, command_executor: Any):
        """Initialize chain executor.

        Args:
            command_executor: CommandExecutor instance
        """
        self._executor = command_executor

    def execute_sync(self, chain: ExecutionChain) -> list[ExecutionResult]:
        """Execute chain synchronously.

        Args:
            chain: ExecutionChain to execute

        Returns:
            List of execution results
        """
        results: list[ExecutionResult] = []

        while not chain.is_complete():
            ready = chain.get_ready_nodes()

            if not ready:
                # No nodes ready - either complete or deadlocked
                break

            # Execute ready nodes (sequentially for sync execution)
            for node in ready:
                chain.mark_running(node.id)

                intent = Intent(
                    type=IntentType.CLI_COMMAND,
                    command=node.command,
                    parameters=node.parameters,
                    confidence=1.0,
                    raw_input=f"chain:{node.command}",
                )

                result = self._executor.execute(intent)
                results.append(result)

                if result.success:
                    chain.mark_completed(node.id, result)
                else:
                    chain.mark_failed(node.id, result)
                    # Stop on first failure
                    return results

        return results


def parse_chain_from_text(text: str) -> list[tuple[str, dict[str, Any] | None]]:
    """Parse a chained command from natural language.

    Args:
        text: User input like "start my agent and show logs"

    Returns:
        List of (command, parameters) tuples
    """
    import re

    # Split by conjunctions
    parts = re.split(r'\b(?:and|then|also|after that|,)\b', text.lower())
    commands: list[tuple[str, dict[str, Any] | None]] = []

    # Command extraction patterns
    COMMAND_PATTERNS: dict[str, str] = {
        r"\b(?:start|run|launch)\b": "run",
        r"\b(?:stop|kill|halt)\b": "stop",
        r"\b(?:logs?|tail|show\s+logs?)\b": "logs",
        r"\b(?:status|check)\b": "status",
        r"\b(?:find|discover|search)\b": "discover",
        r"\b(?:build|compile)\b": "build",
        r"\b(?:validate|verify)\b": "validate",
        r"\b(?:publish|deploy)\b": "publish",
        r"\b(?:call|invoke)\b": "call",
    }

    for part in parts:
        part = part.strip()
        if not part:
            continue

        for pattern, command in COMMAND_PATTERNS.items():
            if re.search(pattern, part):
                commands.append((command, None))
                break

    return commands
