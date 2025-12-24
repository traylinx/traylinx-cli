# 📖 Traylinx CLI Command Reference

This document provides a comprehensive reference for all commands available in the Traylinx CLI.

---

## 🐳 Docker-Powered Agent Commands

These commands manage agent containers locally using Docker Compose.

### `traylinx run`
Start the agent in the current directory.

| Option | Description |
|--------|-------------|
| `--no-detach` | Run in foreground (show logs). |
| `--prod` | Use production configuration. |
| `--native` | Skip Docker, run with local Python. |

### `traylinx stop`
Stop all running containers for the agent.

### `traylinx logs`
Stream logs from the running agent.

| Option | Description |
|--------|-------------|
| `-f`, `--follow` | Follow log output (default). |

### `traylinx list`
List all running agent containers.

---

## 📦 Publishing & Sharing

### `traylinx publish`
Build a multi-arch Docker image and push it to GHCR.

| Option | Description |
|--------|-------------|
| `--tag <tag>` | Specify a version tag. |

### `traylinx pull <agent>`
Download and run a published agent from GHCR.

---

## 🛠️ Core Commands

### `traylinx init <name>`
Create a new agent project from a template.

### `traylinx validate`
Validate the `traylinx-agent.yaml` manifest.

### `traylinx status`
Show current CLI configuration and authentication status.

---

## 🔐 Authentication

### `traylinx login`
Authenticate with the Traylinx Network via OAuth Device Flow.

### `traylinx logout`
Clear stored credentials.

### `traylinx whoami`
Display the currently authenticated user/agent.

---

## 🌐 Stargate P2P Commands

These commands interact with the decentralized agent network.

### `traylinx discover` (alias: `stargate peers`)
Find agents with specific capabilities on the network.

| Argument | Description |
|----------|-------------|
| `--capability <key:value>` | Filter by capability. |

### `traylinx call` (alias: `stargate call`)
Send a JSON-RPC request to a remote agent.

| Argument | Description |
|----------|-------------|
| `<agent_id>` | Target agent's public key or ID. |
| `<payload>` | JSON payload to send. |

### `traylinx certify` (alias: `stargate certify`)
Request a certification token from a peer agent.

---

## 🧩 Plugin Management

### `traylinx plugin list`
Show installed plugins.

### `traylinx plugin install <name>`
Install a plugin package from PyPI.

---
[⬅️ Back to README](../README.md)
