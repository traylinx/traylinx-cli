"""Async execution utilities for I/O operations.

Provides async wrappers for common I/O operations:
- Async file operations
- Async network requests
- Concurrent command execution
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, TypeVar
import functools

from traylinx.cortex.types import Intent, ExecutionResult


T = TypeVar("T")

# Shared thread pool for blocking I/O
_executor: ThreadPoolExecutor | None = None


def get_executor(max_workers: int = 4) -> ThreadPoolExecutor:
    """Get the shared thread pool executor.

    Args:
        max_workers: Maximum number of worker threads

    Returns:
        ThreadPoolExecutor instance
    """
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=max_workers)
    return _executor


async def run_in_thread(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a blocking function in a thread pool.

    Args:
        func: Function to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Function result
    """
    loop = asyncio.get_event_loop()
    executor = get_executor()
    return await loop.run_in_executor(
        executor,
        functools.partial(func, *args, **kwargs),
    )


@dataclass
class AsyncExecutionResult:
    """Result of async execution."""

    results: list[ExecutionResult]
    errors: list[Exception]
    total_time_ms: float


class AsyncCommandExecutor:
    """Executes commands asynchronously.

    Supports:
    - Parallel execution of independent commands
    - Sequential execution with dependencies
    - Timeout handling
    """

    def __init__(self, command_executor: Any, timeout: float = 30.0):
        """Initialize async executor.

        Args:
            command_executor: Synchronous CommandExecutor
            timeout: Default timeout in seconds
        """
        self._executor = command_executor
        self._timeout = timeout

    async def execute_one(self, intent: Intent) -> ExecutionResult:
        """Execute a single intent asynchronously.

        Args:
            intent: Intent to execute

        Returns:
            Execution result
        """
        return await run_in_thread(self._executor.execute, intent)

    async def execute_parallel(
        self,
        intents: list[Intent],
        timeout: float | None = None,
    ) -> AsyncExecutionResult:
        """Execute multiple intents in parallel.

        Args:
            intents: List of intents to execute
            timeout: Optional timeout override

        Returns:
            AsyncExecutionResult with all results
        """
        import time

        start = time.time()
        timeout = timeout or self._timeout
        results: list[ExecutionResult] = []
        errors: list[Exception] = []

        tasks = [self.execute_one(intent) for intent in intents]

        try:
            completed = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout,
            )

            for result in completed:
                if isinstance(result, Exception):
                    errors.append(result)
                else:
                    results.append(result)

        except asyncio.TimeoutError:
            errors.append(TimeoutError(f"Execution timed out after {timeout}s"))

        elapsed_ms = (time.time() - start) * 1000
        return AsyncExecutionResult(
            results=results,
            errors=errors,
            total_time_ms=elapsed_ms,
        )

    async def execute_sequential(
        self,
        intents: list[Intent],
        stop_on_error: bool = True,
    ) -> AsyncExecutionResult:
        """Execute intents sequentially.

        Args:
            intents: List of intents to execute in order
            stop_on_error: Stop if any command fails

        Returns:
            AsyncExecutionResult with all results
        """
        import time

        start = time.time()
        results: list[ExecutionResult] = []
        errors: list[Exception] = []

        for intent in intents:
            try:
                result = await self.execute_one(intent)
                results.append(result)

                if stop_on_error and not result.success:
                    break

            except Exception as e:
                errors.append(e)
                if stop_on_error:
                    break

        elapsed_ms = (time.time() - start) * 1000
        return AsyncExecutionResult(
            results=results,
            errors=errors,
            total_time_ms=elapsed_ms,
        )


def async_to_sync(coro: Any) -> Any:
    """Run an async function synchronously.

    Args:
        coro: Coroutine to run

    Returns:
        Coroutine result
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)
