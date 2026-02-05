"""Workspace initialization for Traylinx Cortex.

Creates bootstrap files following OpenClaw patterns:
- PERSONA.md: Agent personality and behavior
- USER.md: User preferences and context
- TOOLS.md: Tool usage notes and patterns
"""

from pathlib import Path
from typing import Literal

from traylinx.cortex.config import get_cortex_dir


# Default templates for bootstrap files
PERSONA_TEMPLATE = """# Cortex Persona

You are **Cortex**, the natural language interface for Traylinx CLI.

## Core Identity

- **Role**: AI assistant for Traylinx agent management and P2P operations
- **Tone**: Technical, concise, helpful
- **Expertise**: Agent lifecycle, P2P networking, A2A communication, authentication

## Behavioral Guidelines

1. **Command Transparency**: Always show the exact CLI command before execution
2. **Confirmation**: Ask before destructive operations (publish, delete, stop)
3. **Context Awareness**: Use session history to resolve references ("it", "that agent")
4. **Error Handling**: Provide actionable suggestions when commands fail
5. **Efficiency**: Prefer direct answers over verbose explanations

## Capabilities

- **Agent Management**: run, stop, logs, status, build, validate
- **P2P Operations**: discover, call (A2A), network status
- **Authentication**: login, logout, whoami, token management
- **Publishing**: publish agents to registry, version management

## Limitations

- Cannot modify agent code directly (guide user to edit files)
- Cannot access external APIs beyond Traylinx ecosystem
- Cannot execute arbitrary shell commands (only Traylinx CLI)

## Response Style

- Use emojis sparingly (✅ ❌ ⚠️ 💡)
- Format command output with syntax highlighting
- Provide examples when explaining concepts
- Ask clarifying questions when intent is ambiguous

---

*This file can be customized to adjust Cortex's personality and behavior.*
"""

USER_TEMPLATE = """# User Preferences

This file stores your preferences and context for Cortex sessions.

## Preferences

- **Confirmation Level**: `soft` (ask before destructive ops)
- **Verbose Mode**: `false` (concise responses)
- **Default Agent**: `none` (no default agent set)
- **Preferred Model**: `auto` (use fastest available)

## Context

- **Working Directory**: `~/projects/my-agents`
- **Active Projects**: []
- **Frequent Commands**: []

## Custom Aliases

You can define natural language aliases for common workflows:

```yaml
aliases:
  "deploy production": "tx build && tx publish --env production"
  "check status": "tx status --all && tx discover"
```

## Notes

- Add any personal notes or reminders here
- Cortex will use this context to personalize responses

---

*Edit this file to customize your Cortex experience.*
"""

TOOLS_TEMPLATE = """# Tool Usage Notes

This file stores notes about tool usage patterns and lessons learned.

## Command Patterns

### Agent Lifecycle

```bash
# Start agent with specific config
tx run --config ./agent.yaml --detach

# Stop agent gracefully
tx stop <agent-id>

# View live logs
tx logs <agent-id> --follow
```

### P2P Discovery

```bash
# Find agents by capability
tx discover --capability "translation"

# Check network status
tx status --network
```

### A2A Communication

```bash
# Execute A2A call
tx call <target-agent-id> --method "translate" --params '{"text": "hello"}'
```

## Common Issues

### Issue: Agent won't start
**Solution**: Check logs with `tx logs <agent-id>`, verify config with `tx validate`

### Issue: Discovery returns no results
**Solution**: Ensure network connectivity with `tx status --network`

### Issue: Authentication expired
**Solution**: Re-authenticate with `tx login`

## Best Practices

1. Always validate agent config before publishing
2. Use `--detach` for long-running agents
3. Check logs immediately after starting an agent
4. Use `tx whoami` to verify authentication status

---

*Add your own notes and patterns as you learn.*
"""


BootstrapFile = Literal["PERSONA.md", "USER.md", "TOOLS.md"]


def get_bootstrap_template(filename: BootstrapFile) -> str:
    """Get the default template for a bootstrap file.

    Args:
        filename: Name of the bootstrap file

    Returns:
        Template content
    """
    templates = {
        "PERSONA.md": PERSONA_TEMPLATE,
        "USER.md": USER_TEMPLATE,
        "TOOLS.md": TOOLS_TEMPLATE,
    }
    return templates[filename]


def get_bootstrap_path(filename: BootstrapFile) -> Path:
    """Get the path to a bootstrap file.

    Args:
        filename: Name of the bootstrap file

    Returns:
        Path to the file in cortex workspace
    """
    return get_cortex_dir() / filename


def create_bootstrap_file(filename: BootstrapFile, overwrite: bool = False) -> Path:
    """Create a bootstrap file with default template.

    Args:
        filename: Name of the bootstrap file
        overwrite: Whether to overwrite existing file

    Returns:
        Path to created file
    """
    path = get_bootstrap_path(filename)

    if path.exists() and not overwrite:
        return path

    template = get_bootstrap_template(filename)
    path.write_text(template)
    return path


def ensure_workspace() -> dict[BootstrapFile, Path]:
    """Ensure all bootstrap files exist in the workspace.

    Creates missing files with default templates.
    Does not overwrite existing files.

    Returns:
        Dictionary mapping filenames to paths
    """
    cortex_dir = get_cortex_dir()
    cortex_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    files: dict[BootstrapFile, Path] = {}
    for filename in ["PERSONA.md", "USER.md", "TOOLS.md"]:
        files[filename] = create_bootstrap_file(filename, overwrite=False)

    return files


def load_persona() -> str:
    """Load the PERSONA.md content.

    Returns:
        Persona content, or default template if file doesn't exist
    """
    path = get_bootstrap_path("PERSONA.md")
    if path.exists():
        return path.read_text()
    return PERSONA_TEMPLATE


def load_user_preferences() -> str:
    """Load the USER.md content.

    Returns:
        User preferences content, or default template if file doesn't exist
    """
    path = get_bootstrap_path("USER.md")
    if path.exists():
        return path.read_text()
    return USER_TEMPLATE


def load_tool_notes() -> str:
    """Load the TOOLS.md content.

    Returns:
        Tool notes content, or default template if file doesn't exist
    """
    path = get_bootstrap_path("TOOLS.md")
    if path.exists():
        return path.read_text()
    return TOOLS_TEMPLATE
