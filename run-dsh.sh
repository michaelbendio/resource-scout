#!/bin/sh
set -eu
cd "$(dirname "$0")"

RESOURCE_RESEARCH_RUNNER="${RESOURCE_RESEARCH_RUNNER:-./run.sh}"

if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
  exec "$RESOURCE_RESEARCH_RUNNER" "$@"
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
  elif [ "${RESOURCE_RESEARCH_KEYCHAIN_ONLY:-0}" = "1" ]; then
    echo "No saved DeepSeek API key was found in macOS Keychain." >&2
    echo "Run ./run-dsh.sh interactively once to save it, then restart the background service." >&2
    exit 1
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
  if [ "${RESOURCE_RESEARCH_KEYCHAIN_ONLY:-0}" = "1" ]; then
    echo "The background service requires the macOS security command and a saved DeepSeek API key." >&2
    exit 1
  fi
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
exec "$RESOURCE_RESEARCH_RUNNER" "$@"
