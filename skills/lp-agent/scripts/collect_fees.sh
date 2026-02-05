#!/bin/bash
# Collect fees from an LP position without closing it
#
# Usage:
#   ./collect_fees.sh --id <executor_id>
#
# Note: This collects accumulated trading fees while keeping the position open.

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
    "usage": "./collect_fees.sh --id <executor_id>",
    "tip": "Use ./list_lp_positions.sh to find executor IDs"
}
EOF
    exit 1
fi

# Get position info first
POSITION=$(curl -s -u "$API_USER:$API_PASS" "$API_URL/executors/$EXECUTOR_ID")

if echo "$POSITION" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Position not found\", \"detail\": $POSITION}"
    exit 1
fi

# Extract position details
CUSTOM_INFO=$(echo "$POSITION" | jq '.custom_info // {}')
POSITION_ADDRESS=$(echo "$CUSTOM_INFO" | jq -r '.position_address // ""')
CONNECTOR=$(echo "$POSITION" | jq -r '.connector_name // "meteora/clmm"')
NETWORK=$(echo "$POSITION" | jq -r '.network // "solana-mainnet-beta"')

# Extract connector name without /clmm suffix for API call
CONNECTOR_BASE=$(echo "$CONNECTOR" | cut -d'/' -f1)

if [ -z "$POSITION_ADDRESS" ] || [ "$POSITION_ADDRESS" = "null" ]; then
    cat << EOF
{
    "error": "Position address not found",
    "message": "Cannot collect fees - position address not available",
    "executor_id": "$EXECUTOR_ID",
    "suggestion": "Position may still be opening. Wait and try again."
}
EOF
    exit 1
fi

# Current fees before collection
BASE_FEE_BEFORE=$(echo "$CUSTOM_INFO" | jq -r '.base_fee // 0')
QUOTE_FEE_BEFORE=$(echo "$CUSTOM_INFO" | jq -r '.quote_fee // 0')

# Call Gateway to collect fees
COLLECT_REQUEST=$(jq -n \
    --arg connector "$CONNECTOR_BASE" \
    --arg network "$NETWORK" \
    --arg position "$POSITION_ADDRESS" \
    '{
        connector: $connector,
        network: $network,
        position_address: $position
    }')

RESPONSE=$(curl -s -X POST \
    -u "$API_USER:$API_PASS" \
    -H "Content-Type: application/json" \
    -d "$COLLECT_REQUEST" \
    "$API_URL/gateway/clmm/collect-fees")

# Check for errors
if echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to collect fees\", \"detail\": $RESPONSE, \"request\": $COLLECT_REQUEST}"
    exit 1
fi

# Extract collected amounts
BASE_COLLECTED=$(echo "$RESPONSE" | jq -r '.base_amount // .base_fee // 0')
QUOTE_COLLECTED=$(echo "$RESPONSE" | jq -r '.quote_amount // .quote_fee // 0')
TX_HASH=$(echo "$RESPONSE" | jq -r '.transaction_hash // .txHash // "pending"')

cat << EOF
{
    "action": "fees_collected",
    "message": "Successfully collected LP fees",
    "executor_id": "$EXECUTOR_ID",
    "position_address": "$POSITION_ADDRESS",
    "fees_collected": {
        "base_fee": $BASE_COLLECTED,
        "quote_fee": $QUOTE_COLLECTED
    },
    "transaction_hash": "$TX_HASH",
    "response": $RESPONSE,
    "next_steps": [
        "Check updated position: ./get_lp_position.sh --id $EXECUTOR_ID",
        "Close position when ready: ./close_lp_position.sh --id $EXECUTOR_ID"
    ]
}
EOF
