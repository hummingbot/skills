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

## API Configuration

Skills connect to the Hummingbot API using environment variables. Configure once:

```bash
# Create ~/.hummingbot/.env with your settings
./skills/hummingbot-api-setup/scripts/configure_env.sh --url http://localhost:8000 --user admin --pass admin
```

Or set environment variables directly:
```bash
export API_URL=http://localhost:8000
export API_USER=admin
export API_PASS=admin
```

Skills check for `.env` in: current directory → `~/.hummingbot/` → `~/`

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
