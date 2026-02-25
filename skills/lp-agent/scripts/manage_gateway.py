#!/usr/bin/env python3
"""
Manage Gateway via hummingbot-api.

Usage:
    # Check Gateway status
    python manage_gateway.py status

    # Start/stop/restart Gateway
    python manage_gateway.py start
    python manage_gateway.py stop
    python manage_gateway.py restart

    # Get Gateway logs
    python manage_gateway.py logs [--limit 100]

    # Get network config
    python manage_gateway.py network solana-mainnet-beta

    # Update network config (set custom RPC node)
    python manage_gateway.py network solana-mainnet-beta --node-url https://my-rpc.example.com

    # List all networks
    python manage_gateway.py networks

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
        with urllib.request.urlopen(req, timeout=60) as resp:
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


def get_status(args):
    """Get Gateway status."""
    result = api_request("GET", "/gateway/status")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = result.get("status", "unknown")
        container = result.get("container_name", "")
        image = result.get("image", "")
        port = result.get("port", "")

        if status == "running":
            print(f"✓ Gateway is running")
            if container:
                print(f"  Container: {container}")
            if image:
                print(f"  Image: {image}")
            if port:
                print(f"  Port: {port}")
        else:
            print(f"✗ Gateway is {status}")
            if result.get("message"):
                print(f"  {result['message']}")


def start_gateway(args):
    """Start Gateway."""
    data = {}
    if args.passphrase:
        data["passphrase"] = args.passphrase
    if args.image:
        data["image"] = args.image
    if args.port:
        data["port"] = args.port

    print("Starting Gateway...")
    result = api_request("POST", "/gateway/start", data if data else None)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("status") == "running" or result.get("success"):
            print("✓ Gateway started successfully")
        else:
            print(f"Gateway response: {result.get('message', result)}")


def stop_gateway(args):
    """Stop Gateway."""
    print("Stopping Gateway...")
    result = api_request("POST", "/gateway/stop")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("status") == "stopped" or result.get("success"):
            print("✓ Gateway stopped")
        else:
            print(f"Gateway response: {result.get('message', result)}")


def restart_gateway(args):
    """Restart Gateway."""
    print("Restarting Gateway...")
    result = api_request("POST", "/gateway/restart")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("status") == "running" or result.get("success"):
            print("✓ Gateway restarted successfully")
        else:
            print(f"Gateway response: {result.get('message', result)}")


def get_logs(args):
    """Get Gateway logs."""
    params = []
    if args.limit:
        params.append(f"tail={args.limit}")

    endpoint = "/gateway/logs"
    if params:
        endpoint += "?" + "&".join(params)

    result = api_request("GET", endpoint)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        logs = result.get("logs", result) if isinstance(result, dict) else result
        if isinstance(logs, list):
            for log in logs:
                print(log)
        elif isinstance(logs, str):
            print(logs)
        else:
            print(json.dumps(logs, indent=2))


def get_network(args):
    """Get network config."""
    result = api_request("GET", f"/gateway/networks/{args.network_id}")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Network: {args.network_id}")
        print("-" * 40)

        config = result.get("config", result)
        for key, value in config.items():
            if key == "nodeURL":
                print(f"  Node URL: {value}")
            elif key == "tokenListSource":
                print(f"  Token List: {value}")
            elif key == "tokenListType":
                print(f"  Token List Type: {value}")
            elif key == "nativeCurrencySymbol":
                print(f"  Native Currency: {value}")
            else:
                print(f"  {key}: {value}")


def update_network(args):
    """Update network config."""
    data = {}

    if args.node_url:
        data["nodeURL"] = args.node_url
    if args.token_list:
        data["tokenListSource"] = args.token_list

    if not data:
        print("Error: No updates specified. Use --node-url or --token-list", file=sys.stderr)
        sys.exit(1)

    print(f"Updating network {args.network_id}...")
    result = api_request("POST", f"/gateway/networks/{args.network_id}", data)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("success") or result.get("status") == "updated":
            print(f"✓ Network {args.network_id} updated")
            for key, value in data.items():
                print(f"  {key}: {value}")
        else:
            print(f"Response: {result.get('message', result)}")


def list_networks(args):
    """List all available networks."""
    result = api_request("GET", "/gateway/networks")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        networks = result.get("networks", result) if isinstance(result, dict) else result

        if isinstance(networks, list):
            print("Available Networks:")
            print("-" * 40)
            for net in networks:
                if isinstance(net, dict):
                    name = net.get("id", net.get("name", ""))
                    chain = net.get("chain", "")
                    print(f"  {name}" + (f" ({chain})" if chain else ""))
                else:
                    print(f"  {net}")
        elif isinstance(networks, dict):
            print("Available Networks:")
            print("-" * 40)
            for chain, chain_networks in networks.items():
                print(f"\n{chain}:")
                if isinstance(chain_networks, list):
                    for net in chain_networks:
                        print(f"  - {net}")
                elif isinstance(chain_networks, dict):
                    for net_id, net_config in chain_networks.items():
                        print(f"  - {net_id}")
        else:
            print(networks)


def main():
    parser = argparse.ArgumentParser(description="Manage Gateway via hummingbot-api")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status command
    status_parser = subparsers.add_parser("status", help="Get Gateway status")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")
    status_parser.set_defaults(func=get_status)

    # start command
    start_parser = subparsers.add_parser("start", help="Start Gateway")
    start_parser.add_argument("--passphrase", help="Gateway passphrase")
    start_parser.add_argument("--image", help="Docker image (default: hummingbot/gateway:latest)")
    start_parser.add_argument("--port", type=int, help="Port to expose (default: 15888)")
    start_parser.add_argument("--json", action="store_true", help="Output as JSON")
    start_parser.set_defaults(func=start_gateway)

    # stop command
    stop_parser = subparsers.add_parser("stop", help="Stop Gateway")
    stop_parser.add_argument("--json", action="store_true", help="Output as JSON")
    stop_parser.set_defaults(func=stop_gateway)

    # restart command
    restart_parser = subparsers.add_parser("restart", help="Restart Gateway")
    restart_parser.add_argument("--json", action="store_true", help="Output as JSON")
    restart_parser.set_defaults(func=restart_gateway)

    # logs command
    logs_parser = subparsers.add_parser("logs", help="Get Gateway logs")
    logs_parser.add_argument("--limit", type=int, default=100, help="Number of log lines (default: 100)")
    logs_parser.add_argument("--json", action="store_true", help="Output as JSON")
    logs_parser.set_defaults(func=get_logs)

    # networks command (list all)
    networks_parser = subparsers.add_parser("networks", help="List all networks")
    networks_parser.add_argument("--json", action="store_true", help="Output as JSON")
    networks_parser.set_defaults(func=list_networks)

    # network command (get/update single network)
    network_parser = subparsers.add_parser("network", help="Get or update network config")
    network_parser.add_argument("network_id", help="Network ID (e.g., solana-mainnet-beta)")
    network_parser.add_argument("--node-url", help="Set custom RPC node URL")
    network_parser.add_argument("--token-list", help="Set token list source URL")
    network_parser.add_argument("--json", action="store_true", help="Output as JSON")

    def network_handler(args):
        if args.node_url or args.token_list:
            update_network(args)
        else:
            get_network(args)

    network_parser.set_defaults(func=network_handler)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
