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

```bash
# List popular pools on Meteora
./scripts/list_pools.sh --connector meteora

# Search for specific pools
./scripts/list_pools.sh --connector meteora --search SOL-USDC

# Get detailed pool info
./scripts/get_pool_info.sh --connector meteora --network solana-mainnet-beta --pool <pool_address>
```

### 2. Create LP Position

```bash
# Create position with both tokens (double-sided)
./scripts/create_lp_position.sh \
  --connector meteora \
  --network solana-mainnet-beta \
  --pool <pool_address> \
  --pair SOL-USDC \
  --base-amount 1.0 \
  --quote-amount 100 \
  --width 5.0

# Create position with quote only (buy base as price drops)
./scripts/create_lp_position.sh \
  --connector meteora \
  --network solana-mainnet-beta \
  --pool <pool_address> \
  --pair SOL-USDC \
  --quote-amount 100 \
  --width 5.0
```

### 3. Monitor Positions

```bash
# List all LP positions
./scripts/list_lp_positions.sh

# Get specific position details
./scripts/get_lp_position.sh --id <executor_id>
```

### 4. Manage Positions

```bash
# Collect fees without closing
./scripts/collect_fees.sh --id <executor_id>

# Close position and collect all
./scripts/close_lp_position.sh --id <executor_id>

# Rebalance (close and reopen centered on current price)
./scripts/rebalance_position.sh --id <executor_id>
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

### Single-Sided: Quote Only

Position entire range BELOW current price. You're buying base as price drops.

```
     Lower          Upper    Current
       |---------------|--------|
       |<---- Buy zone ---->|
```

- Best for: Accumulating base token at lower prices
- Risk: Price may never enter your range

### Single-Sided: Base Only

Position entire range ABOVE current price. You're selling base as price rises.

```
                   Current    Lower          Upper
                      |--------|---------------|
                               |<-- Sell zone -->|
```

- Best for: Taking profit as price rises
- Risk: Price may never enter your range

## Rebalancing Strategy

When price moves out of your position range:

1. **Price dropped below range** (you're now 100% base):
   - Rebalance creates a BASE-ONLY position above current price
   - You'll sell base as price recovers

2. **Price rose above range** (you're now 100% quote):
   - Rebalance creates a QUOTE-ONLY position below current price
   - You'll buy base if price drops back

```bash
# Manual rebalance
./scripts/rebalance_position.sh --id <executor_id>

# Auto-rebalance (monitors and rebalances when out of range for N seconds)
./scripts/auto_rebalance.sh --id <executor_id> --delay 60
```

## Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--connector` | CLMM connector (meteora, raydium) | meteora |
| `--network` | Network (solana-mainnet-beta) | solana-mainnet-beta |
| `--pool` | Pool address | Required |
| `--pair` | Trading pair (e.g., SOL-USDC) | Required |
| `--base-amount` | Base token amount | 0 |
| `--quote-amount` | Quote token amount | 0 |
| `--width` | Position width as % of current price | 5.0 |
| `--lower-price` | Explicit lower bound (overrides width) | - |
| `--upper-price` | Explicit upper bound (overrides width) | - |

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/gateway/clmm/pools` | GET | List available pools |
| `/gateway/clmm/pool-info` | GET | Get pool details |
| `/gateway/clmm/positions` | GET | Get positions for a pool |
| `/executors/` | POST | Create LP executor |
| `/executors/search` | POST | List executors |
| `/executors/{id}` | GET | Get executor details |
| `/executors/{id}/stop` | POST | Stop executor |

## Supported Connectors

| Connector | Chain | Status |
|-----------|-------|--------|
| `meteora` | Solana | Full support |
| `raydium` | Solana | Full support |
| `orca` | Solana | Coming soon |
| `uniswap_v3` | Ethereum | Coming soon |

## Example: Full LP Management Flow

```bash
# 1. Check prerequisites
./scripts/check_prerequisites.sh

# 2. Find a good pool
./scripts/list_pools.sh --connector meteora --search SOL --sort volume

# 3. Check pool details and current price
./scripts/get_pool_info.sh --connector meteora --network solana-mainnet-beta \
  --pool 2sfxxxxxxxxxxxx

# 4. Create position (5% width around current price)
./scripts/create_lp_position.sh \
  --connector meteora \
  --network solana-mainnet-beta \
  --pool 2sfxxxxxxxxxxxx \
  --pair SOL-USDC \
  --quote-amount 100 \
  --width 5.0

# 5. Monitor position
./scripts/get_lp_position.sh --id <executor_id>

# 6. If out of range, rebalance
./scripts/rebalance_position.sh --id <executor_id>

# 7. When done, close and collect
./scripts/close_lp_position.sh --id <executor_id>
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "Prerequisites not met" | API or MCP not running | Run `hummingbot-deploy` skill |
| "Pool not found" | Invalid pool address | Use `list_pools.sh` to find valid pools |
| "Insufficient balance" | Not enough tokens | Check wallet balance, reduce amounts |
| "Position not in range" | Price outside bounds | Wait or rebalance |
| "Failed to open position" | Transaction failed | Check wallet balance, try again |

## See Also

- [CLMM Documentation](https://hummingbot.org/gateway/clmm/)
- [Meteora DLMM](https://docs.meteora.ag/dlmm/dlmm-overview)
- [LP Manager Controller](https://hummingbot.org/controllers/lp-manager/)
