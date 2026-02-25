---
name: lp-agent
description: Manage concentrated liquidity (CLMM) positions on DEXs like Meteora and Raydium. Create, monitor, and rebalance LP positions automatically.
metadata:
  author: hummingbot
---

# lp-agent

This skill helps you run and analyze concentrated liquidity (CLMM) positions on Solana DEXs like Meteora and Orca.

**Two paths available:**
- **New Bot**: Selection → Deployment → Monitoring
- **Analyze Existing**: Skip directly to Analysis

**Tasks:**
1. **Selection** - Choose to start a new bot OR analyze existing data
2. **Pool Explorer** - Find and explore Meteora pools before deploying
3. **Deployment** - Configure and deploy LP Executor or LP Rebalancer controller
4. **Monitoring** - Track status and logs of running controllers/executors
5. **Analysis** - Export data and generate visual dashboards to analyze performance

## Prerequisites

Before using this skill, ensure hummingbot-api and MCP are running:

```bash
bash <(curl -s https://raw.githubusercontent.com/hummingbot/skills/main/skills/lp-agent/scripts/check_prerequisites.sh)
```

If not installed, use the `hummingbot-deploy` skill first.

---

## Task 1: Selection

**First, ask the user:**
"Do you want to **start a new LP bot** or **analyze an existing one**?"

### Path A: Start New Bot
If user wants to start a new bot, ask which type:

**Option A1: LP Executor (Single Position)**
- Creates ONE liquidity position with fixed price bounds
- Does NOT auto-rebalance when price moves out of range
- Best for: Short-term positions, manual management, testing

**Option A2: LP Rebalancer Controller (Recommended)**
- Creates and manages positions automatically
- Auto-rebalances when price moves out of range
- Supports price limits to control when to rebalance vs keep position
- Best for: Hands-off LP management, longer-term strategies

Then proceed to **Task 2: Pool Explorer** → **Task 3: Deployment** → **Task 4: Monitoring**

### Path B: Analyze Existing Bot
If user wants to analyze existing data, **skip directly to Task 5: Analysis**.

**Default to LP Positions analysis** (`export_lp_positions.py` / `visualize_lp_positions.py`) - this works for both running and stopped bots since position events are recorded immediately when positions are created/closed on-chain.


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

### Step 3.1: Find a Pool

```
# List popular pools
manage_gateway_clmm(action="list_pools", connector="meteora", search_term="SOL")

# Get pool details (IMPORTANT: check bin_step for range limits)
manage_gateway_clmm(action="get_pool_info", connector="meteora", network="solana-mainnet-beta", pool_address="<address>")
```

**CRITICAL - Check bin_step for range limits:**
- `bin_step=1` → max ~0.69% width
- `bin_step=10` → max ~6.9% width
- `bin_step=100` → max ~69% width
- Formula: `max_width_pct = bin_step * 69 / 100`

### Step 3.2: Deploy LP Rebalancer Controller (Recommended)

```
manage_controllers(
    action="create",
    controller_config={
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

**LP Rebalancer Config Fields:**

| Field | Description | Default |
|-------|-------------|---------|
| `connector_name` | CLMM connector (e.g., `meteora/clmm`, `orca/clmm`) | `meteora/clmm` |
| `network` | Network name | `solana-mainnet-beta` |
| `trading_pair` | Pair format "BASE-QUOTE" | Required |
| `pool_address` | Pool contract address | Required |
| `total_amount_quote` | Amount in quote currency for each position | `50` |
| `side` | 0=BOTH, 1=BUY (quote-only), 2=SELL (base-only) | `1` |
| `position_width_pct` | Position width as % (must fit bin_step limits) | `0.5` |
| `position_offset_pct` | Offset from price to start out-of-range | `0.01` |
| `rebalance_seconds` | Seconds out-of-range before rebalancing | `60` |
| `rebalance_threshold_pct` | Price must be this % out before timer starts | `0.1` |
| `sell_price_max/min` | Price limits for sell positions (null = no limit) | `null` |
| `buy_price_max/min` | Price limits for buy positions (null = no limit) | `null` |
| `strategy_type` | Meteora: 0=Spot, 1=Curve, 2=Bid-Ask | `0` |

**Side Values:**
- `0` = Both-sided (base + quote) - provides liquidity on both sides
- `1` = Buy (quote-only) - range below current price, buys base as price drops
- `2` = Sell (base-only) - range above current price, sells base as price rises

### Step 3.3: Deploy Single LP Executor (Alternative)

```
manage_executors(
    action="create",
    executor_config={
        "type": "lp_executor",
        "connector_name": "meteora/clmm",
        "pool_address": "<pool_address>",
        "trading_pair": "SOL-USDC",
        "base_token": "SOL",
        "quote_token": "USDC",
        "base_amount": 0,
        "quote_amount": 100,
        "lower_price": 180,
        "upper_price": 185,
        "side": 1
    }
)
```

### Step 3.4: Verify Deployment

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
