#!/bin/bash
#
# Verify Hummingbot installation
# Usage: ./verify.sh [--json]
#
set -eu

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do
    [[ -f "$f" ]] && source "$f" && break
done

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"
API_DIR="${API_DIR:-$HOME/hummingbot-api}"
CONDOR_DIR="${CONDOR_DIR:-$HOME/condor}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Parse arguments
JSON_OUTPUT=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --json) JSON_OUTPUT=true; shift ;;
        -h|--help)
            echo "Usage: $0 [--json]"
            echo ""
            echo "Options:"
            echo "  --json    Output results as JSON"
            echo "  -h        Show this help"
            exit 0
            ;;
        *) shift ;;
    esac
done

# Check functions
check_api_health() {
    local response http_code
    response=$(curl -s -w "\n%{http_code}" -u "$API_USER:$API_PASS" "$API_URL/health" 2>/dev/null || echo -e "\n000")
    http_code=$(echo "$response" | tail -n1)

    if [[ "$http_code" == "200" ]]; then
        echo "healthy"
    elif [[ "$http_code" == "401" ]]; then
        echo "auth_error"
    elif [[ "$http_code" == "000" ]]; then
        echo "unreachable"
    else
        echo "unhealthy"
    fi
}

check_container() {
    local name=$1
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${name}$"; then
        # Check if has health check
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

check_directory() {
    local dir=$1
    if [[ -d "$dir" ]]; then
        echo "exists"
    else
        echo "missing"
    fi
}

check_mcp_image() {
    if docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -q "hummingbot/hummingbot-mcp"; then
        echo "available"
    else
        echo "missing"
    fi
}

check_claude_mcp() {
    if command -v claude >/dev/null 2>&1; then
        if claude mcp list 2>/dev/null | grep -q "hummingbot"; then
            echo "configured"
        else
            echo "not_configured"
        fi
    else
        echo "claude_not_found"
    fi
}

# Run checks
API_HEALTH=$(check_api_health)
API_DIR_STATUS=$(check_directory "$API_DIR")
CONDOR_DIR_STATUS=$(check_directory "$CONDOR_DIR")
MCP_IMAGE_STATUS=$(check_mcp_image)
CLAUDE_MCP_STATUS=$(check_claude_mcp)

# Container checks
POSTGRES_STATUS=$(check_container "hummingbot-postgres")
EMQX_STATUS=$(check_container "hummingbot-emqx")
GATEWAY_STATUS=$(check_container "hummingbot-gateway")
CONDOR_STATUS=$(check_container "condor")

# Determine overall status
ISSUES=0

[[ "$API_HEALTH" != "healthy" ]] && ISSUES=$((ISSUES + 1))
[[ "$POSTGRES_STATUS" != "healthy" && "$POSTGRES_STATUS" != "running" ]] && ISSUES=$((ISSUES + 1))

if [[ $ISSUES -eq 0 ]]; then
    OVERALL="healthy"
elif [[ $ISSUES -le 2 ]]; then
    OVERALL="degraded"
else
    OVERALL="unhealthy"
fi

# Output
if $JSON_OUTPUT; then
    cat << EOF
{
    "overall": "$OVERALL",
    "components": {
        "hummingbot_api": {
            "directory": "$API_DIR_STATUS",
            "health": "$API_HEALTH",
            "url": "$API_URL"
        },
        "postgresql": {
            "status": "$POSTGRES_STATUS"
        },
        "emqx": {
            "status": "$EMQX_STATUS"
        },
        "gateway": {
            "status": "$GATEWAY_STATUS"
        },
        "mcp_server": {
            "image": "$MCP_IMAGE_STATUS",
            "claude_code": "$CLAUDE_MCP_STATUS"
        },
        "condor": {
            "directory": "$CONDOR_DIR_STATUS",
            "status": "$CONDOR_STATUS"
        }
    },
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
else
    echo ""
    echo -e "${CYAN}Hummingbot Installation Verification${NC}"
    echo -e "${CYAN}=====================================${NC}"
    echo ""

    # Status helper
    status_icon() {
        case $1 in
            healthy|running|exists|available|configured) echo -e "${GREEN}✓${NC}" ;;
            not_configured|missing) echo -e "${YELLOW}○${NC}" ;;
            *) echo -e "${RED}✗${NC}" ;;
        esac
    }

    echo -e "${CYAN}Hummingbot API${NC}"
    echo -e "  $(status_icon "$API_DIR_STATUS") Directory: $API_DIR ($API_DIR_STATUS)"
    echo -e "  $(status_icon "$API_HEALTH") API Health: $API_HEALTH"
    echo -e "  $(status_icon "$POSTGRES_STATUS") PostgreSQL: $POSTGRES_STATUS"
    echo -e "  $(status_icon "$EMQX_STATUS") EMQX: $EMQX_STATUS"
    echo -e "  $(status_icon "$GATEWAY_STATUS") Gateway: $GATEWAY_STATUS"
    echo ""

    echo -e "${CYAN}MCP Server${NC}"
    echo -e "  $(status_icon "$MCP_IMAGE_STATUS") Docker Image: $MCP_IMAGE_STATUS"
    echo -e "  $(status_icon "$CLAUDE_MCP_STATUS") Claude Code: $CLAUDE_MCP_STATUS"
    echo ""

    echo -e "${CYAN}Condor${NC}"
    echo -e "  $(status_icon "$CONDOR_DIR_STATUS") Directory: $CONDOR_DIR ($CONDOR_DIR_STATUS)"
    echo -e "  $(status_icon "$CONDOR_STATUS") Container: $CONDOR_STATUS"
    echo ""

    # Overall status
    case $OVERALL in
        healthy)
            echo -e "${GREEN}Overall Status: All systems operational${NC}"
            ;;
        degraded)
            echo -e "${YELLOW}Overall Status: Some components need attention${NC}"
            ;;
        unhealthy)
            echo -e "${RED}Overall Status: Installation issues detected${NC}"
            ;;
    esac
    echo ""

    # Recommendations
    if [[ "$API_HEALTH" == "unreachable" ]]; then
        echo -e "${YELLOW}Recommendation:${NC} Start the API server"
        echo "  cd $API_DIR && docker compose up -d"
        echo ""
    fi

    if [[ "$MCP_IMAGE_STATUS" == "missing" ]]; then
        echo -e "${YELLOW}Recommendation:${NC} Install MCP server"
        echo "  ./scripts/install_mcp.sh"
        echo ""
    fi

    if [[ "$CONDOR_DIR_STATUS" == "missing" ]]; then
        echo -e "${YELLOW}Recommendation:${NC} Install Condor (optional)"
        echo "  ./scripts/install_condor.sh"
        echo ""
    fi
fi
