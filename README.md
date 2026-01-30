# Hummingbot Skills

AI agent skills for [Hummingbot](https://hummingbot.org) algorithmic trading infrastructure.

## Installation

### Option 1: Claude Code Plugin

```
/plugin marketplace add hummingbot/skills
/plugin install hummingbot-skills@hummingbot-skills
```

### Option 2: skills.sh CLI

```bash
npx skills add hummingbot/skills
```

Or install a specific skill:
```bash
npx skills add hummingbot/skills --skill executor-creator
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
| [hummingbot-api-setup](./skills/hummingbot-api-setup/) | Deploy Hummingbot infrastructure (Docker, API, Gateway) |
| [keys-manager](./skills/keys-manager/) | Manage exchange API credentials |
| [executor-creator](./skills/executor-creator/) | Create trading executors (position, grid, DCA, TWAP) |
| [candles-feed](./skills/candles-feed/) | Fetch market data and technical indicators |

## Prerequisites

Skills interact with the Hummingbot API server:
- **URL**: `http://localhost:8000`
- **Credentials**: `admin:admin`
- **Docs**: `http://localhost:8000/docs`

Use the `hummingbot-api-setup` skill to deploy the API server.

## Repository Structure

```
hummingbot/skills/
├── .claude-plugin/             # Claude Code marketplace config
│   └── marketplace.json
├── skills/                     # Skill definitions
│   ├── hummingbot-api-setup/   # Infrastructure setup
│   ├── keys-manager/           # API credentials
│   ├── executor-creator/       # Trading executors
│   └── candles-feed/           # Market data
├── webapp/                     # skills.hummingbot.org
└── skills.json                 # Registry for skills.sh
```

## Links

- [Hummingbot](https://hummingbot.org)
- [skills.sh](https://skills.sh)
- [skills.hummingbot.org](https://skills.hummingbot.org)
