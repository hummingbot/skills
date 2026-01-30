#!/bin/bash
# Get current portfolio state with balances
# Usage: ./get_state.sh [--account NAME] [--connector NAME] [--refresh] [--skip-gateway]

set -e

API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

ACCOUNT=""
CONNECTOR=""
REFRESH="false"
SKIP_GATEWAY="false"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --account) ACCOUNT="$2"; shift 2 ;;
        --connector) CONNECTOR="$2"; shift 2 ;;
        --refresh) REFRESH="true"; shift ;;
        --skip-gateway) SKIP_GATEWAY="true"; shift ;;
        --api-url) API_URL="$2"; shift 2 ;;
        --api-user) API_USER="$2"; shift 2 ;;
        --api-pass) API_PASS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Build request body
REQUEST=$(jq -n \
    --argjson refresh "$REFRESH" \
    --argjson skip_gateway "$SKIP_GATEWAY" \
    '{refresh: $refresh, skip_gateway: $skip_gateway}')

# Add optional filters
if [ -n "$ACCOUNT" ]; then
    REQUEST=$(echo "$REQUEST" | jq --arg acc "$ACCOUNT" '. + {account_names: [$acc]}')
fi

if [ -n "$CONNECTOR" ]; then
    REQUEST=$(echo "$REQUEST" | jq --arg conn "$CONNECTOR" '. + {connector_names: [$conn]}')
fi

# Fetch portfolio state
RESPONSE=$(curl -s -X POST \
    -u "$API_USER:$API_PASS" \
    -H "Content-Type: application/json" \
    -d "$REQUEST" \
    "$API_URL/portfolio/state")

# Check for error
if echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to get portfolio state\", \"detail\": $RESPONSE}"
    exit 1
fi

# Calculate total value from response
# Response format: {account: {connector: [{token, units, price, value, available_units}]}}
TOTAL_VALUE=$(echo "$RESPONSE" | jq '[.. | objects | .value? // 0 | select(. != null and . != 0)] | add // 0')

# Format balances for easy reading
BALANCES=$(echo "$RESPONSE" | jq '
    [to_entries[] |
        {
            account: .key,
            connectors: [.value | to_entries[] |
                {
                    connector: .key,
                    tokens: [.value[] |
                        {
                            token: .token,
                            units: .units,
                            available: .available_units,
                            price: .price,
                            value: .value
                        }
                    ] | sort_by(-.value)
                }
            ]
        }
    ]
')

cat << EOF
{
    "portfolio_state": $RESPONSE,
    "summary": {
        "total_value_usd": $TOTAL_VALUE,
        "accounts": $(echo "$RESPONSE" | jq 'keys')
    },
    "balances": $BALANCES
}
EOF
