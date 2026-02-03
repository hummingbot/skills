# hummingbot-skills CLI

CLI for managing Hummingbot trading skills for AI agents.

**npm package:** [`hummingbot-skills`](https://www.npmjs.com/package/hummingbot-skills)

## Usage

Run directly with npx (no installation required):

```bash
npx hummingbot-skills
```

## Commands

### Install Skills

```bash
npx hummingbot-skills add                    # Interactive selection
npx hummingbot-skills add portfolio          # Install specific skill
npx hummingbot-skills add portfolio candles  # Install multiple skills
npx hummingbot-skills add -a claude-code     # Install for specific agent
npx hummingbot-skills add -y                 # Skip prompts (install all)
```

### List Installed Skills

```bash
npx hummingbot-skills list
```

### Search for Skills

```bash
npx hummingbot-skills find              # List all available
npx hummingbot-skills find trading      # Search by keyword
```

### Check for Updates

```bash
npx hummingbot-skills check
```

### Update Skills

```bash
npx hummingbot-skills update
```

### Remove Skills

```bash
npx hummingbot-skills remove            # Interactive selection
npx hummingbot-skills remove portfolio  # Remove specific skill
```

### Create a New Skill

```bash
npx hummingbot-skills create my-skill
```

## How It Works

This CLI wraps the [skills CLI](https://github.com/vercel-labs/skills) and automatically points to the `hummingbot/skills` repository. All commands pass through to the skills CLI.

## Development

```bash
cd cli
npm install
npm run build
npm link  # For local testing
```

Test locally:

```bash
npx hummingbot-skills
npx hummingbot-skills add
```

## Publishing to npm

The CLI is published as the `hummingbot-skills` package on npm.

### Option 1: Publish via GitHub Actions (Recommended)

Create a GitHub Release:

1. Go to [Releases](https://github.com/hummingbot/skills/releases)
2. Click "Create a new release"
3. Tag: `cli-v1.0.2` (use `cli-v` prefix)
4. Title: `CLI v1.0.2`
5. Publish release

### Option 2: Manual Publish

```bash
cd cli
npm version patch
npm run build
npm publish --access public
```

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
