#!/bin/bash
# Get comprehensive portfolio overview with balances, positions, and orders
# Usage: ./get_overview.sh [--account NAME] [--connector NAME] [--no-balances] [--no-positions] [--no-orders]

set -e

API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

ACCOUNT=""
CONNECTOR=""
INCLUDE_BALANCES=true
INCLUDE_POSITIONS=true
INCLUDE_ORDERS=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --account) ACCOUNT="$2"; shift 2 ;;
        --connector) CONNECTOR="$2"; shift 2 ;;
        --no-balances) INCLUDE_BALANCES=false; shift ;;
        --no-positions) INCLUDE_POSITIONS=false; shift ;;
        --no-orders) INCLUDE_ORDERS=false; shift ;;
        --api-url) API_URL="$2"; shift 2 ;;
        --api-user) API_USER="$2"; shift 2 ;;
        --api-pass) API_PASS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Build filter request
FILTER_REQUEST='{}'
if [ -n "$ACCOUNT" ]; then
    FILTER_REQUEST=$(echo "$FILTER_REQUEST" | jq --arg acc "$ACCOUNT" '. + {account_names: [$acc]}')
fi
if [ -n "$CONNECTOR" ]; then
    FILTER_REQUEST=$(echo "$FILTER_REQUEST" | jq --arg conn "$CONNECTOR" '. + {connector_names: [$conn]}')
fi

# Initialize results
BALANCES="{}"
POSITIONS="[]"
ORDERS="[]"

# Fetch balances
if [ "$INCLUDE_BALANCES" = true ]; then
    BALANCES=$(curl -s -X POST \
        -u "$API_USER:$API_PASS" \
        -H "Content-Type: application/json" \
        -d "$FILTER_REQUEST" \
        "$API_URL/portfolio/state" 2>/dev/null || echo '{}')
fi

# Fetch positions (for perpetual connectors)
if [ "$INCLUDE_POSITIONS" = true ]; then
    # Get positions from executors endpoint
    POSITIONS=$(curl -s -X GET \
        -u "$API_USER:$API_PASS" \
        "$API_URL/executors/positions/summary" 2>/dev/null || echo '[]')
fi

# Fetch active orders
if [ "$INCLUDE_ORDERS" = true ]; then
    # Search for active orders
    ORDER_REQUEST='{"status": ["OPEN", "PENDING"], "limit": 50}'
    ORDERS=$(curl -s -X POST \
        -u "$API_USER:$API_PASS" \
        -H "Content-Type: application/json" \
        -d "$ORDER_REQUEST" \
        "$API_URL/trading/search-orders/" 2>/dev/null || echo '{"data": []}')
    ORDERS=$(echo "$ORDERS" | jq '.data // []')
fi

# Build overview response
cat << EOF
{
    "overview": {
        "timestamp": $(date +%s),
        "filters": {
            "account": $([ -n "$ACCOUNT" ] && echo "\"$ACCOUNT\"" || echo "null"),
            "connector": $([ -n "$CONNECTOR" ] && echo "\"$CONNECTOR\"" || echo "null")
        }
    },
    "balances": $BALANCES,
    "positions": $POSITIONS,
    "active_orders": $ORDERS,
    "summary": {
        "has_balances": $([ "$BALANCES" != "{}" ] && echo "true" || echo "false"),
        "position_count": $(echo "$POSITIONS" | jq 'if type == "array" then length else 0 end'),
        "order_count": $(echo "$ORDERS" | jq 'if type == "array" then length else 0 end')
    }
}
EOF
