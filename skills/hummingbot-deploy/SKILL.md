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

## Prerequisites

Before installation, ensure you have:
- **Docker** installed and running
- **Git** for cloning repositories
- **2GB+ disk space**

Check prerequisites:
```bash
./scripts/check_dependencies.sh
```

## Installation

### Step 1: Check Dependencies

```bash
./scripts/check_dependencies.sh
```

If dependencies are missing, install them:
```bash
./scripts/install_dependencies.sh
```

### Step 2: Install Hummingbot API

The API server is the core component that manages trading bots.

```bash
./scripts/install_api.sh
```

After installation:
- **API URL:** http://localhost:8000
- **Docs:** http://localhost:8000/docs
- **Credentials:** admin/admin (change in production)

### Step 3: Install MCP Server (for Claude)

Enable Claude Code and Claude Desktop to interact with Hummingbot.

```bash
./scripts/install_mcp.sh
```

This configures the MCP server for your AI assistant.

### Step 4: Install Condor (Optional)

Telegram bot interface for mobile trading.

```bash
./scripts/install_condor.sh
```

## Verification

Verify all services are running:

```bash
./scripts/verify.sh
```

Check API health:

```bash
./scripts/health_check.sh
```

## Status & Management

View status of all components:

```bash
./scripts/status.sh
```

Upgrade existing installation:

```bash
./scripts/upgrade.sh
```

## Quick Install (All Components)

Install everything with a single command:

```bash
./scripts/check_dependencies.sh && \
./scripts/install_api.sh && \
./scripts/install_mcp.sh && \
./scripts/install_condor.sh && \
./scripts/verify.sh
```

## Configuration

### Environment Variables

Create a `.env` file or export these variables:

```bash
export API_URL=http://localhost:8000
export API_USER=admin
export API_PASS=admin
```

The scripts check for `.env` in:
1. Current directory
2. `~/.hummingbot/`
3. Home directory (`~/`)

### Changing API Credentials

1. Edit `~/hummingbot-api/.env`
2. Restart the API: `cd ~/hummingbot-api && docker compose restart`

## Ports Used

| Port | Service | Check |
|------|---------|-------|
| 8000 | Hummingbot API | `lsof -i :8000` |
| 5432 | PostgreSQL | `lsof -i :5432` |
| 1883 | EMQX (MQTT) | `lsof -i :1883` |

## Troubleshooting

### Docker not running

**macOS:**
```bash
open -a Docker
```

**Linux:**
```bash
sudo systemctl start docker
```

### Port already in use

Stop the conflicting service or change the port in docker-compose.yml.

### View logs

```bash
# API logs
cd ~/hummingbot-api && docker compose logs -f

# Condor logs
cd ~/condor && docker compose logs -f
```

### Reset installation

```bash
# Remove API
cd ~/hummingbot-api && docker compose down -v && cd .. && rm -rf hummingbot-api

# Remove Condor
cd ~/condor && docker compose down -v && cd .. && rm -rf condor
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your AI Assistant                     │
│              (Claude Code / Claude Desktop)              │
└─────────────────────┬───────────────────────────────────┘
                      │ MCP Protocol
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   MCP Server (Docker)                    │
│                 hummingbot/hummingbot-mcp               │
└─────────────────────┬───────────────────────────────────┘
                      │ REST API
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   Hummingbot API                         │
│                    localhost:8000                        │
├─────────────────────────────────────────────────────────┤
│  PostgreSQL  │    EMQX    │   Gateway   │   Bots       │
│    :5432     │   :1883    │   :15888    │              │
└─────────────────────────────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │   Exchanges   │
              │ Binance, etc. │
              └───────────────┘
```

## See Also

- [Hummingbot API Documentation](https://hummingbot.org/hummingbot-api/)
- [MCP Server Documentation](https://hummingbot.org/mcp/)
- [Condor Bot Guide](https://github.com/hummingbot/condor)
