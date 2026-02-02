# Hummingbot Skills

AI agent skills for [Hummingbot](https://hummingbot.org) algorithmic trading infrastructure.

Built on the [Agent Skills](https://agentskills.io) open standard.

## Installation

Using the hummingbot-skills CLI:
```bash
npx hummingbot-skills add
```

Or using the skills CLI:
```bash
npx skills add hummingbot/skills
```

Install specific skills:
```bash
npx hummingbot-skills add portfolio candles-feed
```

## Usage

After installing, ask your AI agent:

- "Create a BTC position with 2% stop loss and 4% take profit"
- "Show me the RSI for ETH on Binance"
- "Add my Binance API keys"
- "Set up Hummingbot with Docker"

## Available Skills

| Skill | Description |
|-------|-------------|
| [hummingbot-api-setup](./skills/hummingbot-api-setup/) | Deploy Hummingbot API infrastructure |
| [keys-manager](./skills/keys-manager/) | Manage spot and perpetual exchange API keys |
| [executor-creator](./skills/executor-creator/) | Create trading executors (position, grid, DCA, TWAP) |
| [candles-feed](./skills/candles-feed/) | Fetch market data and technical indicators |
| [portfolio](./skills/portfolio/) | View balances and positions across exchanges |

## Prerequisites

Skills interact with the Hummingbot API server. Use the `hummingbot-api-setup` skill to deploy it.

Configure credentials via `.env` file (see `.env.example`):
```bash
API_URL=http://localhost:8000
API_USER=admin
API_PASS=admin
```

API docs available at `http://localhost:8000/docs`.

## Repository Structure

```
hummingbot/skills/
├── skills/                     # Skill definitions (SKILL.md + scripts/)
├── cli/                        # hummingbot-skills CLI package
├── app/                        # Next.js webapp (skills.hummingbot.org)
└── .env.example                # API configuration template
```

## Links

- [Skills Webapp](https://skills.hummingbot.org)
- [Hummingbot](https://hummingbot.org)
- [Agent Skills Spec](https://agentskills.io)
