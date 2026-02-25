#!/usr/bin/env python3
"""
Manage LP Rebalancer controllers via hummingbot-api.

Usage:
    # Get LP Rebalancer config template
    python manage_controller.py template

    # Create LP Rebalancer controller config
    python manage_controller.py create-config my_lp_config --pool <pool_address> --pair SOL-USDC --amount 100

    # Deploy bot with controller
    python manage_controller.py deploy my_bot --configs my_lp_config

    # Get active bots status
    python manage_controller.py status

    # Get bot logs
    python manage_controller.py logs <bot_name> [--limit 50] [--type error]

    # Stop bot
    python manage_controller.py stop <bot_name>

    # Start/stop controllers within a bot
    python manage_controller.py start-controllers <bot_name> --controllers config1 config2
    python manage_controller.py stop-controllers <bot_name> --controllers config1 config2

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


def get_template(args):
    """Get LP Rebalancer config template."""
    result = api_request("GET", "/controllers/generic/lp_rebalancer/config/template")
    print(json.dumps(result, indent=2))


def create_config(args):
    """Create LP Rebalancer controller config."""
    config_data = {
        "controller_name": "lp_rebalancer",
        "connector_name": args.connector,
        "network": args.network,
        "trading_pair": args.pair,
        "pool_address": args.pool,
        "total_amount_quote": args.amount,
        "side": args.side,
        "position_width_pct": args.width,
        "position_offset_pct": args.offset,
        "rebalance_seconds": args.rebalance_seconds,
        "rebalance_threshold_pct": args.rebalance_threshold,
        "sell_price_max": args.sell_max,
        "sell_price_min": args.sell_min,
        "buy_price_max": args.buy_max,
        "buy_price_min": args.buy_min,
        "strategy_type": args.strategy_type,
    }

    result = api_request("POST", "/controllers/config", {
        "action": "upsert",
        "target": "config",
        "config_name": args.config_name,
        "config_data": config_data,
    })
    print(json.dumps(result, indent=2))


def deploy_bot(args):
    """Deploy bot with controller configs."""
    data = {
        "bot_name": args.bot_name,
        "controllers_config": args.configs,
        "account_name": args.account,
        "image": args.image,
    }

    if args.max_global_drawdown:
        data["max_global_drawdown_quote"] = args.max_global_drawdown
    if args.max_controller_drawdown:
        data["max_controller_drawdown_quote"] = args.max_controller_drawdown

    result = api_request("POST", "/bots/deploy", data)
    print(json.dumps(result, indent=2))


def get_status(args):
    """Get active bots status."""
    result = api_request("GET", "/bots/status")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        bots = result.get("bots", result) if isinstance(result, dict) else result
        if not bots:
            print("No active bots.")
            return

        for bot in bots:
            name = bot.get("bot_name", "")
            status = bot.get("status", "")
            pnl = bot.get("unrealized_pnl", 0)
            rpnl = bot.get("realized_pnl", 0)
            volume = bot.get("volume_traded", 0)
            print(f"\n=== {name} ({status}) ===")
            print(f"  Unrealized PnL: ${pnl:.2f}")
            print(f"  Realized PnL:   ${rpnl:.2f}")
            print(f"  Volume:         ${volume:.2f}")

            controllers = bot.get("controllers", [])
            if controllers:
                print(f"  Controllers:")
                for ctrl in controllers:
                    ctrl_name = ctrl.get("config_name", ctrl.get("id", ""))
                    ctrl_status = ctrl.get("status", "")
                    print(f"    - {ctrl_name}: {ctrl_status}")


def get_logs(args):
    """Get bot logs."""
    params = []
    if args.limit:
        params.append(f"limit={args.limit}")
    if args.type:
        params.append(f"log_type={args.type}")
    if args.search:
        params.append(f"search_term={args.search}")

    endpoint = f"/bots/{args.bot_name}/logs"
    if params:
        endpoint += "?" + "&".join(params)

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


def stop_bot(args):
    """Stop a bot."""
    result = api_request("POST", f"/bots/{args.bot_name}/stop", {"action": "stop_bot"})
    print(json.dumps(result, indent=2))


def manage_controllers(args, action: str):
    """Start or stop controllers within a bot."""
    data = {
        "action": action,
        "controller_names": args.controllers,
    }
    result = api_request("POST", f"/bots/{args.bot_name}/controllers", data)
    print(json.dumps(result, indent=2))


def start_controllers(args):
    """Start controllers within a bot."""
    manage_controllers(args, "start_controllers")


def stop_controllers(args):
    """Stop controllers within a bot."""
    manage_controllers(args, "stop_controllers")


def list_configs(args):
    """List all controller configs."""
    result = api_request("POST", "/controllers/config", {"action": "list"})

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        configs = result.get("configs", result) if isinstance(result, dict) else result
        if not configs:
            print("No configs found.")
            return

        print(f"{'Name':<30} {'Controller':<20} {'Pair':<15} {'Amount'}")
        print("-" * 80)
        for cfg in configs:
            name = cfg.get("id", cfg.get("config_name", ""))[:28]
            controller = cfg.get("controller_name", "")[:18]
            pair = cfg.get("trading_pair", "")[:13]
            amount = cfg.get("total_amount_quote", "")
            print(f"{name:<30} {controller:<20} {pair:<15} {amount}")


def describe_config(args):
    """Get details of a specific config."""
    result = api_request("POST", "/controllers/config", {
        "action": "describe",
        "config_name": args.config_name,
    })
    print(json.dumps(result, indent=2))


def delete_config(args):
    """Delete a controller config."""
    result = api_request("POST", "/controllers/config", {
        "action": "delete",
        "target": "config",
        "config_name": args.config_name,
    })
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Manage LP Rebalancer controllers via hummingbot-api")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # template command
    template_parser = subparsers.add_parser("template", help="Get LP Rebalancer config template")
    template_parser.set_defaults(func=get_template)

    # create-config command
    create_parser = subparsers.add_parser("create-config", help="Create LP Rebalancer config")
    create_parser.add_argument("config_name", help="Config name")
    create_parser.add_argument("--pool", required=True, help="Pool address")
    create_parser.add_argument("--pair", required=True, help="Trading pair (e.g., SOL-USDC)")
    create_parser.add_argument("--connector", default="meteora/clmm", help="Connector name (default: meteora/clmm)")
    create_parser.add_argument("--network", default="solana-mainnet-beta", help="Network (default: solana-mainnet-beta)")
    create_parser.add_argument("--amount", type=float, default=50, help="Total amount in quote currency (default: 50)")
    create_parser.add_argument("--side", type=int, default=1, choices=[0, 1, 2], help="Side: 0=BOTH, 1=BUY, 2=SELL (default: 1)")
    create_parser.add_argument("--width", type=float, default=0.5, help="Position width %% (default: 0.5)")
    create_parser.add_argument("--offset", type=float, default=0.01, help="Position offset %% (default: 0.01)")
    create_parser.add_argument("--rebalance-seconds", type=int, default=60, help="Rebalance seconds (default: 60)")
    create_parser.add_argument("--rebalance-threshold", type=float, default=0.1, help="Rebalance threshold %% (default: 0.1)")
    create_parser.add_argument("--sell-max", type=float, help="Sell price max (anchor)")
    create_parser.add_argument("--sell-min", type=float, help="Sell price min")
    create_parser.add_argument("--buy-max", type=float, help="Buy price max")
    create_parser.add_argument("--buy-min", type=float, help="Buy price min (anchor)")
    create_parser.add_argument("--strategy-type", type=int, default=0, choices=[0, 1, 2], help="Meteora strategy: 0=Spot, 1=Curve, 2=Bid-Ask (default: 0)")
    create_parser.set_defaults(func=create_config)

    # list-configs command
    list_configs_parser = subparsers.add_parser("list-configs", help="List controller configs")
    list_configs_parser.add_argument("--json", action="store_true", help="Output as JSON")
    list_configs_parser.set_defaults(func=list_configs)

    # describe-config command
    describe_parser = subparsers.add_parser("describe-config", help="Get config details")
    describe_parser.add_argument("config_name", help="Config name")
    describe_parser.set_defaults(func=describe_config)

    # delete-config command
    delete_parser = subparsers.add_parser("delete-config", help="Delete a config")
    delete_parser.add_argument("config_name", help="Config name")
    delete_parser.set_defaults(func=delete_config)

    # deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy bot with controllers")
    deploy_parser.add_argument("bot_name", help="Bot name")
    deploy_parser.add_argument("--configs", nargs="+", required=True, help="Controller config names")
    deploy_parser.add_argument("--account", default="master_account", help="Account name (default: master_account)")
    deploy_parser.add_argument("--image", default="hummingbot/hummingbot:latest", help="Docker image")
    deploy_parser.add_argument("--max-global-drawdown", type=float, help="Max global drawdown in quote")
    deploy_parser.add_argument("--max-controller-drawdown", type=float, help="Max controller drawdown in quote")
    deploy_parser.set_defaults(func=deploy_bot)

    # status command
    status_parser = subparsers.add_parser("status", help="Get active bots status")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")
    status_parser.set_defaults(func=get_status)

    # logs command
    logs_parser = subparsers.add_parser("logs", help="Get bot logs")
    logs_parser.add_argument("bot_name", help="Bot name")
    logs_parser.add_argument("--limit", type=int, default=50, help="Number of log entries (default: 50)")
    logs_parser.add_argument("--type", choices=["error", "general", "all"], default="all", help="Log type (default: all)")
    logs_parser.add_argument("--search", help="Search term to filter logs")
    logs_parser.add_argument("--json", action="store_true", help="Output as JSON")
    logs_parser.set_defaults(func=get_logs)

    # stop command
    stop_parser = subparsers.add_parser("stop", help="Stop a bot")
    stop_parser.add_argument("bot_name", help="Bot name")
    stop_parser.set_defaults(func=stop_bot)

    # start-controllers command
    start_ctrl_parser = subparsers.add_parser("start-controllers", help="Start controllers within a bot")
    start_ctrl_parser.add_argument("bot_name", help="Bot name")
    start_ctrl_parser.add_argument("--controllers", nargs="+", required=True, help="Controller names to start")
    start_ctrl_parser.set_defaults(func=start_controllers)

    # stop-controllers command
    stop_ctrl_parser = subparsers.add_parser("stop-controllers", help="Stop controllers within a bot")
    stop_ctrl_parser.add_argument("bot_name", help="Bot name")
    stop_ctrl_parser.add_argument("--controllers", nargs="+", required=True, help="Controller names to stop")
    stop_ctrl_parser.set_defaults(func=stop_controllers)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
