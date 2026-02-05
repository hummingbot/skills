---
name: lp-agent
description: Manage concentrated liquidity (CLMM) positions on DEXs like Meteora and Raydium. Create, monitor, and rebalance LP positions automatically.
metadata:
  author: hummingbot
---

# lp-agent

This skill manages **concentrated liquidity (CLMM) positions** on decentralized exchanges like Meteora (Solana) and Raydium. It provides automated LP position management with rebalancing capabilities similar to the LP Manager controller.

## Prerequisites

Before using this skill, ensure hummingbot-api and MCP are running:

```bash
./scripts/check_prerequisites.sh
```

If not installed, use the `hummingbot-deploy` skill first.

## Quick Start

### 1. Find a Pool

Use the `manage_gateway_clmm` MCP tool:

```
# List popular pools on Meteora
manage_gateway_clmm(action="list_pools", connector="meteora")

# Search for specific pools
manage_gateway_clmm(action="list_pools", connector="meteora", search_term="SOL")

# Get detailed pool info
manage_gateway_clmm(action="get_pool_info", connector="meteora", network="solana-mainnet-beta", pool_address="<address>")
```

### 2. Create LP Position

```
# First, see the LP executor config schema
manage_executors(executor_type="lp_executor")

# Create position with quote only (buy base as price drops)
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
        "upper_price": 200,
        "side": 1
    }
)
```

**Side values:**
- `0` = Both-sided (base + quote)
- `1` = Buy (quote-only, range below current price)
- `2` = Sell (base-only, range above current price)

**IMPORTANT - Verify Position Creation:**

After creating an executor, you MUST verify the position was actually created on-chain. Follow these steps:

**Step 1: Get the executor ID from the creation response**
The `manage_executors(action="create")` call returns the executor_id. If it returns "N/A", search for it:
```
manage_executors(action="search", executor_types=["lp_executor"], status="RUNNING")
```

**Step 2: Poll executor state until it changes from OPENING**
```
manage_executors(action="get", executor_id="<executor_id>")
```

Check `custom_info.state`:
- `OPENING` → Transaction in progress, **wait 5-10 seconds and check again**
- `IN_RANGE` or `OUT_OF_RANGE` → Position created successfully ✓
- `FAILED` or `RETRIES_EXCEEDED` → Transaction failed ✗

**Step 3: Confirm position exists on-chain**
Even if state shows success, verify the position actually exists:
```
manage_gateway_clmm(
    action="get_positions",
    connector="meteora",
    network="solana-mainnet-beta",
    pool_address="<pool_address>"
)
```

The response should contain a position with matching `lower_price` and `upper_price`.

**If verification fails:**
1. Stop the failed executor: `manage_executors(action="stop", executor_id="<id>", keep_position=false)`
2. Check the error in `custom_info.error` if available
3. Common issues: range too wide (reduce width), insufficient balance, network congestion

**IMPORTANT - Range Width Limits:**

Meteora DLMM pools have bin limits. Each bin represents a small price increment based on `bin_step`:
- `bin_step=1` → Each bin is 0.01% apart
- `bin_step=10` → Each bin is 0.1% apart
- `bin_step=100` → Each bin is 1% apart

**Maximum bins per position is ~69 due to Solana account size limits.**

Calculate maximum range width:
```
max_width_pct = bin_step * 69 / 100
```

Examples:
- `bin_step=1`: max ~0.69% width
- `bin_step=10`: max ~6.9% width
- `bin_step=100`: max ~69% width

Get bin_step from pool info before creating position:
```
manage_gateway_clmm(action="get_pool_info", connector="meteora", network="solana-mainnet-beta", pool_address="<address>")
```

Look for `bin_step` in the response and calculate appropriate range width.

### 3. Monitor Positions

```
# List all LP positions
manage_executors(action="search", executor_types=["lp_executor"])

# Get specific position details
manage_executors(action="get", executor_id="<executor_id>")

# Get positions summary
manage_executors(action="get_summary")
```

### 4. Manage Positions

```
# Collect fees (via Gateway CLMM)
manage_gateway_clmm(
    action="collect_fees",
    connector="meteora",
    network="solana-mainnet-beta",
    position_address="<position_nft_address>"
)

# Close position
manage_executors(action="stop", executor_id="<executor_id>", keep_position=false)
```

### 5. Rebalance (Script)

For rebalancing, use the script which implements the LP Manager controller logic:

```bash
# Manual rebalance
./scripts/rebalance_position.sh --id <executor_id>

# Auto-rebalance (monitors and rebalances when out of range for N seconds)
./scripts/auto_rebalance.sh --id <executor_id> --delay 60
```

## Position Types

### Double-Sided (Both Tokens)

Provide liquidity with both base and quote tokens. Best when you expect price to stay within range.

```
     Lower          Current         Upper
       |---------------|---------------|
       |<-- Quote zone | Base zone -->|
```

- Price goes UP: You sell base, accumulate quote
- Price goes DOWN: You buy base with quote

### Single-Sided: Quote Only (side=1)

Position entire range BELOW current price. You're buying base as price drops.

```
     Lower          Upper    Current
       |---------------|--------|
       |<---- Buy zone ---->|
```

### Single-Sided: Base Only (side=2)

Position entire range ABOVE current price. You're selling base as price rises.

```
                   Current    Lower          Upper
                      |--------|---------------|
                               |<-- Sell zone -->|
```

## Rebalancing Strategy

When price moves out of your position range, follow this logic (same as LP Manager controller):

### Step 1: Check Position State

```
manage_executors(action="get", executor_id="<id>")
```

Look at `custom_info.state`:
- `IN_RANGE` → No rebalance needed
- `OUT_OF_RANGE` → Check direction and rebalance

### Step 2: Determine Rebalance Direction

Compare `custom_info.current_price` with `custom_info.lower_price` and `custom_info.upper_price`:

**If current_price < lower_price (price dropped below range):**
- You're now holding mostly BASE tokens
- Strategy: Create BASE-ONLY position ABOVE current price
- This lets you sell base as price recovers

**If current_price > upper_price (price rose above range):**
- You're now holding mostly QUOTE tokens
- Strategy: Create QUOTE-ONLY position BELOW current price
- This lets you buy base if price drops

### Step 3: Calculate New Position

For a position width of W% (e.g., 5%):

**Price below range (base-only, side=2):**
```
new_lower_price = current_price
new_upper_price = current_price * (1 + W/100)
new_base_amount = old_base_amount + old_base_fee
new_quote_amount = 0
side = 2
```

**Price above range (quote-only, side=1):**
```
new_lower_price = current_price * (1 - W/100)
new_upper_price = current_price
new_base_amount = 0
new_quote_amount = old_quote_amount + old_quote_fee
side = 1
```

### Step 4: Close Old Position

```
manage_executors(action="stop", executor_id="<old_id>", keep_position=false)
```

### Step 5: Create New Position

```
manage_executors(action="create", executor_config={
    "type": "lp_executor",
    "connector_name": "<same_connector>",
    "pool_address": "<same_pool>",
    "trading_pair": "<same_pair>",
    "base_token": "<base>",
    "quote_token": "<quote>",
    "base_amount": <new_base_amount>,
    "quote_amount": <new_quote_amount>,
    "lower_price": <new_lower_price>,
    "upper_price": <new_upper_price>,
    "side": <side>
})
```

### Step 6: Verify New Position

```
manage_executors(action="get", executor_id="<new_id>")
```

Confirm `custom_info.state` is `IN_RANGE` or `OUT_OF_RANGE` (not `OPENING` or `FAILED`).

### Auto-Rebalance Script

For continuous monitoring with automatic rebalancing, use the script:

```bash
./scripts/auto_rebalance.sh --id <executor_id> --delay 60 --width 5.0
```

This monitors the position and triggers rebalance when out of range for the specified delay.

## MCP Tools Reference

### manage_gateway_clmm

| Action | Parameters | Description |
|--------|------------|-------------|
| `list_pools` | connector, search_term, sort_key, limit | Browse available pools |
| `get_pool_info` | connector, network, pool_address | Get pool details |
| `get_positions` | connector, network, pool_address | Get positions in a pool |
| `open_position` | connector, network, pool_address, lower_price, upper_price, base_token_amount, quote_token_amount | Open position directly |
| `close_position` | connector, network, position_address | Close position |
| `collect_fees` | connector, network, position_address | Collect accumulated fees |

### manage_executors

| Action | Parameters | Description |
|--------|------------|-------------|
| (none) | executor_type="lp_executor" | Show config schema |
| `create` | executor_config | Create LP executor |
| `search` | executor_types=["lp_executor"] | List LP executors |
| `get` | executor_id | Get executor details |
| `stop` | executor_id, keep_position | Stop executor |
| `get_summary` | - | Get overall summary |

## Scripts (for operations without MCP tools)

| Script | Purpose |
|--------|---------|
| `check_prerequisites.sh` | Verify API, Gateway, wallet setup |
| `rebalance_position.sh` | Close and reopen position centered on current price |
| `auto_rebalance.sh` | Continuous monitoring with auto-rebalance |

## LP Executor Config Schema

```json
{
    "type": "lp_executor",
    "connector_name": "meteora/clmm",
    "pool_address": "2sfXxxxx...",
    "trading_pair": "SOL-USDC",
    "base_token": "SOL",
    "quote_token": "USDC",
    "base_amount": 0,
    "quote_amount": 100,
    "lower_price": 180,
    "upper_price": 200,
    "side": 1,
    "extra_params": {
        "strategyType": 0
    }
}
```

**Fields:**
- `connector_name`: CLMM connector (meteora/clmm, raydium/clmm)
- `pool_address`: Pool contract address
- `trading_pair`: Format "BASE-QUOTE"
- `base_amount` / `quote_amount`: Token amounts (set one to 0 for single-sided)
- `lower_price` / `upper_price`: Position price bounds
- `side`: 0=both, 1=buy (quote-only), 2=sell (base-only)
- `extra_params`: Connector-specific (Meteora strategyType: 0=Spot, 1=Curve, 2=Bid-Ask)

## Example: Full LP Management Flow

```
# 1. Check prerequisites
./scripts/check_prerequisites.sh

# 2. Find a pool
manage_gateway_clmm(action="list_pools", connector="meteora", search_term="SOL", sort_key="volume")

# 3. Get pool details (note the bin_step for range calculation)
manage_gateway_clmm(action="get_pool_info", connector="meteora", network="solana-mainnet-beta", pool_address="2sfXxxxx")
# Example response shows: bin_step=10, current_price=190
# Max range width = 10 * 69 / 100 = 6.9%
# Use conservative 5% width: lower=185.5, upper=194.5

# 4. Create position
manage_executors(action="create", executor_config={
    "type": "lp_executor",
    "connector_name": "meteora/clmm",
    "pool_address": "2sfXxxxx",
    "trading_pair": "SOL-USDC",
    "base_token": "SOL",
    "quote_token": "USDC",
    "base_amount": 0,
    "quote_amount": 100,
    "lower_price": 185.5,
    "upper_price": 194.5,
    "side": 1
})

# 5. VERIFY position was created (critical step!)
manage_executors(action="get", executor_id="<id>")
# Check custom_info.state:
# - "OPENING" → wait and check again
# - "IN_RANGE" or "OUT_OF_RANGE" → success!
# - "FAILED" → check error, possibly reduce range width

# 6. Monitor position
manage_executors(action="get", executor_id="<id>")

# 7. If out of range, rebalance
./scripts/rebalance_position.sh --id <executor_id>

# 8. When done, close and collect
manage_executors(action="stop", executor_id="<id>", keep_position=false)
```

## Supported Connectors

| Connector | Chain | Status |
|-----------|-------|--------|
| `meteora/clmm` | Solana | Full support |
| `raydium/clmm` | Solana | Full support |
| `orca/clmm` | Solana | Coming soon |

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "Prerequisites not met" | API or MCP not running | Run `hummingbot-deploy` skill |
| "Pool not found" | Invalid pool address | Use list_pools to find valid pools |
| "Insufficient balance" | Not enough tokens | Check wallet balance, reduce amounts |
| "Position not in range" | Price outside bounds | Wait or rebalance |
| "InvalidRealloc" | Position range spans too many bins | Reduce range width (see bin_step limits above) |
| State stuck at "OPENING" | Transaction failed silently | Stop executor and retry with narrower range |

## See Also

- [CLMM Documentation](https://hummingbot.org/gateway/clmm/)
- [Meteora DLMM](https://docs.meteora.ag/dlmm/dlmm-overview)
- [LP Manager Controller](https://hummingbot.org/controllers/lp-manager/)
