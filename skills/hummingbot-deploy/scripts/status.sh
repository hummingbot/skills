#!/bin/bash
#
# Show status of all Hummingbot components
# Usage: ./status.sh [--json]
#
set -eu

# Configuration
API_DIR="${API_DIR:-$HOME/hummingbot-api}"
CONDOR_DIR="${CONDOR_DIR:-$HOME/condor}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

# Parse arguments
JSON_OUTPUT=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --json) JSON_OUTPUT=true; shift ;;
        -h|--help)
            echo "Usage: $0 [--json]"
            exit 0
            ;;
        *) shift ;;
    esac
done

# Detect docker compose command
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

get_container_info() {
    local name=$1
    local info

    if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${name}$"; then
        local state status ports
        state=$(docker inspect --format='{{.State.Status}}' "$name" 2>/dev/null || echo "unknown")
        status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "none")
        ports=$(docker port "$name" 2>/dev/null | head -1 || echo "")

        echo "$state|$status|$ports"
    else
        echo "not_found||"
    fi
}

if $JSON_OUTPUT; then
    echo "{"
    echo '  "hummingbot_api": {'

    if [[ -d "$API_DIR" ]]; then
        echo '    "installed": true,'
        echo "    \"directory\": \"$API_DIR\","
        echo '    "containers": {'

        for container in hummingbot-api hummingbot-postgres hummingbot-emqx hummingbot-gateway; do
            info=$(get_container_info "$container")
            IFS='|' read -r state health ports <<< "$info"
            echo "      \"$container\": {\"state\": \"$state\", \"health\": \"$health\"},"
        done | sed '$ s/,$//'

        echo '    }'
    else
        echo '    "installed": false'
    fi
    echo '  },'

    echo '  "condor": {'
    if [[ -d "$CONDOR_DIR" ]]; then
        echo '    "installed": true,'
        echo "    \"directory\": \"$CONDOR_DIR\","
        info=$(get_container_info "condor")
        IFS='|' read -r state health ports <<< "$info"
        echo "    \"state\": \"$state\""
    else
        echo '    "installed": false'
    fi
    echo '  },'

    echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\""
    echo "}"
else
    echo ""
    echo -e "${CYAN}Hummingbot Status${NC}"
    echo -e "${CYAN}==================${NC}"
    echo ""

    # Hummingbot API
    echo -e "${CYAN}Hummingbot API${NC} ${DIM}($API_DIR)${NC}"

    if [[ -d "$API_DIR" ]]; then
        # Get container status
        for container in hummingbot-api hummingbot-postgres hummingbot-emqx hummingbot-gateway; do
            info=$(get_container_info "$container")
            IFS='|' read -r state health ports <<< "$info"

            case $state in
                running)
                    if [[ "$health" == "healthy" ]]; then
                        echo -e "  ${GREEN}●${NC} $container ${DIM}(healthy)${NC}"
                    elif [[ "$health" == "unhealthy" ]]; then
                        echo -e "  ${RED}●${NC} $container ${DIM}(unhealthy)${NC}"
                    else
                        echo -e "  ${GREEN}●${NC} $container ${DIM}(running)${NC}"
                    fi
                    ;;
                exited)
                    echo -e "  ${RED}○${NC} $container ${DIM}(stopped)${NC}"
                    ;;
                not_found)
                    echo -e "  ${DIM}○${NC} $container ${DIM}(not created)${NC}"
                    ;;
                *)
                    echo -e "  ${YELLOW}○${NC} $container ${DIM}($state)${NC}"
                    ;;
            esac
        done

        echo ""
        echo -e "  ${DIM}Manage: cd $API_DIR && $DOCKER_COMPOSE [up -d|down|logs -f]${NC}"
    else
        echo -e "  ${DIM}Not installed${NC}"
        echo -e "  ${DIM}Install: ./scripts/install_api.sh${NC}"
    fi

    echo ""

    # Condor
    echo -e "${CYAN}Condor${NC} ${DIM}($CONDOR_DIR)${NC}"

    if [[ -d "$CONDOR_DIR" ]]; then
        info=$(get_container_info "condor")
        IFS='|' read -r state health ports <<< "$info"

        case $state in
            running)
                echo -e "  ${GREEN}●${NC} condor ${DIM}(running)${NC}"
                ;;
            exited)
                echo -e "  ${RED}○${NC} condor ${DIM}(stopped)${NC}"
                ;;
            not_found)
                echo -e "  ${DIM}○${NC} condor ${DIM}(not created)${NC}"
                ;;
            *)
                echo -e "  ${YELLOW}○${NC} condor ${DIM}($state)${NC}"
                ;;
        esac

        echo ""
        echo -e "  ${DIM}Manage: cd $CONDOR_DIR && $DOCKER_COMPOSE [up -d|down|logs -f]${NC}"
    else
        echo -e "  ${DIM}Not installed (optional)${NC}"
        echo -e "  ${DIM}Install: ./scripts/install_condor.sh${NC}"
    fi

    echo ""

    # MCP Server
    echo -e "${CYAN}MCP Server${NC}"

    if docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -q "hummingbot/hummingbot-mcp"; then
        echo -e "  ${GREEN}●${NC} Docker image available"
    else
        echo -e "  ${DIM}○${NC} Docker image not pulled"
    fi

    if command -v claude >/dev/null 2>&1; then
        if claude mcp list 2>/dev/null | grep -q "hummingbot"; then
            echo -e "  ${GREEN}●${NC} Claude Code configured"
        else
            echo -e "  ${DIM}○${NC} Claude Code not configured"
        fi
    fi

    echo ""
fi
