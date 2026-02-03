#!/bin/bash
#
# Install Condor Telegram Bot
# Usage: ./install_condor.sh [--dir PATH] [--yes]
#
set -eu

# Configuration
CONDOR_REPO="https://github.com/hummingbot/condor.git"
DEFAULT_DIR="$HOME/condor"

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
INSTALL_DIR="$DEFAULT_DIR"
AUTO_YES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dir PATH] [-y|--yes]"
            echo ""
            echo "Options:"
            echo "  --dir PATH    Installation directory (default: ~/condor)"
            echo "  -y, --yes     Auto-confirm prompts"
            echo "  -h            Show this help"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

echo ""
echo -e "${CYAN}Condor Telegram Bot Installation${NC}"
echo -e "${CYAN}==================================${NC}"
echo ""

# Check prerequisites
msg_info "Checking prerequisites..."

if ! command -v git >/dev/null 2>&1; then
    msg_error "git is required. Run ./scripts/install_dependencies.sh"
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    msg_error "docker is required. Run ./scripts/install_dependencies.sh"
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    msg_error "Docker daemon is not running."
    echo ""
    if [[ "$(uname -s)" == "Darwin" ]]; then
        echo -e "Start Docker Desktop: ${CYAN}open -a Docker${NC}"
    else
        echo -e "Start Docker: ${CYAN}sudo systemctl start docker${NC}"
    fi
    exit 1
fi

msg_ok "Prerequisites satisfied"

# Detect docker compose command
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Check if already installed
if [[ -d "$INSTALL_DIR" ]]; then
    msg_warn "Directory already exists: $INSTALL_DIR"

    if ! $AUTO_YES; then
        read -p "Upgrade existing installation? (y/n): " -r CONFIRM < /dev/tty
        if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
            msg_info "Upgrading existing installation..."
            cd "$INSTALL_DIR"
            git pull
            make deploy
            msg_ok "Condor upgraded!"
            exit 0
        else
            msg_info "Installation cancelled."
            exit 0
        fi
    else
        msg_info "Upgrading existing installation..."
        cd "$INSTALL_DIR"
        git pull
        make deploy
        msg_ok "Condor upgraded!"
        exit 0
    fi
fi

# Clone repository
msg_info "Cloning Condor repository..."
git clone --depth 1 "$CONDOR_REPO" "$INSTALL_DIR"
msg_ok "Repository cloned to $INSTALL_DIR"

# Run setup
cd "$INSTALL_DIR"

# Check for setup script
if [[ -f "setup-environment.sh" ]]; then
    msg_info "Running Condor setup script..."
    echo ""
    echo -e "${YELLOW}Note: You will need to provide your Telegram Bot Token.${NC}"
    echo "Create a bot at https://t.me/BotFather to get a token."
    echo ""

    bash setup-environment.sh
else
    msg_warn "No setup script found, checking Makefile..."
    if [[ -f "Makefile" ]] && grep -q "setup:" Makefile; then
        make setup
    fi
fi

# Deploy
msg_info "Deploying Condor (make deploy)..."
make deploy

# Wait for container to start
msg_info "Waiting for Condor to start..."
sleep 5

# Check if running
if docker ps --format '{{.Names}}' | grep -q "condor"; then
    msg_ok "Condor container is running"
else
    msg_warn "Condor container may still be starting"
fi

# Success message
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
msg_ok "Condor Installation Complete!"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Installation Details:${NC}"
echo "  Directory: $INSTALL_DIR"
echo ""
echo -e "${CYAN}Getting Started:${NC}"
echo "  1. Open Telegram"
echo "  2. Find your bot (the one you created with BotFather)"
echo "  3. Send /start to begin"
echo "  4. Use /config to add Hummingbot API servers"
echo ""
echo -e "${CYAN}Useful Commands:${NC}"
echo "  View logs:    cd $INSTALL_DIR && $DOCKER_COMPOSE logs -f"
echo "  Stop:         cd $INSTALL_DIR && $DOCKER_COMPOSE down"
echo "  Restart:      cd $INSTALL_DIR && $DOCKER_COMPOSE restart"
echo "  Status:       cd $INSTALL_DIR && $DOCKER_COMPOSE ps"
echo ""
echo -e "${CYAN}Telegram Bot Commands:${NC}"
echo "  /start    - Start the bot"
echo "  /config   - Configure API servers"
echo "  /balance  - View balances"
echo "  /help     - Show all commands"
echo ""
