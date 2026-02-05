# Publishing Agents Guide

Complete guide to publishing agents to the Traylinx catalog using the CLI.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Understanding Sentinel Passes](#understanding-sentinel-passes)
- [Step-by-Step Guide](#step-by-step-guide)
- [Credential Storage](#credential-storage)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Overview

Publishing agents to the Traylinx catalog makes them discoverable by other users and systems. The publishing process uses **Sentinel Pass** authentication to verify your identity.

### What You'll Need

1. **Developer Sentinel Pass** - Your identity for publishing (created once)
2. **Agent Manifest** - Your agent's configuration file (`agent.yaml`)
3. **Traylinx Account** - Active account with `traylinx login`

---

## Prerequisites

### 1. Login to Traylinx

```bash
traylinx login
```

You must be logged in to create Sentinel Passes.

### 2. Create Agent Manifest

```bash
traylinx init
```

This creates an `agent.yaml` file with your agent's metadata.

---

## Quick Start

```bash
# 1. Create your developer identity (ONE TIME)
traylinx sentinel pass create --name my-developer-identity

# 2. Set environment variables (ONE TIME)
export TRAYLINX_DEVELOPER_AGENT_ID="agent-user-xxx"
export TRAYLINX_DEVELOPER_SECRET="secret-xxx"

# 3. Publish your agent (EVERY TIME)
traylinx publish
```

---

## Understanding Sentinel Passes

### Two Types of Sentinel Passes

Publishing requires understanding **TWO different Sentinel Passes**:

#### 1. Developer Sentinel Pass (For YOU)

**Purpose:** Authenticate when publishing agents  
**Created:** Once per developer  
**Used by:** `traylinx publish` command  
**Stored in:** `~/.traylinx/agents/my-developer-identity/`

```bash
traylinx sentinel pass create --name my-developer-identity
```

#### 2. Agent Sentinel Pass (For YOUR AGENT)

**Purpose:** Agent's runtime identity  
**Created:** Once per agent  
**Used by:** The agent when it runs  
**Stored in:** `~/.traylinx/agents/my-agent-name/`

```bash
traylinx sentinel pass create --name my-weather-agent
```

### Why Two Different Passes?

| Aspect | Developer Pass | Agent Pass |
|--------|---------------|------------|
| **Purpose** | Authenticate publishing | Agent runtime identity |
| **Who uses it** | You (via CLI) | The agent (when running) |
| **When** | During `traylinx publish` | During agent execution |
| **Env vars** | `TRAYLINX_DEVELOPER_*` | `TRAYLINX_CLIENT_*` |

**Key Point:** You use YOUR Sentinel Pass to publish the agent. The agent uses ITS OWN Sentinel Pass when running.

---

## Step-by-Step Guide

### Step 1: Create Developer Sentinel Pass

This is a **ONE-TIME** setup per developer.

```bash
$ traylinx sentinel pass create --name my-developer-identity
```

**Output:**
```
✅ Sentinel Pass created successfully!

   Pass ID:       SP-2026-abc123
   Agent Name:    my-developer-identity
   Agent ID:      agent-user-789abc
   Client ID:     oauth-client-456def
   Client Secret: secret-xyz123...
   Saved to:      ~/.traylinx/agents/my-developer-identity/credentials.json

⚠ The client_secret is shown ONCE. Store it securely!

To use this agent, set these environment variables:
  export TRAYLINX_CLIENT_ID="oauth-client-456def"
  export TRAYLINX_CLIENT_SECRET="secret-xyz123..."
  export TRAYLINX_AGENT_USER_ID="agent-user-789abc"
```

**Important:** Save the `Agent ID` and `Client Secret` - you'll need them next!

### Step 2: Set Environment Variables

Add these to your shell profile (`~/.zshrc` or `~/.bashrc`):

```bash
# Traylinx Developer Credentials (for publishing)
export TRAYLINX_DEVELOPER_AGENT_ID="agent-user-789abc"
export TRAYLINX_DEVELOPER_SECRET="secret-xyz123..."
```

**Reload your shell:**
```bash
source ~/.zshrc
```

**Verify:**
```bash
$ echo $TRAYLINX_DEVELOPER_AGENT_ID
agent-user-789abc

$ echo $TRAYLINX_DEVELOPER_SECRET
secret-xyz123...
```

### Step 3: Check Status

Verify your publishing identity is configured:

```bash
$ traylinx status
```

**Expected output:**
```
⚙️  Configuration
Environment: dev
Registry: https://discovery.traylinx.com
Publishing Identity: ✓ Configured (agent-user-789abc)
```

### Step 4: Publish Your Agent

```bash
$ cd /path/to/your/agent
$ traylinx publish
```

**Expected output:**
```
Publishing to Traylinx Catalog

✓ Manifest valid: my-weather-agent v1.0.0
✓ Registry: https://discovery.traylinx.com
✓ Publishing Identity: agent-user-789abc

Publishing...

╭─────────────────────────────────────────╮
│ 🚀 Published                            │
│                                         │
│ Published successfully!                 │
│                                         │
│ Agent: my-weather-agent                 │
│ Version: 1.0.0                          │
│                                         │
│ View in catalog:                        │
│   https://discovery.traylinx.com/...   │
╰─────────────────────────────────────────╯
```

---

## Credential Storage

All Traylinx credentials are stored in `~/.traylinx/`:

```
~/.traylinx/
├── credentials.json              # OAuth login credentials
├── context.json                  # Current org/project context
├── agents/                       # Sentinel Pass credentials
│   ├── my-developer-identity/
│   │   └── credentials.json      # Developer Sentinel Pass
│   └── my-weather-agent/
│       └── credentials.json      # Agent Sentinel Pass
└── keys/                         # API keys
    └── key-abc123_production.json
```

### Credential Files

**OAuth Credentials** (`~/.traylinx/credentials.json`):
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "user": {
    "id": "user-123",
    "email": "you@example.com"
  }
}
```

**Sentinel Pass** (`~/.traylinx/agents/my-developer-identity/credentials.json`):
```json
{
  "agent_id": "agent-user-789abc",
  "client_id": "oauth-client-456def",
  "client_secret": "secret-xyz123...",
  "pass_id": "SP-2026-abc123",
  "agent_type": "service",
  "project_id": "proj-xxx",
  "org_id": "org-yyy",
  "created_at": "2026-02-05T10:30:00",
  "linked": true
}
```

### Security

- **Permissions:** All credential files are created with `0600` (read/write for owner only)
- **Location:** Stored in your home directory (`~/.traylinx/`)
- **Backup:** Consider backing up `~/.traylinx/agents/` to avoid losing Sentinel Passes

---

## Troubleshooting

### Error: Developer credentials not set

**Symptom:**
```
Error: Developer credentials not set

Publishing requires a Sentinel Pass for authentication.
```

**Solution:**

1. Check if Sentinel Pass exists:
   ```bash
   traylinx sentinel pass list
   ```

2. If not listed, create one:
   ```bash
   traylinx sentinel pass create --name my-developer-identity
   ```

3. Set environment variables:
   ```bash
   export TRAYLINX_DEVELOPER_AGENT_ID="agent-user-xxx"
   export TRAYLINX_DEVELOPER_SECRET="secret-xxx"
   ```

4. Verify:
   ```bash
   echo $TRAYLINX_DEVELOPER_AGENT_ID
   ```

### Error: 401 Unauthorized

**Symptom:**
```
Publish Failed: Publish failed (401): Unauthorized
```

**Possible causes:**

1. **Wrong credentials:**
   - Verify `TRAYLINX_DEVELOPER_AGENT_ID` matches your Sentinel Pass
   - Verify `TRAYLINX_DEVELOPER_SECRET` is correct

2. **Expired/deleted Sentinel Pass:**
   - Check if pass still exists:
     ```bash
     traylinx sentinel pass show my-developer-identity
     ```
   - If deleted, create a new one

3. **Not logged in:**
   - Login first:
     ```bash
     traylinx login
     ```

### Error: Manifest not found

**Symptom:**
```
Error: Manifest not found: agent.yaml
```

**Solution:**
```bash
# Create manifest first
traylinx init

# Then publish
traylinx publish
```

### Check Publishing Identity Status

```bash
$ traylinx status

⚙️  Configuration
Environment: dev
Registry: https://discovery.traylinx.com
Publishing Identity: ✓ Configured (agent-user-789abc)
```

If you see `Publishing Identity: ✗ Not configured`, set your environment variables.

---

## Advanced Usage

### Publish to Different Registry

```bash
traylinx publish --registry http://localhost:8000
```

### Dry Run (Test Without Publishing)

```bash
traylinx publish --dry-run
```

**Output:**
```
╭─────────────────────────────────────────╮
│ 🧪 Dry Run                              │
│                                         │
│ Would publish:                          │
│   Agent: my-weather-agent               │
│   Version: 1.0.0                        │
│   To: https://discovery.traylinx.com    │
╰─────────────────────────────────────────╯
```

### Custom Manifest Path

```bash
traylinx publish --manifest /path/to/custom-manifest.yaml
```

---

## FAQ

### Q: Do I need a Sentinel Pass for every agent I publish?

**A:** No! You need:
- **ONE** Sentinel Pass for YOU (developer) - used for publishing all agents
- **ONE** Sentinel Pass per agent - used when each agent runs

### Q: Can I use the same Sentinel Pass for publishing and running?

**A:** Technically yes, but **not recommended**. Keep them separate:
- Developer Sentinel Pass = YOUR identity (for publishing)
- Agent Sentinel Pass = AGENT's identity (for runtime)

This separation allows better access control and auditing.

### Q: What if I lose my developer credentials?

**A:** Create a new Sentinel Pass:
```bash
traylinx sentinel pass create --name my-developer-identity-2
```

Then update your environment variables. Your old Sentinel Pass will remain in `~/.traylinx/agents/` but won't be used.

### Q: Can multiple developers publish the same agent?

**A:** Yes! Each developer creates their own Sentinel Pass. The registry tracks who published each version.

### Q: Do I need to be logged in to publish?

**A:** No! Publishing uses Sentinel Pass credentials, not OAuth login. However, you need to be logged in to **create** Sentinel Passes.

### Q: Where are my credentials stored?

**A:** All credentials are stored in `~/.traylinx/`:
- OAuth: `~/.traylinx/credentials.json`
- Sentinel Passes: `~/.traylinx/agents/<name>/credentials.json`
- API Keys: `~/.traylinx/keys/<key-id>_<note>.json`

### Q: How do I view my Sentinel Passes?

**A:** Use these commands:
```bash
# List all Sentinel Passes
traylinx sentinel pass list

# Show details of a specific pass
traylinx sentinel pass show my-developer-identity
```

### Q: Can I delete a Sentinel Pass?

**A:** Yes:
```bash
# Delete local only
traylinx sentinel pass delete my-developer-identity

# Delete local AND revoke remote credentials
traylinx sentinel pass delete my-developer-identity --remote
```

---

## Quick Reference

### Commands

```bash
# Sentinel Pass Management
traylinx sentinel pass create --name <name>
traylinx sentinel pass list
traylinx sentinel pass show <name>
traylinx sentinel pass delete <name>

# Publishing
traylinx publish
traylinx publish --dry-run
traylinx publish --registry <url>
traylinx publish --manifest <path>

# Status
traylinx status
```

### Environment Variables

```bash
# For publishing (YOUR credentials)
export TRAYLINX_DEVELOPER_AGENT_ID="agent-user-xxx"
export TRAYLINX_DEVELOPER_SECRET="secret-xxx"

# For agent runtime (AGENT's credentials)
export TRAYLINX_CLIENT_ID="oauth-client-xxx"
export TRAYLINX_CLIENT_SECRET="secret-xxx"
export TRAYLINX_AGENT_USER_ID="agent-user-xxx"
```

### File Locations

```bash
# OAuth credentials
~/.traylinx/credentials.json

# Sentinel Pass credentials
~/.traylinx/agents/<name>/credentials.json

# API keys
~/.traylinx/keys/<key-id>_<note>.json

# Context (current org/project)
~/.traylinx/context.json
```

---

## Next Steps

- **Learn more:** See [Command Reference](COMMAND_REFERENCE.md) for all CLI commands
- **Agent development:** See [Setup Guide](SETUP_GUIDE.md) for creating agents
- **Troubleshooting:** Check `traylinx status` for configuration issues

---

**Need help?** Contact support or check the [Traylinx Documentation Hub](https://docs.traylinx.com)
