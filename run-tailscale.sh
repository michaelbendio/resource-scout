#!/bin/sh
set -eu
cd "$(dirname "$0")"
RESOURCE_SCOUT_PYTHON="${RESOURCE_SCOUT_PYTHON:-python3}"

if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -i "$RESOURCE_SCOUT_PYTHON" -m resource_research_agent --database data/research-agent.sqlite3 tailscale "$@"
fi

exec "$RESOURCE_SCOUT_PYTHON" -m resource_research_agent --database data/research-agent.sqlite3 tailscale "$@"
