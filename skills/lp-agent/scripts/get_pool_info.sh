#!/bin/bash
# Get detailed information about a specific CLMM pool
#
# Usage:
#   ./get_pool_info.sh --connector meteora --network solana-mainnet-beta --pool <address>

set -e

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do [ -f "$f" ] && source "$f" && break; done
API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

# Defaults
CONNECTOR="meteora"
NETWORK="solana-mainnet-beta"
POOL=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --connector) CONNECTOR="$2"; shift 2 ;;
        --network) NETWORK="$2"; shift 2 ;;
        --pool) POOL="$2"; shift 2 ;;
        --api-url) API_URL="$2"; shift 2 ;;
        --api-user) API_USER="$2"; shift 2 ;;
        --api-pass) API_PASS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

if [ -z "$POOL" ]; then
    cat << EOF
{
    "error": "Missing required parameter",
    "message": "Pool address is required",
    "usage": "./get_pool_info.sh --connector meteora --network solana-mainnet-beta --pool <address>",
    "example": "./get_pool_info.sh --connector meteora --network solana-mainnet-beta --pool 2sf5Xxxxxxxxxxx"
}
EOF
    exit 1
fi

# Fetch pool info
RESPONSE=$(curl -s -u "$API_USER:$API_PASS" \
    "$API_URL/gateway/clmm/pool-info?connector=$CONNECTOR&network=$NETWORK&pool_address=$POOL")

# Check for errors
if echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to fetch pool info\", \"detail\": $RESPONSE}"
    exit 1
fi

# Extract key info
CURRENT_PRICE=$(echo "$RESPONSE" | jq -r '.current_price // "unknown"')
BASE_TOKEN=$(echo "$RESPONSE" | jq -r '.base_token // .token_a // "unknown"')
QUOTE_TOKEN=$(echo "$RESPONSE" | jq -r '.quote_token // .token_b // "unknown"')
TVL=$(echo "$RESPONSE" | jq -r '.tvl // "unknown"')
VOLUME_24H=$(echo "$RESPONSE" | jq -r '.volume_24h // "unknown"')
FEE_RATE=$(echo "$RESPONSE" | jq -r '.fee_rate // .fee_pct // "unknown"')

# Calculate suggested price ranges (5%, 10%, 20% width)
if [ "$CURRENT_PRICE" != "unknown" ] && [ "$CURRENT_PRICE" != "null" ]; then
    PRICE_NUM=$(echo "$CURRENT_PRICE" | bc -l 2>/dev/null || echo "0")
    if [ "$PRICE_NUM" != "0" ]; then
        RANGE_5_LOWER=$(echo "scale=6; $PRICE_NUM * 0.975" | bc -l)
        RANGE_5_UPPER=$(echo "scale=6; $PRICE_NUM * 1.025" | bc -l)
        RANGE_10_LOWER=$(echo "scale=6; $PRICE_NUM * 0.95" | bc -l)
        RANGE_10_UPPER=$(echo "scale=6; $PRICE_NUM * 1.05" | bc -l)
        RANGE_20_LOWER=$(echo "scale=6; $PRICE_NUM * 0.90" | bc -l)
        RANGE_20_UPPER=$(echo "scale=6; $PRICE_NUM * 1.10" | bc -l)
    fi
fi

cat << EOF
{
    "action": "get_pool_info",
    "connector": "$CONNECTOR",
    "network": "$NETWORK",
    "pool_address": "$POOL",
    "pool_info": $RESPONSE,
    "summary": {
        "trading_pair": "$BASE_TOKEN-$QUOTE_TOKEN",
        "current_price": $CURRENT_PRICE,
        "tvl": "$TVL",
        "volume_24h": "$VOLUME_24H",
        "fee_rate": "$FEE_RATE"
    },
    "suggested_ranges": {
        "tight_5pct": {
            "lower": ${RANGE_5_LOWER:-"null"},
            "upper": ${RANGE_5_UPPER:-"null"},
            "description": "5% width - higher fee capture, more rebalancing"
        },
        "medium_10pct": {
            "lower": ${RANGE_10_LOWER:-"null"},
            "upper": ${RANGE_10_UPPER:-"null"},
            "description": "10% width - balanced approach"
        },
        "wide_20pct": {
            "lower": ${RANGE_20_LOWER:-"null"},
            "upper": ${RANGE_20_UPPER:-"null"},
            "description": "20% width - less rebalancing, lower fee capture"
        }
    },
    "next_steps": [
        "Create position: ./create_lp_position.sh --connector $CONNECTOR --network $NETWORK --pool $POOL --pair $BASE_TOKEN-$QUOTE_TOKEN --quote-amount 100 --width 5.0"
    ]
}
EOF
