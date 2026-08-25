#!/bin/sh
set -eu
cd "$(dirname "$0")"

RESOURCE_SCOUT_PYTHON="${RESOURCE_RESEARCH_PYTHON:-python3}"
export RESOURCE_SCOUT_PYTHON
exec ./local-qwen.sh serve --quantization 8-bit --validate
