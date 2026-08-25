#!/bin/sh
set -eu
cd "$(dirname "$0")"

# Production is deliberately locked to the unmetered Local Qwen route. An
# existing DeepSeek credential remains untouched but is never loaded here.
RESOURCE_SCOUT_REQUIRE_UNMETERED=1
export RESOURCE_SCOUT_REQUIRE_UNMETERED
unset DEEPSEEK_API_KEY
exec ./run-tailscale.sh "$@"
