---
name: hummingbot-heartbeat
description: Hourly status heartbeat for Hummingbot API, Gateway, active bots/controllers, executors, and portfolio. Run as a cron job to get proactive status updates.
---

# hummingbot-heartbeat

Delivers a formatted hourly status report covering Hummingbot API health, Gateway container, active bots/controllers, executors, and portfolio balances.

## Installation

```bash
clawhub install hummingbot-heartbeat
```

Or manually clone into your skills directory.

## Quick Start

### 1. Run manually

```bash
# From the skill directory
python3 scripts/bot_status.py

# JSON output
python3 scripts/bot_status.py --json
```

### 2. Set up hourly cron

Ask your agent:

> "Set up the hummingbot-heartbeat cron job to run every hour and send me status on Telegram"

Or run the CLI yourself — replace `<SKILL_PATH>` with wherever the skill is installed (e.g. `~/.openclaw/workspace/skills/hummingbot-heartbeat`):

```bash
openclaw cron add \
  --name "bot-status" \
  --description "Hourly Hummingbot status check" \
  --every 1h \
  --announce \
  --channel telegram \
  --message "Run this and send output verbatim: python3 <SKILL_PATH>/scripts/bot_status.py"
```

> **Note:** When an agent installs this skill, it should resolve `<SKILL_PATH>` to the actual installed path before creating the cron job.

## Configuration

Set via environment variables or a `.env` file in the skill directory:

```bash
# .env (optional — defaults shown)
HUMMINGBOT_API_URL=http://localhost:8000
API_USER=admin
API_PASS=admin
```

| Variable | Default | Description |
|----------|---------|-------------|
| `HUMMINGBOT_API_URL` | `http://localhost:8000` | Hummingbot API base URL |
| `API_USER` | `admin` | API username |
| `API_PASS` | `admin` | API password |

## Requirements

- Python 3.9+
- Hummingbot API running (see `hummingbot-deploy` skill)
- Docker (optional — Gateway status check skipped if Docker unavailable)

## Sample Output

```
🤖 Hummingbot Status — Feb 28, 2026 09:06 AM

**Infrastructure**
  API:     ✅ Up (v1.0.1)
  Gateway: ✅ Up 17 hours

**Active Bots:** none

**Active Executors:** none

**Portfolio** (total: $187.23)
  Token           Units       Price      Value
  ------------ ----------- ---------- ----------
  SOL            2.0639    $81.4996    $168.20
  USDC          19.0286     $1.0000     $19.03
```

## What It Checks

| Check | Endpoint | Notes |
|-------|----------|-------|
| API health | `GET /` | Returns version |
| Gateway | `docker ps \| grep gateway` | Skipped if Docker unavailable |
| Active bots | `GET /bot-orchestration/status` | Lists controller configs |
| Active executors | `POST /executors/search` | Filters out CLOSED/FAILED |
| Portfolio | `POST /portfolio/history` | Latest balances with prices |
