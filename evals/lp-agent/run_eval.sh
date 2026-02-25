#!/bin/bash
#
# LP Agent Evaluation Runner
#
# Runs test cases against lp-agent skill via Claude CLI and measures:
#   - Task completion (exit code + output pattern matching)
#   - Duration (wall-clock seconds)
#   - Token usage (input + output tokens via --output-format stream-json)
#   - Number of turns (agent round-trips)
#   - Output length (chars)
#
# Usage:
#   ./run_eval.sh                          # Run all test cases
#   ./run_eval.sh --command start          # Run tests for one command
#   ./run_eval.sh --id explore_top_pools   # Run a single test case
#   ./run_eval.sh --tag conversational     # Run tests matching a tag
#   ./run_eval.sh --dry-run                # List tests without running
#   ./run_eval.sh --model sonnet           # Use a specific model
#
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL_DIR="$REPO_ROOT/skills/lp-agent"
RESULTS_DIR="$SCRIPT_DIR/results"
PROMPTS_FILE="$SCRIPT_DIR/prompts.json"

# Colors
if [ -t 1 ]; then
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    DIM='\033[2m'
    NC='\033[0m'
else
    GREEN='' RED='' YELLOW='' CYAN='' DIM='' NC=''
fi

# Defaults
FILTER_COMMAND=""
FILTER_ID=""
FILTER_TAG=""
DRY_RUN=false
MODEL=""

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --command)  FILTER_COMMAND="$2"; shift 2 ;;
        --id)       FILTER_ID="$2"; shift 2 ;;
        --tag)      FILTER_TAG="$2"; shift 2 ;;
        --model)    MODEL="$2"; shift 2 ;;
        --dry-run)  DRY_RUN=true; shift ;;
        -h|--help)
            echo "Usage: $(basename "$0") [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --command CMD    Run tests for a specific subcommand"
            echo "  --id ID          Run a single test case by ID"
            echo "  --tag TAG        Run tests matching a tag"
            echo "  --model MODEL    Claude model to use (e.g., sonnet, opus, haiku)"
            echo "  --dry-run        List matching tests without running them"
            echo "  -h, --help       Show this help"
            echo ""
            echo "Commands: start, deploy-hummingbot-api, setup-gateway, add-wallet,"
            echo "          explore-pools, select-strategy, run-strategy, analyze-performance"
            echo ""
            echo "Tags: conversational, onboarding, infrastructure, status, install,"
            echo "      config, wallet, pools, discovery, advisory, strategy, analysis"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Validate prompts file
if [[ ! -f "$PROMPTS_FILE" ]]; then
    echo "Error: prompts.json not found at $PROMPTS_FILE"
    exit 1
fi

# Build jq filter for test case selection
JQ_FILTER=".test_cases[]"
if [[ -n "$FILTER_COMMAND" ]]; then
    JQ_FILTER="$JQ_FILTER | select(.command == \"$FILTER_COMMAND\")"
fi
if [[ -n "$FILTER_ID" ]]; then
    JQ_FILTER="$JQ_FILTER | select(.id == \"$FILTER_ID\")"
fi
if [[ -n "$FILTER_TAG" ]]; then
    JQ_FILTER="$JQ_FILTER | select(.tags | index(\"$FILTER_TAG\"))"
fi

# Get matching test cases
CASES=$(jq -c "[$JQ_FILTER]" "$PROMPTS_FILE")
CASE_COUNT=$(echo "$CASES" | jq 'length')

if [[ "$CASE_COUNT" -eq 0 ]]; then
    echo "No test cases match the filter."
    exit 1
fi

# Header
echo ""
echo -e "${CYAN}LP Agent Evaluation${NC}"
echo -e "${CYAN}===================${NC}"
echo ""
echo "Skill: $SKILL_DIR"
[[ -n "$FILTER_COMMAND" ]] && echo "Command: $FILTER_COMMAND"
[[ -n "$FILTER_ID" ]]      && echo "Test ID: $FILTER_ID"
[[ -n "$FILTER_TAG" ]]     && echo "Tag: $FILTER_TAG"
[[ -n "$MODEL" ]]          && echo "Model: $MODEL"
echo "Tests: $CASE_COUNT"
echo ""

# Dry run: just list tests
if [[ "$DRY_RUN" = true ]]; then
    echo -e "${CYAN}Test Cases:${NC}"
    printf "  %-30s %-25s %s\n" "ID" "COMMAND" "DESCRIPTION"
    printf "  %-30s %-25s %s\n" "------------------------------" "-------------------------" "---"
    for i in $(seq 0 $((CASE_COUNT - 1))); do
        id=$(echo "$CASES" | jq -r ".[$i].id")
        cmd=$(echo "$CASES" | jq -r ".[$i].command")
        desc=$(echo "$CASES" | jq -r ".[$i].description")
        printf "  %-30s %-25s %s\n" "$id" "$cmd" "$desc"
    done
    echo ""
    exit 0
fi

# Check claude CLI is available
if ! command -v claude &>/dev/null; then
    echo "Error: claude CLI not found. Install: npm install -g @anthropic-ai/claude-code"
    exit 1
fi

# Prepare results file
mkdir -p "$RESULTS_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILTER_SUFFIX=""
[[ -n "$FILTER_COMMAND" ]] && FILTER_SUFFIX="_${FILTER_COMMAND}"
[[ -n "$FILTER_ID" ]]      && FILTER_SUFFIX="_${FILTER_ID}"
[[ -n "$FILTER_TAG" ]]     && FILTER_SUFFIX="_tag-${FILTER_TAG}"
RESULT_FILE="$RESULTS_DIR/lp-agent${FILTER_SUFFIX}_${TIMESTAMP}.json"

# Temp dir for per-test outputs
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# --- Run each test case ---
PASS_COUNT=0
FAIL_COUNT=0
TOTAL_TOKENS=0
TOTAL_DURATION=0

# Start building results array in memory
RESULTS_JSON="[]"

for i in $(seq 0 $((CASE_COUNT - 1))); do
    id=$(echo "$CASES" | jq -r ".[$i].id")
    cmd=$(echo "$CASES" | jq -r ".[$i].command")
    prompt=$(echo "$CASES" | jq -r ".[$i].prompt")
    description=$(echo "$CASES" | jq -r ".[$i].description")
    expect_patterns=$(echo "$CASES" | jq -c ".[$i].expect_patterns")
    expect_scripts=$(echo "$CASES" | jq -c ".[$i].expect_scripts")
    tags=$(echo "$CASES" | jq -c ".[$i].tags")

    echo -e "${YELLOW}[$((i+1))/$CASE_COUNT]${NC} ${DIM}($cmd)${NC} $id"
    echo -e "  ${DIM}$description${NC}"

    # Build claude command
    CLAUDE_ARGS=(-p --dangerously-skip-permissions --output-format stream-json)
    if [[ -n "$MODEL" ]]; then
        CLAUDE_ARGS+=(--model "$MODEL")
    fi

    # Prepend skill context to prompt
    full_prompt="You have access to the lp-agent skill installed at: $SKILL_DIR
Read the SKILL.md for instructions.

User request: $prompt"

    start_time=$(date +%s.%N 2>/dev/null || date +%s)
    OUTPUT_FILE="$TMPDIR/${id}_output.jsonl"
    TEXT_FILE="$TMPDIR/${id}_text.txt"

    # Run via Claude CLI, capture streaming JSON output
    # Unset CLAUDECODE to allow nested sessions
    set +e
    echo "$full_prompt" | env -u CLAUDECODE claude "${CLAUDE_ARGS[@]}" > "$OUTPUT_FILE" 2>/dev/null
    exit_code=$?
    set -e

    end_time=$(date +%s.%N 2>/dev/null || date +%s)
    duration=$(echo "$end_time - $start_time" | bc 2>/dev/null | xargs printf "%.1f" 2>/dev/null || echo "0")

    # Parse streaming JSON output for metrics
    # Extract the final result message text
    result_text=""
    if [[ -f "$OUTPUT_FILE" ]]; then
        # stream-json: each line is a JSON event. result events have type "result"
        result_text=$(grep '"type":"result"' "$OUTPUT_FILE" | tail -1 | jq -r '.result // ""' 2>/dev/null || true)
        # Fallback: collect all assistant text messages
        if [[ -z "$result_text" ]]; then
            result_text=$(grep '"type":"assistant"' "$OUTPUT_FILE" | jq -r '.message.content[]? | select(.type == "text") | .text' 2>/dev/null | head -200 || true)
        fi
        # Fallback: raw text content from any event
        if [[ -z "$result_text" ]]; then
            result_text=$(jq -r 'select(.type == "content_block_delta") | .delta.text // empty' "$OUTPUT_FILE" 2>/dev/null | head -200 || true)
        fi
    fi
    echo "$result_text" > "$TEXT_FILE"
    output_length=${#result_text}

    # Extract token usage from result event
    RESULT_LINE=$(grep '"type":"result"' "$OUTPUT_FILE" 2>/dev/null | tail -1 || true)

    if [[ -n "$RESULT_LINE" ]]; then
        input_tokens=$(echo "$RESULT_LINE" | jq -r '
          .usage.input_tokens //
          .result_metadata.usage.input_tokens //
          0' 2>/dev/null || echo "0")
        output_tokens=$(echo "$RESULT_LINE" | jq -r '
          .usage.output_tokens //
          .result_metadata.usage.output_tokens //
          0' 2>/dev/null || echo "0")
        num_turns=$(echo "$RESULT_LINE" | jq -r '
          .num_turns //
          .result_metadata.num_turns //
          0' 2>/dev/null || echo "0")
        cost_usd=$(echo "$RESULT_LINE" | jq -r '
          .total_cost_usd //
          .cost_usd //
          0' 2>/dev/null || echo "0")
    else
        input_tokens=0
        output_tokens=0
        num_turns=0
        cost_usd="0"
    fi

    # Sanitize to integers (handle null/empty)
    input_tokens=$((${input_tokens:-0}))
    output_tokens=$((${output_tokens:-0}))
    num_turns=$((${num_turns:-0}))
    [[ "$cost_usd" =~ ^[0-9.]+$ ]] || cost_usd="0"

    total_tokens=$((input_tokens + output_tokens))
    TOTAL_TOKENS=$((TOTAL_TOKENS + total_tokens))
    TOTAL_DURATION=$(echo "$TOTAL_DURATION + $duration" | bc 2>/dev/null || echo "$TOTAL_DURATION")

    # --- Verification ---
    pattern_pass=true
    pattern_results="[]"

    # Check expected output patterns
    if [[ "$expect_patterns" != "[]" && "$expect_patterns" != "null" ]]; then
        for j in $(seq 0 $(($(echo "$expect_patterns" | jq 'length') - 1))); do
            pattern=$(echo "$expect_patterns" | jq -r ".[$j]")
            if echo "$result_text" | grep -qiE "$pattern"; then
                matched=true
            else
                matched=false
                pattern_pass=false
            fi
            pattern_results=$(echo "$pattern_results" | jq \
                --arg p "$pattern" \
                --argjson m "$matched" \
                '. + [{"pattern": $p, "matched": $m}]')
        done
    fi

    # Check expected scripts (in output text — did the agent try to run them?)
    script_pass=true
    script_results="[]"

    if [[ "$expect_scripts" != "[]" && "$expect_scripts" != "null" ]]; then
        for j in $(seq 0 $(($(echo "$expect_scripts" | jq 'length') - 1))); do
            script_alts=$(echo "$expect_scripts" | jq -r ".[$j]")
            # script_alts is "scriptA|scriptB" — any match counts
            matched=false
            IFS='|' read -ra ALTS <<< "$script_alts"
            for alt in "${ALTS[@]}"; do
                if grep -qF "$alt" "$OUTPUT_FILE" 2>/dev/null || echo "$result_text" | grep -qF "$alt"; then
                    matched=true
                    break
                fi
            done
            if [[ "$matched" = false ]]; then
                script_pass=false
            fi
            script_results=$(echo "$script_results" | jq \
                --arg s "$script_alts" \
                --argjson m "$matched" \
                '. + [{"script": $s, "matched": $m}]')
        done
    fi

    # Overall success
    if [[ $exit_code -eq 0 && "$pattern_pass" = true && "$script_pass" = true ]]; then
        success=true
        PASS_COUNT=$((PASS_COUNT + 1))
        echo -e "  ${GREEN}PASS${NC} (${duration}s, ${total_tokens} tokens, ${num_turns} turns)"
    else
        success=false
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo -e "  ${RED}FAIL${NC} (${duration}s, ${total_tokens} tokens, ${num_turns} turns)"
        [[ $exit_code -ne 0 ]] && echo -e "    ${RED}exit_code: $exit_code${NC}"
        [[ "$pattern_pass" != true ]] && echo -e "    ${RED}missing output patterns${NC}"
        [[ "$script_pass" != true ]] && echo -e "    ${RED}expected scripts not found in output${NC}"
    fi

    # Append result to JSON array
    RESULT_ENTRY=$(jq -n \
        --arg id "$id" \
        --arg command "$cmd" \
        --arg description "$description" \
        --argjson success "$success" \
        --argjson exit_code "$exit_code" \
        --arg duration_seconds "$duration" \
        --argjson input_tokens "$input_tokens" \
        --argjson output_tokens "$output_tokens" \
        --argjson total_tokens "$total_tokens" \
        --argjson num_turns "$num_turns" \
        --arg cost_usd "$cost_usd" \
        --argjson output_length "$output_length" \
        --argjson pattern_results "$pattern_results" \
        --argjson script_results "$script_results" \
        --argjson tags "$tags" \
        '{
            id: $id,
            command: $command,
            description: $description,
            success: $success,
            exit_code: $exit_code,
            duration_seconds: ($duration_seconds | tonumber),
            tokens: {
                input: $input_tokens,
                output: $output_tokens,
                total: $total_tokens
            },
            num_turns: $num_turns,
            cost_usd: ($cost_usd | tonumber),
            output_length: $output_length,
            verification: {
                patterns: $pattern_results,
                scripts: $script_results
            },
            tags: $tags
        }')
    RESULTS_JSON=$(echo "$RESULTS_JSON" | jq --argjson entry "$RESULT_ENTRY" '. + [$entry]')

    echo ""
done

# --- Write results file ---
MODEL_INFO="${MODEL:-default}"
jq -n \
    --arg skill "lp-agent" \
    --arg model "$MODEL_INFO" \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --argjson total "$CASE_COUNT" \
    --argjson passed "$PASS_COUNT" \
    --argjson failed "$FAIL_COUNT" \
    --argjson total_tokens "$TOTAL_TOKENS" \
    --arg total_duration "$TOTAL_DURATION" \
    --arg filter_command "$FILTER_COMMAND" \
    --arg filter_tag "$FILTER_TAG" \
    --argjson results "$RESULTS_JSON" \
    '{
        skill: $skill,
        model: $model,
        timestamp: $timestamp,
        summary: {
            total: $total,
            passed: $passed,
            failed: $failed,
            pass_rate: (if $total > 0 then ($passed / $total * 100 | floor) else 0 end),
            total_tokens: $total_tokens,
            total_duration_seconds: ($total_duration | tonumber),
            avg_duration_seconds: (if $total > 0 then ($total_duration | tonumber) / $total | . * 10 | floor | . / 10 else 0 end),
            avg_tokens_per_test: (if $total > 0 then ($total_tokens / $total | floor) else 0 end)
        },
        filters: {
            command: (if $filter_command != "" then $filter_command else null end),
            tag: (if $filter_tag != "" then $filter_tag else null end)
        },
        results: $results
    }' > "$RESULT_FILE"

# --- Summary ---
echo -e "${CYAN}Summary${NC}"
echo -e "${CYAN}=======${NC}"
echo ""
printf "  %-20s %s\n" "Total tests:" "$CASE_COUNT"
printf "  %-20s ${GREEN}%s${NC}\n" "Passed:" "$PASS_COUNT"
printf "  %-20s ${RED}%s${NC}\n" "Failed:" "$FAIL_COUNT"
printf "  %-20s %s%%\n" "Pass rate:" "$((PASS_COUNT * 100 / (CASE_COUNT > 0 ? CASE_COUNT : 1)))"
printf "  %-20s %s\n" "Total tokens:" "$TOTAL_TOKENS"
printf "  %-20s %ss\n" "Total duration:" "$TOTAL_DURATION"
echo ""
echo "Results: $RESULT_FILE"
echo ""

# Exit with failure if any test failed
[[ "$FAIL_COUNT" -gt 0 ]] && exit 1
exit 0
