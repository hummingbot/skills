#!/bin/bash
# List available CLMM pools
#
# Usage:
#   ./list_pools.sh                                    # List pools from default connector
#   ./list_pools.sh --connector meteora                # Specify connector
#   ./list_pools.sh --search SOL                       # Search for pools
#   ./list_pools.sh --sort volume --order desc         # Sort by volume
#   ./list_pools.sh --limit 20                         # Limit results

set -e

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do [ -f "$f" ] && source "$f" && break; done
API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

# Defaults
CONNECTOR="meteora"
NETWORK="solana-mainnet-beta"
SEARCH=""
SORT="volume"
ORDER="desc"
LIMIT=50
PAGE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --connector) CONNECTOR="$2"; shift 2 ;;
        --network) NETWORK="$2"; shift 2 ;;
        --search) SEARCH="$2"; shift 2 ;;
        --sort) SORT="$2"; shift 2 ;;
        --order) ORDER="$2"; shift 2 ;;
        --limit) LIMIT="$2"; shift 2 ;;
        --page) PAGE="$2"; shift 2 ;;
        --api-url) API_URL="$2"; shift 2 ;;
        --api-user) API_USER="$2"; shift 2 ;;
        --api-pass) API_PASS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Build query params
QUERY="connector=$CONNECTOR&page=$PAGE&limit=$LIMIT&sort_key=$SORT&order_by=$ORDER"
if [ -n "$SEARCH" ]; then
    QUERY="$QUERY&search_term=$SEARCH"
fi

# Fetch pools
RESPONSE=$(curl -s -u "$API_USER:$API_PASS" "$API_URL/gateway/clmm/pools?$QUERY")

# Check for errors
if echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to fetch pools\", \"detail\": $RESPONSE}"
    exit 1
fi

# Format output
POOLS=$(echo "$RESPONSE" | jq '.pools // []')
TOTAL=$(echo "$RESPONSE" | jq '.total // 0')

cat << EOF
{
    "action": "list_pools",
    "connector": "$CONNECTOR",
    "search": "$SEARCH",
    "sort": "$SORT",
    "order": "$ORDER",
    "page": $PAGE,
    "limit": $LIMIT,
    "total": $TOTAL,
    "pools": $POOLS,
    "next_steps": [
        "Get detailed pool info: ./get_pool_info.sh --connector $CONNECTOR --network $NETWORK --pool <pool_address>",
        "Create position: ./create_lp_position.sh --connector $CONNECTOR --network $NETWORK --pool <pool_address> --pair <PAIR> --quote-amount 100"
    ]
}
EOF
