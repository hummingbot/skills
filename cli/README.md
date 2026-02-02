# hummingbot-skills CLI

CLI for managing Hummingbot trading skills for AI agents.

**npm package:** [`hummingbot-skills`](https://www.npmjs.com/package/hummingbot-skills)

## Installation

No installation required - run directly with npx:

```bash
npx hummingbot-skills
```

Or install globally:

```bash
npm install -g hummingbot-skills
```

## Commands

### Install Skills

Install all Hummingbot skills:

```bash
npx hummingbot-skills add
```

Install specific skills:

```bash
npx hummingbot-skills add portfolio candles-feed
```

Install globally (recommended):

```bash
npx hummingbot-skills add -g
```

Install for specific agents:

```bash
npx hummingbot-skills add -a claude-code cursor
```

### Remove Skills

Remove installed skills (interactive):

```bash
npx hummingbot-skills remove
```

Remove specific skills:

```bash
npx hummingbot-skills remove portfolio -g
```

### List & Search

```bash
npx hummingbot-skills list          # List all available skills
npx hummingbot-skills find trading  # Search by keyword
```

## How It Works

This CLI is a convenience wrapper around the [skills CLI](https://github.com/vercel-labs/skills). When you run `hummingbot-skills add`, it:

1. Fetches skill metadata from `https://skills.hummingbot.org/api/skills`
2. Runs `npx skills add hummingbot/skills` with appropriate flags
3. The skills CLI installs skills to your AI agents

## Development

```bash
cd cli
npm install
npm run build
npm link  # For local testing
```

Test locally:

```bash
hummingbot-skills list
hummingbot-skills add portfolio -g
```

## Publishing to npm

The CLI is published as the `hummingbot-skills` package on npm.

### Prerequisites

1. **npm account** with publish access to `hummingbot-skills`
2. **Trusted Publisher** configured on npmjs.com (for CI/CD)

### Option 1: Publish via GitHub Actions (Recommended)

Create a GitHub Release:

1. Go to [Releases](https://github.com/hummingbot/skills/releases)
2. Click "Create a new release"
3. Tag: `cli-v1.0.1` (use `cli-v` prefix for CLI releases)
4. Title: `CLI v1.0.1`
5. Publish release

The workflow at `.github/workflows/publish-cli.yml` will:
- Build the CLI
- Publish to npm with provenance

### Option 2: Manual Publish

```bash
cd cli
npm version patch  # or minor/major
npm run build
npm publish --access public
```

### Version Management

- Update version in `cli/package.json`
- CLI versions are independent of the skills/webapp
- Use semantic versioning: `major.minor.patch`

### Trusted Publishers Setup

To enable automated publishing without tokens:

1. Go to [npmjs.com](https://www.npmjs.com) → Package Settings → `hummingbot-skills`
2. Add GitHub Actions as trusted publisher:
   - Repository: `hummingbot/skills`
   - Workflow: `publish-cli.yml`
   - Environment: `npm`

## Project Structure

```
cli/
├── bin/
│   └── cli.mjs       # Entry point
├── src/
│   └── cli.ts        # Main CLI code
├── dist/             # Built output (gitignored)
├── package.json
├── tsconfig.json
└── README.md
```

## Links

- [Hummingbot Skills Webapp](https://skills.hummingbot.org)
- [Main Repository](https://github.com/hummingbot/skills)
- [npm Package](https://www.npmjs.com/package/hummingbot-skills)
