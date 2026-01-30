# Hummingbot Skills

AI agent skills for Hummingbot trading infrastructure.

## Installation

**Claude Code:**
```
/plugin marketplace add hummingbot/skills
/plugin install hummingbot-skills@hummingbot-skills
```

**skills.sh:**
```bash
npx skills add hummingbot/skills
```

## Available Skills

| Skill | Description |
|-------|-------------|
| `hummingbot-api-setup` | Deploy Hummingbot infrastructure |
| `keys-manager` | Manage exchange API credentials |
| `executor-creator` | Create trading executors |
| `candles-feed` | Fetch market data and indicators |

## API Server

Skills call the Hummingbot API at `http://localhost:8000` with Basic Auth (`admin:admin`).

## Project Structure

```
skills/
├── .claude-plugin/marketplace.json   # Claude Code plugin config
├── skills/                           # Skill definitions (SKILL.md + scripts/)
│   ├── hummingbot-api-setup/
│   ├── keys-manager/
│   ├── executor-creator/
│   └── candles-feed/
└── skills.json                       # Registry for skills.sh
```
