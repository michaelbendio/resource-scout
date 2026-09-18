#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

SEED_DB="${SEED_DB:-data/codex-grok.sqlite3}"
SEED_IMPORT_ID="${SEED_IMPORT_ID:-1}"
MAX_CATEGORIES="${MAX_CATEGORIES:-6}"

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found" >&2
  exit 1
fi
if ! command -v grok >/dev/null 2>&1; then
  echo "grok CLI not found" >&2
  exit 1
fi
if ! command -v claude >/dev/null 2>&1; then
  echo "claude CLI not found" >&2
  echo "Install Claude Code and authenticate before starting the overnight experiment." >&2
  exit 1
fi
if [[ ! -f "$SEED_DB" ]]; then
  echo "Seed database not found: $SEED_DB" >&2
  exit 1
fi

echo "Starting three-condition pairwise experiment."
echo "Seed database: $SEED_DB"
echo "Categories per condition: $MAX_CATEGORIES"
echo

exec caffeinate -dimsu python3 -m resource_research_agent.pairwise_supervisor   --seed-database "$SEED_DB"   --seed-import-id "$SEED_IMPORT_ID"   --max-categories "$MAX_CATEGORIES"
