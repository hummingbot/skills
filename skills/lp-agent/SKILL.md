---
name: lp-agent
description: Run automated liquidity provision strategies on concentrated liquidity (CLMM) DEXs using Hummingbot API.
metadata:
  author: hummingbot
commands:
  start:
    description: Onboarding wizard — check setup status and get started
  deploy-hummingbot-api:
    description: Deploy Hummingbot API trading infrastructure
  setup-gateway:
    description: Start Gateway and configure network RPC endpoints
  add-wallet:
    description: Add or import a Solana wallet for trading
  explore-pools:
    description: Find and explore Meteora DLMM pools
  select-strategy:
    description: Choose between LP Executor or Rebalancer Controller strategy
  run-strategy:
    description: Run, monitor, and manage LP strategies
  analyze-performance:
    description: Export data and visualize LP position performance
---

# lp-agent

This skill helps you run automated liquidity provision strategies on concentrated liquidity (CLMM) DEXs using Hummingbot API.

**Commands** (run as `/lp-agent <command>`):

| Command | Description |
|---------|-------------|
| `start` | Onboarding wizard — check setup status and get started |
| `deploy-hummingbot-api` | Deploy Hummingbot API trading infrastructure |
| `setup-gateway` | Start Gateway, configure network RPC endpoints |
| `add-wallet` | Add or import a Solana wallet |
| `explore-pools` | Find and explore Meteora DLMM pools |
| `select-strategy` | Choose LP Executor or Rebalancer Controller |
| `run-strategy` | Run, monitor, and manage LP strategies |
| `analyze-performance` | Visualize LP position performance |

**New here?** Run `/lp-agent start` to check your setup and get a guided walkthrough.

**Typical workflow:** `start` → `deploy-hummingbot-api` → `setup-gateway` → `add-wallet` → `explore-pools` → `select-strategy` → `run-strategy` → `analyze-performance`

---

## Command: start

Welcome the user and guide them through setup. This is a conversational onboarding wizard — no scripts to run, just check infrastructure state and walk them through it.

### Step 1: Welcome & Explain

Introduce yourself and explain what lp-agent does:

> I'm your LP agent — I help you run automated liquidity provision strategies on Meteora DLMM pools (Solana). I can:
>
> - **Deploy infrastructure** — Hummingbot API + Gateway for DEX trading
> - **Manage wallets** — Add Solana wallets, check balances
> - **Explore pools** — Search Meteora DLMM pools, compare APR/volume/TVL
> - **Run strategies** — Auto-rebalancing LP controller or single-position executor
> - **Analyze performance** — Dashboards with PnL, fees, and position history

### Step 2: Check Infrastructure Status

Run the check scripts to assess current state:

```bash
bash scripts/check_api.sh --json      # Is Hummingbot API running?
bash scripts/check_gateway.sh --json  # Is Gateway running?
python scripts/add_wallet.py list     # Any wallets connected?
```

### Step 3: Show Progress

Present a checklist showing what's done and what's remaining:

```
Setup Progress:
  [x] Hummingbot API    — Running at http://localhost:8000
  [x] Gateway           — Running
  [ ] Wallet            — No wallet connected
  [ ] First LP strategy — Not yet

Next step: Add a Solana wallet so you can start trading.
  → Run /lp-agent add-wallet
```

Adapt the checklist to the actual state. If everything is unchecked, start from the top. If everything is checked, skip to the LP lifecycle overview.

### Step 4: Guide Next Action

Based on the first unchecked item, briefly explain what it does and offer to run it:

| Missing | What to say |
|---------|-------------|
| Hummingbot API | "Let's deploy the API first — it's the trading backend. Need Docker installed. Want me to run the installer?" → `/lp-agent deploy-hummingbot-api` |
| Gateway | "API is running! Now we need Gateway for DEX connectivity. Want me to start it?" → `/lp-agent setup-gateway` |
| Wallet | "Infrastructure is ready. You'll need a Solana wallet with some SOL for fees. Want to add one?" → `/lp-agent add-wallet` |
| All ready | Move to Step 5 |

### Step 5: LP Lifecycle Overview

Once infrastructure is ready (or if user wants to understand the flow first), explain the LP lifecycle:

> **How LP strategies work:**
>
> 1. **Explore pools** (`/lp-agent explore-pools`) — Find a Meteora DLMM pool. Look at volume, APR, and fee/TVL ratio to pick a good one.
>
> 2. **Select strategy** (`/lp-agent select-strategy`) — Choose between:
>    - **Rebalancer Controller** (recommended) — Automatically repositions when price moves out of range. Set-and-forget.
>    - **LP Executor** — Single fixed position. You control when to close/reopen. Good for testing or limit-order-style LP.
>
> 3. **Run strategy** (`/lp-agent run-strategy`) — Configure parameters (amount, width, price limits) and deploy. Monitor status and stop when done.
>
> 4. **Analyze** (`/lp-agent analyze-performance`) — View PnL dashboard, fees earned, position history. Works for both running and stopped strategies.
>
> Want to explore some pools to get started?

---

## Command: deploy-hummingbot-api

Deploy the Hummingbot API trading infrastructure. This is the first step before using any LP features.

### What Gets Installed

**Hummingbot API** — A personal trading server that exposes a REST API for trading, market data, and deploying bot strategies across CEXs and DEXs.

- Repository: [hummingbot/hummingbot-api](https://github.com/hummingbot/hummingbot-api)

### Usage

```bash
# Check if already installed
bash scripts/deploy_hummingbot_api.sh status

# Install (interactive, prompts for credentials)
bash scripts/deploy_hummingbot_api.sh install

# Install with defaults (non-interactive: admin/admin)
bash scripts/deploy_hummingbot_api.sh install --defaults

# Upgrade existing installation
bash scripts/deploy_hummingbot_api.sh upgrade

# View container logs
bash scripts/deploy_hummingbot_api.sh logs

# Reset (stop and remove everything)
bash scripts/deploy_hummingbot_api.sh reset
```

### Prerequisites

- Docker and Docker Compose
- Git

### After Installation

Once the API is running:
1. Swagger UI is at `http://localhost:8000/docs`
2. Default credentials: admin/admin
3. Proceed to `setup-gateway` to enable DEX trading

---

## Command: setup-gateway

Start the Gateway service, check its status, and configure key network parameters like RPC node URLs. Gateway is required for all LP operations on DEXs.

**Prerequisite:** Hummingbot API must be running (`deploy-hummingbot-api`). The script checks this automatically.

### Usage

```bash
# Check Gateway status
bash scripts/setup_gateway.sh --status

# Start Gateway with defaults
bash scripts/setup_gateway.sh

# Start Gateway with custom image (e.g., development build)
bash scripts/setup_gateway.sh --image hummingbot/gateway:development

# Start with custom Solana RPC (recommended to avoid rate limits)
bash scripts/setup_gateway.sh --rpc-url https://your-rpc-endpoint.com

# Configure RPC for a different network
bash scripts/setup_gateway.sh --network ethereum-mainnet --rpc-url https://your-eth-rpc.com

# Start with custom passphrase and port
bash scripts/setup_gateway.sh --passphrase mypassword --port 15888
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--status` | | Check Gateway status only (don't start) |
| `--image IMAGE` | `hummingbot/gateway:latest` | Docker image to use |
| `--passphrase TEXT` | `hummingbot` | Gateway passphrase |
| `--rpc-url URL` | | Custom RPC endpoint for `--network` |
| `--network ID` | `solana-mainnet-beta` | Network to configure RPC for |
| `--port PORT` | `15888` | Gateway port |

### Advanced: manage_gateway.py

For finer control (stop, restart, logs, per-network config), use `manage_gateway.py`:

```bash
python scripts/manage_gateway.py status                    # Check status
python scripts/manage_gateway.py start                     # Start Gateway
python scripts/manage_gateway.py stop                      # Stop Gateway
python scripts/manage_gateway.py restart                   # Restart Gateway
python scripts/manage_gateway.py logs                      # View logs
python scripts/manage_gateway.py networks                  # List all networks
python scripts/manage_gateway.py network solana-mainnet-beta                          # Get network config
python scripts/manage_gateway.py network solana-mainnet-beta --node-url https://...   # Set RPC node
```

### Custom RPC Nodes

Gateway uses public RPC nodes by default, which can hit rate limits. Set a custom nodeUrl per network to avoid this.

Popular Solana RPC providers:
- [Helius](https://helius.dev/) — Free tier available
- [QuickNode](https://quicknode.com/)
- [Alchemy](https://alchemy.com/)
- [Triton](https://triton.one/)

---

## Command: add-wallet

Add a Solana wallet for trading.

**Requires:** `deploy-hummingbot-api` and `setup-gateway` completed first.

### Usage

```bash
# List connected wallets
python scripts/add_wallet.py list

# Add wallet (prompted for private key — secure, not in shell history)
python scripts/add_wallet.py add

# Add wallet with private key directly
python scripts/add_wallet.py add --private-key <BASE58_KEY>

# Add wallet on a specific chain/network
python scripts/add_wallet.py add --chain solana --network mainnet-beta

# Check balances
python scripts/add_wallet.py balances --address <WALLET_ADDRESS>

# Check specific token balances
python scripts/add_wallet.py balances --address <WALLET_ADDRESS> --tokens SOL USDC

# Show all balances including zero
python scripts/add_wallet.py balances --address <WALLET_ADDRESS> --all
```

### Important Notes

- **Security**: Omit `--private-key` to be prompted securely (key won't appear in shell history)
- **SOL requirement**: Wallet needs SOL for transaction fees (~0.06 SOL per LP position for rent)
- **Default chain**: Solana mainnet-beta (override with `--chain` and `--network`)

---

## Command: explore-pools

Find and explore Meteora DLMM pools before creating LP positions.

**Note:** Pool listing (`list_meteora_pools.py`) works without any prerequisites — it queries the Meteora API directly. Pool details (`get_meteora_pool.py`) optionally uses Gateway for real-time price and liquidity charts.

### List Pools

Search and list pools by name, token, or address:

```bash
# Top pools by 24h volume
python scripts/list_meteora_pools.py

# Search by token symbol
python scripts/list_meteora_pools.py --query SOL
python scripts/list_meteora_pools.py --query USDC

# Search by pool name
python scripts/list_meteora_pools.py --query SOL-USDC

# Sort by different metrics
python scripts/list_meteora_pools.py --query SOL --sort tvl
python scripts/list_meteora_pools.py --query SOL --sort apr
python scripts/list_meteora_pools.py --query SOL --sort fees

# Pagination
python scripts/list_meteora_pools.py --query SOL --limit 50 --page 2
```

**Output columns:**
- **Pool**: Trading pair name
- **Pool Address**: Pool contract address (shortened, use `get_meteora_pool.py` for full address)
- **Base (mint)**: Base token symbol with shortened mint address
- **Quote (mint)**: Quote token symbol with shortened mint address
- **TVL**: Total value locked
- **Vol 24h**: 24-hour trading volume
- **Fees 24h**: Fees earned in last 24 hours
- **APR**: Annual percentage rate
- **Fee**: Base fee percentage
- **Bin**: Bin step (affects max position width)

**Note:** Token mints help identify the correct token when multiple tokens share the same name (e.g., multiple "PERCOLATOR" tokens).

### Get Pool Details

Get detailed information about a specific pool. Fetches from both Meteora API (historical data) and Gateway (real-time data):

```bash
python scripts/get_meteora_pool.py <pool_address>

# Example
python scripts/get_meteora_pool.py ATrBUW2reZiyftzMQA1hEo8b7w7o8ZLrhPd7M7sPMSms

# Output as JSON for programmatic use
python scripts/get_meteora_pool.py ATrBUW2reZiyftzMQA1hEo8b7w7o8ZLrhPd7M7sPMSms --json

# Skip Gateway (faster, no bin distribution)
python scripts/get_meteora_pool.py ATrBUW2reZiyftzMQA1hEo8b7w7o8ZLrhPd7M7sPMSms --no-gateway
```

**Data sources:**
- **Meteora API**: Historical volume, fees, APR, token info, market caps
- **Gateway** (requires running Gateway): Real-time price, liquidity distribution by bin

**Details shown:**
- Token info (symbols, mints, decimals, prices)
- Pool configuration (bin step, fees, max range width)
- Real-time price from Gateway (SOL/token ratio)
- Liquidity distribution chart showing bins around current price
- Liquidity and reserves
- Volume across time windows (30m, 1h, 4h, 12h, 24h)
- Fees earned across time windows
- Yield (APR, APY, farm rewards)
- Fee/TVL ratio (profitability indicator)

### Choosing a Pool

When selecting a pool, consider:

1. **TVL**: Higher TVL = more stable, but also more competition
2. **Volume**: Higher volume = more fee opportunities
3. **Fee/TVL Ratio**: Higher = more profitable per $ of liquidity
4. **Bin Step**: Determines max position width
   - `bin_step=1` → max ~0.69% width (tight ranges)
   - `bin_step=10` → max ~6.9% width (medium ranges)
   - `bin_step=100` → max ~69% width (wide ranges)

---

## Command: select-strategy

Help the user choose the right LP strategy. See `references/` for detailed guides.

### LP Rebalancer Controller (Recommended)

> **Reference:** `references/lp_rebalancer_guide.md`

A controller that automatically manages LP positions with rebalancing logic.

| Feature | Description |
|---------|-------------|
| **Auto-rebalance** | Closes and reopens positions when price exits range |
| **Price limits** | Configure BUY/SELL zones with anchor points |
| **KEEP logic** | Avoids unnecessary rebalancing when at optimal position |
| **Hands-off** | Set and forget - controller manages everything |

**Best for:** Longer-term LP strategies, range-bound markets, automated fee collection.

### LP Executor (Single Position)

> **Reference:** `references/lp_executor_guide.md`

Creates ONE liquidity position with fixed price bounds. No auto-rebalancing.

| Feature | Description |
|---------|-------------|
| **Fixed bounds** | Position stays at configured price range |
| **Manual control** | User decides when to close/reopen |
| **Limit orders** | Can auto-close when price exits range (like limit orders) |
| **Simple** | Direct control over single position |

**Best for:** Short-term positions, limit-order-style LP, manual management, testing.

### Quick Comparison

| Aspect | Rebalancer Controller | LP Executor |
|--------|----------------------|-------------|
| Rebalancing | Automatic | Manual |
| Position count | One at a time, auto-managed | One, fixed |
| Price limits | Yes (anchor points) | No (but has auto-close) |
| Complexity | Higher (more config) | Lower (simpler) |
| Use case | Set-and-forget | Precise control |

---

## Command: run-strategy

Run, monitor, and manage LP strategies.

**Requires:** `deploy-hummingbot-api`, `setup-gateway`, and `add-wallet` completed first.

### LP Rebalancer Controller (Recommended)

> **Reference:** See `references/lp_rebalancer_guide.md` for full configuration details, rebalancing logic, and KEEP vs REBALANCE scenarios.

Auto-rebalances positions when price moves out of range. Best for hands-off LP management.

```bash
# 1. Create LP Rebalancer config
python scripts/manage_controller.py create-config my_lp_config \
    --pool <pool_address> \
    --pair SOL-USDC \
    --amount 100 \
    --side 1 \
    --width 0.5 \
    --offset 0.01 \
    --rebalance-seconds 60 \
    --sell-max 100 \
    --sell-min 75 \
    --buy-max 90 \
    --buy-min 70

# 2. Deploy bot with the config
python scripts/manage_controller.py deploy my_lp_bot --configs my_lp_config

# 3. Monitor status
python scripts/manage_controller.py status
```

**Key Parameters:**

| Parameter | Description |
|-----------|-------------|
| `--amount` | Position size in quote currency |
| `--side` | 0=BOTH, 1=BUY (quote-only), 2=SELL (base-only) |
| `--width` | Position width % (must fit bin_step limits) |
| `--rebalance-seconds` | Seconds out-of-range before rebalancing |
| `--buy-max/--buy-min` | Price limits for BUY positions (anchor points) |
| `--sell-max/--sell-min` | Price limits for SELL positions (anchor points) |

### Single LP Executor (Alternative)

> **Reference:** See `references/lp_executor_guide.md` for state machine, single/double-sided positions, and limit range orders.

Creates ONE position with fixed bounds. Does NOT auto-rebalance.

```bash
python scripts/manage_executor.py create \
    --pool <pool_address> \
    --pair SOL-USDC \
    --quote-amount 100 \
    --lower 180 \
    --upper 185 \
    --side 1
```

**Key Parameters:**

| Parameter | Description |
|-----------|-------------|
| `--connector` | Must include `/clmm` suffix (default: `meteora/clmm`) |
| `--lower/--upper` | Position price bounds |
| `--base-amount/--quote-amount` | Token amounts (set one to 0 for single-sided) |
| `--side` | 0=BOTH, 1=BUY, 2=SELL |
| `--auto-close-above` | Auto-close when price above range (for limit orders) |
| `--auto-close-below` | Auto-close when price below range (for limit orders) |

### Monitor & Manage

**Check Status:**
```bash
# Bot status
python scripts/manage_controller.py status

# Executor list
python scripts/manage_executor.py list --type lp_executor

# Executor details
python scripts/manage_executor.py get <executor_id>

# Executor summary
python scripts/manage_executor.py summary
```

**Executor States:**
- `OPENING` - Creating position on-chain
- `IN_RANGE` - Position active, earning fees
- `OUT_OF_RANGE` - Price outside position bounds
- `CLOSING` - Removing position
- `FAILED` - Transaction failed

**Stop:**
```bash
# Stop bot (stops all its controllers)
python scripts/manage_controller.py stop my_lp_bot

# Stop individual executor (closes position)
python scripts/manage_executor.py stop <executor_id>

# Stop executor but keep position on-chain
python scripts/manage_executor.py stop <executor_id> --keep-position
```

---

## Command: analyze-performance

Export data and generate visual dashboards from LP position events. Scripts are in this skill's `scripts/` directory.

LP position events (ADD/REMOVE) are recorded **immediately** when transactions complete on-chain, so analysis works for both running and stopped bots.

### Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/export_lp_positions.py` | Export LP position events to CSV |
| `scripts/visualize_lp_positions.py` | Generate HTML dashboard from position events |

### Visualize LP Positions

Shows position ADD/REMOVE events from the blockchain. **Works for both running and stopped bots.**

```bash
# Basic usage (auto-detects database in data/)
python scripts/visualize_lp_positions.py --pair SOL-USDC

# Specify database explicitly
python scripts/visualize_lp_positions.py --db data/my_bot.sqlite --pair SOL-USDC

# Filter by connector
python scripts/visualize_lp_positions.py --pair SOL-USDC --connector meteora/clmm

# Last 24 hours only
python scripts/visualize_lp_positions.py --pair SOL-USDC --hours 24
```

**Dashboard Features:**
- KPI cards (total PnL, fees, IL, win/loss counts)
- Cumulative PnL & fees chart
- Price at open/close with LP range bounds
- Per-position PnL bar chart
- Duration vs PnL scatter plot
- Sortable positions table with Solscan links

### Export to CSV

```bash
# Export all position events
python scripts/export_lp_positions.py --db data/my_bot.sqlite

# Filter by trading pair
python scripts/export_lp_positions.py --pair SOL-USDC --output exports/positions.csv

# Show summary without exporting
python scripts/export_lp_positions.py --summary
```

---

## Quick Reference

### Common Workflows

**Full Setup (first time):**
```bash
# 1. Deploy API
bash scripts/deploy_hummingbot_api.sh install

# 2. Start Gateway
bash scripts/setup_gateway.sh --rpc-url https://your-rpc-endpoint.com

# 3. Add wallet
python scripts/add_wallet.py add

# 4. Find pool
python scripts/list_meteora_pools.py --query SOL-USDC

# 5. Check bin_step
python scripts/get_meteora_pool.py <pool_address>

# 6. Create config and deploy
python scripts/manage_controller.py create-config my_lp --pool <pool_address> --pair SOL-USDC --amount 100
python scripts/manage_controller.py deploy my_bot --configs my_lp

# 7. Verify
python scripts/manage_controller.py status
```

**Analyze LP Positions:**
```bash
# Visualize
python scripts/visualize_lp_positions.py --pair SOL-USDC

# Export CSV
python scripts/export_lp_positions.py --pair SOL-USDC
```

### Checking Prerequisites

Before running commands that need the API or Gateway, verify they're running:

```bash
bash scripts/check_api.sh       # Is Hummingbot API running?
bash scripts/check_gateway.sh   # Is Gateway running? (also checks API)
```

Both support `--json` output. These scripts are also used internally by `setup_gateway.sh` and can be sourced by other shell scripts.

### Scripts Reference

| Script | Purpose |
|--------|---------|
| `check_api.sh` | Check if Hummingbot API is running (shared) |
| `check_gateway.sh` | Check if Gateway is running (shared) |
| `deploy_hummingbot_api.sh` | Install/upgrade/manage Hummingbot API |
| `setup_gateway.sh` | Start Gateway and configure RPC |
| `add_wallet.py` | Add wallets and check balances |
| `manage_gateway.py` | Advanced Gateway management |
| `list_meteora_pools.py` | Search and list pools |
| `get_meteora_pool.py` | Get pool details with liquidity chart |
| `manage_executor.py` | Create, list, stop LP executors |
| `manage_controller.py` | Create configs, deploy bots, get status |
| `export_lp_positions.py` | Export position events to CSV |
| `visualize_lp_positions.py` | Generate HTML dashboard |

### Error Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "InvalidRealloc" | Position range too wide | Reduce `--width` (check bin_step limits) |
| State stuck "OPENING" | Transaction failed | Stop executor, reduce range, retry |
| "Insufficient balance" | Not enough tokens | Check wallet has tokens + 0.06 SOL for rent |
