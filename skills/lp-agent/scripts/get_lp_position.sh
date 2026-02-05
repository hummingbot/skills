#!/bin/bash
# Get detailed information about a specific LP position
#
# Usage:
#   ./get_lp_position.sh --id <executor_id>

set -e

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do [ -f "$f" ] && source "$f" && break; done
API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

EXECUTOR_ID=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --id) EXECUTOR_ID="$2"; shift 2 ;;
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
    "usage": "./get_lp_position.sh --id <executor_id>",
    "tip": "Use ./list_lp_positions.sh to find executor IDs"
}
EOF
    exit 1
fi

# Fetch executor details
RESPONSE=$(curl -s -u "$API_USER:$API_PASS" "$API_URL/executors/$EXECUTOR_ID")

# Check for errors
if echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to get position details\", \"detail\": $RESPONSE}"
    exit 1
fi

# Extract key information
STATUS=$(echo "$RESPONSE" | jq -r '.status // "unknown"')
CUSTOM_INFO=$(echo "$RESPONSE" | jq '.custom_info // {}')
STATE=$(echo "$CUSTOM_INFO" | jq -r '.state // "unknown"')
POSITION_ADDRESS=$(echo "$CUSTOM_INFO" | jq -r '.position_address // "unknown"')
CURRENT_PRICE=$(echo "$CUSTOM_INFO" | jq -r '.current_price // 0')
LOWER_PRICE=$(echo "$CUSTOM_INFO" | jq -r '.lower_price // 0')
UPPER_PRICE=$(echo "$CUSTOM_INFO" | jq -r '.upper_price // 0')
BASE_AMOUNT=$(echo "$CUSTOM_INFO" | jq -r '.base_amount // 0')
QUOTE_AMOUNT=$(echo "$CUSTOM_INFO" | jq -r '.quote_amount // 0')
BASE_FEE=$(echo "$CUSTOM_INFO" | jq -r '.base_fee // 0')
QUOTE_FEE=$(echo "$CUSTOM_INFO" | jq -r '.quote_fee // 0')
OUT_OF_RANGE_SINCE=$(echo "$CUSTOM_INFO" | jq -r '.out_of_range_since // 0')

# Calculate time out of range if applicable
TIME_OUT_OF_RANGE="null"
if [ "$STATE" = "OUT_OF_RANGE" ] && [ "$OUT_OF_RANGE_SINCE" != "0" ] && [ "$OUT_OF_RANGE_SINCE" != "null" ]; then
    CURRENT_TIME=$(date +%s)
    TIME_OUT_OF_RANGE=$(echo "$CURRENT_TIME - $OUT_OF_RANGE_SINCE" | bc 2>/dev/null || echo "0")
fi

# Build price range visualization
RANGE_VIZ=""
if [ "$CURRENT_PRICE" != "0" ] && [ "$LOWER_PRICE" != "0" ] && [ "$UPPER_PRICE" != "0" ]; then
    if (( $(echo "$CURRENT_PRICE < $LOWER_PRICE" | bc -l 2>/dev/null || echo "0") )); then
        RANGE_VIZ="[PRICE] ◀─────|─────────────|  (below range)"
    elif (( $(echo "$CURRENT_PRICE > $UPPER_PRICE" | bc -l 2>/dev/null || echo "0") )); then
        RANGE_VIZ="|─────────────|─────▶ [PRICE]  (above range)"
    else
        # Calculate position within range
        RANGE_VIZ="|─────────●─────────|  (in range)"
    fi
fi

# Determine recommended actions
ACTIONS="[]"
if [ "$STATE" = "OUT_OF_RANGE" ]; then
    ACTIONS='["Consider rebalancing: ./rebalance_position.sh --id '"$EXECUTOR_ID"'", "Or wait for price to return to range"]'
elif [ "$STATE" = "IN_RANGE" ]; then
    ACTIONS='["Position is earning fees", "Collect fees: ./collect_fees.sh --id '"$EXECUTOR_ID"'"]'
elif [ "$STATUS" = "TERMINATED" ]; then
    ACTIONS='["Position is closed", "Create new position: ./create_lp_position.sh ..."]'
fi

cat << EOF
{
    "action": "get_lp_position",
    "executor_id": "$EXECUTOR_ID",
    "status": "$STATUS",
    "state": "$STATE",
    "position_address": "$POSITION_ADDRESS",
    "price_info": {
        "current_price": $CURRENT_PRICE,
        "lower_price": $LOWER_PRICE,
        "upper_price": $UPPER_PRICE,
        "range_visualization": "$RANGE_VIZ"
    },
    "balances": {
        "base_amount": $BASE_AMOUNT,
        "quote_amount": $QUOTE_AMOUNT,
        "base_fee": $BASE_FEE,
        "quote_fee": $QUOTE_FEE,
        "total_fees_collected": $(echo "$BASE_FEE + $QUOTE_FEE" | bc -l 2>/dev/null || echo "0")
    },
    "out_of_range": {
        "since_timestamp": $OUT_OF_RANGE_SINCE,
        "duration_seconds": $TIME_OUT_OF_RANGE
    },
    "full_response": $RESPONSE,
    "recommended_actions": $ACTIONS
}
EOF
