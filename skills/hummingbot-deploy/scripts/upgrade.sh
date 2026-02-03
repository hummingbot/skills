#!/bin/bash
#
# Upgrade Hummingbot components
# Usage: ./upgrade.sh [--api] [--condor] [--mcp] [--all] [--yes]
#
set -eu

# Configuration
API_DIR="${API_DIR:-$HOME/hummingbot-api}"
CONDOR_DIR="${CONDOR_DIR:-$HOME/condor}"
MCP_IMAGE="hummingbot/hummingbot-mcp:latest"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

msg_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
msg_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
msg_warn() { echo -e "${YELLOW}[WARN]${NC} $1" >&2; }
msg_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# Parse arguments
UPGRADE_API=false
UPGRADE_CONDOR=false
UPGRADE_MCP=false
AUTO_YES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --api) UPGRADE_API=true; shift ;;
        --condor) UPGRADE_CONDOR=true; shift ;;
        --mcp) UPGRADE_MCP=true; shift ;;
        --all)
            UPGRADE_API=true
            UPGRADE_CONDOR=true
            UPGRADE_MCP=true
            shift
            ;;
        -y|--yes) AUTO_YES=true; shift ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --api       Upgrade Hummingbot API"
            echo "  --condor    Upgrade Condor"
            echo "  --mcp       Upgrade MCP server image"
            echo "  --all       Upgrade all components"
            echo "  -y, --yes   Auto-confirm prompts"
            echo "  -h          Show this help"
            exit 0
            ;;
        *) shift ;;
    esac
done

# If no specific component selected, upgrade all installed
if ! $UPGRADE_API && ! $UPGRADE_CONDOR && ! $UPGRADE_MCP; then
    [[ -d "$API_DIR" ]] && UPGRADE_API=true
    [[ -d "$CONDOR_DIR" ]] && UPGRADE_CONDOR=true
    docker images --format '{{.Repository}}' 2>/dev/null | grep -q "hummingbot/hummingbot-mcp" && UPGRADE_MCP=true
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    msg_error "Docker daemon is not running."
    exit 1
fi

# Detect docker compose command
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo ""
echo -e "${CYAN}Hummingbot Upgrade${NC}"
echo -e "${CYAN}==================${NC}"
echo ""

UPGRADED=false

# Upgrade API
if $UPGRADE_API && [[ -d "$API_DIR" ]]; then
    msg_info "Upgrading Hummingbot API..."

    cd "$API_DIR"

    # Pull latest code
    if git pull 2>/dev/null; then
        msg_ok "Repository updated"
    else
        msg_warn "Could not update repository (may not be a git repo)"
    fi

    # Pull latest images
    msg_info "Pulling latest Docker images..."
    $DOCKER_COMPOSE pull || msg_warn "Some images could not be updated"

    # Restart services
    msg_info "Restarting services..."
    $DOCKER_COMPOSE up -d --remove-orphans

    msg_ok "Hummingbot API upgraded!"
    UPGRADED=true
    echo ""
fi

# Upgrade Condor
if $UPGRADE_CONDOR && [[ -d "$CONDOR_DIR" ]]; then
    msg_info "Upgrading Condor..."

    cd "$CONDOR_DIR"

    # Pull latest code
    if git pull 2>/dev/null; then
        msg_ok "Repository updated"
    else
        msg_warn "Could not update repository (may not be a git repo)"
    fi

    # Pull latest images
    msg_info "Pulling latest Docker images..."
    $DOCKER_COMPOSE pull || msg_warn "Some images could not be updated"

    # Restart services
    msg_info "Restarting services..."
    $DOCKER_COMPOSE up -d --remove-orphans

    msg_ok "Condor upgraded!"
    UPGRADED=true
    echo ""
fi

# Upgrade MCP
if $UPGRADE_MCP; then
    msg_info "Upgrading MCP server image..."

    OLD_IMAGE_ID=$(docker images -q "$MCP_IMAGE" 2>/dev/null || echo "")

    docker pull "$MCP_IMAGE"

    NEW_IMAGE_ID=$(docker images -q "$MCP_IMAGE" 2>/dev/null || echo "")

    if [[ "$OLD_IMAGE_ID" != "$NEW_IMAGE_ID" && -n "$NEW_IMAGE_ID" ]]; then
        msg_ok "MCP server image updated!"

        # Clean up old image
        if [[ -n "$OLD_IMAGE_ID" && "$OLD_IMAGE_ID" != "$NEW_IMAGE_ID" ]]; then
            docker rmi "$OLD_IMAGE_ID" 2>/dev/null || true
        fi
    else
        msg_info "MCP server image already up to date"
    fi
    UPGRADED=true
    echo ""
fi

if $UPGRADED; then
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    msg_ok "Upgrade Complete!"
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo ""
    echo "Verify installation: ./scripts/verify.sh"
else
    msg_warn "No components found to upgrade."
    echo ""
    echo "Install components first:"
    echo "  ./scripts/install_api.sh"
    echo "  ./scripts/install_mcp.sh"
    echo "  ./scripts/install_condor.sh"
fi
