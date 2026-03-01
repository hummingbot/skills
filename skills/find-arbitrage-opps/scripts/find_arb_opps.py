#!/usr/bin/env python3
"""
Find arbitrage opportunities across CEX and DEX exchanges.

Usage:
    # Basic - find BTC/USDT opportunities
    python find_arb_opps.py --base BTC --quote USDT

    # Include fungible tokens (BTC = WBTC, USDT = USDC)
    python find_arb_opps.py --base BTC,WBTC --quote USDT,USDC

    # Filter by connectors
    python find_arb_opps.py --base BTC --quote USDT --connectors binance,kraken

    # Include DEX prices (Jupiter for Solana, Uniswap for Ethereum)
    python find_arb_opps.py --base SOL --quote USDC --dex

    # Minimum spread filter
    python find_arb_opps.py --base ETH --quote USDT --min-spread 0.1

Notes:
    - BTC markets are only available to Australian residents on some exchanges.

Environment:
    HUMMINGBOT_API_URL  - Hummingbot API base URL (default: http://localhost:8000)
    API_USER            - API username (default: admin)
    API_PASS            - API password (default: admin)
    GATEWAY_URL         - Gateway URL for DEX prices (default: http://localhost:15888)
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


# ─── DEX defaults ────────────────────────────────────────────────────────────

# Jupiter handles Solana tokens; Uniswap handles Ethereum tokens.
# These connectors are queried automatically when --dex flag is set.
DEX_CONNECTORS = [
    {"connector": "jupiter",  "chain": "solana",   "network": "mainnet-beta"},
    {"connector": "uniswap",  "chain": "ethereum",  "network": "mainnet"},
]

# Tokens native to each chain — used to skip irrelevant DEX queries.
# Jupiter only queried if any token is Solana-native.
# Uniswap only queried if any token is Ethereum-native.
SOLANA_TOKENS = {
    "SOL", "WSOL", "RAY", "ORCA", "JUP", "BONK", "WIF", "PYTH",
    "PERCOLATOR", "PRCLT", "JITO", "MNGO", "DRIFT", "METIS",
}
ETHEREUM_TOKENS = {
    "ETH", "WETH", "USDT", "USDC", "DAI", "WBTC", "LINK", "UNI",
    "AAVE", "MKR", "SNX", "COMP", "CRV", "BAL", "SUSHI", "1INCH",
    "LDO", "RPL", "ENS", "GRT", "MATIC", "CBBTC",
}


def dex_applies(dex, base_tokens, quote_tokens):
    """
    Return True if this DEX should be queried.

    Logic: at least one base OR quote token must be *exclusively* native to
    that chain (not cross-chain like USDC/USDT which exist on both).
    Cross-chain stablecoins (USDC, USDT, DAI) are not used as the deciding
    factor — only chain-specific tokens are.
    """
    CROSS_CHAIN = {"USDC", "USDT", "DAI", "BUSD", "FRAX"}
    all_upper = {t.upper() for t in base_tokens + quote_tokens}
    deciding = all_upper - CROSS_CHAIN  # remove cross-chain tokens

    if dex["connector"] == "jupiter":
        return bool(deciding & SOLANA_TOKENS)
    if dex["connector"] == "uniswap":
        return bool(deciding & ETHEREUM_TOKENS)
    return True

# BTC is only available on exchanges open to Australian residents.
BTC_TOKENS = {"BTC", "WBTC", "CBBTC"}

# Connectors restricted to specific regions — excluded from results by default.
# Users can override with --include-btc-markets.
RESTRICTED_CONNECTORS = {
    "btc_markets",  # Australian residents only (KYC with AU passport required)
}


# ─── Environment / config ────────────────────────────────────────────────────

def load_env():
    for path in ["hummingbot-api/.env", os.path.expanduser("~/.hummingbot/.env"), ".env"]:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            break


def get_api_config():
    load_env()
    return {
        "url": os.environ.get("HUMMINGBOT_API_URL", "http://localhost:8000"),
        "user": os.environ.get("API_USER", "admin"),
        "password": os.environ.get("API_PASS", "admin"),
        "gateway_url": os.environ.get("GATEWAY_URL", "http://localhost:15888"),
    }


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _request(url, method="GET", data=None, headers=None, timeout=30):
    h = headers or {}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"HTTP {e.code}: {error_body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection failed: {e.reason}")


def api_request(method, endpoint, data=None, timeout=30):
    config = get_api_config()
    creds = base64.b64encode(f"{config['user']}:{config['password']}".encode()).decode()
    return _request(
        f"{config['url']}{endpoint}",
        method=method,
        data=data,
        headers={"Authorization": f"Basic {creds}", "Content-Type": "application/json"},
        timeout=timeout,
    )


def gateway_request(endpoint, timeout=30):
    config = get_api_config()
    return _request(f"{config['gateway_url']}{endpoint}", timeout=timeout)


# ─── CEX helpers ──────────────────────────────────────────────────────────────

def get_available_connectors():
    try:
        result = api_request("GET", "/connectors/")
        return result if isinstance(result, list) else []
    except RuntimeError as e:
        print(f"Warning: Could not fetch connectors: {e}", file=sys.stderr)
        return []


def get_connector_trading_pairs(connector):
    try:
        result = api_request("GET", f"/connectors/{connector}/trading-rules", timeout=15)
        if isinstance(result, dict) and "detail" not in result:
            return list(result.keys())
        return []
    except RuntimeError:
        return []


def fetch_cex_prices(connector, trading_pairs):
    try:
        result = api_request("POST", "/market-data/prices", {
            "connector_name": connector,
            "trading_pairs": trading_pairs,
        }, timeout=15)
        return result.get("prices", result)
    except RuntimeError as e:
        return {"error": str(e)}


def find_matching_pairs(trading_pairs, base_tokens, quote_tokens):
    matches = []
    base_set = {t.upper() for t in base_tokens}
    quote_set = {t.upper() for t in quote_tokens}
    for pair in trading_pairs:
        if "-" in pair:
            b, q = pair.upper().split("-", 1)
        elif "/" in pair:
            b, q = pair.upper().split("/", 1)
        else:
            continue
        if b in base_set and q in quote_set:
            matches.append(pair)
    return matches


# ─── DEX helpers ─────────────────────────────────────────────────────────────

def fetch_dex_price(connector, network, base_token, quote_token, amount=1.0):
    """
    Fetch a price quote from a DEX connector via Gateway.

    - Jupiter  → Solana  mainnet-beta (default)
    - Uniswap  → Ethereum mainnet     (default)

    Returns a price entry dict or None on failure.
    """
    try:
        params = (
            f"network={network}"
            f"&baseToken={base_token}"
            f"&quoteToken={quote_token}"
            f"&amount={amount}"
            f"&side=SELL"
        )
        endpoint = f"/connectors/{connector}/router/quote-swap?{params}"
        result = gateway_request(endpoint, timeout=20)
        price = result.get("price")
        if price and float(price) > 0:
            return {
                "connector": f"{connector} (DEX)",
                "pair": f"{base_token}-{quote_token}",
                "price": float(price),
                "bid": None,
                "ask": None,
                "source": "dex",
            }
    except RuntimeError as e:
        print(f"  ⚠ {connector} DEX quote failed: {e}", file=sys.stderr)
    return None


def fetch_all_dex_prices(base_tokens, quote_tokens, amount=1.0):
    """
    Query Jupiter (Solana) and Uniswap (Ethereum) for all base/quote combinations.
    Returns a list of price entry dicts.
    """
    results = []
    tasks = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for dex in DEX_CONNECTORS:
            if not dex_applies(dex, base_tokens, quote_tokens):
                continue
            for base in base_tokens:
                for quote in quote_tokens:
                    if base.upper() == quote.upper():
                        continue
                    tasks.append(executor.submit(
                        fetch_dex_price,
                        dex["connector"], dex["network"],
                        base, quote, amount,
                    ))
        for f in as_completed(tasks):
            try:
                entry = f.result()
                if entry:
                    results.append(entry)
            except Exception:
                pass
    return results


# ─── Formatting ───────────────────────────────────────────────────────────────

def format_price(price):
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    else:
        return f"${price:.8f}"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Find arbitrage opportunities across CEX and DEX exchanges")
    parser.add_argument("--base", required=True, help="Base token(s), comma-separated (e.g., BTC,WBTC)")
    parser.add_argument("--quote", required=True, help="Quote token(s), comma-separated (e.g., USDT,USDC)")
    parser.add_argument("--connectors", help="CEX connectors to use, comma-separated (default: all)")
    parser.add_argument("--dex", action="store_true", default=False,
                        help="Include DEX prices (Jupiter/Solana, Uniswap/Ethereum)")
    parser.add_argument("--include-btc-markets", action="store_true", default=False,
                        help="Include btc_markets connector (Australian residents only — requires AU passport KYC)")
    parser.add_argument("--min-spread", type=float, default=0.0, help="Minimum spread %% to show (default: 0.0)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    base_tokens = [t.strip() for t in args.base.split(",")]
    quote_tokens = [t.strip() for t in args.quote.split(",")]

    # Warn about BTC Australian-only restriction
    if any(t.upper() in BTC_TOKENS for t in base_tokens + quote_tokens):
        print("⚠  Note: BTC markets are only available to Australian residents on some exchanges.\n",
              file=sys.stderr)

    # ── CEX prices ──────────────────────────────────────────────────────────
    if args.connectors:
        connectors = [c.strip() for c in args.connectors.split(",")]
    else:
        connectors = get_available_connectors()
        if not connectors:
            print("Warning: No CEX connectors available — CEX prices skipped.", file=sys.stderr)

    # Filter region-restricted connectors unless user opts in
    if not args.include_btc_markets:
        before = len(connectors)
        connectors = [c for c in connectors if c not in RESTRICTED_CONNECTORS]
        removed = before - len(connectors)
        if removed:
            print(f"  ℹ  Excluded {removed} region-restricted connector(s) (use --include-btc-markets to include).",
                  file=sys.stderr)

    connector_pairs = {}
    if connectors:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(get_connector_trading_pairs, c): c for c in connectors}
            for future in as_completed(futures):
                connector = futures[future]
                try:
                    matching = find_matching_pairs(future.result(), base_tokens, quote_tokens)
                    if matching:
                        connector_pairs[connector] = matching
                except Exception:
                    pass

    prices = []

    if connector_pairs:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(fetch_cex_prices, connector, pairs): (connector, pairs)
                for connector, pairs in connector_pairs.items()
            }
            for future in as_completed(futures):
                connector, requested_pairs = futures[future]
                requested_set = {p.upper() for p in requested_pairs}
                try:
                    result = future.result()
                    if "error" in result:
                        continue
                    for pair, price_data in result.items():
                        if pair == "error" or pair.upper() not in requested_set:
                            continue
                        if isinstance(price_data, dict):
                            price = price_data.get("mid_price") or price_data.get("price")
                            bid = price_data.get("best_bid")
                            ask = price_data.get("best_ask")
                        else:
                            price = price_data
                            bid = ask = None
                        if price and float(price) > 0:
                            prices.append({
                                "connector": connector,
                                "pair": pair,
                                "price": float(price),
                                "bid": float(bid) if bid else None,
                                "ask": float(ask) if ask else None,
                                "source": "cex",
                            })
                except Exception:
                    pass

    # ── DEX prices ──────────────────────────────────────────────────────────
    if args.dex:
        dex_prices = fetch_all_dex_prices(base_tokens, quote_tokens)
        prices.extend(dex_prices)
        if not dex_prices:
            print("  ⚠ No DEX prices returned (Gateway may be offline).", file=sys.stderr)

    if not prices:
        print("No prices retrieved from any source.", file=sys.stderr)
        sys.exit(1)

    # ── Filter outliers ─────────────────────────────────────────────────────
    prices.sort(key=lambda x: x["price"])
    if len(prices) >= 3:
        median_price = prices[len(prices) // 2]["price"]
        filtered_prices = [p for p in prices if abs(p["price"] - median_price) / median_price <= 0.20]
        outliers = [p for p in prices if p not in filtered_prices]
    else:
        filtered_prices = prices
        outliers = []

    # ── Arbitrage opportunities ─────────────────────────────────────────────
    opportunities = []
    for i, buy in enumerate(filtered_prices):
        for sell in filtered_prices[i + 1:]:
            spread = (sell["price"] - buy["price"]) / buy["price"] * 100
            if spread >= args.min_spread:
                opportunities.append({
                    "buy_connector": buy["connector"],
                    "buy_pair": buy["pair"],
                    "buy_price": buy["price"],
                    "sell_connector": sell["connector"],
                    "sell_pair": sell["pair"],
                    "sell_price": sell["price"],
                    "spread_pct": spread,
                    "spread_abs": sell["price"] - buy["price"],
                })
    opportunities.sort(key=lambda x: x["spread_pct"], reverse=True)

    # ── Output ───────────────────────────────────────────────────────────────
    if args.json:
        print(json.dumps({
            "base_tokens": base_tokens,
            "quote_tokens": quote_tokens,
            "prices": filtered_prices,
            "outliers": outliers,
            "opportunities": opportunities[:20],
        }, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  {'/'.join(base_tokens)} / {'/'.join(quote_tokens)} Arbitrage Scanner")
        if args.dex:
            print(f"  DEX: Jupiter (Solana mainnet-beta), Uniswap (Ethereum mainnet)")
        print(f"{'='*60}")

        if filtered_prices:
            low = filtered_prices[0]
            high = filtered_prices[-1]
            spread_pct = (high["price"] - low["price"]) / low["price"] * 100
            print(f"\n  Lowest:  {low['connector']:25} {format_price(low['price'])}")
            print(f"  Highest: {high['connector']:25} {format_price(high['price'])}")
            print(f"  Spread:  {spread_pct:.3f}% ({format_price(high['price'] - low['price'])})")
            print(f"  Sources: {len(filtered_prices)} prices from {len(set(p['connector'] for p in filtered_prices))} sources")

        if opportunities:
            print(f"\n  Top Arbitrage Opportunities:")
            print(f"  {'-'*56}")
            for i, opp in enumerate(opportunities[:5], 1):
                print(f"  {i}. Buy  {opp['buy_connector']:23} @ {format_price(opp['buy_price'])}")
                print(f"     Sell {opp['sell_connector']:23} @ {format_price(opp['sell_price'])}")
                print(f"     Profit: {opp['spread_pct']:.3f}% ({format_price(opp['spread_abs'])})")
                if i < min(5, len(opportunities)):
                    print()
        else:
            print(f"\n  No opportunities found with spread >= {args.min_spread}%")

        if outliers:
            print(f"\n  ⚠ {len(outliers)} outlier(s) excluded: ", end="")
            print(", ".join(f"{o['connector']} ({format_price(o['price'])})" for o in outliers[:3]))

        print()


if __name__ == "__main__":
    main()
