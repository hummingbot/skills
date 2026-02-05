#!/bin/bash
# Check if hummingbot-api and MCP are properly configured
#
# Usage:
#   ./check_prerequisites.sh
#
# Returns JSON with status of each component

set -e

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do [ -f "$f" ] && source "$f" && break; done
API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

# Check API health
API_STATUS="not_running"
API_MESSAGE=""
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -u "$API_USER:$API_PASS" "$API_URL/health" 2>/dev/null || echo "000")

if [ "$API_RESPONSE" = "200" ]; then
    API_STATUS="running"
    API_MESSAGE="API is healthy at $API_URL"
elif [ "$API_RESPONSE" = "401" ]; then
    API_STATUS="auth_failed"
    API_MESSAGE="API is running but authentication failed. Check API_USER and API_PASS."
elif [ "$API_RESPONSE" = "000" ]; then
    API_STATUS="not_running"
    API_MESSAGE="Cannot connect to API at $API_URL. Is hummingbot-api running?"
else
    API_STATUS="error"
    API_MESSAGE="API returned HTTP $API_RESPONSE"
fi

# Check Gateway connectivity (required for CLMM)
GATEWAY_STATUS="not_configured"
GATEWAY_MESSAGE=""

if [ "$API_STATUS" = "running" ]; then
    GATEWAY_RESPONSE=$(curl -s -u "$API_USER:$API_PASS" "$API_URL/gateway/status" 2>/dev/null || echo '{"error": "failed"}')

    if echo "$GATEWAY_RESPONSE" | jq -e '.connected == true' > /dev/null 2>&1; then
        GATEWAY_STATUS="connected"
        GATEWAY_MESSAGE="Gateway is connected"
    elif echo "$GATEWAY_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
        GATEWAY_STATUS="error"
        GATEWAY_MESSAGE="Gateway check failed"
    else
        GATEWAY_STATUS="not_connected"
        GATEWAY_MESSAGE="Gateway is not connected. Start Gateway container."
    fi
fi

# Check for CLMM connectors
CLMM_CONNECTORS="[]"
if [ "$GATEWAY_STATUS" = "connected" ]; then
    CONNECTORS_RESPONSE=$(curl -s -u "$API_USER:$API_PASS" "$API_URL/gateway/connectors" 2>/dev/null || echo '[]')
    CLMM_CONNECTORS=$(echo "$CONNECTORS_RESPONSE" | jq '[.[] | select(.type == "clmm" or .name | contains("meteora") or .name | contains("raydium"))]' 2>/dev/null || echo '[]')
fi

# Check wallet configuration
WALLET_STATUS="not_configured"
WALLET_MESSAGE=""
if [ "$GATEWAY_STATUS" = "connected" ]; then
    WALLETS_RESPONSE=$(curl -s -u "$API_USER:$API_PASS" "$API_URL/gateway/wallets" 2>/dev/null || echo '{"wallets": []}')
    WALLET_COUNT=$(echo "$WALLETS_RESPONSE" | jq '.wallets | length' 2>/dev/null || echo "0")

    if [ "$WALLET_COUNT" -gt 0 ]; then
        WALLET_STATUS="configured"
        WALLET_MESSAGE="$WALLET_COUNT wallet(s) configured"
    else
        WALLET_STATUS="not_configured"
        WALLET_MESSAGE="No wallets configured. Add a wallet via Gateway."
    fi
fi

# Determine overall readiness
READY="false"
if [ "$API_STATUS" = "running" ] && [ "$GATEWAY_STATUS" = "connected" ] && [ "$WALLET_STATUS" = "configured" ]; then
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
            "message": "$GATEWAY_MESSAGE"
        },
        "wallets": {
            "status": "$WALLET_STATUS",
            "message": "$WALLET_MESSAGE"
        },
        "clmm_connectors": $CLMM_CONNECTORS
    },
    "next_steps": $(if [ "$READY" = "true" ]; then
        echo '["Ready to manage LP positions! Use list_pools.sh to find pools."]'
    elif [ "$API_STATUS" != "running" ]; then
        echo '["Run hummingbot-deploy skill to install and start the API"]'
    elif [ "$GATEWAY_STATUS" != "connected" ]; then
        echo '["Start Gateway: cd ~/hummingbot-api && docker compose up -d gateway"]'
    elif [ "$WALLET_STATUS" != "configured" ]; then
        echo '["Add a wallet via Gateway API or manage_gateway_config MCP tool"]'
    else
        echo '["Check component statuses above"]'
    fi)
}
EOF
