# 🚀 Traylinx CLI

<div align="center">
  <img src="https://public-uploads-ma-production.s3.eu-west-1.amazonaws.com/traylinx_cli_logo.png" alt="Traylinx CLI Logo" width="120"/>

  The command-line interface for the **Traylinx Agent Network**. Build, run, and share AI agents with Docker-powered simplicity.

  **Version:** 0.2.1 | **Python:** 3.11+ | **Status:** Production-Ready

  [![Status](https://img.shields.io/badge/status-production--ready-success)](https://github.com/traylinx/traylinx-cli)
  [![PyPI](https://img.shields.io/pypi/v/traylinx-cli)](https://pypi.org/project/traylinx-cli/)
</div>

---

## 📚 Documentation Navigation

| Document | Description | Audience |
|----------|-------------|----------|
| **[🏗️ Architecture](./docs/ARCHITECTURE.md)** | Plugin System & Command Structure | Architects / Developers |
| **[📖 Command Reference](./docs/COMMAND_REFERENCE.md)** | All CLI Commands | Developers |
| **[🔌 Setup Guide](./docs/SETUP_GUIDE.md)** | Installation & Configuration | Users / DevOps |

---

## Installation

### Instant Execution (No Install)

Run without installing using [`uvx`](https://github.com/astral-sh/uv):

```bash
uvx traylinx-cli --help
```

### Using pipx (Recommended)

[pipx](https://pipx.pypa.io/) installs CLI tools in isolated environments:

```bash
pipx install traylinx-cli
```

### Using Homebrew (macOS/Linux)

```bash
brew tap traylinx/traylinx
brew install traylinx
```

### Using pip

```bash
pip install traylinx-cli
```

> **💡 Short Alias**: After installation, you can use `tx` as a shortcut:
> ```bash
> tx --help    # Same as traylinx --help
> tx run       # Same as traylinx run
> ```

## Quick Start

```bash
# Create a new agent
traylinx init my-agent
cd my-agent

# Run locally with Docker
traylinx run

# View logs
traylinx logs

# Stop the agent
traylinx stop
```

## 🐳 Docker-Powered Agent Commands

Run agents anywhere with zero configuration — just Docker.

| Command | Description |
|---------|-------------|
| `traylinx run` | 🚀 Start agent via Docker Compose |
| `traylinx stop` | ⏹️ Stop running agent containers |
| `traylinx logs` | 📋 Stream agent logs |
| `traylinx list` | 📊 List all running agents |

### Run Options

```bash
traylinx run                  # Run in background (detached)
traylinx run --no-detach      # Run in foreground (see logs)
traylinx run --prod           # Use production config (Postgres)
traylinx run --native         # Skip Docker, use local Python
```

## 📦 Publishing & Sharing Agents

Share your agents with anyone via GitHub Container Registry.

| Command | Description |
|---------|-------------|
| `traylinx publish` | 📦 Build multi-arch image + push to GHCR |
| `traylinx pull <agent>` | ⬇️ Download and run any published agent |

### Publish Your Agent

```bash
cd my-agent
traylinx publish
# → Building for linux/amd64,linux/arm64...
# → Pushing to ghcr.io/traylinx/my-agent:1.0.0
# → ✓ Published!
```

### Run Any Agent

```bash
# The "Ollama experience" for agents
traylinx pull weather-agent
# → Pulling from ghcr.io/traylinx/weather-agent:latest
# → ✓ Agent running at http://localhost:8000
```

## Core Commands

| Command | Description |
|---------|-------------|
| `traylinx init <name>` | Create new agent project |
| `traylinx validate` | Validate traylinx-agent.yaml |
| `traylinx login` | Log in to your Traylinx account |
| `traylinx status` | Show CLI status and config |
| `traylinx --help` | Show all commands |

## Configuration

### Environment Variables

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
├── cli.py            # Main CLI entry point
├── commands/
│   ├── init.py       # Create projects
│   ├── validate.py   # Validate manifests
│   ├── publish.py    # Publish to catalog
│   └── docker_cmd.py # Docker-powered commands
├── utils/
│   ├── docker.py     # Docker detection + compose
│   └── registry.py   # GHCR integration
├── api/
│   └── registry.py   # API client
├── models/
│   └── manifest.py   # Pydantic models
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

## Requirements

- **Python 3.11+** (for CLI)
- **Docker** (for `run`, `publish`, `pull` commands)
- **Docker Buildx** (for multi-arch builds, optional)

## License

MIT License - Traylinx © 2025
