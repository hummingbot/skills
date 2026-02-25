#!/bin/bash
# Check if hummingbot-api is running
#
# Usage:
#   ./check_prerequisites.sh
#
# Returns JSON with status

set -e

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do [ -f "$f" ] && source "$f" && break; done
API_URL="${API_URL:-http://localhost:8000}"

# Check API (root endpoint returns {"status": "running"})
API_STATUS="not_running"
API_MESSAGE=""
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/" 2>/dev/null || echo "000")

if [ "$API_RESPONSE" = "200" ]; then
    API_STATUS="running"
    API_MESSAGE="API is running at $API_URL"
elif [ "$API_RESPONSE" = "000" ]; then
    API_STATUS="not_running"
    API_MESSAGE="Cannot connect to API at $API_URL"
else
    API_STATUS="error"
    API_MESSAGE="API returned HTTP $API_RESPONSE"
fi

# Determine readiness
READY="false"
if [ "$API_STATUS" = "running" ]; then
    READY="true"
fi

# Output result
cat << EOF
{
    "ready": $READY,
    "api": {
        "status": "$API_STATUS",
        "message": "$API_MESSAGE",
        "url": "$API_URL"
    },
    "next_steps": $(if [ "$READY" = "true" ]; then
        echo '["Ready! You can now deploy LP positions."]'
    else
        echo '["Run hummingbot-deploy skill to install and start the API"]'
    fi)
}
EOF
