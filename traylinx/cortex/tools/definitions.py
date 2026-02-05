"""OpenAI-style tool definitions for CLI commands.

Defines tools in the OpenAI function calling format that can be used
by LLMs to execute Traylinx CLI commands.
"""

from typing import Any


# Tool definitions in OpenAI function calling format
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "traylinx_run",
            "description": "Start a Traylinx agent. Use this when the user wants to start, run, or launch an agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent to start (optional, defaults to current directory agent)",
                    },
                    "detach": {
                        "type": "boolean",
                        "description": "Run agent in background (default: true)",
                        "default": True,
                    },
                    "env": {
                        "type": "object",
                        "description": "Environment variables to pass to the agent",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "traylinx_stop",
            "description": "Stop a running Traylinx agent. Use this when the user wants to stop, kill, or halt an agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent to stop",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force kill the agent (SIGKILL)",
                        "default": False,
                    },
                },
                "required": ["agent_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "traylinx_logs",
            "description": "View logs from a Traylinx agent. Use this to show, view, or tail agent logs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent to view logs for",
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Number of recent log lines to show",
                        "default": 50,
                    },
                    "follow": {
                        "type": "boolean",
                        "description": "Follow log output in real-time",
                        "default": False,
                    },
                },
                "required": ["agent_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "traylinx_status",
            "description": "Check the status of agents. Shows running agents and their state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of specific agent to check (optional, shows all if omitted)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "traylinx_discover",
            "description": "Discover agents on the P2P network. Use this to find or search for agents with specific capabilities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "capability": {
                        "type": "string",
                        "description": "Capability to search for (e.g., 'translate', 'search')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "traylinx_call",
            "description": "Execute an A2A (Agent-to-Agent) call to another agent on the network.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name or address of the agent to call",
                    },
                    "action": {
                        "type": "string",
                        "description": "Action to invoke on the agent",
                        "default": "hello",
                    },
                    "payload": {
                        "type": "object",
                        "description": "Data to send with the call",
                    },
                },
                "required": ["agent_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "traylinx_whoami",
            "description": "Show current authentication status and identity.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "traylinx_login",
            "description": "Sign in to Sentinel (Traylinx authentication service).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "traylinx_logout",
            "description": "Sign out from Sentinel.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "traylinx_build",
            "description": "Build the agent in the current directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory containing the agent (default: current directory)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "traylinx_validate",
            "description": "Validate the agent configuration file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory containing the agent config (default: current directory)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "traylinx_publish",
            "description": "Publish the agent to the Traylinx registry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "version": {
                        "type": "string",
                        "description": "Version to publish (optional, uses config version)",
                    },
                },
                "required": [],
            },
        },
    },
]


# Mapping from tool names to CLI commands
TOOL_TO_COMMAND: dict[str, str] = {
    "traylinx_run": "run",
    "traylinx_stop": "stop",
    "traylinx_logs": "logs",
    "traylinx_status": "status",
    "traylinx_discover": "discover",
    "traylinx_call": "call",
    "traylinx_whoami": "whoami",
    "traylinx_login": "login",
    "traylinx_logout": "logout",
    "traylinx_build": "build",
    "traylinx_validate": "validate",
    "traylinx_publish": "publish",
}


def get_tool_schema() -> list[dict[str, Any]]:
    """Get all tool definitions for OpenAI API.

    Returns:
        List of tool definitions in OpenAI format
    """
    return TOOL_DEFINITIONS


def get_tool_by_name(name: str) -> dict[str, Any] | None:
    """Get a specific tool definition by name.

    Args:
        name: Tool name (e.g., 'traylinx_run')

    Returns:
        Tool definition or None
    """
    for tool in TOOL_DEFINITIONS:
        if tool["function"]["name"] == name:
            return tool
    return None


def tool_name_to_command(name: str) -> str | None:
    """Convert tool name to CLI command.

    Args:
        name: Tool name (e.g., 'traylinx_run')

    Returns:
        CLI command (e.g., 'run') or None
    """
    return TOOL_TO_COMMAND.get(name)
