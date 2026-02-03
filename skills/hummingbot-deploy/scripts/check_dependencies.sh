#!/bin/bash
#
# Check dependencies for Hummingbot deployment
# Usage: ./check_dependencies.sh [--json]
#
set -eu

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
check_command() {
    command -v "$1" >/dev/null 2>&1
}

check_docker_running() {
    docker info >/dev/null 2>&1
}

check_docker_compose() {
    docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1
}

get_version() {
    local cmd=$1
    case $cmd in
        git) git --version 2>/dev/null | awk '{print $3}' || echo "unknown" ;;
        docker) docker --version 2>/dev/null | awk '{print $3}' | tr -d ',' || echo "unknown" ;;
        curl) curl --version 2>/dev/null | head -1 | awk '{print $2}' || echo "unknown" ;;
        make) make --version 2>/dev/null | head -1 | awk '{print $3}' || echo "unknown" ;;
        *) echo "unknown" ;;
    esac
}

# Detect OS
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
case "$ARCH" in
    x86_64|amd64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *) ARCH="$ARCH" ;;
esac

# Check each dependency
DEPS=("git" "docker" "curl" "make")
MISSING=()
INSTALLED=()

for dep in "${DEPS[@]}"; do
    if check_command "$dep"; then
        INSTALLED+=("$dep")
    else
        MISSING+=("$dep")
    fi
done

# Check docker-compose separately
if check_docker_compose; then
    DOCKER_COMPOSE_OK=true
else
    DOCKER_COMPOSE_OK=false
    MISSING+=("docker-compose")
fi

# Check if Docker daemon is running
if check_command docker; then
    if check_docker_running; then
        DOCKER_RUNNING=true
    else
        DOCKER_RUNNING=false
    fi
else
    DOCKER_RUNNING=false
fi

# Check disk space (need 2GB minimum)
if [[ "$OS" == "linux" || "$OS" == "darwin" ]]; then
    AVAILABLE_MB=$(df -m . 2>/dev/null | tail -1 | awk '{print $4}')
    DISK_OK=$([[ -n "$AVAILABLE_MB" ]] && [[ $AVAILABLE_MB -ge 2048 ]] && echo true || echo false)
else
    AVAILABLE_MB="unknown"
    DISK_OK=true
fi

# Determine overall status
if [[ ${#MISSING[@]} -eq 0 ]] && [[ "$DOCKER_RUNNING" == "true" ]] && [[ "$DISK_OK" == "true" ]]; then
    OVERALL="ready"
elif [[ ${#MISSING[@]} -eq 0 ]] && [[ "$DOCKER_RUNNING" == "false" ]]; then
    OVERALL="docker_not_running"
else
    OVERALL="missing_dependencies"
fi

# Output
if $JSON_OUTPUT; then
    cat << EOF
{
    "status": "$OVERALL",
    "os": "$OS",
    "arch": "$ARCH",
    "dependencies": {
        "git": $(check_command git && echo '{"installed": true, "version": "'$(get_version git)'"}' || echo '{"installed": false}'),
        "docker": $(check_command docker && echo '{"installed": true, "version": "'$(get_version docker)'", "running": '$DOCKER_RUNNING'}' || echo '{"installed": false, "running": false}'),
        "docker_compose": $(echo '{"installed": '$DOCKER_COMPOSE_OK'}'),
        "curl": $(check_command curl && echo '{"installed": true, "version": "'$(get_version curl)'"}' || echo '{"installed": false}'),
        "make": $(check_command make && echo '{"installed": true}' || echo '{"installed": false}')
    },
    "disk_space": {
        "available_mb": ${AVAILABLE_MB:-0},
        "sufficient": $DISK_OK
    },
    "missing": [$(IFS=,; echo "\"${MISSING[*]//,/\",\"}\"" | sed 's/^""//' | sed 's/""$//')]
}
EOF
else
    echo ""
    echo -e "${CYAN}Hummingbot Deployment - Dependency Check${NC}"
    echo -e "${CYAN}=========================================${NC}"
    echo ""
    echo -e "System: $OS ($ARCH)"
    echo ""

    # Show dependency status
    for dep in "${DEPS[@]}"; do
        if check_command "$dep"; then
            echo -e "${GREEN}✓${NC} $dep ($(get_version $dep))"
        else
            echo -e "${RED}✗${NC} $dep - NOT INSTALLED"
        fi
    done

    # Docker compose
    if $DOCKER_COMPOSE_OK; then
        echo -e "${GREEN}✓${NC} docker-compose"
    else
        echo -e "${RED}✗${NC} docker-compose - NOT INSTALLED"
    fi

    echo ""

    # Docker daemon status
    if check_command docker; then
        if $DOCKER_RUNNING; then
            echo -e "${GREEN}✓${NC} Docker daemon is running"
        else
            echo -e "${YELLOW}!${NC} Docker is installed but not running"
            if [[ "$OS" == "darwin" ]]; then
                echo -e "  Run: ${CYAN}open -a Docker${NC}"
            else
                echo -e "  Run: ${CYAN}sudo systemctl start docker${NC}"
            fi
        fi
    fi

    # Disk space
    if [[ "$AVAILABLE_MB" != "unknown" ]]; then
        if $DISK_OK; then
            echo -e "${GREEN}✓${NC} Disk space: ${AVAILABLE_MB}MB available"
        else
            echo -e "${RED}✗${NC} Insufficient disk space: ${AVAILABLE_MB}MB (need 2048MB)"
        fi
    fi

    echo ""

    # Summary
    if [[ "$OVERALL" == "ready" ]]; then
        echo -e "${GREEN}All dependencies satisfied. Ready to install!${NC}"
        echo ""
        echo "Next step: ./scripts/install_api.sh"
        exit 0
    elif [[ "$OVERALL" == "docker_not_running" ]]; then
        echo -e "${YELLOW}Please start Docker and try again.${NC}"
        exit 1
    else
        echo -e "${RED}Missing dependencies: ${MISSING[*]}${NC}"
        echo ""
        echo "Install them with: ./scripts/install_dependencies.sh"
        exit 1
    fi
fi
