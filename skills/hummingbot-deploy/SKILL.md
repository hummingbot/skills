---
name: hummingbot-deploy
description: Deploy Hummingbot trading infrastructure including API server, MCP server for Claude, and Condor Telegram bot. Use this skill when the user wants to install, deploy, set up, or configure Hummingbot.
metadata:
  author: hummingbot
---

# hummingbot-deploy

Deploy the complete Hummingbot trading infrastructure.

## Components

| Component | Repository | Description |
|-----------|------------|-------------|
| **Hummingbot API** | [hummingbot/hummingbot-api](https://github.com/hummingbot/hummingbot-api) | REST API server for bot management |
| **MCP Server** | [hummingbot/mcp](https://github.com/hummingbot/mcp) | Claude/AI agent integration via Model Context Protocol |
| **Condor** | [hummingbot/condor](https://github.com/hummingbot/condor) | Telegram bot interface for trading |

## Install Hummingbot API

```bash
git clone https://github.com/hummingbot/hummingbot-api.git ~/hummingbot-api
cd ~/hummingbot-api
make setup    # Prompts for: API username, password, config password (defaults: admin/admin/admin)
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
