#!/usr/bin/env python3
"""
Add and manage wallets via hummingbot-api Gateway.

Usage:
    # List existing wallets
    python add_wallet.py list

    # Add wallet by private key
    python add_wallet.py add --private-key <BASE58_KEY>

    # Add wallet by private key (prompted, not visible in shell history)
    python add_wallet.py add

    # Get wallet balances
    python add_wallet.py balances --address <WALLET_ADDRESS>

    # Get wallet balances for all tokens
    python add_wallet.py balances --address <WALLET_ADDRESS> --all

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


def list_wallets(args):
    """List wallets connected to Gateway."""
    result = api_request("GET", "/gateway/wallets")

    if args.json:
        print(json.dumps(result, indent=2))
        return

    wallets = result.get("wallets", result)

    if not wallets:
        print("No wallets found.")
        print("")
        print("Add one with:")
        print("  python add_wallet.py add --private-key <BASE58_KEY>")
        return

    print("Connected Wallets")
    print("-" * 60)

    if isinstance(wallets, dict):
        for chain, addresses in wallets.items():
            if addresses:
                print(f"\n{chain}:")
                for addr in addresses:
                    if isinstance(addr, dict):
                        print(f"  {addr.get('address', addr)}")
                    else:
                        print(f"  {addr}")
    elif isinstance(wallets, list):
        for w in wallets:
            if isinstance(w, dict):
                chain = w.get("chain", "")
                addr = w.get("address", "")
                print(f"  [{chain}] {addr}")
            else:
                print(f"  {w}")


def add_wallet(args):
    """Add a wallet to Gateway."""
    private_key = args.private_key

    # Prompt for private key if not provided (avoids shell history exposure)
    if not private_key:
        try:
            import getpass
            private_key = getpass.getpass("Enter private key (base58): ")
        except (ImportError, EOFError):
            print("Error: --private-key is required in non-interactive mode", file=sys.stderr)
            sys.exit(1)

    if not private_key:
        print("Error: Private key cannot be empty", file=sys.stderr)
        sys.exit(1)

    data = {
        "chain": args.chain,
        "network": args.network,
        "privateKey": private_key,
    }

    print(f"Adding {args.chain} wallet...")
    result = api_request("POST", "/gateway/wallets", data)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    address = result.get("address", result.get("wallet", ""))
    if address:
        print(f"✓ Wallet added successfully")
        print(f"  Chain: {args.chain}")
        print(f"  Network: {args.network}")
        print(f"  Address: {address}")
    else:
        print(f"Response: {result}")


def get_balances(args):
    """Get wallet balances."""
    params = {
        "chain": args.chain,
        "network": args.network,
        "address": args.address,
    }

    if args.tokens:
        params["tokenSymbols"] = args.tokens

    result = api_request("POST", "/gateway/balances", params)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"Balances for {args.address[:8]}...{args.address[-6:]}")
    print("-" * 50)

    balances = result.get("balances", result)

    if isinstance(balances, dict):
        for token, amount in sorted(balances.items()):
            if float(amount) > 0 or args.all:
                print(f"  {token}: {amount}")
    elif isinstance(balances, list):
        for b in balances:
            if isinstance(b, dict):
                token = b.get("symbol", b.get("token", "?"))
                amount = b.get("balance", b.get("amount", 0))
                if float(amount) > 0 or args.all:
                    print(f"  {token}: {amount}")

    native = result.get("nativeBalance", result.get("native_balance"))
    if native:
        print(f"\n  Native (SOL): {native}")


def main():
    parser = argparse.ArgumentParser(description="Add and manage wallets via hummingbot-api Gateway")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list command
    list_parser = subparsers.add_parser("list", help="List connected wallets")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    list_parser.set_defaults(func=list_wallets)

    # add command
    add_parser = subparsers.add_parser("add", help="Add a wallet")
    add_parser.add_argument("--private-key", help="Private key (base58). Omit to be prompted securely.")
    add_parser.add_argument("--chain", default="solana", help="Blockchain (default: solana)")
    add_parser.add_argument("--network", default="mainnet-beta", help="Network (default: mainnet-beta)")
    add_parser.add_argument("--json", action="store_true", help="Output as JSON")
    add_parser.set_defaults(func=add_wallet)

    # balances command
    bal_parser = subparsers.add_parser("balances", help="Get wallet balances")
    bal_parser.add_argument("--address", required=True, help="Wallet address")
    bal_parser.add_argument("--tokens", nargs="+", help="Specific token symbols to check")
    bal_parser.add_argument("--chain", default="solana", help="Blockchain (default: solana)")
    bal_parser.add_argument("--network", default="mainnet-beta", help="Network (default: mainnet-beta)")
    bal_parser.add_argument("--all", action="store_true", help="Show zero balances too")
    bal_parser.add_argument("--json", action="store_true", help="Output as JSON")
    bal_parser.set_defaults(func=get_balances)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
