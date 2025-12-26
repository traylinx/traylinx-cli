"""Project context loader for TRAYLINX.md files.

This module provides functionality to load project-specific context
from TRAYLINX.md files, similar to GEMINI.md in Gemini CLI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class ProjectContext:
    """Represents loaded project context from TRAYLINX.md."""

    instructions: str
    """Main instructions/rules for the agent."""

    memory: dict[str, str] = field(default_factory=dict)
    """Key-value memory items parsed from the file."""

    tools_config: dict = field(default_factory=dict)
    """Tool-specific configuration."""

    workflows: list[str] = field(default_factory=list)
    """Defined workflow names."""

    source_path: Path | None = None
    """Path to the source TRAYLINX.md file."""

    def to_system_prompt(self) -> str:
        """Convert to a system prompt string for the agent."""
        parts = []

        if self.instructions:
            parts.append("# Project Instructions\n")
            parts.append(self.instructions)
            parts.append("\n")

        if self.memory:
            parts.append("\n# Project Memory\n")
            for key, value in self.memory.items():
                parts.append(f"- **{key}**: {value}\n")

        if self.workflows:
            parts.append("\n# Available Workflows\n")
            for workflow in self.workflows:
                parts.append(f"- {workflow}\n")

        return "".join(parts)


# Section markers in TRAYLINX.md
SECTION_PATTERNS = {
    "instructions": r"^#+\s*(instructions?|rules?|guidelines?)\s*$",
    "memory": r"^#+\s*(memory|context|remember)\s*$",
    "tools": r"^#+\s*(tools?|configuration|config)\s*$",
    "workflows": r"^#+\s*(workflows?|commands?)\s*$",
}


def load_traylinx_md(project_dir: Path) -> ProjectContext | None:
    """Load TRAYLINX.md from a project directory.

    Args:
        project_dir: Path to the project directory

    Returns:
        ProjectContext if file exists, None otherwise
    """
    # Check for TRAYLINX.md (case-insensitive)
    traylinx_file = None
    for name in ["TRAYLINX.md", "traylinx.md", "Traylinx.md"]:
        candidate = project_dir / name
        if candidate.exists():
            traylinx_file = candidate
            break

    if not traylinx_file:
        return None

    try:
        content = traylinx_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    return _parse_traylinx_md(content, traylinx_file)


def _parse_traylinx_md(content: str, source_path: Path) -> ProjectContext:
    """Parse TRAYLINX.md content into ProjectContext.

    Args:
        content: Raw markdown content
        source_path: Path to the source file

    Returns:
        Parsed ProjectContext
    """
    lines = content.split("\n")

    # Track current section
    current_section = "instructions"
    sections: dict[str, list[str]] = {
        "instructions": [],
        "memory": [],
        "tools": [],
        "workflows": [],
    }

    for line in lines:
        # Check if line is a section header
        line_lower = line.lower().strip()
        section_found = False

        for section_name, pattern in SECTION_PATTERNS.items():
            if re.match(pattern, line_lower, re.IGNORECASE):
                current_section = section_name
                section_found = True
                break

        if not section_found:
            sections[current_section].append(line)

    # Build ProjectContext
    instructions = "\n".join(sections["instructions"]).strip()
    memory = _parse_memory_section(sections["memory"])
    tools_config = _parse_tools_section(sections["tools"])
    workflows = _parse_workflows_section(sections["workflows"])

    return ProjectContext(
        instructions=instructions,
        memory=memory,
        tools_config=tools_config,
        workflows=workflows,
        source_path=source_path,
    )


def _parse_memory_section(lines: list[str]) -> dict[str, str]:
    """Parse memory section into key-value pairs."""
    memory = {}
    content = "\n".join(lines).strip()

    # Match patterns like "- **key**: value" or "- key: value"
    pattern = r"^\s*[-*]\s*\*?\*?([^:*]+)\*?\*?:\s*(.+)$"

    for line in content.split("\n"):
        match = re.match(pattern, line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            memory[key] = value

    return memory


def _parse_tools_section(lines: list[str]) -> dict:
    """Parse tools configuration section."""
    content = "\n".join(lines).strip()

    # Try to extract YAML-like config
    config = {}

    # Simple key: value parsing
    for line in content.split("\n"):
        if ":" in line and not line.strip().startswith("#"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                key = parts[0].strip().strip("-").strip()
                value = parts[1].strip()
                if key and value:
                    config[key] = value

    return config


def _parse_workflows_section(lines: list[str]) -> list[str]:
    """Parse workflows section into list of workflow names."""
    workflows = []
    content = "\n".join(lines).strip()

    # Match list items
    for line in content.split("\n"):
        match = re.match(r"^\s*[-*]\s*(.+)$", line)
        if match:
            workflow_name = match.group(1).strip()
            if workflow_name:
                workflows.append(workflow_name)

    return workflows


def find_traylinx_md_up(start_dir: Path, max_depth: int = 5) -> ProjectContext | None:
    """Search up the directory tree for TRAYLINX.md.

    Args:
        start_dir: Starting directory
        max_depth: Maximum directories to traverse up

    Returns:
        ProjectContext if found, None otherwise
    """
    current = start_dir.resolve()

    for _ in range(max_depth):
        context = load_traylinx_md(current)
        if context:
            return context

        parent = current.parent
        if parent == current:
            break
        current = parent

    return None
