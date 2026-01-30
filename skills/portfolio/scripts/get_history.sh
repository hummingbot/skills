#!/bin/bash
# Get portfolio history with interval sampling
# Usage: ./get_history.sh [--days N] [--interval 1h] [--account NAME] [--connector NAME]

set -e

API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

DAYS=7
INTERVAL="1h"
ACCOUNT=""
CONNECTOR=""
LIMIT=100

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --days) DAYS="$2"; shift 2 ;;
        --interval) INTERVAL="$2"; shift 2 ;;
        --account) ACCOUNT="$2"; shift 2 ;;
        --connector) CONNECTOR="$2"; shift 2 ;;
        --limit) LIMIT="$2"; shift 2 ;;
        --api-url) API_URL="$2"; shift 2 ;;
        --api-user) API_USER="$2"; shift 2 ;;
        --api-pass) API_PASS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Calculate start_time (N days ago in seconds)
START_TIME=$(($(date +%s) - (DAYS * 86400)))

# Build request body
REQUEST=$(jq -n \
    --argjson start_time "$START_TIME" \
    --arg interval "$INTERVAL" \
    --argjson limit "$LIMIT" \
    '{start_time: $start_time, interval: $interval, limit: $limit}')

if [ -n "$ACCOUNT" ]; then
    REQUEST=$(echo "$REQUEST" | jq --arg acc "$ACCOUNT" '. + {account_names: [$acc]}')
fi

if [ -n "$CONNECTOR" ]; then
    REQUEST=$(echo "$REQUEST" | jq --arg conn "$CONNECTOR" '. + {connector_names: [$conn]}')
fi

# Fetch history
RESPONSE=$(curl -s -X POST \
    -u "$API_USER:$API_PASS" \
    -H "Content-Type: application/json" \
    -d "$REQUEST" \
    "$API_URL/portfolio/history")

# Check for error
if echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to get portfolio history\", \"detail\": $RESPONSE}"
    exit 1
fi

# Add query metadata
cat << EOF
{
    "query": {
        "days": $DAYS,
        "interval": "$INTERVAL",
        "start_time": $START_TIME
    },
    "response": $RESPONSE
}
EOF
