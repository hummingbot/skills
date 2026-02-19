# LP Rebalancer Scripts

Utility scripts for analyzing and exporting LP executor data from the lp_rebalancer controller.

## Scripts

- `visualize_executors.py` — Generate interactive HTML dashboard from executor data
- `visualize_lp_positions.py` — Generate interactive HTML dashboard from LP position events (recommended)
- `export_lp_executors.py` — Export executor data to CSV (from Executors table)
- `export_lp_positions.py` — Export raw LP add/remove events to CSV (from RangePositionUpdate table)

---

## visualize_executors.py

A zero-dependency Python script that generates an interactive HTML dashboard from Hummingbot LP executor data. It reads directly from the SQLite database (or from a pre-exported CSV) and outputs a self-contained HTML file you can open in any browser.

### Requirements

- Python 3.10+
- No pip dependencies — uses only the standard library
- A modern browser (the HTML loads React, Recharts, and Babel from CDN)

### Usage

#### From the database (most common)

```bash
python controllers/generic/lp_rebalancer/scripts/visualize_executors.py lp_rebalancer_4
```

This finds the most recent `.sqlite` file in `data/`, queries all executors for the given controller ID, generates the dashboard, and opens it in your default browser.

#### Specify a database

```bash
python controllers/generic/lp_rebalancer/scripts/visualize_executors.py lp_rebalancer_4 --db data/my_bot.sqlite
```

#### From an exported CSV

If you've already run `export_lp_executors.py` or have a CSV from somewhere else:

```bash
python controllers/generic/lp_rebalancer/scripts/visualize_executors.py --csv data/lp_rebalancer_4_20260212_120402.csv
```

When using `--csv`, the `controller_id` argument is optional — it defaults to the CSV filename.

#### Custom output path

```bash
python controllers/generic/lp_rebalancer/scripts/visualize_executors.py lp_rebalancer_4 -o reports/feb12.html
```

#### Skip auto-open

```bash
python controllers/generic/lp_rebalancer/scripts/visualize_executors.py lp_rebalancer_4 --no-open
```

### CLI Reference

```
visualize_executors.py [controller_id] [--db PATH] [--csv PATH] [-o PATH] [--no-open]
```

| Argument | Description |
|---|---|
| `controller_id` | Controller ID to query from the DB. Optional when using `--csv`. |
| `--db PATH` | Path to SQLite database. Defaults to the most recently modified `.sqlite` in `data/`. |
| `--csv PATH` | Load from a CSV file instead of querying the DB. |
| `-o`, `--output PATH` | Output HTML path. Defaults to `data/<controller_id>_dashboard.html`. |
| `--no-open` | Don't auto-open the dashboard in the browser. |

### What the dashboard shows

The generated HTML contains six sections:

**KPI cards** — total PnL, fees earned (with bps calculation), volume, win/loss/zero counts, best/worst single executor, and total rent cost as a percentage of PnL.

**Cumulative PnL & Fees** — area chart showing how PnL and fee accrual progressed over the session. Flat sections correspond to out-of-range periods where the strategy was cycling through zero-PnL executors.

**Price & LP Range** — the current price overlaid with the LP position's upper/lower tick boundaries. Useful for seeing how tightly the range tracks price and where positions went out of range.

**Per-Executor PnL** — bar chart of each non-zero executor's PnL. Filterable by side (quote/buy vs base/sell) using the toggle buttons.

**PnL % Distribution** — histogram of PnL percentage buckets across all non-zero executors. Gives a quick read on whether returns are concentrated or spread out.

**Duration vs PnL** — scatter plot of how long each executor lived vs its PnL. Longer-lived executors with in-range positions tend to show up in the upper-right.

**Side Breakdown** — summary stats split by Side 1 (quote/buy) and Side 2 (base/sell), including PnL, fees, win count, and average duration for each.

---

## visualize_lp_positions.py

Generate an interactive HTML dashboard from LP position events (RangePositionUpdate table). Groups ADD/REMOVE events by position address to show complete position lifecycle.

**Recommended over visualize_executors.py** because LP position events are stored immediately when they occur (no need to wait for shutdown or buffer threshold).

### Requirements

- Python 3.10+
- No pip dependencies — uses only the standard library
- A modern browser (the HTML loads React, Recharts, and Babel from CDN)

### Usage

```bash
# Basic usage (trading pair is required)
python controllers/generic/lp_rebalancer/scripts/visualize_lp_positions.py --pair SOL-USDC

# Filter by connector (optional)
python controllers/generic/lp_rebalancer/scripts/visualize_lp_positions.py --pair SOL-USDC --connector orca/clmm
python controllers/generic/lp_rebalancer/scripts/visualize_lp_positions.py --pair SOL-USDC --connector meteora/clmm

# Last 24 hours only
python controllers/generic/lp_rebalancer/scripts/visualize_lp_positions.py --pair SOL-USDC --hours 24

# Combine filters
python controllers/generic/lp_rebalancer/scripts/visualize_lp_positions.py --pair SOL-USDC --connector orca/clmm --hours 12

# Custom output path
python controllers/generic/lp_rebalancer/scripts/visualize_lp_positions.py --pair SOL-USDC -o reports/positions.html

# Skip auto-open
python controllers/generic/lp_rebalancer/scripts/visualize_lp_positions.py --pair SOL-USDC --no-open
```

### CLI Reference

```
visualize_lp_positions.py --pair PAIR [--db PATH] [--connector NAME] [--hours N] [-o PATH] [--no-open]
```

| Argument | Description |
|---|---|
| `-p`, `--pair PAIR` | **Required.** Trading pair (e.g., `SOL-USDC`). IL calculation requires a single pair. |
| `--db PATH` | Path to SQLite database. Defaults to auto-detecting database with most LP data. |
| `-c`, `--connector NAME` | Filter by connector (e.g., `orca/clmm`, `meteora/clmm`). |
| `-H`, `--hours N` | Lookback period in hours (e.g., `24` for last 24 hours). |
| `-o`, `--output PATH` | Output HTML path. Defaults to `data/lp_positions_<connector>_<pair>_dashboard.html`. |
| `--no-open` | Don't auto-open the dashboard in the browser. |

### What the dashboard shows

**KPI cards** — total PnL, fees earned (with bps calculation), IL (impermanent loss), win/loss counts, best/worst position, and average duration.

**Cumulative PnL & Fees** — area chart showing how PnL and fee accrual progressed over closed positions.

**Price at Open/Close** — the price when positions were opened vs closed, overlaid with the LP range bounds.

**Per-Position PnL** — bar chart of each position's PnL. Click a bar to view position details.

**Duration vs PnL** — scatter plot of how long each position lived vs its PnL.

**IL vs Fees Breakdown** — shows how impermanent loss compares to fees earned.

**Positions tab** — sortable/filterable table of all positions with connector column. When multiple connectors are present, filter buttons allow narrowing by connector. Click any row to see full details including:
- Timing (opened, closed, duration)
- Price bounds and prices at ADD/REMOVE
- ADD liquidity section with deposited amounts and Solscan TX link
- REMOVE liquidity section with withdrawn amounts, fees, and Solscan TX link
- PnL breakdown (IL + fees)

---

## export_lp_executors.py

Export LP executor data from SQLite database to CSV for external analysis (Excel, pandas, etc.).

### Usage

```bash
# Export using most recent database in data/
python controllers/generic/lp_rebalancer/scripts/export_lp_executors.py lp_rebalancer_4

# Specify database path
python controllers/generic/lp_rebalancer/scripts/export_lp_executors.py lp_rebalancer_4 --db data/conf_v2_with_controllers_1.sqlite

# Custom output path
python controllers/generic/lp_rebalancer/scripts/export_lp_executors.py lp_rebalancer_4 --output exports/my_export.csv
```

### CLI Reference

```
export_lp_executors.py <controller_id> [--db PATH] [--output PATH]
```

| Argument | Description |
|---|---|
| `controller_id` | Controller ID to export (e.g., `lp_rebalancer_4`) |
| `--db PATH` | Path to SQLite database. Defaults to most recent `.sqlite` in `data/`. |
| `-o`, `--output PATH` | Output CSV path. Defaults to `data/<controller_id>_<timestamp>.csv`. |

### Exported columns

The CSV includes:

- **Base columns**: id, created_at, type, status, close_type, close_timestamp, net_pnl_pct, net_pnl_quote, cum_fees_quote, filled_amount_quote, is_active, is_trading, controller_id
- **Config columns** (prefixed `cfg_`): connector, trading_pair, pool_address, lower_price, upper_price, base_amount, quote_amount, side, extra_params
- **Custom info columns** (prefixed `ci_`): state, position_address, current_price, lower_price, upper_price, base_amount, quote_amount, base_fee, quote_fee, fees_earned_quote, initial_base_amount, initial_quote_amount, total_value_quote, unrealized_pnl_quote, position_rent, position_rent_refunded, out_of_range_seconds, max_retries_reached

---

## export_lp_positions.py

Export raw LP add/remove events from the `RangePositionUpdate` table. Unlike executor data (which requires shutdown or buffer threshold), these events are stored immediately when they occur.

Auto-detects the database with the most LP position data in `data/` (typically `conf_v2_*.sqlite`).

### Usage

```bash
# Export all LP position events
python controllers/generic/lp_rebalancer/scripts/export_lp_positions.py

# Show summary without exporting
python controllers/generic/lp_rebalancer/scripts/export_lp_positions.py --summary

# Filter by trading pair
python controllers/generic/lp_rebalancer/scripts/export_lp_positions.py --pair SOL-USDC

# Custom output path
python controllers/generic/lp_rebalancer/scripts/export_lp_positions.py -o exports/my_positions.csv
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
- **hb_id**: Hummingbot order ID (e.g., `range-SOL-USDC-...`)
- **timestamp**: Unix timestamp in milliseconds
- **datetime**: Human-readable timestamp
- **tx_hash**: Transaction signature
- **config_file**: Strategy config file path
- **connector**: Connector name (e.g., `orca/clmm`)
- **action**: `ADD` or `REMOVE`
- **trading_pair**: Trading pair (e.g., `SOL-USDC`)
- **position_address**: LP position NFT address
- **lower_price, upper_price**: Position price bounds
- **mid_price**: Current price at time of event
- **base_amount, quote_amount**: Token amounts
- **base_fee, quote_fee**: Fees collected (for REMOVE)
- **position_rent**: SOL rent paid (ADD only)
- **position_rent_refunded**: SOL rent refunded (REMOVE only)
- **trade_fee_json**: Full fee info JSON

### When to use each script

| Script | Data Source | When to Use |
|---|---|---|
| `visualize_lp_positions.py` | `RangePositionUpdate` table | **Recommended** — always available, stores events as they happen |
| `visualize_executors.py` | `Executors` table | After graceful shutdown, or when >100 executors completed |
| `export_lp_positions.py` | `RangePositionUpdate` table | Export raw events for external analysis |
| `export_lp_executors.py` | `Executors` table | Export executor data for external analysis |

---

## Notes

- Both scripts use the same database schema and can be used together — export to CSV first, then visualize from CSV if preferred.
- The HTML dashboard is fully self-contained (data is inlined as JSON), so you can share or archive it.
- No pip dependencies required for either script.
