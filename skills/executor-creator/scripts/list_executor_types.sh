#!/bin/bash
# List available executor types with descriptions
# Usage: ./list_executor_types.sh

set -e

# Load .env if present (check current dir, ~/.hummingbot/, ~/)
for f in .env ~/.hummingbot/.env ~/.env; do [ -f "$f" ] && source "$f" && break; done
API_URL="${HUMMINGBOT_API_URL:-${API_URL:-http://localhost:8000}}"
API_USER="${HUMMINGBOT_API_USER:-${API_USER:-admin}}"
API_PASS="${HUMMINGBOT_API_PASS:-${API_PASS:-admin}}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --api-url) API_URL="$2"; shift 2 ;;
        --api-user) API_USER="$2"; shift 2 ;;
        --api-pass) API_PASS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Fetch executor types
RESPONSE=$(curl -s -u "$API_USER:$API_PASS" "$API_URL/executors/types/available")

# Check for error
if echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to get executor types\", \"detail\": $RESPONSE}"
    exit 1
fi

echo "$RESPONSE" | jq '.'
