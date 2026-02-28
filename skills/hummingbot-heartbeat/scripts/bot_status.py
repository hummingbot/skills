#!/usr/bin/env python3
"""
Hummingbot heartbeat status check.
Checks: API, Gateway, active bots/controllers, executors, portfolio.
Outputs a formatted status report.

Usage:
    python bot_status.py
    python bot_status.py --json
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import base64
import datetime


def get_env():
    api_url = os.environ.get("HUMMINGBOT_API_URL", "http://localhost:8000")
    api_user = os.environ.get("API_USER", "admin")
    api_pass = os.environ.get("API_PASS", "admin")
    return api_url, api_user, api_pass


def api_request(path, method="GET", data=None):
    api_url, api_user, api_pass = get_env()
    url = f"{api_url}{path}"
    token = base64.b64encode(f"{api_user}:{api_pass}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data or {}).encode() if data is not None or method == "POST" else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.load(resp), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, str(e)


def check_gateway():
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=gateway", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=5
        )
        lines = [l for l in result.stdout.strip().splitlines() if "gateway" in l.lower()]
        if lines:
            status = lines[0].split("\t")[1] if "\t" in lines[0] else "Up"
            return True, status
        return False, "Not running"
    except FileNotFoundError:
        return None, "Docker not available"
    except Exception as e:
        return False, str(e)


def format_value(v):
    if v >= 1000:
        return f"${v:,.2f}"
    elif v >= 1:
        return f"${v:.2f}"
    else:
        return f"${v:.4f}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    now = datetime.datetime.now().strftime("%b %d, %Y %I:%M %p")
    result = {"timestamp": now, "components": {}, "portfolio": [], "bots": [], "executors": []}

    # 1. API status
    api_data, api_err = api_request("/")
    api_up = api_data is not None
    api_version = api_data.get("version", "?") if api_up else None
    result["components"]["api"] = {"up": api_up, "version": api_version, "error": api_err}

    # 2. Gateway status
    gw_up, gw_status = check_gateway()
    result["components"]["gateway"] = {"up": gw_up, "status": gw_status}

    # 3. Bots / controllers
    bots_data, _ = api_request("/bot-orchestration/status")
    bots = []
    if bots_data:
        for bot_id, bot_info in (bots_data.get("bots", {}) or {}).items():
            controllers = bot_info.get("controllers", {})
            bots.append({
                "id": bot_id[:12],
                "controllers": list(controllers.keys()),
                "pnl": bot_info.get("global_pnl_quote", 0),
            })
    result["bots"] = bots

    # 4. Executors
    exec_data, _ = api_request("/executors/search", method="POST", data={})
    executors = exec_data.get("data", []) if exec_data else []
    active_executors = [e for e in executors if e.get("status") not in ("CLOSED", "FAILED")]
    result["executors"] = [
        {"id": e.get("id", "?")[:12], "type": e.get("type", "?"), "status": e.get("status", "?")}
        for e in active_executors
    ]

    # 5. Portfolio
    portfolio_data, _ = api_request("/portfolio/history", method="POST", data={})
    if portfolio_data and portfolio_data.get("data"):
        latest = portfolio_data["data"][-1].get("state", {})
        tokens = []
        for account, networks in latest.items():
            for network, balances in networks.items():
                for b in balances:
                    if b.get("value", 0) > 0.01:
                        tokens.append({
                            "token": b["token"],
                            "units": b["units"],
                            "price": b.get("price", 0),
                            "value": b.get("value", 0),
                        })
        tokens.sort(key=lambda x: x["value"], reverse=True)
        result["portfolio"] = tokens

    if args.json:
        print(json.dumps(result, indent=2))
        return

    # --- Formatted output ---
    lines = [f"🤖 Hummingbot Status — {now}", ""]

    # Components
    api_str = f"✅ Up (v{api_version})" if api_up else f"❌ Down ({api_err})"
    gw_str = f"✅ {gw_status}" if gw_up else ("⚠️ Docker not available" if gw_up is None else f"❌ {gw_status}")
    lines.append("**Infrastructure**")
    lines.append(f"  API:     {api_str}")
    lines.append(f"  Gateway: {gw_str}")
    lines.append("")

    # Bots
    if bots:
        lines.append("**Active Bots**")
        for b in bots:
            controllers = ", ".join(b["controllers"]) or "none"
            pnl = f"PnL: {b['pnl']:+.4f}" if b["pnl"] else ""
            lines.append(f"  • {b['id']} [{controllers}] {pnl}")
    else:
        lines.append("**Active Bots:** none")
    lines.append("")

    # Executors
    if result["executors"]:
        lines.append("**Active Executors**")
        for e in result["executors"]:
            lines.append(f"  • {e['id']} {e['type']} [{e['status']}]")
    else:
        lines.append("**Active Executors:** none")
    lines.append("")

    # Portfolio
    if result["portfolio"]:
        total = sum(t["value"] for t in result["portfolio"])
        lines.append(f"**Portfolio** (total: {format_value(total)})")
        lines.append(f"  {'Token':<12} {'Units':>14} {'Price':>10} {'Value':>10}")
        lines.append(f"  {'-'*12} {'-'*14} {'-'*10} {'-'*10}")
        for t in result["portfolio"]:
            units_str = f"{t['units']:,.4f}" if t["units"] < 1000 else f"{t['units']:,.2f}"
            price_str = f"${t['price']:.6f}" if t["price"] < 0.01 else f"${t['price']:.4f}"
            value_str = format_value(t["value"])
            lines.append(f"  {t['token']:<12} {units_str:>14} {price_str:>10} {value_str:>10}")
    else:
        lines.append("**Portfolio:** no data")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
