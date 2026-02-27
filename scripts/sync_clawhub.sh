#!/usr/bin/env bash
# sync_clawhub.sh — Publish all skills in this repo to ClawHub
#
# Usage:
#   ./scripts/sync_clawhub.sh              # interactive (prompts for each new/updated skill)
#   ./scripts/sync_clawhub.sh --dry-run    # preview what would be published
#   ./scripts/sync_clawhub.sh --all        # publish everything without prompts
#   ./scripts/sync_clawhub.sh --bump minor # bump minor version for updates (default: patch)
#
# Auth:
#   Log in first:  clawhub login --token <token> --no-browser
#   Or set env:    CLAWHUB_TOKEN=<token>
#
# Requirements:
#   npm i -g clawhub

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"

# ── Check clawhub is installed ────────────────────────────────────────────────
if ! command -v clawhub &>/dev/null; then
  echo "❌ clawhub not found. Install with: npm i -g clawhub"
  exit 1
fi

# ── Auth check ────────────────────────────────────────────────────────────────
if ! clawhub whoami &>/dev/null; then
  echo "❌ Not logged in to ClawHub."
  echo "   Run: clawhub login --token <token> --no-browser"
  echo "   Or set CLAWHUB_TOKEN env var and re-run."
  exit 1
fi

echo "✓ Logged in as $(clawhub whoami 2>&1 | grep -o '@[^ ]*')"
echo "✓ Skills dir: $SKILLS_DIR"
echo ""

# ── Sync ─────────────────────────────────────────────────────────────────────
clawhub sync \
  --root "$SKILLS_DIR" \
  --changelog "Sync from hummingbot/skills $(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
  "$@"
