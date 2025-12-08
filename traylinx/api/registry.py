"""Registry API client for publishing agents."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

from traylinx.constants import (
    ENDPOINTS,
    CONTENT_TYPE_A2A,
    DEFAULT_TIMEOUT,
    PUBLISH_TIMEOUT,
)
from traylinx.models.manifest import AgentManifest


class RegistryError(Exception):
    """Error from registry API."""
    pass


class RegistryClient:
    """Client for Traylinx Agent Registry API."""
    
    def __init__(
        self,
        base_url: str,
        agent_key: str,
        secret_token: str,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.agent_key = agent_key
        self.secret_token = secret_token
        self.timeout = timeout
    
    def _build_envelope(self, action: str) -> dict:
        """Build A2A envelope."""
        return {
            "message_id": str(uuid4()),
            "sender_agent_key": self.agent_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def _build_headers(self) -> dict:
        """Build request headers."""
        return {
            "Content-Type": CONTENT_TYPE_A2A,
            "X-Agent-Key": self.agent_key,
            "X-Agent-Secret-Token": self.secret_token,
        }
    
    def publish(self, manifest: AgentManifest) -> dict[str, Any]:
        """
        Publish agent manifest to catalog.
        
        POST /a2a/catalog/publish
        """
        url = f"{self.base_url}/a2a/catalog/publish"
        
        payload = {
            "envelope": self._build_envelope("catalog.publish"),
            "action": "catalog.publish",
            "payload": {
                "agent_key": manifest.info.name,
                "version": manifest.info.version,
                "manifest": manifest.model_dump(mode="json", by_alias=True),
            },
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                url,
                json=payload,
                headers=self._build_headers(),
            )
        
        if response.status_code not in (200, 201):
            try:
                error = response.json()
                msg = error.get("message", error.get("detail", str(error)))
            except Exception:
                msg = response.text
            raise RegistryError(f"Publish failed ({response.status_code}): {msg}")
        
        return response.json()
    
    def unpublish(self, agent_key: str, version: str | None = None) -> dict[str, Any]:
        """
        Unpublish agent from catalog.
        
        POST /a2a/catalog/unpublish
        """
        url = f"{self.base_url}/a2a/catalog/unpublish"
        
        payload_data = {"agent_key": agent_key}
        if version:
            payload_data["version"] = version
        
        payload = {
            "envelope": self._build_envelope("catalog.unpublish"),
            "action": "catalog.unpublish",
            "payload": payload_data,
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                url,
                json=payload,
                headers=self._build_headers(),
            )
        
        if response.status_code != 200:
            try:
                error = response.json()
                msg = error.get("message", str(error))
            except Exception:
                msg = response.text
            raise RegistryError(f"Unpublish failed ({response.status_code}): {msg}")
        
        return response.json()
    
    def list_versions(self, agent_key: str) -> list[dict]:
        """
        List published versions.
        
        POST /a2a/catalog/versions
        """
        url = f"{self.base_url}/a2a/catalog/versions"
        
        payload = {
            "envelope": self._build_envelope("catalog.versions"),
            "action": "catalog.versions",
            "payload": {"agent_key": agent_key},
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                url,
                json=payload,
                headers=self._build_headers(),
            )
        
        if response.status_code != 200:
            try:
                error = response.json()
                msg = error.get("message", str(error))
            except Exception:
                msg = response.text
            raise RegistryError(f"List versions failed ({response.status_code}): {msg}")
        
        result = response.json()
        return result.get("payload", {}).get("versions", [])
