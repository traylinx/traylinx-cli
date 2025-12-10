"""
Help command for Traylinx CLI.

Provides user-friendly documentation with:
- Branded header with logo
- Grouped commands by category
- Quick start examples
- Topic-specific help
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from typing import Optional

from traylinx.branding import print_logo

app = typer.Typer(help="Help and documentation")
console = Console()

# Command documentation
COMMANDS = {
    "Getting Started": [
        ("login", "Authenticate with your Traylinx account"),
        ("status", "Show current CLI status and configuration"),
        ("logout", "Sign out and revoke tokens"),
    ],
    "Organizations & Projects": [
        ("orgs list", "List your organizations"),
        ("orgs use", "Switch organization (interactive)"),
        ("projects list", "List projects in current organization"),
        ("projects use", "Switch project (interactive)"),
        ("projects create", "Create a new project"),
    ],
    "Agent Development": [
        ("init", "Create a new agent project from template"),
        ("validate", "Validate traylinx-agent.yaml manifest"),
        ("publish", "Publish agent to the Traylinx catalog"),
    ],
    "Security & Authentication": [
        ("assets list", "List assets in current project"),
        ("assets create sentinel-pass", "Create A2A credentials"),
        ("projects keys list", "List API keys"),
        ("projects keys create", "Create new API key"),
    ],
    "Plugins": [
        ("plugin list", "Show installed plugins"),
        ("plugin install", "Install a plugin (e.g., stargate)"),
    ],
}

QUICK_START = """
[bold]Quick Start[/bold]

  1. [cyan]traylinx login[/cyan]              # Sign in via browser
  2. [cyan]traylinx orgs use[/cyan]           # Select your organization
  3. [cyan]traylinx projects use[/cyan]       # Select your project
  4. [cyan]traylinx init[/cyan]               # Create new agent project
  5. [cyan]traylinx publish[/cyan]            # Publish to catalog
"""

TOPICS = {
    "login": """
[bold]traylinx login[/bold]

Authenticate with your Traylinx account using browser-based OAuth.

[bold]Usage:[/bold]
  traylinx login [--no-browser]

[bold]Options:[/bold]
  --no-browser    Don't auto-open browser, show URL instead

[bold]Example:[/bold]
  $ traylinx login
  # Opens browser for authentication
  # After approval, you're logged in!
""",
    "orgs": """
[bold]traylinx orgs[/bold]

Manage your organizations. Your current organization context determines
which projects you can access.

[bold]Commands:[/bold]
  traylinx orgs list      List available organizations
  traylinx orgs use       Switch organization (interactive selector)
  traylinx orgs use <id>  Switch to specific organization
  traylinx orgs current   Show current organization
  traylinx orgs refresh   Reload data from Traylinx API

[bold]Example:[/bold]
  $ traylinx orgs use
  # Use arrow keys to select: ↑ ↓ Enter
""",
    "projects": """
[bold]traylinx projects[/bold]

Manage projects within your current organization. Projects contain
agents, API keys, and security assets.

[bold]Commands:[/bold]
  traylinx projects list         List projects
  traylinx projects use          Switch project (interactive)
  traylinx projects use <id>     Switch to specific project
  traylinx projects create       Create new project
  traylinx projects show         Show project details
  traylinx projects keys list    List API keys
  traylinx projects keys create  Create API key

[bold]Example:[/bold]
  $ traylinx projects create my-agent
  $ traylinx projects use
""",
    "assets": """
[bold]traylinx assets[/bold]

Manage assets in your current project, including Sentinel Passes
for A2A (Agent-to-Agent) authentication.

[bold]Commands:[/bold]
  traylinx assets list                      List all assets
  traylinx assets create sentinel-pass      Create A2A credentials

[bold]Sentinel Pass:[/bold]
  Creates OAuth client_id/client_secret for A2A authentication.
  These credentials are shown ONLY ONCE - save them!

[bold]Example:[/bold]
  $ traylinx assets create sentinel-pass "my-agent" --save
  # Saves credentials to ~/.traylinx/credentials/
""",
    "init": """
[bold]traylinx init[/bold]

Create a new agent project from template.

[bold]Usage:[/bold]
  traylinx init [directory] [--template TEMPLATE]

[bold]Options:[/bold]
  --template    Template to use (default: python-basic)

[bold]Example:[/bold]
  $ traylinx init my-agent
  $ cd my-agent
  $ traylinx validate
""",
    "publish": """
[bold]traylinx publish[/bold]

Publish your agent to the Traylinx catalog.

[bold]Usage:[/bold]
  traylinx publish [--env ENV]

[bold]Requirements:[/bold]
  1. Valid traylinx-agent.yaml manifest
  2. TRAYLINX_AGENT_KEY environment variable
  3. TRAYLINX_SECRET_TOKEN environment variable

[bold]Example:[/bold]
  $ export TRAYLINX_AGENT_KEY=your-key
  $ export TRAYLINX_SECRET_TOKEN=your-token
  $ traylinx publish
""",
}


def help_command(
    topic: Optional[str] = typer.Argument(None, help="Topic to get help on")
):
    """
    Show help and documentation.
    
    Run without arguments for an overview, or specify a topic:
    
        traylinx help login
        traylinx help orgs
        traylinx help projects
        traylinx help assets
    """
    # Show topic-specific help
    if topic:
        topic_lower = topic.lower()
        if topic_lower in TOPICS:
            console.print(TOPICS[topic_lower])
        else:
            console.print(f"[yellow]Unknown topic: {topic}[/yellow]")
            console.print("\n[bold]Available topics:[/bold]")
            for t in TOPICS.keys():
                console.print(f"  • {t}")
            console.print("\nOr run [cyan]traylinx help[/cyan] for full overview.")
        return
    
    # Show full help
    console.print()
    print_logo(compact=True)
    console.print()
    
    # Tagline
    console.print("[bold]TRAYLINX CLI[/bold] - Build and deploy AI agents\n")
    
    # Quick start
    console.print(QUICK_START)
    console.print()
    
    # Commands by category
    console.print("[bold]Commands[/bold]\n")
    
    for category, commands in COMMANDS.items():
        console.print(f"  [bold dim]{category}[/bold dim]")
        for cmd, desc in commands:
            console.print(f"    [cyan]traylinx {cmd:<28}[/cyan] {desc}")
        console.print()
    
    # Footer
    console.print("[dim]For more on a command: traylinx help <topic>[/dim]")
    console.print("[dim]Report issues: https://github.com/traylinx/traylinx-cli[/dim]")
    console.print()
