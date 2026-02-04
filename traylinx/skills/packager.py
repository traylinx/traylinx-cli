"""Skill packager - Create distributable .skill files.

A .skill file is a zip archive containing the skill directory.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from traylinx.skills.validator import validate_skill


class SkillPackager:
    """Package skills into distributable .skill files."""

    def package(
        self,
        skill_path: Path,
        output_dir: Path | None = None,
        validate_first: bool = True,
    ) -> Path | None:
        """
        Package a skill directory into a .skill file.

        Args:
            skill_path: Path to the skill directory.
            output_dir: Directory to write the .skill file. Defaults to skill parent.
            validate_first: If True, validate before packaging.

        Returns:
            Path to the created .skill file, or None if validation failed.
        """
        skill_path = skill_path.resolve()

        if validate_first:
            result = validate_skill(skill_path)
            if not result.valid:
                return None

        if output_dir is None:
            output_dir = skill_path.parent

        output_dir.mkdir(parents=True, exist_ok=True)
        skill_name = skill_path.name
        output_file = output_dir / f"{skill_name}.skill"

        with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in skill_path.rglob("*"):
                if file_path.is_file():
                    # Skip hidden files and __pycache__
                    if any(part.startswith(".") or part == "__pycache__" for part in file_path.parts):
                        continue
                    arcname = file_path.relative_to(skill_path.parent)
                    zf.write(file_path, arcname)

        return output_file


def package_skill(
    skill_path: Path,
    output_dir: Path | None = None,
    validate_first: bool = True,
) -> Path | None:
    """
    Convenience function to package a skill.

    Args:
        skill_path: Path to the skill directory.
        output_dir: Output directory for the .skill file.
        validate_first: Whether to validate before packaging.

    Returns:
        Path to the .skill file, or None if validation failed.
    """
    packager = SkillPackager()
    return packager.package(skill_path, output_dir, validate_first)
