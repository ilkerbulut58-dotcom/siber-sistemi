#!/usr/bin/env bash
# Lightweight cron healthcheck; triggers recover only when needed.
# Installed at /opt/siber/scripts/server/web-stack-healthcheck.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

NEED_RECOVER=0

if ! service_active apache2; then
  log "CHECK FAIL: apache2 inactive"
  NEED_RECOVER=1
fi

if ! service_active nginx; then
  log "CHECK FAIL: nginx inactive"
  NEED_RECOVER=1
fi

if ! port_listening ':443 '; then
  log "CHECK FAIL: 443 not listening"
  NEED_RECOVER=1
fi

if ! curl -sf http://127.0.0.1:8010/api/v1/health >/dev/null 2>&1; then
  log "CHECK FAIL: siber api :8010"
  NEED_RECOVER=1
fi

siber_code=$(http_code "https://${SERVER_IP}/api/v1/health" "siber.cloudnira.com")
if [ "$siber_code" = "000" ] || [ "$siber_code" = "502" ] || [ "$siber_code" = "503" ]; then
  log "CHECK FAIL: siber proxy -> ${siber_code}"
  NEED_RECOVER=1
fi

tur_code=$(http_code "https://${SERVER_IP}/" "turbridge.de")
if [ "$tur_code" = "000" ] || [ "$tur_code" = "502" ] || [ "$tur_code" = "503" ]; then
  log "CHECK FAIL: turbridge proxy -> ${tur_code}"
  NEED_RECOVER=1
fi

if [ "$NEED_RECOVER" -eq 0 ]; then
  log "CHECK OK"
  exit 0
fi

log "CHECK triggering auto recover"
exec "${SCRIPT_DIR}/web-stack-recover.sh" auto
