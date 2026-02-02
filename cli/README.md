# hummingbot-skills

CLI for managing Hummingbot trading skills for AI agents.

## Installation

```bash
npx hummingbot-skills
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

Install globally:

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
npx hummingbot-skills remove portfolio
```

Remove globally:

```bash
npx hummingbot-skills remove portfolio -g
```

### List Skills

List all available skills:

```bash
npx hummingbot-skills list
```

### Search Skills

Search for skills by keyword:

```bash
npx hummingbot-skills find trading
npx hummingbot-skills find api
```

## Available Skills

| Skill | Description |
|-------|-------------|
| `hummingbot-api-setup` | Deploy Hummingbot API infrastructure |
| `keys-manager` | Manage spot and perpetual exchange API keys |
| `executor-creator` | Create trading executors |
| `candles-feed` | Fetch market data and indicators |
| `portfolio` | View balances, positions, and history |

## Learn More

- [Hummingbot Skills](https://skills.hummingbot.org)
- [Hummingbot API](https://hummingbot.org/hummingbot-api/)
- [GitHub Repository](https://github.com/hummingbot/skills)
