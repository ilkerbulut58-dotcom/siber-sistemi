#!/usr/bin/env bash
# Run web-realistic-active benchmark N times for determinism measurement (Faz 11.5).
set -euo pipefail

ROOT="${1:-.}"
RUNS="${2:-5}"
COMPOSE_FILE="${ROOT}/docker-compose.realistic.yml"
STORAGE="${BENCHMARK_STORAGE_PATH:-/tmp/siber-benchmark-determinism}"
SUMMARY="${STORAGE}/determinism-summary.json"

mkdir -p "${STORAGE}/reports"
chmod -R 777 "$(dirname "$STORAGE")" 2>/dev/null || true

docker compose -f "$COMPOSE_FILE" --profile realistic --profile realistic-runner build benchmark-runner

run_once() {
  local run_index="$1"
  docker compose -f "$COMPOSE_FILE" --profile realistic --profile realistic-runner run --rm \
    -v "${STORAGE}:${STORAGE}" \
    -e "DATABASE_URL=${DATABASE_URL:?DATABASE_URL is required}" \
    -e "REDIS_URL=${REDIS_URL:?REDIS_URL is required}" \
    -e "BENCHMARK_GATE_MODE=${BENCHMARK_GATE_MODE:-report}" \
    -e "BENCHMARK_STORAGE_PATH=${STORAGE}" \
    -e "BENCHMARK_ACTIVE_REALISTIC_ENABLED=true" \
    -e "BENCHMARK_ACTIVE_SCAN_ALLOWED=true" \
    -e "BENCHMARK_DETERMINISM_RUN=${run_index}" \
    benchmark-runner run --suite web-realistic-active --subset main
}

for i in $(seq 1 "$RUNS"); do
  echo "=== Determinism run ${i}/${RUNS} ==="
  run_once "$i"
done

python "${ROOT}/scripts/summarize-determinism-runs.py" "${STORAGE}" "${RUNS}" > "${SUMMARY}"
cat "${SUMMARY}"
