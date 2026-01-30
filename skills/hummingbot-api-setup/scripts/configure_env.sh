#!/bin/bash
# Configure Hummingbot API environment variables
# Usage: ./configure_env.sh [--url URL] [--user USER] [--pass PASS] [--output PATH]
#
# Creates or updates .env file with Hummingbot API configuration

set -e

# Defaults
API_URL="http://localhost:8000"
API_USER="admin"
API_PASS="admin"
OUTPUT_PATH="$HOME/.hummingbot/.env"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url) API_URL="$2"; shift 2 ;;
        --user) API_USER="$2"; shift 2 ;;
        --pass) API_PASS="$2"; shift 2 ;;
        --output) OUTPUT_PATH="$2"; shift 2 ;;
        --show) SHOW_ONLY=true; shift ;;
        *) shift ;;
    esac
done

# If show only, display current config and exit
if [ "$SHOW_ONLY" = true ]; then
    echo "Checking for .env files..."

    for f in .env "$HOME/.hummingbot/.env" "$HOME/.env"; do
        if [ -f "$f" ]; then
            echo ""
            echo "Found: $f"
            grep -E "^API_URL|^API_USER|^API_PASS" "$f" 2>/dev/null | sed 's/API_PASS=.*/API_PASS=***/' || echo "  (no API config found)"
        fi
    done

    echo ""
    echo "Current effective settings:"
    # Load existing
    for f in .env "$HOME/.hummingbot/.env" "$HOME/.env"; do [ -f "$f" ] && source "$f" && break; done
    echo "  API_URL: ${API_URL:-http://localhost:8000}"
    echo "  API_USER: ${API_USER:-admin}"
    echo "  API_PASS: ***"
    exit 0
fi

# Create directory if needed
OUTPUT_DIR=$(dirname "$OUTPUT_PATH")
if [ ! -d "$OUTPUT_DIR" ]; then
    mkdir -p "$OUTPUT_DIR"
    echo "Created directory: $OUTPUT_DIR"
fi

# Write .env file
cat > "$OUTPUT_PATH" << EOF
# Hummingbot API Configuration
API_URL=$API_URL
API_USER=$API_USER
API_PASS=$API_PASS
EOF

chmod 600 "$OUTPUT_PATH"

cat << EOF
{
    "status": "success",
    "action": "env_configured",
    "path": "$OUTPUT_PATH",
    "config": {
        "api_url": "$API_URL",
        "api_user": "$API_USER",
        "api_pass": "***"
    },
    "note": "All Hummingbot skills will now use these settings"
}
EOF
