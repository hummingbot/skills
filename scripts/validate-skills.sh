#!/bin/bash
# Validates all SKILL.md files against the Agent Skills specification
# https://agentskills.io/specification

set -e

SKILLS_DIR="${1:-skills}"
ERRORS=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_error() {
    echo -e "${RED}ERROR:${NC} $1"
    ERRORS=$((ERRORS + 1))
}

log_warn() {
    echo -e "${YELLOW}WARN:${NC} $1"
}

log_success() {
    echo -e "${GREEN}OK:${NC} $1"
}

# Check if directory exists
if [ ! -d "$SKILLS_DIR" ]; then
    log_error "Skills directory '$SKILLS_DIR' not found"
    exit 1
fi

# Find all SKILL.md files
SKILL_FILES=$(find "$SKILLS_DIR" -name "SKILL.md" -type f 2>/dev/null)

if [ -z "$SKILL_FILES" ]; then
    log_error "No SKILL.md files found in '$SKILLS_DIR'"
    exit 1
fi

echo "Validating skills in '$SKILLS_DIR'..."
echo ""

for skill_file in $SKILL_FILES; do
    skill_dir=$(dirname "$skill_file")
    skill_name=$(basename "$skill_dir")

    echo "Checking: $skill_name"

    # Check SKILL.md exists (already confirmed by find)
    if [ ! -f "$skill_file" ]; then
        log_error "$skill_name: SKILL.md not found"
        continue
    fi

    # Extract frontmatter
    frontmatter=$(sed -n '/^---$/,/^---$/p' "$skill_file" | sed '1d;$d')

    if [ -z "$frontmatter" ]; then
        log_error "$skill_name: Missing YAML frontmatter"
        continue
    fi

    # Check required 'name' field
    name_value=$(echo "$frontmatter" | grep -E "^name:" | sed 's/^name:[[:space:]]*//')
    if [ -z "$name_value" ]; then
        log_error "$skill_name: Missing required 'name' field"
    else
        # Validate name format: lowercase alphanumeric with hyphens, 1-64 chars
        if ! echo "$name_value" | grep -qE '^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$|^[a-z0-9]$'; then
            log_error "$skill_name: Invalid name format '$name_value' (must be lowercase alphanumeric with hyphens, 1-64 chars)"
        fi

        # Check name doesn't start/end with hyphen or have consecutive hyphens
        if echo "$name_value" | grep -qE '^-|-$|--'; then
            log_error "$skill_name: Name cannot start/end with hyphen or have consecutive hyphens"
        fi

        # Check name matches directory name
        if [ "$name_value" != "$skill_name" ]; then
            log_error "$skill_name: Name '$name_value' doesn't match directory name '$skill_name'"
        fi
    fi

    # Check required 'description' field
    description_value=$(echo "$frontmatter" | grep -E "^description:" | sed 's/^description:[[:space:]]*//')
    if [ -z "$description_value" ]; then
        log_error "$skill_name: Missing required 'description' field"
    else
        # Check description length (max 1024 chars)
        desc_len=${#description_value}
        if [ "$desc_len" -gt 1024 ]; then
            log_error "$skill_name: Description exceeds 1024 characters ($desc_len chars)"
        fi
    fi

    # Check for invalid fields (not in spec)
    invalid_fields=$(echo "$frontmatter" | grep -E "^[a-z-]+:" | grep -vE "^(name|description|license|compatibility|metadata|allowed-tools):" | sed 's/:.*$//')
    if [ -n "$invalid_fields" ]; then
        for field in $invalid_fields; do
            log_error "$skill_name: Invalid frontmatter field '$field' (use 'metadata' for custom fields)"
        done
    fi

    # Check SKILL.md line count (recommended < 500)
    line_count=$(wc -l < "$skill_file" | tr -d ' ')
    if [ "$line_count" -gt 500 ]; then
        log_warn "$skill_name: SKILL.md has $line_count lines (recommended < 500)"
    fi

    # Check for scripts directory if referenced
    if grep -q "scripts/" "$skill_file" && [ ! -d "$skill_dir/scripts" ]; then
        log_warn "$skill_name: References scripts/ but directory not found"
    fi

    # Check for references directory if referenced
    if grep -q "references/" "$skill_file" && [ ! -d "$skill_dir/references" ]; then
        log_warn "$skill_name: References references/ but directory not found"
    fi

    if [ $ERRORS -eq 0 ]; then
        log_success "$skill_name"
    fi

    echo ""
done

echo "================================"
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Validation failed with $ERRORS error(s)${NC}"
    exit 1
else
    echo -e "${GREEN}All skills validated successfully${NC}"
    exit 0
fi
