# Skills

Skills are reusable instruction sets that extend the agent's capabilities. Each skill is a `SKILL.md` file in its own directory, providing specialized knowledge, workflows, and tool integrations for specific tasks.

## Skill Hub

Skills can be installed from GitHub, ClawHub, local directories, or URLs.

## Install Skills

Install skills from multiple sources via chat (`/skill`) or terminal (`myclaw skill`):

```bash
/skill install <name>                   # From skill hub
/skill install <owner>/<repo>           # From GitHub
/skill install clawhub:<name>           # From ClawHub
/skill install <url>                    # From URL (zip or SKILL.md)
```

List all available remote skills:

```bash
/skill list --remote
```

## Manage Skills

```bash
/skill list                  # List installed skills
/skill info <name>           # View skill details
/skill enable <name>         # Enable a skill
/skill disable <name>        # Disable a skill
/skill uninstall <name>      # Uninstall a skill
```

> In terminal, replace `/skill` with `myclaw skill`.

## Skill Structure

```
skills/
  my-skill/
    SKILL.md          # Required: skill definition
    scripts/          # Optional: bundled scripts
    resources/        # Optional: reference files
```

`SKILL.md` uses YAML frontmatter:

```markdown
---
name: my-skill
description: Brief description of what the skill does
metadata: {"myclaw":{"emoji":"🔧","requires":{"bins":["tool"],"env":["API_KEY"]}}}
---

# My Skill

Instructions, examples, and usage patterns...
```

### Frontmatter Fields

| Field | Description |
|---|---|
| `name` | Skill name (must match directory name) |
| `description` | Brief description (required) |
| `metadata.myclaw.emoji` | Display emoji |
| `metadata.myclaw.always` | Always include this skill (default: false) |
| `metadata.myclaw.requires.bins` | Required binaries |
| `metadata.myclaw.requires.env` | Required environment variables |
| `metadata.myclaw.requires.config` | Required config paths |
| `metadata.myclaw.os` | Supported OS (e.g., `["darwin", "linux"]`) |

## Skill Loading Order

Skills are loaded from two locations (higher precedence overrides lower):

1. **Builtin skills** (lower): `<project_root>/skills/` — shipped with the codebase
2. **Custom skills** (higher): `~/myclaw/skills/` — installed via `myclaw skill install` or skill creator

Skills with the same name in the custom directory override builtin ones.

## Create & Contribute

To create a skill, write a `SKILL.md` with YAML frontmatter and place it in its own directory under `skills/` or `~/myclaw/skills/`.
