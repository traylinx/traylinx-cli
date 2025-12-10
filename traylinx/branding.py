"""
Branding module for Traylinx CLI.

Contains ASCII art logo and branding utilities for consistent CLI appearance.
"""

from rich.console import Console
from rich.text import Text

console = Console()

# Traylinx ASCII logo - T-shape with gradient from cyan (#00c3ff) to purple (#8800ff)
# Based on the official Traylinx icon
TRAYLINX_LOGO = """
████████████████████████████████████████
████████████████████████████████████████
████████████████████████████████████████
            ████████████
            ████████████
            ████████████
            ████████████
            ████████████
            ████████████
            ████████████
      ██████████████████████
"""

# Compact version for status display
TRAYLINX_LOGO_COMPACT = """
 ██████████████████████████
       ████████████
       ████████████
       ████████████
   ████████████████████
"""

# Color gradient for the logo (top to bottom: cyan → blue → purple)
LOGO_COLORS = [
    "#00c3ff",  # Cyan
    "#00aaff",  # Light blue
    "#0088ff",  # Blue
    "#0066ff",  # Medium blue
    "#0044ff",  # Blue-purple
    "#0022ff",  # Blue-purple
    "#0000ff",  # Dark blue
    "#2200ff",  # Blue-purple
    "#4400ff",  # Purple-blue
    "#6600ff",  # Purple
    "#8800ff",  # Purple
]


def print_logo(compact: bool = False):
    """
    Print the Traylinx logo with gradient colors.
    
    Args:
        compact: If True, use the compact version of the logo
    """
    logo = TRAYLINX_LOGO_COMPACT if compact else TRAYLINX_LOGO
    lines = [line for line in logo.split('\n') if line.strip()]
    
    for i, line in enumerate(lines):
        # Select color based on line position
        color_index = min(i, len(LOGO_COLORS) - 1)
        color = LOGO_COLORS[color_index]
        
        text = Text(line)
        text.stylize(color)
        console.print(text)


def print_welcome(email: str = None, version: str = "0.2.0"):
    """
    Print welcome message with logo after login.
    
    Args:
        email: User email if available
        version: CLI version
    """
    console.print()
    print_logo(compact=True)
    console.print()
    console.print(f"[bold]TRAYLINX[/bold] CLI v{version}", style="bold cyan")
    console.print()
    
    if email:
        console.print(f"[green]Welcome, {email}![/green]")
    
    console.print()
    console.print("[dim]Tips for getting started:[/dim]")
    console.print("  1. Run [cyan]traylinx orgs list[/cyan] to see your organizations")
    console.print("  2. Run [cyan]traylinx projects list[/cyan] to see your projects")
    console.print("  3. Run [cyan]traylinx --help[/cyan] for more commands")
    console.print()


def print_status_header(version: str = "0.2.0", environment: str = "prod"):
    """
    Print status header with logo.
    
    Args:
        version: CLI version
        environment: Current environment
    """
    console.print()
    print_logo(compact=True)
    console.print()
    
    # Build styled header
    header = Text()
    header.append("TRAYLINX", style="bold cyan")
    header.append(" CLI ", style="bold white")
    header.append(f"v{version}", style="dim cyan")
    header.append(" • ", style="dim")
    header.append(environment, style="bold magenta" if environment != "prod" else "bold green")
    
    console.print(header)
    console.print()
