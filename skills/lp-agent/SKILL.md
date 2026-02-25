---
name: lp-agent
description: Run automated trading strategies on concentrated liquidity (CLMM) positions on DEXs like Meteora and Raydium.
metadata:
  author: hummingbot
---

# lp-agent

This skill helps you run automated trading strategies on concentrated liquidity (CLMM) positions on Solana DEXs like Meteora and Orca.

**Tasks** (start with any):
1. **Strategy Selector** - Choose between LP Executor or Rebalancer Controller
2. **Pool Explorer** - Find and explore Meteora pools
3. **Deployment** - Deploy LP positions
4. **Monitoring** - Track running positions
5. **Analysis** - Visualize performance

## Prerequisites

Before using this skill, ensure hummingbot-api is running:

```bash
bash <(curl -s https://raw.githubusercontent.com/hummingbot/skills/main/skills/lp-agent/scripts/check_prerequisites.sh)
```

If not installed, use the `hummingbot-deploy` skill first.

**Gateway** is required for LP operations. Start it with:
```bash
python scripts/manage_gateway.py start
```

To avoid RPC rate limits, configure a custom Solana RPC endpoint:
```bash
python scripts/manage_gateway.py network solana-mainnet-beta --node-url https://your-rpc-endpoint.com
```

---

## Task 1: Strategy Selector

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

## Task 2: Pool Explorer

Use these scripts to find and explore Meteora DLMM pools before creating LP positions. Scripts are in this skill's `scripts/` directory.

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

## Task 3: Deployment

### Step 3.1: Deploy LP Rebalancer Controller (Recommended)

> **Reference:** See `references/lp_rebalancer_guide.md` for full configuration details, rebalancing logic, and KEEP vs REBALANCE scenarios.

Auto-rebalances positions when price moves out of range. Best for hands-off LP management.

```bash
# Create LP Rebalancer config
python scripts/manage_controller.py create-config my_lp_config \
    --pool <pool_address> \
    --pair SOL-USDC \
    --amount 100 \
    --side 1 \
    --width 0.5 \
    --offset 0.01 \
    --rebalance-seconds 60

# Deploy bot with the config
python scripts/manage_controller.py deploy my_lp_bot --configs my_lp_config
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

### Step 3.2: Deploy Single LP Executor (Alternative)

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

### Step 3.3: Verify Deployment

**For LP Rebalancer Controller:**
```bash
# Check bot status
python scripts/manage_controller.py status

# Get bot logs
python scripts/manage_controller.py logs my_lp_bot
```

**For LP Executor:**
```bash
# List executors
python scripts/manage_executor.py list --type lp_executor

# Get specific executor
python scripts/manage_executor.py get <executor_id>
```

Check state:
- `OPENING` → Transaction in progress, wait 5-10 seconds
- `IN_RANGE` or `OUT_OF_RANGE` → Success!
- `FAILED` or `RETRIES_EXCEEDED` → Check error, possibly reduce range width

---

## Task 4: Monitoring

### Monitor Controller Status

```bash
# Get all active bots status
python scripts/manage_controller.py status

# Get bot logs
python scripts/manage_controller.py logs my_lp_bot --limit 100

# Get error logs only
python scripts/manage_controller.py logs my_lp_bot --type error
```

### Monitor Executor Details

```bash
# List all LP executors
python scripts/manage_executor.py list --type lp_executor

# Get specific executor state
python scripts/manage_executor.py get <executor_id>

# Get executor logs
python scripts/manage_executor.py logs <executor_id>

# Get summary of all executors
python scripts/manage_executor.py summary
```

### Key State Values to Monitor

**Executor States:**
- `OPENING` - Creating position on-chain
- `IN_RANGE` - Position active, earning fees
- `OUT_OF_RANGE` - Price outside position bounds
- `CLOSING` - Removing position
- `FAILED` - Transaction failed

**Controller Behavior:**
- When `OUT_OF_RANGE` for `rebalance_seconds`, controller closes and reopens position
- If price hits limits (`buy_price_min`, `sell_price_max`, etc.), controller KEEPs position instead of rebalancing

### Stop Controller/Executor

```bash
# Stop bot (stops all its controllers)
python scripts/manage_controller.py stop my_lp_bot

# Stop specific controllers within a bot
python scripts/manage_controller.py stop-controllers my_lp_bot --controllers my_lp_config

# Stop individual executor (closes position)
python scripts/manage_executor.py stop <executor_id>

# Stop executor but keep position on-chain
python scripts/manage_executor.py stop <executor_id> --keep-position
```

---

## Task 5: Analysis

Use the analysis scripts to export data and generate visual dashboards. Scripts are in this skill's `scripts/` directory.

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

**Start LP Rebalancer:**
```bash
# 1. Find pool
python scripts/list_meteora_pools.py --query SOL-USDC

# 2. Check bin_step
python scripts/get_meteora_pool.py <pool_address>

# 3. Create config and deploy
python scripts/manage_controller.py create-config my_lp --pool <pool_address> --pair SOL-USDC --amount 100
python scripts/manage_controller.py deploy my_bot --configs my_lp

# 4. Verify
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
