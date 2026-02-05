#!/bin/bash
# Create a new LP position via LP executor
#
# Usage:
#   ./create_lp_position.sh --connector meteora --network solana-mainnet-beta \
#       --pool <address> --pair SOL-USDC --quote-amount 100 --width 5.0
#
# Position types:
#   - Double-sided: Provide both --base-amount and --quote-amount
#   - Quote-only (buy base): Provide only --quote-amount (range below current price)
#   - Base-only (sell base): Provide only --base-amount (range above current price)

set -e

# Load .env if present
for f in .env ~/.hummingbot/.env ~/.env; do [ -f "$f" ] && source "$f" && break; done
API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-admin}"

# Defaults
CONNECTOR="meteora"
NETWORK="solana-mainnet-beta"
POOL=""
PAIR=""
BASE_AMOUNT="0"
QUOTE_AMOUNT="0"
WIDTH="5.0"
LOWER_PRICE=""
UPPER_PRICE=""
STRATEGY_TYPE=""  # Meteora: 0=Spot, 1=Curve, 2=Bid-Ask
ACCOUNT="master_account"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --connector) CONNECTOR="$2"; shift 2 ;;
        --network) NETWORK="$2"; shift 2 ;;
        --pool) POOL="$2"; shift 2 ;;
        --pair) PAIR="$2"; shift 2 ;;
        --base-amount) BASE_AMOUNT="$2"; shift 2 ;;
        --quote-amount) QUOTE_AMOUNT="$2"; shift 2 ;;
        --width) WIDTH="$2"; shift 2 ;;
        --lower-price) LOWER_PRICE="$2"; shift 2 ;;
        --upper-price) UPPER_PRICE="$2"; shift 2 ;;
        --strategy-type) STRATEGY_TYPE="$2"; shift 2 ;;
        --account) ACCOUNT="$2"; shift 2 ;;
        --api-url) API_URL="$2"; shift 2 ;;
        --api-user) API_USER="$2"; shift 2 ;;
        --api-pass) API_PASS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Validate required parameters
if [ -z "$POOL" ] || [ -z "$PAIR" ]; then
    cat << EOF
{
    "error": "Missing required parameters",
    "message": "Pool address and trading pair are required",
    "usage": "./create_lp_position.sh --connector meteora --network solana-mainnet-beta --pool <address> --pair SOL-USDC --quote-amount 100",
    "required": ["--pool", "--pair"],
    "optional": ["--base-amount", "--quote-amount", "--width", "--lower-price", "--upper-price", "--strategy-type"]
}
EOF
    exit 1
fi

# Check that at least one amount is provided
if [ "$BASE_AMOUNT" = "0" ] && [ "$QUOTE_AMOUNT" = "0" ]; then
    cat << EOF
{
    "error": "No tokens specified",
    "message": "Provide at least --base-amount or --quote-amount",
    "examples": [
        "./create_lp_position.sh --pool $POOL --pair $PAIR --quote-amount 100 --width 5.0",
        "./create_lp_position.sh --pool $POOL --pair $PAIR --base-amount 1.0 --quote-amount 100 --width 5.0"
    ]
}
EOF
    exit 1
fi

# Extract base and quote tokens from pair
BASE_TOKEN=$(echo "$PAIR" | cut -d'-' -f1)
QUOTE_TOKEN=$(echo "$PAIR" | cut -d'-' -f2)

# Determine position side based on amounts
# 0 = BOTH (double-sided), 1 = BUY (quote-only), 2 = SELL (base-only)
if [ "$BASE_AMOUNT" != "0" ] && [ "$QUOTE_AMOUNT" != "0" ]; then
    SIDE=0
    POSITION_TYPE="double_sided"
elif [ "$QUOTE_AMOUNT" != "0" ]; then
    SIDE=1
    POSITION_TYPE="quote_only_buy"
else
    SIDE=2
    POSITION_TYPE="base_only_sell"
fi

# Get current price if we need to calculate bounds
if [ -z "$LOWER_PRICE" ] || [ -z "$UPPER_PRICE" ]; then
    POOL_INFO=$(curl -s -u "$API_USER:$API_PASS" \
        "$API_URL/gateway/clmm/pool-info?connector=$CONNECTOR&network=$NETWORK&pool_address=$POOL")

    CURRENT_PRICE=$(echo "$POOL_INFO" | jq -r '.current_price // "0"')

    if [ "$CURRENT_PRICE" = "0" ] || [ "$CURRENT_PRICE" = "null" ]; then
        cat << EOF
{
    "error": "Could not get current price",
    "message": "Failed to fetch pool info to calculate price bounds",
    "solution": "Provide explicit --lower-price and --upper-price"
}
EOF
        exit 1
    fi

    # Calculate price bounds based on position type and width
    WIDTH_FACTOR=$(echo "scale=6; $WIDTH / 100" | bc -l)

    if [ "$SIDE" = "0" ]; then
        # Double-sided: split width evenly around current price
        HALF_WIDTH=$(echo "scale=6; $WIDTH_FACTOR / 2" | bc -l)
        LOWER_PRICE=$(echo "scale=6; $CURRENT_PRICE * (1 - $HALF_WIDTH)" | bc -l)
        UPPER_PRICE=$(echo "scale=6; $CURRENT_PRICE * (1 + $HALF_WIDTH)" | bc -l)
    elif [ "$SIDE" = "1" ]; then
        # Quote-only (buy): full width below current price
        LOWER_PRICE=$(echo "scale=6; $CURRENT_PRICE * (1 - $WIDTH_FACTOR)" | bc -l)
        UPPER_PRICE="$CURRENT_PRICE"
    else
        # Base-only (sell): full width above current price
        LOWER_PRICE="$CURRENT_PRICE"
        UPPER_PRICE=$(echo "scale=6; $CURRENT_PRICE * (1 + $WIDTH_FACTOR)" | bc -l)
    fi
fi

# Build executor config
EXECUTOR_CONFIG=$(jq -n \
    --arg type "lp_executor" \
    --arg connector "$CONNECTOR/clmm" \
    --arg pool "$POOL" \
    --arg pair "$PAIR" \
    --arg base_token "$BASE_TOKEN" \
    --arg quote_token "$QUOTE_TOKEN" \
    --arg base_amount "$BASE_AMOUNT" \
    --arg quote_amount "$QUOTE_AMOUNT" \
    --arg lower_price "$LOWER_PRICE" \
    --arg upper_price "$UPPER_PRICE" \
    --argjson side "$SIDE" \
    '{
        type: $type,
        connector_name: $connector,
        pool_address: $pool,
        trading_pair: $pair,
        base_token: $base_token,
        quote_token: $quote_token,
        base_amount: ($base_amount | tonumber),
        quote_amount: ($quote_amount | tonumber),
        lower_price: ($lower_price | tonumber),
        upper_price: ($upper_price | tonumber),
        side: $side,
        keep_position: false
    }')

# Add extra_params for connector-specific options (e.g., Meteora strategy type)
if [ -n "$STRATEGY_TYPE" ]; then
    EXECUTOR_CONFIG=$(echo "$EXECUTOR_CONFIG" | jq --argjson st "$STRATEGY_TYPE" '. + {extra_params: {strategyType: $st}}')
fi

# Build request
REQUEST=$(jq -n \
    --argjson config "$EXECUTOR_CONFIG" \
    --arg account "$ACCOUNT" \
    '{executor_config: $config, account_name: $account}')

# Create executor
RESPONSE=$(curl -s -X POST \
    -u "$API_USER:$API_PASS" \
    -H "Content-Type: application/json" \
    -d "$REQUEST" \
    "$API_URL/executors/")

# Check for errors
if echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "{\"error\": \"Failed to create LP position\", \"detail\": $RESPONSE, \"request\": $REQUEST}"
    exit 1
fi

# Extract executor ID
EXECUTOR_ID=$(echo "$RESPONSE" | jq -r '.id // .executor_id // "unknown"')

cat << EOF
{
    "action": "lp_position_created",
    "message": "Successfully created LP position",
    "executor_id": "$EXECUTOR_ID",
    "position_type": "$POSITION_TYPE",
    "config": {
        "connector": "$CONNECTOR",
        "network": "$NETWORK",
        "pool": "$POOL",
        "pair": "$PAIR",
        "base_amount": $BASE_AMOUNT,
        "quote_amount": $QUOTE_AMOUNT,
        "lower_price": $LOWER_PRICE,
        "upper_price": $UPPER_PRICE,
        "width_pct": $WIDTH
    },
    "response": $RESPONSE,
    "next_steps": [
        "Monitor position: ./get_lp_position.sh --id $EXECUTOR_ID",
        "List all positions: ./list_lp_positions.sh",
        "Collect fees: ./collect_fees.sh --id $EXECUTOR_ID",
        "Close position: ./close_lp_position.sh --id $EXECUTOR_ID"
    ]
}
EOF
