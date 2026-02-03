---
name: hummingbot-deploy
description: Deploy Hummingbot trading infrastructure including API server, MCP server for Claude, and Condor Telegram bot. Use this skill when the user wants to install, deploy, set up, or configure Hummingbot.
metadata:
  author: hummingbot
---

# hummingbot-deploy

Deploy the complete Hummingbot trading infrastructure with modular installation.

## Components

| Component | Repository | Description |
|-----------|------------|-------------|
| **Hummingbot API** | [hummingbot/hummingbot-api](https://github.com/hummingbot/hummingbot-api) | REST API server for bot management |
| **MCP Server** | [hummingbot/mcp](https://github.com/hummingbot/mcp) | Claude/AI agent integration via Model Context Protocol |
| **Condor** | [hummingbot/condor](https://github.com/hummingbot/condor) | Telegram bot interface for trading |

## Installation

### Step 1: Install Hummingbot API

```bash
./scripts/install_api.sh
```

- **API URL:** http://localhost:8000
- **Credentials:** admin/admin

### Step 2: Install MCP Server (for Claude)

```bash
./scripts/install_mcp.sh
```

### Step 3: Install Condor (Optional)

Telegram bot interface for mobile trading.

```bash
./scripts/install_condor.sh
```

## Other Scripts

| Script | Purpose |
|--------|---------|
| `check_dependencies.sh` | Check if Docker/Git are installed |
| `health_check.sh` | Check API health |
| `status.sh` | Show status of all components |
| `verify.sh` | Verify installation |
| `upgrade.sh` | Upgrade existing installation |

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
