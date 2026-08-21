#!/bin/sh
set -eu
cd "$(dirname "$0")"

MLX_SERVER="${RESOURCE_SCOUT_MLX_SERVER:-/opt/homebrew/opt/mlx-lm/bin/mlx_lm.server}"
if [ ! -x "$MLX_SERVER" ]; then
  echo "MLX LM is not installed at $MLX_SERVER." >&2
  echo "Install it with: brew install mlx-lm" >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js and npm are required to install the DSH plugins." >&2
  exit 1
fi

RESOURCE_SCOUT_PYTHON="${RESOURCE_SCOUT_PYTHON:-python3}"
echo "Installing the pinned DSH runtime and Resource Scout plugins..."
npm ci --prefix dsh-runtime --cache dsh-runtime/.npm-cache --install-links --no-audit --no-fund

echo "Installing the pinned DDGS search dependency..."
"$RESOURCE_SCOUT_PYTHON" -m venv dsh-runtime/.venv-ddgs
dsh-runtime/.venv-ddgs/bin/python -m pip install \
  --disable-pip-version-check \
  -r dsh-plugins/web-search-ddgs/requirements.txt

dsh-runtime/.venv-ddgs/bin/python -c "from ddgs import DDGS"
echo "Local Qwen prerequisites are installed. Start the model with ./local-qwen.sh serve"
