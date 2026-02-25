---
name: lp-agent
description: Manage concentrated liquidity (CLMM) positions on DEXs like Meteora and Raydium. Create, monitor, and rebalance LP positions automatically.
metadata:
  author: hummingbot
---

# lp-agent

This skill helps you run and analyze concentrated liquidity (CLMM) positions on Solana DEXs like Meteora and Orca.

**Tasks** (start with any):
1. **Strategy Selector** - Choose between LP Executor or Rebalancer Controller
2. **Pool Explorer** - Find and explore Meteora pools
3. **Deployment** - Deploy LP positions
4. **Monitoring** - Track running positions
5. **Analysis** - Visualize performance

## Prerequisites

Before using this skill, ensure hummingbot-api and MCP are running:

```bash
bash <(curl -s https://raw.githubusercontent.com/hummingbot/skills/main/skills/lp-agent/scripts/check_prerequisites.sh)
```

If not installed, use the `hummingbot-deploy` skill first.

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

```
modify_controllers(
    action="upsert",
    target="config",
    config_name="my_lp_config",
    config_data={
        "controller_name": "lp_rebalancer",
        "connector_name": "meteora/clmm",
        "network": "solana-mainnet-beta",
        "trading_pair": "SOL-USDC",
        "pool_address": "<pool_address>",
        "total_amount_quote": 100,
        "side": 1,
        "position_width_pct": 0.5,
        "position_offset_pct": 0.01,
        "rebalance_seconds": 60,
        "rebalance_threshold_pct": 0.1,
        "sell_price_max": null,
        "sell_price_min": null,
        "buy_price_max": null,
        "buy_price_min": null,
        "strategy_type": 0
    }
)
```

Then deploy with:
```
deploy_bot_with_controllers(bot_name="my_lp_bot", controllers_config=["my_lp_config"])
```

**Key Parameters:**

| Parameter | Description |
|-----------|-------------|
| `total_amount_quote` | Position size in quote currency |
| `side` | 0=BOTH, 1=BUY (quote-only), 2=SELL (base-only) |
| `position_width_pct` | Position width % (must fit bin_step limits) |
| `rebalance_seconds` | Seconds out-of-range before rebalancing |
| `buy_price_max/min` | Price limits for BUY positions (anchor points) |
| `sell_price_max/min` | Price limits for SELL positions (anchor points) |

### Step 3.2: Deploy Single LP Executor (Alternative)

> **Reference:** See `references/lp_executor_guide.md` for state machine, single/double-sided positions, and limit range orders.

Creates ONE position with fixed bounds. Does NOT auto-rebalance.

```
manage_executors(
    action="create",
    executor_config={
        "type": "lp_executor",
        "connector_name": "meteora/clmm",
        "pool_address": "<pool_address>",
        "trading_pair": "SOL-USDC",
        "base_amount": 0,
        "quote_amount": 100,
        "lower_price": 180,
        "upper_price": 185,
        "side": 1
    }
)
```

**Key Parameters:**

| Parameter | Description |
|-----------|-------------|
| `connector_name` | Must include `/clmm` suffix (e.g., `meteora/clmm`) |
| `lower_price/upper_price` | Position price bounds |
| `base_amount/quote_amount` | Token amounts (set one to 0 for single-sided) |
| `side` | 0=BOTH, 1=BUY, 2=SELL |
| `auto_close_above_range_seconds` | Auto-close when price above range (for limit orders) |
| `auto_close_below_range_seconds` | Auto-close when price below range (for limit orders) |

### Step 3.3: Verify Deployment

**For LP Rebalancer Controller:**
```
# Check controller status
manage_controllers(action="get_active")

# See executors created by the controller
manage_executors(action="search", executor_types=["lp_executor"])
```

**For LP Executor:**
```
# Poll until state changes from OPENING
manage_executors(action="get", executor_id="<executor_id>")
```

Check `custom_info.state`:
- `OPENING` → Transaction in progress, wait 5-10 seconds
- `IN_RANGE` or `OUT_OF_RANGE` → Success!
- `FAILED` or `RETRIES_EXCEEDED` → Check error, possibly reduce range width

---

## Task 4: Monitoring

### Monitor Controller Status

```
# List active controllers
manage_controllers(action="get_active")

# Get controller details
manage_controllers(action="get", controller_id="<controller_id>")

# See all executors from the controller
manage_executors(action="search", executor_types=["lp_executor"])
```

### Monitor Executor Details

```
# Get specific executor state
manage_executors(action="get", executor_id="<executor_id>")

# Get summary of all executors
manage_executors(action="get_summary")
```

### Key State Values to Monitor

**Executor States (`custom_info.state`):**
- `OPENING` - Creating position on-chain
- `IN_RANGE` - Position active, earning fees
- `OUT_OF_RANGE` - Price outside position bounds
- `CLOSING` - Removing position
- `FAILED` - Transaction failed

**Controller Behavior:**
- When `OUT_OF_RANGE` for `rebalance_seconds`, controller closes and reopens position
- If price hits limits (`buy_price_min`, `sell_price_max`, etc.), controller KEEPs position instead of rebalancing

### Check Logs for Errors

```
# Use Bash to tail hummingbot logs
tail -100 /path/to/hummingbot/logs/logs_*.log | grep -i "lp\|error\|fail"
```

### Stop Controller/Executor

```
# Stop controller (stops all its executors)
manage_controllers(action="stop", controller_id="<controller_id>")

# Stop individual executor
manage_executors(action="stop", executor_id="<executor_id>", keep_position=false)
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
1. Find pool: `manage_gateway_clmm(action="list_pools", ...)`
2. Check bin_step: `manage_gateway_clmm(action="get_pool_info", ...)`
3. Deploy: `manage_controllers(action="create", controller_config={...})`
4. Verify: `manage_controllers(action="get_active")`

**Analyze LP Positions:**
1. Visualize: `python scripts/visualize_lp_positions.py --pair SOL-USDC`
2. Review dashboard in browser
3. Export CSV: `python scripts/export_lp_positions.py --pair SOL-USDC`

### MCP Tools Reference

| Tool | Actions |
|------|---------|
| `manage_gateway_clmm` | `list_pools`, `get_pool_info`, `get_positions`, `collect_fees` |
| `manage_controllers` | `create`, `get_active`, `get`, `stop`, `update` |
| `manage_executors` | `create`, `get`, `search`, `stop`, `get_summary` |

### Error Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "InvalidRealloc" | Position range too wide | Reduce `position_width_pct` (check bin_step limits) |
| State stuck "OPENING" | Transaction failed | Stop executor, reduce range, retry |
| "Insufficient balance" | Not enough tokens | Check wallet has tokens + 0.06 SOL for rent |
