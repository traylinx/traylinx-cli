"""Skill loader - Discovery and parsing of SKILL.md files.

Skills follow the AgentSkills spec: YAML frontmatter + Markdown body.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Skill:
    """Represents a loaded skill."""

    name: str
    description: str
    path: Path
    body: str = ""
    resources: dict[str, list[str]] = field(default_factory=dict)

    @property
    def has_scripts(self) -> bool:
        return bool(self.resources.get("scripts"))

    @property
    def has_references(self) -> bool:
        return bool(self.resources.get("references"))

    @property
    def has_assets(self) -> bool:
        return bool(self.resources.get("assets"))


# Regex to parse YAML frontmatter
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def parse_skill_md(path: Path) -> Skill | None:
    """
    Parse a SKILL.md file into a Skill object.

    Args:
        path: Path to the SKILL.md file.

    Returns:
        Skill object or None if parsing fails.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return None

    frontmatter_str, body = match.groups()

    try:
        frontmatter = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError:
        return None

    if not isinstance(frontmatter, dict):
        return None

    name = frontmatter.get("name")
    description = frontmatter.get("description")

    if not name or not description:
        return None

    # Discover resources
    skill_dir = path.parent
    resources: dict[str, list[str]] = {}

    for resource_type in ["scripts", "references", "assets"]:
        resource_dir = skill_dir / resource_type
        if resource_dir.is_dir():
            resources[resource_type] = [
                f.name for f in resource_dir.iterdir() if f.is_file()
            ]

    return Skill(
        name=name,
        description=description,
        path=skill_dir,
        body=body.strip(),
        resources=resources,
    )


class SkillLoader:
    """Load and manage skills from multiple directories."""

    def __init__(self, search_paths: list[Path] | None = None):
        """
        Initialize the skill loader.

        Args:
            search_paths: List of directories to search for skills.
                          Defaults to ~/.traylinx/skills/ and .traylinx/skills/
        """
        if search_paths is None:
            home = Path.home()
            search_paths = [
                home / ".traylinx" / "skills",
                Path.cwd() / ".traylinx" / "skills",
            ]
        self.search_paths = search_paths
        self._cache: dict[str, Skill] = {}

    def discover(self, force_refresh: bool = False) -> dict[str, Skill]:
        """
        Discover all skills in search paths.

        Args:
            force_refresh: If True, refresh the cache.

        Returns:
            Dict mapping skill name to Skill object.
        """
        if self._cache and not force_refresh:
            return self._cache

        self._cache = {}

        for search_path in self.search_paths:
            if not search_path.is_dir():
                continue

            # Look for skill directories (contain SKILL.md)
            for skill_dir in search_path.iterdir():
                if not skill_dir.is_dir():
                    continue

                skill_md = skill_dir / "SKILL.md"
                if not skill_md.is_file():
                    continue

                skill = parse_skill_md(skill_md)
                if skill:
                    # Later paths override earlier ones
                    self._cache[skill.name] = skill

        return self._cache

    def get(self, name: str) -> Skill | None:
        """Get a skill by name."""
        skills = self.discover()
        return skills.get(name)

    def list_names(self) -> list[str]:
        """List all discovered skill names."""
        return list(self.discover().keys())


def discover_skills(search_paths: list[Path] | None = None) -> dict[str, Skill]:
    """
    Convenience function to discover all skills.

    Args:
        search_paths: Optional list of paths to search.

    Returns:
        Dict mapping skill name to Skill object.
    """
    loader = SkillLoader(search_paths)
    return loader.discover()
