# 🚀 Traylinx CLI

<div align="center">
  <img src="https://public-uploads-ma-production.s3.eu-west-1.amazonaws.com/traylinx_cli_logo.png" alt="Traylinx CLI Logo" width="120"/>

  The command-line interface for the **Traylinx Agent Network**. Build, run, and connect AI agents with Docker-powered simplicity.

  **Version:** 0.3.0 | **Python:** 3.11+ | **Status:** Production-Ready

  [![CI](https://github.com/traylinx/traylinx-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/traylinx/traylinx-cli/actions)
  [![PyPI](https://img.shields.io/pypi/v/traylinx-cli)](https://pypi.org/project/traylinx-cli/)
  [![Homebrew](https://img.shields.io/badge/homebrew-traylinx-8800ff)](https://github.com/traylinx/homebrew-traylinx)
  [![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
</div>

---

## ✨ What's New in v0.3.0

- **🌐 Stargate P2P**: Full network commands (`tx connect`, `tx discover`, `tx call`)
- **🧠 Cortex Intelligence**: Memory and session management plugin
- **📝 Session Audit**: Git-aware logging with `tx sessions`
- **🌍 NAT Traversal**: Automatic relay for agents behind NAT
- **📎 @path Embedding**: Reference files in chat with `@filename.ext`

---

## 📚 Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| **[🏗️ Architecture](./docs/ARCHITECTURE.md)** | Plugin System & Command Structure | Architects |
| **[📖 Command Reference](./docs/COMMAND_REFERENCE.md)** | All CLI Commands | Developers |
| **[🔌 Setup Guide](./docs/SETUP_GUIDE.md)** | Installation & Configuration | Users |

---

## 🚀 Installation

### One-Line Install (Recommended)

```bash
curl -sSL https://get.traylinx.com/install.sh | sh
```

### Homebrew (macOS/Linux)

```bash
brew tap traylinx/traylinx && brew install traylinx
```

### pip

```bash
pip install traylinx-cli
```

> **💡 Short Alias**: Use `tx` as a shortcut for `traylinx`

---

## 🎯 Quick Start

```bash
# Create a new agent
tx init my-agent && cd my-agent

# Run locally with Docker
tx run

# Connect to P2P network
tx connect

# Discover other agents
tx discover

# Call another agent
tx call <peer_id> ping
```

---

## 📦 Command Reference

### Agent Lifecycle

| Command | Description |
|---------|-------------|
| `tx init <name>` | Create new agent project |
| `tx run` | 🚀 Start agent via Docker Compose |
| `tx stop` | ⏹️ Stop running containers |
| `tx logs` | 📋 Stream agent logs |
| `tx list` | 📊 List running agents |

### Publishing & Distribution

| Command | Description |
|---------|-------------|
| `tx publish` | 📦 Build + push to GHCR |
| `tx pull <agent>` | ⬇️ Download and run any agent |
| `tx validate` | ✅ Check traylinx-agent.yaml |

### 🌐 Stargate Network (v0.3.0)

| Command | Description |
|---------|-------------|
| `tx connect` | Connect to P2P network |
| `tx disconnect` | Disconnect from network |
| `tx network` | Show network status + NAT info |
| `tx discover` | Find agents by capability |
| `tx call <peer> <action>` | Execute A2A call |
| `tx announce` | Broadcast presence |
| `tx listen` | Debug: listen for messages |
| `tx stargate identity` | Manage P2P identity |
| `tx stargate certify` | Get Sentinel certificate |

### 🧠 Cortex Intelligence (v0.3.0)

| Command | Description |
|---------|-------------|
| `tx cortex connect <url>` | Connect to Cortex instance |
| `tx cortex status` | Show connection status |
| `tx cortex enable/disable` | Toggle chat routing |
| `tx cortex memory search` | Search memory |
| `tx cortex sessions list` | List chat sessions |

### 📝 Session Audit (v0.3.0)

| Command | Description |
|---------|-------------|
| `tx sessions list` | List saved sessions |
| `tx sessions view <id>` | View session details |

### Interactive TUI

| Command | Description |
|---------|-------------|
| `tx chat` | 💬 Interactive chat with agents |
| `tx dashboard` | 📊 Live status dashboard |

---

## ⚙️ Configuration

### Environment Variables

```bash
export TRAYLINX_ENV=prod                    # dev, staging, prod
export STARGATE_NATS_URL=nats://...         # P2P server
export CORTEX_URL=https://cortex.example    # Cortex endpoint
```

### Config File

Create `~/.traylinx/config.yaml`:

```yaml
registry_url: https://api.traylinx.com
credentials:
  agent_key: your-agent-key
  secret_token: your-secret-token
cortex:
  url: https://cortex.example.com
  enabled: true
```

---

## 🏗️ Architecture

```
traylinx/
├── cli.py              # Main entry point
├── commands/
│   ├── init.py         # Create projects
│   ├── docker_cmd.py   # run, stop, logs, list
│   ├── stargate.py     # P2P network commands
│   ├── cortex_cmd.py   # Intelligence plugin
│   └── sessions_cmd.py # Session audit
├── tui/
│   ├── chat.py         # Interactive chat
│   └── status.py       # Dashboard
└── utils/
    ├── session_logger.py # Audit logging
    └── registry.py       # GHCR integration
```

---

## 🧪 Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run CLI locally
uv run tx --help
```

---

## 📊 Tech Stack

| Component | Technology |
|-----------|------------|
| CLI Framework | Typer |
| TUI | Textual |
| Validation | Pydantic |
| P2P | traylinx-stargate |
| Containers | Docker |

---

## 📄 License

MIT License - Traylinx © 2025
