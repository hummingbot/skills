---
name: x402-data-feed
description: Wire pay-per-call x402 API endpoints into Hummingbot as price/signal data feeds. X402APIDataFeed pays HTTP 402 challenges in USDC on Base (gasless EIP-3009) with a hard per-call budget cap — use when a strategy needs an external signal (funding rates, spreads, macro series) without API keys or subscriptions.
license: Apache-2.0
metadata:
  author: GTCC777
---

# x402-data-feed

Add pay-per-call HTTP APIs to a Hummingbot instance as native price/signal feeds. `X402APIDataFeed` is a drop-in sibling of Hummingbot's stock `CustomAPIDataFeed` that transparently answers [x402](https://x402.org) HTTP 402 payment challenges in USDC on Base, so a strategy can buy exactly the data tick it needs (typically $0.01–$0.05/call) instead of holding a monthly data subscription. Works with any endpoint that speaks x402.

Source: [GTCC777/hummingbot-x402](https://github.com/GTCC777/hummingbot-x402) (Apache-2.0).

## Prerequisites

- A Hummingbot instance where you can add files (source install, or a mounted `scripts/` folder in Docker)
- A dedicated hot wallet holding a few dollars of **USDC on Base** — payments are gasless [EIP-3009](https://eips.ethereum.org/EIPS/eip-3009) transfer authorizations submitted by the seller's facilitator, so the wallet needs **no ETH**

## Installation

Run the install script from the Hummingbot root directory:

```bash
bash <(curl -s https://raw.githubusercontent.com/hummingbot/skills/main/skills/x402-data-feed/scripts/install_x402_feed.sh)
```

Or manually:

1. Copy the two feed files into the Hummingbot root (next to `scripts/`):

   ```bash
   curl -fsSLO https://raw.githubusercontent.com/GTCC777/hummingbot-x402/main/x402_api_data_feed.py
   curl -fsSLO https://raw.githubusercontent.com/GTCC777/hummingbot-x402/main/x402_fetcher.py
   ```

2. In the Hummingbot conda/venv environment:

   ```bash
   pip install "x402[evm,httpx]"
   ```

3. Export the paying wallet's private key:

   ```bash
   export X402_PRIVATE_KEY=0x...
   ```

## Quick Start

Use the feed inside any script strategy:

```python
import os
from decimal import Decimal
from x402_api_data_feed import X402APIDataFeed

feed = X402APIDataFeed(
    api_url="https://cryptopulse.theaslangroupllc.com/api/funding-check?coin=ETH",
    json_path="markets.0.funding_annualized_pct",  # dotted path into the JSON response
    private_key=os.environ["X402_PRIVATE_KEY"],
    max_price_usdc=Decimal("0.05"),                # refuse any challenge above this
    update_interval=60.0,                          # seconds between paid polls
)
feed.start()

# later, e.g. in on_tick():
if feed.is_ready:
    value = feed.get_price()   # Decimal
```

A complete runnable script strategy (polls an ETH perp funding-rate endpoint and logs the annualized rate) ships with the component:

```bash
curl -fsSL https://raw.githubusercontent.com/GTCC777/hummingbot-x402/main/scripts/x402_funding_signal_example.py -o scripts/x402_funding_signal_example.py
```

Then inside Hummingbot: `start --script x402_funding_signal_example.py`

## Parameters

| Parameter | Description |
|-----------|-------------|
| `api_url` | Any x402-payable GET endpoint |
| `json_path` | Dotted path to the numeric value, e.g. `"greeks.price"`, `"markets.0.mark_price"`; `""` for bare-number bodies |
| `private_key` | Key of the wallet holding USDC on Base |
| `max_price_usdc` | Hard per-call cap (default `0.10`) — the feed refuses any challenge above it |
| `update_interval` | Seconds between paid polls (default `60`) |

## Cost Math

Every poll is a paid call: **daily cost = (86400 / update_interval) × price per call**.

| Endpoint price | 60s polling | 300s polling | 3600s polling |
|---------------:|------------:|-------------:|--------------:|
| $0.02 | $28.80/day | $5.76/day | $0.48/day |
| $0.05 | $72.00/day | $14.40/day | $1.20/day |

Set `update_interval` to match how fresh the strategy actually needs the signal, and fund the wallet with only what you are willing to spend.

## Safety Notes

- **Budget cap.** `max_price_usdc` is enforced before signing anything — if the endpoint reprices above the cap, the fetch raises instead of paying. A repriced endpoint can never silently drain the wallet.
- **Health checks never pay.** `check_network()` probes unpaid and treats a `402` response as CONNECTED — for a paid endpoint that is the "alive" signal. Only `fetch_price()` spends.
- **Loud failures.** A missing `json_path` or non-numeric value raises with the available keys listed; the price is never silently zero.
- **Use a dedicated hot wallet** with a small USDC balance, not a main trading wallet.

## Example Endpoints

Any x402-payable endpoint works. The [PulseNetwork catalog](https://pulse.theaslangroupllc.com) has machine-payable endpoints useful as strategy inputs, for example:

| Endpoint | Price | `json_path` |
|----------|-------|-------------|
| `cryptopulse…/api/funding-check?coin=ETH` | $0.02 | `markets.0.funding_annualized_pct` |
| `cryptopulse…/api/funding-arb-scan` | $0.05 | `opportunities.0.spread_annualized_pct` |
| `macropulse…/api/macro/bls-series?series=cpi` | $0.02 | `series.0.yoy_pct_change` |

## Hummingbot v2.16

- **Compatibility:** verified against the `v2.16.0` tag — `X402APIDataFeed` uses the same core imports as the stock `CustomAPIDataFeed` that ships in 2.16 (`hummingbot.core.network_base`, `hummingbot.core.network_iterator`), so it should drop in unchanged.
- **hbot CLI:** the new non-interactive CLI pairs naturally with pay-per-call feeds — start a strategy headless from CI or cron (`hbot start --script x402_funding_signal_example.py`, then `hbot status --json`); the bot only spends while it runs, and `max_price_usdc` bounds the worst case.
- **Robinhood Chain:** v2.16 adds Robinhood Chain to Gateway (Uniswap AMM & CLMM on mainnet), where most tokens are fresh launchpad launches. A runnable pre-trade safety-gate example ships with the component — it pays $0.015 for a deterministic CLEAR / CAUTION / AVOID verdict (sell-simulation honeypot, taxes, owner privileges, LP lock, holder concentration) and keeps the gate closed on anything but CLEAR:

  ```bash
  curl -fsSL https://raw.githubusercontent.com/GTCC777/hummingbot-x402/main/scripts/x402_rh_chain_pretrade_check.py -o scripts/x402_rh_chain_pretrade_check.py
  ```

## Requirements

- Python 3.9+ (inside the Hummingbot environment)
- `x402[evm,httpx]` (official x402 SDK)
- USDC on Base in the paying wallet
