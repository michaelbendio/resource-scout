#!/bin/sh
set -eu

APP_LABEL="com.michaelbendio.resource-research-agent"
QWEN_LABEL="com.michaelbendio.resource-scout-local-qwen"
REPOSITORY="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
APP_PLIST="$HOME/Library/LaunchAgents/$APP_LABEL.plist"
QWEN_PLIST="$HOME/Library/LaunchAgents/$QWEN_LABEL.plist"
APP_TEMPLATE="$REPOSITORY/service/$APP_LABEL.plist.template"
QWEN_TEMPLATE="$REPOSITORY/service/$QWEN_LABEL.plist.template"
DOMAIN="gui/$(id -u)"
APP_SERVICE="$DOMAIN/$APP_LABEL"
QWEN_SERVICE="$DOMAIN/$QWEN_LABEL"

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
  launchctl print "$1" >/dev/null 2>&1
}

bootstrap_one() {
  service="$1"
  plist="$2"
  if [ ! -f "$plist" ]; then
    echo "The background services are not installed. Run ./background-service.sh install first." >&2
    exit 1
  fi
  if ! is_loaded "$service"; then
    launchctl bootstrap "$DOMAIN" "$plist"
  fi
  launchctl kickstart -k "$service"
}

stop_one() {
  service="$1"
  plist="$2"
  if is_loaded "$service"; then
    launchctl bootout "$DOMAIN" "$plist"
  fi
}

render_plist() {
  template="$1"
  destination="$2"
  python="$3"
  temporary="$(mktemp "${TMPDIR:-/tmp}/resource-scout-service.XXXXXX")"
  sed -e "s|__REPOSITORY__|$REPOSITORY|g" -e "s|__PYTHON__|$python|g" "$template" >"$temporary"
  plutil -lint "$temporary" >/dev/null
  install -m 600 "$temporary" "$destination"
  rm -f "$temporary"
}

show_service() {
  name="$1"
  service="$2"
  if is_loaded "$service"; then
    echo "$name is loaded."
    launchctl print "$service" | sed -n -e '/state =/p' -e '/pid =/p' -e '/last exit code =/p'
  else
    echo "$name is not loaded."
    return 1
  fi
}

case "${1:-}" in
  install)
    [ "$(uname -s)" = "Darwin" ] || { echo "The background service requires macOS." >&2; exit 1; }
    command -v launchctl >/dev/null 2>&1 || { echo "launchctl was not found." >&2; exit 1; }
    command -v tailscale >/dev/null 2>&1 || { echo "Tailscale was not found. Install and connect it first." >&2; exit 1; }
    PYTHON="$(command -v python3 || true)"
    [ -n "$PYTHON" ] || { echo "Python 3 was not found." >&2; exit 1; }
    [ -x "$REPOSITORY/dsh-runtime/node_modules/.bin/dsh" ] || {
      echo "DeepSeek Harness is not installed. Run ./install-local-qwen.sh first." >&2
      exit 1
    }
    [ -x "$REPOSITORY/dsh-runtime/.venv-ddgs/bin/python" ] || {
      echo "The project-owned DDGS search runtime is missing. Run ./install-local-qwen.sh first." >&2
      exit 1
    }
    MLX_SERVER="${RESOURCE_SCOUT_MLX_SERVER:-/opt/homebrew/opt/mlx-lm/bin/mlx_lm.server}"
    [ -x "$MLX_SERVER" ] || {
      echo "MLX LM is not installed. Run ./install-local-qwen.sh first." >&2
      exit 1
    }
    require_safe_xml_value "$REPOSITORY"
    require_safe_xml_value "$PYTHON"
    mkdir -p "$HOME/Library/LaunchAgents" "$REPOSITORY/data"
    render_plist "$QWEN_TEMPLATE" "$QWEN_PLIST" "$PYTHON"
    render_plist "$APP_TEMPLATE" "$APP_PLIST" "$PYTHON"
    stop_one "$APP_SERVICE" "$APP_PLIST"
    stop_one "$QWEN_SERVICE" "$QWEN_PLIST"
    launchctl bootstrap "$DOMAIN" "$QWEN_PLIST"
    launchctl bootstrap "$DOMAIN" "$APP_PLIST"
    launchctl kickstart -k "$QWEN_SERVICE"
    launchctl kickstart -k "$APP_SERVICE"
    echo "Resource Scout and Local Qwen services installed and started."
    echo "Qwen will report ready after its automatic model completion check finishes."
    echo "Private address: https://$(tailscale status --json | "$PYTHON" -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
    ;;
  start)
    bootstrap_one "$QWEN_SERVICE" "$QWEN_PLIST"
    bootstrap_one "$APP_SERVICE" "$APP_PLIST"
    echo "Resource Scout and Local Qwen services started."
    ;;
  stop)
    stop_one "$APP_SERVICE" "$APP_PLIST"
    stop_one "$QWEN_SERVICE" "$QWEN_PLIST"
    echo "Resource Scout and Local Qwen services stopped."
    ;;
  restart)
    bootstrap_one "$QWEN_SERVICE" "$QWEN_PLIST"
    bootstrap_one "$APP_SERVICE" "$APP_PLIST"
    echo "Resource Scout and Local Qwen services restarted."
    echo "Qwen will report ready after its automatic model completion check finishes."
    ;;
  status)
    result=0
    show_service "Local Qwen" "$QWEN_SERVICE" || result=1
    show_service "Resource Scout" "$APP_SERVICE" || result=1
    if command -v curl >/dev/null 2>&1 && STATUS="$(curl -fsS --max-time 3 http://127.0.0.1:8765/api/status 2>/dev/null)"; then
      echo "App response: $STATUS"
    else
      echo "The app is not responding on http://127.0.0.1:8765 yet."
      result=1
    fi
    exit "$result"
    ;;
  logs)
    echo "Recent Local Qwen output:"
    tail -n 80 "$REPOSITORY/data/local-qwen-service.log" 2>/dev/null || true
    echo "Recent Local Qwen errors:"
    tail -n 80 "$REPOSITORY/data/local-qwen-service.error.log" 2>/dev/null || true
    echo "Recent Resource Scout output:"
    tail -n 80 "$REPOSITORY/data/background-service.log" 2>/dev/null || true
    echo "Recent Resource Scout errors:"
    tail -n 80 "$REPOSITORY/data/background-service.error.log" 2>/dev/null || true
    ;;
  uninstall)
    stop_one "$APP_SERVICE" "$APP_PLIST"
    stop_one "$QWEN_SERVICE" "$QWEN_PLIST"
    rm -f "$APP_PLIST" "$QWEN_PLIST"
    echo "Background services removed. Research data, model cache, credentials, and logs were left in place."
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
