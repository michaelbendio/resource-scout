#!/bin/sh
set -eu
cd "$(dirname "$0")"

if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -i python3 -m resource_research_agent --database data/research-agent.sqlite3 tailscale "$@"
fi

exec python3 -m resource_research_agent --database data/research-agent.sqlite3 tailscale "$@"
