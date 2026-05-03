#!/usr/bin/env bash
# Runs Flutter web in debug mode using Brave (or any Chromium-based binary).
# Flutter's device is still named "chrome"; it uses the CHROME_EXECUTABLE env var.
#
# Usage (from anywhere): ./scripts/run_web_brave.sh [flutter run args...]
# Optional: BRAVE_EXECUTABLE=/path/to/brave-browser ./scripts/run_web_brave.sh
#
# If no Brave/Chromium binary exists in this environment (typical in distrobox),
# falls back to "web-server": open the printed http://127.0.0.1:... URL in Brave on the host.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${APP_ROOT}"

log() {
  printf "%s\n" "$*" >&2
}

# Pick a Chromium-compatible binary. Avoid brave-host-bridge unless forced: it often fails
# with Flutter's DevTools handshake (distrobox-host-exec / root / PATH).
pick_chromium_browser() {
  local c
  if [[ -n "${USE_BRAVE_HOST_BRIDGE:-}" ]] && command -v brave-host-bridge >/dev/null 2>&1; then
    command -v brave-host-bridge
    return 0
  fi
  if [[ -n "${CHROME_EXECUTABLE:-}" ]] && [[ -x "${CHROME_EXECUTABLE}" ]]; then
    if [[ "${CHROME_EXECUTABLE}" == *brave-host-bridge* ]] && [[ -z "${USE_BRAVE_HOST_BRIDGE:-}" ]]; then
      log "warn: CHROME_EXECUTABLE points at brave-host-bridge; ignoring (set USE_BRAVE_HOST_BRIDGE=1 to force)."
    else
      printf "%s" "${CHROME_EXECUTABLE}"
      return 0
    fi
  fi
  local flatpak_exports=(
    "${HOME}/.local/share/flatpak/exports/bin/com.brave.Browser"
    "/var/lib/flatpak/exports/bin/com.brave.Browser"
  )
  local candidates=(
    "${BRAVE_EXECUTABLE:-}"
    "${flatpak_exports[@]}"
    "/usr/bin/brave-browser"
    "/usr/bin/brave"
    "/app/bin/brave"
    "/usr/bin/google-chrome-stable"
    "/usr/bin/chromium"
    "/usr/bin/chromium-browser"
  )
  for c in "${candidates[@]}"; do
    if [[ -n "${c}" && -x "${c}" ]]; then
      printf "%s" "${c}"
      return 0
    fi
  done
  for c in brave-browser brave google-chrome-stable chromium; do
    if command -v "${c}" >/dev/null 2>&1; then
      command -v "${c}"
      return 0
    fi
  done
  return 1
}

if BROWSER_BIN="$(pick_chromium_browser)"; then
  export CHROME_EXECUTABLE="${BROWSER_BIN}"
  log "Using CHROME_EXECUTABLE=${CHROME_EXECUTABLE}"
  exec flutter run -d chrome "$@"
fi

log "info: No Chromium-based browser in this environment (Brave is usually on the host only)."
log "info: Starting Flutter web-server — open the URL below in Brave on your machine."
log "info: To use -d chrome instead, install Brave in this box or run: BRAVE_EXECUTABLE=/path/to/brave-browser $0"
log "info: Optional: USE_BRAVE_HOST_BRIDGE=1 $0  (retry distrobox bridge; often flaky with Flutter)"
exec flutter run -d web-server "$@"
