#!/bin/sh
set -eu

APP_LABEL="com.michaelbendio.resource-research-agent"
REPOSITORY="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
APP_PLIST="$HOME/Library/LaunchAgents/$APP_LABEL.plist"
APP_TEMPLATE="$REPOSITORY/service/$APP_LABEL.plist.template"
DOMAIN="gui/$(id -u)"
APP_SERVICE="$DOMAIN/$APP_LABEL"

usage() {
  echo "Usage: ./background-service.sh {install|start|stop|restart|status|logs|uninstall}"
}

is_loaded() {
  launchctl print "$1" >/dev/null 2>&1
}

start_service() {
  if [ ! -f "$APP_PLIST" ]; then
    echo "Resource Scout is not installed. Run ./background-service.sh install first." >&2
    exit 1
  fi
  if ! is_loaded "$APP_SERVICE"; then
    launchctl bootstrap "$DOMAIN" "$APP_PLIST"
  fi
  launchctl kickstart -k "$APP_SERVICE"
}

stop_service() {
  if is_loaded "$APP_SERVICE"; then
    launchctl bootout "$DOMAIN" "$APP_PLIST"
  fi
}

case "${1:-}" in
  install)
    [ "$(uname -s)" = "Darwin" ] || { echo "The background service requires macOS." >&2; exit 1; }
    command -v launchctl >/dev/null 2>&1 || { echo "launchctl was not found." >&2; exit 1; }
    command -v tailscale >/dev/null 2>&1 || { echo "Tailscale was not found. Install and connect it first." >&2; exit 1; }
    PYTHON="$(command -v python3 || true)"
    [ -n "$PYTHON" ] || { echo "Python 3 was not found." >&2; exit 1; }
    case "$REPOSITORY$PYTHON" in
      *'&'*|*'<'*|*'>'*|*'"'*) echo "The service path contains unsupported XML punctuation." >&2; exit 1 ;;
    esac
    mkdir -p "$HOME/Library/LaunchAgents" "$REPOSITORY/data"
    temporary="$(mktemp "${TMPDIR:-/tmp}/resource-scout-service.XXXXXX")"
    sed -e "s|__REPOSITORY__|$REPOSITORY|g" -e "s|__PYTHON__|$PYTHON|g" "$APP_TEMPLATE" >"$temporary"
    plutil -lint "$temporary" >/dev/null
    install -m 600 "$temporary" "$APP_PLIST"
    rm -f "$temporary"
    stop_service
    launchctl bootstrap "$DOMAIN" "$APP_PLIST"
    launchctl kickstart -k "$APP_SERVICE"
    echo "Resource Scout installed and started."
    ;;
  start)
    start_service
    echo "Resource Scout started."
    ;;
  stop)
    stop_service
    echo "Resource Scout stopped."
    ;;
  restart)
    start_service
    echo "Resource Scout restarted."
    ;;
  status)
    if is_loaded "$APP_SERVICE"; then
      echo "Resource Scout is loaded."
      launchctl print "$APP_SERVICE" | sed -n -e '/state =/p' -e '/pid =/p' -e '/last exit code =/p'
    else
      echo "Resource Scout is not loaded."
      exit 1
    fi
    ;;
  logs)
    tail -n 80 "$REPOSITORY/data/background-service.log" 2>/dev/null || true
    tail -n 80 "$REPOSITORY/data/background-service.error.log" 2>/dev/null || true
    ;;
  uninstall)
    stop_service
    rm -f "$APP_PLIST"
    echo "Resource Scout background service removed. Research data and logs were left in place."
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
