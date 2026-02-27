#!/usr/bin/env python3
"""
Export executor history from the Hummingbot REST API to CSV.

Works directly from the API — no SQLite database required. Useful for executors
deployed via the API rather than bot containers (which don't always produce SQLite records).

Usage:
    python scripts/export_executor.py                                    # export all executors
    python scripts/export_executor.py --pair SOL-USDC                   # filter by pair
    python scripts/export_executor.py --connector meteora/clmm          # filter by connector
    python scripts/export_executor.py --status TERMINATED               # filter by status
    python scripts/export_executor.py --summary                         # summary stats only
    python scripts/export_executor.py --output exports/executors.csv    # custom output path

Examples:
    python scripts/export_executor.py --pair SOL-USDC --status TERMINATED
    python scripts/export_executor.py --summary
    python scripts/export_executor.py --pair SOL-USDC --output data/sol_usdc.csv
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
    """Load environment variables from .env files. Priority: ~/mcp/.env, ~/.hummingbot/.env, .env"""
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
    """Get API base URL and auth credentials from environment."""
    load_env()
    base_url = os.environ.get("HUMMINGBOT_API_URL", "http://localhost:8000").rstrip("/")
    username = os.environ.get("HUMMINGBOT_USERNAME", "admin")
    password = os.environ.get("HUMMINGBOT_PASSWORD", "admin")
    return base_url, username, password


def make_auth_header(username, password):
    """Build Basic Auth header value."""
    creds = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {creds}"


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_post(url, payload, auth_header):
    """POST JSON to API endpoint, return parsed response dict."""
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
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error: {e.reason}") from e


def api_get(url, auth_header):
    """GET from API endpoint, return parsed response dict."""
    req = urllib.request.Request(
        url,
        headers={"Authorization": auth_header},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error: {e.reason}") from e


# ---------------------------------------------------------------------------
# Executor fetching
# ---------------------------------------------------------------------------

def fetch_executors(base_url, auth_header, trading_pair=None, connector_name=None, status=None):
    """Fetch all executors via POST /executors/search with optional filters."""
    url = f"{base_url}/executors/search"
    payload = {}
    if trading_pair:
        payload["trading_pair"] = trading_pair
    if connector_name:
        payload["connector_name"] = connector_name
    if status:
        payload["status"] = status

    try:
        result = api_post(url, payload, auth_header)
    except RuntimeError as e:
        print(f"Error fetching executors: {e}")
        sys.exit(1)

    # The API may return a list directly or wrap it in a key
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for key in ("executors", "data", "items", "results"):
            if key in result and isinstance(result[key], list):
                return result[key]
    return []


def fetch_executor_summary(base_url, auth_header):
    """Fetch aggregate executor summary stats."""
    url = f"{base_url}/executors/summary"
    try:
        return api_get(url, auth_header)
    except RuntimeError as e:
        print(f"Error fetching executor summary: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Data extraction helpers
# ---------------------------------------------------------------------------

def _float(v, default=None):
    """Safe float conversion."""
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _str(v, default=""):
    if v is None:
        return default
    return str(v)


def parse_created_at_ts(created_at_str):
    """Parse ISO timestamp string to unix timestamp float."""
    if not created_at_str:
        return None
    # Handle various ISO formats with/without timezone
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            dt = datetime.strptime(created_at_str[:26], fmt[:len(fmt)])
            return dt.timestamp()
        except (ValueError, TypeError):
            pass
    # Try stripping the timezone suffix and parsing
    try:
        clean = created_at_str.replace("+00:00", "").replace("Z", "")
        dt = datetime.fromisoformat(clean)
        return dt.timestamp()
    except Exception:
        return None


def executor_to_row(executor):
    """
    Convert a raw executor dict to a flat row dict for CSV export.
    Returns an ordered dict matching the CSV columns spec.
    """
    config = executor.get("config") or {}
    custom = executor.get("custom_info") or {}

    created_at_str = _str(executor.get("created_at"))
    created_at_ts = parse_created_at_ts(created_at_str)
    close_ts = _float(executor.get("close_timestamp"))

    # Duration in seconds
    duration_seconds = None
    if created_at_ts is not None and close_ts is not None and close_ts > created_at_ts:
        duration_seconds = round(close_ts - created_at_ts, 1)

    row = {
        "executor_id": _str(executor.get("executor_id")),
        "executor_type": _str(executor.get("executor_type")),
        "trading_pair": _str(executor.get("trading_pair")),
        "connector_name": _str(executor.get("connector_name")),
        "status": _str(executor.get("status")),
        "close_type": _str(executor.get("close_type")),
        "created_at": created_at_str,
        "close_timestamp": close_ts,
        "duration_seconds": duration_seconds,
        "net_pnl_quote": _float(executor.get("net_pnl_quote")),
        "net_pnl_pct": _float(executor.get("net_pnl_pct")),
        "cum_fees_quote": _float(executor.get("cum_fees_quote")),
        "filled_amount_quote": _float(executor.get("filled_amount_quote")),
        # custom_info
        "state": _str(custom.get("state")),
        "lower_price": _float(custom.get("lower_price")),
        "upper_price": _float(custom.get("upper_price")),
        "initial_base_amount": _float(custom.get("initial_base_amount")),
        "initial_quote_amount": _float(custom.get("initial_quote_amount")),
        "base_amount_final": _float(custom.get("base_amount")),
        "quote_amount_final": _float(custom.get("quote_amount")),
        "fees_earned_quote": _float(custom.get("fees_earned_quote")),
        "position_rent": _float(custom.get("position_rent")),
        "position_rent_refunded": _float(custom.get("position_rent_refunded")),
        "tx_fee": _float(custom.get("tx_fee")),
        "out_of_range_seconds": _float(custom.get("out_of_range_seconds")),
        # config
        "auto_close_above_range_seconds": config.get("auto_close_above_range_seconds"),
        "auto_close_below_range_seconds": config.get("auto_close_below_range_seconds"),
        "pool_address": _str(config.get("pool_address")),
        "side": config.get("side"),
    }
    return row


CSV_COLUMNS = [
    "executor_id", "executor_type", "trading_pair", "connector_name",
    "status", "close_type", "created_at", "close_timestamp", "duration_seconds",
    "net_pnl_quote", "net_pnl_pct", "cum_fees_quote", "filled_amount_quote",
    "state", "lower_price", "upper_price",
    "initial_base_amount", "initial_quote_amount",
    "base_amount_final", "quote_amount_final",
    "fees_earned_quote", "position_rent", "position_rent_refunded",
    "tx_fee", "out_of_range_seconds",
    "auto_close_above_range_seconds", "auto_close_below_range_seconds",
    "pool_address", "side",
]


# ---------------------------------------------------------------------------
# Summary display
# ---------------------------------------------------------------------------

def show_summary(base_url, auth_header, executors):
    """Show summary of executor data."""
    print("\nExecutor Summary")
    print("=" * 60)

    if not executors:
        print("No executors found.")
        return

    total = len(executors)
    by_status = {}
    by_pair = {}
    by_connector = {}
    total_pnl = 0.0
    total_fees = 0.0
    wins = 0
    losses = 0

    for ex in executors:
        status = _str(ex.get("status", "UNKNOWN"))
        pair = _str(ex.get("trading_pair", "UNKNOWN"))
        connector = _str(ex.get("connector_name", "UNKNOWN"))
        pnl = _float(ex.get("net_pnl_quote"), 0.0)
        fees = _float(ex.get("cum_fees_quote"), 0.0)

        by_status[status] = by_status.get(status, 0) + 1
        by_pair[pair] = by_pair.get(pair, 0) + 1
        by_connector[connector] = by_connector.get(connector, 0) + 1
        total_pnl += pnl
        total_fees += fees
        if pnl >= 0:
            wins += 1
        else:
            losses += 1

    print(f"Total executors: {total}")
    print(f"Total PnL:       ${total_pnl:.4f}")
    print(f"Total Fees:      ${total_fees:.4f}")
    print(f"Win/Loss:        {wins}/{losses}")

    print("\nBy Status:")
    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count}")

    print("\nBy Trading Pair:")
    for pair, count in sorted(by_pair.items()):
        print(f"  {pair}: {count}")

    print("\nBy Connector:")
    for connector, count in sorted(by_connector.items()):
        print(f"  {connector}: {count}")

    # Try to also fetch API summary for any extra stats
    try:
        api_summary = fetch_executor_summary(base_url, auth_header)
        if api_summary:
            print("\nAPI Aggregate Summary:")
            for key, value in api_summary.items():
                if not isinstance(value, (dict, list)):
                    print(f"  {key}: {value}")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main export
# ---------------------------------------------------------------------------

def export_executors(executors, output_path):
    """Write executor list to CSV. Returns number of rows written."""
    if not executors:
        return 0

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    rows = [executor_to_row(ex) for ex in executors]

    with open(output_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Export executor history from Hummingbot API to CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--pair", "-p", help="Filter by trading pair (e.g., SOL-USDC)")
    parser.add_argument("--connector", "-c", help="Filter by connector (e.g., meteora/clmm)")
    parser.add_argument("--status", "-s", help="Filter by status (e.g., TERMINATED, ACTIVE)")
    parser.add_argument("--summary", action="store_true", help="Show summary stats only, don't export CSV")
    parser.add_argument("--output", "-o", help="Output CSV path (default: data/executors_<timestamp>.csv)")

    args = parser.parse_args()

    base_url, username, password = get_api_config()
    auth_header = make_auth_header(username, password)

    print(f"Fetching executors from {base_url} ...")

    executors = fetch_executors(base_url, auth_header, args.pair, args.connector, args.status)

    if not executors:
        filters = []
        if args.pair:
            filters.append(f"pair={args.pair}")
        if args.connector:
            filters.append(f"connector={args.connector}")
        if args.status:
            filters.append(f"status={args.status}")
        filter_str = f" ({', '.join(filters)})" if filters else ""
        print(f"No executors found{filter_str}.")
        return 0

    print(f"Found {len(executors)} executor(s).")

    if args.summary:
        show_summary(base_url, auth_header, executors)
        return 0

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        os.makedirs("data", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/executors_{timestamp}.csv"

    count = export_executors(executors, output_path)
    print(f"Exported {count} executor(s) to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
