#!/bin/bash
#
# Install Hummingbot API Server
# Usage: ./install_api.sh [--dir PATH] [-y]
#
set -eu

API_REPO="https://github.com/hummingbot/hummingbot-api.git"
INSTALL_DIR="${1:-$HOME/hummingbot-api}"

# Remove --dir flag if present
[[ "$INSTALL_DIR" == "--dir" ]] && INSTALL_DIR="${2:-$HOME/hummingbot-api}"

# Check prerequisites
for cmd in git docker; do
    command -v $cmd >/dev/null || { echo "Error: $cmd required"; exit 1; }
done
docker info >/dev/null 2>&1 || { echo "Error: Docker not running"; exit 1; }

# Detect docker compose
DC="docker compose"
$DC version >/dev/null 2>&1 || DC="docker-compose"

# Install or upgrade
if [[ -d "$INSTALL_DIR" ]]; then
    echo "Upgrading $INSTALL_DIR..."
    cd "$INSTALL_DIR"
    git pull
    $DC pull
    $DC up -d
else
    echo "Installing to $INSTALL_DIR..."
    git clone --depth 1 "$API_REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    # Create default .env and skip interactive setup
    if [[ ! -f .env ]]; then
        echo "Creating default .env..."
        cat > .env << 'EOF'
USERNAME=admin
PASSWORD=admin
CONFIG_PASSWORD=admin
DEBUG_MODE=false
BROKER_HOST=localhost
BROKER_PORT=1883
BROKER_USERNAME=admin
BROKER_PASSWORD=password
DATABASE_URL=postgresql+asyncpg://hbot:hummingbot-api@localhost:5432/hummingbot_api
GATEWAY_URL=http://localhost:15888
GATEWAY_PASSPHRASE=admin
EOF
    fi
    # Skip setup.sh (requires interactive input), go straight to deploy
    touch .setup-complete
    $DC up -d
fi

# Quick health check (5s max)
echo "Verifying..."
for i in {1..5}; do
    curl -s http://localhost:8000/health >/dev/null 2>&1 && break
    sleep 1
done

echo ""
echo "Done! API running at http://localhost:8000"
echo "Credentials: admin/admin"
echo "Logs: cd $INSTALL_DIR && $DC logs -f"
