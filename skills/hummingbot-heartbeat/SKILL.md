---
name: hummingbot-heartbeat
description: Hourly status heartbeat for Hummingbot API, Gateway, active bots/controllers, executors, and portfolio. Run as a cron job to get proactive status updates.
---

# hummingbot-heartbeat

Runs a status check against Hummingbot API and Gateway and delivers a formatted report covering infrastructure health, active bots, executors, and portfolio.

## Setup

Install via cron job (runs every hour, delivers to Telegram):

```bash
openclaw cron add \
  --name "bot-status" \
  --description "Hourly Hummingbot status check" \
  --every 1h \
  --announce \
  --channel telegram \
  --message "Run: python3 ~/.openclaw/workspace/skills/hummingbot-heartbeat/scripts/bot_status.py — then send the output as-is."
```

Or run manually:

```bash
python3 scripts/bot_status.py
python3 scripts/bot_status.py --json
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HUMMINGBOT_API_URL` | `http://localhost:8000` | Hummingbot API base URL |
| `API_USER` | `admin` | API username |
| `API_PASS` | `admin` | API password |

## Output

```
🤖 Hummingbot Status — Feb 28, 2026 09:05 AM

**Infrastructure**
  API:     ✅ Up (v1.0.1)
  Gateway: ✅ Up 17 hours

**Active Bots:** none

**Active Executors:** none

**Portfolio** (total: $187.23)
  Token              Units      Price      Value
  ------------ ------------ ---------- ----------
  SOL              2.0639   $81.4996    $168.20
  USDC            19.0286    $1.0000     $19.03
```

## Checks

1. **API** — GET `/` to verify Hummingbot API is up and get version
2. **Gateway** — `docker ps | grep gateway` to check container status
3. **Bots/Controllers** — GET `/bot-orchestration/status` for active bots and their controller configs
4. **Executors** — POST `/executors/search` for active (non-closed) executors
5. **Portfolio** — POST `/portfolio/history` for latest balances with token prices and values
