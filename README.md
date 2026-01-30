# Hummingbot Skills

AI agent skills for [Hummingbot](https://hummingbot.org) algorithmic trading infrastructure.

## Claude Code Plugin (Recommended)

Add Hummingbot as a Claude Code plugin marketplace:

```
/plugin marketplace add hummingbot/skills
```

Then install the trading skills:

```
/plugin install trading-skills@hummingbot-skills
```

After installing, just ask Claude:
- "Create a BTC position with 2% stop loss"
- "Show me the RSI for ETH on Binance"
- "Add my Binance API keys"
- "Set up Hummingbot with Docker"

## Alternative: skills.sh CLI

You can also install via the [skills.sh](https://skills.sh) CLI:

```bash
npx skills add hummingbot/skills --skill executor-creator
```

Browse skills at [skills.hummingbot.org](https://skills.hummingbot.org)

## Available Skills

| Skill | Description | Category |
|-------|-------------|----------|
| [hummingbot-api-setup](./skills/hummingbot-api-setup/) | Deploy Hummingbot infrastructure (Docker, API, Gateway) | Infrastructure |
| [keys-manager](./skills/keys-manager/) | Manage exchange API credentials | Configuration |
| [executor-creator](./skills/executor-creator/) | Create trading executors (position, grid, DCA, TWAP) | Trading |
| [candles-feed](./skills/candles-feed/) | Fetch market data and technical indicators | Data |

## Supported AI Agents

- Claude Code (via plugin marketplace)
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
├── .claude-plugin/             # Claude Code plugin config
│   └── marketplace.json        # Plugin marketplace definition
├── skills/                     # Skill definitions
│   ├── hummingbot-api-setup/   # Infrastructure setup
│   ├── keys-manager/           # API credentials
│   ├── executor-creator/       # Trading executors
│   └── candles-feed/           # Market data & indicators
├── webapp/                     # skills.hummingbot.org
└── skills.json                 # Skills registry
```

## Development

```bash
git clone https://github.com/hummingbot/skills.git
cd skills

# Test a skill script
./skills/executor-creator/scripts/list_executor_types.sh

# Test marketplace locally in Claude Code
/plugin marketplace add ./
/plugin install trading-skills@hummingbot-skills
```

## License

Apache-2.0

## Links

- [Hummingbot](https://hummingbot.org)
- [skills.sh](https://skills.sh) - The open agent skills ecosystem
- [Claude Code Plugins](https://code.claude.com/docs/en/discover-plugins)
