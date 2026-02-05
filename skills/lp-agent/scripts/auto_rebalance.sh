#!/bin/bash
# Auto-rebalance: Monitor position and rebalance when out of range for specified time
#
# Usage:
#   ./auto_rebalance.sh --id <executor_id> --delay 60
#   ./auto_rebalance.sh --id <executor_id> --delay 300 --width 5.0
#
# This script runs continuously and:
# 1. Monitors the position state
# 2. When OUT_OF_RANGE for longer than --delay seconds, triggers rebalance
# 3. Continues monitoring the new position
#
# Press Ctrl+C to stop.

set -e

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do [ -f "$f" ] && source "$f" && break; done
API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

EXECUTOR_ID=""
DELAY=60  # Seconds to wait before rebalancing
WIDTH="5.0"
POLL_INTERVAL=10  # Check every 10 seconds
ACCOUNT="master_account"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --id) EXECUTOR_ID="$2"; shift 2 ;;
        --delay) DELAY="$2"; shift 2 ;;
        --width) WIDTH="$2"; shift 2 ;;
        --poll) POLL_INTERVAL="$2"; shift 2 ;;
        --account) ACCOUNT="$2"; shift 2 ;;
        --api-url) API_URL="$2"; shift 2 ;;
        --api-user) API_USER="$2"; shift 2 ;;
        --api-pass) API_PASS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

if [ -z "$EXECUTOR_ID" ]; then
    cat << EOF
{
    "error": "Missing required parameter",
    "message": "Executor ID is required",
    "usage": "./auto_rebalance.sh --id <executor_id> --delay 60",
    "parameters": {
        "--id": "Executor ID to monitor (required)",
        "--delay": "Seconds out of range before rebalancing (default: 60)",
        "--width": "Position width % for rebalanced positions (default: 5.0)",
        "--poll": "Polling interval in seconds (default: 10)"
    }
}
EOF
    exit 1
fi

# Get script directory for calling rebalance script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting auto-rebalance monitor..." >&2
echo "  Executor ID: $EXECUTOR_ID" >&2
echo "  Rebalance delay: ${DELAY}s" >&2
echo "  Position width: ${WIDTH}%" >&2
echo "  Poll interval: ${POLL_INTERVAL}s" >&2
echo "" >&2
echo "Press Ctrl+C to stop." >&2
echo "" >&2

# Track when we first saw out of range
OUT_OF_RANGE_START=""

while true; do
    # Fetch position state
    POSITION=$(curl -s -u "$API_USER:$API_PASS" "$API_URL/executors/$EXECUTOR_ID" 2>/dev/null)

    if echo "$POSITION" | jq -e '.detail' > /dev/null 2>&1; then
        echo "[$(date '+%H:%M:%S')] Error fetching position: $(echo "$POSITION" | jq -r '.detail')" >&2
        sleep "$POLL_INTERVAL"
        continue
    fi

    STATUS=$(echo "$POSITION" | jq -r '.status // "unknown"')

    # If executor is terminated, exit
    if [ "$STATUS" = "TERMINATED" ]; then
        echo "[$(date '+%H:%M:%S')] Position terminated. Exiting auto-rebalance." >&2
        cat << EOF
{
    "action": "auto_rebalance_stopped",
    "reason": "Position terminated",
    "executor_id": "$EXECUTOR_ID"
}
EOF
        exit 0
    fi

    CUSTOM_INFO=$(echo "$POSITION" | jq '.custom_info // {}')
    STATE=$(echo "$CUSTOM_INFO" | jq -r '.state // "unknown"')
    CURRENT_PRICE=$(echo "$CUSTOM_INFO" | jq -r '.current_price // 0')
    LOWER_PRICE=$(echo "$CUSTOM_INFO" | jq -r '.lower_price // 0')
    UPPER_PRICE=$(echo "$CUSTOM_INFO" | jq -r '.upper_price // 0')

    CURRENT_TIME=$(date +%s)

    if [ "$STATE" = "OUT_OF_RANGE" ]; then
        if [ -z "$OUT_OF_RANGE_START" ]; then
            OUT_OF_RANGE_START="$CURRENT_TIME"
            echo "[$(date '+%H:%M:%S')] Position went OUT_OF_RANGE. Starting timer..." >&2
        fi

        ELAPSED=$((CURRENT_TIME - OUT_OF_RANGE_START))
        echo "[$(date '+%H:%M:%S')] OUT_OF_RANGE for ${ELAPSED}s / ${DELAY}s (price: $CURRENT_PRICE, range: $LOWER_PRICE - $UPPER_PRICE)" >&2

        if [ "$ELAPSED" -ge "$DELAY" ]; then
            echo "[$(date '+%H:%M:%S')] Rebalance threshold reached. Triggering rebalance..." >&2

            # Call rebalance script
            REBALANCE_RESULT=$("$SCRIPT_DIR/rebalance_position.sh" \
                --id "$EXECUTOR_ID" \
                --width "$WIDTH" \
                --account "$ACCOUNT" \
                --api-url "$API_URL" \
                --api-user "$API_USER" \
                --api-pass "$API_PASS" 2>&1)

            # Extract new executor ID from rebalance result
            NEW_ID=$(echo "$REBALANCE_RESULT" | jq -r '.new_position.executor_id // ""' 2>/dev/null)

            if [ -n "$NEW_ID" ] && [ "$NEW_ID" != "null" ] && [ "$NEW_ID" != "" ]; then
                echo "[$(date '+%H:%M:%S')] Rebalance successful. New executor: $NEW_ID" >&2
                EXECUTOR_ID="$NEW_ID"
                OUT_OF_RANGE_START=""

                # Output rebalance event
                echo "$REBALANCE_RESULT"
            else
                echo "[$(date '+%H:%M:%S')] Rebalance failed: $REBALANCE_RESULT" >&2
                # Reset timer to try again
                OUT_OF_RANGE_START=""
            fi
        fi

    elif [ "$STATE" = "IN_RANGE" ]; then
        if [ -n "$OUT_OF_RANGE_START" ]; then
            echo "[$(date '+%H:%M:%S')] Position returned to IN_RANGE. Resetting timer." >&2
            OUT_OF_RANGE_START=""
        fi
        echo "[$(date '+%H:%M:%S')] IN_RANGE (price: $CURRENT_PRICE, range: $LOWER_PRICE - $UPPER_PRICE)" >&2

    elif [ "$STATE" = "OPENING" ] || [ "$STATE" = "CLOSING" ]; then
        echo "[$(date '+%H:%M:%S')] Position state: $STATE - waiting..." >&2
        OUT_OF_RANGE_START=""

    else
        echo "[$(date '+%H:%M:%S')] Unknown state: $STATE" >&2
    fi

    sleep "$POLL_INTERVAL"
done
