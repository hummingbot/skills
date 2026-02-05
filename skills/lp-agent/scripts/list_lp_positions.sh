#!/bin/bash
# List all LP executor positions
#
# Usage:
#   ./list_lp_positions.sh                    # List all LP positions
#   ./list_lp_positions.sh --status RUNNING   # Filter by status
#   ./list_lp_positions.sh --connector meteora # Filter by connector

set -e

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do [ -f "$f" ] && source "$f" && break; done
API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

# Defaults
STATUS=""
CONNECTOR=""
PAIR=""
LIMIT=50

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --status) STATUS="$2"; shift 2 ;;
        --connector) CONNECTOR="$2"; shift 2 ;;
        --pair) PAIR="$2"; shift 2 ;;
        --limit) LIMIT="$2"; shift 2 ;;
        --api-url) API_URL="$2"; shift 2 ;;
        --api-user) API_USER="$2"; shift 2 ;;
        --api-pass) API_PASS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Build filter request
FILTER=$(jq -n \
    --argjson limit "$LIMIT" \
    '{
        executor_types: ["lp_executor"],
        limit: $limit
    }')

if [ -n "$STATUS" ]; then
    FILTER=$(echo "$FILTER" | jq --arg status "$STATUS" '. + {status: $status}')
fi

if [ -n "$CONNECTOR" ]; then
    # Handle both "meteora" and "meteora/clmm" formats
    if [[ "$CONNECTOR" != *"/"* ]]; then
        CONNECTOR="$CONNECTOR/clmm"
    fi
    FILTER=$(echo "$FILTER" | jq --arg connector "$CONNECTOR" '. + {connector_names: [$connector]}')
fi

if [ -n "$PAIR" ]; then
    FILTER=$(echo "$FILTER" | jq --arg pair "$PAIR" '. + {trading_pairs: [$pair]}')
fi

# Fetch executors
RESPONSE=$(curl -s -X POST \
    -u "$API_USER:$API_PASS" \
    -H "Content-Type: application/json" \
    -d "$FILTER" \
    "$API_URL/executors/search")

# Check for errors
if echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to list LP positions\", \"detail\": $RESPONSE}"
    exit 1
fi

# Extract positions and format
POSITIONS=$(echo "$RESPONSE" | jq '.data // []')
TOTAL=$(echo "$RESPONSE" | jq '.pagination.total_count // 0')

# Summarize positions
RUNNING_COUNT=$(echo "$POSITIONS" | jq '[.[] | select(.status == "RUNNING")] | length')
IN_RANGE_COUNT=$(echo "$POSITIONS" | jq '[.[] | select(.custom_info.state == "IN_RANGE")] | length')
OUT_OF_RANGE_COUNT=$(echo "$POSITIONS" | jq '[.[] | select(.custom_info.state == "OUT_OF_RANGE")] | length')

cat << EOF
{
    "action": "list_lp_positions",
    "summary": {
        "total": $TOTAL,
        "running": $RUNNING_COUNT,
        "in_range": $IN_RANGE_COUNT,
        "out_of_range": $OUT_OF_RANGE_COUNT
    },
    "filters": {
        "status": $([ -n "$STATUS" ] && echo "\"$STATUS\"" || echo "null"),
        "connector": $([ -n "$CONNECTOR" ] && echo "\"$CONNECTOR\"" || echo "null"),
        "pair": $([ -n "$PAIR" ] && echo "\"$PAIR\"" || echo "null")
    },
    "positions": $POSITIONS,
    "next_steps": [
        "Get position details: ./get_lp_position.sh --id <executor_id>",
        "Rebalance out-of-range: ./rebalance_position.sh --id <executor_id>",
        "Close position: ./close_lp_position.sh --id <executor_id>"
    ]
}
EOF
