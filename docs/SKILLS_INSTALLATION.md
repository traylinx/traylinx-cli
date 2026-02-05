# 📦 Skills Installation Guide

## Overview

The Traylinx CLI provides a complete skills management system that allows you to discover, create, validate, package, and install AgentSkills.

## Installation Locations

### Default Location (Recommended)
Skills are installed to `~/.traylinx/skills/` by default. This is the **global skills library** accessible to all agents.

```bash
# Install to default location (~/.traylinx/skills/)
tx skills install ./my-skill
```

### Custom Location (Optional)
Use the `--target` flag to install to a custom directory:

```bash
# Install to custom location
tx skills install ./my-skill --target /custom/path/skills
```

### Project-Local Skills
You can also place skills in `./.traylinx/skills/` within your project directory for project-specific skills.

## Discovery Paths

The CLI searches for skills in the following order:

1. **Global**: `~/.traylinx/skills/`
2. **Project-local**: `./.traylinx/skills/` (current working directory)
3. **Additional paths**: Specified via `--path` flag

```bash
# List skills from all default locations
tx skills list

# Include additional search path
tx skills list --path /custom/skills
```

## Installation Methods

### 1. From Skill Directory

Install directly from a skill source directory:

```bash
tx skills install ./my-skill
# ✅ Installs to ~/.traylinx/skills/my-skill
```

### 2. From .skill Package

Install from a packaged `.skill` file (zip archive):

```bash
tx skills install ./my-skill.skill
# ✅ Extracts to ~/.traylinx/skills/
```

### 3. From External Sources

Install skills from other repositories (e.g., OpenClaw):

```bash
# Install OpenClaw weather skill
tx skills install ../openclaw/skills/weather

# Install multiple skills
tx skills install ../openclaw/skills/github
tx skills install ../openclaw/skills/notion
```

## Complete Workflow Example

### Creating and Installing a New Skill

```bash
# 1. Initialize a new skill
tx skills init weather-api --resources scripts,references

# 2. Edit the SKILL.md file
# Add instructions, metadata, and examples

# 3. Add scripts and references
# Place files in scripts/ and references/ directories

# 4. Validate the skill
tx skills validate ./weather-api

# 5. (Optional) Package for distribution
tx skills package ./weather-api
# Creates: weather-api.skill

# 6. Install to global library
tx skills install ./weather-api
# ✅ Installed to ~/.traylinx/skills/weather-api

# 7. Verify installation
tx skills list
tx skills info weather-api
```

## Installation Verification

After installing skills, verify they are available:

```bash
# List all installed skills
tx skills list

# Show detailed information
tx skills info <skill-name>

# Check installation location
ls -la ~/.traylinx/skills/
```

## Directory Structure

After installation, your skills directory looks like this:

```
~/.traylinx/skills/
├── weather/
│   ├── SKILL.md
│   └── (optional resources)
├── github/
│   ├── SKILL.md
│   └── (optional resources)
└── notion/
    ├── SKILL.md
    └── (optional resources)
```

## Best Practices

1. **Use default location**: Install to `~/.traylinx/skills/` for global availability
2. **Validate before installing**: Always run `tx skills validate` first
3. **Use descriptive names**: Choose clear, kebab-case names (e.g., `weather-api`)
4. **Document thoroughly**: Provide clear instructions in `SKILL.md`
5. **Version your skills**: Use git or package versioning for skill updates

## Troubleshooting

### Skill Not Found After Installation

```bash
# Check if skill directory exists
ls -la ~/.traylinx/skills/

# Verify SKILL.md exists
cat ~/.traylinx/skills/my-skill/SKILL.md

# Re-run discovery
tx skills list
```

### Permission Issues

```bash
# Ensure directory has correct permissions
chmod 700 ~/.traylinx/skills/

# Check ownership
ls -la ~/.traylinx/
```

### Validation Errors

```bash
# Validate before installing
tx skills validate ./my-skill

# Check SKILL.md frontmatter format
# Must have:
# ---
# name: skill-name
# description: Skill description
# ---
```

## Environment Variables

Override the default skills directory:

```bash
# Set custom state directory (includes skills/)
export TRAYLINX_STATE_DIR=/custom/path

# Skills will be in /custom/path/skills/
tx skills install ./my-skill
```

## Related Documentation

- [Skills Guide](./SKILLS_GUIDE.md) - Complete guide to creating skills
- [Skills Quick Start](./SKILLS_QUICKSTART.md) - Quick reference
- [Command Reference](./COMMAND_REFERENCE.md) - All CLI commands

---

[⬅️ Back to README](../README.md)
