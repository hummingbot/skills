# Hummingbot Skills

Claude Code plugin marketplace for Hummingbot trading infrastructure.

## Quick Reference

```bash
# Claude Code (recommended)
/plugin marketplace add hummingbot/skills
/plugin install trading-skills@hummingbot-skills

# skills.sh CLI
npx skills add hummingbot/skills --skill executor-creator

# Development
./skills/executor-creator/scripts/list_executor_types.sh
```

## Project Structure

```
skills/
├── .claude-plugin/             # Claude Code plugin config
│   └── marketplace.json        # Marketplace definition
├── skills/                     # Skill definitions (SKILL.md + scripts/)
│   ├── hummingbot-api-setup/   # Infrastructure deployment
│   ├── keys-manager/           # API credentials management
│   ├── executor-creator/       # Trading executors
│   └── candles-feed/           # Market data & indicators
├── webapp/                     # skills.hummingbot.org (Next.js)
├── docs/
│   └── webapp-design.md        # Web app design spec
└── skills.json                 # Skills registry for skills.sh
```

## Skill Structure

Each skill follows this structure:

```
skills/<name>/
├── SKILL.md              # Instructions for AI agent (frontmatter + markdown)
└── scripts/              # Executable bash scripts
    ├── action1.sh
    └── action2.sh
```

### SKILL.md Format

```markdown
---
name: <skill-name>
description: What this skill does. When to use it.
license: Apache-2.0
---

# Skill Title

Instructions for the AI agent...
```

## Key Files

| File | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Claude Code plugin marketplace |
| `skills/*/SKILL.md` | Skill instructions for AI agents |
| `skills.json` | Skills registry for skills.sh |
| `docs/webapp-design.md` | Web app design specification |

## Development Guidelines

- **No fallback values**: Fetch data dynamically from APIs
- **No mock data**: Throw clear errors instead
- **Dynamic fetching**: Prefer real-time data over hardcoded values

## API Server

The skills interact with the Hummingbot API server:

- **Default URL**: `http://localhost:8000`
- **Default credentials**: `admin:admin`
- **Environment variables**: `API_URL`, `API_USER`, `API_PASS`
- **Docs**: `http://localhost:8000/docs`

## Links

- [Hummingbot](https://hummingbot.org)
- [skills.sh](https://skills.sh)
- [Claude Code Plugins](https://code.claude.com/docs/en/discover-plugins)
