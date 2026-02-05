# 🚀 Skills Quick Start Guide

## What Are Skills?

Skills are modular packages that extend AI agents with specialized knowledge and capabilities. Each skill contains instructions, scripts, and reference materials.

## Installation

### Default Installation (Recommended)
Skills are installed to `~/.traylinx/skills/` by default:

```bash
# Install from a skill directory
tx skills install ./my-skill

# Install from a .skill package
tx skills install ./my-skill.skill

# Install from another location (e.g., OpenClaw skills)
tx skills install ../openclaw/skills/weather
```

### Custom Installation Location
Use the `--target` flag to install elsewhere:

```bash
tx skills install ./my-skill --target /custom/path/skills
```

## Discovery

### List All Skills
```bash
# List all discovered skills
tx skills list

# Show detailed information about a skill
tx skills info weather
```

Skills are discovered from:
1. `~/.traylinx/skills/` (global skills)
2. `./.traylinx/skills/` (project-local skills)

## Creating Skills

### 1. Initialize
```bash
tx skills init my-skill --resources scripts,references
```

### 2. Edit SKILL.md
Add instructions and metadata:

```markdown
---
name: my-skill
description: What this skill does and when to use it
---

# My Skill

Instructions for the AI agent...
```

### 3. Validate
```bash
tx skills validate ./my-skill
```

### 4. Package (Optional)
```bash
tx skills package ./my-skill
```

### 5. Install
```bash
# Installs to ~/.traylinx/skills/ by default
tx skills install ./my-skill
```

## Example: Installing OpenClaw Skills

```bash
# Install weather skill
tx skills install ../openclaw/skills/weather

# Install GitHub skill
tx skills install ../openclaw/skills/github

# Install Notion skill
tx skills install ../openclaw/skills/notion

# List installed skills
tx skills list
```

## Skill Structure

```
my-skill/
├── SKILL.md           # Required: Instructions and metadata
├── scripts/           # Optional: Executable scripts
├── references/        # Optional: Documentation and schemas
└── assets/            # Optional: Templates and static files
```

## Tips

- Skills in `~/.traylinx/skills/` are available globally
- Skills in `./.traylinx/skills/` are project-specific
- Use `tx skills info <name>` to see full instructions
- The `--target` flag is optional; default is `~/.traylinx/skills/`

---

[📚 Full Skills Guide](./SKILLS_GUIDE.md) | [⬅️ Back to README](../README.md)
