# 🔌 Traylinx CLI Setup Guide

This guide walks you through installing and configuring the Traylinx CLI.

## 🛠️ Prerequisites

- **Python 3.11+**
- **Docker** (for `run`, `stop`, `logs`, `publish`, `pull` commands)
- **Docker Buildx** (optional, for multi-arch image builds)

## 🚀 Installation

### Option 1: pipx (Recommended)
[pipx](https://pipx.pypa.io/) installs CLI tools in isolated environments:
```bash
pipx install traylinx-cli
```

### Option 2: Homebrew (macOS/Linux)
```bash
brew tap traylinx/traylinx
brew install traylinx
```

### Option 3: pip
```bash
pip install traylinx-cli
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TRAYLINX_ENV` | Environment mode (`dev`, `staging`, `prod`) | `prod` |
| `TRAYLINX_REGISTRY_URL` | Override the Agent Registry URL | (auto) |
| `TRAYLINX_AGENT_KEY` | Your agent's public key | - |
| `TRAYLINX_SECRET_TOKEN` | Your Sentinel-issued secret token | - |

### Config File

Create `~/.traylinx/config.yaml`:
```yaml
env: prod
registry_url: https://api.traylinx.com
credentials:
  agent_key: your-agent-key
  secret_token: your-secret-token
```

## ✅ Verification

### Check Installation
```bash
traylinx --version
```

### Login to the Network
```bash
traylinx login
```
Follow the on-screen instructions to complete OAuth authentication via Sentinel.

---
[⬅️ Back to README](../README.md)
