#!/bin/bash
# Close an LP position and collect all tokens/fees
#
# Usage:
#   ./close_lp_position.sh --id <executor_id>

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
    "usage": "./close_lp_position.sh --id <executor_id>",
    "tip": "Use ./list_lp_positions.sh to find executor IDs"
}
EOF
    exit 1
fi

# Get current position state first
POSITION=$(curl -s -u "$API_USER:$API_PASS" "$API_URL/executors/$EXECUTOR_ID")

if echo "$POSITION" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Position not found\", \"detail\": $POSITION}"
    exit 1
fi

# Extract position info before closing
CUSTOM_INFO=$(echo "$POSITION" | jq '.custom_info // {}')
BASE_AMOUNT=$(echo "$CUSTOM_INFO" | jq -r '.base_amount // 0')
QUOTE_AMOUNT=$(echo "$CUSTOM_INFO" | jq -r '.quote_amount // 0')
BASE_FEE=$(echo "$CUSTOM_INFO" | jq -r '.base_fee // 0')
QUOTE_FEE=$(echo "$CUSTOM_INFO" | jq -r '.quote_fee // 0')

# Stop executor (this closes the position)
REQUEST='{"keep_position": false}'
RESPONSE=$(curl -s -X POST \
    -u "$API_USER:$API_PASS" \
    -H "Content-Type: application/json" \
    -d "$REQUEST" \
    "$API_URL/executors/$EXECUTOR_ID/stop")

# Check for errors
if echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to close position\", \"detail\": $RESPONSE}"
    exit 1
fi

cat << EOF
{
    "action": "lp_position_closed",
    "message": "Successfully closed LP position",
    "executor_id": "$EXECUTOR_ID",
    "final_balances": {
        "base_amount": $BASE_AMOUNT,
        "quote_amount": $QUOTE_AMOUNT,
        "base_fee": $BASE_FEE,
        "quote_fee": $QUOTE_FEE,
        "total_value_note": "Tokens and fees have been returned to your wallet"
    },
    "response": $RESPONSE,
    "next_steps": [
        "Create new position: ./create_lp_position.sh ...",
        "Check wallet balance via Gateway"
    ]
}
EOF
