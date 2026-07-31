#!/bin/bash
# Installs X402APIDataFeed into a Hummingbot instance.
# Usage: install_x402_feed.sh [HUMMINGBOT_ROOT]   (defaults to current directory)
set -e

HB_ROOT="${1:-.}"
SRC="https://raw.githubusercontent.com/GTCC777/hummingbot-x402/main"

echo "Installing X402APIDataFeed into: $HB_ROOT"

curl -fsSL "$SRC/x402_api_data_feed.py" -o "$HB_ROOT/x402_api_data_feed.py"
curl -fsSL "$SRC/x402_fetcher.py" -o "$HB_ROOT/x402_fetcher.py"

if [ -d "$HB_ROOT/scripts" ]; then
    curl -fsSL "$SRC/scripts/x402_funding_signal_example.py" \
        -o "$HB_ROOT/scripts/x402_funding_signal_example.py"
    echo "Example strategy: scripts/x402_funding_signal_example.py"
fi

echo "Installing the x402 SDK into the current Python environment..."
pip install "x402[evm,httpx]"

echo ""
echo "Done. Next steps:"
echo "  1. Fund a dedicated wallet with a few dollars of USDC on Base (no ETH needed)."
echo "  2. export X402_PRIVATE_KEY=0x<that wallet's key>"
echo "  3. In Hummingbot: start --script x402_funding_signal_example.py"
