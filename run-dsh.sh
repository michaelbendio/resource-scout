#!/bin/sh
set -eu
cd "$(dirname "$0")"

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

if [ -z "$RESOURCE_RESEARCH_DEEPSEEK_KEY" ]; then
  echo "No API key was entered." >&2
  exit 1
fi

export DEEPSEEK_API_KEY="$RESOURCE_RESEARCH_DEEPSEEK_KEY"
unset RESOURCE_RESEARCH_DEEPSEEK_KEY
exec ./run.sh
