---
name: perp-dex-costs
description: Before a perpetual futures trade on a decentralised exchange, check which perp DEX is cheapest right now for your size (taker fees on both legs + slippage on the live order book), compare funding and order book depth, find the best delta-neutral funding pair net of costs, and plan large orders or airdrop farming, across 25+ perp DEXs including Hyperliquid and dYdX. Nine tools free, no API key; five paid per call in USDC on Base (x402).
metadata:
  author: dineroenlamesa
---

# perp-dex-costs

Pre-trade cost check for perpetual futures on decentralised exchanges. Use it **before** you pick a connector, size an order or set up a funding trade, so the bot opens where the round trip costs least and the funding works in its favour.

Data comes from the Dinero en la Mesa API (dineroenlamesa.com/agents): taker fees verified in each venue's docs plus slippage walked on the live order book, read in real time; funding normalised to 8 hours. Every figure carries the time it was read. No API key, no account.

## Prerequisites

Python 3 (standard library only). No Hummingbot API is needed to read the data; use it together with the `hummingbot` skill to act on it. When a venue has a Hummingbot connector, the output names it (`hyperliquid_perpetual`, `dydx_v4_perpetual`).

## Workflow

### Step 1: Cheapest venue for the trade

```bash
python scripts/perp_dex_costs.py best --pair BTC --size 25000
```

The venue with the lowest round-trip cost (open and close at market) for that size, its cost in USD and bps, and the runner-up. `costs` gives every venue ranked, with fees and slippage split and the venues that give no figure and why:

```bash
python scripts/perp_dex_costs.py costs --pair ETH --size 100000 --limit 10
```

### Step 2: Can the book take the order?

```bash
python scripts/perp_dex_costs.py depth --pair SOL
```

Spread in bps and the USD resting within 0.5% and 1% of mid, on each side, for every live book.

### Step 3: Funding before holding a position

```bash
python scripts/perp_dex_costs.py funding --pair SOL
python scripts/perp_dex_costs.py delta --pair BTC --size 10000 --days 7
```

`funding`: rate per venue, normalised to 8 hours and annualised, and who pays. `delta`: the best long/short venue couple to collect the funding gap on one pair, net of opening and closing both legs at market (a reading up to 15 minutes old; rates change every hour, so it is a snapshot, not a forecast).

### Step 4: Large orders and farming (paid)

```bash
python scripts/perp_dex_costs.py plan --pair BTC --size 5000000 --side buy
python scripts/perp_dex_costs.py scanner --size 10000 --days 7
python scripts/perp_dex_costs.py points
python scripts/perp_dex_costs.py route --budget 500 --size 10000
```

| Command | What it gives | Price |
|---------|---------------|-------|
| `plan` | How to split one side of a large order across venues so each book only absorbs what it can, leg by leg, against doing it all on the single cheapest venue | 1 USDC, charged only if the split saves 20 USD or more |
| `scanner` | Every pair and every venue couple, read every minute, net of opening and closing both legs, with how long each gap has lasted | 0.10 USDC |
| `points` | Share of this week's points pool that 1M USD of volume would earn on each venue with a published pool, and what that volume costs in fees | 0.05 USDC |
| `route` | What your weekly farming budget buys on each venue: volume at your order size on the live book, and your share of the pool | 0.50 USDC |
| `alerts` | A signed webhook the minute a net funding gap or a trading cost crosses your threshold, for 30 days, up to 3 pairs | 29 USDC |

Without payment the server answers HTTP 402 with what the call would give right now (for example how much a split saves) and its price, and the script prints it. Payment is USDC on Base through x402: no account and no key, from any x402-capable client or from an agent connected to the MCP server `https://dineroenlamesa.com/agents/mcp`. You are not charged when the data is stale or the result is empty.

### Other free commands

| Command | What it gives |
|---------|---------------|
| `venues` | The perp DEXs covered, order book type, entry-tier maker/taker fees verified in each venue's docs and the date they were checked |
| `airdrops` | Open airdrop and points campaigns, next hard date first |
| `changes --days 7` | What changed in those campaigns (dates, rules, rewards) |
| `signup --venue hyperliquid` | Account-opening link for one venue |

## Options

| Option | Meaning |
|--------|---------|
| `--pair` | Base asset of the perpetual: BTC, ETH, SOL, XRP, BNB, DOGE, HYPE, SUI, LINK, AAVE, ENA, LTC |
| `--size` | Order size in USD (notional); per leg for `delta` and `scanner`; your trade size for `route` |
| `--volume` | Your 30-day volume in USD, to price your fee tier (`best`, `costs`, `plan`) |
| `--days` | Holding days (`delta`, `scanner`) or look-back (`changes`) |
| `--side` | `buy` or `sell` (`plan`) |
| `--budget` | Weekly farming budget in USD (`route`) |
| `--venue` | Venue id from `venues` (`signup`) |
| `--limit` | Rows to print (default 10) |
| `--json` | Print the raw JSON instead of the table |

Set `DLM_API` to point the script at another base URL (default `https://dineroenlamesa.com/agents/api`).

## Notes

- Costs are for market orders (taker). Limit orders that fill as maker usually cost less.
- Each venue in the output carries its account-opening link and, when there is one, what you get by opening the account that way (for example a fee rebate or a points boost). These are Dinero en la Mesa referral links: they never change the ranking, which is by cost only.
- Terms of use: https://dineroenlamesa.com/agents/terms/
