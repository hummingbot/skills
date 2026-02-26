#!/usr/bin/env python3
"""
Quick Hummingbot status check: API health, running bots, portfolio snapshot.

Usage:
    python scripts/status.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from hbot_client import client, get_config, print_table


async def main():
    url, username, _ = get_config()

    print("Hummingbot Status")
    print("=" * 40)

    try:
        async with client() as c:
            print(f"✓ API running at {url}\n")

            # Running bots
            try:
                bots = await c.bots.get_active_bots()
                if bots:
                    print(f"Active Bots ({len(bots)}):")
                    rows = [
                        {
                            "name": b.get("bot_name", b.get("instance_name", "?")),
                            "status": b.get("status", "?"),
                            "script": b.get("script", b.get("strategy", "?")),
                        }
                        for b in bots
                    ]
                    print_table(rows, ["name", "status", "script"])
                else:
                    print("Active Bots: none")
            except Exception as e:
                print(f"  (could not fetch bots: {e})")

            print()

            # Portfolio snapshot
            try:
                summary = await c.portfolio.get_portfolio_summary()
                total = summary.get("total_value_usd", 0)
                print(f"Portfolio Total: ${total:,.2f}")
                dist = summary.get("distribution", {})
                if dist:
                    top = sorted(dist.items(), key=lambda x: x[1], reverse=True)[:5]
                    for token, pct in top:
                        print(f"  {token}: {pct:.1f}%")
            except Exception as e:
                print(f"  (could not fetch portfolio: {e})")

    except Exception as e:
        print(f"✗ Cannot connect to API at {url}")
        print(f"  Error: {e}")
        print(f"\n  Start the API: cd ~/hummingbot-api && make deploy")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
