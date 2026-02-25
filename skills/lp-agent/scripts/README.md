# LP Agent Scripts

Utility scripts for exploring Meteora pools and analyzing LP position data.

## Scripts

**Pool Explorer:**
- `list_meteora_pools.py` — Search and list Meteora DLMM pools
- `get_meteora_pool.py` — Get detailed pool information with liquidity distribution

**Analysis:**
- `export_lp_positions.py` — Export LP position events to CSV
- `visualize_lp_positions.py` — Generate interactive HTML dashboard from LP position events

---

## list_meteora_pools.py

Search and list Meteora DLMM pools by name, token, or address. Shows token mint addresses to identify correct tokens.

### Requirements

- Python 3.10+
- No pip dependencies — uses only the standard library

### Usage

```bash
# Top pools by 24h volume
python scripts/list_meteora_pools.py

# Search by token symbol
python scripts/list_meteora_pools.py --query SOL
python scripts/list_meteora_pools.py --query PERCOLATOR

# Sort by different metrics
python scripts/list_meteora_pools.py --query SOL --sort tvl
python scripts/list_meteora_pools.py --query SOL --sort apr
python scripts/list_meteora_pools.py --query SOL --sort fees

# Output as JSON
python scripts/list_meteora_pools.py --query SOL --json
```

### CLI Reference

```
list_meteora_pools.py [-q QUERY] [-s SORT] [--order ORDER] [-n LIMIT] [-p PAGE] [--json]
```

| Argument | Description |
|---|---|
| `-q`, `--query` | Search by pool name, token symbol, or address |
| `-s`, `--sort` | Sort by: `volume`, `tvl`, `fees`, `apr`, `apy` (default: `volume`) |
| `--order` | Sort order: `asc` or `desc` (default: `desc`) |
| `-n`, `--limit` | Number of results (default: 10, max: 1000) |
| `-p`, `--page` | Page number (default: 1) |
| `--json` | Output as JSON |

### Output

Outputs a markdown table with token mint addresses to identify correct tokens:

| # | Pool | Pool Address | Base (mint) | Quote (mint) | TVL | Vol 24h | Fees 24h | APR | Fee | Bin |
|---|------|--------------|-------------|--------------|-----|---------|----------|-----|-----|-----|
| 1 | Percolator-SOL | `ATrBUW..sPMSms` | Percolator (`8PzF..pump`) | SOL (`So11..1112`) | $8.9K | $15.5K | $348 | 3.9% | 2.00% | 100 |

---

## get_meteora_pool.py

Get detailed information about a specific Meteora DLMM pool. Fetches from both Meteora API (historical data) and Gateway (real-time price, liquidity distribution).

### Requirements

- Python 3.10+
- No pip dependencies — uses only the standard library
- Optional: Gateway running for real-time price and liquidity distribution chart

### Usage

```bash
# Get pool details (includes liquidity chart if Gateway is running)
python scripts/get_meteora_pool.py <pool_address>

# Skip Gateway API (faster, no liquidity distribution)
python scripts/get_meteora_pool.py <pool_address> --no-gateway

# Output as JSON
python scripts/get_meteora_pool.py <pool_address> --json
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_HOST` | `localhost` | Gateway API host |
| `GATEWAY_PORT` | `15888` | Gateway API port |

### Output Sections

1. **Pool Summary** - Current price, TVL, volume, fees, APR/APY, fee tier, bin step
2. **Token Info** - Base/quote token details (symbol, mint, price, decimals, market cap)
3. **Reserves** - Token amounts and USD values
4. **Volume & Fees by Time Window** - 30m, 1h, 4h, 12h, 24h metrics with Fee/TVL ratio
5. **Cumulative Metrics** - All-time volume and fees
6. **Real-Time Price** - Current price from Gateway (with subscript notation for small prices)
7. **Liquidity Distribution** - Vertical ASCII chart showing base/quote liquidity around current price
8. **Active Bin Info** - Active bin ID, min/max bin IDs, dynamic fee

### Liquidity Distribution Chart

The chart shows liquidity distribution like the Meteora UI:

```
Liquidity Distribution
▓ Percolator  ░ SOL  │ Current Price: 0.0₄169 SOL/Percolator

░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
──────────────────────────────┴─────────────────────────────
0.0₄125                    0.0₄169                   0.0₄225
```

- `▓` Base token (above current price = sell liquidity)
- `░` Quote token (below current price = buy liquidity)
- `│` Current price line
- Subscript notation: `0.0₄169` = 0.0000169

---

## export_lp_positions.py

Export LP position events from the `RangePositionUpdate` table to CSV. Events are stored immediately when they occur on-chain.

### Usage

```bash
# Export all LP position events (auto-detects database)
python scripts/export_lp_positions.py

# Show summary without exporting
python scripts/export_lp_positions.py --summary

# Filter by trading pair
python scripts/export_lp_positions.py --pair SOL-USDC

# Specify database
python scripts/export_lp_positions.py --db data/my_bot.sqlite

# Custom output path
python scripts/export_lp_positions.py -o exports/my_positions.csv
```

### CLI Reference

```
export_lp_positions.py [--db PATH] [--output PATH] [--pair PAIR] [--summary]
```

| Argument | Description |
|---|---|
| `--db PATH` | Path to SQLite database. Defaults to auto-detecting database with most LP data. |
| `-o`, `--output PATH` | Output CSV path. Defaults to `data/lp_positions_<timestamp>.csv`. |
| `-p`, `--pair PAIR` | Filter by trading pair (e.g., `SOL-USDC`). |
| `-s`, `--summary` | Show summary only, don't export. |

### Exported columns

- **id**: Database row ID
- **hb_id**: Hummingbot order ID
- **timestamp**: Unix timestamp in milliseconds
- **datetime**: Human-readable timestamp
- **tx_hash**: Transaction signature
- **connector**: Connector name (e.g., `meteora/clmm`)
- **action**: `ADD` or `REMOVE`
- **trading_pair**: Trading pair (e.g., `SOL-USDC`)
- **position_address**: LP position NFT address
- **lower_price, upper_price**: Position price bounds
- **mid_price**: Current price at time of event
- **base_amount, quote_amount**: Token amounts
- **base_fee, quote_fee**: Fees collected (for REMOVE)
- **position_rent**: SOL rent paid (ADD only)
- **position_rent_refunded**: SOL rent refunded (REMOVE only)

---

## visualize_lp_positions.py

Generate an interactive HTML dashboard from LP position events. Groups ADD/REMOVE events by position address to show complete position lifecycle with PnL, fees, and impermanent loss.

### Requirements

- Python 3.10+
- No pip dependencies — uses only the standard library
- A modern browser (the HTML loads React, Recharts, and Babel from CDN)

### Usage

```bash
# Basic usage (trading pair is required)
python scripts/visualize_lp_positions.py --pair SOL-USDC

# Filter by connector
python scripts/visualize_lp_positions.py --pair SOL-USDC --connector meteora/clmm

# Last 24 hours only
python scripts/visualize_lp_positions.py --pair SOL-USDC --hours 24

# Specify database
python scripts/visualize_lp_positions.py --db data/my_bot.sqlite --pair SOL-USDC

# Custom output path
python scripts/visualize_lp_positions.py --pair SOL-USDC -o reports/positions.html

# Skip auto-open
python scripts/visualize_lp_positions.py --pair SOL-USDC --no-open
```

### CLI Reference

```
visualize_lp_positions.py --pair PAIR [--db PATH] [--connector NAME] [--hours N] [-o PATH] [--no-open]
```

| Argument | Description |
|---|---|
| `-p`, `--pair PAIR` | **Required.** Trading pair (e.g., `SOL-USDC`). |
| `--db PATH` | Path to SQLite database. Defaults to auto-detecting database with most LP data. |
| `-c`, `--connector NAME` | Filter by connector (e.g., `meteora/clmm`). |
| `-H`, `--hours N` | Lookback period in hours (e.g., `24` for last 24 hours). |
| `-o`, `--output PATH` | Output HTML path. |
| `--no-open` | Don't auto-open the dashboard in the browser. |

### Dashboard Features

**KPI cards** — total PnL, fees earned (with bps calculation), IL (impermanent loss), win/loss counts, best/worst position, average duration.

**Cumulative PnL & Fees** — area chart showing PnL and fee accrual over closed positions.

**Price at Open/Close** — price when positions were opened vs closed, overlaid with LP range bounds.

**Per-Position PnL** — bar chart of each position's PnL. Click a bar to view details.

**Duration vs PnL** — scatter plot of position duration vs PnL.

**IL vs Fees Breakdown** — how impermanent loss compares to fees earned.

**Positions table** — sortable/filterable table with:
- Timing (opened, closed, duration)
- Price bounds and prices at ADD/REMOVE
- ADD liquidity with deposited amounts and Solscan TX link
- REMOVE liquidity with withdrawn amounts, fees, and Solscan TX link
- PnL breakdown (IL + fees)

---

## Notes

- All scripts use only the Python standard library (no pip install required)
- The HTML dashboard is fully self-contained (data inlined as JSON), shareable and archivable
- LP position events are stored immediately on-chain, so analysis works for both running and stopped bots
