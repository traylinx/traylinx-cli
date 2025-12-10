"""
Traylinx CLI - Open Command.

Opens the Traylinx platform in the default browser.
"""

import typer
import webbrowser
from rich.console import Console

console = Console()
PLATFORM_URL = "https://traylinx.com"


def open_command():
    """
    Open the Traylinx platform in your default web browser.
    """
    console.print(f"Opening [bold blue]{PLATFORM_URL}[/bold blue]...")
    webbrowser.open(PLATFORM_URL)
