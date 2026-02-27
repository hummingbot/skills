# Hummingbot Skills

AI agent skills for [Hummingbot](https://hummingbot.org) algorithmic trading infrastructure.

Built on the [Agent Skills](https://agentskills.io) open standard.

## Quick Start

```bash
npx skills add hummingbot/skills
```

This installs Hummingbot skills to your AI agents (Claude Code, Cursor, etc.).

## Commands

```bash
npx skills add hummingbot/skills                              # Install all skills
npx skills add hummingbot/skills --skill hummingbot-deploy    # Install specific skill
npx skills list                                               # List installed skills
npx skills remove                                             # Remove installed skills
```

## Available Skills

| Skill | Description |
|-------|-------------|
| [hummingbot-deploy](./skills/hummingbot-deploy/) | Deploy Hummingbot API server, MCP server, and Condor Telegram bot |
| [hummingbot](./skills/hummingbot/) | Hummingbot CLI commands (connect, balance, create, start, stop, status, history) via API |
| [lp-agent](./skills/lp-agent/) | Automated liquidity provision on CLMM DEXs (Meteora/Solana) |
| [connectors-available](./skills/connectors-available/) | Check exchange availability and search token trading rules |
| [find-arbitrage-opps](./skills/find-arbitrage-opps/) | Find arbitrage opportunities across exchanges for fungible pairs |
| [slides-generator](./skills/slides-generator/) | Create Hummingbot-branded PDF slides from markdown |

## Usage

After installing, ask your AI agent:

- "Deploy Hummingbot API"
- "Open a liquidity position on Meteora"

## Prerequisites

Skills interact with the Hummingbot API server. Use the `hummingbot-deploy` skill to deploy it.

Configure credentials via `.env` file:
```bash
API_URL=http://localhost:8000
API_USER=admin
API_PASS=admin
```

## Repository Structure

```
hummingbot/skills/
├── skills/           # Skill definitions (SKILL.md + scripts/)
├── app/              # Next.js webapp (skills.hummingbot.org)
└── .github/          # CI/CD workflows
```

| Component | Description | Docs |
|-----------|-------------|------|
| **skills/** | Trading skill definitions | Each skill has its own README |
| **app/** | Skills browser webapp | [app/README.md](./app/README.md) |

## Development

### Skills

Each skill is a folder with:
- `SKILL.md` - Skill definition with frontmatter metadata
- `scripts/` - Shell scripts the agent can execute

### Webapp

```bash
cd app
npm install
npm run dev
```

See [app/README.md](./app/README.md) for deployment instructions.

## Links

- [Skills Webapp](https://skills.hummingbot.org)
- [Hummingbot](https://hummingbot.org)
- [Hummingbot API](https://hummingbot.org/hummingbot-api/)
- [Agent Skills Spec](https://agentskills.io)
