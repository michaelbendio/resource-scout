#!/bin/sh
set -eu
cd "$(dirname "$0")"

if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js and npm are required to install DeepSeek Harness."
  echo "Install Node.js, then run this installer again."
  exit 1
fi

echo "Installing the pinned DeepSeek Harness developer preview..."
npm ci --prefix dsh-runtime --cache dsh-runtime/.npm-cache --install-links --no-audit --no-fund
echo "DeepSeek Harness is installed."
echo "Start the app with ./run-dsh.sh and enter your API key when prompted."
