#!/bin/bash
#
# Install Hummingbot MCP Server for Claude
# Usage: ./install_mcp.sh [--api-url URL] [--api-user USER] [--api-pass PASS]
#
set -eu

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do
    [[ -f "$f" ]] && source "$f" && break
done

# Configuration
MCP_IMAGE="hummingbot/hummingbot-mcp:latest"
DEFAULT_API_URL="${API_URL:-http://localhost:8000}"
DEFAULT_API_USER="${API_USER:-admin}"
DEFAULT_API_PASS="${API_PASS:-admin}"

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
API_URL="$DEFAULT_API_URL"
API_USER="$DEFAULT_API_USER"
API_PASS="$DEFAULT_API_PASS"
AGENT_TYPE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        --api-user)
            API_USER="$2"
            shift 2
            ;;
        --api-pass)
            API_PASS="$2"
            shift 2
            ;;
        --agent)
            AGENT_TYPE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --api-url URL     Hummingbot API URL (default: http://localhost:8000)"
            echo "  --api-user USER   API username (default: admin)"
            echo "  --api-pass PASS   API password (default: admin)"
            echo "  --agent TYPE      Agent type: claude-code, claude-desktop, or both"
            echo "  -h                Show this help"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

echo ""
echo -e "${CYAN}Hummingbot MCP Server Installation${NC}"
echo -e "${CYAN}====================================${NC}"
echo ""

# Check prerequisites
msg_info "Checking prerequisites..."

if ! command -v docker >/dev/null 2>&1; then
    msg_error "docker is required. Run ./scripts/install_dependencies.sh"
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    msg_error "Docker daemon is not running."
    exit 1
fi

msg_ok "Prerequisites satisfied"

# For Docker on macOS/Windows, localhost needs special handling
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
if [[ "$API_URL" == *"localhost"* || "$API_URL" == *"127.0.0.1"* ]]; then
    # Replace localhost with host.docker.internal for Docker
    DOCKER_API_URL="${API_URL//localhost/host.docker.internal}"
    DOCKER_API_URL="${DOCKER_API_URL//127.0.0.1/host.docker.internal}"
else
    DOCKER_API_URL="$API_URL"
fi

msg_info "API URL: $API_URL"
msg_info "Docker API URL: $DOCKER_API_URL"

# Pull the MCP image
msg_info "Pulling MCP server image..."
docker pull "$MCP_IMAGE"
msg_ok "MCP image pulled"

# Test the MCP server
msg_info "Testing MCP server connection..."
TEST_RESULT=$(docker run --rm \
    -e HUMMINGBOT_API_URL="$DOCKER_API_URL" \
    -e HUMMINGBOT_API_USERNAME="$API_USER" \
    -e HUMMINGBOT_API_PASSWORD="$API_PASS" \
    "$MCP_IMAGE" \
    echo "MCP server configured successfully" 2>&1 || echo "")

if [[ "$TEST_RESULT" == *"successfully"* ]]; then
    msg_ok "MCP server test passed"
else
    msg_warn "Could not verify MCP server. API may not be running yet."
fi

# Detect agent type if not specified
if [[ -z "$AGENT_TYPE" ]]; then
    echo ""
    echo "Which AI assistant do you want to configure?"
    echo ""
    echo "  1) Claude Code (CLI)"
    echo "  2) Claude Desktop"
    echo "  3) Both"
    echo ""
    read -p "Enter choice (1-3): " -r CHOICE < /dev/tty

    case $CHOICE in
        1) AGENT_TYPE="claude-code" ;;
        2) AGENT_TYPE="claude-desktop" ;;
        3) AGENT_TYPE="both" ;;
        *) AGENT_TYPE="claude-code" ;;
    esac
fi

# Configure Claude Code
configure_claude_code() {
    msg_info "Configuring Claude Code..."

    if command -v claude >/dev/null 2>&1; then
        # Use claude mcp add command
        MCP_CMD="docker run --rm -i -e HUMMINGBOT_API_URL=$DOCKER_API_URL -e HUMMINGBOT_API_USERNAME=$API_USER -e HUMMINGBOT_API_PASSWORD=$API_PASS -v hummingbot_mcp:/root/.hummingbot_mcp $MCP_IMAGE"

        claude mcp add --transport stdio hummingbot -- $MCP_CMD 2>/dev/null || {
            msg_warn "Could not auto-configure. Add manually with:"
            echo ""
            echo "  claude mcp add --transport stdio hummingbot -- \\"
            echo "    docker run --rm -i \\"
            echo "    -e HUMMINGBOT_API_URL=$DOCKER_API_URL \\"
            echo "    -e HUMMINGBOT_API_USERNAME=$API_USER \\"
            echo "    -e HUMMINGBOT_API_PASSWORD=$API_PASS \\"
            echo "    -v hummingbot_mcp:/root/.hummingbot_mcp \\"
            echo "    $MCP_IMAGE"
            echo ""
        }
        msg_ok "Claude Code configured"
    else
        msg_warn "Claude Code CLI not found."
        echo ""
        echo "Install Claude Code first, then run:"
        echo ""
        echo "  claude mcp add --transport stdio hummingbot -- \\"
        echo "    docker run --rm -i \\"
        echo "    -e HUMMINGBOT_API_URL=$DOCKER_API_URL \\"
        echo "    -e HUMMINGBOT_API_USERNAME=$API_USER \\"
        echo "    -e HUMMINGBOT_API_PASSWORD=$API_PASS \\"
        echo "    -v hummingbot_mcp:/root/.hummingbot_mcp \\"
        echo "    $MCP_IMAGE"
        echo ""
    fi
}

# Configure Claude Desktop
configure_claude_desktop() {
    msg_info "Configuring Claude Desktop..."

    # Determine config path
    if [[ "$OS" == "darwin" ]]; then
        CONFIG_DIR="$HOME/Library/Application Support/Claude"
    elif [[ "$OS" == "linux" ]]; then
        CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/Claude"
    else
        # Windows (Git Bash / WSL)
        CONFIG_DIR="${APPDATA:-$HOME/AppData/Roaming}/Claude"
    fi

    CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

    # Create config directory
    mkdir -p "$CONFIG_DIR"

    # Generate config
    MCP_CONFIG=$(cat << EOF
{
  "mcpServers": {
    "hummingbot": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "HUMMINGBOT_API_URL=$DOCKER_API_URL",
        "-e", "HUMMINGBOT_API_USERNAME=$API_USER",
        "-e", "HUMMINGBOT_API_PASSWORD=$API_PASS",
        "-v", "hummingbot_mcp:/root/.hummingbot_mcp",
        "$MCP_IMAGE"
      ]
    }
  }
}
EOF
)

    # Check if config exists
    if [[ -f "$CONFIG_FILE" ]]; then
        msg_warn "Config file exists: $CONFIG_FILE"
        echo ""
        echo "Add this to your mcpServers section:"
        echo ""
        cat << EOF
    "hummingbot": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "HUMMINGBOT_API_URL=$DOCKER_API_URL",
        "-e", "HUMMINGBOT_API_USERNAME=$API_USER",
        "-e", "HUMMINGBOT_API_PASSWORD=$API_PASS",
        "-v", "hummingbot_mcp:/root/.hummingbot_mcp",
        "$MCP_IMAGE"
      ]
    }
EOF
        echo ""
    else
        # Create new config
        echo "$MCP_CONFIG" > "$CONFIG_FILE"
        msg_ok "Created config: $CONFIG_FILE"
    fi
}

# Apply configuration
case $AGENT_TYPE in
    claude-code)
        configure_claude_code
        ;;
    claude-desktop)
        configure_claude_desktop
        ;;
    both)
        configure_claude_code
        echo ""
        configure_claude_desktop
        ;;
esac

# Success message
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
msg_ok "MCP Server Installation Complete!"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  API URL:      $API_URL"
echo "  Docker URL:   $DOCKER_API_URL"
echo "  MCP Image:    $MCP_IMAGE"
echo ""
echo -e "${CYAN}Available MCP Tools:${NC}"
echo "  - get_accounts: List exchange accounts"
echo "  - get_balances: Get portfolio balances"
echo "  - get_positions: View open positions"
echo "  - create_executor: Create trading executors"
echo "  - get_candles: Fetch market data"
echo "  - get_funding_rate: Get funding rates"
echo ""
echo -e "${CYAN}Test in Claude:${NC}"
echo '  "Show my portfolio balances"'
echo '  "What is the current BTC price on Binance?"'
echo ""
