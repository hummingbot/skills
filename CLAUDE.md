# Hummingbot Skills

Skills repository for AI agents to interact with Hummingbot trading infrastructure.

**Inspired by**: [skills.sh](https://skills.sh) / [agentskills.io](https://agentskills.io)

## Quick Reference

```bash
# Install all skills
npx skills add hummingbot/skills

# Install specific skill
npx skills add hummingbot/skills --skill executors

# Development
./skills/executors/scripts/create_position.sh --help
```

## Project Structure

```
skills/
├── skills/                 # Skill definitions (each has SKILL.md + scripts/)
│   ├── executors/          # Trading executors
│   ├── candles/            # Market data & indicators
│   ├── keys/               # API credentials management
│   └── setup/              # Infrastructure deployment
├── webapp/                 # skills.hummingbot.org (Next.js)
├── docs/
│   └── webapp-design.md    # Web app design spec
└── skills.json             # Skills registry
```

## Naming Conventions

- **Repo**: `hummingbot/skills`
- **Web URL**: `skills.hummingbot.org`
- **Skills**: Named by function (e.g., `executors`, `candles`, `keys`)
- **Install**: `npx skills add hummingbot/skills --skill <name>`

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
name: hummingbot-<name>
description: What this skill does
version: 1.0.0
author: Hummingbot Foundation
triggers:
  - keyword1
  - keyword2
---

# Skill Name

Instructions for the AI agent...
```

## Key Files

| File | Purpose |
|------|---------|
| `skills.json` | Registry of available skills with metadata |
| `skills/*/SKILL.md` | Skill instructions for AI agents |
| `docs/webapp-design.md` | Web app design specification |

## Development Guidelines

- **No fallback values**: Fetch data dynamically from APIs
- **No mock data**: Throw clear errors instead
- **No deprecated methods**: Update all references directly
- **Dynamic fetching**: Prefer real-time data over hardcoded values

## Supported AI Agents

| Agent | Project Path | Global Path |
|-------|--------------|-------------|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Cursor | `.cursor/skills/` | `~/.cursor/skills/` |
| Windsurf | `.windsurf/skills/` | `~/.windsurf/skills/` |
| VS Code | `.github/skills/` | `~/.vscode/skills/` |
| OpenCode | `.opencode/skills/` | `~/.opencode/skills/` |
| Goose | `.goose/skills/` | `~/.goose/skills/` |
| Gemini CLI | `.gemini/skills/` | `~/.gemini/skills/` |
| Codex | `.codex/skills/` | `~/.codex/skills/` |

## TODO

### Skills (`skills/`)
- [ ] Complete `setup/` scripts (steps 3-8 not implemented)
- [ ] Add `test-spot/` skill for spot connector QA
- [ ] Add `test-perp/` skill for perpetual connector QA
- [ ] Add `test-gateway/` skill for Gateway connector QA
- [ ] Add `create-pmm/` skill for PMM controller bots

### Webapp (`webapp/`)
- [ ] Initialize Next.js 15 with App Router
- [ ] Apply HBUI theme (dark bg, green accent)
- [ ] Build Hero component with ASCII art
- [ ] Build SkillsLeaderboard component
- [ ] Build skill detail pages with markdown rendering
- [ ] Add search/filter functionality
- [ ] Add install tracking analytics
- [ ] Deploy to Vercel at skills.hummingbot.org
- [ ] Add Playwright E2E tests

### Registry (`skills.json`)
- [ ] Add install counts structure
- [ ] Add `first_seen` timestamps
- [ ] Sync with actual skill files

## API Server

The skills interact with the Hummingbot API server:

- **Default URL**: `http://localhost:8000`
- **Default credentials**: `admin:admin`
- **Environment variables**: `API_URL`, `API_USER`, `API_PASS`
- **Health check**: `GET /api/v1/executors`

## Skill Categories

| Category | Description |
|----------|-------------|
| `trading` | Executors, strategies |
| `configuration` | API keys, credentials |
| `data` | Market data, indicators |
| `infrastructure` | Deployment, setup, Docker |
| `qa` | Testing, validation |
| `bots` | Controller bots |

## Links

- [Hummingbot](https://hummingbot.org)
- [skills.sh](https://skills.sh)
- [Agent Skills Spec](https://agentskills.io)
