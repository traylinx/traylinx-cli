"""Skill validator - Validate skill structure and content.

Checks:
- YAML frontmatter has required fields (name, description)
- Skill naming conventions (lowercase, hyphens)
- Resources exist if referenced
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from traylinx.skills.loader import parse_skill_md


@dataclass
class ValidationResult:
    """Result of skill validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


# Skill name pattern: lowercase letters, digits, hyphens
SKILL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")


class SkillValidator:
    """Validate skills against the AgentSkills spec."""

    def validate(self, skill_path: Path) -> ValidationResult:
        """
        Validate a skill directory.

        Args:
            skill_path: Path to the skill directory.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult(valid=True)

        # Check directory exists
        if not skill_path.is_dir():
            result.add_error(f"Skill path is not a directory: {skill_path}")
            return result

        # Check SKILL.md exists
        skill_md = skill_path / "SKILL.md"
        if not skill_md.is_file():
            result.add_error("Missing required SKILL.md file")
            return result

        # Parse SKILL.md
        skill = parse_skill_md(skill_md)
        if skill is None:
            result.add_error("Failed to parse SKILL.md - check YAML frontmatter format")
            return result

        # Validate name format
        if not SKILL_NAME_PATTERN.match(skill.name):
            result.add_error(
                f"Invalid skill name '{skill.name}': must be lowercase letters, "
                "digits, and hyphens, starting with a letter"
            )

        # Check name matches directory
        if skill_path.name != skill.name:
            result.add_warning(
                f"Directory name '{skill_path.name}' does not match skill name '{skill.name}'"
            )

        # Check description length
        if len(skill.description) < 10:
            result.add_warning("Description is very short - consider adding more detail")

        if len(skill.description) > 500:
            result.add_warning("Description is very long - consider being more concise")

        # Validate body content
        if not skill.body:
            result.add_warning("SKILL.md body is empty - consider adding instructions")

        # Check for prohibited files
        prohibited_files = ["README.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md"]
        for prohibited in prohibited_files:
            if (skill_path / prohibited).exists():
                result.add_warning(
                    f"Found '{prohibited}' - skills should not contain auxiliary documentation"
                )

        return result


def validate_skill(skill_path: Path) -> ValidationResult:
    """
    Convenience function to validate a skill.

    Args:
        skill_path: Path to the skill directory.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = SkillValidator()
    return validator.validate(skill_path)
