#!/bin/sh
set -eu
cd "$(dirname "$0")"

if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
  exec ./run.sh
fi

RESOURCE_RESEARCH_KEYCHAIN_SERVICE="resource-research-agent-deepseek"
RESOURCE_RESEARCH_KEYCHAIN_ACCOUNT="${USER:-$(id -un)}"

if command -v security >/dev/null 2>&1; then
  if RESOURCE_RESEARCH_DEEPSEEK_KEY="$(
    security find-generic-password \
      -a "$RESOURCE_RESEARCH_KEYCHAIN_ACCOUNT" \
      -s "$RESOURCE_RESEARCH_KEYCHAIN_SERVICE" \
      -w 2>/dev/null
  )" && [ -n "$RESOURCE_RESEARCH_DEEPSEEK_KEY" ]; then
    echo "Using the DeepSeek API key saved in macOS Keychain."
  else
    echo "No saved DeepSeek API key was found."
    echo "Enter it once at the macOS Keychain prompt; later launches will reuse it."
    security add-generic-password \
      -U \
      -a "$RESOURCE_RESEARCH_KEYCHAIN_ACCOUNT" \
      -s "$RESOURCE_RESEARCH_KEYCHAIN_SERVICE" \
      -l "Resource Research Agent - DeepSeek API key" \
      -w
    RESOURCE_RESEARCH_DEEPSEEK_KEY="$(
      security find-generic-password \
        -a "$RESOURCE_RESEARCH_KEYCHAIN_ACCOUNT" \
        -s "$RESOURCE_RESEARCH_KEYCHAIN_SERVICE" \
        -w
    )"
  fi
else
  restore_terminal() {
    stty echo </dev/tty 2>/dev/null || true
  }
  trap restore_terminal EXIT HUP INT TERM

  printf "DeepSeek API key: " >/dev/tty
  stty -echo </dev/tty
  IFS= read -r RESOURCE_RESEARCH_DEEPSEEK_KEY </dev/tty
  restore_terminal
  printf "\n" >/dev/tty
  trap - EXIT HUP INT TERM
fi

if [ -z "${RESOURCE_RESEARCH_DEEPSEEK_KEY:-}" ]; then
  echo "No API key was entered." >&2
  exit 1
fi

export DEEPSEEK_API_KEY="$RESOURCE_RESEARCH_DEEPSEEK_KEY"
unset RESOURCE_RESEARCH_DEEPSEEK_KEY
exec ./run.sh
