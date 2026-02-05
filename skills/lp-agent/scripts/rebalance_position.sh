#!/bin/bash
# Rebalance an LP position - close current and open new position centered on current price
#
# Usage:
#   ./rebalance_position.sh --id <executor_id>
#   ./rebalance_position.sh --id <executor_id> --width 5.0  # Custom width
#
# Rebalancing strategy (same as LP Manager controller):
# - If price dropped below range (you're 100% base): Opens BASE-ONLY position above current price
# - If price rose above range (you're 100% quote): Opens QUOTE-ONLY position below current price
# - Collected fees are included in the new position

set -e

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do [ -f "$f" ] && source "$f" && break; done
API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

EXECUTOR_ID=""
WIDTH="5.0"  # Default position width %
ACCOUNT="master_account"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --id) EXECUTOR_ID="$2"; shift 2 ;;
        --width) WIDTH="$2"; shift 2 ;;
        --account) ACCOUNT="$2"; shift 2 ;;
        --api-url) API_URL="$2"; shift 2 ;;
        --api-user) API_USER="$2"; shift 2 ;;
        --api-pass) API_PASS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

if [ -z "$EXECUTOR_ID" ]; then
    cat << EOF
{
    "error": "Missing required parameter",
    "message": "Executor ID is required",
    "usage": "./rebalance_position.sh --id <executor_id>",
    "tip": "Use ./list_lp_positions.sh to find executor IDs"
}
EOF
    exit 1
fi

# Get current position state
POSITION=$(curl -s -u "$API_USER:$API_PASS" "$API_URL/executors/$EXECUTOR_ID")

if echo "$POSITION" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Position not found\", \"detail\": $POSITION}"
    exit 1
fi

# Extract position info
CONNECTOR=$(echo "$POSITION" | jq -r '.connector_name // "meteora/clmm"')
NETWORK=$(echo "$POSITION" | jq -r '.network // "solana-mainnet-beta"')
POOL=$(echo "$POSITION" | jq -r '.pool_address // ""')
PAIR=$(echo "$POSITION" | jq -r '.trading_pair // ""')
CUSTOM_INFO=$(echo "$POSITION" | jq '.custom_info // {}')

STATE=$(echo "$CUSTOM_INFO" | jq -r '.state // "unknown"')
CURRENT_PRICE=$(echo "$CUSTOM_INFO" | jq -r '.current_price // 0')
LOWER_PRICE=$(echo "$CUSTOM_INFO" | jq -r '.lower_price // 0')
UPPER_PRICE=$(echo "$CUSTOM_INFO" | jq -r '.upper_price // 0')
BASE_AMOUNT=$(echo "$CUSTOM_INFO" | jq -r '.base_amount // 0')
QUOTE_AMOUNT=$(echo "$CUSTOM_INFO" | jq -r '.quote_amount // 0')
BASE_FEE=$(echo "$CUSTOM_INFO" | jq -r '.base_fee // 0')
QUOTE_FEE=$(echo "$CUSTOM_INFO" | jq -r '.quote_fee // 0')

# Extract tokens from pair
BASE_TOKEN=$(echo "$PAIR" | cut -d'-' -f1)
QUOTE_TOKEN=$(echo "$PAIR" | cut -d'-' -f2)

# Determine rebalance direction
# If current price < lower_price: Price dropped below range (we're 100% base)
# If current price > upper_price: Price rose above range (we're 100% quote)

REBALANCE_DIRECTION="unknown"
NEW_BASE_AMOUNT="0"
NEW_QUOTE_AMOUNT="0"
NEW_SIDE=0

if (( $(echo "$CURRENT_PRICE < $LOWER_PRICE" | bc -l 2>/dev/null || echo "0") )); then
    # Price dropped below range - we're holding base tokens
    # Strategy: Create BASE-ONLY position ABOVE current price to sell as price recovers
    REBALANCE_DIRECTION="price_below_range"
    NEW_BASE_AMOUNT=$(echo "$BASE_AMOUNT + $BASE_FEE" | bc -l)
    NEW_QUOTE_AMOUNT="0"
    NEW_SIDE=2  # SELL (base-only)

    # Calculate new range: full width above current price
    WIDTH_FACTOR=$(echo "scale=6; $WIDTH / 100" | bc -l)
    NEW_LOWER_PRICE="$CURRENT_PRICE"
    NEW_UPPER_PRICE=$(echo "scale=6; $CURRENT_PRICE * (1 + $WIDTH_FACTOR)" | bc -l)

elif (( $(echo "$CURRENT_PRICE > $UPPER_PRICE" | bc -l 2>/dev/null || echo "0") )); then
    # Price rose above range - we're holding quote tokens
    # Strategy: Create QUOTE-ONLY position BELOW current price to buy as price drops
    REBALANCE_DIRECTION="price_above_range"
    NEW_BASE_AMOUNT="0"
    NEW_QUOTE_AMOUNT=$(echo "$QUOTE_AMOUNT + $QUOTE_FEE" | bc -l)
    NEW_SIDE=1  # BUY (quote-only)

    # Calculate new range: full width below current price
    WIDTH_FACTOR=$(echo "scale=6; $WIDTH / 100" | bc -l)
    NEW_LOWER_PRICE=$(echo "scale=6; $CURRENT_PRICE * (1 - $WIDTH_FACTOR)" | bc -l)
    NEW_UPPER_PRICE="$CURRENT_PRICE"

else
    # Position is in range - no rebalance needed
    cat << EOF
{
    "action": "rebalance_skipped",
    "message": "Position is currently in range - no rebalance needed",
    "executor_id": "$EXECUTOR_ID",
    "state": "$STATE",
    "price_info": {
        "current_price": $CURRENT_PRICE,
        "lower_price": $LOWER_PRICE,
        "upper_price": $UPPER_PRICE
    },
    "suggestion": "Rebalance is only triggered when price moves outside the position range"
}
EOF
    exit 0
fi

# Step 1: Close current position
echo "Closing current position..." >&2
CLOSE_REQUEST='{"keep_position": false}'
CLOSE_RESPONSE=$(curl -s -X POST \
    -u "$API_USER:$API_PASS" \
    -H "Content-Type: application/json" \
    -d "$CLOSE_REQUEST" \
    "$API_URL/executors/$EXECUTOR_ID/stop")

if echo "$CLOSE_RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to close position for rebalance\", \"detail\": $CLOSE_RESPONSE}"
    exit 1
fi

# Wait a moment for position to close
sleep 2

# Step 2: Create new position
echo "Creating new rebalanced position..." >&2

# Build new executor config
NEW_CONFIG=$(jq -n \
    --arg type "lp_executor" \
    --arg connector "$CONNECTOR" \
    --arg pool "$POOL" \
    --arg pair "$PAIR" \
    --arg base_token "$BASE_TOKEN" \
    --arg quote_token "$QUOTE_TOKEN" \
    --arg base_amount "$NEW_BASE_AMOUNT" \
    --arg quote_amount "$NEW_QUOTE_AMOUNT" \
    --arg lower_price "$NEW_LOWER_PRICE" \
    --arg upper_price "$NEW_UPPER_PRICE" \
    --argjson side "$NEW_SIDE" \
    '{
        type: $type,
        connector_name: $connector,
        pool_address: $pool,
        trading_pair: $pair,
        base_token: $base_token,
        quote_token: $quote_token,
        base_amount: ($base_amount | tonumber),
        quote_amount: ($quote_amount | tonumber),
        lower_price: ($lower_price | tonumber),
        upper_price: ($upper_price | tonumber),
        side: $side,
        keep_position: false
    }')

NEW_REQUEST=$(jq -n \
    --argjson config "$NEW_CONFIG" \
    --arg account "$ACCOUNT" \
    '{executor_config: $config, account_name: $account}')

CREATE_RESPONSE=$(curl -s -X POST \
    -u "$API_USER:$API_PASS" \
    -H "Content-Type: application/json" \
    -d "$NEW_REQUEST" \
    "$API_URL/executors/")

if echo "$CREATE_RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to create rebalanced position\", \"detail\": $CREATE_RESPONSE, \"config\": $NEW_CONFIG}"
    exit 1
fi

NEW_EXECUTOR_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id // .executor_id // "unknown"')

cat << EOF
{
    "action": "position_rebalanced",
    "message": "Successfully rebalanced LP position",
    "old_position": {
        "executor_id": "$EXECUTOR_ID",
        "state": "$STATE",
        "lower_price": $LOWER_PRICE,
        "upper_price": $UPPER_PRICE,
        "base_amount": $BASE_AMOUNT,
        "quote_amount": $QUOTE_AMOUNT,
        "base_fee": $BASE_FEE,
        "quote_fee": $QUOTE_FEE
    },
    "rebalance_info": {
        "direction": "$REBALANCE_DIRECTION",
        "current_price": $CURRENT_PRICE,
        "strategy": $(if [ "$NEW_SIDE" = "2" ]; then echo '"BASE_ONLY (sell base as price recovers)"'; else echo '"QUOTE_ONLY (buy base as price drops)"'; fi)
    },
    "new_position": {
        "executor_id": "$NEW_EXECUTOR_ID",
        "lower_price": $NEW_LOWER_PRICE,
        "upper_price": $NEW_UPPER_PRICE,
        "base_amount": $NEW_BASE_AMOUNT,
        "quote_amount": $NEW_QUOTE_AMOUNT,
        "side": $NEW_SIDE,
        "width_pct": $WIDTH
    },
    "next_steps": [
        "Monitor new position: ./get_lp_position.sh --id $NEW_EXECUTOR_ID",
        "Set up auto-rebalance: ./auto_rebalance.sh --id $NEW_EXECUTOR_ID --delay 60"
    ]
}
EOF
