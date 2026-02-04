"""
Secure Write: Atomic file operations using rename-swap pattern.

This module provides crash-safe file writing that prevents data corruption
from power failures or crashes. It uses the standard pattern of:

1. Write to temp file
2. Sync to disk (fsync)
3. Atomic rename to target

Also supports read-only mode detection via TRAYLINX_READONLY=1.
"""

import json
import uuid
from pathlib import Path


class ReadOnlyError(Exception):
    """Raised when write attempted in read-only mode."""

    pass


def secure_write(
    path: Path,
    data: bytes,
    *,
    backup: bool = True,
    permissions: int = 0o600,
) -> None:
    """
    Atomically write data to a file using rename-swap pattern.

    This ensures the file is never in a partially-written state,
    even if the process crashes or power is lost.

    Args:
        path: Target file path
        data: Bytes to write
        backup: If True, create .bak file before overwriting
        permissions: File permissions (default: 0600 - owner read/write only)

    Raises:
        ReadOnlyError: If TRAYLINX_READONLY=1 is set
        OSError: If file operations fail
    """
    from traylinx.utils.statebox import StateBox

    if StateBox.is_read_only():
        raise ReadOnlyError("Read-only environment: write operations disabled")

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Write to temp file
    temp_path = path.with_suffix(f".tmp.{uuid.uuid4().hex[:8]}")
    try:
        temp_path.write_bytes(data)

        # 2. Sync to disk (fsync)
        with temp_path.open("rb") as f:
            import os

            os.fsync(f.fileno())

        # 3. Create backup if target exists
        if backup and path.exists():
            backup_path = path.with_suffix(path.suffix + ".bak")
            try:
                backup_path.write_bytes(path.read_bytes())
            except OSError:
                pass  # Non-fatal: backup is best-effort

        # 4. Atomic rename
        temp_path.rename(path)

        # 5. Set secure permissions
        path.chmod(permissions)

    finally:
        # Clean up temp file if it still exists (rename failed)
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def secure_write_json(
    path: Path,
    obj: dict,
    *,
    backup: bool = True,
    permissions: int = 0o600,
    indent: int = 2,
) -> None:
    """
    Atomically write JSON data to a file.

    Args:
        path: Target file path
        obj: Dictionary to serialize as JSON
        backup: If True, create .bak file before overwriting
        permissions: File permissions (default: 0600)
        indent: JSON indentation (default: 2 spaces)

    Raises:
        ReadOnlyError: If TRAYLINX_READONLY=1 is set
        OSError: If file operations fail
        TypeError: If obj is not JSON-serializable
    """
    data = json.dumps(obj, indent=indent).encode("utf-8")
    secure_write(path, data, backup=backup, permissions=permissions)


def secure_write_text(
    path: Path,
    text: str,
    *,
    backup: bool = True,
    permissions: int = 0o600,
) -> None:
    """
    Atomically write text to a file.

    Args:
        path: Target file path
        text: Text content to write
        backup: If True, create .bak file before overwriting
        permissions: File permissions (default: 0600)

    Raises:
        ReadOnlyError: If TRAYLINX_READONLY=1 is set
        OSError: If file operations fail
    """
    secure_write(path, text.encode("utf-8"), backup=backup, permissions=permissions)
