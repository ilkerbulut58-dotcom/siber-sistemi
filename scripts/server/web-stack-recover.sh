#!/usr/bin/env bash
# Full web stack recovery for single-server Plesk host.
# Usage: web-stack-recover.sh [boot|manual|auto]
# Installed at /opt/siber/scripts/server/web-stack-recover.sh

set -euo pipefail

MODE="${1:-manual}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

log "=== recover start mode=${MODE} ==="

enable_boot_services
wait_for_ip "$SERVER_IP" 90 || true

start_apache_if_needed
start_nginx_if_needed
start_siber_stack
start_turbridge_if_needed

ensure_https_listeners

if [ "$MODE" = "boot" ]; then
  # After reboot Plesk nginx SSL vhosts are sometimes empty.
  if ! port_listening ':443 '; then
    repair_plesk_web_if_allowed
    reload_nginx_safe || systemctl restart nginx
  fi
fi

if ! smoke_test_domains; then
  log "Smoke failed — running plesk repair web"
  repair_plesk_web_if_allowed
  start_apache_if_needed
  reload_nginx_safe || systemctl restart nginx
  sleep 2
  smoke_test_domains || true
fi

log "=== recover done ==="
