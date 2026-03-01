---
name: find-arbitrage-opps
description: Find arbitrage opportunities across exchanges by comparing prices for fungible token pairs like BTC/WBTC and USDT/USDC.
metadata:
  author: hummingbot
---

# find-arbitrage-opps

Find arbitrage opportunities across all Hummingbot-connected exchanges by comparing prices for a trading pair, accounting for fungible tokens (e.g., BTC = WBTC, USDT = USDC).

## Prerequisites

Hummingbot API must be running with exchange connectors configured:

```bash
bash <(curl -s https://raw.githubusercontent.com/hummingbot/skills/main/skills/lp-agent/scripts/check_prerequisites.sh)
```

## DEX Support

By default the script queries CEX connectors via the Hummingbot API. Add `--dex` to also fetch prices from:

| DEX | Chain | Default Network |
|-----|-------|-----------------|
| **Jupiter** | Solana | `mainnet-beta` |
| **Uniswap** | Ethereum | `mainnet` |

DEX prices are fetched directly via the Hummingbot Gateway. Make sure Gateway is running on `http://localhost:15888` (or set `GATEWAY_URL`).

> ⚠️ **BTC markets** are only available to Australian residents on some exchanges. A warning is printed automatically when BTC/WBTC/cbBTC is included in the search.

## Workflow

### Step 1: Define Token Mappings

User specifies the base and quote tokens, including fungible equivalents:

- **Base tokens**: BTC, WBTC, cbBTC (all represent Bitcoin)
- **Quote tokens**: USDT, USDC, USD (all represent USD)

### Step 2: Find Arbitrage Opportunities

```bash
# Basic - CEX only
python scripts/find_arb_opps.py --base BTC --quote USDT

# Include fungible tokens
python scripts/find_arb_opps.py --base BTC,WBTC --quote USDT,USDC

# Include DEX prices (Jupiter + Uniswap via Gateway)
python scripts/find_arb_opps.py --base SOL --quote USDC --dex
python scripts/find_arb_opps.py --base ETH,WETH --quote USDT,USDC --dex

# Minimum spread filter
python scripts/find_arb_opps.py --base SOL --quote USDC --dex --min-spread 0.1

# Filter to specific CEX connectors
python scripts/find_arb_opps.py --base BTC --quote USDT --connectors binance,kraken,coinbase
```

### Step 3: Analyze Results

The script outputs:
- Prices from each CEX and DEX source
- Best bid/ask across all sources
- Arbitrage spread (buy low, sell high)
- Recommended pairs for arbitrage

## Script Options

```bash
python scripts/find_arb_opps.py --help
```

| Option | Description |
|--------|-------------|
| `--base` | Base token(s), comma-separated (e.g., BTC,WBTC) |
| `--quote` | Quote token(s), comma-separated (e.g., USDT,USDC) |
| `--connectors` | Filter to specific CEX connectors (optional) |
| `--dex` | Include DEX prices via Gateway (Jupiter + Uniswap) |
| `--min-spread` | Minimum spread % to show (default: 0.0) |
| `--json` | Output as JSON |

## Output Example

```
============================================================
  SOL / USDC Arbitrage Scanner
  DEX: Jupiter (Solana mainnet-beta), Uniswap (Ethereum mainnet)
============================================================

  Lowest:  binance                   $132.4500
  Highest: jupiter (DEX)             $132.8900
  Spread:  0.332% ($0.4400)
  Sources: 5 prices from 5 sources

  Top Arbitrage Opportunities:
  --------------------------------------------------------
  1. Buy  binance                   @ $132.4500
     Sell jupiter (DEX)             @ $132.8900
     Profit: 0.332% ($0.4400)
```

## Environment Variables

```bash
export HUMMINGBOT_API_URL=http://localhost:8000
export API_USER=admin
export API_PASS=admin
export GATEWAY_URL=http://localhost:15888   # for DEX prices
```

Scripts check for `.env` in: `./hummingbot-api/.env` → `~/.hummingbot/.env` → `.env`

## Requirements

- Hummingbot API running (for CEX prices)
- Gateway running (for DEX prices with `--dex` flag)
- Exchange connectors configured with API keys
