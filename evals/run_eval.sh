#!/bin/bash
#
# Minimal skill evaluation runner
# Usage: ./run_eval.sh <skill-name> [prompt-id] [--direct]
#
# --direct: Run scripts directly without Claude (measures script performance)
#
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$(dirname "$SCRIPT_DIR")/skills"
RESULTS_DIR="$SCRIPT_DIR/results"

# Parse args
SKILL_NAME=""
PROMPT_ID="all"
DIRECT_MODE=false

for arg in "$@"; do
    case $arg in
        --direct) DIRECT_MODE=true ;;
        -*) ;;
        *)
            if [[ -z "$SKILL_NAME" ]]; then
                SKILL_NAME="$arg"
            else
                PROMPT_ID="$arg"
            fi
            ;;
    esac
done

if [[ -z "$SKILL_NAME" ]]; then
    echo "Usage: $0 <skill-name> [prompt-id] [--direct]"
    echo ""
    echo "Options:"
    echo "  --direct  Run scripts directly (skip Claude)"
    echo ""
    echo "Skills:"
    ls -1 "$SKILLS_DIR" | grep -E "hummingbot" | sed 's/^/  /'
    exit 1
fi

SKILL_PATH="$SKILLS_DIR/$SKILL_NAME"

if [[ ! -d "$SKILL_PATH" ]]; then
    echo "Error: Skill not found: $SKILL_PATH"
    exit 1
fi

mkdir -p "$RESULTS_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MODE_SUFFIX=$($DIRECT_MODE && echo "_direct" || echo "")
RESULT_FILE="$RESULTS_DIR/${SKILL_NAME}${MODE_SUFFIX}_${TIMESTAMP}.json"

echo ""
echo "Skill Evaluation: $SKILL_NAME"
$DIRECT_MODE && echo "Mode: DIRECT (script only)" || echo "Mode: CLAUDE (end-to-end)"
echo "================================"
echo ""

# Script mapping for direct mode
get_script() {
    case "$1" in
        install_api) echo "install_api.sh" ;;
        check_dependencies) echo "check_dependencies.sh" ;;
        health_check) echo "health_check.sh" ;;
        install_mcp) echo "install_mcp.sh --agent claude-code" ;;
        full_setup) echo "install_api.sh && ./install_mcp.sh --agent claude-code" ;;
        *) echo "" ;;
    esac
}

# Get prompt count
PROMPT_COUNT=$(jq '.prompts | length' "$SCRIPT_DIR/prompts.json")

# Start JSON
echo "{" > "$RESULT_FILE"
echo "  \"skill\": \"$SKILL_NAME\"," >> "$RESULT_FILE"
echo "  \"mode\": \"$($DIRECT_MODE && echo "direct" || echo "claude")\"," >> "$RESULT_FILE"
echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"," >> "$RESULT_FILE"
echo "  \"results\": [" >> "$RESULT_FILE"

FIRST=true

for i in $(seq 0 $((PROMPT_COUNT - 1))); do
    id=$(jq -r ".prompts[$i].id" "$SCRIPT_DIR/prompts.json")
    prompt=$(jq -r ".prompts[$i].prompt" "$SCRIPT_DIR/prompts.json")
    verify=$(jq -r ".prompts[$i].verify" "$SCRIPT_DIR/prompts.json")

    if [[ "$PROMPT_ID" != "all" && "$id" != "$PROMPT_ID" ]]; then
        continue
    fi

    echo -n "[$id] "

    start_time=$(date +%s.%N)

    set +e
    if $DIRECT_MODE; then
        # Run script directly
        script=$(get_script "$id")
        if [[ -n "$script" ]]; then
            output=$(cd "$SKILL_PATH/scripts" && bash -c "./$script" 2>&1)
            exit_code=$?
        else
            output="No script mapping for $id"
            exit_code=1
        fi
    else
        # Run via Claude - use direct prompt with skill path
        full_prompt="$prompt
Skill path: $SKILL_PATH"
        output=$(echo "$full_prompt" | claude -p \
            --dangerously-skip-permissions \
            --allowedTools "Bash" \
            2>&1)
        exit_code=$?
    fi
    set -e

    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc | xargs printf "%.1f")

    if [[ $exit_code -eq 0 ]]; then
        success="true"
        echo "PASS (${duration}s)"
    else
        success="false"
        echo "FAIL (${duration}s)"
    fi

    # Append comma if not first
    if [[ "$FIRST" != "true" ]]; then
        echo "," >> "$RESULT_FILE"
    fi
    FIRST=false

    cat >> "$RESULT_FILE" << EOF
    {
      "id": "$id",
      "success": $success,
      "duration_seconds": $duration,
      "exit_code": $exit_code
    }
EOF

done

echo "" >> "$RESULT_FILE"
echo "  ]" >> "$RESULT_FILE"
echo "}" >> "$RESULT_FILE"

echo ""
echo "Results: $RESULT_FILE"
