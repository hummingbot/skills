#!/bin/bash
#
# Health check for Hummingbot API
# Usage: ./health_check.sh [--api-url URL] [--api-user USER] [--api-pass PASS] [--json]
#
set -eu

# Detect if running inside a container
is_container() {
    [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null || grep -q containerd /proc/1/cgroup 2>/dev/null
}

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do
    [[ -f "$f" ]] && source "$f" && break
done

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

# Parse arguments
JSON_OUTPUT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --api-url) API_URL="$2"; shift 2 ;;
        --api-user) API_USER="$2"; shift 2 ;;
        --api-pass) API_PASS="$2"; shift 2 ;;
        --json) JSON_OUTPUT=true; shift ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --api-url URL     API URL (default: http://localhost:8000)"
            echo "  --api-user USER   API username (default: admin)"
            echo "  --api-pass PASS   API password (default: admin)"
            echo "  --json            Output as JSON"
            echo "  -h                Show this help"
            exit 0
            ;;
        *) shift ;;
    esac
done

# Check API health
check_api() {
    local response http_code body

    # If in container, use docker exec to check from inside the API container
    if is_container && docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^hummingbot-api$"; then
        # Use python since curl may not be available in the API container
        response=$(docker exec hummingbot-api python -c "
import urllib.request, base64
try:
    auth = base64.b64encode(b'$API_USER:$API_PASS').decode()
    req = urllib.request.Request('http://localhost:8000/health', headers={'Authorization': f'Basic {auth}'})
    resp = urllib.request.urlopen(req, timeout=5)
    print(resp.read().decode())
    print(resp.status)
except urllib.error.HTTPError as e:
    print(e.reason)
    print(e.code)
except Exception as e:
    print(str(e))
    print('000')
" 2>/dev/null || echo -e "error\n000")
        body=$(echo "$response" | head -n -1)
        http_code=$(echo "$response" | tail -n1)
    else
        response=$(curl -s -w "\n%{http_code}" -u "$API_USER:$API_PASS" "$API_URL/health" 2>/dev/null || echo -e "\n000")
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n -1)
    fi

    echo "$http_code|$body"
}

# Check container health
check_container() {
    local name=$1

    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${name}$"; then
        local health
        health=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "none")

        if [[ "$health" == "healthy" ]]; then
            echo "healthy"
        elif [[ "$health" == "none" ]]; then
            echo "running"
        else
            echo "$health"
        fi
    else
        echo "not_running"
    fi
}

# Run checks
API_RESULT=$(check_api)
API_CODE=$(echo "$API_RESULT" | cut -d'|' -f1)
API_BODY=$(echo "$API_RESULT" | cut -d'|' -f2-)

case $API_CODE in
    200) API_STATUS="healthy" ;;
    401) API_STATUS="auth_error" ;;
    000) API_STATUS="unreachable" ;;
    *) API_STATUS="unhealthy" ;;
esac

POSTGRES_STATUS=$(check_container "hummingbot-postgres")
EMQX_STATUS=$(check_container "hummingbot-emqx")
GATEWAY_STATUS=$(check_container "hummingbot-gateway")

# Determine overall health
if [[ "$API_STATUS" == "healthy" ]]; then
    OVERALL="healthy"
elif [[ "$API_STATUS" == "auth_error" ]]; then
    OVERALL="auth_error"
elif [[ "$POSTGRES_STATUS" == "healthy" || "$POSTGRES_STATUS" == "running" ]]; then
    OVERALL="degraded"
else
    OVERALL="unhealthy"
fi

# Output
if $JSON_OUTPUT; then
    cat << EOF
{
    "overall": "$OVERALL",
    "api": {
        "status": "$API_STATUS",
        "url": "$API_URL",
        "http_code": $API_CODE
    },
    "services": {
        "postgresql": "$POSTGRES_STATUS",
        "emqx": "$EMQX_STATUS",
        "gateway": "$GATEWAY_STATUS"
    },
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
else
    # Colors
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    NC='\033[0m'

    echo ""
    echo -e "${CYAN}Hummingbot API Health Check${NC}"
    echo -e "${CYAN}============================${NC}"
    echo ""

    status_icon() {
        case $1 in
            healthy|running) echo -e "${GREEN}✓${NC}" ;;
            auth_error|degraded) echo -e "${YELLOW}!${NC}" ;;
            *) echo -e "${RED}✗${NC}" ;;
        esac
    }

    echo "API URL: $API_URL"
    echo ""
    echo -e "$(status_icon "$API_STATUS") API Server: $API_STATUS"
    echo -e "$(status_icon "$POSTGRES_STATUS") PostgreSQL: $POSTGRES_STATUS"
    echo -e "$(status_icon "$EMQX_STATUS") EMQX: $EMQX_STATUS"
    echo -e "$(status_icon "$GATEWAY_STATUS") Gateway: $GATEWAY_STATUS"
    echo ""

    case $OVERALL in
        healthy)
            echo -e "${GREEN}Overall: Healthy${NC}"
            ;;
        auth_error)
            echo -e "${YELLOW}Overall: Authentication Error${NC}"
            echo "Check your API credentials."
            ;;
        degraded)
            echo -e "${YELLOW}Overall: Degraded${NC}"
            echo "Some services may not be responding."
            ;;
        unhealthy)
            echo -e "${RED}Overall: Unhealthy${NC}"
            echo "API server is not responding."
            ;;
    esac
    echo ""
fi
