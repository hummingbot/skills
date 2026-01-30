# Hummingbot Skills

Reusable capabilities for AI agents to interact with [Hummingbot](https://hummingbot.org) trading infrastructure.

```bash
npx @hummingbot/skills add
```

## What are Skills?

Skills are instruction sets that extend AI agent capabilities. Instead of loading thousands of tokens of tool definitions, skills load on-demand when relevant to your task.

**Context efficiency:**
- Skill metadata at startup: ~100 tokens per skill
- Full skill on activation: <5,000 tokens
- Compare to MCP tools: ~20,000+ tokens always loaded

## Available Skills

| Skill | Description | Category |
|-------|-------------|----------|
| [setup](./skills/setup/) | Deploy Hummingbot infrastructure (Docker, API, Gateway) | Infrastructure |
| [keys](./skills/keys/) | Manage exchange API credentials | Configuration |
| [executors](./skills/executors/) | Create trading executors (position, grid, DCA, TWAP) | Trading |
| [candles](./skills/candles/) | Market data and technical indicators | Data |

## Quick Start

### 1. Install Skills

```bash
# Install all skills to your AI agent
npx @hummingbot/skills add

# Install specific skill
npx @hummingbot/skills add -s executors

# Install to specific agent
npx @hummingbot/skills add -a cursor
```

### 2. Start Trading

Ask your AI agent:
```
"Create a BTC position with 2% stop loss and 4% take profit"
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `npx @hummingbot/skills add` | Install skills |
| `npx @hummingbot/skills add -l` | List available skills |
| `npx @hummingbot/skills list` | Show installed skills |
| `npx @hummingbot/skills find [query]` | Search skills |
| `npx @hummingbot/skills remove <name>` | Uninstall skill |
| `npx @hummingbot/skills check` | Verify API server |
| `npx @hummingbot/skills init <name>` | Create custom skill |

## Supported AI Agents

- Claude Code
- Cursor
- VS Code (GitHub Copilot)
- OpenCode
- Goose
- Gemini CLI

## Repository Structure

```
skills/
├── cli/                    # @hummingbot/skills npm package
├── skills/                 # Skill definitions
│   ├── setup/
│   ├── keys/
│   ├── executors/
│   └── candles/
├── webapp/                 # Skills discovery web app
└── docs/                   # Documentation
    └── webapp-design.md
```

## Web App

Browse and discover skills at [skills.hummingbot.org](https://skills.hummingbot.org)

See [docs/webapp-design.md](./docs/webapp-design.md) for the web application design.

## Development

```bash
git clone https://github.com/hummingbot/skills.git
cd skills

# Run CLI locally
node cli/bin/cli.mjs --help

# Test a skill
./skills/executors/scripts/setup_executor.sh
```

## License

Apache-2.0

## Links

- [Hummingbot](https://hummingbot.org)
- [Agent Skills Specification](https://agentskills.io)
