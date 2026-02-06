#!/bin/bash
# Check if hummingbot-api and Gateway are running
#
# Usage:
#   ./check_prerequisites.sh
#
# Returns JSON with status of each component

set -e

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do [ -f "$f" ] && source "$f" && break; done
API_URL="${API_URL:-http://localhost:8000}"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:15888}"

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

# Check Gateway (root endpoint returns {"status": "ok"})
GATEWAY_STATUS="not_running"
GATEWAY_MESSAGE=""

if [ "$API_STATUS" = "running" ]; then
    GATEWAY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/" 2>/dev/null || echo "000")

    if [ "$GATEWAY_RESPONSE" = "200" ]; then
        GATEWAY_STATUS="running"
        GATEWAY_MESSAGE="Gateway is running at $GATEWAY_URL"
    elif [ "$GATEWAY_RESPONSE" = "000" ]; then
        GATEWAY_STATUS="not_running"
        GATEWAY_MESSAGE="Cannot connect to Gateway at $GATEWAY_URL"
    else
        GATEWAY_STATUS="error"
        GATEWAY_MESSAGE="Gateway returned HTTP $GATEWAY_RESPONSE"
    fi
fi

# Determine overall readiness (API + Gateway running)
READY="false"
if [ "$API_STATUS" = "running" ] && [ "$GATEWAY_STATUS" = "running" ]; then
    READY="true"
fi

# Output result
cat << EOF
{
    "ready": $READY,
    "components": {
        "api": {
            "status": "$API_STATUS",
            "message": "$API_MESSAGE",
            "url": "$API_URL"
        },
        "gateway": {
            "status": "$GATEWAY_STATUS",
            "message": "$GATEWAY_MESSAGE",
            "url": "$GATEWAY_URL"
        }
    },
    "next_steps": $(if [ "$READY" = "true" ]; then
        echo '["Ready! Use get_portfolio_overview MCP tool to check wallets."]'
    elif [ "$API_STATUS" != "running" ]; then
        echo '["Run hummingbot-deploy skill to install and start the API"]'
    else
        echo '["Start Gateway container"]'
    fi)
}
EOF
