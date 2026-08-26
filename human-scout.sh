#!/bin/sh
set -eu
cd "$(dirname "$0")"

RESOURCE_SCOUT_PYTHON="${RESOURCE_SCOUT_PYTHON:-python3}"
exec "$RESOURCE_SCOUT_PYTHON" -m resource_research_agent.human_scout "$@"

