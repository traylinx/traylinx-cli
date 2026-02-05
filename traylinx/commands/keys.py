"""
API Keys management command for Traylinx CLI.

Commands:
    traylinx keys create       - Create a new API key
    traylinx keys list         - List API keys (API + local)
    traylinx keys show         - Show stored key details
    traylinx keys delete       - Delete an API key
    traylinx keys export       - Export key for other apps
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from traylinx.auth import AuthManager
from traylinx.context import ContextManager
from traylinx.utils.statebox import StateBox

# API Configuration
METRICS_API_URL = os.environ.get(
    "TRAYLINX_METRICS_URL", "https://api.makakoo.com/ma-metrics-wsp-ms/v1/api"
)

# Default base URL for switchAI
SWITCHAI_BASE_URL = "https://switchai.traylinx.com/v1"

app = typer.Typer(
    help="Manage API keys for Traylinx projects",
    invoke_without_command=True,
    no_args_is_help=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

console = Console()


# =============================================================================
# Helper Functions
# =============================================================================


def _get_auth_headers() -> dict:
    """Get auth headers for API requests with automatic token refresh."""
    # Use get_access_token() which handles expiration and refresh automatically
    token = AuthManager.get_access_token()
    
    if not token:
        console.print("[red]Authentication failed.[/red]")
        console.print("[dim]Run 'traylinx login' to authenticate[/dim]")
        return {}
    
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get_api_keys_dir() -> Path:
    """Get directory for storing API keys."""
    return StateBox.credentials_dir() / "api-keys"


def _save_api_key(note: str, data: dict) -> Path:
    """Save API key securely to local storage.
    
    Uses key ID as primary identifier to prevent collisions.
    Filename format: {key_id}_{sanitized_note}.json
    
    Args:
        note: User-provided note for the key
        data: Key data including id, secret_key, etc.
    
    Returns:
        Path to saved key file
    
    Raises:
        ValueError: If key ID is missing or file collision detected
    """
    from traylinx.utils.secure_write import secure_write_json
    import uuid

    keys_dir = _get_api_keys_dir()
    StateBox.ensure_dir(keys_dir)

    # Validate note
    if not note or not note.strip():
        note = "unnamed"
    note = note.strip()
    if len(note) > 100:
        console.print("[yellow]Note truncated to 100 characters[/yellow]")
        note = note[:100]

    # Get or generate key ID
    key_id = data.get("id")
    if not key_id:
        # Fallback for keys without ID (shouldn't happen with API keys)
        key_id = str(uuid.uuid4())
        data["id"] = key_id
        console.print(f"[dim]Generated key ID: {key_id}[/dim]")

    # Sanitize note for filename (keep only alphanumeric, dash, underscore)
    safe_note = "".join(c if c.isalnum() or c in "-_" else "_" for c in note)
    if not safe_note:
        safe_note = "unnamed"

    # Create filename: {key_id}_{note}.json
    # This ensures uniqueness even with duplicate notes
    filename = f"{key_id}_{safe_note}.json"
    key_file = keys_dir / filename

    # Check for existing file with different key ID (shouldn't happen, but be safe)
    if key_file.exists():
        try:
            existing_data = json.loads(key_file.read_text())
            existing_id = existing_data.get("id")
            if existing_id and existing_id != key_id:
                console.print(f"[red]Error: File collision detected[/red]")
                console.print(f"[dim]File: {key_file}[/dim]")
                console.print(f"[dim]Existing ID: {existing_id}[/dim]")
                console.print(f"[dim]New ID: {key_id}[/dim]")
                raise ValueError(f"File collision: {filename} exists with different key ID")
        except json.JSONDecodeError:
            # Corrupted file, overwrite it
            console.print(f"[yellow]Warning: Overwriting corrupted file {filename}[/yellow]")

    secure_write_json(key_file, data)
    return key_file


def _load_api_key(name: str) -> dict | None:
    """Load API key from local storage by name or ID.
    
    Lookup order:
    1. Exact filename match: {name}.json (legacy format)
    2. Key ID match: {name}_*.json
    3. Note suffix match: *_{name}.json
    4. Search all files for matching note or ID (case-sensitive)
    
    Args:
        name: Key name, note, or ID to search for
    
    Returns:
        Key data dict or None if not found
    """
    keys_dir = _get_api_keys_dir()
    if not keys_dir.exists():
        return None

    # Try exact filename match first (legacy format)
    exact_file = keys_dir / f"{name}.json"
    if exact_file.exists():
        try:
            return json.loads(exact_file.read_text())
        except (OSError, json.JSONDecodeError) as e:
            console.print(f"[yellow]Warning: Could not read {exact_file.name}: {e}[/yellow]")
            return None

    # Try key ID prefix match: {key_id}_*.json
    id_matches = list(keys_dir.glob(f"{name}_*.json"))
    if id_matches:
        if len(id_matches) > 1:
            console.print(f"[yellow]Warning: Multiple keys match ID '{name}':[/yellow]")
            for m in id_matches:
                console.print(f"  - {m.name}")
            console.print("[dim]Using first match. Specify full filename to disambiguate.[/dim]")
        try:
            return json.loads(id_matches[0].read_text())
        except (OSError, json.JSONDecodeError) as e:
            console.print(f"[yellow]Warning: Could not read {id_matches[0].name}: {e}[/yellow]")
            return None

    # Try note suffix match: *_{name}.json
    note_matches = list(keys_dir.glob(f"*_{name}.json"))
    if note_matches:
        if len(note_matches) > 1:
            console.print(f"[yellow]Warning: Multiple keys match note '{name}':[/yellow]")
            for m in note_matches:
                console.print(f"  - {m.name}")
            console.print("[dim]Using first match. Specify key ID to disambiguate.[/dim]")
        try:
            return json.loads(note_matches[0].read_text())
        except (OSError, json.JSONDecodeError) as e:
            console.print(f"[yellow]Warning: Could not read {note_matches[0].name}: {e}[/yellow]")
            return None

    # Fallback: search all files for matching note or ID (case-sensitive)
    for key_file in keys_dir.glob("*.json"):
        try:
            data = json.loads(key_file.read_text())
            # Match by note (exact, case-sensitive)
            if data.get("note") == name:
                return data
            # Match by ID (in case filename doesn't match)
            if data.get("id") == name:
                return data
        except (OSError, json.JSONDecodeError) as e:
            console.print(f"[dim]Warning: Skipping corrupted file {key_file.name}: {e}[/dim]")
            continue

    return None


def _list_local_keys() -> list[dict]:
    """List all locally stored API keys."""
    keys_dir = _get_api_keys_dir()
    if not keys_dir.exists():
        return []

    keys = []
    for key_file in keys_dir.glob("*.json"):
        try:
            data = json.loads(key_file.read_text())
            data["_local_file"] = key_file.name
            keys.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return keys


def _require_auth():
    """Verify user is logged in."""
    if not AuthManager.get_credentials():
        console.print("[red]Not logged in.[/red] Run [cyan]traylinx login[/cyan] first.")
        raise typer.Exit(1)


def _require_project() -> tuple[str, str]:
    """Get current org_id and project_id, or exit with error."""
    org_id = ContextManager.get_current_organization_id()
    project_id = ContextManager.get_current_project_id()

    if not org_id:
        console.print("[yellow]No organization selected.[/yellow]")
        console.print("Run [cyan]traylinx orgs use[/cyan] first.")
        raise typer.Exit(1)

    if not project_id:
        console.print("[yellow]No project selected.[/yellow]")
        console.print("Run [cyan]traylinx projects use[/cyan] first.")
        raise typer.Exit(1)

    return org_id, project_id


# =============================================================================
# Callbacks
# =============================================================================


@app.callback()
def keys_callback(ctx: typer.Context):
    """Manage API keys for Traylinx projects."""
    if ctx.invoked_subcommand is None:
        console.print()
        console.print("[bold cyan]traylinx keys[/bold cyan] - API key management\n")
        console.print("[bold]Commands:[/bold]")
        console.print("  [cyan]create[/cyan]         Create a new API key")
        console.print("  [cyan]list[/cyan]           List all API keys")
        console.print("  [cyan]show[/cyan]           Show stored key details")
        console.print("  [cyan]delete[/cyan]         Delete an API key")
        console.print("  [cyan]export[/cyan]         Export key for switchAILocal")
        console.print()
        console.print("[bold]Examples:[/bold]")
        console.print('  $ traylinx keys create --note "my-app" --save')
        console.print("  $ traylinx keys list")
        console.print("  $ traylinx keys export --format yaml")
        console.print()
        console.print("[dim]For more info: traylinx help keys[/dim]")
        console.print()


# =============================================================================
# Commands
# =============================================================================


@app.command("create")
def create_key(
    note: str = typer.Option(
        "CLI created",
        "--note",
        "-n",
        help="Note to identify this key",
    ),
    save: bool = typer.Option(
        False,
        "--save",
        "-s",
        help="Save key locally for later use",
    ),
    project: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Project ID (defaults to current project)",
    ),
):
    """
    Create a new API key.

    The secret key is shown ONCE at creation time - save it securely!
    Use --save to store it locally in ~/.traylinx/credentials/api-keys/
    """
    _require_auth()

    org_id = ContextManager.get_current_organization_id()
    if not org_id:
        console.print("[yellow]No organization selected.[/yellow]")
        console.print("Run [cyan]traylinx orgs use[/cyan] first.")
        raise typer.Exit(1)

    project_id = project or ContextManager.get_current_project_id()
    if not project_id:
        console.print("[yellow]No project selected.[/yellow]")
        console.print("Run [cyan]traylinx projects use[/cyan] or use --project option.")
        raise typer.Exit(1)

    console.print(f"Creating API key [bold]{note}[/bold]...")

    try:
        response = httpx.post(
            f"{METRICS_API_URL}/organizations/{org_id}/projects/{project_id}/api_keys",
            json={"data": {"attributes": {"note": note}}},
            headers=_get_auth_headers(),
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        key_data = data.get("data", {})
        attrs = key_data.get("attributes", {})
        meta = data.get("meta", {})

        public_key = attrs.get("publicKey", "")
        secret_key = meta.get("secretKey", "")
        display_secret = attrs.get("displaySecretKey", "")

        if not public_key or not secret_key:
            console.print("[red]Unexpected response format from API.[/red]")
            console.print(f"[dim]{data}[/dim]")
            raise typer.Exit(1)

        # Display success
        console.print()
        console.print(
            Panel.fit(
                f"[bold green]✅ API Key created![/bold green]\n\n"
                f"   [bold]Note:[/bold]        {note}\n"
                f"   [bold]Public Key:[/bold]  {public_key}\n"
                f"   [bold]Secret Key:[/bold]  {secret_key}\n\n"
                f"[yellow]⚠ The secret key is shown ONCE. Store it securely![/yellow]",
                title="API Key",
                border_style="green",
            )
        )

        # Save locally if requested
        if save:
            local_data = {
                "id": key_data.get("id", ""),
                "public_key": public_key,
                "secret_key": secret_key,
                "note": note,
                "project_id": project_id,
                "org_id": org_id,
                "created_at": attrs.get("createdAt", datetime.now().isoformat()),
                "saved_at": datetime.now().isoformat(),
            }
            key_file = _save_api_key(note, local_data)
            console.print(f"\n[green]✓ Saved to:[/green] {key_file}")

        # Show usage hints
        console.print("\n[bold]To use this key:[/bold]")
        console.print(f'  export TRAYLINX_API_KEY="{secret_key}"')
        console.print(f'  export OPENAI_API_KEY="{secret_key}"')
        console.print(f'  export OPENAI_BASE_URL="{SWITCHAI_BASE_URL}"')
        console.print()

    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error creating API key: {e.response.status_code}[/red]")
        if e.response.text:
            console.print(f"[dim]{e.response.text[:200]}[/dim]")
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_keys(
    project: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Project ID (defaults to current project)",
    ),
    local_only: bool = typer.Option(
        False,
        "--local",
        "-l",
        help="Show only locally stored keys",
    ),
):
    """List API keys from API and local storage."""
    _require_auth()

    # Get local keys
    local_keys = _list_local_keys()
    local_by_id = {k.get("id"): k for k in local_keys if k.get("id")}

    api_keys = []
    if not local_only:
        org_id = ContextManager.get_current_organization_id()
        project_id = project or ContextManager.get_current_project_id()

        if org_id and project_id:
            try:
                response = httpx.get(
                    f"{METRICS_API_URL}/organizations/{org_id}/projects/{project_id}/api_keys",
                    headers=_get_auth_headers(),
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
                api_keys = data.get("data", [])
            except httpx.HTTPError as e:
                console.print(f"[yellow]Warning: Could not fetch API keys: {e}[/yellow]")

    # Merge and display
    if not api_keys and not local_keys:
        console.print("[yellow]No API keys found.[/yellow]")
        console.print('Run [cyan]traylinx keys create --note "my-app" --save[/cyan] to create one.')
        return

    table = Table(title="API Keys")
    table.add_column("Note", style="bold")
    table.add_column("Public Key", style="cyan")
    table.add_column("Secret Key", style="dim")
    table.add_column("Local", style="green")
    table.add_column("Created", style="dim")

    seen_ids = set()

    # Add API keys
    for key in api_keys:
        key_id = key.get("id", "")
        attrs = key.get("attributes", {})
        is_local = key_id in local_by_id
        local_data = local_by_id.get(key_id, {})

        seen_ids.add(key_id)

        # Show full secret if available locally, otherwise display version
        secret_display = local_data.get("secret_key", attrs.get("displaySecretKey", ""))
        if secret_display and len(secret_display) > 20:
            secret_display = f"{secret_display[:6]}...{secret_display[-4:]}"

        table.add_row(
            attrs.get("note", ""),
            attrs.get("publicKey", ""),
            secret_display,
            "✓" if is_local else "",
            (attrs.get("createdAt", "")[:10] if attrs.get("createdAt") else ""),
        )

    # Add local-only keys not in API
    for local_key in local_keys:
        if local_key.get("id") not in seen_ids:
            secret = local_key.get("secret_key", "")
            if secret and len(secret) > 20:
                secret = f"{secret[:6]}...{secret[-4:]}"

            table.add_row(
                local_key.get("note", ""),
                local_key.get("public_key", ""),
                secret,
                "✓",
                (local_key.get("created_at", "")[:10] if local_key.get("created_at") else ""),
            )

    console.print(table)
    console.print(f"\n[dim]Local keys stored in: {_get_api_keys_dir()}[/dim]")


@app.command("show")
def show_key(
    name: str = typer.Argument(..., help="Key note/name to show"),
):
    """Show details of a locally stored API key."""
    _require_auth()

    key_data = _load_api_key(name)

    if not key_data:
        console.print(f"[red]API key '{name}' not found locally.[/red]")
        console.print("Run [cyan]traylinx keys list --local[/cyan] to see stored keys.")
        raise typer.Exit(1)

    console.print()
    console.print(
        Panel.fit(
            f"[bold]Note:[/bold]        {key_data.get('note', 'N/A')}\n"
            f"[bold]Public Key:[/bold]  {key_data.get('public_key', 'N/A')}\n"
            f"[bold]Secret Key:[/bold]  {key_data.get('secret_key', 'N/A')}\n"
            f"[bold]Project:[/bold]     {key_data.get('project_id', 'N/A')}\n"
            f"[bold]Created:[/bold]     {key_data.get('created_at', 'N/A')}\n"
            f"[bold]Saved:[/bold]       {key_data.get('saved_at', 'N/A')}",
            title=f"API Key: {name}",
            border_style="cyan",
        )
    )
    console.print()


@app.command("delete")
def delete_key(
    name: str = typer.Argument(..., help="Key note/name or ID to delete"),
    local_only: bool = typer.Option(
        False,
        "--local",
        "-l",
        help="Only delete local copy (keep on server)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation",
    ),
):
    """Delete an API key locally and/or from server.
    
    By default, deletes from both server and local storage.
    Use --local to only delete the local copy.
    
    IMPORTANT: The secret key cannot be recovered after deletion from the server.
    """
    _require_auth()

    # Find local key
    local_key = _load_api_key(name)
    key_id = local_key.get("id") if local_key else name

    # Show what will be deleted
    console.print()
    if local_key:
        console.print("[bold]Key to delete:[/bold]")
        console.print(f"  Note:       {local_key.get('note', 'N/A')}")
        console.print(f"  Public Key: {local_key.get('public_key', 'N/A')}")
        console.print(f"  ID:         {key_id}")
    else:
        console.print(f"[yellow]Warning: Key '{name}' not found locally[/yellow]")
        if not local_only:
            console.print("[dim]Will attempt to delete from server using provided ID[/dim]")
        else:
            console.print("[red]Cannot delete: key not found locally[/red]")
            raise typer.Exit(1)

    # Confirm deletion
    if not force:
        from InquirerPy import inquirer

        console.print()
        if local_only:
            console.print("[yellow]⚠ This will delete the LOCAL copy only[/yellow]")
            console.print("[dim]The key will remain on the server[/dim]")
        else:
            console.print("[yellow]⚠ This will delete the key from SERVER and locally[/yellow]")
            console.print("[yellow]⚠ The secret key CANNOT be recovered after deletion[/yellow]")

        confirm = inquirer.confirm(
            message=f"Are you sure you want to delete '{name}'?",
            default=False,
        ).execute()

        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    # Track deletion status
    server_deleted = False
    local_deleted = False

    # Step 1: Delete from server FIRST (if not local_only)
    if not local_only and key_id:
        org_id = ContextManager.get_current_organization_id()
        project_id = local_key.get("project_id") if local_key else ContextManager.get_current_project_id()

        if not org_id or not project_id:
            console.print("[red]Error: No organization or project context[/red]")
            console.print("[dim]Run 'traylinx orgs use' and 'traylinx projects use' first[/dim]")
            raise typer.Exit(1)

        console.print(f"\n[dim]Deleting from server...[/dim]")
        try:
            response = httpx.delete(
                f"{METRICS_API_URL}/organizations/{org_id}/projects/{project_id}/api_keys/{key_id}",
                headers=_get_auth_headers(),
                timeout=30,
            )

            if response.status_code in (200, 204):
                console.print("[green]✓ Deleted from server[/green]")
                server_deleted = True
            elif response.status_code == 404:
                console.print("[yellow]⚠ Key not found on server (may have been deleted already)[/yellow]")
                server_deleted = True  # Treat as success
            else:
                console.print(f"[red]✗ Server deletion failed: HTTP {response.status_code}[/red]")
                if response.text:
                    console.print(f"[dim]{response.text[:200]}[/dim]")
                console.print("\n[yellow]⚠ Local copy will NOT be deleted to prevent data loss[/yellow]")
                console.print("[dim]Fix the server issue and try again, or use --local to delete only locally[/dim]")
                raise typer.Exit(1)

        except httpx.TimeoutException:
            console.print("[red]✗ Server deletion timed out[/red]")
            console.print("\n[yellow]⚠ Local copy will NOT be deleted to prevent data loss[/yellow]")
            console.print("[dim]Check your network connection and try again[/dim]")
            raise typer.Exit(1)

        except httpx.HTTPError as e:
            console.print(f"[red]✗ Network error during server deletion: {e}[/red]")
            console.print("\n[yellow]⚠ Local copy will NOT be deleted to prevent data loss[/yellow]")
            console.print("[dim]Check your network connection and try again[/dim]")
            raise typer.Exit(1)

    # Step 2: Delete local file ONLY if server deletion succeeded OR local_only flag is set
    if local_only or server_deleted:
        if local_key:
            console.print(f"\n[dim]Deleting local copy...[/dim]")
            keys_dir = _get_api_keys_dir()

            # Try to find and delete the file
            deleted_files = []

            # Try direct filename match (new format: {id}_{note}.json)
            if key_id:
                for pattern in [f"{key_id}_*.json", f"*_{key_id}.json"]:
                    for f in keys_dir.glob(pattern):
                        try:
                            data = json.loads(f.read_text())
                            if data.get("id") == key_id:
                                f.unlink()
                                deleted_files.append(f.name)
                        except (OSError, json.JSONDecodeError):
                            continue

            # Try legacy filename format
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
            legacy_file = keys_dir / f"{safe_name}.json"
            if legacy_file.exists():
                try:
                    data = json.loads(legacy_file.read_text())
                    if data.get("id") == key_id or data.get("note") == name:
                        legacy_file.unlink()
                        deleted_files.append(legacy_file.name)
                except (OSError, json.JSONDecodeError):
                    pass

            if deleted_files:
                console.print(f"[green]✓ Deleted local copy: {', '.join(deleted_files)}[/green]")
                local_deleted = True
            else:
                console.print("[yellow]⚠ Local file not found (may have been deleted already)[/yellow]")
                local_deleted = True  # Treat as success
        else:
            console.print("[dim]No local copy to delete[/dim]")
            local_deleted = True

    # Summary
    console.print()
    if local_only:
        if local_deleted:
            console.print(f"[green]✓ API key '{name}' deleted locally[/green]")
            console.print("[dim]Note: Key still exists on server[/dim]")
        else:
            console.print(f"[red]✗ Failed to delete local copy[/red]")
            raise typer.Exit(1)
    else:
        if server_deleted and local_deleted:
            console.print(f"[green]✓ API key '{name}' deleted successfully[/green]")
        elif server_deleted:
            console.print(f"[yellow]⚠ Deleted from server but local copy not found[/yellow]")
        else:
            console.print(f"[red]✗ Deletion failed[/red]")
            raise typer.Exit(1)


@app.command("export")
def export_key(
    name: str | None = typer.Argument(
        None,
        help="Key note/name to export (defaults to most recent)",
    ),
    format: str = typer.Option(
        "yaml",
        "--format",
        "-f",
        help="Export format: yaml, env, json",
    ),
    base_url: str = typer.Option(
        SWITCHAI_BASE_URL,
        "--base-url",
        "-b",
        help="Base URL for API calls",
    ),
):
    """Export key for use in switchAILocal or other applications."""
    _require_auth()

    # Get key
    local_keys = _list_local_keys()

    if not local_keys:
        console.print("[yellow]No locally stored API keys found.[/yellow]")
        console.print('Run [cyan]traylinx keys create --note "my-app" --save[/cyan] first.')
        raise typer.Exit(1)

    if name:
        key_data = _load_api_key(name)
        if not key_data:
            console.print(f"[red]API key '{name}' not found locally.[/red]")
            raise typer.Exit(1)
    else:
        # Use most recently saved
        local_keys.sort(key=lambda k: k.get("saved_at", ""), reverse=True)
        key_data = local_keys[0]
        console.print(f"[dim]Using most recent key: {key_data.get('note', 'unnamed')}[/dim]")

    secret_key = key_data.get("secret_key", "")
    note = key_data.get("note", "unnamed")

    if not secret_key:
        console.print("[red]No secret key found in stored data.[/red]")
        raise typer.Exit(1)

    format_lower = format.lower()

    if format_lower == "yaml":
        # switchAILocal format
        output = f"""# switchAILocal configuration for {note}
# Add this to your config.yaml

switchai-api-key:
  - api-key: "{secret_key}"
    base-url: "{base_url}"
    models:
      - name: "openai/gpt-oss-120b"
        alias: "switchai-fast"
      - name: "deepseek-reasoner"
        alias: "switchai-reasoner"
"""
        console.print(Panel(output, title="switchAILocal Config (YAML)", border_style="cyan"))

    elif format_lower == "env":
        output = f"""# Environment variables for {note}

export TRAYLINX_API_KEY="{secret_key}"
export OPENAI_API_KEY="{secret_key}"
export OPENAI_BASE_URL="{base_url}"
"""
        console.print(Panel(output, title="Environment Variables", border_style="green"))

    elif format_lower == "json":
        output = json.dumps(
            {
                "api_key": secret_key,
                "base_url": base_url,
                "note": note,
            },
            indent=2,
        )
        console.print(Panel(output, title="JSON Export", border_style="blue"))

    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        console.print("Supported formats: yaml, env, json")
        raise typer.Exit(1)
