# Hummingbot Skills

AI agent skills for [Hummingbot](https://hummingbot.org) algorithmic trading infrastructure.

Built on the [Agent Skills](https://agentskills.io) open standard.

## Quick Start

```bash
npx hummingbot-skills add
```

This installs all Hummingbot skills to your AI agents (Claude Code, Cursor, etc.).

## Available Skills

| Skill | Description |
|-------|-------------|
| [hummingbot-api-setup](./skills/hummingbot-api-setup/) | Deploy Hummingbot API infrastructure |
| [keys-manager](./skills/keys-manager/) | Manage spot and perpetual exchange API keys |
| [executor-creator](./skills/executor-creator/) | Create trading executors (position, grid, DCA, TWAP) |
| [candles-feed](./skills/candles-feed/) | Fetch market data and technical indicators |
| [portfolio](./skills/portfolio/) | View balances and positions across exchanges |

## Usage

After installing, ask your AI agent:

- "Create a BTC position with 2% stop loss and 4% take profit"
- "Show me the RSI for ETH on Binance"
- "Add my Binance API keys"
- "Set up Hummingbot with Docker"

## Prerequisites

Skills interact with the Hummingbot API server. Use the `hummingbot-api-setup` skill to deploy it.

Configure credentials via `.env` file:
```bash
API_URL=http://localhost:8000
API_USER=admin
API_PASS=admin
```

## Repository Structure

This is a monorepo containing skills, CLI, and webapp:

```
hummingbot/skills/
├── skills/           # Skill definitions (SKILL.md + scripts/)
├── cli/              # hummingbot-skills CLI (npm package)
├── app/              # Next.js webapp (skills.hummingbot.org)
└── .github/          # CI/CD workflows
```

| Component | Description | Docs |
|-----------|-------------|------|
| **skills/** | Trading skill definitions | Each skill has its own README |
| **cli/** | `hummingbot-skills` npm package | [cli/README.md](./cli/README.md) |
| **app/** | Skills browser webapp | [app/README.md](./app/README.md) |

## Development

### Skills

Each skill is a folder with:
- `SKILL.md` - Skill definition with frontmatter metadata
- `scripts/` - Shell scripts the agent can execute

### CLI

```bash
cd cli
npm install
npm run build
npm link  # For local testing
```

See [cli/README.md](./cli/README.md) for publishing instructions.

### Webapp

```bash
cd app
npm install
npm run dev
```

See [app/README.md](./app/README.md) for deployment instructions.

## Links

- [Skills Webapp](https://skills.hummingbot.org)
- [CLI on npm](https://www.npmjs.com/package/hummingbot-skills)
- [Hummingbot](https://hummingbot.org)
- [Hummingbot API](https://hummingbot.org/hummingbot-api/)
- [Agent Skills Spec](https://agentskills.io)
