#!/usr/bin/env python3
"""
Export LP executor history from the Hummingbot REST API to CSV.

Targets `lp_executor` type executors deployed via the API directly.
No SQLite database required. All data comes from POST /executors/search.

Usage:
    python scripts/export_lp_executor.py                                    # export all LP executors
    python scripts/export_lp_executor.py --pair PERCOLATOR-SOL              # filter by pair
    python scripts/export_lp_executor.py --pair SOL-USDC --status TERMINATED
    python scripts/export_lp_executor.py --summary                          # summary stats only
    python scripts/export_lp_executor.py --output exports/lp_executors.csv  # custom output path

CSV columns exported:
    id, account_name, controller_id, connector_name, trading_pair, status,
    close_type, is_active, is_trading, error_count, created_at, closed_at,
    close_timestamp, duration_seconds, net_pnl_quote, net_pnl_pct,
    cum_fees_quote, filled_amount_quote,
    [config] pool_address, lower_price, upper_price, base_amount, quote_amount,
    side, position_offset_pct, auto_close_above_range_seconds,
    auto_close_below_range_seconds, keep_position,
    [custom_info] state, position_address, current_price, lower_price_actual,
    upper_price_actual, base_amount_current, quote_amount_current,
    base_fee, quote_fee, fees_earned_quote, total_value_quote,
    unrealized_pnl_quote, position_rent, position_rent_refunded, tx_fee,
    out_of_range_seconds, max_retries_reached, initial_base_amount,
    initial_quote_amount
"""

import argparse
import base64
import csv
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Environment / Auth
# ---------------------------------------------------------------------------

def load_env():
    """Load .env files in priority order: ~/mcp/.env, ~/.hummingbot/.env, .env"""
    env_files = [
        Path.home() / "mcp" / ".env",
        Path.home() / ".hummingbot" / ".env",
        Path(".env"),
    ]
    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key and key not in os.environ:
                                os.environ[key] = value
            except Exception:
                pass


def get_api_config():
    load_env()
    base_url = os.environ.get("HUMMINGBOT_API_URL", "http://localhost:8000").rstrip("/")
    username = os.environ.get("HUMMINGBOT_USERNAME", "admin")
    password = os.environ.get("HUMMINGBOT_PASSWORD", "admin")
    return base_url, username, password


def make_auth_header(username, password):
    creds = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {creds}"


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_post(url, payload, auth_header, timeout=30):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": auth_header,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error: {e.reason}") from e


def api_get(url, auth_header, timeout=30):
    req = urllib.request.Request(
        url,
        headers={"Authorization": auth_header},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error: {e.reason}") from e


# ---------------------------------------------------------------------------
# Fetch LP executors
# ---------------------------------------------------------------------------

def fetch_lp_executors(base_url, auth_header, trading_pair=None, status=None):
    """
    Fetch lp_executor records via POST /executors/search.
    The API returns {"data": [...]} (list may be mixed types).
    We filter client-side to lp_executor only.
    """
    url = f"{base_url}/executors/search"
    payload = {"type": "lp_executor"}
    if trading_pair:
        payload["trading_pair"] = trading_pair
    if status:
        payload["status"] = status

    try:
        result = api_post(url, payload, auth_header)
    except RuntimeError as e:
        print(f"Error fetching executors: {e}", file=sys.stderr)
        sys.exit(1)

    # API returns {"data": [...]} or a raw list
    items = []
    if isinstance(result, list):
        items = result
    elif isinstance(result, dict):
        for key in ("data", "executors", "items", "results"):
            if key in result and isinstance(result[key], list):
                items = result[key]
                break

    # Filter to lp_executor only (defensive in case API returns mixed types)
    return [
        ex for ex in items
        if ex.get("type") == "lp_executor"
        or ex.get("executor_type") == "lp_executor"
    ]


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def _f(v, default=None):
    """Safe float."""
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _s(v, default=""):
    return str(v) if v is not None else default


def _b(v):
    """Safe bool → string."""
    if v is None:
        return ""
    return "true" if v else "false"


def parse_ts(iso_str):
    """Parse ISO datetime string → unix float, or None."""
    if not iso_str:
        return None
    try:
        clean = str(iso_str).replace("+00:00", "").replace("Z", "")
        if "." in clean:
            parts = clean.split(".")
            clean = parts[0] + "." + parts[1][:6]
        dt = datetime.fromisoformat(clean)
        import calendar
        return calendar.timegm(dt.timetuple()) + dt.microsecond / 1e6
    except Exception:
        return None


def executor_to_row(ex):
    """
    Flatten a single lp_executor API response dict into a CSV row dict.

    LP executor API shape:
      Top-level: id, timestamp, type, status, net_pnl_pct, net_pnl_quote,
                 cum_fees_quote, filled_amount_quote, is_active, is_trading,
                 close_timestamp, close_type, controller_id, executor_id,
                 executor_type, account_name, created_at, connector_name,
                 trading_pair, error_count, last_error, closed_at
      config:    id, type, timestamp, controller_id, connector_name,
                 trading_pair, pool_address, lower_price, upper_price,
                 base_amount, quote_amount, side, position_offset_pct,
                 auto_close_above_range_seconds, auto_close_below_range_seconds,
                 extra_params, keep_position
      custom_info: side, state, position_address, current_price, lower_price,
                   upper_price, base_amount, quote_amount, base_fee, quote_fee,
                   fees_earned_quote, total_value_quote, unrealized_pnl_quote,
                   position_rent, position_rent_refunded, tx_fee,
                   out_of_range_seconds, max_retries_reached,
                   initial_base_amount, initial_quote_amount
    """
    cfg = ex.get("config") or {}
    ci = ex.get("custom_info") or {}

    # Primary ID: prefer "executor_id" top-level (alias for "id")
    eid = _s(ex.get("executor_id") or ex.get("id"))
    created_at_str = _s(ex.get("created_at"))
    created_at_ts = parse_ts(created_at_str)
    close_ts = _f(ex.get("close_timestamp"))

    # closed_at may be an ISO string in some API versions
    closed_at_str = _s(ex.get("closed_at"))
    if not closed_at_str and close_ts is not None:
        closed_at_str = datetime.utcfromtimestamp(close_ts).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")

    # Duration
    duration = None
    close_ts_for_duration = close_ts or parse_ts(closed_at_str)
    if created_at_ts is not None and close_ts_for_duration and close_ts_for_duration > created_at_ts:
        duration = round(close_ts_for_duration - created_at_ts, 1)

    return {
        # Identity
        "id": eid,
        "account_name": _s(ex.get("account_name")),
        "controller_id": _s(ex.get("controller_id")),
        "connector_name": _s(ex.get("connector_name")),
        "trading_pair": _s(ex.get("trading_pair")),
        # State
        "status": _s(ex.get("status")),
        "close_type": _s(ex.get("close_type")),
        "is_active": _b(ex.get("is_active")),
        "is_trading": _b(ex.get("is_trading")),
        "error_count": ex.get("error_count", 0),
        # Timing
        "created_at": created_at_str,
        "closed_at": closed_at_str,
        "close_timestamp": close_ts,
        "duration_seconds": duration,
        # PnL (top-level)
        "net_pnl_quote": _f(ex.get("net_pnl_quote")),
        "net_pnl_pct": _f(ex.get("net_pnl_pct")),
        "cum_fees_quote": _f(ex.get("cum_fees_quote")),
        "filled_amount_quote": _f(ex.get("filled_amount_quote")),
        # Config fields (deployment parameters)
        "pool_address": _s(cfg.get("pool_address")),
        "lower_price": _f(cfg.get("lower_price")),
        "upper_price": _f(cfg.get("upper_price")),
        "base_amount_config": _f(cfg.get("base_amount")),
        "quote_amount_config": _f(cfg.get("quote_amount")),
        "side": cfg.get("side"),
        "position_offset_pct": _f(cfg.get("position_offset_pct")),
        "auto_close_above_range_seconds": cfg.get("auto_close_above_range_seconds"),
        "auto_close_below_range_seconds": cfg.get("auto_close_below_range_seconds"),
        "keep_position": _b(cfg.get("keep_position")),
        # custom_info fields (live position data)
        "state": _s(ci.get("state")),
        "position_address": _s(ci.get("position_address")),
        "current_price": _f(ci.get("current_price")),
        "lower_price_actual": _f(ci.get("lower_price")),
        "upper_price_actual": _f(ci.get("upper_price")),
        "base_amount_current": _f(ci.get("base_amount")),
        "quote_amount_current": _f(ci.get("quote_amount")),
        "base_fee": _f(ci.get("base_fee")),
        "quote_fee": _f(ci.get("quote_fee")),
        "fees_earned_quote": _f(ci.get("fees_earned_quote")),
        "total_value_quote": _f(ci.get("total_value_quote")),
        "unrealized_pnl_quote": _f(ci.get("unrealized_pnl_quote")),
        "position_rent": _f(ci.get("position_rent")),
        "position_rent_refunded": _f(ci.get("position_rent_refunded")),
        "tx_fee": _f(ci.get("tx_fee")),
        "out_of_range_seconds": _f(ci.get("out_of_range_seconds")),
        "max_retries_reached": _b(ci.get("max_retries_reached")),
        "initial_base_amount": _f(ci.get("initial_base_amount")),
        "initial_quote_amount": _f(ci.get("initial_quote_amount")),
    }


CSV_COLUMNS = [
    # Identity
    "id", "account_name", "controller_id", "connector_name", "trading_pair",
    # State
    "status", "close_type", "is_active", "is_trading", "error_count",
    # Timing
    "created_at", "closed_at", "close_timestamp", "duration_seconds",
    # PnL
    "net_pnl_quote", "net_pnl_pct", "cum_fees_quote", "filled_amount_quote",
    # Config (deployment parameters)
    "pool_address", "lower_price", "upper_price",
    "base_amount_config", "quote_amount_config", "side",
    "position_offset_pct",
    "auto_close_above_range_seconds", "auto_close_below_range_seconds",
    "keep_position",
    # custom_info (live / final position data)
    "state", "position_address", "current_price",
    "lower_price_actual", "upper_price_actual",
    "base_amount_current", "quote_amount_current",
    "base_fee", "quote_fee", "fees_earned_quote",
    "total_value_quote", "unrealized_pnl_quote",
    "position_rent", "position_rent_refunded", "tx_fee",
    "out_of_range_seconds", "max_retries_reached",
    "initial_base_amount", "initial_quote_amount",
]


# ---------------------------------------------------------------------------
# Summary display
# ---------------------------------------------------------------------------

def fmt_duration(seconds):
    if seconds is None or seconds <= 0:
        return "—"
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    return f"{s // 3600}h {(s % 3600) // 60}m"


def show_summary(executors):
    print("\nLP Executor Summary")
    print("=" * 60)
    if not executors:
        print("No LP executors found.")
        return

    total = len(executors)
    by_status = {}
    by_pair = {}
    total_pnl = 0.0
    total_fees = 0.0
    wins = losses = 0

    for ex in executors:
        row = executor_to_row(ex)
        status = row["status"] or "UNKNOWN"
        pair = row["trading_pair"] or "UNKNOWN"
        pnl = row["net_pnl_quote"] or 0.0
        fees = row["fees_earned_quote"] or 0.0

        by_status[status] = by_status.get(status, 0) + 1
        by_pair[pair] = by_pair.get(pair, 0) + 1
        total_pnl += pnl
        total_fees += fees
        if pnl >= 0:
            wins += 1
        else:
            losses += 1

    print(f"Total LP executors : {total}")
    print(f"Total PnL          : {total_pnl:.6f} (quote)")
    print(f"Total Fees Earned  : {total_fees:.6f} (quote)")
    print(f"Win / Loss         : {wins} / {losses}")
    print("\nBy Status:")
    for k, v in sorted(by_status.items()):
        print(f"  {k}: {v}")
    print("\nBy Trading Pair:")
    for k, v in sorted(by_pair.items()):
        print(f"  {k}: {v}")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_to_csv(executors, output_path):
    if not executors:
        return 0
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    rows = [executor_to_row(ex) for ex in executors]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Export LP executor history from Hummingbot API to CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--pair", "-p", help="Filter by trading pair (e.g., SOL-USDC)")
    parser.add_argument("--status", "-s", help="Filter by status (e.g., TERMINATED, RUNNING)")
    parser.add_argument("--summary", action="store_true", help="Show summary stats only (no CSV)")
    parser.add_argument("--output", "-o", help="Output CSV path (default: data/lp_executors_<ts>.csv)")
    args = parser.parse_args()

    base_url, username, password = get_api_config()
    auth_header = make_auth_header(username, password)

    print(f"Fetching LP executors from {base_url} ...")
    executors = fetch_lp_executors(base_url, auth_header, args.pair, args.status)

    if not executors:
        filters = []
        if args.pair:
            filters.append(f"pair={args.pair}")
        if args.status:
            filters.append(f"status={args.status}")
        suffix = f" ({', '.join(filters)})" if filters else ""
        print(f"No LP executors found{suffix}.")
        return 0

    print(f"Found {len(executors)} LP executor(s).")

    if args.summary:
        show_summary(executors)
        return 0

    output_path = args.output
    if not output_path:
        os.makedirs("data", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{args.pair.replace('-', '_')}" if args.pair else ""
        output_path = f"data/lp_executors{suffix}_{ts}.csv"

    count = export_to_csv(executors, output_path)
    print(f"Exported {count} LP executor(s) to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
