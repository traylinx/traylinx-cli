# Traylinx CLI

**The command-line interface for the Traylinx Agent Network.**

```bash
pip install traylinx-cli
```

## Quick Start

```bash
# Create a new agent
traylinx init my-agent

# Navigate to project
cd my-agent

# Validate manifest
traylinx validate

# Publish to catalog
traylinx publish
```

## Commands

| Command | Description |
|---------|-------------|
| `traylinx init <name>` | Create new agent project |
| `traylinx validate` | Validate traylinx-agent.yaml |
| `traylinx publish` | Publish to Traylinx catalog |
| `traylinx --help` | Show all commands |

## Configuration

### Environment Variables (Recommended)

```bash
export TRAYLINX_ENV=dev                           # dev, staging, prod
export TRAYLINX_REGISTRY_URL=http://localhost:8000  # Override registry URL
export TRAYLINX_AGENT_KEY=my-agent                # Your agent key
export TRAYLINX_SECRET_TOKEN=your-token           # From Sentinel
```

### Config File

Create `~/.traylinx/config.yaml`:

```yaml
registry_url: https://api.traylinx.com
credentials:
  agent_key: your-agent-key
  secret_token: your-secret-token
```

## Architecture

```
traylinx/
├── constants.py      # All URLs, endpoints, env vars
├── cli.py            # Main CLI entry point
├── commands/
│   ├── init.py       # Create projects
│   ├── validate.py   # Validate manifests
│   └── publish.py    # Publish to catalog
├── api/
│   └── registry.py   # API client
├── models/
│   └── manifest.py   # Pydantic models
├── utils/
│   └── config.py     # Config loading
└── templates/        # Project templates
```

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run CLI locally
uv run traylinx --help
```

## License

MIT License - Traylinx © 2025
