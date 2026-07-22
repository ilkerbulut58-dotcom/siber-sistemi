#!/usr/bin/env bash
# Run realistic active benchmark suites inside the pinned benchmark-runner container.
set -euo pipefail

ROOT="${1:-.}"
SUBSET="${2:-main}"
COMPOSE_FILE="${ROOT}/docker-compose.realistic.yml"
STORAGE="${BENCHMARK_STORAGE_PATH:-/tmp/siber-benchmark}"

mkdir -p "${STORAGE}/reports"
chmod -R 777 "$(dirname "$STORAGE")" 2>/dev/null || true
chmod -R 777 "$STORAGE" 2>/dev/null || true

docker compose -f "$COMPOSE_FILE" --profile realistic --profile realistic-runner build benchmark-runner

run_suite() {
  local suite="$1"
  local args=(run --suite "$suite")
  if [ -n "$SUBSET" ]; then
    args+=(--subset "$SUBSET")
  fi

  docker compose -f "$COMPOSE_FILE" --profile realistic --profile realistic-runner run --rm \
    -v "${STORAGE}:${STORAGE}" \
    -e "DATABASE_URL=${DATABASE_URL:?DATABASE_URL is required}" \
    -e "REDIS_URL=${REDIS_URL:?REDIS_URL is required}" \
    -e "BENCHMARK_GATE_MODE=${BENCHMARK_GATE_MODE:-report}" \
    -e "BENCHMARK_STORAGE_PATH=${STORAGE}" \
    -e "BENCHMARK_ACTIVE_REALISTIC_ENABLED=true" \
    -e "BENCHMARK_ACTIVE_SCAN_ALLOWED=true" \
    benchmark-runner "${args[@]}"
}

run_suite web-realistic-active
run_suite api-realistic-active
ls -la "${STORAGE}/reports" || true
