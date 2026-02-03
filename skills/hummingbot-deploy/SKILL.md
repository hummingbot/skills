---
name: hummingbot-deploy
description: Deploy Hummingbot trading infrastructure including API server, MCP server for Claude, and Condor Telegram bot. Use this skill when the user wants to install, deploy, set up, or configure Hummingbot.
metadata:
  author: hummingbot
---

# hummingbot-deploy

Deploy the Hummingbot trading infrastructure. Before starting, explain to the user what will be installed:

## What You're Installing

1. **Hummingbot API** (Required): Your personal trading server that exposes a standardized REST API for trading, fetching market data, and deploying bot strategies across many CEXs and DEXs.

2. **Hummingbot MCP** (Required): MCP server that helps AI assistants like Claude interact with Hummingbot API. This is necessary to use Hummingbot Skills.

3. **Condor** (Optional): Terminal and Telegram-based UI for Hummingbot API.

## Components

| Component | Repository |
|-----------|------------|
| Hummingbot API | [hummingbot/hummingbot-api](https://github.com/hummingbot/hummingbot-api) |
| MCP Server | [hummingbot/mcp](https://github.com/hummingbot/mcp) |
| Condor | [hummingbot/condor](https://github.com/hummingbot/condor) |

## Install Hummingbot API

```bash
git clone https://github.com/hummingbot/hummingbot-api.git ~/hummingbot-api
cd ~/hummingbot-api
```

**On regular machines** (interactive TTY available):
```bash
make setup    # Prompts for: API username, password, config password (defaults: admin/admin/admin)
make deploy
```

**In containers** (no TTY - check with `[ -t 0 ] && echo "TTY" || echo "No TTY"`):
```bash
# Set USER env var and create sudo shim if needed
export USER=${USER:-root}
[ "$(id -u)" = "0" ] && ! command -v sudo &>/dev/null && echo -e '#!/bin/bash\nwhile [[ "$1" == *=* ]]; do export "$1"; shift; done\nexec "$@"' > /usr/local/bin/sudo && chmod +x /usr/local/bin/sudo

# Create .env manually (skip interactive setup)
cat > .env << 'EOF'
USERNAME=admin
PASSWORD=admin
CONFIG_PASSWORD=admin
DEBUG_MODE=false
BROKER_HOST=localhost
BROKER_PORT=1883
BROKER_USERNAME=admin
BROKER_PASSWORD=password
DATABASE_URL=postgresql+asyncpg://hbot:hummingbot-api@localhost:5432/hummingbot_api
EOF

touch .setup-complete
make deploy
```

**Verify:** Open http://localhost:8000/docs - should show Swagger UI.

## Install MCP Server (for Claude)

```bash
./scripts/install_mcp.sh
```

## Install Condor (Optional)

```bash
./scripts/install_condor.sh
```

## Upgrade

```bash
cd ~/hummingbot-api && git pull && make deploy
```

## Verify Installation

```bash
./scripts/verify.sh
```

## Troubleshooting

```bash
# View logs
cd ~/hummingbot-api && docker compose logs -f

# Reset
cd ~/hummingbot-api && docker compose down -v && rm -rf ~/hummingbot-api
```

## See Also

- [Hummingbot API Docs](https://hummingbot.org/hummingbot-api/)
- [MCP Server Docs](https://hummingbot.org/mcp/)
