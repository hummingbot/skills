#!/usr/bin/env python3
"""
Manage LP executors via hummingbot-api.

Usage:
    # Create LP executor
    python manage_executor.py create --pool <pool_address> --pair SOL-USDC --quote-amount 100 --lower 180 --upper 185

    # Get executor status
    python manage_executor.py get <executor_id>

    # List all executors
    python manage_executor.py list [--type lp_executor]

    # Get executor logs
    python manage_executor.py logs <executor_id> [--limit 50]

    # Stop executor
    python manage_executor.py stop <executor_id> [--keep-position]

Environment:
    API_URL - API base URL (default: http://localhost:8000)
    API_USER - API username (default: admin)
    API_PASS - API password (default: admin)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import base64
from datetime import datetime


def load_env():
    """Load environment from .env files."""
    for path in [".env", os.path.expanduser("~/.hummingbot/.env"), os.path.expanduser("~/.env")]:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            break


def get_api_config():
    """Get API configuration from environment."""
    load_env()
    return {
        "url": os.environ.get("API_URL", "http://localhost:8000"),
        "user": os.environ.get("API_USER", "admin"),
        "password": os.environ.get("API_PASS", "admin"),
    }


def api_request(method: str, endpoint: str, data: dict | None = None) -> dict:
    """Make authenticated API request."""
    config = get_api_config()
    url = f"{config['url']}{endpoint}"

    # Basic auth
    credentials = base64.b64encode(f"{config['user']}:{config['password']}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"Error: HTTP {e.code} - {e.reason}", file=sys.stderr)
        if error_body:
            try:
                print(json.dumps(json.loads(error_body), indent=2), file=sys.stderr)
            except json.JSONDecodeError:
                print(error_body, file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Cannot connect to API at {config['url']}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def create_executor(args):
    """Create a new LP executor."""
    # LP executor uses 'market' object for connector/pair
    executor_config = {
        "type": "lp_executor",
        "market": {
            "connector_name": args.connector,
            "trading_pair": args.pair,
        },
        "pool_address": args.pool,
        "lower_price": args.lower,
        "upper_price": args.upper,
        "base_amount": args.base_amount,
        "quote_amount": args.quote_amount,
        "side": args.side,
    }

    # Add optional parameters
    if args.auto_close_above is not None:
        executor_config["auto_close_above_range_seconds"] = args.auto_close_above
    if args.auto_close_below is not None:
        executor_config["auto_close_below_range_seconds"] = args.auto_close_below
    if args.strategy_type is not None:
        executor_config["extra_params"] = {"strategyType": args.strategy_type}

    request_data = {
        "executor_config": executor_config,
        "account_name": args.account,
    }

    result = api_request("POST", "/executors/", request_data)
    print(json.dumps(result, indent=2))


def get_executor(args):
    """Get executor status."""
    result = api_request("GET", f"/executors/{args.executor_id}")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Executor: {result.get('executor_id', args.executor_id)}")
        print("-" * 50)
        print(f"  Type: {result.get('executor_type', result.get('type', ''))}")
        print(f"  Status: {result.get('status', '')}")
        print(f"  Trading Pair: {result.get('trading_pair', '')}")
        print(f"  Connector: {result.get('connector_name', '')}")

        custom_info = result.get("custom_info", {})
        if custom_info:
            state = custom_info.get("state", "")
            if state:
                print(f"  State: {state}")
            position_address = custom_info.get("position_address", "")
            if position_address:
                print(f"  Position: {position_address[:20]}...")

        pnl = result.get("net_pnl_quote", result.get("pnl", 0))
        print(f"  PnL: ${pnl:.4f}" if pnl else "  PnL: $0.00")


def list_executors(args):
    """List all executors."""
    # Use POST /executors/search with filter
    filter_request = {
        "limit": args.limit,
    }

    if args.type:
        filter_request["executor_types"] = [args.type]
    if args.status:
        filter_request["status"] = args.status

    result = api_request("POST", "/executors/search", filter_request)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        executors = result.get("data", [])
        pagination = result.get("pagination", {})

        if not executors:
            print("No executors found.")
            return

        print(f"Executors ({pagination.get('total_count', len(executors))} total):")
        print("-" * 110)
        print(f"{'ID':<46} {'Type':<15} {'Status':<12} {'Pair':<15} {'PnL':<10}")
        print("-" * 110)

        for ex in executors:
            ex_id = ex.get("executor_id", "")
            ex_type = ex.get("executor_type", ex.get("type", ""))[:13]
            status = ex.get("status", "")[:10]
            pair = ex.get("trading_pair", "")[:13]
            pnl = ex.get("net_pnl_quote", ex.get("pnl", 0))
            pnl_str = f"${pnl:.2f}" if pnl else "$0.00"
            print(f"{ex_id:<46} {ex_type:<15} {status:<12} {pair:<15} {pnl_str:<10}")


def get_logs(args):
    """Get executor logs."""
    params = [f"limit={args.limit}"]
    if args.level:
        params.append(f"level={args.level}")

    endpoint = f"/executors/{args.executor_id}/logs?{'&'.join(params)}"
    result = api_request("GET", endpoint)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        logs = result.get("logs", [])
        total = result.get("total_count", len(logs))
        print(f"Logs for {args.executor_id} ({total} total, showing {len(logs)}):")
        print("-" * 80)

        for log in logs:
            ts = log.get("timestamp", "")
            level = log.get("level", "INFO")
            msg = log.get("message", str(log))
            print(f"[{ts}] {level}: {msg}")


def stop_executor(args):
    """Stop an executor."""
    data = {"keep_position": args.keep_position}
    result = api_request("POST", f"/executors/{args.executor_id}/stop", data)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("success"):
            print(f"✓ Executor {args.executor_id} stopped")
            if args.keep_position:
                print("  Position kept on-chain")
            else:
                print("  Position closed")
        else:
            print(f"Response: {result}")


def get_summary(args):
    """Get summary of all executors."""
    result = api_request("GET", "/executors/summary")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Executor Summary")
        print("-" * 40)
        print(f"  Active: {result.get('active_count', 0)}")
        print(f"  Completed: {result.get('completed_count', 0)}")
        print(f"  Total PnL: ${result.get('total_pnl', 0):.2f}")
        print(f"  Total Volume: ${result.get('total_volume', 0):.2f}")

        by_type = result.get("by_type", {})
        if by_type:
            print("\n  By Type:")
            for t, count in by_type.items():
                print(f"    {t}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Manage LP executors via hummingbot-api")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create command
    create_parser = subparsers.add_parser("create", help="Create LP executor")
    create_parser.add_argument("--pool", required=True, help="Pool address")
    create_parser.add_argument("--pair", required=True, help="Trading pair (e.g., SOL-USDC)")
    create_parser.add_argument("--connector", default="meteora/clmm", help="Connector name (default: meteora/clmm)")
    create_parser.add_argument("--lower", type=float, required=True, help="Lower price bound")
    create_parser.add_argument("--upper", type=float, required=True, help="Upper price bound")
    create_parser.add_argument("--base-amount", type=float, default=0, help="Base token amount (default: 0)")
    create_parser.add_argument("--quote-amount", type=float, default=0, help="Quote token amount")
    create_parser.add_argument("--side", type=int, default=1, choices=[0, 1, 2], help="Side: 0=BOTH, 1=BUY, 2=SELL (default: 1)")
    create_parser.add_argument("--auto-close-above", type=int, help="Auto-close seconds when price above range")
    create_parser.add_argument("--auto-close-below", type=int, help="Auto-close seconds when price below range")
    create_parser.add_argument("--strategy-type", type=int, choices=[0, 1, 2], help="Meteora strategy: 0=Spot, 1=Curve, 2=Bid-Ask")
    create_parser.add_argument("--account", default="master_account", help="Account name (default: master_account)")
    create_parser.set_defaults(func=create_executor)

    # get command
    get_parser = subparsers.add_parser("get", help="Get executor status")
    get_parser.add_argument("executor_id", help="Executor ID")
    get_parser.add_argument("--json", action="store_true", help="Output as JSON")
    get_parser.set_defaults(func=get_executor)

    # list command
    list_parser = subparsers.add_parser("list", help="List executors")
    list_parser.add_argument("--type", help="Filter by executor type (e.g., lp_executor)")
    list_parser.add_argument("--status", help="Filter by status (e.g., RUNNING, TERMINATED)")
    list_parser.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    list_parser.set_defaults(func=list_executors)

    # logs command
    logs_parser = subparsers.add_parser("logs", help="Get executor logs")
    logs_parser.add_argument("executor_id", help="Executor ID")
    logs_parser.add_argument("--limit", type=int, default=50, help="Number of log entries (default: 50)")
    logs_parser.add_argument("--level", choices=["ERROR", "WARNING", "INFO", "DEBUG"], help="Filter by log level")
    logs_parser.add_argument("--json", action="store_true", help="Output as JSON")
    logs_parser.set_defaults(func=get_logs)

    # stop command
    stop_parser = subparsers.add_parser("stop", help="Stop executor")
    stop_parser.add_argument("executor_id", help="Executor ID")
    stop_parser.add_argument("--keep-position", action="store_true", help="Keep position on-chain (don't close)")
    stop_parser.add_argument("--json", action="store_true", help="Output as JSON")
    stop_parser.set_defaults(func=stop_executor)

    # summary command
    summary_parser = subparsers.add_parser("summary", help="Get executor summary")
    summary_parser.add_argument("--json", action="store_true", help="Output as JSON")
    summary_parser.set_defaults(func=get_summary)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
