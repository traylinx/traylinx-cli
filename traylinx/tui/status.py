"""Status screen for agent dashboard.

This module provides a real-time dashboard showing
running agents, resource usage, and system status.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

if TYPE_CHECKING:
    pass


class StatusPanel(Static):
    """A status panel widget showing key metrics."""

    def __init__(
        self,
        title: str,
        value: str,
        status: str = "ok",
        **kwargs,
    ):
        self.panel_title = title
        self.panel_value = value
        self.panel_status = status
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        status_class = f"status-{self.panel_status}"
        yield Static(f"[bold]{self.panel_title}[/bold]", classes="panel-title")
        yield Static(f"[{status_class}]{self.panel_value}[/{status_class}]", classes="panel-value")


class StatusScreen(Screen):
    """Dashboard showing agent and system status."""

    CSS = """
    StatusScreen {
        layout: grid;
        grid-size: 1;
        grid-rows: auto 1fr;
    }
    
    #status-header {
        height: 3;
        padding: 1;
        background: $primary-darken-2;
    }
    
    #status-container {
        padding: 2;
    }
    
    #metrics-row {
        height: auto;
        margin-bottom: 2;
    }
    
    .status-panel {
        width: 1fr;
        height: auto;
        margin: 1;
        padding: 2;
        border: solid $primary;
        text-align: center;
    }
    
    .panel-title {
        text-align: center;
        margin-bottom: 1;
    }
    
    .panel-value {
        text-align: center;
        text-style: bold;
    }
    
    #agents-list {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    
    .status-ok { color: $success; }
    .status-warning { color: $warning; }
    .status-error { color: $error; }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, project_dir: Path | None = None):
        """Initialize status screen.

        Args:
            project_dir: Project directory for context
        """
        super().__init__()
        self.project_dir = project_dir or Path.cwd()
        self._refresh_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="status-header"):
            yield Static(
                "[bold]📊 Status Dashboard[/bold]",
                id="status-title",
            )
        with Vertical(id="status-container"):
            with Horizontal(id="metrics-row"):
                yield Static(
                    "[bold]Agents[/bold]\n[green]0[/green] running",
                    classes="status-panel",
                )
                yield Static(
                    "[bold]Docker[/bold]\n[green]✓[/green] connected",
                    classes="status-panel",
                )
                yield Static(
                    "[bold]Stargate[/bold]\n[yellow]○[/yellow] offline",
                    classes="status-panel",
                )
                yield Static(
                    "[bold]Context[/bold]\n[dim]TRAYLINX.md[/dim]",
                    classes="status-panel",
                )
            yield Static(id="agents-list")
        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        self._update_status()

    def _update_status(self) -> None:
        """Update the status display."""
        agents_list = self.query_one("#agents-list", Static)

        # Check for Docker
        docker_status = self._check_docker()

        # Check for TRAYLINX.md
        context_status = self._check_context()

        # Build agents list
        content_parts = [
            "[bold]Running Agents[/bold]",
            "",
        ]

        if docker_status:
            containers = self._get_running_containers()
            if containers:
                for container in containers:
                    content_parts.append(
                        f"  [green]●[/green] {container['name']} ({container['status']})"
                    )
            else:
                content_parts.append("  [dim]No running agents[/dim]")
                content_parts.append("")
                content_parts.append("  [dim]Start an agent:[/dim] [cyan]tx run[/cyan]")
        else:
            content_parts.append("  [red]Docker not available[/red]")

        content_parts.append("")
        content_parts.append("[bold]Project Context[/bold]")
        content_parts.append("")

        if context_status:
            content_parts.append(f"  [green]✓[/green] {context_status}")
        else:
            content_parts.append("  [dim]No TRAYLINX.md found[/dim]")

        agents_list.update("\n".join(content_parts))

    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        import shutil

        return shutil.which("docker") is not None

    def _check_context(self) -> str | None:
        """Check for TRAYLINX.md context file."""
        from traylinx.context import load_traylinx_md

        context = load_traylinx_md(self.project_dir)
        if context and context.source_path:
            return context.source_path.name
        return None

    def _get_running_containers(self) -> list[dict]:
        """Get list of running Docker containers."""
        # Placeholder for actual Docker integration
        return []

    def _check_stargate(self) -> tuple[str, str]:
        """Check Stargate P2P status.

        Returns:
            Tuple of (display text, status class)
        """
        try:
            from traylinx_stargate.identity import IdentityManager
            from traylinx_stargate.node import get_node

            identity = IdentityManager()

            if not identity.has_identity():
                return "[yellow]○[/yellow] no identity", "warning"

            node = get_node()
            if node and node.is_running:
                return "[green]●[/green] connected", "ok"
            elif identity.has_certificate():
                return "[cyan]○[/cyan] certified", "ok"
            else:
                return "[yellow]○[/yellow] uncertified", "warning"
        except ImportError:
            return "[dim]○[/dim] not installed", "warning"
        except Exception:
            return "[red]✗[/red] error", "error"

    def _check_cortex(self) -> tuple[str, str]:
        """Check Cortex connection status.

        Returns:
            Tuple of (display text, status class)
        """
        try:
            from traylinx.commands.cortex_cmd import load_cortex_config

            config = load_cortex_config()
            if not config.get("url"):
                return "[dim]○[/dim] not configured", "warning"
            elif config.get("enabled"):
                return "[green]●[/green] enabled", "ok"
            else:
                return "[yellow]○[/yellow] disabled", "warning"
        except ImportError:
            return "[dim]○[/dim] unavailable", "warning"
        except Exception:
            return "[red]✗[/red] error", "error"

    def action_refresh(self) -> None:
        """Refresh the status display."""
        self.notify("Refreshing status...")
        self._update_status()
        self._update_panels()

    def _update_panels(self) -> None:
        """Update the metric panels with live data."""
        panels = self.query(".status-panel")
        panel_list = list(panels)

        if len(panel_list) >= 3:
            # Update Stargate panel (index 2)
            stargate_text, _ = self._check_stargate()
            panel_list[2].update(f"[bold]Stargate[/bold]\n{stargate_text}")

        if len(panel_list) >= 4:
            # Add Cortex panel info
            cortex_text, _ = self._check_cortex()
            # Update Context panel to show Cortex
            context_status = self._check_context()
            if context_status:
                panel_list[3].update(f"[bold]Cortex[/bold]\n{cortex_text}")

