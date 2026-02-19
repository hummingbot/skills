# Hummingbot Skills

AI agent skills for Hummingbot trading infrastructure. Built on the [Agent Skills](https://agentskills.io) open standard.

## Monorepo Structure

```
hummingbot/skills/
├── skills/           # Skill definitions (SKILL.md + scripts/)
├── app/              # Next.js webapp (skills.hummingbot.org)
└── .github/          # CI/CD workflows
```

### skills/

Trading skill definitions. Each skill has:
- `SKILL.md` - Frontmatter with name, description, metadata.author
- `scripts/` - Shell scripts for the agent to execute

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
| `hummingbot-deploy` | Deploy Hummingbot infrastructure |
| `lp-agent` | CLMM liquidity provision agent |
| `slides-generator` | Create PDF slides from markdown |

## Installation

Use the standard [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add hummingbot/skills                              # Install all skills
npx skills add hummingbot/skills --skill hummingbot-deploy    # Install specific skill
```

## API Configuration

Skills connect to the Hummingbot API. Configure credentials:

```bash
# Option 1: Use the setup script
./skills/hummingbot-deploy/scripts/configure_env.sh --url http://localhost:8000 --user admin --pass admin

# Option 2: Set environment variables
export API_URL=http://localhost:8000
export API_USER=admin
export API_PASS=admin
```

Skills check for `.env` in: current directory → `~/.hummingbot/` → `~/`

## Publishing

### Webapp to Vercel

Auto-deploys on push to `main`. Manual: `cd app && vercel --prod`

## Key Files

- `skills/*/SKILL.md` - Skill definitions (source of truth for metadata)
- `app/src/lib/skills.ts` - Reads SKILL.md files, serves via API
- `app/src/app/api/skills/route.ts` - API endpoint
