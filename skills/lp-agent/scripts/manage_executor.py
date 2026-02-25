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
from typing import Any


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
    config = {
        "type": "lp_executor",
        "connector_name": args.connector,
        "trading_pair": args.pair,
        "pool_address": args.pool,
        "lower_price": args.lower,
        "upper_price": args.upper,
        "base_amount": args.base_amount,
        "quote_amount": args.quote_amount,
        "side": args.side,
    }

    # Add optional parameters
    if args.auto_close_above is not None:
        config["auto_close_above_range_seconds"] = args.auto_close_above
    if args.auto_close_below is not None:
        config["auto_close_below_range_seconds"] = args.auto_close_below
    if args.strategy_type is not None:
        config["extra_params"] = {"strategyType": args.strategy_type}

    result = api_request("POST", "/executors", {"executor_config": config})
    print(json.dumps(result, indent=2))


def get_executor(args):
    """Get executor status."""
    result = api_request("GET", f"/executors/{args.executor_id}")
    print(json.dumps(result, indent=2))


def list_executors(args):
    """List all executors."""
    params = []
    if args.type:
        params.append(f"executor_type={args.type}")
    if args.status:
        params.append(f"status={args.status}")

    endpoint = "/executors"
    if params:
        endpoint += "?" + "&".join(params)

    result = api_request("GET", endpoint)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        executors = result.get("executors", result) if isinstance(result, dict) else result
        if not executors:
            print("No executors found.")
            return

        print(f"{'ID':<40} {'Type':<15} {'Status':<12} {'Pair':<12} {'Created'}")
        print("-" * 100)
        for ex in executors:
            ex_id = ex.get("id", "")[:38] if ex.get("id") else ""
            ex_type = ex.get("type", "")
            status = ex.get("status", ex.get("custom_info", {}).get("state", ""))
            pair = ex.get("trading_pair", "")
            created = ex.get("timestamp", "")
            print(f"{ex_id:<40} {ex_type:<15} {status:<12} {pair:<12} {created}")


def get_logs(args):
    """Get executor logs."""
    endpoint = f"/executors/{args.executor_id}/logs"
    if args.limit:
        endpoint += f"?limit={args.limit}"

    result = api_request("GET", endpoint)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        logs = result.get("logs", result) if isinstance(result, dict) else result
        for log in logs:
            ts = log.get("timestamp", "")
            level = log.get("level", "INFO")
            msg = log.get("message", str(log))
            print(f"[{ts}] {level}: {msg}")


def stop_executor(args):
    """Stop an executor."""
    data = {"keep_position": args.keep_position}
    result = api_request("POST", f"/executors/{args.executor_id}/stop", data)
    print(json.dumps(result, indent=2))


def get_summary(args):
    """Get summary of all executors."""
    result = api_request("GET", "/executors/summary")
    print(json.dumps(result, indent=2))


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
    create_parser.set_defaults(func=create_executor)

    # get command
    get_parser = subparsers.add_parser("get", help="Get executor status")
    get_parser.add_argument("executor_id", help="Executor ID")
    get_parser.set_defaults(func=get_executor)

    # list command
    list_parser = subparsers.add_parser("list", help="List executors")
    list_parser.add_argument("--type", help="Filter by executor type")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    list_parser.set_defaults(func=list_executors)

    # logs command
    logs_parser = subparsers.add_parser("logs", help="Get executor logs")
    logs_parser.add_argument("executor_id", help="Executor ID")
    logs_parser.add_argument("--limit", type=int, default=50, help="Number of log entries (default: 50)")
    logs_parser.add_argument("--json", action="store_true", help="Output as JSON")
    logs_parser.set_defaults(func=get_logs)

    # stop command
    stop_parser = subparsers.add_parser("stop", help="Stop executor")
    stop_parser.add_argument("executor_id", help="Executor ID")
    stop_parser.add_argument("--keep-position", action="store_true", help="Keep position on-chain (don't close)")
    stop_parser.set_defaults(func=stop_executor)

    # summary command
    summary_parser = subparsers.add_parser("summary", help="Get executor summary")
    summary_parser.set_defaults(func=get_summary)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
