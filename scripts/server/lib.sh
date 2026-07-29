#!/usr/bin/env bash
# Shared helpers for single-server Plesk/nginx/apache guardrails.
# Installed on server at /opt/siber/scripts/server/lib.sh

set -euo pipefail

SERVER_IP="${SERVER_IP:-87.106.10.169}"
SIBER_ROOT="${SIBER_ROOT:-/opt/siber}"
LOG_TAG="${LOG_TAG:-siber-web-guard}"
STATE_DIR="${STATE_DIR:-/var/run/siber-web-guard}"
REPAIR_COOLDOWN_SEC="${REPAIR_COOLDOWN_SEC:-900}"

log() {
  echo "[$(date -Iseconds)] [$LOG_TAG] $*"
}

ensure_state_dir() {
  mkdir -p "$STATE_DIR"
}

wait_for_ip() {
  local ip="$1"
  local max="${2:-60}"
  local i=0
  while [ "$i" -lt "$max" ]; do
    if ip -4 addr show | grep -q "inet ${ip}/"; then
      return 0
    fi
    sleep 2
    i=$((i + 2))
  done
  log "WARN: IP ${ip} not ready after ${max}s"
  return 1
}

service_active() {
  systemctl is-active --quiet "$1"
}

port_listening() {
  ss -lntp 2>/dev/null | grep -q "$1"
}

http_code() {
  local url="$1"
  local host="${2:-}"
  local extra=()
  if [ -n "$host" ]; then
    extra+=(-H "Host: ${host}")
  fi
  curl -sS -k -o /dev/null -w '%{http_code}' --connect-timeout 8 "${extra[@]}" "$url" 2>/dev/null || echo '000'
}

enable_boot_services() {
  systemctl enable apache2 nginx docker 2>/dev/null || true
}

start_apache_if_needed() {
  if ! service_active apache2; then
    log "Starting apache2"
    systemctl start apache2
  fi
}

start_nginx_if_needed() {
  if ! service_active nginx; then
    log "Starting nginx"
    systemctl start nginx
  fi
}

reload_nginx_safe() {
  if nginx -t 2>/dev/null; then
    systemctl reload nginx
    return 0
  fi
  log "ERROR: nginx -t failed; not reloading"
  return 1
}

repair_plesk_web_if_allowed() {
  ensure_state_dir
  local stamp="$STATE_DIR/last-plesk-repair"
  if [ -f "$stamp" ]; then
    local last now
    last=$(stat -c %Y "$stamp" 2>/dev/null || echo 0)
    now=$(date +%s)
    if [ $((now - last)) -lt "$REPAIR_COOLDOWN_SEC" ]; then
      log "Skipping plesk repair web (cooldown active)"
      return 0
    fi
  fi
  log "Running plesk repair web -y"
  plesk repair web -y >/dev/null 2>&1 || plesk repair web -y
  touch "$stamp"
}

ensure_https_listeners() {
  if port_listening ':443 '; then
    return 0
  fi
  log "HTTPS 443 not listening — repairing Plesk web config"
  repair_plesk_web_if_allowed
  start_apache_if_needed
  reload_nginx_safe || systemctl restart nginx
}

start_siber_stack() {
  if [ ! -d "$SIBER_ROOT" ]; then
    log "WARN: $SIBER_ROOT missing; skip docker stack"
    return 0
  fi
  if ! service_active docker; then
    log "Starting docker"
    systemctl start docker
    sleep 3
  fi
  (
    cd "$SIBER_ROOT"
    docker compose -f docker-compose.prod.yml up -d
  )
}

start_turbridge_if_needed() {
  if curl -sf http://127.0.0.1:3006/ >/dev/null 2>&1; then
    return 0
  fi
  log "Turbridge :3006 down — trying PM2"
  if command -v pm2 >/dev/null 2>&1; then
    pm2 resurrect 2>/dev/null || true
    pm2 restart all 2>/dev/null || true
    sleep 3
  fi
}

reconfigure_domain_safe() {
  local domain="$1"
  if [ -z "$domain" ]; then
    return 1
  fi
  if [ ! -d "/var/www/vhosts/system/${domain}" ]; then
    log "WARN: domain ${domain} not found"
    return 1
  fi
  log "Reconfigure domain: ${domain}"
  /usr/local/psa/admin/sbin/httpdmng --reconfigure-domain "$domain" || true
  reload_nginx_safe
}

smoke_test_domains() {
  local failed=0
  local domains=(
    "siber.cloudnira.com"
    "turbridge.de"
    "cloudnira.com"
    "wolkeshopping.de"
  )
  for d in "${domains[@]}"; do
    local code
    code=$(http_code "https://${SERVER_IP}/" "$d")
    if [ "$code" = "000" ] || [ "$code" = "502" ] || [ "$code" = "503" ]; then
      log "FAIL smoke ${d} -> ${code}"
      failed=$((failed + 1))
    else
      log "OK smoke ${d} -> ${code}"
    fi
  done
  return "$failed"
}
