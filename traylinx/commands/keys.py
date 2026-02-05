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
    """Get auth headers for API requests."""
    creds = AuthManager.get_credentials()
    if not creds:
        return {}
    return {
        "Authorization": f"Bearer {creds['access_token']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get_api_keys_dir() -> Path:
    """Get directory for storing API keys."""
    return StateBox.credentials_dir() / "api-keys"


def _save_api_key(note: str, data: dict) -> Path:
    """Save API key securely to local storage."""
    from traylinx.utils.secure_write import secure_write_json

    keys_dir = _get_api_keys_dir()
    StateBox.ensure_dir(keys_dir)

    # Generate safe filename from note
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in note)
    if not safe_name:
        safe_name = f"key_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    key_file = keys_dir / f"{safe_name}.json"
    secure_write_json(key_file, data)
    return key_file


def _load_api_key(name: str) -> dict | None:
    """Load API key from local storage by name."""
    keys_dir = _get_api_keys_dir()
    key_file = keys_dir / f"{name}.json"

    if not key_file.exists():
        # Try to find by note in all files
        if keys_dir.exists():
            for f in keys_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    if data.get("note", "").lower() == name.lower():
                        return data
                except (OSError, json.JSONDecodeError):
                    continue
        return None

    try:
        return json.loads(key_file.read_text())
    except (OSError, json.JSONDecodeError):
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
    """Delete an API key locally and/or from server."""
    _require_auth()

    # Find local key
    local_key = _load_api_key(name)
    key_id = local_key.get("id") if local_key else name

    # Confirm deletion
    if not force:
        from InquirerPy import inquirer

        action = "locally" if local_only else "from server and locally"
        confirm = inquirer.confirm(
            message=f"Delete API key '{name}' {action}?",
            default=False,
        ).execute()

        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    # Delete from server if not local_only
    if not local_only and key_id:
        org_id = ContextManager.get_current_organization_id()
        project_id = local_key.get("project_id") if local_key else ContextManager.get_current_project_id()

        if org_id and project_id:
            try:
                response = httpx.delete(
                    f"{METRICS_API_URL}/organizations/{org_id}/projects/{project_id}/api_keys/{key_id}",
                    headers=_get_auth_headers(),
                    timeout=30,
                )
                if response.status_code in (200, 204, 404):
                    console.print("[green]Deleted from server.[/green]")
                else:
                    console.print(f"[yellow]Server deletion returned {response.status_code}[/yellow]")
            except httpx.HTTPError as e:
                console.print(f"[yellow]Warning: Could not delete from server: {e}[/yellow]")

    # Delete local file
    keys_dir = _get_api_keys_dir()
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    local_file = keys_dir / f"{safe_name}.json"

    if local_file.exists():
        local_file.unlink()
        console.print("[green]Deleted local copy.[/green]")
    elif local_key:
        # Try to find and delete by searching
        for f in keys_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("note", "").lower() == name.lower():
                    f.unlink()
                    console.print("[green]Deleted local copy.[/green]")
                    break
            except (OSError, json.JSONDecodeError):
                continue

    console.print(f"[green]✓ API key '{name}' deleted.[/green]")


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
