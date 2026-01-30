# Hummingbot Skills

Reusable capabilities for AI agents to interact with [Hummingbot](https://hummingbot.org) trading infrastructure.

```bash
npx skills add hummingbot/skills --skill executors
```

Browse skills at [skills.hummingbot.org](https://skills.hummingbot.org)

## What are Skills?

Skills are instruction sets that extend AI agent capabilities. Instead of loading thousands of tokens of tool definitions, skills load on-demand when relevant to your task.

**How it works:**
1. Install skills using the [skills.sh](https://skills.sh) CLI
2. Skills are copied to your agent's skills directory
3. When you ask about trading, your agent loads the relevant skill

## Available Skills

| Skill | Description | Category |
|-------|-------------|----------|
| [executors](./skills/executors/) | Create trading executors (position, grid, DCA, TWAP) | Trading |
| [candles](./skills/candles/) | Market data and technical indicators | Data |
| [keys](./skills/keys/) | Manage exchange API credentials | Configuration |
| [setup](./skills/setup/) | Deploy Hummingbot infrastructure (Docker, API, Gateway) | Infrastructure |

## Installation

Install all Hummingbot skills:
```bash
npx skills add hummingbot/skills
```

Install a specific skill:
```bash
npx skills add hummingbot/skills --skill executors
```

## Usage

After installation, ask your AI agent:

```
"Create a BTC position with 2% stop loss and 4% take profit"
"Show me the RSI for ETH on Binance"
"Add my Binance API keys"
"Set up Hummingbot with Docker"
```

## Supported AI Agents

- Claude Code
- Cursor
- Windsurf
- VS Code (GitHub Copilot)
- OpenCode
- Goose
- Gemini CLI
- Codex

## Repository Structure

```
skills/
├── skills/                 # Skill definitions
│   ├── executors/          # Trading executors
│   ├── candles/            # Market data & indicators
│   ├── keys/               # API credentials
│   └── setup/              # Infrastructure setup
├── webapp/                 # skills.hummingbot.org
├── docs/                   # Documentation
└── skills.json             # Skills registry
```

## Web App

Browse and discover skills at [skills.hummingbot.org](https://skills.hummingbot.org)

See [docs/webapp-design.md](./docs/webapp-design.md) for the web application design.

## Development

```bash
git clone https://github.com/hummingbot/skills.git
cd skills

# Test a skill
./skills/executors/scripts/create_position.sh --help
```

## License

Apache-2.0

## Links

- [Hummingbot](https://hummingbot.org)
- [skills.sh](https://skills.sh) - The open agent skills ecosystem
- [Agent Skills Specification](https://agentskills.io)
