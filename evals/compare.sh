#!/bin/bash
#
# Compare evaluation results between two skills
# Usage: ./compare.sh <skill1> <skill2>
#
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/results"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <skill1> <skill2>"
    echo ""
    echo "Available results:"
    ls -1 "$RESULTS_DIR" 2>/dev/null | sed 's/^/  /' || echo "  (none)"
    exit 1
fi

SKILL1="$1"
SKILL2="$2"

# Find latest result file for each skill
get_latest_result() {
    local skill="$1"
    ls -t "$RESULTS_DIR/${skill}_"*.json 2>/dev/null | head -1
}

RESULT1=$(get_latest_result "$SKILL1")
RESULT2=$(get_latest_result "$SKILL2")

if [[ -z "$RESULT1" ]]; then
    echo "Error: No results found for $SKILL1"
    echo "Run: ./run_eval.sh $SKILL1"
    exit 1
fi

if [[ -z "$RESULT2" ]]; then
    echo "Error: No results found for $SKILL2"
    echo "Run: ./run_eval.sh $SKILL2"
    exit 1
fi

echo ""
echo -e "${CYAN}Skill Comparison${NC}"
echo -e "${CYAN}================${NC}"
echo ""
echo "Comparing:"
echo "  A: $SKILL1 ($(basename "$RESULT1"))"
echo "  B: $SKILL2 ($(basename "$RESULT2"))"
echo ""

# Extract metrics
extract_metrics() {
    local file="$1"
    local success_count=$(jq '[.results[] | select(.success == true)] | length' "$file")
    local total_count=$(jq '.results | length' "$file")
    local total_duration=$(jq '[.results[].duration_seconds] | add // 0' "$file")
    local avg_duration=$(jq '[.results[].duration_seconds] | if length > 0 then add / length else 0 end | floor' "$file")

    echo "$success_count|$total_count|$total_duration|$avg_duration"
}

METRICS1=$(extract_metrics "$RESULT1")
METRICS2=$(extract_metrics "$RESULT2")

IFS='|' read -r S1_SUCCESS S1_TOTAL S1_DURATION S1_AVG <<< "$METRICS1"
IFS='|' read -r S2_SUCCESS S2_TOTAL S2_DURATION S2_AVG <<< "$METRICS2"

# Print comparison table
printf "%-20s %15s %15s\n" "Metric" "$SKILL1" "$SKILL2"
printf "%-20s %15s %15s\n" "--------------------" "---------------" "---------------"
printf "%-20s %15s %15s\n" "Success Rate" "$S1_SUCCESS/$S1_TOTAL" "$S2_SUCCESS/$S2_TOTAL"
printf "%-20s %15s %15s\n" "Total Time (s)" "$S1_DURATION" "$S2_DURATION"
printf "%-20s %15s %15s\n" "Avg Time (s)" "$S1_AVG" "$S2_AVG"
echo ""

# Per-prompt comparison
echo -e "${CYAN}Per-Prompt Comparison:${NC}"
echo ""
printf "%-20s %10s %10s %10s %10s\n" "Prompt" "A Success" "A Time" "B Success" "B Time"
printf "%-20s %10s %10s %10s %10s\n" "--------------------" "----------" "----------" "----------" "----------"

# Get all prompt IDs
jq -r '.results[].id' "$RESULT1" | while read -r id; do
    r1_success=$(jq -r ".results[] | select(.id == \"$id\") | .success" "$RESULT1")
    r1_time=$(jq -r ".results[] | select(.id == \"$id\") | .duration_seconds" "$RESULT1")
    r2_success=$(jq -r ".results[] | select(.id == \"$id\") | .success" "$RESULT2" 2>/dev/null || echo "N/A")
    r2_time=$(jq -r ".results[] | select(.id == \"$id\") | .duration_seconds" "$RESULT2" 2>/dev/null || echo "N/A")

    # Color code success
    if [[ "$r1_success" == "true" ]]; then
        r1_display="${GREEN}pass${NC}"
    else
        r1_display="${RED}fail${NC}"
    fi

    if [[ "$r2_success" == "true" ]]; then
        r2_display="${GREEN}pass${NC}"
    else
        r2_display="${RED}fail${NC}"
    fi

    printf "%-20s %10b %10s %10b %10s\n" "$id" "$r1_display" "${r1_time}s" "$r2_display" "${r2_time}s"
done

echo ""

# Winner
if [[ $S1_SUCCESS -gt $S2_SUCCESS ]]; then
    echo -e "${GREEN}Winner: $SKILL1${NC} (higher success rate)"
elif [[ $S2_SUCCESS -gt $S1_SUCCESS ]]; then
    echo -e "${GREEN}Winner: $SKILL2${NC} (higher success rate)"
elif [[ $S1_DURATION -lt $S2_DURATION ]]; then
    echo -e "${GREEN}Winner: $SKILL1${NC} (faster)"
elif [[ $S2_DURATION -lt $S1_DURATION ]]; then
    echo -e "${GREEN}Winner: $SKILL2${NC} (faster)"
else
    echo -e "${YELLOW}Tie${NC}"
fi
echo ""
