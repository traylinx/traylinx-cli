"""Path validation for security.

Prevents path traversal attacks and restricts file operations
to the designated working directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# Sensitive paths that should never be accessible
SENSITIVE_PATHS = [
    # System files
    "/etc/passwd",
    "/etc/shadow",
    "/etc/sudoers",
    "/etc/ssh",
    # User secrets
    "~/.ssh",
    "~/.gnupg",
    "~/.aws",
    "~/.config/gcloud",
    "~/.kube",
    # Docker socket
    "/var/run/docker.sock",
    # System directories
    "/proc",
    "/sys",
    "/dev",
    # Root directories
    "/bin",
    "/sbin",
    "/usr/bin",
    "/usr/sbin",
]


class PathValidator:
    """Validates file paths for security.

    Ensures all file operations are scoped within the working directory
    and prevents access to sensitive system paths.
    """

    def __init__(self, workdir: Path, allowed_paths: list[Path] | None = None):
        """Initialize validator with working directory.

        Args:
            workdir: The base directory for allowed operations
            allowed_paths: Additional paths outside workdir that are allowed
        """
        self.workdir = workdir.resolve()
        self.allowed_paths = [p.resolve() for p in (allowed_paths or [])]
        self.sensitive_paths = self._expand_sensitive_paths()

    def _expand_sensitive_paths(self) -> list[Path]:
        """Expand sensitive paths with home directory."""
        expanded = []
        home = Path.home()
        for path_str in SENSITIVE_PATHS:
            if path_str.startswith("~"):
                expanded.append(home / path_str[2:])
            else:
                expanded.append(Path(path_str))
        return expanded

    def is_safe(self, path: Path | str) -> bool:
        """Check if a path is safe for file operations.

        Args:
            path: Path to validate

        Returns:
            True if path is safe, False otherwise
        """
        try:
            # Resolve the path (handles .., symlinks, etc.)
            if isinstance(path, str):
                path = Path(path)

            # Expand user directory
            path = path.expanduser()

            # Resolve to absolute path
            if not path.is_absolute():
                path = (self.workdir / path).resolve()
            else:
                path = path.resolve()

            # Check if within workdir
            try:
                path.relative_to(self.workdir)
                in_workdir = True
            except ValueError:
                in_workdir = False

            # Check if in allowed paths
            in_allowed = any(
                self._is_subpath(path, allowed) for allowed in self.allowed_paths
            )

            if not (in_workdir or in_allowed):
                return False

            # Check against sensitive paths
            for sensitive in self.sensitive_paths:
                if self._is_subpath(path, sensitive) or self._is_subpath(sensitive, path):
                    return False

            return True

        except (OSError, ValueError):
            # Path resolution failed
            return False

    def _is_subpath(self, path: Path, parent: Path) -> bool:
        """Check if path is a subpath of parent."""
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    def validate(self, path: Path | str) -> tuple[bool, str]:
        """Validate a path and return detailed result.

        Args:
            path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if isinstance(path, str):
            path = Path(path)

        # Check for path traversal attempts
        path_str = str(path)
        if ".." in path_str:
            # Resolve and check if it escapes workdir
            try:
                resolved = path.expanduser().resolve()
                if not self.is_safe(resolved):
                    return False, "Path traversal detected"
            except (OSError, ValueError):
                return False, "Invalid path"

        # Check for null bytes (common injection technique)
        if "\x00" in path_str:
            return False, "Null byte injection detected"

        # Check against sensitive paths
        try:
            resolved = path.expanduser()
            if not path.is_absolute():
                resolved = (self.workdir / path).resolve()
            else:
                resolved = resolved.resolve()

            for sensitive in self.sensitive_paths:
                if self._is_subpath(resolved, sensitive):
                    return False, f"Access to sensitive path: {sensitive}"

        except (OSError, ValueError) as e:
            return False, f"Path resolution error: {e}"

        if not self.is_safe(path):
            return False, f"Path outside allowed directories: {path}"

        return True, ""

    def get_safe_path(self, path: Path | str) -> Path | None:
        """Get a safe resolved path or None if unsafe.

        Args:
            path: Path to resolve safely

        Returns:
            Resolved Path if safe, None otherwise
        """
        if not self.is_safe(path):
            return None

        if isinstance(path, str):
            path = Path(path)

        path = path.expanduser()
        if not path.is_absolute():
            path = self.workdir / path

        return path.resolve()


def validate_path(path: Path | str, workdir: Path) -> tuple[bool, str]:
    """Convenience function to validate a path.

    Args:
        path: Path to validate
        workdir: Working directory to scope operations

    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = PathValidator(workdir)
    return validator.validate(path)


def is_path_safe(path: Path | str, workdir: Path) -> bool:
    """Convenience function to check if a path is safe.

    Args:
        path: Path to check
        workdir: Working directory to scope operations

    Returns:
        True if path is safe
    """
    validator = PathValidator(workdir)
    return validator.is_safe(path)
