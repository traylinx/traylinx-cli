# 🎯 AgentSkills Guide

AgentSkills are modular, reusable packages that extend your AI agent's capabilities with specialized knowledge, workflows, and tools. They transform a general-purpose agent into a domain expert equipped with procedural knowledge.

## 📁 Skill Structure

Every skill consists of a mandatory `SKILL.md` file and optional resource directories:

```text
my-skill/
├── SKILL.md (required)     # Core instructions and metadata
├── scripts/                # Executable code (Python/Bash)
├── references/             # Documentation and schemas
└── assets/                 # Templates, icons, and static files
```

### `SKILL.md` Specification

The `SKILL.md` file must contain YAML frontmatter:

```markdown
---
name: my-skill
description: Comprehensive description for triggering the skill.
---

# My Skill Instructions
... instructions for the AI ...
```


## 🛠️ Working with Skills

### 1. Initialize a New Skill

Scaffold a skill directory with a template `SKILL.md`:

```bash
tx skills init my-new-skill --resources scripts,references
```


### 2. Implementation

- **Edit `SKILL.md`**: Provide clear, imperative instructions for the agent.
- **Add Resources**: Place executable scripts in `scripts/` and reference material in `references/`.

### 3. Validation

Ensure your skill meets the AgentSkills specification:

```bash
tx skills validate ./my-new-skill
```

### 4. Packaging

Package your skill for distribution as a `.skill` file (a specialized zip archive):

```bash
tx skills package ./my-new-skill
```

### 5. Installation

Install skills into your global library. By default, skills are installed to `~/.traylinx/skills/`:

```bash
# Install from .skill package (installs to ~/.traylinx/skills/ by default)
tx skills install ./my-new-skill.skill

# Install from source directory (installs to ~/.traylinx/skills/ by default)
tx skills install ./my-new-skill

# Install to custom location (optional)
tx skills install ./my-new-skill --target /custom/path/skills
```

## 🔍 Discovery

List all skills in your global library and current project:

```bash
tx skills list
```

Show detailed information and instructions for a specific skill:

```bash
tx skills info my-skill
```

---

[⬅️ Back to README](../README.md)
