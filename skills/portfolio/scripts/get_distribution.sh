#!/bin/bash
# Get portfolio distribution by token
# Usage: ./get_distribution.sh [--account NAME] [--connector NAME]

set -e

# Load .env if present (check current dir, ~/.hummingbot/, ~/)
for f in .env ~/.hummingbot/.env ~/.env; do [ -f "$f" ] && source "$f" && break; done
API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

ACCOUNT=""
CONNECTOR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --account) ACCOUNT="$2"; shift 2 ;;
        --connector) CONNECTOR="$2"; shift 2 ;;
        --api-url) API_URL="$2"; shift 2 ;;
        --api-user) API_USER="$2"; shift 2 ;;
        --api-pass) API_PASS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Build request body
REQUEST='{}'

if [ -n "$ACCOUNT" ]; then
    REQUEST=$(echo "$REQUEST" | jq --arg acc "$ACCOUNT" '. + {account_names: [$acc]}')
fi

if [ -n "$CONNECTOR" ]; then
    REQUEST=$(echo "$REQUEST" | jq --arg conn "$CONNECTOR" '. + {connector_names: [$conn]}')
fi

# Fetch distribution
RESPONSE=$(curl -s -X POST \
    -u "$API_USER:$API_PASS" \
    -H "Content-Type: application/json" \
    -d "$REQUEST" \
    "$API_URL/portfolio/distribution")

# Check for error
if echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to get portfolio distribution\", \"detail\": $RESPONSE}"
    exit 1
fi

echo "$RESPONSE" | jq '.'
