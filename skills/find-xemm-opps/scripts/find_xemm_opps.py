#!/usr/bin/env python3
"""
Find Cross-Exchange Market Making (XEMM) opportunities.

XEMM involves simultaneously quoting on one exchange while hedging on another.
The best opportunities exist where:
  - A mid-price difference exists between two exchanges
  - One exchange has thin liquidity (wide spread, shallow book) — the "maker" side
  - Another has deep liquidity and tight spread — the "taker/hedge" side

Usage:
    # Basic scan for SOL-USDT xemm opportunities
    python find_xemm_opps.py --base SOL --quote USDT

    # Include fungible tokens
    python find_xemm_opps.py --base ETH,WETH --quote USDT,USDC

    # Filter to specific connectors
    python find_xemm_opps.py --base BTC --quote USDT --connectors binance,kraken,coinbase

    # Adjust order book depth (default: 20)
    python find_xemm_opps.py --base SOL --quote USDC --depth 10

    # Minimum mid-price spread to show (default: 0.0)
    python find_xemm_opps.py --base ETH --quote USDC --min-spread 0.05

Notes:
    - btc_markets is excluded by default (Australian residents only).
    - ndax is excluded by default (Canadian residents only).

Environment:
    HUMMINGBOT_API_URL  - Hummingbot API base URL (default: http://localhost:8000)
    API_USER            - API username (default: admin)
    API_PASS            - API password (default: admin)
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


# ─── Regional restrictions ────────────────────────────────────────────────────

RESTRICTED_CONNECTORS = {
    "btc_markets",  # Australian residents only
    "ndax",         # Canadian residents only
}


# ─── Environment / config ─────────────────────────────────────────────────────

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
    }


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def api_request(method, endpoint, data=None, timeout=30):
    config = get_api_config()
    url = f"{config['url']}{endpoint}"
    creds = base64.b64encode(f"{config['user']}:{config['password']}".encode()).decode()
    headers = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"HTTP {e.code}: {error_body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection failed: {e.reason}")


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


def init_order_book(connector, trading_pair, timeout=15):
    """Initialize order book tracker for a trading pair."""
    try:
        api_request("POST", "/market-data/trading-pair/add", {
            "connector_name": connector,
            "trading_pair": trading_pair,
            "timeout": timeout,
        }, timeout=timeout + 5)
        return True
    except RuntimeError:
        return False


def fetch_order_book(connector, trading_pair, depth=20):
    """Initialize order book tracker then fetch snapshot."""
    import time
    # Initialize feed if not already running
    init_order_book(connector, trading_pair)
    time.sleep(1)  # brief wait for snapshot to populate
    try:
        result = api_request("POST", "/market-data/order-book", {
            "connector_name": connector,
            "trading_pair": trading_pair,
            "depth": depth,
        }, timeout=20)
        return result
    except RuntimeError as e:
        return {"error": str(e)}


# ─── XEMM analysis ────────────────────────────────────────────────────────────

def analyze_order_book(ob):
    """
    Compute key metrics from an order book snapshot.

    Returns dict with:
      mid_price      - mid between best bid and best ask
      spread_pct     - bid-ask spread as % of mid
      bid_depth      - total quote value of top-N bids (price * qty)
      ask_depth      - total base value of top-N asks (qty)
      bid_ask_ratio  - bid_depth / ask_depth (>1 = more buy pressure)
      best_bid       - best bid price
      best_ask       - best ask price
    """
    bids = ob.get("bids", [])
    asks = ob.get("asks", [])

    if not bids or not asks:
        return None

    # Entries are either [price, qty] lists or {"price": x, "amount": y} dicts
    def get_price(entry):
        return float(entry["price"] if isinstance(entry, dict) else entry[0])

    def get_amount(entry):
        return float(entry["amount"] if isinstance(entry, dict) else entry[1])

    best_bid = get_price(bids[0])
    best_ask = get_price(asks[0])

    if best_bid <= 0 or best_ask <= 0 or best_ask <= best_bid:
        return None

    mid = (best_bid + best_ask) / 2
    spread_pct = (best_ask - best_bid) / mid * 100

    # Total value depth (in quote currency)
    bid_depth = sum(get_price(b) * get_amount(b) for b in bids)
    ask_depth = sum(get_price(a) * get_amount(a) for a in asks)

    ratio = bid_depth / ask_depth if ask_depth > 0 else 0

    return {
        "mid_price": mid,
        "spread_pct": spread_pct,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "bid_depth": bid_depth,
        "ask_depth": ask_depth,
        "bid_ask_ratio": ratio,
        "bid_levels": len(bids),
        "ask_levels": len(asks),
    }


def score_xemm_opportunity(maker, taker):
    """
    Score a potential XEMM pair (maker exchange + taker/hedge exchange).

    Best XEMM setup:
      - maker: wide spread (room to quote), thin book (less competition)
      - taker: tight spread (cheap to hedge), deep book (can fill hedge)
      - significant mid-price difference between them

    Returns a score (higher = better opportunity).
    """
    mid_diff_pct = abs(taker["metrics"]["mid_price"] - maker["metrics"]["mid_price"]) \
                   / maker["metrics"]["mid_price"] * 100

    # Spread advantage: wide maker spread relative to taker spread
    spread_ratio = maker["metrics"]["spread_pct"] / max(taker["metrics"]["spread_pct"], 0.001)

    # Depth advantage: taker has deeper book (better hedge liquidity)
    taker_total = taker["metrics"]["bid_depth"] + taker["metrics"]["ask_depth"]
    maker_total = maker["metrics"]["bid_depth"] + maker["metrics"]["ask_depth"]
    depth_ratio = taker_total / max(maker_total, 1)

    score = mid_diff_pct * 3 + spread_ratio + (depth_ratio ** 0.5)
    return score, mid_diff_pct, spread_ratio, depth_ratio


# ─── Formatting ───────────────────────────────────────────────────────────────

def fmt_price(p):
    if p >= 1000:
        return f"${p:,.2f}"
    elif p >= 1:
        return f"${p:.4f}"
    else:
        return f"${p:.8f}"


def fmt_depth(d):
    if d >= 1_000_000:
        return f"${d/1_000_000:.2f}M"
    elif d >= 1_000:
        return f"${d/1_000:.1f}K"
    else:
        return f"${d:.2f}"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Find Cross-Exchange Market Making (XEMM) opportunities"
    )
    parser.add_argument("--base", required=True, help="Base token(s), comma-separated")
    parser.add_argument("--quote", required=True, help="Quote token(s), comma-separated")
    parser.add_argument("--connectors", help="Filter to specific connectors, comma-separated")
    parser.add_argument("--depth", type=int, default=20, help="Order book depth (default: 20)")
    parser.add_argument("--min-spread", type=float, default=0.0,
                        help="Minimum mid-price spread %% between exchanges to show (default: 0.0)")
    parser.add_argument("--include-btc-markets", action="store_true", default=False,
                        help="Include btc_markets (Australian residents only)")
    parser.add_argument("--include-ndax", action="store_true", default=False,
                        help="Include ndax (Canadian residents only)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    base_tokens = [t.strip() for t in args.base.split(",")]
    quote_tokens = [t.strip() for t in args.quote.split(",")]

    # ── Connectors ──────────────────────────────────────────────────────────
    if args.connectors:
        connectors = [c.strip() for c in args.connectors.split(",")]
    else:
        connectors = get_available_connectors()
        if not connectors:
            print("Error: No connectors available. Check API connection.", file=sys.stderr)
            sys.exit(1)

    # Filter restricted
    restricted = set(RESTRICTED_CONNECTORS)
    if args.include_btc_markets:
        restricted.discard("btc_markets")
    if args.include_ndax:
        restricted.discard("ndax")
    connectors = [c for c in connectors if c not in restricted]

    # ── Find matching pairs ─────────────────────────────────────────────────
    connector_pairs = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_connector_trading_pairs, c): c for c in connectors}
        for future in as_completed(futures):
            connector = futures[future]
            try:
                matching = find_matching_pairs(future.result(), base_tokens, quote_tokens)
                if matching:
                    connector_pairs[connector] = matching[0]  # use first match per connector
            except Exception:
                pass

    if len(connector_pairs) < 2:
        print(f"Need at least 2 connectors with matching pairs. Found {len(connector_pairs)}.",
              file=sys.stderr)
        sys.exit(1)

    # ── Fetch order books in parallel ───────────────────────────────────────
    print(f"Fetching order books (depth={args.depth}) from {len(connector_pairs)} connectors...",
          file=sys.stderr)

    books = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_order_book, c, pair, args.depth): c
            for c, pair in connector_pairs.items()
        }
        for future in as_completed(futures):
            connector = futures[future]
            try:
                ob = future.result()
                if "error" not in ob:
                    metrics = analyze_order_book(ob)
                    if metrics:
                        books[connector] = {
                            "pair": connector_pairs[connector],
                            "metrics": metrics,
                            "raw": ob,
                        }
            except Exception:
                pass

    if len(books) < 2:
        print(f"Got order books from only {len(books)} connector(s). Need at least 2.",
              file=sys.stderr)
        sys.exit(1)

    # ── Score all exchange pairs ─────────────────────────────────────────────
    connectors_with_books = list(books.keys())
    opportunities = []

    for i, maker_name in enumerate(connectors_with_books):
        for taker_name in connectors_with_books[i + 1:]:
            maker = books[maker_name]
            taker = books[taker_name]

            score, mid_diff_pct, spread_ratio, depth_ratio = score_xemm_opportunity(maker, taker)

            if mid_diff_pct < args.min_spread:
                continue

            # Determine which side is better as maker vs taker
            # Better maker: wider spread, shallower book
            # Better taker: tighter spread, deeper book
            maker_score = maker["metrics"]["spread_pct"] / max(
                maker["metrics"]["bid_depth"] + maker["metrics"]["ask_depth"], 1) * 1e6
            taker_score_b = taker["metrics"]["spread_pct"] / max(
                taker["metrics"]["bid_depth"] + taker["metrics"]["ask_depth"], 1) * 1e6

            if maker_score < taker_score_b:
                maker_name, taker_name = taker_name, maker_name
                maker, taker = taker, maker

            opportunities.append({
                "maker": maker_name,
                "maker_pair": maker["pair"],
                "maker_mid": maker["metrics"]["mid_price"],
                "maker_spread_pct": maker["metrics"]["spread_pct"],
                "maker_bid_depth": maker["metrics"]["bid_depth"],
                "maker_ask_depth": maker["metrics"]["ask_depth"],
                "maker_ratio": maker["metrics"]["bid_ask_ratio"],
                "taker": taker_name,
                "taker_pair": taker["pair"],
                "taker_mid": taker["metrics"]["mid_price"],
                "taker_spread_pct": taker["metrics"]["spread_pct"],
                "taker_bid_depth": taker["metrics"]["bid_depth"],
                "taker_ask_depth": taker["metrics"]["ask_depth"],
                "taker_ratio": taker["metrics"]["bid_ask_ratio"],
                "mid_diff_pct": mid_diff_pct,
                "spread_ratio": spread_ratio,
                "depth_ratio": depth_ratio,
                "score": score,
            })

    opportunities.sort(key=lambda x: x["score"], reverse=True)

    # ── Output ───────────────────────────────────────────────────────────────
    if args.json:
        print(json.dumps({
            "base_tokens": base_tokens,
            "quote_tokens": quote_tokens,
            "depth": args.depth,
            "books_fetched": len(books),
            "opportunities": opportunities[:20],
        }, indent=2))
        return

    pair_label = f"{'/'.join(base_tokens)} / {'/'.join(quote_tokens)}"
    print(f"\n{'='*68}")
    print(f"  XEMM Opportunities — {pair_label}")
    print(f"  Order book depth: {args.depth} levels | Sources: {len(books)}")
    print(f"{'='*68}\n")

    # Market overview table
    print(f"  {'Exchange':<22} {'Pair':<14} {'Mid':>10} {'Spread':>8} {'Bid Depth':>12} {'Ask Depth':>12} {'B/A':>6}")
    print(f"  {'-'*22} {'-'*14} {'-'*10} {'-'*8} {'-'*12} {'-'*12} {'-'*6}")
    sorted_books = sorted(books.items(), key=lambda x: x[1]["metrics"]["mid_price"])
    for name, book in sorted_books:
        m = book["metrics"]
        print(f"  {name:<22} {book['pair']:<14} {fmt_price(m['mid_price']):>10} "
              f"{m['spread_pct']:>7.3f}% {fmt_depth(m['bid_depth']):>12} "
              f"{fmt_depth(m['ask_depth']):>12} {m['bid_ask_ratio']:>6.2f}")

    if not opportunities:
        print(f"\n  No XEMM opportunities found with mid-spread >= {args.min_spread}%\n")
        return

    print(f"\n  Top XEMM Opportunities (MAKER → hedge on TAKER):")
    print(f"  {'-'*64}")

    for i, opp in enumerate(opportunities[:5], 1):
        print(f"\n  #{i}  Score: {opp['score']:.2f}")
        print(f"      MAKER  {opp['maker']:<22} {fmt_price(opp['maker_mid'])}  "
              f"spread {opp['maker_spread_pct']:.3f}%  "
              f"depth {fmt_depth(opp['maker_bid_depth'] + opp['maker_ask_depth'])}")
        print(f"      TAKER  {opp['taker']:<22} {fmt_price(opp['taker_mid'])}  "
              f"spread {opp['taker_spread_pct']:.3f}%  "
              f"depth {fmt_depth(opp['taker_bid_depth'] + opp['taker_ask_depth'])}")
        print(f"      Mid-price gap: {opp['mid_diff_pct']:.4f}%  |  "
              f"Spread ratio: {opp['spread_ratio']:.1f}x  |  "
              f"Depth ratio: {opp['depth_ratio']:.1f}x")

        # Liquidity imbalance note
        if opp["maker_ratio"] > 1.5:
            print(f"      ⚠  Maker book: buy-heavy (B/A={opp['maker_ratio']:.2f}) — ask side may be thin")
        elif opp["maker_ratio"] < 0.67:
            print(f"      ⚠  Maker book: sell-heavy (B/A={opp['maker_ratio']:.2f}) — bid side may be thin")

    # ── Suggested XEMM config for top opportunity ────────────────────────────
    if opportunities:
        top = opportunities[0]
        mid = top["maker_mid"]
        # Suggest 3 levels: min, mid, max profitability
        min_prof = max(top["taker_spread_pct"] / 100, 0.001)
        max_prof = min_prof * 3
        mid_prof = (min_prof + max_prof) / 2
        amount = 10  # placeholder

        print(f"  Suggested xemm_multiple_levels config for #{1}:")
        print(f"  {'─'*64}")
        print(f"    maker_connector:           {top['maker']}")
        print(f"    maker_trading_pair:        {top['maker_pair']}")
        print(f"    taker_connector:           {top['taker']}")
        print(f"    taker_trading_pair:        {top['taker_pair']}")
        print(f"    min_profitability:         {min_prof:.4f}  ({min_prof*100:.3f}%)")
        print(f"    max_profitability:         {max_prof:.4f}  ({max_prof*100:.3f}%)")
        print(f"    buy_levels_targets_amount: {min_prof:.4f},{amount}-{mid_prof:.4f},{amount*2}-{max_prof:.4f},{amount*3}")
        print(f"    sell_levels_targets_amount:{min_prof:.4f},{amount}-{mid_prof:.4f},{amount*2}-{max_prof:.4f},{amount*3}")
        print(f"    max_executors_imbalance:   1")
        print()


if __name__ == "__main__":
    main()
