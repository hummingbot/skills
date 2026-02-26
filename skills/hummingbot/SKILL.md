---
name: hummingbot
description: >
  General-purpose Hummingbot API skill for portfolio monitoring, CEX trading, bot management,
  market data, and account management. Use when the user wants to check balances, place orders,
  manage bots, view market data, or configure exchange accounts. For DEX/LP strategies on
  Solana, use the lp-agent skill instead.
metadata:
  author: hummingbot
  requires: hummingbot-api-client>=1.2.8
commands:
  status:
    description: API health check + running bots + portfolio snapshot
  portfolio:
    description: View balances, token distribution, and portfolio value
  bots:
    description: List, deploy, start, and stop trading bots
  market:
    description: Prices, order books, and candles for any trading pair
  trade:
    description: Place/cancel orders, view positions and trade history
  accounts:
    description: Manage accounts and exchange credentials
---

# hummingbot

General-purpose skill for interacting with the Hummingbot API. Covers portfolio monitoring,
CEX trading, bot lifecycle management, market data, and account setup.

**Commands** (run as `/hummingbot <command>`):

| Command | Description |
|---------|-------------|
| `status` | API health + running bots + portfolio snapshot |
| `portfolio` | Balances, distribution, total value |
| `bots` | List, deploy, start, stop trading bots |
| `market` | Prices, order books, candles |
| `trade` | Place/cancel orders, positions, history |
| `accounts` | Manage accounts and exchange credentials |

## When to Use This Skill vs the MCP Server

Think of them as parallel paths to the same destination:

```
Claude Code / Claude Desktop / Gemini CLI
    → MCP protocol → hummingbot MCP server → Hummingbot API

Lupin in OpenClaw (or any OpenClaw agent)
    → hummingbot skill → hummingbot-api-client → Hummingbot API
```

The MCP server still has value for anyone using a tool that natively speaks MCP
(Claude Code, Claude Desktop, Cursor, etc.). The `~/mcp` repo doesn't go away —
it's just not the path OpenClaw agents use.

This skill is the native OpenClaw integration. Same API, same capabilities,
different plumbing that fits how OpenClaw actually works.

- **Use this skill** when working through an OpenClaw agent (Telegram, WhatsApp, web chat)
- **Use the MCP server** when working in Claude Code, Claude Desktop, Cursor, or Gemini CLI

## Related Skills

- **lp-agent** — Specialized DEX liquidity provision on Meteora/Solana. Use for CLMM strategies.
  lp-agent manages its own API scripts independently. This skill covers CEX and general API usage.
- **hummingbot-deploy** — First-time setup of the Hummingbot API server. Run this before using this skill.

## Prerequisites

- Hummingbot API running at `http://localhost:8000` (deploy with `/hummingbot-deploy` or `/lp-agent deploy-hummingbot-api`)
- `hummingbot-api-client` installed: `pip3 install hummingbot-api-client`
- Credentials in `~/mcp/.env` (or env vars `HUMMINGBOT_API_URL`, `HUMMINGBOT_USERNAME`, `HUMMINGBOT_PASSWORD`)

## Auth & Config

All scripts read credentials from these sources in order:
1. `~/mcp/.env` — primary (set up during Hummingbot deploy)
2. `~/.hummingbot/.env`
3. Environment variables: `HUMMINGBOT_API_URL`, `HUMMINGBOT_USERNAME`, `HUMMINGBOT_PASSWORD`
4. Defaults: `http://localhost:8000`, `admin`, `admin`

---

## Command: status

Quick health check: is the API running, what bots are active, and a portfolio snapshot.

```bash
python scripts/status.py
```

**Interpreting output:**

| Output | Meaning |
|--------|---------|
| `✓ API running at http://localhost:8000` | Connected |
| `✗ Cannot connect to API` | API down — run `make deploy` in `~/hummingbot-api` |
| Running bots table | Shows active bots, status, strategy |
| Portfolio snapshot | Total value + top holdings |

---

## Command: portfolio

View portfolio balances, token distribution, and total value across all accounts and exchanges.

```bash
# Full portfolio state
python scripts/portfolio.py state

# Total portfolio value (USD)
python scripts/portfolio.py value

# Token distribution (%)
python scripts/portfolio.py distribution

# Holdings for a specific token
python scripts/portfolio.py token USDT

# Filter by account
python scripts/portfolio.py state --account master_account
```

**Interpreting output:**

| Output | Meaning |
|--------|---------|
| Table of accounts/exchanges/balances | Normal portfolio view |
| `Total: $X,XXX.XX` | Sum of all holdings in USD |
| `No balances found` | No connected accounts or all zero balances |
| `Error: 401 Unauthorized` | Wrong credentials — check `~/mcp/.env` |

---

## Command: bots

Manage bot lifecycle: list running bots, deploy new ones, start/stop.

```bash
# List all active bots
python scripts/bots.py list

# Deploy a V2 controller bot
python scripts/bots.py deploy <bot_name> --controller <config_name>

# Deploy a script bot
python scripts/bots.py deploy <bot_name> --script <script_name> [--config <config_name>]

# Stop a bot
python scripts/bots.py stop <bot_name>

# Get bot status/logs
python scripts/bots.py status <bot_name>
python scripts/bots.py logs <bot_name> [--lines 50]

# List available controllers and scripts
python scripts/bots.py controllers
python scripts/bots.py scripts
```

**Interpreting output:**

| Output | Meaning |
|--------|---------|
| Bot table with `running` status | Bot is active |
| `stopped` or `error` status | Bot not trading — check logs |
| `✓ Bot deployed` | Successfully started |
| `Error: Bot already exists` | Use `stop` first, then redeploy |

---

## Command: market

Fetch real-time market data: prices, order books, candles.

```bash
# Current price for a pair
python scripts/market.py price binance_paper_trade BTC-USDT

# Multiple pairs
python scripts/market.py price binance_paper_trade BTC-USDT ETH-USDT SOL-USDT

# Order book (top 10 levels)
python scripts/market.py orderbook binance_paper_trade BTC-USDT [--depth 10]

# Candles (OHLCV)
python scripts/market.py candles binance_paper_trade BTC-USDT --interval 1m [--limit 100]

# Funding rates (perpetuals)
python scripts/market.py funding binance_perpetual BTC-USDT
```

**Connector examples:** `binance`, `binance_paper_trade`, `kucoin`, `gate_io`, `binance_perpetual`

---

## Command: trade

Place and manage trades across exchanges.

```bash
# Place a market order
python scripts/trade.py order master_account binance BTC-USDT buy 0.001

# Place a limit order
python scripts/trade.py order master_account binance BTC-USDT buy 0.001 --price 85000 --type limit

# List active orders
python scripts/trade.py orders [--account master_account] [--connector binance]

# Cancel an order
python scripts/trade.py cancel master_account binance <order_id>

# View open positions (perpetuals)
python scripts/trade.py positions [--account master_account]

# Trade history
python scripts/trade.py history [--limit 50] [--account master_account]
```

**⚠️ Before placing real orders:** confirm exchange account is set up (`/hummingbot accounts`) and has funded balances (`/hummingbot portfolio`).

---

## Command: accounts

Manage trading accounts and exchange credentials.

```bash
# List all accounts
python scripts/accounts.py list

# Create a new account
python scripts/accounts.py add <account_name>

# Add exchange credentials to an account
python scripts/accounts.py credentials <account_name> <connector>

# List credentials for an account
python scripts/accounts.py credentials <account_name>

# Remove credentials
python scripts/accounts.py remove-credentials <account_name> <connector>
```

**Connector credential fields vary by exchange.** The script will show required fields for the selected connector. Common fields:
- Binance: `api_key`, `secret_key`
- KuCoin: `api_key`, `secret_key`, `passphrase`
- Gate.io: `api_key`, `secret_key`

---

## Quick Reference

### Common Workflows

**Check everything is working:**
```bash
python scripts/status.py
```

**View my portfolio:**
```bash
python scripts/portfolio.py value
python scripts/portfolio.py distribution
```

**Check price and place a trade:**
```bash
python scripts/market.py price binance BTC-USDT
python scripts/trade.py order master_account binance BTC-USDT buy 0.001 --price 85000 --type limit
```

**Deploy a bot:**
```bash
python scripts/bots.py controllers          # See available configs
python scripts/bots.py deploy my_bot --controller my_config
python scripts/bots.py status my_bot
```

### Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot connect to API` | API not running | `cd ~/hummingbot-api && make deploy` |
| `401 Unauthorized` | Bad credentials | Check `~/mcp/.env` |
| `404 Not Found` | Wrong endpoint/bot name | Check spelling, use `list` first |
| `hummingbot_api_client not found` | Package not installed | `pip3 install hummingbot-api-client` |
