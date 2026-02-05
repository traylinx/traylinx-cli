# Getting Started with Traylinx Cortex

> **Natural Language CLI Interface for Traylinx**

Cortex lets you control Traylinx using natural language instead of memorizing CLI commands.

## Quick Start

```bash
# Start an interactive chat session
tx cortex chat

# Or run a single command
tx cortex chat "start my agent"
```

## Features

### 💬 Natural Language Commands

Instead of memorizing CLI syntax, just say what you want:

| What you type                    | What happens            |
| -------------------------------- | ----------------------- |
| "start my agent"                 | `tx run --detach`       |
| "show me the logs"               | `tx logs`               |
| "find agents that can translate" | `tx discover translate` |
| "stop it"                        | `tx stop <last agent>`  |

### 🔄 Multi-Turn Conversations

Cortex remembers context:

```
You: find agents that can search
Cortex: Found 3 agents with 'search' capability...
You: call the first one
Cortex: Calling agent-1/search-service...
```

### 🧠 Smart Suggestions

After each command, Cortex suggests next actions:

```
You: start my agent
Cortex: ✅ Agent started!
        💡 Suggestions:
        1. View logs
        2. Check status
```

### ⛓️ Command Chaining

Execute multiple commands at once:

```
You: start my agent and show logs
Cortex: Starting agent... ✅
        Showing logs... 📝
```

## Available Commands

### Agent Lifecycle
- **start/run** - Start your agent
- **stop/kill** - Stop running agent
- **logs/tail** - View agent logs
- **status** - Check agent status

### Discovery & Networking
- **find/discover** - Find agents on the network
- **call** - Call another agent

### Authentication
- **whoami** - Show current identity
- **login** - Sign in to Sentinel
- **logout** - Sign out

### Build & Publish
- **build** - Build your agent
- **validate** - Validate config
- **publish** - Publish to registry

## Special Commands

| Command    | Description          |
| ---------- | -------------------- |
| `/help`    | Show help            |
| `/history` | Show command history |
| `/clear`   | Clear screen         |
| `/exit`    | Exit chat            |

## Options

```bash
tx cortex chat --no-llm    # Use pattern matching only (faster, offline)
```

## Configuration

Cortex stores configuration in `~/.traylinx/cortex/`:

- `PERSONA.md` - Customize Cortex's personality
- `USER.md` - Your preferences
- `TOOLS.md` - Tool usage notes

## Examples

```bash
# Interactive session
tx cortex chat
> start my agent in background
> show me errors in the logs
> stop it

# One-shot commands
tx cortex chat "check if I'm logged in"
tx cortex chat "find agents that can translate documents"
```
