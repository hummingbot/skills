# Hummingbot Skills

AI agent skills for Hummingbot trading infrastructure. Built on the [Agent Skills](https://agentskills.io) open standard.

## Monorepo Structure

This is a monorepo with three main components:

```
hummingbot/skills/
├── skills/           # Skill definitions (SKILL.md + scripts/)
├── cli/              # hummingbot-skills CLI (npm package)
├── app/              # Next.js webapp (skills.hummingbot.org)
└── .github/          # CI/CD workflows
```

### skills/

Trading skill definitions. Each skill has:
- `SKILL.md` - Frontmatter with name, description, metadata.author
- `scripts/` - Shell scripts for the agent to execute

### cli/

The `hummingbot-skills` npm package. A wrapper around the [skills CLI](https://github.com/vercel-labs/skills).

**Usage:**
```bash
npx hummingbot-skills add           # Install skills
npx hummingbot-skills list          # List installed
npx hummingbot-skills find          # Search
npx hummingbot-skills check         # Check for updates
npx hummingbot-skills update        # Update all
npx hummingbot-skills remove        # Remove
npx hummingbot-skills create        # Create new skill
```

**Development:**
```bash
cd cli && npm install && npm run build && npm link
```

**Publishing:** See [cli/README.md](./cli/README.md)

### app/

Next.js webapp deployed at [skills.hummingbot.org](https://skills.hummingbot.org).

**Development:**
```bash
cd app && npm install && npm run dev
```

**Deployment:** Auto-deploys via Vercel on push to main. See [app/README.md](./app/README.md)

## Available Skills

| Skill | Description |
|-------|-------------|
| `hummingbot-api-setup` | Deploy Hummingbot infrastructure |
| `keys-manager` | Manage exchange API credentials |
| `executor-creator` | Create trading executors |
| `candles-feed` | Fetch market data and indicators |
| `portfolio` | View balances, positions, and history |

## API Configuration

Skills connect to the Hummingbot API. Configure credentials:

```bash
# Option 1: Use the setup script
./skills/hummingbot-api-setup/scripts/configure_env.sh --url http://localhost:8000 --user admin --pass admin

# Option 2: Set environment variables
export API_URL=http://localhost:8000
export API_USER=admin
export API_PASS=admin
```

Skills check for `.env` in: current directory → `~/.hummingbot/` → `~/`

## Publishing

### CLI to npm

**Option A:** Create a GitHub Release with tag `cli-v*` → auto-publishes via workflow

**Option B:** Manual
```bash
cd cli
npm version patch
npm run build
npm publish --access public
```

### Webapp to Vercel

Auto-deploys on push to `main`. Manual: `cd app && vercel --prod`

## Key Files

- `skills/*/SKILL.md` - Skill definitions (source of truth for metadata)
- `app/src/lib/skills.ts` - Reads SKILL.md files, serves via API
- `app/src/app/api/skills/route.ts` - API endpoint for CLI
- `cli/src/cli.ts` - CLI implementation
