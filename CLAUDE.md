# Hummingbot Skills

AI agent skills for Hummingbot trading infrastructure. Built on the [Agent Skills](https://agentskills.io) open standard.

## Installation

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
| `portfolio` | View balances, positions, and history |

## API Server

Skills call the Hummingbot API at `http://localhost:8000` with Basic Auth (`admin:admin`).

## Publishing to npm

- **Option A:** Create a GitHub Release → auto-publishes to npm
- **Option B:** Go to Actions → "Publish to npm" → Run workflow (choose patch/minor/major)

## Project Structure

```
skills/
├── skills/                 # Skill definitions (SKILL.md + scripts/)
│   ├── hummingbot-api-setup/
│   ├── keys-manager/
│   ├── executor-creator/
│   ├── candles-feed/
│   └── portfolio/
└── skills.json             # Skill metadata (for webapp)
```
