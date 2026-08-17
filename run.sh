#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec python3 -m resource_research_agent --database data/research-agent.sqlite3 serve "$@"

