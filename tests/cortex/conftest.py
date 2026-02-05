"""Pytest configuration for Cortex tests."""

import pytest
import sys
from pathlib import Path

# Add traylinx-cli to path
traylinx_cli_path = Path(__file__).parent.parent
sys.path.insert(0, str(traylinx_cli_path))
