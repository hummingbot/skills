---
name: lp-agent
description: Run automated liquidity provision strategies on concentrated liquidity (CLMM) DEXs using Hummingbot API.
metadata:
  author: hummingbot
commands:
  deploy-hummingbot-api:
    description: Deploy Hummingbot API trading infrastructure
  setup-gateway:
    description: Start Gateway and configure Solana RPC endpoint
  add-wallet:
    description: Add or import a Solana wallet for trading
  explore-pools:
    description: Find and explore Meteora DLMM pools
  select-strategy:
    description: Choose between LP Executor or Rebalancer Controller strategy
  deploy:
    description: Deploy, monitor, and manage LP strategies
  analyze:
    description: Export data and visualize LP position performance
---

# lp-agent

This skill helps you run automated liquidity provision strategies on concentrated liquidity (CLMM) DEXs using Hummingbot API.

**Commands** (run as `/lp-agent <command>`):

| Command | Description |
|---------|-------------|
| `deploy-hummingbot-api` | Deploy Hummingbot API trading infrastructure |
| `setup-gateway` | Start Gateway and configure Solana RPC |
| `add-wallet` | Add or import a Solana wallet |
| `explore-pools` | Find and explore Meteora DLMM pools |
| `select-strategy` | Choose LP Executor or Rebalancer Controller |
| `deploy` | Deploy, monitor, and stop LP strategies |
| `analyze` | Visualize LP position performance |

**Typical workflow:** `deploy-hummingbot-api` → `setup-gateway` → `add-wallet` → `explore-pools` → `select-strategy` → `deploy` → `analyze`

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

Start the Gateway service and optionally configure a custom Solana RPC endpoint. Gateway is required for all LP operations on DEXs.

### Usage

```bash
# Start Gateway with defaults
bash scripts/setup_gateway.sh

# Start with custom Solana RPC (recommended to avoid rate limits)
bash scripts/setup_gateway.sh --rpc-url https://your-rpc-endpoint.com

# Start with custom passphrase
bash scripts/setup_gateway.sh --passphrase mypassword

# Check Gateway status only
bash scripts/setup_gateway.sh --status
```

### Advanced Gateway Management

For finer control, use `manage_gateway.py` directly:

```bash
# Check status
python scripts/manage_gateway.py status

# Start/stop/restart
python scripts/manage_gateway.py start --passphrase mypassword
python scripts/manage_gateway.py stop
python scripts/manage_gateway.py restart

# View logs
python scripts/manage_gateway.py logs [--limit 100]

# List all supported networks
python scripts/manage_gateway.py networks

# Get network config
python scripts/manage_gateway.py network solana-mainnet-beta

# Set custom RPC node (avoid rate limits)
python scripts/manage_gateway.py network solana-mainnet-beta --node-url https://my-rpc.example.com
```

### Custom RPC Nodes

Gateway uses public RPC nodes by default, which can hit rate limits. Popular Solana RPC providers:
- [Helius](https://helius.dev/) — Free tier available
- [QuickNode](https://quicknode.com/)
- [Alchemy](https://alchemy.com/)
- [Triton](https://triton.one/)

---

## Command: add-wallet

Add a Solana wallet for trading. Gateway must be running first (`setup-gateway`).

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

Find and explore Meteora DLMM pools before creating LP positions. Scripts are in this skill's `scripts/` directory.

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

## Command: deploy

Deploy, monitor, and manage LP strategies.

### Deploy LP Rebalancer Controller (Recommended)

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

### Deploy Single LP Executor (Alternative)

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

## Command: analyze

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

### Scripts Reference

| Script | Purpose |
|--------|---------|
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
