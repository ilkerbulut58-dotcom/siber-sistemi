#!/usr/bin/env bash
# Wait for realistic benchmark fixtures (Juice Shop, crAPI, ZAP) to become healthy.
set -euo pipefail

ROOT="${1:-.}"
COMPOSE_FILE="${ROOT}/docker-compose.realistic.yml"
PROJECT="${COMPOSE_PROJECT_NAME:-siber-sistemi}"

juice_container="${PROJECT}-benchmark-juice-proxy-1"
crapi_container="${PROJECT}-benchmark-crapi-proxy-1"
zap_container="${PROJECT}-benchmark-zap-1"

health_status() {
  local container="$1"
  docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container" 2>/dev/null || echo missing
}

for attempt in $(seq 1 90); do
  juice="$(health_status "$juice_container")"
  crapi="$(health_status "$crapi_container")"
  zap="$(health_status "$zap_container")"
  echo "wait=${attempt} juice_proxy=${juice} crapi_proxy=${crapi} zap=${zap}"
  if [ "$juice" = "healthy" ] && [ "$crapi" = "healthy" ] && [ "$zap" = "healthy" ]; then
    echo "Realistic fixtures healthy (including ZAP daemon)"
    exit 0
  fi
  sleep 2
done

echo "Realistic fixtures failed health check"
docker compose -f "$COMPOSE_FILE" --profile realistic ps
docker compose -f "$COMPOSE_FILE" --profile realistic logs benchmark-zap --tail 80 || true
docker compose -f "$COMPOSE_FILE" --profile realistic logs benchmark-crapi-identity --tail 120 || true
docker compose -f "$COMPOSE_FILE" --profile realistic logs benchmark-crapi-workshop --tail 120 || true
docker compose -f "$COMPOSE_FILE" --profile realistic logs benchmark-crapi-web --tail 80 || true
docker compose -f "$COMPOSE_FILE" --profile realistic logs benchmark-crapi-proxy --tail 80 || true
exit 1
