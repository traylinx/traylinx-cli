"""Docker security safeguards.

Provides security checks for Docker operations including:
- Image source verification
- Resource limits
- Volume mount restrictions
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# Trusted container registries
TRUSTED_REGISTRIES = [
    "ghcr.io/traylinx/",
    "docker.io/library/",
    "docker.io/traylinx/",
    "gcr.io/traylinx/",
]

# Default resource limits
DEFAULT_MEMORY_LIMIT = "2g"
DEFAULT_CPU_LIMIT = "2"
DEFAULT_PIDS_LIMIT = "100"


@dataclass
class ResourceLimits:
    """Container resource limits."""

    memory: str = DEFAULT_MEMORY_LIMIT
    cpus: str = DEFAULT_CPU_LIMIT
    pids_limit: str = DEFAULT_PIDS_LIMIT


@dataclass
class ImageVerificationResult:
    """Result of image verification."""

    is_trusted: bool
    registry: str | None = None
    reason: str = ""


class DockerSafeguards:
    """Security safeguards for Docker operations."""

    def __init__(
        self,
        trusted_registries: list[str] | None = None,
        resource_limits: ResourceLimits | None = None,
    ):
        """Initialize Docker safeguards.

        Args:
            trusted_registries: List of trusted registry prefixes
            resource_limits: Custom resource limits
        """
        self.trusted_registries = trusted_registries or TRUSTED_REGISTRIES.copy()
        self.resource_limits = resource_limits or ResourceLimits()

    def verify_image(self, image: str) -> ImageVerificationResult:
        """Verify if a Docker image is from a trusted source.

        Args:
            image: Docker image reference (e.g., "ghcr.io/traylinx/agent:v1")

        Returns:
            ImageVerificationResult with trust status
        """
        # Normalize image reference
        image = image.lower().strip()

        # Handle images without registry (default to docker.io/library/)
        if "/" not in image:
            image = f"docker.io/library/{image}"
        elif image.count("/") == 1 and "." not in image.split("/")[0]:
            # User image without registry (e.g., "user/image")
            image = f"docker.io/{image}"

        # Check against trusted registries
        for registry in self.trusted_registries:
            if image.startswith(registry.lower()):
                return ImageVerificationResult(
                    is_trusted=True,
                    registry=registry,
                    reason="Image from trusted registry",
                )

        return ImageVerificationResult(
            is_trusted=False,
            registry=None,
            reason=f"Image not from trusted registry. Trusted: {', '.join(self.trusted_registries)}",
        )

    def is_trusted_image(self, image: str) -> bool:
        """Quick check if image is from trusted registry.

        Args:
            image: Docker image reference

        Returns:
            True if image is from trusted registry
        """
        return self.verify_image(image).is_trusted

    def get_safe_volume_mounts(self, workdir: Path) -> list[str]:
        """Get restricted volume mount flags for docker run.

        Args:
            workdir: Working directory to mount

        Returns:
            List of volume mount flags
        """
        workdir = workdir.resolve()
        return [
            f"{workdir}:/app:rw",  # Workdir is read-write
        ]

    def get_safe_volume_mounts_flags(self, workdir: Path) -> list[str]:
        """Get volume mount flags formatted for docker command.

        Args:
            workdir: Working directory to mount

        Returns:
            List of -v flags for docker command
        """
        mounts = self.get_safe_volume_mounts(workdir)
        return [item for mount in mounts for item in ["-v", mount]]

    def get_resource_limit_flags(self) -> list[str]:
        """Get resource limit flags for docker run.

        Returns:
            List of resource limit flags
        """
        return [
            "--memory",
            self.resource_limits.memory,
            "--cpus",
            self.resource_limits.cpus,
            "--pids-limit",
            self.resource_limits.pids_limit,
        ]

    def get_security_flags(self) -> list[str]:
        """Get additional security flags for docker run.

        Returns:
            List of security-related flags
        """
        return [
            "--security-opt",
            "no-new-privileges:true",
            "--cap-drop",
            "ALL",
            "--read-only",
        ]

    def get_all_safe_flags(self, workdir: Path) -> list[str]:
        """Get all security-related flags for docker run.

        Args:
            workdir: Working directory for volume mounts

        Returns:
            Combined list of all security flags
        """
        flags = []
        flags.extend(self.get_safe_volume_mounts_flags(workdir))
        flags.extend(self.get_resource_limit_flags())
        flags.extend(self.get_security_flags())
        return flags

    def validate_compose_config(self, compose_config: dict) -> list[str]:
        """Validate a docker-compose configuration for security issues.

        Args:
            compose_config: Parsed docker-compose configuration

        Returns:
            List of security warnings
        """
        warnings = []

        services = compose_config.get("services", {})
        for service_name, service in services.items():
            # Check for privileged mode
            if service.get("privileged"):
                warnings.append(f"Service '{service_name}' uses privileged mode")

            # Check for host network
            if service.get("network_mode") == "host":
                warnings.append(f"Service '{service_name}' uses host network")

            # Check for dangerous volume mounts
            volumes = service.get("volumes", [])
            for vol in volumes:
                vol_str = str(vol)
                if "/var/run/docker.sock" in vol_str and ":rw" in vol_str:
                    warnings.append(
                        f"Service '{service_name}' has write access to Docker socket"
                    )
                if vol_str.startswith("/:/") or vol_str.startswith("/"):
                    if ":" in vol_str:
                        host_path = vol_str.split(":")[0]
                        if host_path in ["/", "/etc", "/var", "/usr"]:
                            warnings.append(
                                f"Service '{service_name}' mounts sensitive host path: {host_path}"
                            )

            # Check for added capabilities
            cap_add = service.get("cap_add", [])
            dangerous_caps = ["SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE"]
            for cap in cap_add:
                if cap in dangerous_caps:
                    warnings.append(
                        f"Service '{service_name}' adds dangerous capability: {cap}"
                    )

        return warnings
