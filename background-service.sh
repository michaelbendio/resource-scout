#!/bin/sh
set -eu

LABEL="com.michaelbendio.resource-research-agent"
REPOSITORY="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
TEMPLATE="$REPOSITORY/service/$LABEL.plist.template"
DOMAIN="gui/$(id -u)"
SERVICE="$DOMAIN/$LABEL"

usage() {
  echo "Usage: ./background-service.sh {install|start|stop|restart|status|logs|uninstall}"
}

require_safe_xml_value() {
  case "$1" in
    *'&'*|*'<'*|*'>'*|*'"'*)
      echo "The background service cannot be installed from a path containing XML punctuation." >&2
      exit 1
      ;;
  esac
}

is_loaded() {
  launchctl print "$SERVICE" >/dev/null 2>&1
}

bootstrap() {
  if [ ! -f "$PLIST" ]; then
    echo "The background service is not installed. Run ./background-service.sh install first." >&2
    exit 1
  fi
  if ! is_loaded; then
    launchctl bootstrap "$DOMAIN" "$PLIST"
  fi
  launchctl kickstart -k "$SERVICE"
}

case "${1:-}" in
  install)
    [ "$(uname -s)" = "Darwin" ] || { echo "The background service requires macOS." >&2; exit 1; }
    command -v launchctl >/dev/null 2>&1 || { echo "launchctl was not found." >&2; exit 1; }
    command -v security >/dev/null 2>&1 || { echo "The macOS Keychain command was not found." >&2; exit 1; }
    command -v tailscale >/dev/null 2>&1 || { echo "Tailscale was not found. Install and connect it first." >&2; exit 1; }
    PYTHON="$(command -v python3 || true)"
    [ -n "$PYTHON" ] || { echo "Python 3 was not found." >&2; exit 1; }
    [ -x "$REPOSITORY/dsh-runtime/node_modules/.bin/dsh" ] || {
      echo "DeepSeek Harness is not installed. Run ./install-dsh.sh first." >&2
      exit 1
    }
    KEYCHAIN_ACCOUNT="${USER:-$(id -un)}"
    security find-generic-password -a "$KEYCHAIN_ACCOUNT" -s resource-research-agent-deepseek -w >/dev/null 2>&1 || {
      echo "No saved DeepSeek API key was found. Run ./run-dsh.sh interactively once first." >&2
      exit 1
    }
    require_safe_xml_value "$REPOSITORY"
    require_safe_xml_value "$PYTHON"
    mkdir -p "$HOME/Library/LaunchAgents" "$REPOSITORY/data"
    TEMP_PLIST="$(mktemp "${TMPDIR:-/tmp}/resource-research-agent.XXXXXX")"
    trap 'rm -f "$TEMP_PLIST"' EXIT HUP INT TERM
    sed -e "s|__REPOSITORY__|$REPOSITORY|g" -e "s|__PYTHON__|$PYTHON|g" "$TEMPLATE" >"$TEMP_PLIST"
    plutil -lint "$TEMP_PLIST" >/dev/null
    install -m 600 "$TEMP_PLIST" "$PLIST"
    if is_loaded; then
      launchctl bootout "$DOMAIN" "$PLIST"
    fi
    launchctl bootstrap "$DOMAIN" "$PLIST"
    launchctl kickstart -k "$SERVICE"
    echo "Background service installed and started."
    echo "Private address: https://$(tailscale status --json | "$PYTHON" -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
    ;;
  start)
    bootstrap
    echo "Background service started."
    ;;
  stop)
    if is_loaded; then
      launchctl bootout "$DOMAIN" "$PLIST"
      echo "Background service stopped."
    else
      echo "Background service is already stopped."
    fi
    ;;
  restart)
    bootstrap
    echo "Background service restarted."
    ;;
  status)
    if is_loaded; then
      echo "Background service is loaded."
      launchctl print "$SERVICE" | sed -n -e '/state =/p' -e '/pid =/p' -e '/last exit code =/p'
      if command -v curl >/dev/null 2>&1 && STATUS="$(curl -fsS --max-time 3 http://127.0.0.1:8765/api/status 2>/dev/null)"; then
        echo "App response: $STATUS"
      else
        echo "The app is not responding on http://127.0.0.1:8765 yet."
      fi
    else
      echo "Background service is not loaded."
      exit 1
    fi
    ;;
  logs)
    echo "Recent output:"
    tail -n 80 "$REPOSITORY/data/background-service.log" 2>/dev/null || true
    echo "Recent errors:"
    tail -n 80 "$REPOSITORY/data/background-service.error.log" 2>/dev/null || true
    ;;
  uninstall)
    if is_loaded; then
      launchctl bootout "$DOMAIN" "$PLIST"
    fi
    rm -f "$PLIST"
    echo "Background service removed. Research data and logs were left in place."
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
