#!/bin/sh
set -eu
cd "$(dirname "$0")"
RESOURCE_RESEARCH_PYTHON="${RESOURCE_RESEARCH_PYTHON:-python3}"
exec "$RESOURCE_RESEARCH_PYTHON" -m resource_research_agent --database data/research-agent.sqlite3 serve "$@"
