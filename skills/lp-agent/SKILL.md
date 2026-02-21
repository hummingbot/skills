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
2. **Deployment** - Configure and deploy LP Executor or LP Rebalancer controller
3. **Monitoring** - Track status and logs of running controllers/executors
4. **Analysis** - Export data and generate visual dashboards to analyze performance

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

Then proceed to **Task 2: Deployment** → **Task 3: Monitoring**

### Path B: Analyze Existing Bot
If user wants to analyze existing data, **skip directly to Task 4: Analysis**.

**Default to LP Positions analysis** (`export_lp_positions.py` / `visualize_lp_positions.py`) - this works for both running and stopped bots since position events are recorded immediately when positions are created/closed on-chain.

Only use Executor analysis if user explicitly asks for it, and explain:
> **Note:** Executors are only saved to the database when:
> 1. They complete/close (e.g., after a rebalance)
> 2. The bot shuts down gracefully
>
> If the bot is still running with active positions, use LP Positions analysis instead.

---

## Task 2: Deployment

### Step 2.1: Find a Pool

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

### Step 2.2: Deploy LP Rebalancer Controller (Recommended)

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

### Step 2.3: Deploy Single LP Executor (Alternative)

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

### Step 2.4: Verify Deployment

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

## Task 3: Monitoring

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

## Task 4: Analysis

Use the analysis scripts to export data and generate visual dashboards. Scripts are in this skill's `scripts/` directory.

### Important: Positions vs Executors

**Default to LP Positions analysis** for running bots:
- LP position events (ADD/REMOVE) are recorded **immediately** when transactions complete on-chain
- Works for both running and stopped bots

**Executor analysis** requires completed executors:
- Executors are only saved to database when they **complete/close** (e.g., after rebalance) or when the **bot shuts down gracefully**
- If no executors found, the bot is likely still running - use LP Positions instead

### Available Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `scripts/export_lp_positions.py` | Export LP position events to CSV | **Default** - works for running bots |
| `scripts/visualize_lp_positions.py` | Generate HTML dashboard from position events | **Default** - works for running bots |
| `scripts/export_lp_executors.py` | Export executor data from SQLite to CSV | After bot stops or rebalances |
| `scripts/visualize_executors.py` | Generate HTML dashboard from executor data | After bot stops or rebalances |

### Visualize LP Positions (Recommended for Running Bots)

Shows position ADD/REMOVE events from the blockchain. **Works immediately for running bots.**

```bash
# Basic usage (auto-detects database in data/)
python scripts/visualize_lp_positions.py --pair SOL-USDC

# Specify database explicitly
python scripts/visualize_lp_positions.py --db data/my_bot.sqlite --pair SOL-USDC

# Filter by connector
python scripts/visualize_lp_positions.py --db data/my_bot.sqlite --pair SOL-USDC --connector meteora/clmm
```

**Dashboard Features:**
- Position range chart over time
- Position table with PnL, fees, duration
- Detailed position panel with ADD/REMOVE amounts
- Links to Solscan for transaction verification

### Visualize Executors (After Bot Stops or Rebalances)

Shows PnL, fees, duration, and range utilization for executors created by a controller.

> **Note:** If no executors found, the bot is likely still running. Use LP Positions analysis instead, or stop the bot gracefully to flush executor data to the database.

```bash
python scripts/visualize_executors.py <controller_id>
python scripts/visualize_executors.py <controller_id> --db data/my.sqlite
python scripts/visualize_executors.py <controller_id> --output report.html --no-open
```

**Dashboard Features:**
- Cumulative PnL & fees chart
- Per-executor PnL bar chart
- Price & LP range chart
- Position range visualization over time
- Filterable executor table with sorting
- Detailed executor panel showing all metrics

### Export to CSV for External Analysis

```bash
# Export position events (works for running bots)
python scripts/export_lp_positions.py --db data/my_bot.sqlite --output exports/positions.csv

# Export executor data (requires completed executors)
python scripts/export_lp_executors.py <controller_id> --db data/my_bot.sqlite --output exports/executors.csv
```

---

## Quick Reference

### Common Workflows

**Start LP Rebalancer:**
1. Find pool: `manage_gateway_clmm(action="list_pools", ...)`
2. Check bin_step: `manage_gateway_clmm(action="get_pool_info", ...)`
3. Deploy: `manage_controllers(action="create", controller_config={...})`
4. Verify: `manage_controllers(action="get_active")`

**Analyze Running Bot:**
1. Export positions: `python scripts/export_lp_positions.py --db data/<db>.sqlite`
2. Visualize: `python scripts/visualize_lp_positions.py --db data/<db>.sqlite --pair SOL-USDC`
3. Review dashboard in browser

**Analyze After Bot Stops:**
1. Stop: `manage_controllers(action="stop", controller_id="<id>")`
2. Export executors: `python scripts/export_lp_executors.py <controller_id> --db data/<db>.sqlite`
3. Visualize: `python scripts/visualize_executors.py <controller_id> --db data/<db>.sqlite`

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
| No executors found | Bot still running | Use LP Positions analysis instead, or run `stop` in Hummingbot CLI to flush executors to DB |
