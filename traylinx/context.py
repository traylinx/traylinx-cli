"""
Context management for Traylinx CLI.

Manages organization and project context, syncing with the User Settings API.
Follows the same pattern as the React app's OrganizationContext.

Storage:
    ~/.traylinx/context.json - Local context cache
    
API Sync:
    GET /user_settings?client=cli - Load on login
    PATCH /user_settings - Sync changes
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

import httpx
from rich.console import Console

from traylinx.auth import AuthManager, CREDENTIALS_FILE

# Constants
CONTEXT_FILE = Path.home() / ".traylinx" / "context.json"
METRICS_API_URL = os.environ.get(
    "TRAYLINX_METRICS_URL",
    "https://api.makakoo.com/ma-metrics-wsp-ms/v1/api"
)

console = Console()


class ContextManager:
    """Manages organization and project context for CLI commands."""

    @staticmethod
    def _get_auth_headers() -> Dict[str, str]:
        """Get authorization headers from stored credentials."""
        creds = AuthManager.get_credentials()
        if not creds or "access_token" not in creds:
            return {}
        return {
            "Authorization": f"Bearer {creds['access_token']}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    @staticmethod
    def load_from_api() -> Optional[Dict[str, Any]]:
        """
        Load user settings from API after login.
        
        Called automatically after successful login to populate context.
        
        Returns:
            dict with context data or None if failed
        """
        headers = ContextManager._get_auth_headers()
        if not headers:
            console.print("[yellow]No authentication token available[/yellow]")
            return None

        try:
            response = httpx.get(
                f"{METRICS_API_URL}/user_settings",
                params={"client": "cli"},
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            settings = response.json()
            
            # Transform API response to context format
            context = ContextManager._transform_settings_to_context(settings)
            
            # Save to local file
            ContextManager._save_context(context)
            
            console.print("[dim]✓ Context loaded from Traylinx[/dim]")
            return context
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                console.print("[yellow]Session expired. Please login again.[/yellow]")
            else:
                console.print(f"[dim]Could not load context: {e.response.status_code}[/dim]")
            return None
        except httpx.HTTPError as e:
            console.print(f"[dim]Could not connect to Traylinx: {e}[/dim]")
            return None

    @staticmethod
    def _transform_settings_to_context(settings: Dict[str, Any]) -> Dict[str, Any]:
        """Transform API settings response to local context format."""
        context = {
            "current_organization_id": settings.get("current_organization_id"),
            "current_project_id": settings.get("current_project_id"),
            "organizations": []
        }
        
        # Extract organizations from sidebar if available
        sidebar = settings.get("sidebar", {})
        orgs = sidebar.get("organizations", [])
        
        for org in orgs:
            org_data = {
                "id": org.get("id"),
                "name": org.get("name"),
                "projects": []
            }
            
            # Extract projects
            for project in org.get("projects", []):
                org_data["projects"].append({
                    "id": project.get("id"),
                    "name": project.get("name")
                })
            
            context["organizations"].append(org_data)
        
        return context

    @staticmethod
    def _save_context(context: Dict[str, Any]) -> None:
        """Save context to local file."""
        CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONTEXT_FILE, "w") as f:
            json.dump(context, f, indent=2)

    @staticmethod
    def _load_context() -> Dict[str, Any]:
        """Load context from local file."""
        if not CONTEXT_FILE.exists():
            return {
                "current_organization_id": None,
                "current_project_id": None,
                "organizations": []
            }
        
        try:
            with open(CONTEXT_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {
                "current_organization_id": None,
                "current_project_id": None,
                "organizations": []
            }

    @staticmethod
    def sync_to_api(org_id: Optional[str] = None, project_id: Optional[str] = None) -> bool:
        """
        Sync context changes to API.
        
        Args:
            org_id: Organization ID to sync (if changed)
            project_id: Project ID to sync (if changed)
            
        Returns:
            True if sync successful
        """
        headers = ContextManager._get_auth_headers()
        if not headers:
            return False

        payload = {}
        if org_id is not None:
            payload["current_organization_id"] = org_id
        if project_id is not None:
            payload["current_project_id"] = project_id
        
        if not payload:
            return True  # Nothing to sync

        try:
            response = httpx.patch(
                f"{METRICS_API_URL}/user_settings",
                json=payload,
                params={"client": "cli"},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            # Non-blocking - local context is already updated
            return False

    @staticmethod
    def get_current_organization_id() -> Optional[str]:
        """Get current organization ID."""
        context = ContextManager._load_context()
        return context.get("current_organization_id")

    @staticmethod
    def set_current_organization_id(org_id: str) -> None:
        """
        Set current organization ID.
        
        Updates local context and syncs to API in background.
        Also clears current project when switching orgs.
        """
        context = ContextManager._load_context()
        
        # Clear project when switching orgs
        if context.get("current_organization_id") != org_id:
            context["current_project_id"] = None
        
        context["current_organization_id"] = org_id
        ContextManager._save_context(context)
        
        # Sync to API (non-blocking)
        ContextManager.sync_to_api(org_id=org_id, project_id=None)

    @staticmethod
    def get_current_project_id() -> Optional[str]:
        """Get current project ID."""
        context = ContextManager._load_context()
        return context.get("current_project_id")

    @staticmethod
    def set_current_project_id(project_id: str) -> None:
        """
        Set current project ID.
        
        Updates local context and syncs to API.
        """
        context = ContextManager._load_context()
        context["current_project_id"] = project_id
        ContextManager._save_context(context)
        
        # Sync to API (non-blocking)
        ContextManager.sync_to_api(project_id=project_id)

    @staticmethod
    def get_organizations() -> List[Dict[str, Any]]:
        """Get list of organizations from context."""
        context = ContextManager._load_context()
        return context.get("organizations", [])

    @staticmethod
    def get_current_organization() -> Optional[Dict[str, Any]]:
        """Get current organization details."""
        org_id = ContextManager.get_current_organization_id()
        if not org_id:
            return None
        
        for org in ContextManager.get_organizations():
            if str(org.get("id")) == str(org_id):
                return org
        return None

    @staticmethod
    def get_projects(org_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get projects for an organization.
        
        Args:
            org_id: Organization ID (defaults to current)
            
        Returns:
            List of project dicts with id and name
        """
        if org_id is None:
            org_id = ContextManager.get_current_organization_id()
        
        if not org_id:
            return []
        
        for org in ContextManager.get_organizations():
            if str(org.get("id")) == str(org_id):
                return org.get("projects", [])
        
        return []

    @staticmethod
    def get_current_project() -> Optional[Dict[str, Any]]:
        """Get current project details."""
        project_id = ContextManager.get_current_project_id()
        if not project_id:
            return None
        
        for project in ContextManager.get_projects():
            if str(project.get("id")) == str(project_id):
                return project
        return None

    @staticmethod
    def clear() -> None:
        """Clear all context (on logout)."""
        if CONTEXT_FILE.exists():
            CONTEXT_FILE.unlink()

    @staticmethod
    def require_organization() -> str:
        """
        Get current organization ID or raise error.
        
        Use this in commands that require an organization context.
        
        Returns:
            Organization ID
            
        Raises:
            SystemExit if no organization selected
        """
        org_id = ContextManager.get_current_organization_id()
        if not org_id:
            console.print("[red]No organization selected.[/red]")
            console.print("Run [cyan]traylinx orgs use <id>[/cyan] to select one.")
            raise SystemExit(1)
        return org_id

    @staticmethod
    def require_project() -> str:
        """
        Get current project ID or raise error.
        
        Use this in commands that require a project context.
        
        Returns:
            Project ID
            
        Raises:
            SystemExit if no project selected
        """
        project_id = ContextManager.get_current_project_id()
        if not project_id:
            console.print("[red]No project selected.[/red]")
            console.print("Run [cyan]traylinx projects use <id>[/cyan] to select one.")
            raise SystemExit(1)
        return project_id
