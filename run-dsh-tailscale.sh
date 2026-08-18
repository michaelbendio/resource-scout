#!/bin/sh
set -eu
cd "$(dirname "$0")"

# A LaunchAgent has no terminal, so it may only use a key that was already
# saved by an interactive run of run-dsh.sh.
RESOURCE_RESEARCH_RUNNER=./run-tailscale.sh
RESOURCE_RESEARCH_KEYCHAIN_ONLY=1
export RESOURCE_RESEARCH_RUNNER RESOURCE_RESEARCH_KEYCHAIN_ONLY
exec ./run-dsh.sh "$@"
