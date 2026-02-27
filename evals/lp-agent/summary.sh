#!/bin/bash
#
# Analyze lp-agent evaluation results
#
# Usage:
#   ./summary.sh                     # Analyze latest result
#   ./summary.sh <result-file>       # Analyze specific file
#   ./summary.sh --compare           # Compare two most recent runs
#   ./summary.sh --all               # Summarize all historical runs
#
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/results"

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

# Parse args
MODE="latest"
FILE=""
for arg in "$@"; do
    case $arg in
        --compare) MODE="compare" ;;
        --all)     MODE="all" ;;
        --help|-h)
            echo "Usage: $(basename "$0") [OPTIONS] [result-file]"
            echo ""
            echo "Options:"
            echo "  --compare    Compare two most recent runs"
            echo "  --all        Summarize all historical runs"
            echo "  -h, --help   Show this help"
            exit 0
            ;;
        *) FILE="$arg" ;;
    esac
done

# Find result files
get_latest() {
    ls -t "$RESULTS_DIR"/lp-agent*.json 2>/dev/null | head -1
}

get_all() {
    ls -t "$RESULTS_DIR"/lp-agent*.json 2>/dev/null
}

# --- Pretty-print one result file ---
show_result() {
    local file="$1"
    local data
    data=$(cat "$file")

    echo -e "${CYAN}$(basename "$file")${NC}"
    echo -e "${DIM}$(echo "$data" | jq -r '.timestamp')${NC}  Model: $(echo "$data" | jq -r '.model')"
    echo ""

    # Overall summary
    local total passed failed pass_rate total_tokens avg_dur avg_tok
    total=$(echo "$data" | jq '.summary.total')
    passed=$(echo "$data" | jq '.summary.passed')
    failed=$(echo "$data" | jq '.summary.failed')
    pass_rate=$(echo "$data" | jq '.summary.pass_rate')
    total_tokens=$(echo "$data" | jq '.summary.total_tokens')
    avg_dur=$(echo "$data" | jq '.summary.avg_duration_seconds')
    avg_tok=$(echo "$data" | jq '.summary.avg_tokens_per_test')

    printf "  %-22s " "Pass rate:"
    if [[ "$pass_rate" -ge 80 ]]; then
        echo -e "${GREEN}${passed}/${total} (${pass_rate}%)${NC}"
    elif [[ "$pass_rate" -ge 50 ]]; then
        echo -e "${YELLOW}${passed}/${total} (${pass_rate}%)${NC}"
    else
        echo -e "${RED}${passed}/${total} (${pass_rate}%)${NC}"
    fi
    printf "  %-22s %s\n" "Total tokens:" "$total_tokens"
    printf "  %-22s %ss\n" "Avg duration/test:" "$avg_dur"
    printf "  %-22s %s\n" "Avg tokens/test:" "$avg_tok"
    echo ""

    # Per-command breakdown
    echo -e "  ${CYAN}By Command:${NC}"
    echo ""
    printf "    %-28s %8s %10s %10s %8s\n" "Command" "Pass" "Tokens" "Duration" "Turns"
    printf "    %-28s %8s %10s %10s %8s\n" "----------------------------" "--------" "----------" "----------" "--------"

    echo "$data" | jq -r '
        .results | group_by(.command) | .[] |
        {
            command: .[0].command,
            total: length,
            passed: [.[] | select(.success)] | length,
            tokens: [.[].tokens.total] | add,
            duration: [.[].duration_seconds] | add | . * 10 | floor | . / 10,
            turns: [.[].num_turns] | add
        } |
        "\(.command)|\(.passed)/\(.total)|\(.tokens)|\(.duration)|\(.turns)"
    ' | while IFS='|' read -r cmd pass tok dur turns; do
        printf "    %-28s %8s %10s %9ss %8s\n" "$cmd" "$pass" "$tok" "$dur" "$turns"
    done
    echo ""

    # Per-test details
    echo -e "  ${CYAN}Test Results:${NC}"
    echo ""
    printf "    %-30s %-24s %8s %8s %8s %6s\n" "ID" "Command" "Status" "Tokens" "Turns" "Secs"
    printf "    %-30s %-24s %8s %8s %8s %6s\n" "------------------------------" "------------------------" "--------" "--------" "--------" "------"

    echo "$data" | jq -r '
        .results[] |
        "\(.id)|\(.command)|\(.success)|\(.tokens.total)|\(.num_turns)|\(.duration_seconds)"
    ' | while IFS='|' read -r id cmd success tok turns dur; do
        if [[ "$success" = "true" ]]; then
            status="${GREEN}  PASS${NC}"
        else
            status="${RED}  FAIL${NC}"
        fi
        printf "    %-30s %-24s %b %8s %8s %6s\n" "$id" "$cmd" "$status" "$tok" "$turns" "$dur"
    done
    echo ""

    # Show failures detail
    local fail_count
    fail_count=$(echo "$data" | jq '[.results[] | select(.success == false)] | length')
    if [[ "$fail_count" -gt 0 ]]; then
        echo -e "  ${RED}Failures:${NC}"
        echo ""
        echo "$data" | jq -r '
            .results[] | select(.success == false) |
            "    \(.id) (\(.command))\n" +
            (if .exit_code != 0 then "      exit_code: \(.exit_code)\n" else "" end) +
            (.verification.patterns // [] | map(select(.matched == false)) | if length > 0 then
                "      missing patterns: " + (map(.pattern) | join(", ")) + "\n"
            else "" end) +
            (.verification.scripts // [] | map(select(.matched == false)) | if length > 0 then
                "      missing scripts: " + (map(.script) | join(", ")) + "\n"
            else "" end)
        '
        echo ""
    fi
}

# --- Compare two result files ---
compare_results() {
    local files
    mapfile -t files < <(get_all)

    if [[ ${#files[@]} -lt 2 ]]; then
        echo "Need at least 2 result files to compare."
        echo "Run: ./run_eval.sh  (at least twice)"
        exit 1
    fi

    local file_a="${files[0]}"
    local file_b="${files[1]}"

    echo -e "${CYAN}Comparison${NC}"
    echo -e "${CYAN}==========${NC}"
    echo ""
    echo "  A (newer): $(basename "$file_a")"
    echo "  B (older): $(basename "$file_b")"
    echo ""

    printf "  %-22s %15s %15s %8s\n" "Metric" "A" "B" "Delta"
    printf "  %-22s %15s %15s %8s\n" "----------------------" "---------------" "---------------" "--------"

    local a_pass a_total a_tok a_dur b_pass b_total b_tok b_dur
    a_pass=$(jq '.summary.passed' "$file_a")
    a_total=$(jq '.summary.total' "$file_a")
    a_tok=$(jq '.summary.total_tokens' "$file_a")
    a_dur=$(jq '.summary.total_duration_seconds' "$file_a")
    b_pass=$(jq '.summary.passed' "$file_b")
    b_total=$(jq '.summary.total' "$file_b")
    b_tok=$(jq '.summary.total_tokens' "$file_b")
    b_dur=$(jq '.summary.total_duration_seconds' "$file_b")

    local a_rate=$((a_pass * 100 / (a_total > 0 ? a_total : 1)))
    local b_rate=$((b_pass * 100 / (b_total > 0 ? b_total : 1)))
    local rate_delta=$((a_rate - b_rate))

    printf "  %-22s %14s%% %14s%% %+7d%%\n" "Pass rate" "$a_rate" "$b_rate" "$rate_delta"
    printf "  %-22s %15s %15s %+8d\n" "Total tokens" "$a_tok" "$b_tok" "$((a_tok - b_tok))"
    printf "  %-22s %14ss %14ss\n" "Total duration" "$a_dur" "$b_dur"
    echo ""

    # Per-test comparison
    echo -e "  ${CYAN}Per-Test:${NC}"
    echo ""
    printf "    %-28s %8s %8s %10s %10s\n" "ID" "A" "B" "A tokens" "B tokens"
    printf "    %-28s %8s %8s %10s %10s\n" "----------------------------" "--------" "--------" "----------" "----------"

    jq -r '.results[].id' "$file_a" | while read -r id; do
        a_success=$(jq -r ".results[] | select(.id == \"$id\") | .success" "$file_a" 2>/dev/null || echo "N/A")
        b_success=$(jq -r ".results[] | select(.id == \"$id\") | .success" "$file_b" 2>/dev/null || echo "N/A")
        a_tokens=$(jq -r ".results[] | select(.id == \"$id\") | .tokens.total" "$file_a" 2>/dev/null || echo "0")
        b_tokens=$(jq -r ".results[] | select(.id == \"$id\") | .tokens.total" "$file_b" 2>/dev/null || echo "0")

        if [[ "$a_success" = "true" ]]; then a_display="${GREEN}pass${NC}"; else a_display="${RED}fail${NC}"; fi
        if [[ "$b_success" = "true" ]]; then b_display="${GREEN}pass${NC}"; else b_display="${RED}fail${NC}"; fi

        printf "    %-28s %b   %b   %10s %10s\n" "$id" "$a_display" "$b_display" "$a_tokens" "$b_tokens"
    done
    echo ""
}

# --- Summarize all historical runs ---
show_all() {
    local files
    mapfile -t files < <(get_all)

    if [[ ${#files[@]} -eq 0 ]]; then
        echo "No result files found in $RESULTS_DIR"
        exit 1
    fi

    echo -e "${CYAN}All Evaluation Runs${NC}"
    echo -e "${CYAN}===================${NC}"
    echo ""
    printf "  %-40s %6s %8s %10s %10s\n" "File" "Pass%" "Tests" "Tokens" "Duration"
    printf "  %-40s %6s %8s %10s %10s\n" "----------------------------------------" "------" "--------" "----------" "----------"

    for file in "${files[@]}"; do
        local fname pass_rate total tokens dur
        fname=$(basename "$file")
        pass_rate=$(jq '.summary.pass_rate' "$file")
        total=$(jq '.summary.total' "$file")
        tokens=$(jq '.summary.total_tokens' "$file")
        dur=$(jq '.summary.total_duration_seconds' "$file")

        if [[ "$pass_rate" -ge 80 ]]; then
            rate_color="$GREEN"
        elif [[ "$pass_rate" -ge 50 ]]; then
            rate_color="$YELLOW"
        else
            rate_color="$RED"
        fi

        printf "  %-40s ${rate_color}%5s%%${NC} %8s %10s %9ss\n" "$fname" "$pass_rate" "$total" "$tokens" "$dur"
    done
    echo ""
}

# --- Main ---
case "$MODE" in
    latest)
        if [[ -n "$FILE" ]]; then
            if [[ ! -f "$FILE" ]]; then
                echo "File not found: $FILE"
                exit 1
            fi
            show_result "$FILE"
        else
            LATEST=$(get_latest)
            if [[ -z "$LATEST" ]]; then
                echo "No result files found. Run: ./run_eval.sh"
                exit 1
            fi
            show_result "$LATEST"
        fi
        ;;
    compare)
        compare_results
        ;;
    all)
        show_all
        ;;
esac
