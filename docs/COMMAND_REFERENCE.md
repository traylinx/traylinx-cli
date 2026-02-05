# 📖 Traylinx CLI Command Reference

Complete reference for all commands available in the Traylinx CLI v0.3.0.

> **💡 Shorthand**: All commands work with both `traylinx` and `tx`:
> ```bash
> traylinx run    # Full form
> tx run          # Short form
> ```

---

## 🔐 Security & Keys

Manage authentication and API keys.

| Command                   | Description                    |
| ------------------------- | ------------------------------ |
| `tx projects keys create` | Create a new API key           |
| `tx projects keys list`   | List API keys (server + local) |
| `tx keys create`          | Create API key (shortcut)      |
| `tx keys list`            | List API keys (shortcut)       |
| `tx keys show`            | Show stored key details        |
| `tx keys delete`          | Delete an API key              |
| `tx keys export`          | Export key for switchAILocal   |

### `tx keys create`
| Option           | Description                                 |
| ---------------- | ------------------------------------------- |
| `--note <note>`  | Note/description for the key                |
| `--save`         | Save locally (required to see secret later) |
| `--project <id>` | Project ID (defaults to current context)    |

### `tx keys export`
| Option             | Description                                   |
| ------------------ | --------------------------------------------- |
| `--format <fmt>`   | Export format: `yaml`, `env`, `json`          |
| `--base-url <url>` | Base URL for switchAI (default: platform url) |

---

## 🎯 Skills Management (v0.3.0)

Extend CLI capabilities with AgentSkills. Discover, create, and package skills.

| Command                      | Description                                    |
| ---------------------------- | ---------------------------------------------- |
| `tx skills list`             | 🎯 List all discovered skills (global + local)  |
| `tx skills info <name>`      | ℹ️ Show detailed information about a skill      |
| `tx skills init <name>`      | 📁 Scaffold a new skill from template           |
| `tx skills validate <path>`  | ✅ Validate a skill against AgentSkills spec    |
| `tx skills package <path>`   | 📦 Create a .skill zip archive for distribution |
| `tx skills install <source>` | ⬇️ Install a skill from file or directory       |

### `tx skills list`
| Option          | Description                               |
| --------------- | ----------------------------------------- |
| `--path <path>` | Additional directory to search for skills |

### `tx skills init`
| Option                | Description                                      |
| --------------------- | ------------------------------------------------ |
| `--output <dir>`      | Directory to create the skill in (default: cwd)  |
| `--resources <types>` | Comma-separated list (scripts,references,assets) |

---

## 🐳 Docker-Powered Agent Commands

Manage agent containers locally using Docker Compose.

| Command   | Description                      |
| --------- | -------------------------------- |
| `tx run`  | 🚀 Start agent via Docker Compose |
| `tx stop` | ⏹️ Stop running agent containers  |
| `tx logs` | 📋 Stream agent logs              |
| `tx list` | 📊 List all running agents        |

### `tx run`
Start the agent in the current directory.

| Option        | Description                        |
| ------------- | ---------------------------------- |
| `--no-detach` | Run in foreground (show logs)      |
| `--prod`      | Use production configuration       |
| `--native`    | Skip Docker, run with local Python |

### `tx logs`
| Option           | Description                 |
| ---------------- | --------------------------- |
| `-f`, `--follow` | Follow log output (default) |

---

## 📦 Publishing & Sharing

| Command           | Description                          |
| ----------------- | ------------------------------------ |
| `tx publish`      | 📤 Build and push image to GHCR       |
| `tx pull <agent>` | ⬇️ Download and run a published agent |

### `tx publish`
| Option                           | Description             |
| -------------------------------- | ----------------------- |
| `--tag <tag>`                    | Specify a version tag   |
| `--multiarch` / `--no-multiarch` | Build for AMD64 + ARM64 |
| `--latest` / `--no-latest`       | Also tag as `:latest`   |

---

## 🛠️ Core Commands

| Command          | Description                     |
| ---------------- | ------------------------------- |
| `tx init <name>` | 📁 Create a new agent project    |
| `tx validate`    | ✅ Validate manifest             |
| `tx status`      | 📊 Show CLI configuration status |

---

## 🔐 Authentication

| Command     | Description                          |
| ----------- | ------------------------------------ |
| `tx login`  | 🔑 Authenticate via OAuth Device Flow |
| `tx logout` | 🚪 Clear stored credentials           |
| `tx whoami` | 👤 Display current user               |

---

## 🏢 Organization Management

| Command             | Description                          |
| ------------------- | ------------------------------------ |
| `tx orgs list`      | List available organizations         |
| `tx orgs use <org>` | Switch to a different organization   |
| `tx orgs current`   | Show current organization            |
| `tx orgs refresh`   | Refresh org/project data from server |

---

## 📂 Project Management

| Command                     | Description                    |
| --------------------------- | ------------------------------ |
| `tx projects list`          | List projects in current org   |
| `tx projects use <project>` | Switch to a different project  |
| `tx projects show`          | Show project details           |
| `tx projects create`        | Create a new project           |
| `tx projects create`        | Create a new project           |
| `tx projects keys`          | Manage API keys (see Security) |

---

## 🗂️ Asset Management

| Command            | Description                    |
| ------------------ | ------------------------------ |
| `tx assets list`   | List assets in current project |
| `tx assets create` | Create a new asset             |

---

## 🌌 Stargate P2P Commands

Interact with the decentralized agent network.

### Connection Management

| Command                  | Description                 |
| ------------------------ | --------------------------- |
| `tx stargate connect`    | Connect to the P2P network  |
| `tx stargate disconnect` | Disconnect from the network |
| `tx stargate status`     | Show connection status      |

### Identity Management

| Command                         | Description                |
| ------------------------------- | -------------------------- |
| `tx stargate identity generate` | Create new Ed25519 keypair |
| `tx stargate identity show`     | Display current identity   |
| `tx stargate identity export`   | Export identity to file    |

### Discovery & Communication

| Command                            | Description                              |
| ---------------------------------- | ---------------------------------------- |
| `tx stargate peers`                | List connected peers                     |
| `tx stargate discover`             | Find agents by capability                |
| `tx stargate announce`             | Announce your agent to network           |
| `tx stargate call <peer> <method>` | Send JSON-RPC request to agent           |
| `tx stargate listen`               | Listen for incoming A2A messages (debug) |

### Top-Level Aliases

| Shortcut      | Equivalent             |
| ------------- | ---------------------- |
| `tx discover` | `tx stargate discover` |
| `tx call`     | `tx stargate call`     |
| `tx certify`  | `tx stargate certify`  |

---

## 🧩 Plugin Management

| Command                    | Description                |
| -------------------------- | -------------------------- |
| `tx plugin list`           | Show installed plugins     |
| `tx plugin install <name>` | Install a plugin from PyPI |

---

## 📋 Full Command Tree

```
tx (traylinx)
├── init <name>          # Create agent project
├── validate             # Validate manifest
├── status               # Show CLI status
├── login                # OAuth authentication
├── logout               # Clear credentials
├── whoami               # Show current user
├── run                  # Start agent (Docker)
├── stop                 # Stop agent
├── logs                 # Stream logs
├── list                 # List running agents
├── publish              # Push to GHCR
├── pull <agent>         # Pull and run agent
├── discover             # Find agents (alias)
├── call                 # Call agent (alias)
├── certify              # Request certification (alias)
├── orgs
│   ├── list
│   ├── use <org>
│   ├── current
│   └── refresh
├── projects
│   ├── list
│   ├── use <project>
│   ├── show
│   ├── create
│   └── keys
├── assets
│   ├── list
│   └── create
├── stargate
│   ├── connect
│   ├── disconnect
│   ├── status
│   ├── peers
│   ├── discover
│   ├── announce
│   ├── call <peer> <method>
│   ├── listen
│   └── identity
│       ├── generate
│       ├── show
│       └── export
├── skills
│   ├── list
│   ├── info <name>
│   ├── init <name>
│   ├── validate <path>
│   ├── package <path>
│   └── install <source>
└── plugin
    ├── list
    └── install <name>
```

---

[⬅️ Back to README](../README.md)
