"""
Authentication module for Traylinx CLI.

Handles device-based login flow, credential storage, and token management.

Flow:
1. CLI calls /devices to create a session
2. CLI opens browser for user to authorize
3. CLI polls /devices/:id/status until authorized
4. CLI saves tokens to ~/.traylinx/credentials.json
"""

import json
import os
import time
import webbrowser
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import httpx
from rich.console import Console

# Constants
CREDENTIALS_FILE = Path.home() / ".traylinx" / "credentials.json"
SENTINEL_URL = os.environ.get(
    "TRAYLINX_AUTH_URL",
    "https://api.makakoo.com/ma-authentication-ms/v1/api"
)
POLL_INTERVAL = 2  # seconds
POLL_TIMEOUT = 600  # 10 minutes

console = Console()


class AuthError(Exception):
    """Authentication error."""
    pass


class AuthManager:
    """Manages CLI authentication via device session flow."""

    @staticmethod
    def login(no_browser: bool = False) -> dict:
        """
        Perform device login flow.
        
        Args:
            no_browser: If True, don't auto-open browser
            
        Returns:
            dict with user info
            
        Raises:
            AuthError: If login fails
        """
        # 1. Create device session
        console.print("\n[bold]🔐 Logging in to Traylinx...[/bold]\n")
        
        try:
            response = httpx.post(
                f"{SENTINEL_URL}/devices",
                json={"client": "traylinx-cli"},
                timeout=30
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise AuthError(f"Failed to connect to Traylinx: {e}")
        
        data = response.json()
        device_id = data["device_id"]
        verification_uri = data["verification_uri"]
        user_code = data.get("user_code")
        interval = data.get("interval", POLL_INTERVAL)
        expires_in = data.get("expires_in", POLL_TIMEOUT)
        
        # 2. Show URL to user
        console.print("Please open this URL in your browser:")
        console.print(f"  [cyan]{verification_uri}[/cyan]\n")
        
        if user_code:
            console.print(f"Code: [bold]{user_code}[/bold]\n")
        
        # 3. Open browser (unless --no-browser)
        if not no_browser:
            try:
                webbrowser.open(verification_uri)
                console.print("[dim]Browser opened automatically[/dim]\n")
            except Exception:
                console.print("[yellow]Could not open browser automatically[/yellow]\n")
        
        console.print("[dim]Waiting for authorization...[/dim]")
        
        # 4. Poll for status
        start_time = time.time()
        while time.time() - start_time < expires_in:
            time.sleep(interval)
            
            try:
                status_response = httpx.get(
                    f"{SENTINEL_URL}/devices/{device_id}/status",
                    timeout=10
                )
            except httpx.HTTPError:
                continue  # Retry on network error
            
            if status_response.status_code == 410:
                raise AuthError("Session expired. Please try again.")
            
            if status_response.status_code != 200:
                continue
            
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status == "authorized":
                # Success! Save credentials
                expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=status_data.get("expires_in", 7200)
                )
                
                creds = {
                    "access_token": status_data["access_token"],
                    "refresh_token": status_data.get("refresh_token"),
                    "token_type": status_data.get("token_type", "Bearer"),
                    "expires_at": expires_at.isoformat(),
                    "user": status_data.get("user", {})
                }
                
                AuthManager.save_credentials(creds)
                
                # Load organization/project context from API
                from traylinx.context import ContextManager
                ContextManager.load_from_api()
                
                # Show branded welcome message
                from traylinx.branding import print_welcome
                email = creds["user"].get("email", "unknown")
                print_welcome(email=email)
                
                return creds
            
            elif status == "denied":
                raise AuthError("Authorization denied by user.")
            
            # Still pending, continue polling
            console.print(".", end="")
        
        raise AuthError("Login timed out. Please try again.")

    @staticmethod
    def save_credentials(data: dict) -> None:
        """Save credentials to file with secure permissions."""
        CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_FILE.write_text(json.dumps(data, indent=2))
        CREDENTIALS_FILE.chmod(0o600)  # Owner read/write only

    @staticmethod
    def get_credentials() -> Optional[dict]:
        """Load credentials from file."""
        if not CREDENTIALS_FILE.exists():
            return None
        try:
            return json.loads(CREDENTIALS_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            return None

    @staticmethod
    def clear_credentials() -> None:
        """Delete stored credentials."""
        if CREDENTIALS_FILE.exists():
            CREDENTIALS_FILE.unlink()

    @staticmethod
    def is_logged_in() -> bool:
        """Check if user is logged in with valid token."""
        creds = AuthManager.get_credentials()
        if not creds:
            return False
        
        # Check if token is expired
        expires_at_str = creds.get("expires_at")
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now(timezone.utc) >= expires_at:
                    # Token expired, try to refresh
                    if AuthManager.refresh_token():
                        return True
                    return False
            except ValueError:
                pass
        
        return "access_token" in creds

    @staticmethod
    def validate_token() -> bool:
        """
        Validate current access token with the server.
        
        Calls /oauth/token/info to check if the token is still valid.
        This is more reliable than just checking local expiration.
        
        Returns:
            True if token is valid, False otherwise
        """
        creds = AuthManager.get_credentials()
        if not creds or "access_token" not in creds:
            return False
        
        try:
            response = httpx.get(
                f"{SENTINEL_URL}/oauth/token/info",
                headers={"Authorization": f"Bearer {creds['access_token']}"},
                timeout=10
            )
            
            if response.status_code == 200:
                # Token is valid - optionally update local expiry from server
                data = response.json()
                if "expires_in" in data:
                    expires_at = datetime.now(timezone.utc) + timedelta(
                        seconds=data["expires_in"]
                    )
                    creds["expires_at"] = expires_at.isoformat()
                    AuthManager.save_credentials(creds)
                return True
            else:
                # Token invalid or expired
                return False
                
        except httpx.HTTPError as e:
            console.print(f"[dim]Token validation error: {e}[/dim]")
            return False

    @staticmethod
    def get_access_token() -> Optional[str]:
        """Get access token, refreshing if needed."""
        creds = AuthManager.get_credentials()
        if not creds:
            return None
        
        # Check expiration
        expires_at_str = creds.get("expires_at")
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now(timezone.utc) >= expires_at:
                    # Try to refresh
                    if AuthManager.refresh_token():
                        creds = AuthManager.get_credentials()
                    else:
                        return None
            except ValueError:
                pass
        
        return creds.get("access_token")

    @staticmethod
    def refresh_token() -> bool:
        """
        Refresh access token using refresh token.
        
        Tries /devices/refresh first (CLI-specific), then falls back to 
        standard OAuth /oauth/token endpoint.
        """
        creds = AuthManager.get_credentials()
        if not creds or "refresh_token" not in creds:
            return False
        
        refresh_token_value = creds["refresh_token"]
        
        # Try CLI-specific endpoint first
        endpoints = [
            # CLI-specific endpoint (no client credentials needed)
            {
                "url": f"{SENTINEL_URL}/devices/refresh",
                "data": {"refresh_token": refresh_token_value},
                "headers": {"Content-Type": "application/json"},
                "json": True,
            },
            # Standard OAuth endpoint (fallback)
            {
                "url": f"{SENTINEL_URL}/oauth/token",
                "data": {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token_value,
                },
                "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                "json": False,
            },
        ]
        
        for endpoint in endpoints:
            try:
                if endpoint["json"]:
                    response = httpx.post(
                        endpoint["url"],
                        json=endpoint["data"],
                        timeout=30
                    )
                else:
                    response = httpx.post(
                        endpoint["url"],
                        data=endpoint["data"],
                        headers=endpoint["headers"],
                        timeout=30
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    expires_at = datetime.now(timezone.utc) + timedelta(
                        seconds=data.get("expires_in", 7200)
                    )
                    
                    creds["access_token"] = data["access_token"]
                    creds["expires_at"] = expires_at.isoformat()
                    
                    if "refresh_token" in data:
                        creds["refresh_token"] = data["refresh_token"]
                    
                    AuthManager.save_credentials(creds)
                    console.print("[green]✓ Token refreshed[/green]")
                    return True
                    
                elif response.status_code == 404:
                    # Endpoint not available, try next
                    continue
                else:
                    # Log error for debugging
                    console.print(f"[dim]Token refresh failed: {response.status_code}[/dim]")
                    
            except httpx.HTTPError as e:
                console.print(f"[dim]Token refresh error: {e}[/dim]")
        
        return False

    @staticmethod
    def revoke_token(all_devices: bool = False) -> bool:
        """
        Revoke access token on the backend.
        
        Args:
            all_devices: If True, revoke tokens on all devices. Otherwise, only current.
            
        Returns:
            True if revocation was successful
        """
        creds = AuthManager.get_credentials()
        if not creds or "access_token" not in creds:
            return False
        
        access_token = creds["access_token"]
        
        try:
            url = f"{SENTINEL_URL}/oauth/token/revoke"
            if not all_devices:
                url += "?logoutCurrentDevice=true"
            
            response = httpx.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30
            )
            
            if response.status_code == 200:
                return True
            else:
                # Log the error but don't fail - we'll still clear local credentials
                console.print(f"[dim]Warning: Could not revoke token on server (status {response.status_code})[/dim]")
                return False
                
        except httpx.HTTPError as e:
            console.print(f"[dim]Warning: Could not reach server to revoke token: {e}[/dim]")
            return False

    @staticmethod
    def get_user() -> Optional[dict]:
        """Get stored user info."""
        creds = AuthManager.get_credentials()
        if not creds:
            return None
        return creds.get("user")

