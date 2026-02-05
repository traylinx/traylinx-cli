"""Pattern definitions for intent classification.

Maps natural language patterns to CLI commands using regex patterns.
Patterns are ordered by specificity - more specific patterns should match first.
"""

import re
from typing import NamedTuple


class PatternMatch(NamedTuple):
    """Result of pattern matching."""

    command: str
    confidence: float
    matched_text: str
    groups: dict[str, str]


# Pattern registry: command -> list of regex patterns with named groups
COMMAND_PATTERNS: dict[str, list[str]] = {
    # Agent lifecycle
    "run": [
        # Specific agent: "run my-agent", "start foo"
        r"^(?:start|run|launch|boot)(?: (?:my|the))? (?P<agent_name>[\w-]+)\b",
        # Generic: "run agent"
        r"^(?:start|run|launch|boot)(?: (?:my|the))? agent\b",
        r"^(?:spin|fire) (?:up|off)(?: (?:my|the))? agent\b",
        r"^agent start\b",
        # Bare command
        r"^(?:start|run|launch|boot)\b",
    ],
    "stop": [
        r"^(?:stop|kill|halt|shutdown|terminate)(?: (?:my|the))? (?P<agent_name>[\w-]+)\b",
        r"^(?:stop|kill|halt|shutdown|terminate)(?: (?:my|the))? agent\b",
        r"^(?:shut|power) down(?: (?:my|the))? agent\b",
        r"^agent stop\b",
        r"^(?:stop|kill|halt|shutdown|terminate)\b",
    ],
    "logs": [
        r"^(?:show|view|display|get|tail|stream)(?: (?:me|the))?(?: (?:the))?(?:agent)? logs(?: for)? (?P<agent_name>[\w-]+)\b",
        r"^(?:show|view|display|get|tail|stream)(?: (?:me|the))?(?: (?:the))?(?:agent)? logs?\b",
        r"^logs?\b",
        r"^what(?:'s| is) (?:going on|happening)\b",
    ],
    "status": [
        r"^(?:check|status)(?: (?:of|for|on))? (?P<agent_name>[\w-]+)\b",
        r"^(?:what(?:'s| is) (?:the )?)?(?:status|state)(?: of (?:my|the) agent)?\b",
        r"^(?:is|are) (?:my|the)? agent(?:s)? (?:running|up|down|alive)\b",
        r"^check (?:on )?(?:my|the)? agent\b",
        r"^(?:check|status)\b",
    ],
    # Discovery & networking
    "discover": [
        r"^(?:find|search|discover|look for|list)(?: (?:me))? agents?(?: (?:that|which|who)(?: can)? (?P<capability>\w+))?\b",
        r"^(?:what|which) agents? (?:can|are available)\b",
        r"^browse(?: the)? (?:network|registry)\b",
    ],
    "call": [
        r"^call(?: (?:agent|peer))? (?P<peer_id>[\w-]+)(?: (?:with|to) (?P<action>.+))?\b",
        r"^(?:invoke|contact|ping) (?P<peer_id>[\w-]+)\b",
        r"^a2a call (?P<peer_id>[\w-]+)\b",
    ],
    # Authentication
    "whoami": [
        r"^who(?:'s|se| is| am (?:i|I))\b",
        r"^(?:my )?(?:auth|authentication|identity|login)(?: status)?\b",
        r"^am i (?:logged in|authenticated)\b",
        r"^(?:show|check)(?: my)? (?:credentials|identity)\b",
    ],
    "login": [
        r"^log(?:in|me in)\b",
        r"^(?:sign|authenticate)(?: (?:me))? in\b",
        r"^connect to sentinel\b",
    ],
    "logout": [
        r"^log(?:out| me out)\b",
        r"^sign out\b",
        r"^disconnect\b",
    ],
    # Build & publish
    "build": [
        r"^(?:build|compile|package)(?: (?:my|the))? agent\b",
        r"^make(?: a)? (?:build|package)\b",
    ],
    "validate": [
        r"^(?:validate|check|verify|lint)(?: (?:my|the))? agent\b",
        r"^run validation\b",
    ],
    "publish": [
        r"^(?:publish|deploy|release|push)(?: (?:my|the))? agent\b",
        r"^make (?:public|available)\b",
    ],
    # Info & help
    "help": [
        r"^(?:help|commands?|what can (?:you|i) do)\b",
        r"^(?:show|list)(?: (?:me|all))? (?:available )?commands?\b",
        r"^how (?:do i|to)\b",
    ],
    "version": [
        r"^(?:version|ver|v)\b",
        r"^what version\b",
    ],
}

# Confirmation requirements per command
CONFIRMATION_REQUIRED: dict[str, str] = {
    "publish": "hard",  # Always require explicit confirmation
    "delete": "hard",
    "stop": "soft",  # Show command, auto-proceed
    "logout": "soft",
}


def match_pattern(user_input: str) -> PatternMatch | None:
    """Match user input against known patterns.

    Args:
        user_input: Raw user input string

    Returns:
        PatternMatch if a pattern matches, None otherwise
    """
    normalized = user_input.lower().strip()

    for command, patterns in COMMAND_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                return PatternMatch(
                    command=command,
                    confidence=0.9 if match.start() == 0 else 0.8,
                    matched_text=match.group(0),
                    groups=match.groupdict(),
                )

    return None


def get_confirmation_level(command: str) -> str:
    """Get confirmation level for a command.

    Returns:
        "none", "soft", or "hard"
    """
    return CONFIRMATION_REQUIRED.get(command, "none")
