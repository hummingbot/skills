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

## Vercel Deployment

**Live site:** https://skills.hummingbot.org

### Manual Deploy
```bash
vercel --prod
```

### Automatic Deploys (GitHub Integration)

To enable auto-deploy on push to GitHub:

1. Go to [Vercel Dashboard](https://vercel.com/botcamps-projects/hummingbot-skills/settings/git)
2. Under "Connected Git Repository", connect `hummingbot/skills` if not already
3. Configure branches:
   - **Production Branch:** `main` → deploys to skills.hummingbot.org
   - **Preview Branches:** `dev`, PRs → deploys to preview URLs

Once connected:
- Push to `main` → auto-deploys to production
- Push to `dev` → creates preview deployment
- Open PR → creates preview deployment with comment link

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
