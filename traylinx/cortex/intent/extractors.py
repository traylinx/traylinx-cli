"""Parameter extraction from user input.

Extracts command parameters from natural language patterns,
including flags, options, and positional arguments.
"""

import re
from typing import Any


# Parameter extraction patterns per command
PARAMETER_EXTRACTORS: dict[str, list[tuple[str, str]]] = {
    # run command parameters
    "run": [
        (r"\b(?:in the )?background\b", "--detach"),
        (r"\b(?:with )?rebuild(?:ing)?\b", "--build"),
        (r"\bdetach(?:ed)?\b", "--detach"),
        (r"\b--build\b", "--build"),
        (r"\b--detach\b", "--detach"),
    ],
    # logs command parameters
    "logs": [
        (r"\blast (\d+) lines?\b", "--tail"),
        (r"\btail(?: (\d+))?\b", "--tail"),
        (r"\bfollow(?:ing)?\b", "--follow"),
        (r"\b--follow\b", "--follow"),
        (r"\b-f\b", "--follow"),
    ],
    # discover command parameters
    "discover": [
        (r"\b(?:that|which) (?:can )?(\w+)\b", "--capability"),
        (r"\b(?:show|limit)(?: me)? (\d+)\b", "--limit"),
        (r"\btop (\d+)\b", "--limit"),
        (r"\b--capability[= ](\w+)\b", "--capability"),
        (r"\b--limit[= ](\d+)\b", "--limit"),
    ],
    # call command parameters
    "call": [
        (r"\bwith payload (.+)$", "--payload"),
        (r"\b--timeout[= ](\d+)\b", "--timeout"),
    ],
}


def extract_parameters(command: str, user_input: str) -> dict[str, Any]:
    """Extract parameters for a command from user input.

    Args:
        command: The identified CLI command
        user_input: Raw user input string

    Returns:
        Dictionary of extracted parameters
    """
    params: dict[str, Any] = {}
    extractors = PARAMETER_EXTRACTORS.get(command, [])

    for pattern, param_name in extractors:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            if match.groups():
                # Pattern has capture group - use captured value
                value = match.group(1)
                if value:
                    # Convert numeric values
                    if value.isdigit():
                        params[param_name] = int(value)
                    else:
                        params[param_name] = value
            else:
                # Boolean flag
                params[param_name] = True

    return params


def extract_peer_id(user_input: str) -> str | None:
    """Extract peer ID from call-related input.

    Args:
        user_input: Raw user input

    Returns:
        Peer ID if found, None otherwise
    """
    patterns = [
        r"\bcall\s+(?:agent\s+)?([a-zA-Z0-9_-]+)\b",
        r"\bpeer[_-]?id[= ]([a-zA-Z0-9_-]+)\b",
        r"\bagent[= ]([a-zA-Z0-9_-]+)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def extract_capability(user_input: str) -> str | None:
    """Extract capability from discover-related input.

    Args:
        user_input: Raw user input

    Returns:
        Capability if found, None otherwise
    """
    patterns = [
        r"\b(?:that|which|who) can\s+(\w+)\b",
        r"\b(?:for|with|supporting)\s+(\w+)\b",
        r"\bcapability[= ](\w+)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            return match.group(1)

    return None
