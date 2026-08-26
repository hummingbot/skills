#!/bin/bash
# generate_spec.sh -- produce a Gateway OpenAPI spec from a version of the gateway repo.
#
# scripts/generate-openapi.ts builds the document from Gateway's route table without
# starting a server, so this needs an installed node_modules and nothing running.
#
# Usage:
#   bash scripts/generate_spec.sh --out /tmp/gw.json                 # the working tree as it stands
#   bash scripts/generate_spec.sh --ref development --out /tmp/dev.json   # a branch, tag, or commit
#   bash scripts/generate_spec.sh --gateway ~/src/gateway --out /tmp/gw.json
#
# --ref checks the ref out into a throwaway git worktree and generates there, so the
# working tree you are editing is never touched. Its node_modules is populated with
# symlinks to the main checkout's packages rather than reinstalled: a pnpm install per
# ref costs minutes, and spec generation only needs the app's own imports to resolve. If
# the ref moved a dependency the generator reaches for, run `pnpm install` in the
# worktree this prints and rerun.
#
# Prints the path of the spec it wrote on the last line; progress goes to stderr, so
#   SPEC=$(bash scripts/generate_spec.sh --ref development --out /tmp/dev.json)
# captures just the path.

set -euo pipefail

GATEWAY_DIR="${GATEWAY_DIR:-$HOME/gateway}"
REF=""
OUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref)     REF="$2"; shift 2 ;;
    --out)     OUT="$2"; shift 2 ;;
    --gateway) GATEWAY_DIR="$2"; shift 2 ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

GATEWAY_DIR="${GATEWAY_DIR/#\~/$HOME}"
GENERATOR="scripts/generate-openapi.ts"

[ -d "$GATEWAY_DIR" ] || { echo "No gateway checkout at $GATEWAY_DIR. Pass --gateway or set GATEWAY_DIR." >&2; exit 1; }
[ -f "$GATEWAY_DIR/package.json" ] || { echo "$GATEWAY_DIR has no package.json -- is that the gateway repo?" >&2; exit 1; }
[ -x "$GATEWAY_DIR/node_modules/.bin/ts-node" ] || { echo "No ts-node in $GATEWAY_DIR/node_modules. Run 'pnpm install' there first." >&2; exit 1; }

RESTORE_SPEC=false

if [ -z "$REF" ]; then
  SOURCE_DIR="$GATEWAY_DIR"
  DESCRIBED="$(git -C "$GATEWAY_DIR" describe --always --dirty 2>/dev/null || echo 'not a git checkout')"
  echo "Generating from the gateway working tree at $GATEWAY_DIR ($DESCRIBED)" >&2
  # The generator overwrites gateway's own committed openapi.json. Put it back afterwards
  # if it was clean, so asking this skill a question never dirties the gateway checkout.
  if git -C "$GATEWAY_DIR" diff --quiet -- openapi.json 2>/dev/null; then
    RESTORE_SPEC=true
  fi
else
  git -C "$GATEWAY_DIR" rev-parse --verify --quiet "$REF^{commit}" >/dev/null \
    || { echo "No such ref in $GATEWAY_DIR: $REF. Fetch it first: git -C $GATEWAY_DIR fetch --all" >&2; exit 1; }
  SHA="$(git -C "$GATEWAY_DIR" rev-parse --short "$REF^{commit}")"

  git -C "$GATEWAY_DIR" cat-file -e "$SHA:$GENERATOR" 2>/dev/null || {
    echo "$REF ($SHA) has no $GENERATOR -- it predates server-free spec generation." >&2
    echo "Against a Gateway that old, start it and curl its /docs/json instead." >&2
    exit 1
  }

  SOURCE_DIR="${TMPDIR:-/tmp}/gateway-spec-$SHA"
  if [ ! -d "$SOURCE_DIR" ]; then
    echo "Checking $REF ($SHA) out into $SOURCE_DIR" >&2
    git -C "$GATEWAY_DIR" worktree add --detach "$SOURCE_DIR" "$SHA" >&2
  fi
  if [ ! -d "$SOURCE_DIR/node_modules" ]; then
    # One symlink per package, not one symlink for the whole directory: node resolves a
    # symlinked node_modules root to its real path and then cannot find the worktree's
    # own sources, and pnpm treats it as a directory it may delete -- which would take
    # the real checkout's node_modules with it.
    mkdir "$SOURCE_DIR/node_modules"
    for entry in "$GATEWAY_DIR"/node_modules/* "$GATEWAY_DIR"/node_modules/.bin "$GATEWAY_DIR"/node_modules/.pnpm; do
      [ -e "$entry" ] && ln -s "$entry" "$SOURCE_DIR/node_modules/"
    done
  fi
  # Gateway seeds conf/ from dist/src/templates on first import, and dist/ is a build
  # output that a fresh worktree does not have. Copying the templates is enough -- the
  # spec comes from the route table, not from compiled output -- and it is what makes the
  # document reproducible: a worktree's conf/ is the shipped defaults rather than
  # whatever networks and wallets this machine happens to be configured with.
  mkdir -p "$SOURCE_DIR/dist" "$SOURCE_DIR/conf"
  ( cd "$SOURCE_DIR" && ./node_modules/.bin/copyfiles 'src/templates/*' 'src/templates/**/*' dist >&2 )
  echo "Remove the worktree when done: git -C $GATEWAY_DIR worktree remove --force $SOURCE_DIR" >&2
fi

[ -f "$SOURCE_DIR/$GENERATOR" ] || { echo "No $GENERATOR in $SOURCE_DIR." >&2; exit 1; }

# ts-node directly rather than `pnpm generate:openapi`, which is the same command behind
# a deps-status check that wants to reinstall node_modules before it will run.
( cd "$SOURCE_DIR" && ./node_modules/.bin/ts-node "$GENERATOR" >&2 )

SPEC="$SOURCE_DIR/openapi.json"
[ -f "$SPEC" ] || { echo "$GENERATOR wrote no $SPEC" >&2; exit 1; }

if [ -n "$OUT" ]; then
  OUT="${OUT/#\~/$HOME}"
  mkdir -p "$(dirname "$OUT")"
  cp "$SPEC" "$OUT"
  SPEC="$OUT"
elif [ "$RESTORE_SPEC" = true ]; then
  # Nowhere else to put it, so it stays where the generator wrote it. Say so, rather than
  # restoring the file out from under the path printed below.
  RESTORE_SPEC=false
  echo "Left in place at $SPEC (pass --out to keep the gateway checkout clean)." >&2
fi

[ "$RESTORE_SPEC" = true ] && git -C "$GATEWAY_DIR" checkout -- openapi.json

python3 -c "
import json, sys
spec = json.load(open('$SPEC'))
print('%d paths, %d schemas' % (len(spec['paths']), len(spec.get('components', {}).get('schemas', {}))), file=sys.stderr)
"
echo "$SPEC"
